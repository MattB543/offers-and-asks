"""
File: check_complete_profiles.py
Created: 2025-10-06
Creation Reason: DIRECT USER REQUEST
Purpose: Check how many CSV rows meet the complete profile criteria:
         - Biography > 50 chars
         - "How Others Can Help Me" > 20 chars
         - "How I Can Help Others" > 20 chars
Author: Claude AI (at user request)
"""

import pandas as pd
import os

# CSV path
CSV_PATH = "input/[Do not share with non-attendees] Swapcard Attendee Data _ EA Global_ NYC 2025 - Attendee Data.csv"

def check_complete_profiles():
    """Count rows meeting completeness criteria"""

    print("[INFO] Loading CSV...")

    # Skip the header rows (first 4 rows are metadata/description)
    # The CSV has a multi-line description that counts as 1 row
    df = pd.read_csv(CSV_PATH, skiprows=4)

    # Clean column names
    df.columns = df.columns.str.strip()

    total_rows = len(df)
    print(f"[OK] Loaded {total_rows} total rows")

    # Debug: Show column names
    print(f"[DEBUG] Column names: {list(df.columns)}")

    # Debug: Show first row
    print(f"[DEBUG] Sample row 0:")
    print(f"  Biography: '{df.iloc[0].get('Biography', 'MISSING')}'")
    print(f"  How Others Can Help Me: '{df.iloc[0].get('How Others Can Help Me', 'MISSING')}'")
    print(f"  How I Can Help Others: '{df.iloc[0].get('How I Can Help Others', 'MISSING')}'")
    print()

    # Apply filters
    stats = {
        'total': total_rows,
        'no_biography': 0,
        'short_biography': 0,
        'no_help_me': 0,
        'short_help_me': 0,
        'no_can_help': 0,
        'short_can_help': 0,
        'passed_all': 0
    }

    passed_rows = []

    for idx, row in df.iterrows():
        bio = str(row.get('Biography', '')).strip()
        help_me = str(row.get('How Others Can Help Me', '')).strip()
        can_help = str(row.get('How I Can Help Others', '')).strip()

        # Check biography
        if bio == 'nan' or not bio:
            stats['no_biography'] += 1
            continue

        if len(bio) <= 50:
            stats['short_biography'] += 1
            continue

        # Check "How Others Can Help Me"
        if help_me == 'nan' or not help_me:
            stats['no_help_me'] += 1
            continue

        if len(help_me) <= 20:
            stats['short_help_me'] += 1
            continue

        # Check "How I Can Help Others"
        if can_help == 'nan' or not can_help:
            stats['no_can_help'] += 1
            continue

        if len(can_help) <= 20:
            stats['short_can_help'] += 1
            continue

        # If we get here, row passed all filters
        stats['passed_all'] += 1
        passed_rows.append({
            'index': idx,
            'first_name': row.get('First Name', ''),
            'last_name': row.get('Last Name', ''),
            'bio_length': len(bio),
            'help_me_length': len(help_me),
            'can_help_length': len(can_help)
        })

    # Print detailed statistics
    print("="*80)
    print("COMPLETE PROFILE ANALYSIS")
    print("="*80)
    print(f"\nTotal rows in CSV: {stats['total']}")
    print(f"\nFiltering Criteria:")
    print(f"  - Biography > 50 characters")
    print(f"  - 'How Others Can Help Me' > 20 characters")
    print(f"  - 'How I Can Help Others' > 20 characters")
    print(f"\nFilter Results:")
    print(f"  [FAIL] No biography: {stats['no_biography']} ({stats['no_biography']/stats['total']*100:.1f}%)")
    print(f"  [FAIL] Biography too short (<=50 chars): {stats['short_biography']} ({stats['short_biography']/stats['total']*100:.1f}%)")
    print(f"  [FAIL] No 'How Others Can Help Me': {stats['no_help_me']} ({stats['no_help_me']/stats['total']*100:.1f}%)")
    print(f"  [FAIL] 'How Others Can Help Me' too short (<=20 chars): {stats['short_help_me']} ({stats['short_help_me']/stats['total']*100:.1f}%)")
    print(f"  [FAIL] No 'How I Can Help Others': {stats['no_can_help']} ({stats['no_can_help']/stats['total']*100:.1f}%)")
    print(f"  [FAIL] 'How I Can Help Others' too short (<=20 chars): {stats['short_can_help']} ({stats['short_can_help']/stats['total']*100:.1f}%)")
    print(f"  [OK] PASSED ALL FILTERS: {stats['passed_all']} ({stats['passed_all']/stats['total']*100:.1f}%)")
    print("="*80)

    # Show sample of passed rows
    if passed_rows:
        print(f"\n[INFO] Sample of rows that passed (showing first 10):\n")
        for i, row in enumerate(passed_rows[:10], 1):
            print(f"{i}. {row['first_name']} {row['last_name']}")
            print(f"   Bio: {row['bio_length']} chars | Help Me: {row['help_me_length']} chars | Can Help: {row['can_help_length']} chars")

        if len(passed_rows) > 10:
            print(f"\n... and {len(passed_rows) - 10} more rows")

    print(f"\n{'='*80}")
    print(f"[OK] ANSWER: {stats['passed_all']} rows meet all criteria")
    print(f"{'='*80}\n")

    return stats, passed_rows


if __name__ == "__main__":
    stats, passed_rows = check_complete_profiles()
