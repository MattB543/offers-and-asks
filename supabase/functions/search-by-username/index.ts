// search-by-username/index.ts
// Bidirectional matching for a specific attendee
// Matches Python: ea_matching.py lines 514-666

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import { corsHeaders, handleCors } from '../_shared/cors.ts';
import { generateEmbedding, generateSyntheticOffering, rerankMatches } from '../_shared/gemini.ts';

Deno.serve(async (req) => {
  // Handle CORS preflight
  const corsResponse = handleCors(req);
  if (corsResponse) return corsResponse;

  try {
    console.log('[START] Username search initiated');
    const { name } = await req.json();
    console.log(`[1] Searching for attendee: "${name}"`);

    if (!name || typeof name !== 'string') {
      console.log('[ERROR] Invalid name parameter');
      return new Response(
        JSON.stringify({ error: 'Name parameter is required and must be a string' }),
        { status: 400, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    // Initialize Supabase client
    const supabase = createClient(
      Deno.env.get('SUPABASE_URL')!,
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
    );
    console.log('[2] Supabase client initialized');

    // Search for attendee by name (case-insensitive partial match)
    console.log(`[3] Querying attendees table with name: "${name}"`);

    // Parse name - split by spaces to handle "First Last" format
    const nameParts = name.trim().split(/\s+/);
    console.log(`[3a] Name parts: ${JSON.stringify(nameParts)} (${nameParts.length} parts)`);

    let attendees = null;
    let searchError = null;

    // Strategy 1: If multiple words, try exact first + last name match
    if (nameParts.length >= 2) {
      const firstName = nameParts[0];
      const lastName = nameParts.slice(1).join(' ');
      console.log(`[3b] Trying exact match: first="${firstName}", last="${lastName}"`);

      const result = await supabase
        .from('attendees')
        .select('*')
        .ilike('first_name', firstName)
        .ilike('last_name', lastName)
        .limit(1);

      attendees = result.data;
      searchError = result.error;
      console.log(`[3c] Exact match result: ${attendees?.length || 0} attendees found`);
    }

    // Strategy 2: If no match, try partial match on concatenated name
    if (!attendees || attendees.length === 0) {
      console.log(`[3d] Trying partial match on either first or last name containing: "${name}"`);
      const result = await supabase
        .from('attendees')
        .select('*')
        .or(`first_name.ilike.%${name}%,last_name.ilike.%${name}%`)
        .limit(5);

      attendees = result.data;
      searchError = result.error;
      console.log(`[3e] Partial match result: ${attendees?.length || 0} attendees found`);

      if (attendees && attendees.length > 0) {
        console.log(`[3f] Candidates: ${attendees.map(a => `${a.first_name} ${a.last_name}`).join(', ')}`);
      }
    }

    // Strategy 3: If still no match and we have multiple name parts, try fuzzy matching
    if ((!attendees || attendees.length === 0) && nameParts.length >= 2) {
      console.log(`[3g] Trying fuzzy match with each name part`);
      const firstName = nameParts[0];
      const lastName = nameParts[nameParts.length - 1];

      const result = await supabase
        .from('attendees')
        .select('*')
        .or(`first_name.ilike.%${firstName}%,last_name.ilike.%${lastName}%`)
        .limit(5);

      attendees = result.data;
      searchError = result.error;
      console.log(`[3h] Fuzzy match result: ${attendees?.length || 0} attendees found`);

      if (attendees && attendees.length > 0) {
        console.log(`[3i] Fuzzy candidates: ${attendees.map(a => `${a.first_name} ${a.last_name}`).join(', ')}`);
      }
    }

    if (searchError) {
      console.error('[ERROR] Failed to search attendees:', searchError);
      throw searchError;
    }

    if (!attendees || attendees.length === 0) {
      console.log(`[WARN] No attendee found matching "${name}" after trying all search strategies`);
      return new Response(
        JSON.stringify({ error: `No attendee found matching '${name}'` }),
        { status: 404, headers: { ...corsHeaders, 'Content-Type': 'application/json' } }
      );
    }

    const attendee = attendees[0];
    console.log(`[4] Found attendee: ${attendee.first_name} ${attendee.last_name} (ID: ${attendee.id})`);

    // Get attendee's offerings and requests WITH ERROR CHECKING
    console.log(`[5] Fetching offerings for attendee ${attendee.id}...`);
    const { data: attendeeOfferings, error: offeringsError } = await supabase
      .from('offerings')
      .select('text')
      .eq('attendee_id', attendee.id);

    if (offeringsError) {
      console.error('[ERROR] Failed to fetch offerings:', offeringsError);
      throw new Error(`Database error fetching offerings: ${offeringsError.message}`);
    }

    console.log(`[6] Fetching requests for attendee ${attendee.id}...`);
    const { data: attendeeRequests, error: requestsError } = await supabase
      .from('requests')
      .select('text')
      .eq('attendee_id', attendee.id);

    if (requestsError) {
      console.error('[ERROR] Failed to fetch requests:', requestsError);
      throw new Error(`Database error fetching requests: ${requestsError.message}`);
    }

    // Ensure we have arrays even if queries returned null
    const offerings = attendeeOfferings || [];
    const requests = attendeeRequests || [];
    console.log(`[7] Found ${offerings.length} offerings and ${requests.length} requests`);

    const result = {
      attendee: {
        name: `${attendee.first_name} ${attendee.last_name}`,
        company: attendee.company,
        job_title: attendee.job_title,
        country: attendee.country,
      },
      people_who_can_help_you: [],
      people_you_can_help: [],
    };

    // For each request: find matching offerings
    console.log(`[8] Processing ${requests.length} requests for matches...`);
    for (let i = 0; i < requests.length; i++) {
      const req = requests[i];
      console.log(`[8.${i}] Processing request: "${req.text.substring(0, 80)}..."`);

      // Generate synthetic offering
      const syntheticOffering = await generateSyntheticOffering(req.text);
      console.log(`[8.${i}a] Synthetic offering: "${syntheticOffering.substring(0, 80)}..."`);

      // Generate embedding
      const queryEmbedding = await generateEmbedding(syntheticOffering);
      console.log(`[8.${i}b] Generated embedding (${queryEmbedding.length} dimensions)`);

      // Vector search using pgvector WITH ERROR CHECKING
      console.log(`[8.${i}c] Calling match_offerings RPC...`);
      const { data: rawMatches, error: matchError } = await supabase.rpc('match_offerings', {
        query_embedding: queryEmbedding,
        match_threshold: 0.5,
        match_count: 50,
        exclude_attendee_id: attendee.id,
      });

      if (matchError) {
        console.error(`[ERROR] RPC match_offerings failed for request "${req.text.substring(0, 50)}":`, matchError);
        continue; // Skip this request but continue processing others
      }

      console.log(`[8.${i}d] Found ${rawMatches?.length || 0} raw matches`);

      if (rawMatches && rawMatches.length > 0) {
        // Get attendee details for matches
        console.log(`[8.${i}e] Fetching attendee details for ${rawMatches.length} matches...`);
        const matchesWithAttendees = await Promise.all(
          rawMatches.map(async (match: any, idx: number) => {
            const { data: matchAttendee, error: attendeeError } = await supabase
              .from('attendees')
              .select('*')
              .eq('id', match.attendee_id)
              .single();

            if (attendeeError) {
              console.error(`[ERROR] Failed to fetch attendee ${match.attendee_id}:`, attendeeError);
              return null;
            }

            if (!matchAttendee) {
              console.error(`[WARN] No attendee found for id ${match.attendee_id}`);
              return null;
            }

            return { ...match, attendee: matchAttendee };
          })
        );

        // Filter out null entries
        const validMatches = matchesWithAttendees.filter((match) => match !== null);
        console.log(`[8.${i}f] ${validMatches.length} valid matches after filtering`);

        if (validMatches.length > 0) {
          // Re-rank with LLM
          console.log(`[8.${i}g] Re-ranking with LLM...`);
          const finalMatches = await rerankMatches(req.text, 'request', validMatches, 25);
          console.log(`[8.${i}h] Re-ranking returned ${finalMatches.length} final matches`);

          result.people_who_can_help_you.push({
            your_request: req.text,
            matches: finalMatches,
          });
        }
      } else {
        console.log(`[8.${i}] No matches found for this request`);
      }
    }

    // For each offering: find matching requests
    console.log(`[9] Processing ${offerings.length} offerings for matches...`);
    for (let i = 0; i < offerings.length; i++) {
      const offer = offerings[i];
      console.log(`[9.${i}] Processing offering: "${offer.text.substring(0, 80)}..."`);

      // Generate embedding
      const queryEmbedding = await generateEmbedding(offer.text);
      console.log(`[9.${i}a] Generated embedding (${queryEmbedding.length} dimensions)`);

      // Vector search WITH ERROR CHECKING
      console.log(`[9.${i}b] Calling match_requests RPC...`);
      const { data: rawMatches, error: matchError } = await supabase.rpc('match_requests', {
        query_embedding: queryEmbedding,
        match_threshold: 0.5,
        match_count: 50,
        exclude_attendee_id: attendee.id,
      });

      if (matchError) {
        console.error(`[ERROR] RPC match_requests failed for offering "${offer.text.substring(0, 50)}":`, matchError);
        continue; // Skip this offering but continue processing others
      }

      console.log(`[9.${i}c] Found ${rawMatches?.length || 0} raw matches`);

      if (rawMatches && rawMatches.length > 0) {
        // Get attendee details
        console.log(`[9.${i}d] Fetching attendee details for ${rawMatches.length} matches...`);
        const matchesWithAttendees = await Promise.all(
          rawMatches.map(async (match: any) => {
            const { data: matchAttendee, error: attendeeError } = await supabase
              .from('attendees')
              .select('*')
              .eq('id', match.attendee_id)
              .single();

            if (attendeeError) {
              console.error(`[ERROR] Failed to fetch attendee ${match.attendee_id}:`, attendeeError);
              return null;
            }

            if (!matchAttendee) {
              console.error(`[WARN] No attendee found for id ${match.attendee_id}`);
              return null;
            }

            return { ...match, attendee: matchAttendee };
          })
        );

        // Filter out null entries
        const validMatches = matchesWithAttendees.filter((match) => match !== null);
        console.log(`[9.${i}e] ${validMatches.length} valid matches after filtering`);

        if (validMatches.length > 0) {
          // Re-rank
          console.log(`[9.${i}f] Re-ranking with LLM...`);
          const finalMatches = await rerankMatches(offer.text, 'offering', validMatches, 25);
          console.log(`[9.${i}g] Re-ranking returned ${finalMatches.length} final matches`);

          result.people_you_can_help.push({
            your_offering: offer.text,
            matches: finalMatches,
          });
        }
      } else {
        console.log(`[9.${i}] No matches found for this offering`);
      }
    }

    console.log(`[10] Username search completed successfully`);
    console.log(`[10a] Total "people who can help you" groups: ${result.people_who_can_help_you.length}`);
    console.log(`[10b] Total "people you can help" groups: ${result.people_you_can_help.length}`);

    return new Response(JSON.stringify(result), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('Error in search-by-username:', error);
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }
});
