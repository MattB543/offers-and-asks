"""
File: test_cli_search.py
Created: 2025-10-05
Creation Reason: DIRECT USER REQUEST
Purpose: Test the CLI search functionality using the 25-sample processed data
         to validate matching algorithm before full dataset processing.
Author: Claude AI (at user request)
Input: outputs/extracted_data/, outputs/embeddings/
Output: Console output + outputs/results/
"""

import os
import json
import numpy as np
from typing import List, Dict
from google import genai
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("[ERROR] GEMINI_API_KEY environment variable not set")

client = genai.Client(api_key=GEMINI_API_KEY)

# Paths - automatically find most recent files
def get_most_recent_file(directory: str, pattern: str = None) -> str:
    """Get the most recently created file in a directory"""
    if not os.path.exists(directory):
        raise FileNotFoundError(f"[ERROR] Directory not found: {directory}")

    files = [f for f in os.listdir(directory) if f.endswith('.json')]
    if pattern:
        files = [f for f in files if pattern in f]

    if not files:
        raise FileNotFoundError(f"[ERROR] No JSON files found in {directory}")

    files_with_time = [(f, os.path.getctime(os.path.join(directory, f))) for f in files]
    most_recent = max(files_with_time, key=lambda x: x[1])
    return os.path.join(directory, most_recent[0])

EXTRACTED_DATA_FILE = get_most_recent_file("outputs/extracted_data")
EMBEDDINGS_FILE = get_most_recent_file("outputs/embeddings")
RESULTS_DIR = "outputs/results"

os.makedirs(RESULTS_DIR, exist_ok=True)

print(f"[INFO] Using extracted data: {EXTRACTED_DATA_FILE}")
print(f"[INFO] Using embeddings: {EMBEDDINGS_FILE}")

print("="*80)
print("CLI SEARCH TEST - 25 Sample Dataset")
print("="*80)

# Load data
print("\n[START] Loading processed data...")
with open(EXTRACTED_DATA_FILE, 'r', encoding='utf-8') as f:
    extracted_data = json.load(f)
print(f"[OK] Loaded {len(extracted_data)} attendees")

with open(EMBEDDINGS_FILE, 'r', encoding='utf-8') as f:
    embeddings_data = json.load(f)
print(f"[OK] Loaded {len(embeddings_data['offerings'])} offering embeddings")
print(f"[OK] Loaded {len(embeddings_data['requests'])} request embeddings")


def generate_embedding(text: str) -> List[float]:
    """Generate normalized embedding for text"""
    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text,
        config={"output_dimensionality": 1536}
    )
    embedding = result.embeddings[0].values
    embedding_array = np.array(embedding)
    normalized = embedding_array / np.linalg.norm(embedding_array)
    return normalized.tolist()


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity"""
    return np.dot(vec1, vec2)


def find_top_matches(query_embedding: List[float], candidates: List[Dict], top_k: int = 10) -> List[tuple]:
    """Find top K matches by cosine similarity"""
    matches = []
    for candidate in candidates:
        similarity = cosine_similarity(query_embedding, candidate["embedding"])
        matches.append((candidate, similarity))

    matches.sort(key=lambda x: x[1], reverse=True)
    return matches[:top_k]


def display_matches(matches: List[tuple], title: str, interactive: bool = True):
    """Display matches in formatted way with option to view full details"""
    print("\n" + "="*80)
    print(f"{title}")
    print("="*80)

    enriched_matches = []
    for idx, (match, score) in enumerate(matches, 1):
        # Find attendee info and enrich the match with full profile
        attendee = next((a for a in extracted_data if a["id"] == match["attendee_id"]), None)
        if attendee:
            print(f"\n{idx}. {attendee['first_name']} {attendee['last_name']}")
            if attendee.get('company'):
                print(f"   Company: {attendee['company']}")
            if attendee.get('job_title'):
                print(f"   Title: {attendee['job_title']}")
            if attendee.get('country'):
                print(f"   Country: {attendee['country']}")
            print(f"   Match: {match['text'][:120]}...")
            print(f"   Score: {score:.3f}")

            # Store enriched match data for later access
            enriched_matches.append({
                "match_text": match['text'],
                "score": score,
                "attendee": attendee
            })

    # Option to view full details
    if interactive and enriched_matches:
        while True:
            choice = input(f"\nEnter number (1-{len(enriched_matches)}) to view full profile, or 'c' to continue: ").strip().lower()
            if choice == 'c':
                break
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(enriched_matches):
                    display_full_profile(enriched_matches[idx])
                else:
                    print(f"[ERROR] Please enter a number between 1 and {len(enriched_matches)}")
            except ValueError:
                print("[ERROR] Invalid input. Enter a number or 'c'")

    return enriched_matches


def display_full_profile(match_data: Dict):
    """Display complete profile information for an attendee"""
    attendee = match_data["attendee"]

    print("\n" + "="*80)
    print("FULL PROFILE")
    print("="*80)

    print(f"\nName: {attendee['first_name']} {attendee['last_name']}")
    print(f"Company: {attendee.get('company', 'N/A')}")
    print(f"Job Title: {attendee.get('job_title', 'N/A')}")
    print(f"Country: {attendee.get('country', 'N/A')}")

    if attendee.get('linkedin'):
        print(f"LinkedIn: {attendee['linkedin']}")
    if attendee.get('swapcard'):
        print(f"Swapcard: {attendee['swapcard']}")

    print(f"\nMatch Score: {match_data['score']:.3f}")
    print(f"Matched On: {match_data['match_text']}")

    if attendee.get('biography') and attendee['biography'] != 'nan':
        print(f"\n--- ORIGINAL BIOGRAPHY ---")
        print(attendee['biography'])

    print(f"\n--- OFFERINGS ({len(attendee['offerings'])}) ---")
    for i, offering in enumerate(attendee['offerings'], 1):
        print(f"{i}. {offering}")

    print(f"\n--- REQUESTS ({len(attendee['requests'])}) ---")
    for i, request in enumerate(attendee['requests'], 1):
        print(f"{i}. {request}")

    print("\n" + "="*80)


def search_by_custom_request(request: str, save_results: bool = False) -> List[tuple]:
    """Search for people who can help with a custom request"""
    print(f"\n[INFO] Searching for: '{request}'")

    # Generate synthetic offering from request
    print("[INFO] Generating synthetic offering...")
    synthetic_prompt = f"""Convert this REQUEST into a synthetic OFFERING that would fulfill it.
REQUEST: "{request}"
Return ONLY the synthetic offering text (one sentence), nothing else."""

    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=synthetic_prompt
    )
    synthetic_offering = response.text.strip()
    print(f"[INFO] Synthetic offering: '{synthetic_offering}'")

    # Generate embedding
    print("[INFO] Generating embedding...")
    query_embedding = generate_embedding(synthetic_offering)

    # Find matches
    print("[INFO] Finding top matches...")
    matches = find_top_matches(query_embedding, embeddings_data["offerings"], top_k=10)

    # Optionally save enriched results
    if save_results:
        save_enriched_results(request, matches, "request")

    return matches


def search_by_custom_offering(offering: str, save_results: bool = False) -> List[tuple]:
    """Search for people who need a custom offering"""
    print(f"\n[INFO] Searching for people who need: '{offering}'")

    # Generate embedding
    print("[INFO] Generating embedding...")
    query_embedding = generate_embedding(offering)

    # Find matches
    print("[INFO] Finding top matches...")
    matches = find_top_matches(query_embedding, embeddings_data["requests"], top_k=10)

    # Optionally save enriched results
    if save_results:
        save_enriched_results(offering, matches, "offering")

    return matches


def save_enriched_results(query: str, matches: List[tuple], query_type: str):
    """Save search results with full profile data to JSON file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_search_results_{query_type}.json"
    filepath = os.path.join(RESULTS_DIR, filename)

    enriched_results = {
        "query": query,
        "query_type": query_type,
        "timestamp": timestamp,
        "matches": []
    }

    for match, score in matches:
        attendee = next((a for a in extracted_data if a["id"] == match["attendee_id"]), None)
        if attendee:
            enriched_results["matches"].append({
                "score": float(score),
                "match_text": match["text"],
                "attendee": {
                    "id": attendee["id"],
                    "first_name": attendee["first_name"],
                    "last_name": attendee["last_name"],
                    "company": attendee.get("company"),
                    "job_title": attendee.get("job_title"),
                    "country": attendee.get("country"),
                    "linkedin": attendee.get("linkedin"),
                    "swapcard": attendee.get("swapcard"),
                    "biography": attendee.get("biography"),
                    "offerings": attendee["offerings"],
                    "requests": attendee["requests"]
                }
            })

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(enriched_results, f, indent=2, ensure_ascii=False)

    print(f"[OK] Results saved to: {filepath}")


def search_by_name(name: str):
    """Search for an attendee by name"""
    print(f"\n[INFO] Searching for attendee: '{name}'")

    name_lower = name.lower()
    attendee = None

    for a in extracted_data:
        full_name = f"{a['first_name']} {a['last_name']}".lower()
        if name_lower in full_name:
            attendee = a
            break

    if not attendee:
        print(f"[ERROR] No attendee found matching '{name}'")
        return

    print(f"[OK] Found: {attendee['first_name']} {attendee['last_name']}")
    print(f"     Company: {attendee.get('company', 'N/A')}")
    print(f"     Title: {attendee.get('job_title', 'N/A')}")
    print(f"     Country: {attendee.get('country', 'N/A')}")

    print(f"\n[INFO] Offerings ({len(attendee['offerings'])}):")
    for i, offering in enumerate(attendee['offerings'], 1):
        print(f"  {i}. {offering}")

    print(f"\n[INFO] Requests ({len(attendee['requests'])}):")
    for i, request in enumerate(attendee['requests'], 1):
        print(f"  {i}. {request}")

    # Find who can help them
    if attendee['requests']:
        print("\n" + "="*80)
        print("PEOPLE WHO CAN HELP THIS PERSON")
        print("="*80)

        for request in attendee['requests'][:2]:  # Show first 2 requests
            print(f"\n[PROGRESS] Processing request: {request[:80]}...")
            matches = search_by_custom_request(request)
            display_matches(matches[:5], f"Top 5 matches for: {request[:60]}...")

    # Find who they can help
    if attendee['offerings']:
        print("\n" + "="*80)
        print("PEOPLE THIS PERSON CAN HELP")
        print("="*80)

        for offering in attendee['offerings'][:2]:  # Show first 2 offerings
            print(f"\n[PROGRESS] Processing offering: {offering[:80]}...")
            matches = search_by_custom_offering(offering)
            display_matches(matches[:5], f"Top 5 matches for: {offering[:60]}...")


def interactive_cli():
    """Interactive CLI for testing search"""
    print("\n" + "="*80)
    print("INTERACTIVE SEARCH TEST")
    print("="*80)
    print("\nAvailable Commands:")
    print("  1. Search by attendee name")
    print("  2. Search by custom request (find who can help)")
    print("  3. Search by custom offering (find who you can help)")
    print("  4. List all attendees in sample")
    print("  5. Exit")

    while True:
        print("\n" + "-"*80)
        choice = input("\nEnter choice (1-5): ").strip()

        if choice == "1":
            name = input("Enter attendee name (first or last): ").strip()
            search_by_name(name)

        elif choice == "2":
            request = input("Enter your request: ").strip()
            save = input("Save results to JSON? (y/n): ").strip().lower() == 'y'
            matches = search_by_custom_request(request, save_results=save)
            display_matches(matches, "People who can help you:")

        elif choice == "3":
            offering = input("Enter your offering: ").strip()
            save = input("Save results to JSON? (y/n): ").strip().lower() == 'y'
            matches = search_by_custom_offering(offering, save_results=save)
            display_matches(matches, "People you can help:")

        elif choice == "4":
            print("\n" + "="*80)
            print("ALL ATTENDEES IN SAMPLE (25)")
            print("="*80)
            for i, a in enumerate(extracted_data, 1):
                print(f"{i:2d}. {a['first_name']} {a['last_name']:20s} | {a.get('company', 'N/A')[:40]}")

        elif choice == "5":
            print("\n[OK] Exiting CLI test")
            break

        else:
            print("[ERROR] Invalid choice. Please enter 1-5.")


def run_demo_searches():
    """Run pre-configured demo searches to showcase functionality"""
    print("\n" + "="*80)
    print("DEMO SEARCHES")
    print("="*80)

    # Demo 1: Find AI safety mentors
    print("\n[DEMO 1] Finding AI safety mentors...")
    matches = search_by_custom_request("I need mentorship on AI safety research")
    display_matches(matches[:5], "Top 5 AI Safety Mentors", interactive=False)

    # Demo 2: Find people interested in community building
    print("\n[DEMO 2] Finding people who need community building help...")
    matches = search_by_custom_offering("I can help with EA community building and event organization")
    display_matches(matches[:5], "Top 5 People Needing Community Building Help", interactive=False)

    # Demo 3: Search for specific person
    print("\n[DEMO 3] Searching for Manuel Allgaier...")
    search_by_name("Manuel")


if __name__ == "__main__":
    # Uncomment the mode you want to test:

    # Option 1: Run pre-configured demos (quick test)
    # run_demo_searches()

    # Option 2: Interactive CLI (full control)
    interactive_cli()

    print("\n" + "="*80)
    print("[OK] CLI test completed successfully!")
    print("="*80)
