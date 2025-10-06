-- Pre-computed Matches Migration
-- This adds tables to store pre-computed top-50 matches for instant username search
-- Created: 2025-10-06
-- Purpose: Optimize search_by_username by pre-computing all similarity matches

-- ============================================================================
-- STEP 1: Add synthetic offering columns to requests table
-- ============================================================================
-- When matching requests to offerings, we convert requests to "synthetic offerings"
-- Store both the text and embedding for reuse

ALTER TABLE requests
  ADD COLUMN IF NOT EXISTS synthetic_offering_text TEXT,
  ADD COLUMN IF NOT EXISTS synthetic_offering_embedding vector(1536);

COMMENT ON COLUMN requests.synthetic_offering_text IS
  'The request converted to synthetic offering form (e.g., "need AI safety mentor" -> "can provide AI safety mentorship")';
COMMENT ON COLUMN requests.synthetic_offering_embedding IS
  'Embedding of the synthetic offering text, used for matching against real offerings';

-- ============================================================================
-- STEP 2: Create pre-computed match tables
-- ============================================================================

-- For each request, store top 50 offerings that fulfill it
-- This enables instant lookup: "Given this request, who can help?"
CREATE TABLE IF NOT EXISTS request_to_offering_matches (
  request_id INTEGER REFERENCES requests(id) ON DELETE CASCADE,
  offering_id INTEGER REFERENCES offerings(id) ON DELETE CASCADE,
  similarity_score FLOAT NOT NULL,
  rank INTEGER NOT NULL CHECK (rank >= 1 AND rank <= 50),
  created_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (request_id, offering_id)
);

-- For each offering, store top 50 requests it can fulfill
-- This enables instant lookup: "Given this offering, who needs help?"
CREATE TABLE IF NOT EXISTS offering_to_request_matches (
  offering_id INTEGER REFERENCES offerings(id) ON DELETE CASCADE,
  request_id INTEGER REFERENCES requests(id) ON DELETE CASCADE,
  similarity_score FLOAT NOT NULL,
  rank INTEGER NOT NULL CHECK (rank >= 1 AND rank <= 50),
  created_at TIMESTAMP DEFAULT NOW(),
  PRIMARY KEY (offering_id, request_id)
);

-- ============================================================================
-- STEP 3: Create indexes for fast lookups
-- ============================================================================

-- Index for looking up all matches for a specific request
CREATE INDEX IF NOT EXISTS idx_request_matches_by_request
  ON request_to_offering_matches(request_id, rank);

-- Index for looking up all matches for a specific offering
CREATE INDEX IF NOT EXISTS idx_offering_matches_by_offering
  ON offering_to_request_matches(offering_id, rank);

-- Index for looking up who matched with a specific offering
CREATE INDEX IF NOT EXISTS idx_request_matches_by_offering
  ON request_to_offering_matches(offering_id);

-- Index for looking up who matched with a specific request
CREATE INDEX IF NOT EXISTS idx_offering_matches_by_request
  ON offering_to_request_matches(request_id);

-- ============================================================================
-- STEP 4: Create helper functions for pre-computed match lookups
-- ============================================================================

-- Get top matches for a request (who can help fulfill this request?)
CREATE OR REPLACE FUNCTION get_request_matches(
  p_request_id INTEGER,
  p_limit INTEGER DEFAULT 50
)
RETURNS TABLE (
  offering_id INTEGER,
  attendee_id INTEGER,
  offering_text TEXT,
  similarity_score FLOAT,
  rank INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    m.offering_id,
    o.attendee_id,
    o.text as offering_text,
    m.similarity_score,
    m.rank
  FROM request_to_offering_matches m
  JOIN offerings o ON m.offering_id = o.id
  WHERE m.request_id = p_request_id
  ORDER BY m.rank
  LIMIT p_limit;
END;
$$;

-- Get top matches for an offering (who needs this offering?)
CREATE OR REPLACE FUNCTION get_offering_matches(
  p_offering_id INTEGER,
  p_limit INTEGER DEFAULT 50
)
RETURNS TABLE (
  request_id INTEGER,
  attendee_id INTEGER,
  request_text TEXT,
  similarity_score FLOAT,
  rank INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    m.request_id,
    r.attendee_id,
    r.text as request_text,
    m.similarity_score,
    m.rank
  FROM offering_to_request_matches m
  JOIN requests r ON m.request_id = r.id
  WHERE m.offering_id = p_offering_id
  ORDER BY m.rank
  LIMIT p_limit;
END;
$$;

-- Get all matches for an attendee by username
-- Returns both directions: people who can help them + people they can help
CREATE OR REPLACE FUNCTION get_attendee_matches_by_name(
  p_first_name TEXT,
  p_last_name TEXT,
  p_limit_per_match INTEGER DEFAULT 50
)
RETURNS TABLE (
  match_direction TEXT,  -- 'can_help_me' or 'i_can_help'
  my_item_type TEXT,     -- 'request' or 'offering'
  my_item_id INTEGER,
  my_item_text TEXT,
  match_attendee_id INTEGER,
  match_item_type TEXT,  -- 'offering' or 'request'
  match_item_id INTEGER,
  match_item_text TEXT,
  similarity_score FLOAT,
  rank INTEGER
)
LANGUAGE plpgsql
AS $$
DECLARE
  v_attendee_id INTEGER;
BEGIN
  -- Get the attendee ID
  SELECT id INTO v_attendee_id
  FROM attendees
  WHERE first_name = p_first_name AND last_name = p_last_name
  LIMIT 1;

  IF v_attendee_id IS NULL THEN
    RAISE EXCEPTION 'Attendee not found: % %', p_first_name, p_last_name;
  END IF;

  -- Return matches where their requests are fulfilled by others' offerings
  RETURN QUERY
  SELECT
    'can_help_me'::TEXT as match_direction,
    'request'::TEXT as my_item_type,
    r.id as my_item_id,
    r.text as my_item_text,
    o.attendee_id as match_attendee_id,
    'offering'::TEXT as match_item_type,
    m.offering_id as match_item_id,
    o.text as match_item_text,
    m.similarity_score,
    m.rank
  FROM requests r
  JOIN request_to_offering_matches m ON r.id = m.request_id
  JOIN offerings o ON m.offering_id = o.id
  WHERE r.attendee_id = v_attendee_id
    AND m.rank <= p_limit_per_match
  ORDER BY r.id, m.rank;

  -- Return matches where their offerings fulfill others' requests
  RETURN QUERY
  SELECT
    'i_can_help'::TEXT as match_direction,
    'offering'::TEXT as my_item_type,
    o.id as my_item_id,
    o.text as my_item_text,
    r.attendee_id as match_attendee_id,
    'request'::TEXT as match_item_type,
    m.request_id as match_item_id,
    r.text as match_item_text,
    m.similarity_score,
    m.rank
  FROM offerings o
  JOIN offering_to_request_matches m ON o.id = m.offering_id
  JOIN requests r ON m.request_id = r.id
  WHERE o.attendee_id = v_attendee_id
    AND m.rank <= p_limit_per_match
  ORDER BY o.id, m.rank;
END;
$$;

-- ============================================================================
-- STEP 5: Add utility functions for managing pre-computed matches
-- ============================================================================

-- Function to get statistics on pre-computed matches
CREATE OR REPLACE FUNCTION get_precomputed_match_stats()
RETURNS TABLE (
  metric TEXT,
  value BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT 'total_requests' as metric, COUNT(*)::BIGINT as value FROM requests
  UNION ALL
  SELECT 'total_offerings', COUNT(*)::BIGINT FROM offerings
  UNION ALL
  SELECT 'requests_with_synthetic_embeddings', COUNT(*)::BIGINT FROM requests WHERE synthetic_offering_embedding IS NOT NULL
  UNION ALL
  SELECT 'request_to_offering_matches', COUNT(*)::BIGINT FROM request_to_offering_matches
  UNION ALL
  SELECT 'offering_to_request_matches', COUNT(*)::BIGINT FROM offering_to_request_matches
  UNION ALL
  SELECT 'avg_matches_per_request', AVG(match_count)::BIGINT FROM (
    SELECT request_id, COUNT(*) as match_count FROM request_to_offering_matches GROUP BY request_id
  ) sub
  UNION ALL
  SELECT 'avg_matches_per_offering', AVG(match_count)::BIGINT FROM (
    SELECT offering_id, COUNT(*) as match_count FROM offering_to_request_matches GROUP BY offering_id
  ) sub;
END;
$$;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- After running the pre-computation script, verify with:
-- SELECT * FROM get_precomputed_match_stats();

-- Test username lookup:
-- SELECT * FROM get_attendee_matches_by_name('John', 'Smith', 25);

-- Check table sizes:
-- SELECT
--   'request_to_offering_matches' as table_name,
--   COUNT(*) as rows,
--   pg_size_pretty(pg_total_relation_size('request_to_offering_matches')) as size
-- FROM request_to_offering_matches
-- UNION ALL
-- SELECT
--   'offering_to_request_matches',
--   COUNT(*),
--   pg_size_pretty(pg_total_relation_size('offering_to_request_matches'))
-- FROM offering_to_request_matches;
