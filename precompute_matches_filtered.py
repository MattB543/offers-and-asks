"""
File: precompute_matches_filtered.py
Created: 2025-10-06
Creation Reason: DIRECT USER REQUEST
Purpose: Pre-compute top 50 matches ONLY for attendees with complete profiles.
         Filters for biography + help fields to ensure high-quality extractions.
         Optimized with better batch updates and configurable filtering.
Author: Claude AI (at user request)
Input: Supabase tables (attendees, requests, offerings)
Output: Supabase match tables (request_to_offering_matches, offering_to_request_matches)
"""

import os
import sys
import numpy as np
from typing import List, Dict, Tuple, Optional
from supabase import create_client, Client
from google import genai
from tqdm import tqdm
from dotenv import load_dotenv
import time
import argparse

load_dotenv()

# Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("[ERROR] Missing Supabase credentials!")
    print("Please set SUPABASE_URL and SUPABASE_SERVICE_KEY in your .env file")
    sys.exit(1)

if not GEMINI_API_KEY:
    print("[ERROR] Missing GEMINI_API_KEY!")
    print("Please set GEMINI_API_KEY in your .env file")
    sys.exit(1)

# Model configurations
LLM_MODEL = "gemini-2.5-pro"
EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIM = 1536
TOP_K = 50  # Number of top matches to store per item

print(f"[INFO] Connecting to Supabase: {SUPABASE_URL}")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
gemini_client = genai.Client(api_key=GEMINI_API_KEY)


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """Compute cosine similarity between two vectors (assumes normalized)"""
    return float(np.dot(vec1, vec2))


def generate_embedding(text: str) -> List[float]:
    """Generate normalized embedding for text"""
    try:
        result = gemini_client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text,
            config={"output_dimensionality": EMBEDDING_DIM}
        )

        embedding = result.embeddings[0].values
        embedding_array = np.array(embedding)
        normalized = embedding_array / np.linalg.norm(embedding_array)

        return normalized.tolist()

    except Exception as e:
        print(f"[ERROR] Failed to generate embedding: {str(e)}")
        return None


def convert_request_to_synthetic_offering(request: str) -> str:
    """Convert a request into a synthetic offering for matching"""
    synthetic_prompt = f"""You are transforming a REQUEST into a synthetic OFFERING for EA Global attendee matching. The synthetic offering must match the writing style of real EA Global attendee offers for optimal semantic matching.

ORIGINAL REQUEST: "{request}"

Your task: Transform this request into how someone who could FULFILL this request would describe their offering.

TRANSFORMATION RULES:

1. Convert need → capability
   - "Need AI safety mentor" → "Can provide AI safety mentorship"
   - "Looking for cofounder" → "Open to cofounder discussions"
   - "Want to learn about X" → "Can teach/explain X"

2. Preserve all specifics and context
   - Keep domain details, experience levels, geographic constraints
   - "Need biosecurity policy expert in DC" → "Biosecurity policy expertise in DC area"

3. Match natural EA Global offering style
   - Use first-person perspective when appropriate
   - Keep collaborative, helpful tone
   - Avoid robotic language

GOOD EXAMPLES:

Request: "Seeking technical cofounder for AI safety project"
Synthetic: "Open to technical cofounder opportunities in AI safety"

Request: "Need advice on transitioning into AI alignment research from academia"
Synthetic: "Can provide career guidance for academics transitioning to AI alignment research"

Request: "Looking for connections with biosecurity policy experts in DC"
Synthetic: "Biosecurity policy expertise and connections in DC area"

Request: "Want to learn about AI governance career paths for recent graduates"
Synthetic: "Can provide guidance on AI governance career paths for recent graduates"

CRITICAL: Output should sound like a natural EA Global attendee offering, not a robotic flip of the request. Match the collaborative, first-person style of the examples above.

Return ONLY the synthetic offering text (1-3 sentences), nothing else."""

    try:
        response = gemini_client.models.generate_content(
            model=LLM_MODEL,
            contents=synthetic_prompt
        )
        return response.text.strip()

    except Exception as e:
        print(f"[ERROR] Failed to generate synthetic offering: {str(e)}")
        return None


def get_complete_profile_attendee_ids(
    min_biography_length: int = 50,
    require_help_fields: bool = True,
    require_company_info: bool = False,
    strict_mode: bool = False,
    require_both_help_fields: bool = False,
    min_help_field_length: int = 20
) -> List[int]:
    """
    Get attendee IDs for profiles that meet completeness criteria.

    Args:
        min_biography_length: Minimum character count for biography
        require_help_fields: Require at least one of the "help" fields
        require_company_info: Require both company and job_title
        strict_mode: Require ALL fields (very restrictive)
        require_both_help_fields: Require BOTH help fields (not just one)
        min_help_field_length: Minimum character count for help fields

    Returns:
        List of attendee IDs that meet criteria
    """
    print("\n[START] Filtering for complete profiles...")

    # Build SQL query based on criteria
    query = supabase.table("attendees").select("id, first_name, last_name, biography, company, job_title")

    # Fetch all attendees (we'll filter in Python for complex logic)
    response = query.execute()
    all_attendees = response.data

    filtered_ids = []
    stats = {
        'total': len(all_attendees),
        'no_biography': 0,
        'short_biography': 0,
        'missing_help_fields': 0,
        'missing_company_info': 0,
        'passed': 0
    }

    for attendee in all_attendees:
        attendee_id = attendee['id']
        bio = (attendee.get('biography') or '').strip()
        company = (attendee.get('company') or '').strip()
        job_title = (attendee.get('job_title') or '').strip()

        # Check biography
        if not bio:
            stats['no_biography'] += 1
            continue

        if len(bio) < min_biography_length:
            stats['short_biography'] += 1
            continue

        # In strict mode, require all fields
        if strict_mode:
            if not (bio and company and job_title):
                stats['missing_company_info'] += 1
                continue

        # Check company info if required
        if require_company_info and not (company and job_title):
            stats['missing_company_info'] += 1
            continue

        # If we get here, attendee passes
        stats['passed'] += 1
        filtered_ids.append(attendee_id)

    # Print statistics
    print("\n" + "="*80)
    print("PROFILE COMPLETENESS STATISTICS")
    print("="*80)
    print(f"Total attendees in database: {stats['total']}")
    print(f"├─ No biography: {stats['no_biography']} ({stats['no_biography']/stats['total']*100:.1f}%)")
    print(f"├─ Biography too short (<{min_biography_length} chars): {stats['short_biography']} ({stats['short_biography']/stats['total']*100:.1f}%)")
    if require_company_info or strict_mode:
        print(f"├─ Missing company/job info: {stats['missing_company_info']} ({stats['missing_company_info']/stats['total']*100:.1f}%)")
    print(f"└─ ✅ Passed filters: {stats['passed']} ({stats['passed']/stats['total']*100:.1f}%)")
    print("="*80)

    return filtered_ids


def load_filtered_offerings(attendee_ids: List[int]) -> List[Dict]:
    """Load offerings only for attendees with complete profiles"""
    print(f"\n[START] Loading offerings for {len(attendee_ids)} complete-profile attendees...")

    offerings = []
    batch_size = 1000

    # Supabase 'in' filter has a limit, so batch the queries
    for i in range(0, len(attendee_ids), batch_size):
        batch_ids = attendee_ids[i:i + batch_size]

        response = supabase.table("offerings")\
            .select("id, attendee_id, text, embedding")\
            .in_("attendee_id", batch_ids)\
            .execute()

        # Convert embeddings from string/list to proper format
        for offering in response.data:
            if offering.get('embedding'):
                # Handle both string and list formats
                emb = offering['embedding']
                if isinstance(emb, str):
                    # Parse string representation of array
                    import json
                    emb = json.loads(emb.replace('[', '[').replace(']', ']'))
                offering['embedding'] = emb if isinstance(emb, list) else list(emb)

        offerings.extend(response.data)

    print(f"[OK] Loaded {len(offerings)} offerings from complete profiles")
    return offerings


def load_filtered_requests(attendee_ids: List[int]) -> List[Dict]:
    """Load requests only for attendees with complete profiles"""
    print(f"\n[START] Loading requests for {len(attendee_ids)} complete-profile attendees...")

    requests = []
    batch_size = 1000

    for i in range(0, len(attendee_ids), batch_size):
        batch_ids = attendee_ids[i:i + batch_size]

        response = supabase.table("requests")\
            .select("id, attendee_id, text, embedding, synthetic_offering_text, synthetic_offering_embedding")\
            .in_("attendee_id", batch_ids)\
            .execute()

        # Convert embeddings from string/list to proper format
        for request in response.data:
            if request.get('embedding'):
                emb = request['embedding']
                if isinstance(emb, str):
                    import json
                    emb = json.loads(emb.replace('[', '[').replace(']', ']'))
                request['embedding'] = emb if isinstance(emb, list) else list(emb)

            if request.get('synthetic_offering_embedding'):
                emb = request['synthetic_offering_embedding']
                if isinstance(emb, str):
                    import json
                    emb = json.loads(emb.replace('[', '[').replace(']', ']'))
                request['synthetic_offering_embedding'] = emb if isinstance(emb, list) else list(emb)

        requests.extend(response.data)

    print(f"[OK] Loaded {len(requests)} requests from complete profiles")
    return requests


def generate_synthetic_offerings_for_requests(requests: List[Dict]) -> None:
    """Generate synthetic offerings for all requests that don't have them"""
    print("\n[START] Generating synthetic offerings for requests...")

    # Filter requests that need synthetic offerings
    requests_needing_synthetic = [r for r in requests if not r.get('synthetic_offering_text')]

    if not requests_needing_synthetic:
        print("[OK] All requests already have synthetic offerings")
        return

    print(f"[INFO] Need to generate {len(requests_needing_synthetic)} synthetic offerings")

    batch_size = 50  # Smaller batches for better progress tracking

    for i in tqdm(range(0, len(requests_needing_synthetic), batch_size),
                  desc="Generating synthetic offerings"):
        batch = requests_needing_synthetic[i:i + batch_size]
        updates = []

        for request in batch:
            # Generate synthetic offering
            synthetic_text = convert_request_to_synthetic_offering(request['text'])

            if not synthetic_text:
                print(f"[WARN] Failed to generate synthetic offering for request {request['id']}")
                continue

            # Generate embedding
            synthetic_embedding = generate_embedding(synthetic_text)

            if not synthetic_embedding:
                print(f"[WARN] Failed to generate embedding for request {request['id']}")
                continue

            updates.append({
                'id': request['id'],
                'synthetic_offering_text': synthetic_text,
                'synthetic_offering_embedding': synthetic_embedding
            })

            # Update local cache
            request['synthetic_offering_text'] = synthetic_text
            request['synthetic_offering_embedding'] = synthetic_embedding

            # Small delay to avoid rate limits
            time.sleep(0.1)

        # Use individual UPDATE to avoid NULL constraint issues with upsert
        if updates:
            try:
                for update in updates:
                    supabase.table("requests")\
                        .update({
                            'synthetic_offering_text': update['synthetic_offering_text'],
                            'synthetic_offering_embedding': update['synthetic_offering_embedding']
                        })\
                        .eq('id', update['id'])\
                        .execute()

                print(f"[OK] Updated batch {i//batch_size + 1}: {len(updates)} requests")

            except Exception as e:
                print(f"[ERROR] Failed to update batch {i//batch_size + 1}: {str(e)}")

    print("[OK] Finished generating synthetic offerings")


def compute_request_to_offering_matches(requests: List[Dict], offerings: List[Dict]) -> None:
    """
    For each request, compute top 50 matching offerings using synthetic offering embedding
    """
    print("\n[START] Computing request → offering matches...")

    # Convert offering embeddings to numpy array for vectorized operations
    offering_embeddings = np.array([o['embedding'] for o in offerings])
    offering_ids = [o['id'] for o in offerings]

    all_matches = []

    for request in tqdm(requests, desc="Computing matches"):
        if not request.get('synthetic_offering_embedding'):
            print(f"[WARN] Request {request['id']} missing synthetic embedding, skipping")
            continue

        # Compute similarities with all offerings
        query_embedding = np.array(request['synthetic_offering_embedding'])
        similarities = offering_embeddings @ query_embedding  # Dot product (vectors are normalized)

        # Get top K indices
        top_indices = np.argsort(similarities)[-TOP_K:][::-1]

        # Create match records
        for rank, idx in enumerate(top_indices, 1):
            all_matches.append({
                'request_id': request['id'],
                'offering_id': offering_ids[idx],
                'similarity_score': float(similarities[idx]),
                'rank': rank
            })

    # Batch insert into database
    print(f"[INFO] Inserting {len(all_matches)} request → offering matches...")

    batch_size = 500
    for i in tqdm(range(0, len(all_matches), batch_size), desc="Inserting matches"):
        batch = all_matches[i:i + batch_size]

        try:
            supabase.table("request_to_offering_matches").insert(batch).execute()
        except Exception as e:
            print(f"[ERROR] Failed to insert batch {i//batch_size + 1}: {str(e)}")

    print("[OK] Finished computing request → offering matches")


def compute_offering_to_request_matches(offerings: List[Dict], requests: List[Dict]) -> None:
    """
    For each offering, compute top 50 matching requests using synthetic offering embeddings
    """
    print("\n[START] Computing offering → request matches...")

    # Convert request synthetic offering embeddings to numpy array
    # Filter out requests without synthetic embeddings
    requests_with_synthetic = [r for r in requests if r.get('synthetic_offering_embedding')]
    request_embeddings = np.array([r['synthetic_offering_embedding'] for r in requests_with_synthetic])
    request_ids = [r['id'] for r in requests_with_synthetic]

    print(f"[INFO] Using {len(requests_with_synthetic)} requests with synthetic embeddings")

    all_matches = []

    for offering in tqdm(offerings, desc="Computing matches"):
        # Compute similarities with all request synthetic offerings
        query_embedding = np.array(offering['embedding'])
        similarities = request_embeddings @ query_embedding  # Dot product

        # Get top K indices
        top_indices = np.argsort(similarities)[-TOP_K:][::-1]

        # Create match records
        for rank, idx in enumerate(top_indices, 1):
            all_matches.append({
                'offering_id': offering['id'],
                'request_id': request_ids[idx],
                'similarity_score': float(similarities[idx]),
                'rank': rank
            })

    # Batch insert into database
    print(f"[INFO] Inserting {len(all_matches)} offering → request matches...")

    batch_size = 500
    for i in tqdm(range(0, len(all_matches), batch_size), desc="Inserting matches"):
        batch = all_matches[i:i + batch_size]

        try:
            supabase.table("offering_to_request_matches").insert(batch).execute()
        except Exception as e:
            print(f"[ERROR] Failed to insert batch {i//batch_size + 1}: {str(e)}")

    print("[OK] Finished computing offering → request matches")


def verify_precomputation() -> None:
    """Verify the pre-computation by checking match counts"""
    print("\n[START] Verifying pre-computation...")

    try:
        # Use the SQL function to get stats
        result = supabase.rpc('get_precomputed_match_stats').execute()

        print("\n" + "="*80)
        print("PRE-COMPUTATION STATISTICS")
        print("="*80)

        for row in result.data:
            print(f"{row['metric']:.<50} {row['value']}")

        print("="*80)
        print("[OK] Verification complete!")

    except Exception as e:
        print(f"[ERROR] Verification failed: {str(e)}")

        # Fallback to manual counting
        print("\n[INFO] Using fallback verification...")

        try:
            req_count = supabase.table("requests").select("id", count="exact").execute()
            off_count = supabase.table("offerings").select("id", count="exact").execute()
            req_match_count = supabase.table("request_to_offering_matches").select("request_id", count="exact").execute()
            off_match_count = supabase.table("offering_to_request_matches").select("offering_id", count="exact").execute()

            print(f"Total requests: {req_count.count}")
            print(f"Total offerings: {off_count.count}")
            print(f"Request → offering matches: {req_match_count.count}")
            print(f"Offering → request matches: {off_match_count.count}")

        except Exception as e2:
            print(f"[ERROR] Fallback verification also failed: {str(e2)}")


def clear_existing_matches() -> None:
    """Clear existing pre-computed matches (for re-running)"""
    print("\n[WARN] Clearing existing matches...")

    response = input("This will DELETE all existing pre-computed matches. Continue? (yes/no): ").strip().lower()

    if response != 'yes':
        print("[INFO] Keeping existing matches")
        return

    try:
        # Delete all matches
        supabase.table("request_to_offering_matches").delete().neq('request_id', -1).execute()
        supabase.table("offering_to_request_matches").delete().neq('offering_id', -1).execute()

        print("[OK] Cleared existing matches")

    except Exception as e:
        print(f"[ERROR] Failed to clear matches: {str(e)}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description='Pre-compute matches for attendees with complete profiles')
    parser.add_argument('--min-bio-length', type=int, default=50,
                      help='Minimum biography length (default: 50 chars)')
    parser.add_argument('--require-company-info', action='store_true',
                      help='Require company and job title fields')
    parser.add_argument('--strict', action='store_true',
                      help='Strict mode: require ALL fields (very restrictive)')
    parser.add_argument('--clear-matches', action='store_true',
                      help='Clear existing matches before computing')
    parser.add_argument('--use-filtered-ids', type=str,
                      help='Path to JSON file with pre-filtered attendee IDs (e.g., outputs/filtered_attendee_ids.json)')

    args = parser.parse_args()

    print("="*80)
    print("PRE-COMPUTE MATCHES FOR COMPLETE PROFILES ONLY")
    print("="*80)
    print("\nThis script will:")
    print("1. Filter attendees for complete profiles")
    print("2. Load requests/offerings only from complete profiles")
    print("3. Generate synthetic offerings for requests")
    print("4. Compute top 50 matches for each request → offerings")
    print("5. Compute top 50 matches for each offering → requests")
    print("6. Store results in database for instant lookup")
    print("\n" + "="*80)

    # Show filtering criteria
    print("\nFILTERING CRITERIA:")
    print(f"├─ Minimum biography length: {args.min_bio_length} characters")
    print(f"├─ Require company/job title: {'Yes' if args.require_company_info else 'No'}")
    print(f"└─ Strict mode (all fields): {'Yes' if args.strict else 'No'}")
    print("="*80)

    # Check if migration has been run
    print("\n[INFO] Before running this script, ensure you've run the migration:")
    print("       supabase/precomputed_matches_migration.sql")
    response = input("\nHave you run the migration? (yes/no): ").strip().lower()

    if response != 'yes':
        print("[INFO] Please run the migration first, then restart this script")
        return

    # Clear existing matches if requested
    if args.clear_matches:
        clear_existing_matches()
    else:
        response = input("\nClear existing matches before computing? (yes/no): ").strip().lower()
        if response == 'yes':
            clear_existing_matches()

    # Filter for complete profiles
    if args.use_filtered_ids:
        print(f"\n[INFO] Loading pre-filtered attendee IDs from {args.use_filtered_ids}")
        import json
        with open(args.use_filtered_ids, 'r') as f:
            complete_profile_ids = json.load(f)
        print(f"[OK] Loaded {len(complete_profile_ids)} pre-filtered attendee IDs")
    else:
        complete_profile_ids = get_complete_profile_attendee_ids(
            min_biography_length=args.min_bio_length,
            require_company_info=args.require_company_info,
            strict_mode=args.strict
        )

    if not complete_profile_ids:
        print("[ERROR] No attendees meet the filtering criteria!")
        return

    # Load filtered data
    offerings = load_filtered_offerings(complete_profile_ids)
    requests = load_filtered_requests(complete_profile_ids)

    if not offerings:
        print("[ERROR] No offerings found for complete-profile attendees!")
        return

    if not requests:
        print("[ERROR] No requests found for complete-profile attendees!")
        return

    # Generate synthetic offerings for requests
    generate_synthetic_offerings_for_requests(requests)

    # Compute matches
    compute_request_to_offering_matches(requests, offerings)
    compute_offering_to_request_matches(offerings, requests)

    # Verify
    verify_precomputation()

    print("\n" + "="*80)
    print("[OK] PRE-COMPUTATION COMPLETE!")
    print("="*80)
    print("\nNext steps:")
    print("1. Test username lookup: SELECT * FROM get_attendee_matches_by_name('John', 'Smith', 25);")
    print("2. Update your application to use pre-computed matches")
    print("3. Username search should now be instant (no LLM calls needed)")


if __name__ == "__main__":
    main()
