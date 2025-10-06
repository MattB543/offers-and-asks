"""
File: upload_to_supabase.py
Created: 2025-10-06
Creation Reason: DIRECT USER REQUEST
Purpose: Upload extracted attendee data and embeddings to Supabase PostgreSQL
         with pgvector support. Works with both test (25 samples) and full
         (5000 attendees) datasets.
Author: Claude AI (at user request)
Input: outputs/extracted_data/*.json, outputs/embeddings/*.json
Output: Supabase PostgreSQL tables (attendees, offerings, requests)
"""

import json
import os
import sys
from supabase import create_client, Client
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

# Supabase credentials
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("[ERROR] Missing Supabase credentials!")
    print("Please set SUPABASE_URL and SUPABASE_SERVICE_KEY in your .env file")
    sys.exit(1)

print(f"[INFO] Connecting to Supabase: {SUPABASE_URL}")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Data paths - will use the latest files in each directory
def find_latest_file(directory: str, pattern: str) -> str:
    """Find the most recent file matching pattern in directory"""
    import glob
    files = glob.glob(os.path.join(directory, f"*{pattern}*.json"))
    if not files:
        raise FileNotFoundError(f"No files matching '{pattern}' found in {directory}")
    # Sort by modification time, most recent first
    latest = max(files, key=os.path.getmtime)
    return latest

# Find latest extracted data and embeddings
EXTRACTED_DATA_PATH = find_latest_file("outputs/extracted_data", "extracted")
EMBEDDINGS_PATH = find_latest_file("outputs/embeddings", "embeddings")

print(f"[INFO] Using extracted data: {EXTRACTED_DATA_PATH}")
print(f"[INFO] Using embeddings: {EMBEDDINGS_PATH}")


def upload_attendees(extracted_data):
    """Upload attendees to Supabase"""
    print("\n[START] Uploading attendees...")

    attendees = []
    for item in extracted_data:
        # Handle 'nan' string values from pandas
        attendees.append({
            "id": item["id"],
            "first_name": item["first_name"],
            "last_name": item["last_name"],
            "company": item["company"] if item["company"] != "nan" else None,
            "job_title": item["job_title"] if item["job_title"] != "nan" else None,
            "country": item["country"] if item["country"] != "nan" else None,
            "linkedin": item["linkedin"] if item["linkedin"] != "nan" else None,
            "swapcard": item["swapcard"] if item["swapcard"] != "nan" else None,
            "biography": item["biography"] if item["biography"] != "nan" else None
        })

    # Batch insert (Supabase handles up to 1000 rows per insert)
    batch_size = 500
    for i in tqdm(range(0, len(attendees), batch_size), desc="Uploading attendees"):
        batch = attendees[i:i + batch_size]
        try:
            response = supabase.table("attendees").upsert(batch).execute()
            # Check if response has data
            if hasattr(response, 'data'):
                print(f"[OK] Batch {i//batch_size + 1}: Uploaded {len(batch)} attendees")
        except Exception as e:
            print(f"[ERROR] Failed to upload batch {i//batch_size + 1}: {str(e)}")
            raise

    print(f"[OK] Successfully uploaded {len(attendees)} attendees")


def upload_offerings(embeddings_data):
    """Upload offerings with embeddings"""
    print("\n[START] Uploading offerings...")

    offerings = []
    for item in embeddings_data["offerings"]:
        offerings.append({
            "attendee_id": item["attendee_id"],
            "text": item["text"],
            "embedding": item["embedding"]  # pgvector handles list automatically
        })

    # Batch insert
    batch_size = 500
    for i in tqdm(range(0, len(offerings), batch_size), desc="Uploading offerings"):
        batch = offerings[i:i + batch_size]
        try:
            response = supabase.table("offerings").insert(batch).execute()
            if hasattr(response, 'data'):
                print(f"[OK] Batch {i//batch_size + 1}: Uploaded {len(batch)} offerings")
        except Exception as e:
            print(f"[ERROR] Failed to upload batch {i//batch_size + 1}: {str(e)}")
            raise

    print(f"[OK] Successfully uploaded {len(offerings)} offerings")


def upload_requests(embeddings_data):
    """Upload requests with embeddings"""
    print("\n[START] Uploading requests...")

    requests = []
    for item in embeddings_data["requests"]:
        requests.append({
            "attendee_id": item["attendee_id"],
            "text": item["text"],
            "embedding": item["embedding"]
        })

    # Batch insert
    batch_size = 500
    for i in tqdm(range(0, len(requests), batch_size), desc="Uploading requests"):
        batch = requests[i:i + batch_size]
        try:
            response = supabase.table("requests").insert(batch).execute()
            if hasattr(response, 'data'):
                print(f"[OK] Batch {i//batch_size + 1}: Uploaded {len(batch)} requests")
        except Exception as e:
            print(f"[ERROR] Failed to upload batch {i//batch_size + 1}: {str(e)}")
            raise

    print(f"[OK] Successfully uploaded {len(requests)} requests")


def verify_upload():
    """Verify the upload by counting rows in each table"""
    print("\n[START] Verifying upload...")

    try:
        # Count attendees
        attendees_count = supabase.table("attendees").select("id", count="exact").execute()
        print(f"[INFO] Attendees in database: {attendees_count.count}")

        # Count offerings
        offerings_count = supabase.table("offerings").select("id", count="exact").execute()
        print(f"[INFO] Offerings in database: {offerings_count.count}")

        # Count requests
        requests_count = supabase.table("requests").select("id", count="exact").execute()
        print(f"[INFO] Requests in database: {requests_count.count}")

        print("[OK] Verification complete!")

    except Exception as e:
        print(f"[WARN] Verification failed: {str(e)}")


def main():
    print("="*80)
    print("UPLOADING DATA TO SUPABASE")
    print("="*80)

    # Load data
    print("\n[START] Loading JSON files...")
    with open(EXTRACTED_DATA_PATH, 'r', encoding='utf-8') as f:
        extracted_data = json.load(f)

    with open(EMBEDDINGS_PATH, 'r', encoding='utf-8') as f:
        embeddings_data = json.load(f)

    print(f"[OK] Loaded {len(extracted_data)} attendees")
    print(f"[OK] Loaded {len(embeddings_data['offerings'])} offerings")
    print(f"[OK] Loaded {len(embeddings_data['requests'])} requests")

    # Confirm before uploading
    print("\n" + "="*80)
    print("READY TO UPLOAD")
    print("="*80)
    print(f"Target: {SUPABASE_URL}")
    print(f"Attendees: {len(extracted_data)}")
    print(f"Offerings: {len(embeddings_data['offerings'])}")
    print(f"Requests: {len(embeddings_data['requests'])}")
    print("\nNOTE: This will INSERT data into your Supabase tables.")
    print("Make sure tables are empty or you may get duplicate key errors.")

    response = input("\nProceed with upload? (yes/no): ").strip().lower()
    if response != 'yes':
        print("[INFO] Upload cancelled by user")
        return

    # Upload in order (attendees first due to foreign key constraints)
    upload_attendees(extracted_data)
    upload_offerings(embeddings_data)
    upload_requests(embeddings_data)

    # Verify
    verify_upload()

    print("\n" + "="*80)
    print("✅ UPLOAD COMPLETE!")
    print("="*80)
    print("\nNext steps:")
    print("1. Check Supabase dashboard to verify data")
    print("2. Test vector search: SELECT * FROM match_offerings(...)")
    print("3. Deploy Edge Functions")
    print("4. Test Edge Functions in Supabase dashboard")


if __name__ == "__main__":
    main()
