"""
Utility script to inspect extracted data and embeddings
"""

import json
import os
from collections import Counter

DATA_DIR = "/home/claude/ea_data"
EXTRACTED_DATA_PATH = f"{DATA_DIR}/extracted_data.json"
EMBEDDINGS_PATH = f"{DATA_DIR}/embeddings.json"


def inspect_extracted_data():
    """Show statistics about extracted offerings and requests"""
    
    if not os.path.exists(EXTRACTED_DATA_PATH):
        print(f"❌ No extracted data found at {EXTRACTED_DATA_PATH}")
        print("Run the main script first: python ea_matching.py")
        return
    
    with open(EXTRACTED_DATA_PATH, 'r') as f:
        data = json.load(f)
    
    print("="*80)
    print("EXTRACTED DATA STATISTICS")
    print("="*80)
    
    total_attendees = len(data)
    attendees_with_offerings = sum(1 for a in data if a['offerings'])
    attendees_with_requests = sum(1 for a in data if a['requests'])
    
    total_offerings = sum(len(a['offerings']) for a in data)
    total_requests = sum(len(a['requests']) for a in data)
    
    offerings_per_person = [len(a['offerings']) for a in data if a['offerings']]
    requests_per_person = [len(a['requests']) for a in data if a['requests']]
    
    print(f"\n📊 Overall Stats:")
    print(f"   Total attendees: {total_attendees}")
    print(f"   Attendees with offerings: {attendees_with_offerings} ({attendees_with_offerings/total_attendees*100:.1f}%)")
    print(f"   Attendees with requests: {attendees_with_requests} ({attendees_with_requests/total_attendees*100:.1f}%)")
    
    print(f"\n📈 Offerings:")
    print(f"   Total offerings: {total_offerings}")
    print(f"   Avg per person: {sum(offerings_per_person)/len(offerings_per_person):.1f}")
    print(f"   Max per person: {max(offerings_per_person) if offerings_per_person else 0}")
    print(f"   Min per person: {min(offerings_per_person) if offerings_per_person else 0}")
    
    print(f"\n📋 Requests:")
    print(f"   Total requests: {total_requests}")
    print(f"   Avg per person: {sum(requests_per_person)/len(requests_per_person):.1f}")
    print(f"   Max per person: {max(requests_per_person) if requests_per_person else 0}")
    print(f"   Min per person: {min(requests_per_person) if requests_per_person else 0}")
    
    # Show some examples
    print(f"\n💡 Sample Offerings:")
    sample_offerings = []
    for a in data[:20]:
        if a['offerings']:
            sample_offerings.extend(a['offerings'][:2])
    
    for i, offering in enumerate(sample_offerings[:5], 1):
        print(f"   {i}. {offering[:100]}...")
    
    print(f"\n🙋 Sample Requests:")
    sample_requests = []
    for a in data[:20]:
        if a['requests']:
            sample_requests.extend(a['requests'][:2])
    
    for i, request in enumerate(sample_requests[:5], 1):
        print(f"   {i}. {request[:100]}...")


def inspect_embeddings():
    """Show statistics about embeddings"""
    
    if not os.path.exists(EMBEDDINGS_PATH):
        print(f"❌ No embeddings found at {EMBEDDINGS_PATH}")
        print("Run the main script first: python ea_matching.py")
        return
    
    with open(EMBEDDINGS_PATH, 'r') as f:
        data = json.load(f)
    
    print("\n" + "="*80)
    print("EMBEDDINGS STATISTICS")
    print("="*80)
    
    offering_embeddings = data['offerings']
    request_embeddings = data['requests']
    
    print(f"\n🔢 Embedding Stats:")
    print(f"   Total offering embeddings: {len(offering_embeddings)}")
    print(f"   Total request embeddings: {len(request_embeddings)}")
    
    if offering_embeddings:
        dim = len(offering_embeddings[0]['embedding'])
        print(f"   Embedding dimensions: {dim}")
    
    # Count by attendee
    offering_counts = Counter(e['attendee_id'] for e in offering_embeddings)
    request_counts = Counter(e['attendee_id'] for e in request_embeddings)
    
    print(f"\n👥 Coverage:")
    print(f"   Unique attendees with offering embeddings: {len(offering_counts)}")
    print(f"   Unique attendees with request embeddings: {len(request_counts)}")
    
    print(f"\n📏 Distribution:")
    print(f"   Attendees with most offerings: {offering_counts.most_common(3)}")
    print(f"   Attendees with most requests: {request_counts.most_common(3)}")


def search_attendee(name_query: str):
    """Search for a specific attendee and show their data"""
    
    if not os.path.exists(EXTRACTED_DATA_PATH):
        print(f"❌ No extracted data found")
        return
    
    with open(EXTRACTED_DATA_PATH, 'r') as f:
        data = json.load(f)
    
    name_query = name_query.lower()
    matches = []
    
    for a in data:
        full_name = f"{a['first_name']} {a['last_name']}".lower()
        if name_query in full_name:
            matches.append(a)
    
    if not matches:
        print(f"❌ No matches found for '{name_query}'")
        return
    
    if len(matches) > 1:
        print(f"\n🔍 Found {len(matches)} matches:")
        for i, m in enumerate(matches, 1):
            print(f"   {i}. {m['first_name']} {m['last_name']} - {m.get('company', 'N/A')}")
        
        choice = input("\nEnter number to view details (or 0 to cancel): ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(matches):
                attendee = matches[idx]
            else:
                return
        except:
            return
    else:
        attendee = matches[0]
    
    print("\n" + "="*80)
    print(f"ATTENDEE: {attendee['first_name']} {attendee['last_name']}")
    print("="*80)
    
    print(f"\n👤 Profile:")
    print(f"   Company: {attendee.get('company', 'N/A')}")
    print(f"   Title: {attendee.get('job_title', 'N/A')}")
    print(f"   Country: {attendee.get('country', 'N/A')}")
    
    if attendee.get('linkedin'):
        print(f"   LinkedIn: {attendee['linkedin']}")
    
    print(f"\n💼 Offerings ({len(attendee['offerings'])}):")
    for i, offering in enumerate(attendee['offerings'], 1):
        print(f"   {i}. {offering}")
    
    print(f"\n🙋 Requests ({len(attendee['requests'])}):")
    for i, request in enumerate(attendee['requests'], 1):
        print(f"   {i}. {request}")
    
    if attendee.get('biography'):
        print(f"\n📝 Biography:")
        print(f"   {attendee['biography'][:300]}...")


def main():
    """Main menu"""
    
    while True:
        print("\n" + "="*80)
        print("DATA INSPECTOR")
        print("="*80)
        print("\n1. Show extracted data statistics")
        print("2. Show embedding statistics")
        print("3. Search for specific attendee")
        print("4. Exit")
        
        choice = input("\nEnter choice (1-4): ").strip()
        
        if choice == "1":
            inspect_extracted_data()
        elif choice == "2":
            inspect_embeddings()
        elif choice == "3":
            name = input("Enter name to search: ").strip()
            search_attendee(name)
        elif choice == "4":
            break
        else:
            print("Invalid choice")


if __name__ == "__main__":
    main()
