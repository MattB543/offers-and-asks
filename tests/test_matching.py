"""
Quick test script to validate the EA matching system on just 5 attendees
Run this first before processing all 5000!
"""

import os
import json
from ea_matching import (
    load_csv, 
    process_all_attendees, 
    generate_all_embeddings,
    search_by_custom_request,
    search_by_custom_offering,
    display_matches
)

# Override paths for test data
TEST_DATA_DIR = "/home/claude/ea_data_test"
os.makedirs(TEST_DATA_DIR, exist_ok=True)

def test_quick_run():
    """Test the system with just 5 attendees"""
    print("="*80)
    print("QUICK TEST: Processing first 5 attendees")
    print("="*80)
    
    # Load CSV
    df = load_csv()
    
    # Take only first 5 attendees
    df_test = df.head(5)
    print(f"\nUsing {len(df_test)} test attendees")
    
    # Temporarily override paths
    import ea_matching
    original_extracted = ea_matching.EXTRACTED_DATA_PATH
    original_embeddings = ea_matching.EMBEDDINGS_PATH
    
    ea_matching.EXTRACTED_DATA_PATH = f"{TEST_DATA_DIR}/extracted_data.json"
    ea_matching.EMBEDDINGS_PATH = f"{TEST_DATA_DIR}/embeddings.json"
    
    # Process
    print("\n--- Step 1: Extracting offerings and requests ---")
    extracted_data = process_all_attendees(df_test, force_refresh=True)
    
    print("\n--- Step 2: Generating embeddings ---")
    embeddings_data = generate_all_embeddings(extracted_data, force_refresh=True)
    
    # Restore paths
    ea_matching.EXTRACTED_DATA_PATH = original_extracted
    ea_matching.EMBEDDINGS_PATH = original_embeddings
    
    # Test a search
    print("\n--- Step 3: Testing a custom request search ---")
    test_request = "I need help with AI safety research and policy"
    matches = search_by_custom_request(test_request, extracted_data, embeddings_data)
    display_matches(matches, f"Test: People who can help with: {test_request}")
    
    print("\n" + "="*80)
    print("✅ TEST COMPLETED SUCCESSFULLY!")
    print("="*80)
    print("\nIf this looks good, run the full script with: python ea_matching.py")
    

if __name__ == "__main__":
    test_quick_run()
