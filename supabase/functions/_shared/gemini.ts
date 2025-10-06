// _shared/gemini.ts
// Gemini API helpers for Deno Edge Functions
// Matches Python implementation in ea_matching.py

const GEMINI_API_KEY = Deno.env.get('GEMINI_API_KEY')!;
const LLM_MODEL = 'gemini-2.5-pro';  // For re-ranking (complex task requiring high quality)
const SYNTHETIC_MODEL = 'gemini-2.5-flash';  // For request→offering transformation (simple task, faster)
const EMBEDDING_MODEL = 'gemini-embedding-001';  // Matches Python: ea_matching.py line 26
const EMBEDDING_DIM = 1536;  // Matches Python: ea_matching.py line 27

interface EmbeddingResponse {
  embedding: { values: number[] };  // API returns singular "embedding", not plural
}

interface GenerateResponse {
  candidates: Array<{
    content: {
      parts: Array<{ text: string }>;
    };
  }>;
}

/**
 * Generate 1536-dim embedding for text using Gemini
 * Matches Python: ea_matching.py lines 227-251
 */
export async function generateEmbedding(text: string): Promise<number[]> {
  if (!text) {
    throw new Error('generateEmbedding: text parameter is required');
  }

  const url = `https://generativelanguage.googleapis.com/v1beta/models/${EMBEDDING_MODEL}:embedContent?key=${GEMINI_API_KEY}`;

  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      content: { parts: [{ text }] },
      task_type: 'RETRIEVAL_DOCUMENT',  // snake_case for API
      output_dimensionality: EMBEDDING_DIM,  // snake_case for API
    }),
  });

  if (!response) {
    throw new Error('Gemini embedding: No response received from API');
  }

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Gemini embedding failed: ${response.statusText} - ${errorText}`);
  }

  const data: EmbeddingResponse = await response.json();

  if (!data) {
    throw new Error('Gemini embedding: Response JSON parsing returned null/undefined');
  }

  // Debug logging and validation
  if (!data.embedding || !data.embedding.values) {
    console.error('Invalid embedding response:', JSON.stringify(data));
    throw new Error(`No embedding in response. Full response: ${JSON.stringify(data)}`);
  }

  const embedding = data.embedding.values;

  if (!embedding || embedding.length === 0) {
    console.error('Empty embedding values:', JSON.stringify(data));
    throw new Error(`Empty embedding values. Full response: ${JSON.stringify(data)}`);
  }

  // L2 normalize (required for cosine similarity via dot product)
  // Matches Python: ea_matching.py lines 244-245
  const norm = Math.sqrt(embedding.reduce((sum, val) => sum + val * val, 0));
  return embedding.map(val => val / norm);
}

/**
 * Generate synthetic offering from request
 * Matches Python: ea_matching.py lines 553-597
 */
export async function generateSyntheticOffering(request: string): Promise<string> {
  if (!request) {
    throw new Error('generateSyntheticOffering: request parameter is required');
  }

  const prompt = `You are transforming a REQUEST into a synthetic OFFERING for EA Global attendee matching. The synthetic offering must match the writing style of real EA Global attendee offers for optimal semantic matching.

ORIGINAL REQUEST: "${request}"

TRANSFORMATION RULES:

1. **Match the EA Offer Style:**
   - First-person perspective ("I can...", "Happy to...", "I'm happy to...")
   - Collaborative, purpose-driven tone
   - Action-oriented verbs: "happy to discuss", "can offer advice on", "can help with", "sharing my experience in"

2. **Preserve All Specifics:**
   - Domain expertise, experience level, location, constraints
   - Career stage, technical details, geographic context

EXAMPLES:

Request: "Seeking technical cofounder with AI safety background for startup in San Francisco"
→ "I'm a technical person with an AI safety background, happy to discuss cofounder opportunities for startups in the San Francisco area."

Request: "Looking for mentorship on transitioning from software engineering to AI safety research"
→ "Having transitioned from software engineering to AI safety research, I'm happy to mentor folks making a similar career shift. I can share insights on research directions, necessary skills, and making connections in the field."

Request: "Need connections to biosecurity policy experts in DC area"
→ "I can connect you with biosecurity policy experts in the DC area."

Return ONLY the synthetic offering text (1-3 sentences), nothing else.`;

  const url = `https://generativelanguage.googleapis.com/v1beta/models/${SYNTHETIC_MODEL}:generateContent?key=${GEMINI_API_KEY}`;

  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      contents: [{ parts: [{ text: prompt }] }],
    }),
  });

  if (!response) {
    throw new Error('Gemini LLM: No response received from API');
  }

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Gemini LLM failed: ${response.statusText} - ${errorText}`);
  }

  const data: GenerateResponse = await response.json();

  if (!data) {
    throw new Error('Gemini LLM: Response JSON parsing returned null/undefined');
  }

  // Debug logging and validation
  if (!data.candidates || data.candidates.length === 0) {
    console.error('Invalid LLM response:', JSON.stringify(data));
    throw new Error(`No candidates in response. Full response: ${JSON.stringify(data)}`);
  }

  if (!data.candidates[0]?.content?.parts?.[0]?.text) {
    throw new Error(`Invalid response structure. Full response: ${JSON.stringify(data)}`);
  }

  return data.candidates[0].content.parts[0].text.trim();
}

/**
 * Re-rank matches using LLM
 * Matches Python: ea_matching.py lines 333-511
 */
export async function rerankMatches(
  query: string,
  queryType: 'request' | 'offering',
  matches: Array<{ attendee_id: number; text: string; similarity: number; attendee: any }>,
  topK: number = 25
): Promise<any[]> {
  // Build match descriptions for LLM
  const matchDescriptions = matches.map((match, idx) => ({
    index: idx,
    attendee_id: match.attendee_id,
    name: `${match.attendee.first_name} ${match.attendee.last_name}`,
    company: match.attendee.company,
    text: match.text,
    similarity_score: Math.round(match.similarity * 1000) / 1000,
  }));

  const prompt = queryType === 'request'
    ? `You are matching EA Global attendees. Someone needs help with this:

REQUEST: "${query}"

Below are ${matches.length} potential helpers (ranked by semantic similarity). Your task: Select the BEST ${topK} matches using strict quality criteria.

EVALUATION CRITERIA:
1. **Direct Relevance**: Does the offering directly address the request?
2. **Expertise Level**: Does experience/background match what's needed?
3. **Specificity**: Concrete capabilities vs vague offerings?

TASK: Remove poor matches and prioritize high-quality matches.

CANDIDATES:
${JSON.stringify(matchDescriptions, null, 2)}

Return ONLY a JSON array of indices for the top ${topK} matches, ranked best to worst:
[index1, index2, index3, ...]

No markdown, no explanation, just the array.`
    : `You are matching EA Global attendees. Someone can provide this:

OFFERING: "${query}"

Below are ${matches.length} people who might need this (ranked by semantic similarity). Your task: Select the BEST ${topK} matches using strict quality criteria.

EVALUATION CRITERIA:
1. **Need Alignment**: Does the request actually need this offering?
2. **Scope Match**: Is the offering's level/scope appropriate?
3. **Mutual Benefit**: Would this connection be valuable for both?

CANDIDATES:
${JSON.stringify(matchDescriptions, null, 2)}

Return ONLY a JSON array of indices for the top ${topK} matches:
[index1, index2, index3, ...]`;

  const url = `https://generativelanguage.googleapis.com/v1beta/models/${LLM_MODEL}:generateContent?key=${GEMINI_API_KEY}`;

  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      contents: [{ parts: [{ text: prompt }] }],
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Gemini re-ranking failed: ${response.statusText} - ${errorText}`);
  }

  const data: GenerateResponse = await response.json();

  // Debug logging and validation
  if (!data.candidates || data.candidates.length === 0) {
    console.error('Invalid re-ranking response:', JSON.stringify(data));
    throw new Error(`No candidates in re-ranking response. Full response: ${JSON.stringify(data)}`);
  }

  let resultText = data.candidates[0].content.parts[0].text.trim();

  // Clean markdown code blocks if present
  if (resultText.startsWith('```')) {
    resultText = resultText.split('```')[1];
    if (resultText.startsWith('json')) {
      resultText = resultText.substring(4);
    }
    resultText = resultText.trim();
  }

  const topIndices: number[] = JSON.parse(resultText);

  // Build final results with validation
  const finalResults = [];

  for (const idx of topIndices.slice(0, topK)) {
    // Validate index is within bounds
    if (idx < 0 || idx >= matches.length) {
      console.error(`Invalid index ${idx} returned by LLM, matches length: ${matches.length}`);
      continue;
    }

    const match = matches[idx];

    // Validate match and attendee exist
    if (!match) {
      console.error(`No match found at index ${idx}`);
      continue;
    }

    if (!match.attendee) {
      console.error(`No attendee data for match at index ${idx}:`, JSON.stringify(match));
      continue;
    }

    finalResults.push({
      name: `${match.attendee.first_name} ${match.attendee.last_name}`,
      company: match.attendee.company || '',
      job_title: match.attendee.job_title || '',
      country: match.attendee.country || '',
      text: match.text,
      similarity_score: Math.round(match.similarity * 1000) / 1000,
      linkedin: match.attendee.linkedin || '',
      swapcard: match.attendee.swapcard || '',
      biography: match.attendee.biography || '',
    });
  }

  return finalResults;
}
