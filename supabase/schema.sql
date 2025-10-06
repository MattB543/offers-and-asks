-- EA Global Attendee Matching - Supabase Schema
-- Run this SQL in your Supabase SQL Editor to set up all tables, indexes, and functions
-- Created: 2025-10-06

-- ============================================================================
-- STEP 1: Enable pgvector extension
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- STEP 2: Create Tables
-- ============================================================================

-- Attendees table
-- Maps directly to extracted_data.json structure
CREATE TABLE IF NOT EXISTS attendees (
  id INTEGER PRIMARY KEY,
  first_name TEXT,
  last_name TEXT,
  company TEXT,
  job_title TEXT,
  country TEXT,
  linkedin TEXT,
  swapcard TEXT,
  biography TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Offerings table (with vector embeddings)
-- Maps to embeddings.json "offerings" array
CREATE TABLE IF NOT EXISTS offerings (
  id SERIAL PRIMARY KEY,
  attendee_id INTEGER REFERENCES attendees(id) ON DELETE CASCADE,
  text TEXT NOT NULL,
  embedding vector(1536),  -- 1536-dim to match gemini-embedding-001
  created_at TIMESTAMP DEFAULT NOW()
);

-- Requests table (with vector embeddings)
-- Maps to embeddings.json "requests" array
CREATE TABLE IF NOT EXISTS requests (
  id SERIAL PRIMARY KEY,
  attendee_id INTEGER REFERENCES attendees(id) ON DELETE CASCADE,
  text TEXT NOT NULL,
  embedding vector(1536),  -- 1536-dim to match gemini-embedding-001
  created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- STEP 3: Create Indexes
-- ============================================================================

-- B-tree indexes for foreign key lookups
CREATE INDEX IF NOT EXISTS idx_offerings_attendee ON offerings(attendee_id);
CREATE INDEX IF NOT EXISTS idx_requests_attendee ON requests(attendee_id);

-- HNSW vector indexes for similarity search
-- HNSW is recommended over IVFFlat for:
-- - Better query performance
-- - No need to rebuild when data changes
-- - More robust with growing datasets
CREATE INDEX IF NOT EXISTS idx_offerings_embedding ON offerings
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_requests_embedding ON requests
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

-- Full-text search index for name lookups
CREATE INDEX IF NOT EXISTS idx_attendees_name ON attendees
  USING gin(to_tsvector('english', first_name || ' ' || last_name));

-- ============================================================================
-- STEP 4: Create Helper Functions for Vector Search
-- ============================================================================

-- Function to match offerings by vector similarity
CREATE OR REPLACE FUNCTION match_offerings(
  query_embedding vector(1536),
  match_threshold float,
  match_count int,
  exclude_attendee_id int DEFAULT NULL
)
RETURNS TABLE (
  attendee_id int,
  text text,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    offerings.attendee_id,
    offerings.text,
    1 - (offerings.embedding <=> query_embedding) as similarity
  FROM offerings
  WHERE (exclude_attendee_id IS NULL OR offerings.attendee_id != exclude_attendee_id)
    AND 1 - (offerings.embedding <=> query_embedding) > match_threshold
  ORDER BY offerings.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- Function to match requests by vector similarity
CREATE OR REPLACE FUNCTION match_requests(
  query_embedding vector(1536),
  match_threshold float,
  match_count int,
  exclude_attendee_id int DEFAULT NULL
)
RETURNS TABLE (
  attendee_id int,
  text text,
  similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    requests.attendee_id,
    requests.text,
    1 - (requests.embedding <=> query_embedding) as similarity
  FROM requests
  WHERE (exclude_attendee_id IS NULL OR requests.attendee_id != exclude_attendee_id)
    AND 1 - (requests.embedding <=> query_embedding) > match_threshold
  ORDER BY requests.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================
-- Run these after uploading data to verify everything works

-- Check table counts
-- SELECT 'attendees' as table_name, COUNT(*) as count FROM attendees
-- UNION ALL
-- SELECT 'offerings', COUNT(*) FROM offerings
-- UNION ALL
-- SELECT 'requests', COUNT(*) FROM requests;

-- Check indexes exist
-- SELECT tablename, indexname, indexdef
-- FROM pg_indexes
-- WHERE tablename IN ('attendees', 'offerings', 'requests')
-- ORDER BY tablename, indexname;

-- Test vector search (replace with actual embedding vector)
-- SELECT * FROM match_offerings(
--   (SELECT embedding FROM offerings LIMIT 1),
--   0.5,
--   10,
--   null
-- );
