"""
EA Global Attendee Matching System
Process attendee data, generate embeddings, and find optimal matches
"""

import os
import json
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from google import genai
from tqdm import tqdm
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set. Please create a .env file with GEMINI_API_KEY=your-api-key")

# Model configurations
LLM_MODEL = "gemini-2.5-pro"
EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIM = 1536

# File paths
DATA_DIR = "/home/claude/ea_data"
CSV_PATH = "/mnt/user-data/uploads/_Do_not_share_with_non-attendees__Swapcard_Attendee_Data___EA_Global__NYC_2025_-_Attendee_Data.csv"
EXTRACTED_DATA_PATH = f"{DATA_DIR}/extracted_data.json"
EMBEDDINGS_PATH = f"{DATA_DIR}/embeddings.json"

# Create data directory
os.makedirs(DATA_DIR, exist_ok=True)

# Initialize Gemini client
client = genai.Client(api_key=GEMINI_API_KEY)


def load_csv() -> pd.DataFrame:
    """Load and clean the attendee CSV data"""
    print("Loading CSV data...")
    
    # Skip the header rows (first 8 rows are metadata)
    df = pd.read_csv(CSV_PATH, skiprows=8)
    
    # Clean column names
    df.columns = df.columns.str.strip()
    
    print(f"Loaded {len(df)} attendees")
    return df


def extract_offerings_and_requests(row: pd.Series) -> Dict:
    """
    Use Gemini to extract distinct offerings and requests from a person's profile
    """
    # Build the profile text
    profile_parts = []
    
    if pd.notna(row.get('Biography')):
        profile_parts.append(f"Biography: {row['Biography']}")
    
    if pd.notna(row.get('Job Title')):
        profile_parts.append(f"Job Title: {row['Job Title']}")
    
    if pd.notna(row.get('Company')):
        profile_parts.append(f"Company: {row['Company']}")
    
    if pd.notna(row.get('Areas of Expertise')):
        profile_parts.append(f"Areas of Expertise: {row['Areas of Expertise']}")
    
    if pd.notna(row.get('How I Can Help Others')):
        profile_parts.append(f"How I Can Help: {row['How I Can Help Others']}")
    
    if pd.notna(row.get('Areas of Interest')):
        profile_parts.append(f"Areas of Interest: {row['Areas of Interest']}")
    
    if pd.notna(row.get('How Others Can Help Me')):
        profile_parts.append(f"How Others Can Help Me: {row['How Others Can Help Me']}")
    
    if pd.notna(row.get('Recruitment')):
        profile_parts.append(f"Recruitment Info: {row['Recruitment']}")
    
    profile_text = "\n".join(profile_parts)
    
    if not profile_text.strip():
        return {
            "offerings": [],
            "requests": []
        }
    
    # Create prompt for extraction
    prompt = f"""You are analyzing an EA Global attendee's profile. EA Global brings together people working on the world's most pressing problems - AI safety, biosecurity, global health, animal welfare, effective policy, etc.

Your task: Extract DISTINCT, SPECIFIC offerings and requests that would enable high-quality professional connections.

PROFILE:
{profile_text}

EXTRACTION RULES:

OFFERINGS (Skills/expertise they can share):
✓ Include: Specific technical skills, domain expertise, mentorship, connections, resources
✓ Make self-contained: "AI safety research mentorship with 8+ years at leading labs" not just "mentorship"
✓ Preserve context: Experience level, domain specifics, unique qualifiers
✓ Preserve natural phrasing: Keep conversational language like "happy to chat about" or "can help with"
✓ Group related items: Combine "Python" + "ML engineering" → "ML engineering expertise in Python/PyTorch"
✗ Skip: Generic networking, vague "happy to chat", learning (that's a request)

REQUESTS (Needs/asks from others):
✓ Include: Specific expertise needs, collaboration asks, career advice, introductions
✓ Make self-contained: "Seeking connections with biosecurity policy experts in DC" not just "connections"
✓ Preserve specifics: Career stage, domain, geographic preferences, constraints
✓ Group related items: Combine multiple related asks into coherent requests
✗ Skip: Generic networking, vague "learning more", attending conference (implicit)

EXAMPLES OF GOOD EXTRACTIONS:

Profile: "ML engineer at Anthropic. 5 years in RLHF. Looking for cofounder."
✓ GOOD:
  offerings: ["RLHF and alignment engineering expertise from 5 years at Anthropic"]
  requests: ["Seeking technical cofounder for AI safety project"]
✗ BAD:
  offerings: ["ML", "engineering"]
  requests: ["cofounder", "networking"]

Profile: "Interested in global health. Just graduated. Want to learn about career paths."
✓ GOOD:
  offerings: []
  requests: ["Career guidance for recent graduate interested in global health careers"]
✗ BAD:
  offerings: ["enthusiasm", "recent graduate perspective"]
  requests: ["learning", "career advice"]

Profile: "Biosecurity researcher at Johns Hopkins. Can introduce people to policy folks. Looking for technical collaborators on detection systems."
✓ GOOD:
  offerings: ["Biosecurity research expertise from academic position", "Connections to biosecurity policy experts"]
  requests: ["Technical collaborators for pathogen detection system development"]

Profile: "Happy to chat about nonprofit operations. Ran ops at 3 orgs over 8 years. Want to meet other ops people."
✓ GOOD:
  offerings: ["Happy to chat about nonprofit operations, having run ops at 3 organizations over 8 years"]
  requests: ["Seeking connections with other nonprofit operations professionals"]

CRITICAL: If profile is sparse/generic with nothing substantive, return empty arrays rather than inventing generic items.

Return ONLY valid JSON (no markdown, no code blocks):
{{
  "offerings": ["offering 1", "offering 2", ...],
  "requests": ["request 1", "request 2", ...]
}}"""
    
    try:
        response = client.models.generate_content(
            model=LLM_MODEL,
            contents=prompt
        )
        
        result_text = response.text.strip()
        
        # Clean up any markdown code blocks if present
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
            result_text = result_text.strip()
        
        result = json.loads(result_text)
        
        return {
            "offerings": result.get("offerings", []),
            "requests": result.get("requests", [])
        }
    
    except Exception as e:
        print(f"Error extracting for {row.get('First Name')} {row.get('Last Name')}: {e}")
        return {
            "offerings": [],
            "requests": []
        }


def process_all_attendees(df: pd.DataFrame, force_refresh: bool = False) -> List[Dict]:
    """
    Extract offerings and requests for all attendees
    """
    if os.path.exists(EXTRACTED_DATA_PATH) and not force_refresh:
        print(f"Loading extracted data from {EXTRACTED_DATA_PATH}")
        with open(EXTRACTED_DATA_PATH, 'r') as f:
            return json.load(f)
    
    print("Extracting offerings and requests from all attendees...")
    print("This will take a while (5000+ LLM calls)...")
    
    extracted_data = []
    
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Processing attendees"):
        extracted = extract_offerings_and_requests(row)
        
        attendee_data = {
            "id": idx,
            "first_name": row.get('First Name', ''),
            "last_name": row.get('Last Name', ''),
            "company": row.get('Company', ''),
            "job_title": row.get('Job Title', ''),
            "country": row.get('Country', ''),
            "linkedin": row.get('LinkedIn', ''),
            "swapcard": row.get('Swapcard', ''),
            "biography": row.get('Biography', ''),
            "offerings": extracted["offerings"],
            "requests": extracted["requests"]
        }
        
        extracted_data.append(attendee_data)
    
    # Save to JSON
    print(f"Saving extracted data to {EXTRACTED_DATA_PATH}")
    with open(EXTRACTED_DATA_PATH, 'w') as f:
        json.dump(extracted_data, f, indent=2)
    
    return extracted_data


def generate_embedding(text: str) -> List[float]:
    """
    Generate embedding for a text using Gemini embedding model
    Returns normalized embedding of specified dimension
    """
    try:
        result = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text,
            config={
                "output_dimensionality": EMBEDDING_DIM
            }
        )
        
        embedding = result.embeddings[0].values
        
        # Normalize the embedding (required for 1536 dimensions)
        embedding_array = np.array(embedding)
        normalized = embedding_array / np.linalg.norm(embedding_array)
        
        return normalized.tolist()
    
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None


def generate_all_embeddings(extracted_data: List[Dict], force_refresh: bool = False) -> Dict:
    """
    Generate embeddings for all offerings and requests
    """
    if os.path.exists(EMBEDDINGS_PATH) and not force_refresh:
        print(f"Loading embeddings from {EMBEDDINGS_PATH}")
        with open(EMBEDDINGS_PATH, 'r') as f:
            return json.load(f)
    
    print("Generating embeddings for all offerings and requests...")
    
    embeddings_data = {
        "offerings": [],  # List of {attendee_id, offering_text, embedding}
        "requests": []    # List of {attendee_id, request_text, embedding}
    }
    
    # Generate embeddings for offerings
    print("Generating embeddings for offerings...")
    for attendee in tqdm(extracted_data, desc="Offering embeddings"):
        for offering in attendee["offerings"]:
            embedding = generate_embedding(offering)
            if embedding:
                embeddings_data["offerings"].append({
                    "attendee_id": attendee["id"],
                    "text": offering,
                    "embedding": embedding
                })
    
    # Generate embeddings for requests
    print("Generating embeddings for requests...")
    for attendee in tqdm(extracted_data, desc="Request embeddings"):
        for request in attendee["requests"]:
            embedding = generate_embedding(request)
            if embedding:
                embeddings_data["requests"].append({
                    "attendee_id": attendee["id"],
                    "text": request,
                    "embedding": embedding
                })
    
    # Save to JSON
    print(f"Saving embeddings to {EMBEDDINGS_PATH}")
    with open(EMBEDDINGS_PATH, 'w') as f:
        json.dump(embeddings_data, f, indent=2)
    
    print(f"Generated {len(embeddings_data['offerings'])} offering embeddings")
    print(f"Generated {len(embeddings_data['requests'])} request embeddings")
    
    return embeddings_data


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors"""
    return np.dot(vec1, vec2)  # Already normalized, so dot product = cosine similarity


def find_top_matches(query_embedding: List[float], 
                     candidate_embeddings: List[Dict], 
                     top_k: int = 50,
                     exclude_attendee_id: Optional[int] = None) -> List[Tuple[Dict, float]]:
    """
    Find top K matches based on cosine similarity
    """
    matches = []
    
    for candidate in candidate_embeddings:
        # Skip if this is the same person
        if exclude_attendee_id is not None and candidate["attendee_id"] == exclude_attendee_id:
            continue
        
        similarity = cosine_similarity(query_embedding, candidate["embedding"])
        matches.append((candidate, similarity))
    
    # Sort by similarity (descending)
    matches.sort(key=lambda x: x[1], reverse=True)
    
    return matches[:top_k]


def rerank_with_llm(query_text: str, 
                    query_type: str,  # "request" or "offering"
                    matches: List[Tuple[Dict, float]], 
                    extracted_data: List[Dict],
                    top_k: int = 25) -> List[Dict]:
    """
    Use Gemini to re-rank and filter matches to top K
    """
    # Build context for LLM
    match_descriptions = []
    for idx, (match, score) in enumerate(matches):
        attendee = next((a for a in extracted_data if a["id"] == match["attendee_id"]), None)
        if not attendee:
            continue
        
        match_descriptions.append({
            "index": idx,
            "attendee_id": match["attendee_id"],
            "name": f"{attendee['first_name']} {attendee['last_name']}",
            "company": attendee["company"],
            "text": match["text"],
            "similarity_score": round(score, 3)
        })
    
    if query_type == "request":
        prompt = f"""You are matching EA Global attendees. Someone needs help with this:

REQUEST: "{query_text}"

Below are 50 potential helpers (ranked by semantic similarity). Your task: Select the BEST 25 matches using strict quality criteria.

EVALUATION CRITERIA:
1. **Direct Relevance** (most important): Does the offering directly address the request?
2. **Expertise Level**: Does experience/background match what's needed?
3. **Specificity**: Concrete capabilities vs vague offerings?
4. **Context Match**: Domain, career stage, geography (if relevant)?

MATCH QUALITY EXAMPLES:

Request: "Seeking AI safety research mentorship for PhD student"
✓ EXCELLENT: "AI safety research mentorship with 10 years at leading labs, specializing in mechanistic interpretability"
✓ GOOD: "Research mentorship in AI safety and alignment for graduate students"
✗ POOR: "General career mentorship" // Too vague
✗ POOR: "AI safety reading group facilitation" // Wrong type of help

Request: "Looking for technical cofounder with biosecurity background"
✓ EXCELLENT: "Available as technical cofounder, computational biology PhD with biosecurity experience"
✓ GOOD: "Computational biology expertise and interest in biosecurity entrepreneurship"
✗ POOR: "Software engineering skills" // Missing biosecurity
✗ POOR: "Connections in biosecurity field" // Wrong type of help (not cofounder)

Request: "Need advice on nonprofit operations for early-stage founder"
✓ EXCELLENT: "Happy to advise on nonprofit operations, having run ops at 3 organizations as founding team member"
✓ GOOD: "Nonprofit operations experience and happy to share lessons learned"
✗ POOR: "Nonprofit board experience" // Wrong angle (governance not ops)
✗ POOR: "General startup advice" // Missing nonprofit context

NOTE: EA Global offerings typically use collaborative language ("happy to discuss", "can help with"). Don't penalize natural, conversational phrasing - it's authentic to the community.

TASK:
- Remove matches that don't truly help (be strict!)
- Prioritize direct, specific, high-quality matches
- Consider both capability AND alignment
- Rank best → good → acceptable

CANDIDATES:
{json.dumps(match_descriptions, indent=2)}

Return ONLY a JSON array of indices for the top 25 matches, ranked best to worst:
[index1, index2, index3, ...]

No markdown, no explanation, just the array."""
    else:  # offering
        prompt = f"""You are matching EA Global attendees. Someone can provide this:

OFFERING: "{query_text}"

Below are 50 people who might need this (ranked by semantic similarity). Your task: Select the BEST 25 matches using strict quality criteria.

EVALUATION CRITERIA:
1. **Need Alignment** (most important): Does the request actually need this offering?
2. **Scope Match**: Is the offering's level/scope appropriate for the request?
3. **Context Match**: Domain, career stage, specifics align?
4. **Mutual Benefit**: Would this connection be valuable for both parties?

MATCH QUALITY EXAMPLES:

Offering: "AI safety research mentorship with 10 years experience at leading labs"
✓ EXCELLENT: "Seeking AI safety research mentorship as early-career researcher transitioning from ML"
✓ GOOD: "Looking for guidance on AI safety career paths for PhD student"
✗ POOR: "Want to learn about AI in general" // Too broad/vague
✗ POOR: "Seeking senior AI safety researcher for collaboration" // Wrong relationship (peer not mentee)

Offering: "Connections to biosecurity policy experts in DC"
✓ EXCELLENT: "Need introductions to biosecurity policy community in DC for new role"
✓ GOOD: "Seeking connections in biosecurity policy for career transition"
✗ POOR: "Interested in biosecurity" // Too vague, unclear need
✗ POOR: "Looking for technical collaborators in biosecurity" // Wrong type of connection

Offering: "Happy to advise on nonprofit operations from 8 years running ops at EA orgs"
✓ EXCELLENT: "Seeking operations mentorship for launching new EA nonprofit"
✓ GOOD: "Need advice on scaling operations for growing nonprofit"
✗ POOR: "Want to learn about EA community" // Too broad
✗ POOR: "Looking for nonprofit board members" // Wrong type of help

NOTE: EA Global offerings typically use collaborative language ("happy to discuss", "can help with"). This is authentic community style, not lack of expertise.

TASK:
- Remove requests this offering doesn't actually fulfill
- Prioritize clear needs that match offering strength
- Consider whether connection would be mutually valuable
- Rank best → good → acceptable

CANDIDATES:
{json.dumps(match_descriptions, indent=2)}

Return ONLY a JSON array of indices for the top 25 matches, ranked best to worst:
[index1, index2, index3, ...]

No markdown, no explanation, just the array."""
    
    try:
        response = client.models.generate_content(
            model=LLM_MODEL,
            contents=prompt
        )
        
        result_text = response.text.strip()
        
        # Clean up any markdown code blocks
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
            result_text = result_text.strip()
        
        top_indices = json.loads(result_text)
        
        # Build final results
        final_matches = []
        for idx in top_indices[:top_k]:
            if idx < len(match_descriptions):
                match_info = match_descriptions[idx]
                original_match = matches[idx]
                
                attendee = next((a for a in extracted_data if a["id"] == match_info["attendee_id"]), None)
                
                final_matches.append({
                    "name": match_info["name"],
                    "company": attendee.get("company", ""),
                    "job_title": attendee.get("job_title", ""),
                    "country": attendee.get("country", ""),
                    "text": match_info["text"],
                    "similarity_score": match_info["similarity_score"],
                    "linkedin": attendee.get("linkedin", ""),
                    "swapcard": attendee.get("swapcard", ""),
                    "biography": attendee.get("biography", "")
                })
        
        return final_matches
    
    except Exception as e:
        print(f"Error in LLM re-ranking: {e}")
        # Fallback: just return top 25 by similarity
        return [
            {
                "name": f"{next((a for a in extracted_data if a['id'] == match['attendee_id']), {}).get('first_name', '')} "
                        f"{next((a for a in extracted_data if a['id'] == match['attendee_id']), {}).get('last_name', '')}",
                "company": next((a for a in extracted_data if a['id'] == match['attendee_id']), {}).get("company", ""),
                "job_title": next((a for a in extracted_data if a['id'] == match['attendee_id']), {}).get("job_title", ""),
                "country": next((a for a in extracted_data if a['id'] == match['attendee_id']), {}).get("country", ""),
                "text": match["text"],
                "similarity_score": round(score, 3),
                "linkedin": next((a for a in extracted_data if a['id'] == match['attendee_id']), {}).get("linkedin", ""),
                "swapcard": next((a for a in extracted_data if a['id'] == match['attendee_id']), {}).get("swapcard", ""),
                "biography": next((a for a in extracted_data if a['id'] == match['attendee_id']), {}).get("biography", "")
            }
            for match, score in matches[:top_k]
        ]


def search_by_username(name: str, extracted_data: List[Dict], embeddings_data: Dict) -> Dict:
    """
    Search for an attendee by name and show both:
    1. Who can help them (their requests -> others' offerings)
    2. Who they can help (their offerings -> others' requests)
    """
    # Find the attendee
    name_lower = name.lower()
    attendee = None
    
    for a in extracted_data:
        full_name = f"{a['first_name']} {a['last_name']}".lower()
        if name_lower in full_name:
            attendee = a
            break
    
    if not attendee:
        return {"error": f"No attendee found matching '{name}'"}
    
    results = {
        "attendee": {
            "name": f"{attendee['first_name']} {attendee['last_name']}",
            "company": attendee.get("company", ""),
            "job_title": attendee.get("job_title", ""),
            "country": attendee.get("country", "")
        },
        "people_who_can_help_you": [],  # Your requests -> their offerings
        "people_you_can_help": []       # Your offerings -> their requests
    }
    
    print(f"\nFound: {results['attendee']['name']}")
    print(f"Offerings: {len(attendee['offerings'])}")
    print(f"Requests: {len(attendee['requests'])}")
    
    # For each request, find matching offerings
    print("\n=== Finding people who can help you ===")
    for request in attendee["requests"]:
        print(f"Processing request: {request[:80]}...")
        
        # Generate synthetic offering from request
        synthetic_prompt = f"""You are transforming a REQUEST into a synthetic OFFERING for EA Global attendee matching. The synthetic offering must match the writing style of real EA Global attendee offers for optimal semantic matching.

ORIGINAL REQUEST: "{request}"

TRANSFORMATION RULES:

1. **Match the EA Offer Style:**
   - First-person perspective ("I can...", "Happy to...", "I'm happy to...")
   - Collaborative, purpose-driven tone
   - Action-oriented verbs: "happy to discuss", "can offer advice on", "can help with", "sharing my experience in"
   - Add credibility context when present in request (experience level, domain specifics)

2. **Preserve All Specifics:**
   - Domain expertise, experience level, location, constraints
   - Career stage, technical details, geographic context
   - Any qualifiers from the original request

3. **Use Conditional Framing When Appropriate:**
   - "If you're considering X, I can share my experience"
   - "For folks working on Y, I'm happy to discuss"

EXAMPLES:

Request: "Seeking technical cofounder with AI safety background for startup in San Francisco"
→ "I'm a technical person with an AI safety background, happy to discuss cofounder opportunities for startups in the San Francisco area."

Request: "Looking for mentorship on transitioning from software engineering to AI safety research"
→ "Having transitioned from software engineering to AI safety research, I'm happy to mentor folks making a similar career shift. I can share insights on research directions, necessary skills, and making connections in the field."

Request: "Need connections to biosecurity policy experts in DC area"
→ "I can connect you with biosecurity policy experts in the DC area."

Request: "Seeking advice on career paths in animal welfare for recent graduates"
→ "I'm happy to discuss career paths in animal welfare for recent graduates. I can share my perspective on different organizations, skill-building, and early-career opportunities."

Request: "Looking for feedback on AI governance research agenda"
→ "I can offer feedback on AI governance research agendas. Happy to discuss research directions, framing, and connection to policy priorities."

Request: "Need introductions to people working on global health interventions in South Asia"
→ "I can provide introductions to people working on global health interventions in South Asia."

CRITICAL: Output should sound like a natural EA Global attendee offering, not a robotic flip of the request. Match the collaborative, first-person style of the examples above.

Return ONLY the synthetic offering text (1-3 sentences), nothing else."""
        
        try:
            response = client.models.generate_content(
                model=LLM_MODEL,
                contents=synthetic_prompt
            )
            synthetic_offering = response.text.strip()
            
            # Generate embedding for synthetic offering
            query_embedding = generate_embedding(synthetic_offering)
            
            if query_embedding:
                # Find top 50 matches
                top_matches = find_top_matches(
                    query_embedding,
                    embeddings_data["offerings"],
                    top_k=50,
                    exclude_attendee_id=attendee["id"]
                )
                
                # Re-rank with LLM to top 25
                final_matches = rerank_with_llm(
                    request,
                    "request",
                    top_matches,
                    extracted_data,
                    top_k=25
                )
                
                results["people_who_can_help_you"].append({
                    "your_request": request,
                    "matches": final_matches
                })
        
        except Exception as e:
            print(f"Error processing request: {e}")
    
    # For each offering, find matching requests
    print("\n=== Finding people you can help ===")
    for offering in attendee["offerings"]:
        print(f"Processing offering: {offering[:80]}...")
        
        # Generate embedding for offering
        query_embedding = generate_embedding(offering)
        
        if query_embedding:
            # Find top 50 matches
            top_matches = find_top_matches(
                query_embedding,
                embeddings_data["requests"],
                top_k=50,
                exclude_attendee_id=attendee["id"]
            )
            
            # Re-rank with LLM to top 25
            final_matches = rerank_with_llm(
                offering,
                "offering",
                top_matches,
                extracted_data,
                top_k=25
            )
            
            results["people_you_can_help"].append({
                "your_offering": offering,
                "matches": final_matches
            })
    
    return results


def search_by_custom_request(request: str, extracted_data: List[Dict], embeddings_data: Dict) -> List[Dict]:
    """
    Search for people who can fulfill a custom request
    """
    print(f"Searching for offerings matching: {request}")
    
    # Generate synthetic offering from request
    synthetic_prompt = f"""You are transforming a REQUEST into a synthetic OFFERING for EA Global attendee matching. The synthetic offering must match the writing style of real EA Global attendee offers for optimal semantic matching.

ORIGINAL REQUEST: "{request}"

TRANSFORMATION RULES:

1. **Match the EA Offer Style:**
   - First-person perspective ("I can...", "Happy to...", "I'm happy to...")
   - Collaborative, purpose-driven tone
   - Action-oriented verbs: "happy to discuss", "can offer advice on", "can help with", "sharing my experience in"
   - Add credibility context when present in request (experience level, domain specifics)

2. **Preserve All Specifics:**
   - Domain expertise, experience level, location, constraints
   - Career stage, technical details, geographic context
   - Any qualifiers from the original request

3. **Use Conditional Framing When Appropriate:**
   - "If you're considering X, I can share my experience"
   - "For folks working on Y, I'm happy to discuss"

EXAMPLES:

Request: "Seeking technical cofounder with AI safety background for startup in San Francisco"
→ "I'm a technical person with an AI safety background, happy to discuss cofounder opportunities for startups in the San Francisco area."

Request: "Looking for mentorship on transitioning from software engineering to AI safety research"
→ "Having transitioned from software engineering to AI safety research, I'm happy to mentor folks making a similar career shift. I can share insights on research directions, necessary skills, and making connections in the field."

Request: "Need connections to biosecurity policy experts in DC area"
→ "I can connect you with biosecurity policy experts in the DC area."

Request: "Seeking advice on career paths in animal welfare for recent graduates"
→ "I'm happy to discuss career paths in animal welfare for recent graduates. I can share my perspective on different organizations, skill-building, and early-career opportunities."

Request: "Looking for feedback on AI governance research agenda"
→ "I can offer feedback on AI governance research agendas. Happy to discuss research directions, framing, and connection to policy priorities."

Request: "Need introductions to people working on global health interventions in South Asia"
→ "I can provide introductions to people working on global health interventions in South Asia."

CRITICAL: Output should sound like a natural EA Global attendee offering, not a robotic flip of the request. Match the collaborative, first-person style of the examples above.

Return ONLY the synthetic offering text (1-3 sentences), nothing else."""
    
    response = client.models.generate_content(
        model=LLM_MODEL,
        contents=synthetic_prompt
    )
    synthetic_offering = response.text.strip()
    
    print(f"Synthetic offering: {synthetic_offering}")
    
    # Generate embedding
    query_embedding = generate_embedding(synthetic_offering)
    
    # Find top 50 matches
    top_matches = find_top_matches(
        query_embedding,
        embeddings_data["offerings"],
        top_k=50
    )
    
    # Re-rank with LLM to top 25
    final_matches = rerank_with_llm(
        request,
        "request",
        top_matches,
        extracted_data,
        top_k=25
    )
    
    return final_matches


def search_by_custom_offering(offering: str, extracted_data: List[Dict], embeddings_data: Dict) -> List[Dict]:
    """
    Search for people who need a custom offering
    """
    print(f"Searching for requests matching: {offering}")
    
    # Generate embedding
    query_embedding = generate_embedding(offering)
    
    # Find top 50 matches
    top_matches = find_top_matches(
        query_embedding,
        embeddings_data["requests"],
        top_k=50
    )
    
    # Re-rank with LLM to top 25
    final_matches = rerank_with_llm(
        offering,
        "offering",
        top_matches,
        extracted_data,
        top_k=25
    )
    
    return final_matches


def display_matches(matches: List[Dict], title: str):
    """Display matches in a formatted way"""
    print(f"\n{'='*80}")
    print(f"{title}")
    print(f"{'='*80}\n")
    
    for idx, match in enumerate(matches, 1):
        print(f"{idx}. {match['name']}")
        if match.get('company'):
            print(f"   Company: {match['company']}")
        if match.get('job_title'):
            print(f"   Title: {match['job_title']}")
        if match.get('country'):
            print(f"   Country: {match['country']}")
        print(f"   Match: {match['text']}")
        print(f"   Score: {match['similarity_score']}")
        if match.get('linkedin'):
            print(f"   LinkedIn: {match['linkedin']}")
        print()


def interactive_search(extracted_data: List[Dict], embeddings_data: Dict):
    """
    Interactive CLI for searching matches
    """
    while True:
        print("\n" + "="*80)
        print("EA GLOBAL ATTENDEE MATCHING")
        print("="*80)
        print("\n1. Search by username (see who can help you + who you can help)")
        print("2. Enter a custom request (find people who can help)")
        print("3. Enter a custom offering (find people you can help)")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == "1":
            name = input("\nEnter attendee name (first or last): ").strip()
            results = search_by_username(name, extracted_data, embeddings_data)
            
            if "error" in results:
                print(f"\n{results['error']}")
                continue
            
            print(f"\n{'='*80}")
            print(f"RESULTS FOR: {results['attendee']['name']}")
            print(f"{'='*80}")
            
            # Display people who can help you
            print("\n" + "="*80)
            print("PEOPLE WHO CAN HELP YOU")
            print("="*80)
            
            for item in results["people_who_can_help_you"]:
                print(f"\nYour Request: {item['your_request']}")
                display_matches(item['matches'][:10], "Top 10 Matches")  # Show top 10 for brevity
            
            # Display people you can help
            print("\n" + "="*80)
            print("PEOPLE YOU CAN HELP")
            print("="*80)
            
            for item in results["people_you_can_help"]:
                print(f"\nYour Offering: {item['your_offering']}")
                display_matches(item['matches'][:10], "Top 10 Matches")  # Show top 10 for brevity
        
        elif choice == "2":
            request = input("\nEnter your request: ").strip()
            matches = search_by_custom_request(request, extracted_data, embeddings_data)
            display_matches(matches, f"People Who Can Help With: {request}")
        
        elif choice == "3":
            offering = input("\nEnter your offering: ").strip()
            matches = search_by_custom_offering(offering, extracted_data, embeddings_data)
            display_matches(matches, f"People Who Need: {offering}")
        
        elif choice == "4":
            print("\nGoodbye!")
            break
        
        else:
            print("\nInvalid choice. Please enter 1-4.")


def main():
    """Main execution flow"""
    print("="*80)
    print("EA GLOBAL ATTENDEE MATCHING SYSTEM")
    print("="*80)
    
    # Step 1: Load CSV
    df = load_csv()
    
    # Step 2: Extract offerings and requests
    print("\nStep 1: Extracting offerings and requests...")
    extracted_data = process_all_attendees(df, force_refresh=False)
    
    # Step 3: Generate embeddings
    print("\nStep 2: Generating embeddings...")
    embeddings_data = generate_all_embeddings(extracted_data, force_refresh=False)
    
    # Step 4: Interactive search
    print("\nStep 3: Ready for searching!")
    interactive_search(extracted_data, embeddings_data)


if __name__ == "__main__":
    main()
