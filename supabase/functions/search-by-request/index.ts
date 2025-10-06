// search-by-request/index.ts
// Find people who can help with a custom request
// Matches Python: ea_matching.py lines 669-748

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import { corsHeaders, handleCors } from '../_shared/cors.ts';
import { generateEmbedding, generateSyntheticOffering, rerankMatches } from '../_shared/gemini.ts';

Deno.serve(async (req) => {
  // Handle CORS preflight
  const corsResponse = handleCors(req);
  if (corsResponse) return corsResponse;

  try {
    console.log('[START] Request search initiated');
    const { request } = await req.json();
    console.log('[1] Received request:', request?.substring(0, 100));

    if (!request || typeof request !== 'string') {
      console.log('[ERROR] Invalid request parameter');
      return new Response(
        JSON.stringify({ error: 'Request parameter is required and must be a string' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    // Initialize Supabase
    const supabase = createClient(
      Deno.env.get('SUPABASE_URL')!,
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
    );
    console.log('[2] Supabase client initialized');

    // 1. Generate synthetic offering from request
    console.log('[3] Generating synthetic offering...');
    const syntheticOffering = await generateSyntheticOffering(request);
    console.log('[4] Synthetic offering generated:', syntheticOffering?.substring(0, 100));

    // 2. Generate embedding
    console.log('[5] Generating embedding...');
    const queryEmbedding = await generateEmbedding(syntheticOffering);
    console.log('[6] Embedding generated, length:', queryEmbedding?.length);

    // 3. Vector similarity search using pgvector
    console.log('[7] Calling match_offerings RPC...');
    const rpcResponse = await supabase.rpc('match_offerings', {
      query_embedding: queryEmbedding,
      match_threshold: 0.5,
      match_count: 50,
      exclude_attendee_id: null,
    });

    if (!rpcResponse) {
      throw new Error('No response from match_offerings RPC call');
    }

    const { data: rawMatches, error } = rpcResponse;
    console.log('[8] RPC response received, matches:', rawMatches?.length, 'error:', error);

    if (error) {
      console.error('[ERROR] RPC match_offerings error:', error);
      throw error;
    }

    if (!rawMatches || rawMatches.length === 0) {
      console.log('[8a] No matches found, returning empty results');
      return new Response(
        JSON.stringify({
          query: request,
          matches: [],
        }),
        {
          headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        }
      );
    }

    // 4. Get attendee details for all matches
    console.log('[9] Fetching attendee details for', rawMatches.length, 'matches...');
    const matchesWithAttendees = await Promise.all(
      rawMatches.map(async (match: any, idx: number) => {
        try {
          const response = await supabase
            .from('attendees')
            .select('*')
            .eq('id', match.attendee_id)
            .single();

          if (!response) {
            console.error(`[9.${idx}] No response for attendee ${match.attendee_id}`);
            return null;
          }

          const { data: attendee, error: attendeeError } = response;

          if (attendeeError) {
            console.error(`[9.${idx}] Failed to fetch attendee ${match.attendee_id}:`, attendeeError);
            return null;
          }

          if (!attendee) {
            console.error(`[9.${idx}] No attendee found for id ${match.attendee_id}`);
            return null;
          }

          return { ...match, attendee };
        } catch (e) {
          console.error(`[9.${idx}] Exception fetching attendee ${match.attendee_id}:`, e);
          return null;
        }
      })
    );

    // Filter out null entries (failed attendee lookups)
    const validMatches = matchesWithAttendees.filter((match) => match !== null);
    console.log('[10] Valid matches after filtering:', validMatches.length);

    // 5. Re-rank with LLM to top 25
    console.log('[11] Re-ranking with LLM...');
    const finalMatches = await rerankMatches(request, 'request', validMatches, 25);
    console.log('[12] Re-ranking returned', finalMatches.length, 'final matches');

    console.log('[END] Request search completed successfully');

    return new Response(
      JSON.stringify({
        query: request,
        matches: finalMatches,
      }),
      {
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
      }
    );
  } catch (error) {
    console.error('[ERROR] Error in search-by-request:', error);
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }
});
