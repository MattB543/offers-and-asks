"""
File: upload_filtered_to_supabase.py
Created: 2025-10-06
Creation Reason: DIRECT USER REQUEST
Purpose: Upload ONLY the filtered 575 attendees to Supabase
         (replacing the current 25 test rows)
Author: Claude AI (at user request)
Input: outputs/extracted_data/*_filtered_575_attendees.json
       outputs/embeddings/*_filtered_575_embeddings.json
Output: Supabase database (attendees, offerings, requests tables)
"""

import json
import os
import sys
import glob
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


def find_latest_files():
    """Find the most recent extraction and embedding files"""
    extraction_files = glob.glob("outputs/extracted_data/*_filtered_575_attendees.json")
    embedding_files = glob.glob("outputs/embeddings/*_filtered_575_embeddings.json")

    if not extraction_files:
        raise FileNotFoundError("No filtered extraction file found. Run extract_filtered_attendees.py first.")

    if not embedding_files:
        raise FileNotFoundError("No filtered embeddings file found. Run generate_embeddings_filtered.py first.")

    extraction_file = max(extraction_files, key=os.path.getmtime)
    embeddings_file = max(embedding_files, key=os.path.getmtime)

    return extraction_file, embeddings_file


def clear_existing_data():
    """Clear existing data from database"""
    print("\n[WARN] Clearing existing data from database...")

    response = input("This will DELETE all existing attendees, offerings, and requests. Continue? (yes/no): ").strip().lower()

    if response != 'yes':
        print("[INFO] Keeping existing data")
        return False

    try:
        # Delete in reverse order of foreign key dependencies
        print("[INFO] Deleting pre-computed matches...")
        supabase.table("request_to_offering_matches").delete().neq('request_id', -1).execute()
        supabase.table("offering_to_request_matches").delete().neq('offering_id', -1).execute()

        print("[INFO] Deleting offerings...")
        supabase.table("offerings").delete().neq('id', -1).execute()

        print("[INFO] Deleting requests...")
        supabase.table("requests").delete().neq('id', -1).execute()

        print("[INFO] Deleting attendees...")
        supabase.table("attendees").delete().neq('id', -1).execute()

        print("[OK] Cleared all existing data")
        return True

    except Exception as e:
        print(f"[ERROR] Failed to clear data: {str(e)}")
        sys.exit(1)


def upload_attendees(extracted_data):
    """Upload attendees to Supabase"""
    print("\n[START] Uploading attendees...")

    attendees = []
    for item in extracted_data:
        attendees.append({
            "id": item["id"],
            "first_name": item["first_name"],
            "last_name": item["last_name"],
            "company": item["company"] if item["company"] not in ["nan", ""] else None,
            "job_title": item["job_title"] if item["job_title"] not in ["nan", ""] else None,
            "country": item["country"] if item["country"] not in ["nan", ""] else None,
            "linkedin": item["linkedin"] if item["linkedin"] not in ["nan", ""] else None,
            "swapcard": item["swapcard"] if item["swapcard"] not in ["nan", ""] else None,
            "biography": item["biography"] if item["biography"] not in ["nan", ""] else None
        })

    # Batch insert
    batch_size = 500
    for i in tqdm(range(0, len(attendees), batch_size), desc="Uploading attendees"):
        batch = attendees[i:i + batch_size]
        try:
            response = supabase.table("attendees").upsert(batch).execute()
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
            "embedding": item["embedding"]
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
    print("UPLOAD FILTERED 575 ATTENDEES TO SUPABASE")
    print("="*80)

    # Find latest files
    extraction_file, embeddings_file = find_latest_files()

    print(f"\n[INFO] Using extraction file: {extraction_file}")
    print(f"[INFO] Using embeddings file: {embeddings_file}")

    # Load data
    print("\n[START] Loading JSON files...")

    with open(extraction_file, 'r', encoding='utf-8') as f:
        extracted_data = json.load(f)

    with open(embeddings_file, 'r', encoding='utf-8') as f:
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
    print("\n[WARN] This will REPLACE all existing data in your database.")

    response = input("\nProceed with upload? (yes/no): ").strip().lower()

    if response != 'yes':
        print("[INFO] Upload cancelled by user")
        return

    # Clear existing data
    if not clear_existing_data():
        print("[INFO] Upload cancelled - keeping existing data")
        return

    # Upload in order (attendees first due to foreign key constraints)
    upload_attendees(extracted_data)
    upload_offerings(embeddings_data)
    upload_requests(embeddings_data)

    # Verify
    verify_upload()

    print("\n" + "="*80)
    print("[OK] UPLOAD COMPLETE!")
    print("="*80)
    print("\nNext steps:")
    print("1. Verify data in Supabase dashboard")
    print("2. Pre-compute matches: python precompute_matches_filtered.py")


if __name__ == "__main__":
    main()
