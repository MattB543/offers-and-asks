"""
File: get_filtered_attendee_ids.py
Created: 2025-10-06
Creation Reason: DIRECT USER REQUEST
Purpose: Get list of attendee IDs that meet specific completeness criteria:
         - Biography > 50 chars
         - "How Others Can Help Me" > 20 chars
         - "How I Can Help Others" > 20 chars
         Returns JSON list for use in precompute_matches_filtered.py
Author: Claude AI (at user request)
"""

import pandas as pd
import json
import sys

CSV_PATH = "input/[Do not share with non-attendees] Swapcard Attendee Data _ EA Global_ NYC 2025 - Attendee Data.csv"
OUTPUT_PATH = "outputs/filtered_attendee_ids.json"

def get_filtered_ids():
    """Get attendee IDs that meet the criteria"""

    print("[INFO] Loading CSV...")

    # Skip the header rows - MUST match ea_matching.py (skiprows=8)
    # This ensures CSV indices match database attendee IDs
    df = pd.read_csv(CSV_PATH, skiprows=8)
    df.columns = df.columns.str.strip()

    print(f"[OK] Loaded {len(df)} total rows")

    # Filter for complete profiles
    filtered_ids = []

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
            filtered_ids.append(idx)

    print(f"[OK] Found {len(filtered_ids)} attendees meeting criteria ({len(filtered_ids)/len(df)*100:.1f}%)")

    # Save to JSON
    with open(OUTPUT_PATH, 'w') as f:
        json.dump(filtered_ids, f)

    print(f"[OK] Saved filtered IDs to {OUTPUT_PATH}")

    return filtered_ids

if __name__ == "__main__":
    filtered_ids = get_filtered_ids()
    print(f"\n[OK] {len(filtered_ids)} attendee IDs ready for pre-computation")
