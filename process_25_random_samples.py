"""
File: process_25_random_samples.py
Created: 2025-10-05 14:05:23
Creation Reason: DIRECT USER REQUEST
Purpose: Process 25 random attendees from EA Global NYC 2025 CSV to validate
         the extraction and embedding pipeline with extensive logging before
         running on full 5000+ attendee dataset.
Author: Claude AI (at user request)
Input: input/[Do not share with non-attendees] Swapcard Attendee Data _ EA Global_ NYC 2025 - Attendee Data.csv
Output: outputs/extracted_data/, outputs/embeddings/, outputs/logs/, outputs/analysis/
"""

import os
import json
import pandas as pd
import numpy as np
import random
from typing import List, Dict, Tuple
from google import genai
from datetime import datetime
import time
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("[ERROR] GEMINI_API_KEY environment variable not set. Please create a .env file with GEMINI_API_KEY=your-api-key")

# Model configurations
LLM_MODEL = "gemini-2.5-pro"
EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIM = 1536

# Generate timestamp for this run
RUN_TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

# Output directory structure
OUTPUT_BASE = "outputs"
OUTPUT_DIRS = {
    "logs": os.path.join(OUTPUT_BASE, "logs"),
    "extracted_data": os.path.join(OUTPUT_BASE, "extracted_data"),
    "embeddings": os.path.join(OUTPUT_BASE, "embeddings"),
    "analysis": os.path.join(OUTPUT_BASE, "analysis"),
    "results": os.path.join(OUTPUT_BASE, "results")
}

# Create all output directories
for dir_path in OUTPUT_DIRS.values():
    os.makedirs(dir_path, exist_ok=True)

print(f"[OK] Created output directory structure in: {OUTPUT_BASE}")

# File paths
CSV_PATH = os.path.join("input", "[Do not share with non-attendees] Swapcard Attendee Data _ EA Global_ NYC 2025 - Attendee Data.csv")
LOG_FILE = os.path.join(OUTPUT_DIRS["logs"], f"{RUN_TIMESTAMP}_processing_log_25_random_samples.txt")
EXTRACTED_DATA_FILE = os.path.join(OUTPUT_DIRS["extracted_data"], f"{RUN_TIMESTAMP}_extracted_data_25_random_samples.json")
EMBEDDINGS_FILE = os.path.join(OUTPUT_DIRS["embeddings"], f"{RUN_TIMESTAMP}_embeddings_1536dim_25_random_samples.json")
ANALYSIS_FILE = os.path.join(OUTPUT_DIRS["analysis"], f"{RUN_TIMESTAMP}_extraction_analysis_25_samples.json")

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Gemini client
client = genai.Client(api_key=GEMINI_API_KEY)

logger.info("=" * 80)
logger.info("PROCESSING LOG - 25 RANDOM SAMPLES")
logger.info("=" * 80)
logger.info(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
logger.info(f"Input File: {CSV_PATH}")
logger.info(f"Sample Size: 25 random rows")
logger.info(f"Output Directory: {OUTPUT_BASE}/")
logger.info(f"Log File: {LOG_FILE}")
logger.info("=" * 80)


def load_csv() -> pd.DataFrame:
    """Load and clean the attendee CSV data"""
    logger.info("[START] Loading CSV file...")

    try:
        # CSV structure (verified with test script):
        # Lines 1-4: Metadata text
        # Line 5: ACTUAL column headers ("First Name,Last Name,Company...")
        # Line 6+: Data rows
        # So skiprows=4 skips lines 1-4, making line 5 the header row
        df = pd.read_csv(CSV_PATH, skiprows=4, encoding='utf-8-sig')

        # Clean column names
        df.columns = df.columns.str.strip()

        logger.info(f"[OK] CSV loaded successfully - {len(df)} total rows")
        logger.debug(f"[DEBUG] First 10 columns: {list(df.columns)[:10]}")
        logger.info(f"[INFO] Skipped 4 rows, line 5 used as header")

        # Verify we have the expected columns
        expected_cols = ['First Name', 'Last Name', 'Biography', 'Company']
        missing_cols = [col for col in expected_cols if col not in df.columns]
        if missing_cols:
            logger.error(f"[ERROR] Missing expected columns: {missing_cols}")
            logger.debug(f"[DEBUG] Available columns: {list(df.columns)}")
            raise ValueError(f"CSV missing expected columns: {missing_cols}")

        logger.info("[OK] All expected columns found")
        return df

    except Exception as e:
        logger.error(f"[ERROR] Failed to load CSV: {str(e)}")
        raise


def select_random_sample(df: pd.DataFrame, n: int = 25) -> Tuple[pd.DataFrame, List[int]]:
    """Select n random rows from dataframe, filtering for rows with complete data"""
    logger.info(f"[START] Selecting {n} random rows from {len(df)} total rows")

    # Filter for rows with data in key columns
    # A row is "complete" if it has First Name, Last Name, and at least one of:
    # Biography, Areas of Expertise, How I Can Help Others, or How Others Can Help Me
    logger.info("[INFO] Filtering for rows with sufficient data...")

    key_data_cols = ['Biography', 'Areas of Expertise', 'How I Can Help Others', 'How Others Can Help Me']

    def has_sufficient_data(row):
        # Must have first and last name
        if pd.isna(row.get('First Name')) or pd.isna(row.get('Last Name')):
            return False
        # Must have at least one key data field
        return any(pd.notna(row.get(col)) and str(row.get(col)).strip() != '' for col in key_data_cols)

    df_complete = df[df.apply(has_sufficient_data, axis=1)].copy()

    logger.info(f"[INFO] Found {len(df_complete)} rows with sufficient data ({len(df_complete)/len(df)*100:.1f}%)")

    if len(df_complete) < n:
        logger.warning(f"[WARN] Only {len(df_complete)} complete rows available, less than requested {n}")
        n = len(df_complete)

    # Set seed for reproducibility
    random.seed(42)
    sample_indices = random.sample(range(len(df_complete)), n)
    sample_indices.sort()

    df_sample = df_complete.iloc[sample_indices].copy()

    logger.info(f"[OK] Selected {len(df_sample)} random rows with complete data")
    logger.debug(f"[DEBUG] Sample indices: {sample_indices}")

    # Log some sample names to verify we got real data
    sample_names = [f"{row['First Name']} {row['Last Name']}" for _, row in df_sample.head(5).iterrows()]
    logger.debug(f"[DEBUG] First 5 sample names: {sample_names}")

    return df_sample, sample_indices


def extract_offerings_and_requests(row: pd.Series, row_num: int, total: int) -> Dict:
    """
    Use Gemini to extract distinct offerings and requests from a person's profile
    """
    logger.info(f"[PROGRESS] {row_num}/{total} - Processing: {row.get('First Name', 'N/A')} {row.get('Last Name', 'N/A')}")

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

    logger.debug(f"[DEBUG] Profile text length: {len(profile_text)} characters")

    if not profile_text.strip():
        logger.warning(f"[WARN] Empty profile for {row.get('First Name')} {row.get('Last Name')}")
        return {"offerings": [], "requests": []}

    # Create prompt for extraction
    prompt = f"""You are analyzing an EA Global attendee's profile to extract their distinct offerings and requests.

PROFILE:
{profile_text}

Extract:
1. OFFERINGS: Distinct skills, expertise, or ways they can help others. Each offering should be self-contained and include relevant context (experience level, specifics, domain expertise).

2. REQUESTS: Distinct needs, asks, or ways others can help them. Each request should be self-contained and include relevant context.

Guidelines:
- Group related items together (not too granular)
- Make each item standalone (should make sense without seeing the full profile)
- Include qualifiers and context in each item
- Skip generic items like "networking" or "learning"
- If there's nothing substantive to extract for a category, return an empty array

Return ONLY a JSON object in this exact format:
{{
  "offerings": ["offering 1", "offering 2", ...],
  "requests": ["request 1", "request 2", ...]
}}

DO NOT include any text outside the JSON object. DO NOT use markdown code blocks.
"""

    logger.debug(f"[DEBUG] Calling Gemini API - Model: {LLM_MODEL}")
    start_time = time.time()

    try:
        response = client.models.generate_content(
            model=LLM_MODEL,
            contents=prompt
        )

        elapsed = time.time() - start_time
        logger.debug(f"[DEBUG] API response received in {elapsed:.2f}s")

        result_text = response.text.strip()
        logger.debug(f"[DEBUG] Response length: {len(result_text)} characters")

        # Clean up any markdown code blocks if present
        if result_text.startswith("```"):
            logger.debug("[DEBUG] Removing markdown code block formatting")
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
            result_text = result_text.strip()

        result = json.loads(result_text)

        offerings_count = len(result.get("offerings", []))
        requests_count = len(result.get("requests", []))

        logger.info(f"[OK] Extracted {offerings_count} offerings, {requests_count} requests")
        logger.debug(f"[DEBUG] Offerings: {result.get('offerings', [])[:2]}...")  # Show first 2
        logger.debug(f"[DEBUG] Requests: {result.get('requests', [])[:2]}...")

        return {
            "offerings": result.get("offerings", []),
            "requests": result.get("requests", [])
        }

    except Exception as e:
        logger.error(f"[ERROR] Extraction failed for {row.get('First Name')} {row.get('Last Name')}: {str(e)}")
        logger.debug(f"[DEBUG] Error details: {type(e).__name__}")
        return {
            "offerings": [],
            "requests": []
        }


def process_sample_attendees(df: pd.DataFrame) -> List[Dict]:
    """
    Extract offerings and requests for sample attendees
    """
    logger.info("=" * 80)
    logger.info("[START] Extracting offerings and requests from sample attendees")
    logger.info("=" * 80)

    extracted_data = []
    total = len(df)

    for idx, (df_idx, row) in enumerate(df.iterrows(), 1):
        logger.info("")  # Blank line for readability
        extracted = extract_offerings_and_requests(row, idx, total)

        attendee_data = {
            "id": int(df_idx),
            "first_name": str(row.get('First Name', '')),
            "last_name": str(row.get('Last Name', '')),
            "company": str(row.get('Company', '')),
            "job_title": str(row.get('Job Title', '')),
            "country": str(row.get('Country', '')),
            "linkedin": str(row.get('LinkedIn', '')),
            "swapcard": str(row.get('Swapcard', '')),
            "biography": str(row.get('Biography', '')),
            "offerings": extracted["offerings"],
            "requests": extracted["requests"]
        }

        extracted_data.append(attendee_data)

        # Small delay to avoid rate limiting
        time.sleep(0.5)

    # Save to JSON
    logger.info("")
    logger.info("=" * 80)
    logger.info(f"[START] Saving extracted data to {EXTRACTED_DATA_FILE}")

    try:
        with open(EXTRACTED_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(extracted_data, f, indent=2, ensure_ascii=False)
        logger.info(f"[OK] Saved extracted data successfully")
    except Exception as e:
        logger.error(f"[ERROR] Failed to save extracted data: {str(e)}")

    return extracted_data


def generate_embedding(text: str) -> List[float]:
    """
    Generate embedding for a text using Gemini embedding model
    Returns normalized embedding of specified dimension
    """
    logger.debug(f"[DEBUG] Generating embedding for text: '{text[:100]}...'")

    try:
        start_time = time.time()

        result = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text,
            config={
                "output_dimensionality": EMBEDDING_DIM
            }
        )

        embedding = result.embeddings[0].values

        # Normalize the embedding
        embedding_array = np.array(embedding)
        normalized = embedding_array / np.linalg.norm(embedding_array)

        elapsed = time.time() - start_time
        logger.debug(f"[DEBUG] Embedding generated in {elapsed:.2f}s - Dimension: {len(normalized)}")
        logger.debug(f"[DEBUG] Normalized L2 norm: {np.linalg.norm(normalized):.6f}")

        return normalized.tolist()

    except Exception as e:
        logger.error(f"[ERROR] Failed to generate embedding: {str(e)}")
        return None


def generate_all_embeddings(extracted_data: List[Dict]) -> Dict:
    """
    Generate embeddings for all offerings and requests
    """
    logger.info("=" * 80)
    logger.info("[START] Generating embeddings for all offerings and requests")
    logger.info("=" * 80)

    embeddings_data = {
        "offerings": [],
        "requests": []
    }

    # Generate embeddings for offerings
    logger.info("[INFO] Generating embeddings for offerings...")
    offering_count = 0
    for attendee in extracted_data:
        for offering in attendee["offerings"]:
            offering_count += 1
            logger.info(f"[PROGRESS] Offering {offering_count}: {offering[:80]}...")

            embedding = generate_embedding(offering)
            if embedding:
                embeddings_data["offerings"].append({
                    "attendee_id": attendee["id"],
                    "text": offering,
                    "embedding": embedding
                })
                logger.debug(f"[OK] Embedding added for offering {offering_count}")
            else:
                logger.warning(f"[WARN] Failed to generate embedding for offering {offering_count}")

            # Small delay
            time.sleep(0.3)

    # Generate embeddings for requests
    logger.info("")
    logger.info("[INFO] Generating embeddings for requests...")
    request_count = 0
    for attendee in extracted_data:
        for request in attendee["requests"]:
            request_count += 1
            logger.info(f"[PROGRESS] Request {request_count}: {request[:80]}...")

            embedding = generate_embedding(request)
            if embedding:
                embeddings_data["requests"].append({
                    "attendee_id": attendee["id"],
                    "text": request,
                    "embedding": embedding
                })
                logger.debug(f"[OK] Embedding added for request {request_count}")
            else:
                logger.warning(f"[WARN] Failed to generate embedding for request {request_count}")

            # Small delay
            time.sleep(0.3)

    # Save to JSON
    logger.info("")
    logger.info("=" * 80)
    logger.info(f"[START] Saving embeddings to {EMBEDDINGS_FILE}")

    try:
        with open(EMBEDDINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(embeddings_data, f, indent=2, ensure_ascii=False)
        logger.info(f"[OK] Saved embeddings successfully")
    except Exception as e:
        logger.error(f"[ERROR] Failed to save embeddings: {str(e)}")

    logger.info(f"[OK] Generated {len(embeddings_data['offerings'])} offering embeddings")
    logger.info(f"[OK] Generated {len(embeddings_data['requests'])} request embeddings")

    return embeddings_data


def analyze_results(extracted_data: List[Dict], embeddings_data: Dict):
    """
    Analyze and generate statistics on the extraction and embedding results
    """
    logger.info("=" * 80)
    logger.info("ANALYSIS AND STATISTICS")
    logger.info("=" * 80)

    total_attendees = len(extracted_data)
    attendees_with_offerings = sum(1 for a in extracted_data if a['offerings'])
    attendees_with_requests = sum(1 for a in extracted_data if a['requests'])

    total_offerings = sum(len(a['offerings']) for a in extracted_data)
    total_requests = sum(len(a['requests']) for a in extracted_data)

    offerings_per_person = [len(a['offerings']) for a in extracted_data if a['offerings']]
    requests_per_person = [len(a['requests']) for a in extracted_data if a['requests']]

    avg_offerings = sum(offerings_per_person) / len(offerings_per_person) if offerings_per_person else 0
    avg_requests = sum(requests_per_person) / len(requests_per_person) if requests_per_person else 0

    analysis = {
        "run_timestamp": RUN_TIMESTAMP,
        "sample_size": total_attendees,
        "attendees_with_offerings": attendees_with_offerings,
        "attendees_with_requests": attendees_with_requests,
        "total_offerings": total_offerings,
        "total_requests": total_requests,
        "avg_offerings_per_person": round(avg_offerings, 2),
        "avg_requests_per_person": round(avg_requests, 2),
        "max_offerings_per_person": max(offerings_per_person) if offerings_per_person else 0,
        "max_requests_per_person": max(requests_per_person) if requests_per_person else 0,
        "offering_embeddings_generated": len(embeddings_data['offerings']),
        "request_embeddings_generated": len(embeddings_data['requests']),
        "embedding_dimension": EMBEDDING_DIM
    }

    logger.info(f"[INFO] Attendees processed: {total_attendees}")
    logger.info(f"[INFO] Attendees with offerings: {attendees_with_offerings} ({attendees_with_offerings/total_attendees*100:.1f}%)")
    logger.info(f"[INFO] Attendees with requests: {attendees_with_requests} ({attendees_with_requests/total_attendees*100:.1f}%)")
    logger.info(f"[INFO] Total offerings extracted: {total_offerings}")
    logger.info(f"[INFO] Total requests extracted: {total_requests}")
    logger.info(f"[INFO] Average offerings per person: {avg_offerings:.2f}")
    logger.info(f"[INFO] Average requests per person: {avg_requests:.2f}")
    logger.info(f"[INFO] Offering embeddings generated: {len(embeddings_data['offerings'])}")
    logger.info(f"[INFO] Request embeddings generated: {len(embeddings_data['requests'])}")

    # Save analysis
    try:
        with open(ANALYSIS_FILE, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        logger.info(f"[OK] Saved analysis to {ANALYSIS_FILE}")
    except Exception as e:
        logger.error(f"[ERROR] Failed to save analysis: {str(e)}")

    # Show sample offerings and requests
    logger.info("")
    logger.info("Sample Offerings:")
    sample_offerings = []
    for a in extracted_data[:10]:
        if a['offerings']:
            sample_offerings.extend(a['offerings'][:2])

    for i, offering in enumerate(sample_offerings[:5], 1):
        logger.info(f"  {i}. {offering}")

    logger.info("")
    logger.info("Sample Requests:")
    sample_requests = []
    for a in extracted_data[:10]:
        if a['requests']:
            sample_requests.extend(a['requests'][:2])

    for i, request in enumerate(sample_requests[:5], 1):
        logger.info(f"  {i}. {request}")


def main():
    """Main execution flow"""
    start_time = time.time()

    try:
        # Step 1: Load CSV
        df = load_csv()

        # Step 2: Select random sample
        df_sample, sample_indices = select_random_sample(df, n=25)

        # Step 3: Extract offerings and requests
        extracted_data = process_sample_attendees(df_sample)

        # Step 4: Generate embeddings
        embeddings_data = generate_all_embeddings(extracted_data)

        # Step 5: Analyze results
        analyze_results(extracted_data, embeddings_data)

        # Final summary
        total_elapsed = time.time() - start_time
        logger.info("")
        logger.info("=" * 80)
        logger.info("PROCESSING COMPLETE")
        logger.info("=" * 80)
        logger.info(f"[OK] Total processing time: {total_elapsed/60:.2f} minutes")
        logger.info(f"[OK] Log file: {LOG_FILE}")
        logger.info(f"[OK] Extracted data: {EXTRACTED_DATA_FILE}")
        logger.info(f"[OK] Embeddings: {EMBEDDINGS_FILE}")
        logger.info(f"[OK] Analysis: {ANALYSIS_FILE}")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"[ERROR] Fatal error in main execution: {str(e)}")
        logger.exception("Full traceback:")
        raise


if __name__ == "__main__":
    main()
