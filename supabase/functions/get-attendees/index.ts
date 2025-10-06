// get-attendees/index.ts
// Returns a list of all attendees for the searchable dropdown

import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import { corsHeaders, handleCors } from '../_shared/cors.ts';

Deno.serve(async (req) => {
  // Handle CORS preflight
  const corsResponse = handleCors(req);
  if (corsResponse) return corsResponse;

  try {
    console.log('[START] Fetching attendees list');

    // Initialize Supabase client
    const supabase = createClient(
      Deno.env.get('SUPABASE_URL')!,
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
    );
    console.log('[1] Supabase client initialized');

    // Fetch all attendees (id, first_name, last_name only)
    console.log('[2] Querying attendees table...');
    const { data: attendees, error } = await supabase
      .from('attendees')
      .select('id, first_name, last_name')
      .order('last_name', { ascending: true })
      .order('first_name', { ascending: true });

    if (error) {
      console.error('[ERROR] Failed to fetch attendees:', error);
      throw error;
    }

    console.log(`[3] Fetched ${attendees?.length || 0} attendees`);

    // Format for dropdown: { value: "Full Name", label: "Full Name", id: number }
    const formattedAttendees = (attendees || []).map(att => ({
      id: att.id,
      value: `${att.first_name} ${att.last_name}`,
      label: `${att.first_name} ${att.last_name}`,
    }));

    console.log('[END] Attendees list prepared successfully');

    return new Response(JSON.stringify(formattedAttendees), {
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  } catch (error) {
    console.error('[ERROR] Error in get-attendees:', error);
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500,
      headers: { ...corsHeaders, 'Content-Type': 'application/json' },
    });
  }
});
