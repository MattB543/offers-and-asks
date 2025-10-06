// search-by-offering/index.ts
// Find people you can help with a custom offering
// Matches Python: ea_matching.py lines 751-776

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import { corsHeaders, handleCors } from '../_shared/cors.ts';
import { generateEmbedding, rerankMatches } from '../_shared/gemini.ts';

Deno.serve(async (req) => {
  // Handle CORS preflight
  const corsResponse = handleCors(req);
  if (corsResponse) return corsResponse;

  try {
    console.log('[START] Offering search initiated');
    const { offering } = await req.json();
    console.log('[1] Received offering:', offering?.substring(0, 100));

    if (!offering || typeof offering !== 'string') {
      console.log('[ERROR] Invalid offering parameter');
      return new Response(
        JSON.stringify({ error: 'Offering parameter is required and must be a string' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    // Initialize Supabase
    const supabase = createClient(
      Deno.env.get('SUPABASE_URL')!,
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
    );
    console.log('[2] Supabase client initialized');

    // 1. Generate embedding for offering (no synthetic transformation needed)
    console.log('[3] Generating embedding...');
    const queryEmbedding = await generateEmbedding(offering);
    console.log('[4] Embedding generated, length:', queryEmbedding?.length);

    // 2. Vector similarity search on requests table
    console.log('[5] Calling match_requests RPC...');
    const { data: rawMatches, error } = await supabase.rpc('match_requests', {
      query_embedding: queryEmbedding,
      match_threshold: 0.5,
      match_count: 50,
      exclude_attendee_id: null,
    });

    if (error) {
      console.error('[ERROR] RPC match_requests error:', error);
      throw error;
    }

    console.log('[6] RPC response received, matches:', rawMatches?.length);

    if (!rawMatches || rawMatches.length === 0) {
      console.log('[6a] No matches found, returning empty results');
      return new Response(
        JSON.stringify({
          query: offering,
          matches: [],
        }),
        {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        }
      );
    }

    // 3. Get attendee details for all matches
    console.log('[7] Fetching attendee details for', rawMatches.length, 'matches...');
    const matchesWithAttendees = await Promise.all(
      rawMatches.map(async (match: any, idx: number) => {
        const { data: attendee, error: attendeeError } = await supabase
          .from('attendees')
          .select('*')
          .eq('id', match.attendee_id)
          .single();

        if (attendeeError) {
          console.error(`[7.${idx}] Failed to fetch attendee ${match.attendee_id}:`, attendeeError);
          return null;
        }

        if (!attendee) {
          console.error(`[7.${idx}] No attendee found for id ${match.attendee_id}`);
          return null;
        }

        return { ...match, attendee };
      })
    );

    // Filter out null entries (failed attendee lookups)
    const validMatches = matchesWithAttendees.filter((match) => match !== null);
    console.log('[8] Valid matches after filtering:', validMatches.length);

    // 4. Re-rank with LLM to top 25
    console.log('[9] Re-ranking with LLM...');
    const finalMatches = await rerankMatches(offering, 'offering', validMatches, 25);
    console.log('[10] Re-ranking returned', finalMatches.length, 'final matches');

    console.log('[END] Offering search completed successfully');

    return new Response(
      JSON.stringify({
        query: offering,
        matches: finalMatches,
      }),
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      }
    );
  } catch (error) {
    console.error('[ERROR] Error in search-by-offering:', error);
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }
});
