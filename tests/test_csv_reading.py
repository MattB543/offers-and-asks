"""
File: test_csv_reading.py
Created: 2025-10-05
Creation Reason: AUTONOMOUS (Testing/Analysis)
Purpose: Debug CSV reading to find the correct header row and understand structure
Author: Claude AI (autonomous debugging)
"""

import pandas as pd
import os

CSV_PATH = r"input\[Do not share with non-attendees] Swapcard Attendee Data _ EA Global_ NYC 2025 - Attendee Data.csv"

print("="*80)
print("CSV STRUCTURE DEBUG TEST")
print("="*80)

# Read first 15 lines raw to see structure
print("\n[TEST 1] First 15 lines RAW:")
print("-"*80)
with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
    for i, line in enumerate(f, 1):
        if i <= 15:
            # Show first 120 chars of each line
            print(f"Line {i:2d}: {line[:120].strip()}")
        else:
            break

print("\n" + "="*80)

# Test different skiprows values
for skip in [0, 7, 8, 9]:
    print(f"\n[TEST 2.{skip}] Testing skiprows={skip}")
    print("-"*80)
    try:
        df = pd.read_csv(CSV_PATH, skiprows=skip, encoding='utf-8-sig', nrows=3)
        print(f"  Shape: {df.shape}")
        print(f"  Columns (first 5): {list(df.columns)[:5]}")
        print(f"  First row values (first 3 cols):")
        for col in list(df.columns)[:3]:
            print(f"    {col}: {df.iloc[0][col]}")
    except Exception as e:
        print(f"  [ERROR] {str(e)[:100]}")

print("\n" + "="*80)

# Test with header parameter
for header_row in [0, 7, 8, 9]:
    print(f"\n[TEST 3.{header_row}] Testing header={header_row}")
    print("-"*80)
    try:
        df = pd.read_csv(CSV_PATH, header=header_row, encoding='utf-8-sig', nrows=3)
        print(f"  Shape: {df.shape}")
        print(f"  Columns (first 5): {list(df.columns)[:5]}")
        if 'First Name' in df.columns and 'Last Name' in df.columns:
            print(f"  [OK] Found 'First Name' and 'Last Name' columns!")
            print(f"  First data row: {df.iloc[0]['First Name']} {df.iloc[0]['Last Name']}")
        else:
            print(f"  [WARN] Expected columns not found")
    except Exception as e:
        print(f"  [ERROR] {str(e)[:100]}")

print("\n" + "="*80)
print("RECOMMENDATION:")
print("-"*80)

# Final test - find which works
for skip in range(0, 12):
    try:
        df = pd.read_csv(CSV_PATH, skiprows=skip, encoding='utf-8-sig', nrows=1)
        if 'First Name' in df.columns and 'Last Name' in df.columns:
            print(f"\n[OK] CORRECT SETTING: skiprows={skip}")
            print(f"     Columns: {list(df.columns)[:8]}")
            print(f"     First attendee: {df.iloc[0]['First Name']} {df.iloc[0]['Last Name']}")
            break
    except:
        pass

print("\n" + "="*80)
