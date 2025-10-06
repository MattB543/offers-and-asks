# EA Global Attendee Matching System

AI-powered matching system to help EA Global NYC 2025 attendees find the best connections based on their skills, expertise, and needs.

## 🌟 Features

- 🤖 **AI-Powered Extraction**: Uses Gemini 2.5 Pro to extract structured offerings and requests from attendee profiles
- 🔍 **Semantic Search**: Gemini embeddings (1536 dimensions) with pgvector for high-quality similarity matching
- 🎯 **Smart Re-ranking**: LLM-based re-ranking for highest quality matches
- ⚡ **Pre-computed Matches**: Instant username lookup with pre-computed top 50 matches
- 🔄 **Bidirectional Matching**: Find both who can help you AND who you can help
- 🌐 **Web Interface**: Modern Vue.js app with Supabase backend
- 📊 **Quality Filtering**: Only processes complete profiles (biography >50 chars, both help fields >20 chars)

## 📋 Architecture

```
┌─────────────────┐
│   CSV Data      │  Raw attendee data from Swapcard
│   (5000+ rows)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Filtering     │  Extract complete profiles (~575 attendees)
│ check_complete_ │  check_complete_profiles.py
│   profiles.py   │  extract_filtered_attendees.py
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Embeddings    │  Generate 1536-dim embeddings for all offerings/requests
│   Generation    │  generate_embeddings_filtered.py
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Supabase      │  Upload to PostgreSQL with pgvector
│    Upload       │  upload_filtered_to_supabase.py
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Pre-compute    │  Compute top 50 matches for each request/offering
│    Matches      │  precompute_matches_filtered.py
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Web App       │  Vue.js + Supabase Edge Functions
│  (Production)   │  Instant search, no real-time LLM calls
└─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

1. **Python 3.10+** with pip
2. **Node.js 18+** and npm (for web app)
3. **Gemini API Key**: Get from [Google AI Studio](https://aistudio.google.com/app/apikey)
4. **Supabase Account**: Sign up at [supabase.com](https://supabase.com)

### Environment Setup

Create a `.env` file:

```bash
# Gemini API
GEMINI_API_KEY=your-gemini-api-key

# Supabase
SUPABASE_URL=your-supabase-project-url
SUPABASE_SERVICE_KEY=your-supabase-service-key
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Install Node dependencies (for web app):

```bash
npm install
```

## 📊 Data Processing Pipeline

### Step 1: Check Profile Completeness

See how many attendees have complete profiles:

```bash
python check_complete_profiles.py
```

**Criteria:**

- Biography > 50 characters
- "How Others Can Help Me" > 20 characters
- "How I Can Help Others" > 20 characters

**Output**: Statistics showing ~575 attendees meet criteria (~11% of total)

### Step 2: Extract Offerings & Requests

Extract structured data for complete profiles only:

```bash
python extract_filtered_attendees.py
```

**What it does:**

- Loads CSV and filters for complete profiles
- For each attendee, uses Gemini 2.5 Pro to extract:
  - **Offerings**: Distinct skills, expertise, mentorship, connections
  - **Requests**: Specific needs, asks, collaboration opportunities
- Saves to `outputs/extracted_data/TIMESTAMP_filtered_575_attendees.json`

⏱️ **Time**: ~30-45 minutes (575 LLM calls)  
💰 **Cost**: ~$5-8

### Step 3: Generate Embeddings

Generate semantic embeddings for all offerings and requests:

```bash
python generate_embeddings_filtered.py
```

**What it does:**

- Loads extracted data from Step 2
- Generates 1536-dim embeddings for each offering and request
- Normalizes embeddings for cosine similarity
- Saves to `outputs/embeddings/TIMESTAMP_filtered_575_embeddings.json`

⏱️ **Time**: ~15-20 minutes (~2000+ embeddings)  
💰 **Cost**: ~$1-2

### Step 4: Upload to Supabase

Upload processed data to your Supabase database:

```bash
python upload_filtered_to_supabase.py
```

**What it does:**

- Finds latest extraction and embeddings files
- Uploads to three tables:
  - `attendees`: Basic profile info
  - `offerings`: Offerings with embeddings
  - `requests`: Requests with embeddings
- Uses batch inserts for efficiency

⏱️ **Time**: ~2-3 minutes

**Note**: Run the database migration first:

```sql
-- In Supabase SQL Editor, run: supabase/schema.sql
```

### Step 5: Pre-compute Matches

Pre-compute top 50 matches for instant lookup:

```bash
python precompute_matches_filtered.py
```

**What it does:**

- Generates synthetic offerings for all requests
- Computes top 50 matches for each request → offerings
- Computes top 50 matches for each offering → requests
- Stores in match tables for instant lookup
- No LLM calls needed during username search!

⏱️ **Time**: ~30-45 minutes  
💰 **Cost**: ~$5-8 (for synthetic offerings)

**Run the match migration first:**

```sql
-- In Supabase SQL Editor: supabase/precomputed_matches_migration.sql
```

## 🌐 Web Application

### Local Development

Start the development server:

```bash
npm run dev
```

Access at `http://localhost:5173`

### Production Build

Build for production:

```bash
npm run build
```

Deploy the `dist/` folder to Vercel, Netlify, or Cloudflare Pages.

### Deploy Supabase Functions

```bash
supabase functions deploy search-by-username
supabase functions deploy search-by-request
supabase functions deploy search-by-offering
supabase functions deploy get-attendees
```

## 🔍 Search Methods

### 1. Username Search (Bidirectional)

Find matches for a specific attendee:

**Web App**: Type name in search bar  
**CLI**: `python test_cli_search.py username "John Smith"`

Returns:

- **People who can help you**: Based on your requests → their offerings
- **People you can help**: Based on your offerings → their requests

⚡ **Speed**: ~1-2 seconds (instant database lookup + LLM re-ranking)

### 2. Custom Request Search

Find people who can fulfill a custom need:

**Web App**: Select "Request" and enter your need  
**CLI**: `python test_cli_search.py request "I need AI safety mentorship"`

Returns: Top 25 people whose offerings match your request

### 3. Custom Offering Search

Find people who need what you can offer:

**Web App**: Select "Offering" and enter what you offer  
**CLI**: `python test_cli_search.py offering "I can mentor on policy careers"`

Returns: Top 25 people whose requests match your offering

## 🧠 Matching Algorithm

### For Username Search (Pre-computed)

1. **Lookup**: Fetch pre-computed top 50 matches from database (instant)
2. **LLM Re-ranking**: Send to Gemini 2.5 Pro for quality filtering
3. **Return**: Top 25 highest-quality matches

### For Custom Requests

1. **Synthetic Offering**: Convert request → synthetic offering using LLM
   - "Need AI safety mentor" → "I can provide AI safety mentorship"
2. **Embedding**: Generate embedding for synthetic offering
3. **Vector Search**: Find top 50 similar offerings using pgvector
4. **LLM Re-ranking**: Filter and re-rank to top 25
5. **Return**: Final matches with attendee details

### For Custom Offerings

1. **Embedding**: Generate embedding for offering
2. **Vector Search**: Find top 50 similar request synthetic offerings using pgvector
3. **LLM Re-ranking**: Filter and re-rank to top 25
4. **Return**: Final matches with attendee details

## 📁 Project Structure

```
.
├── input/                                    # CSV data
│   └── [Do not share...] Attendee Data.csv
│
├── outputs/                                  # Generated data
│   ├── extracted_data/
│   │   └── TIMESTAMP_filtered_575_attendees.json
│   ├── embeddings/
│   │   └── TIMESTAMP_filtered_575_embeddings.json
│   └── filtered_attendee_ids.json
│
├── Python Scripts (Data Processing)
│   ├── check_complete_profiles.py           # Step 1: Check completeness
│   ├── extract_filtered_attendees.py        # Step 2: Extract data
│   ├── generate_embeddings_filtered.py      # Step 3: Generate embeddings
│   ├── upload_filtered_to_supabase.py       # Step 4: Upload to DB
│   ├── precompute_matches_filtered.py       # Step 5: Pre-compute matches
│   ├── ea_matching.py                       # Original CLI script (legacy)
│   └── test_cli_search.py                   # CLI testing tool
│
├── src/                                      # Vue.js frontend
│   ├── App.vue
│   ├── components/
│   │   ├── SearchBar.vue
│   │   ├── ResultsList.vue
│   │   └── ProfileCard.vue
│   ├── views/
│   │   ├── SearchView.vue
│   │   └── AboutView.vue
│   └── composables/
│       └── useSupabase.ts
│
├── supabase/                                 # Supabase backend
│   ├── schema.sql                           # Database schema + pgvector
│   ├── precomputed_matches_migration.sql    # Match tables
│   └── functions/
│       ├── search-by-username/              # Bidirectional search
│       ├── search-by-request/               # Custom request search
│       ├── search-by-offering/              # Custom offering search
│       └── get-attendees/                   # List attendees
│
├── requirements.txt                          # Python dependencies
├── package.json                              # Node dependencies
└── README.md                                 # This file
```

## ⚙️ Configuration

### Python Scripts

Edit models in script headers:

```python
LLM_MODEL = "gemini-2.5-pro"              # Extraction & re-ranking
EMBEDDING_MODEL = "gemini-embedding-001"  # Embeddings
EMBEDDING_DIM = 1536                       # Embedding dimensions
```

### Filtering Criteria

Adjust in `precompute_matches_filtered.py`:

```bash
python precompute_matches_filtered.py --min-bio-length 50 --require-company-info
```

## 💰 Cost Breakdown

| Stage              | Operations                 | Time           | Cost       |
| ------------------ | -------------------------- | -------------- | ---------- |
| Extraction         | ~575 LLM calls             | 30-45 min      | $5-8       |
| Embeddings         | ~2000+ embeddings          | 15-20 min      | $1-2       |
| Pre-compute        | ~575 LLM calls (synthetic) | 30-45 min      | $5-8       |
| **One-time Setup** |                            | **~1.5 hours** | **$11-18** |
| Username Search    | LLM re-rank only           | ~1-2 sec       | $0.01      |
| Custom Search      | Embed + LLM re-rank        | ~2-3 sec       | $0.02-0.05 |

## 🧪 Testing

### CLI Testing

Test username search:

```bash
python test_cli_search.py username "John Smith"
```

Test custom request:

```bash
python test_cli_search.py request "Need AI safety mentorship"
```

Test custom offering:

```bash
python test_cli_search.py offering "Can help with nonprofit operations"
```

### Unit Tests

Run test suite:

```bash
python -m pytest tests/
```

## 🐛 Troubleshooting

**"No attendees meet filtering criteria"**

- Check CSV path in script
- Verify skiprows value (should be 4 or 8 depending on CSV format)
- Lower `--min-bio-length` flag

**"Failed to generate embedding"**

- Check Gemini API key in `.env`
- Verify API quota/rate limits
- Add retry logic with exponential backoff

**"Database error"**

- Ensure migrations are run in correct order
- Check Supabase service key permissions
- Verify pgvector extension is enabled

## 📚 Documentation

See `claude/` directory for detailed docs:

- `QUICKSTART.md` - Getting started guide
- `PRECOMPUTED_MATCHING.md` - Pre-computation deep dive
- `db_schema.md` - Database schema details
- `DEPLOYMENT.md` - Production deployment guide

## 🤝 Contributing

This is a private event tool. For questions or improvements, contact the maintainer.

## 📄 License

See LICENSE file.
