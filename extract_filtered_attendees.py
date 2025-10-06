"""
File: extract_filtered_attendees.py
Created: 2025-10-06
Creation Reason: DIRECT USER REQUEST
Purpose: Extract offerings/requests ONLY for the 575 attendees that meet completeness criteria
         (Bio >50 chars, both help fields >20 chars)
Author: Claude AI (at user request)
Input: CSV file
Output: outputs/extracted_data/TIMESTAMP_filtered_575_attendees.json
"""

import os
import json
import pandas as pd
import numpy as np
from typing import List, Dict
from google import genai
from tqdm import tqdm
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set")

LLM_MODEL = "gemini-2.5-pro"
CSV_PATH = "input/[Do not share with non-attendees] Swapcard Attendee Data _ EA Global_ NYC 2025 - Attendee Data.csv"

# Initialize Gemini client
client = genai.Client(api_key=GEMINI_API_KEY)

# Create output directory
os.makedirs("outputs/extracted_data", exist_ok=True)


def load_and_filter_csv() -> pd.DataFrame:
    """Load CSV and filter for complete profiles"""
    print("[INFO] Loading CSV...")

    # Use skiprows=4 for correct column headers
    df = pd.read_csv(CSV_PATH, skiprows=4)
    df.columns = df.columns.str.strip()

    print(f"[OK] Loaded {len(df)} total rows")

    # Filter for complete profiles
    print("[INFO] Filtering for complete profiles...")

    filtered_indices = []

    for idx, row in df.iterrows():
        bio = str(row.get('Biography', '')).strip()
        help_me = str(row.get('How Others Can Help Me', '')).strip()
        can_help = str(row.get('How I Can Help Others', '')).strip()

        # Skip nan values
        if bio == 'nan': bio = ''
        if help_me == 'nan': help_me = ''
        if can_help == 'nan': can_help = ''

        # Apply criteria: bio >50, both help fields >20
        if len(bio) > 50 and len(help_me) > 20 and len(can_help) > 20:
            filtered_indices.append(idx)

    df_filtered = df.loc[filtered_indices].copy()

    print(f"[OK] Filtered to {len(df_filtered)} attendees ({len(df_filtered)/len(df)*100:.1f}%)")

    return df_filtered


def extract_offerings_and_requests(row: pd.Series) -> Dict:
    """Use Gemini to extract offerings and requests from a person's profile"""

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
        return {"offerings": [], "requests": []}

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
        print(f"[ERROR] Extraction failed for {row.get('First Name')} {row.get('Last Name')}: {e}")
        return {"offerings": [], "requests": []}


def process_filtered_attendees(df: pd.DataFrame) -> str:
    """Extract offerings and requests for filtered attendees"""

    print(f"\n[START] Extracting offerings/requests for {len(df)} filtered attendees...")
    print("[INFO] This will take ~30-45 minutes...")

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

    # Save to JSON with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"outputs/extracted_data/{timestamp}_filtered_575_attendees.json"

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(extracted_data, f, indent=2, ensure_ascii=False)

    print(f"[OK] Saved extracted data to {output_path}")

    # Print statistics
    total_offerings = sum(len(a['offerings']) for a in extracted_data)
    total_requests = sum(len(a['requests']) for a in extracted_data)

    print(f"\n[OK] Extraction complete!")
    print(f"  Attendees processed: {len(extracted_data)}")
    print(f"  Total offerings: {total_offerings}")
    print(f"  Total requests: {total_requests}")
    print(f"  Avg offerings per person: {total_offerings/len(extracted_data):.1f}")
    print(f"  Avg requests per person: {total_requests/len(extracted_data):.1f}")

    return output_path


def main():
    print("="*80)
    print("EXTRACT OFFERINGS/REQUESTS FOR FILTERED ATTENDEES (575)")
    print("="*80)
    print("\nCriteria:")
    print("  - Biography > 50 characters")
    print("  - 'How Others Can Help Me' > 20 characters")
    print("  - 'How I Can Help Others' > 20 characters")
    print("\n" + "="*80)

    # Load and filter CSV
    df_filtered = load_and_filter_csv()

    # Confirm
    print(f"\n[INFO] Ready to extract offerings/requests for {len(df_filtered)} attendees")
    print("[INFO] Estimated time: 30-45 minutes")
    print("[INFO] Estimated cost: ~$5-8")

    response = input("\nProceed? (yes/no): ").strip().lower()

    if response != 'yes':
        print("[INFO] Cancelled by user")
        return

    # Process
    output_path = process_filtered_attendees(df_filtered)

    print("\n" + "="*80)
    print("[OK] EXTRACTION COMPLETE!")
    print("="*80)
    print(f"\nOutput file: {output_path}")
    print("\nNext steps:")
    print("1. Generate embeddings: python generate_embeddings_filtered.py")
    print("2. Upload to database: python upload_filtered_to_supabase.py")
    print("3. Pre-compute matches: python precompute_matches_filtered.py")


if __name__ == "__main__":
    main()
