"""
File: generate_embeddings_filtered.py
Created: 2025-10-06
Creation Reason: DIRECT USER REQUEST
Purpose: Generate embeddings for the filtered 575 attendees' offerings and requests
Author: Claude AI (at user request)
Input: outputs/extracted_data/*_filtered_575_attendees.json
Output: outputs/embeddings/TIMESTAMP_filtered_575_embeddings.json
"""

import os
import json
import numpy as np
from typing import List, Dict
from google import genai
from tqdm import tqdm
from dotenv import load_dotenv
from datetime import datetime
import glob

load_dotenv()

# Configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set")

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIM = 1536

# Initialize Gemini client
client = genai.Client(api_key=GEMINI_API_KEY)

# Create output directory
os.makedirs("outputs/embeddings", exist_ok=True)


def find_latest_extracted_file() -> str:
    """Find the most recent filtered extraction file"""
    files = glob.glob("outputs/extracted_data/*_filtered_575_attendees.json")

    if not files:
        raise FileNotFoundError("No filtered extraction file found. Run extract_filtered_attendees.py first.")

    latest = max(files, key=os.path.getmtime)
    return latest


def generate_embedding(text: str) -> List[float]:
    """Generate normalized embedding for text"""
    try:
        result = client.models.embed_content(
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


def generate_all_embeddings(extracted_data: List[Dict]) -> str:
    """Generate embeddings for all offerings and requests"""

    print("\n[START] Generating embeddings...")

    embeddings_data = {
        "offerings": [],
        "requests": []
    }

    # Generate embeddings for offerings
    print("\n[INFO] Generating embeddings for offerings...")
    offering_count = sum(len(a['offerings']) for a in extracted_data)
    print(f"[INFO] Total offerings to process: {offering_count}")

    with tqdm(total=offering_count, desc="Offering embeddings") as pbar:
        for attendee in extracted_data:
            for offering in attendee["offerings"]:
                embedding = generate_embedding(offering)
                if embedding:
                    embeddings_data["offerings"].append({
                        "attendee_id": attendee["id"],
                        "text": offering,
                        "embedding": embedding
                    })
                pbar.update(1)

    # Generate embeddings for requests
    print("\n[INFO] Generating embeddings for requests...")
    request_count = sum(len(a['requests']) for a in extracted_data)
    print(f"[INFO] Total requests to process: {request_count}")

    with tqdm(total=request_count, desc="Request embeddings") as pbar:
        for attendee in extracted_data:
            for request in attendee["requests"]:
                embedding = generate_embedding(request)
                if embedding:
                    embeddings_data["requests"].append({
                        "attendee_id": attendee["id"],
                        "text": request,
                        "embedding": embedding
                    })
                pbar.update(1)

    # Save to JSON with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"outputs/embeddings/{timestamp}_filtered_575_embeddings.json"

    print(f"\n[INFO] Saving embeddings to {output_path}...")

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(embeddings_data, f, indent=2, ensure_ascii=False)

    print(f"[OK] Generated {len(embeddings_data['offerings'])} offering embeddings")
    print(f"[OK] Generated {len(embeddings_data['requests'])} request embeddings")

    return output_path


def main():
    print("="*80)
    print("GENERATE EMBEDDINGS FOR FILTERED ATTENDEES (575)")
    print("="*80)

    # Find latest extraction file
    extraction_file = find_latest_extracted_file()
    print(f"\n[INFO] Using extraction file: {extraction_file}")

    # Load extracted data
    print("[INFO] Loading extracted data...")

    with open(extraction_file, 'r', encoding='utf-8') as f:
        extracted_data = json.load(f)

    print(f"[OK] Loaded {len(extracted_data)} attendees")

    total_offerings = sum(len(a['offerings']) for a in extracted_data)
    total_requests = sum(len(a['requests']) for a in extracted_data)
    total_embeddings = total_offerings + total_requests

    print(f"\n[INFO] Will generate embeddings for:")
    print(f"  Offerings: {total_offerings}")
    print(f"  Requests: {total_requests}")
    print(f"  Total: {total_embeddings}")

    print(f"\n[INFO] Estimated time: 15-20 minutes")
    print(f"[INFO] Estimated cost: ~$1-2")

    response = input("\nProceed? (yes/no): ").strip().lower()

    if response != 'yes':
        print("[INFO] Cancelled by user")
        return

    # Generate embeddings
    output_path = generate_all_embeddings(extracted_data)

    print("\n" + "="*80)
    print("[OK] EMBEDDINGS GENERATED!")
    print("="*80)
    print(f"\nOutput file: {output_path}")
    print("\nNext steps:")
    print("1. Upload to database: python upload_filtered_to_supabase.py")
    print("2. Pre-compute matches: python precompute_matches_filtered.py")


if __name__ == "__main__":
    main()
