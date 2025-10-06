"""
File: get_filtered_attendee_ids_by_name.py
Created: 2025-10-06
Creation Reason: Fix index mismatch issue
Purpose: Get database attendee IDs by querying with first/last names from CSV
         instead of relying on index matching
Author: Claude AI
"""

import pandas as pd
import json
import os
from supabase import create_client
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

CSV_PATH = "input/[Do not share with non-attendees] Swapcard Attendee Data _ EA Global_ NYC 2025 - Attendee Data.csv"
OUTPUT_PATH = "outputs/filtered_attendee_ids.json"

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def get_filtered_ids():
    """Get attendee IDs from database by matching names from CSV"""

    print("[INFO] Loading CSV with CORRECT skiprows=4...")

    # Use correct skiprows to get proper column headers
    df = pd.read_csv(CSV_PATH, skiprows=4)
    df.columns = df.columns.str.strip()

    print(f"[OK] Loaded {len(df)} total rows from CSV")

    # Find rows that meet criteria
    filtered_names = []

    for idx, row in df.iterrows():
        bio = str(row.get('Biography', '')).strip()
        help_me = str(row.get('How Others Can Help Me', '')).strip()
        can_help = str(row.get('How I Can Help Others', '')).strip()

        # Skip nan values
        if bio == 'nan': bio = ''
        if help_me == 'nan': help_me = ''
        if can_help == 'nan': can_help = ''

        # Apply criteria
        if len(bio) > 50 and len(help_me) > 20 and len(can_help) > 20:
            filtered_names.append({
                'first_name': str(row.get('First Name', '')).strip(),
                'last_name': str(row.get('Last Name', '')).strip()
            })

    print(f"[OK] Found {len(filtered_names)} attendees meeting criteria in CSV")

    # Now query database to get IDs by name
    print(f"\n[INFO] Querying database for attendee IDs by name...")

    filtered_ids = []
    not_found = []

    for name in tqdm(filtered_names, desc="Looking up database IDs"):
        response = supabase.table("attendees")\
            .select("id")\
            .eq("first_name", name['first_name'])\
            .eq("last_name", name['last_name'])\
            .execute()

        if response.data and len(response.data) > 0:
            filtered_ids.append(response.data[0]['id'])
        else:
            not_found.append(f"{name['first_name']} {name['last_name']}")

    print(f"\n[OK] Found {len(filtered_ids)} matching attendees in database")

    if not_found:
        print(f"[WARN] {len(not_found)} attendees from CSV not found in database")
        if len(not_found) <= 10:
            print(f"[WARN] Missing: {', '.join(not_found)}")

    # Save to JSON
    with open(OUTPUT_PATH, 'w') as f:
        json.dump(filtered_ids, f)

    print(f"[OK] Saved {len(filtered_ids)} filtered IDs to {OUTPUT_PATH}")

    return filtered_ids

if __name__ == "__main__":
    filtered_ids = get_filtered_ids()
    print(f"\n[OK] {len(filtered_ids)} database attendee IDs ready for pre-computation")
