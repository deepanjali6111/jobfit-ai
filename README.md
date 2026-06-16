# 🎯 JobFit AI — AI-Powered Resume Job Matcher

> Upload your resume → AI extracts your skills → Fetches real jobs → Scores each job against your profile → Shows ranked matches with match %, matching skills, missing skills, and apply links.

**Live Demo:** [jobfit-ai-ageu5ncxuncsjtcz8y5hpx.streamlit.app](https://jobfit-ai-ageu5ncxuncsjtcz8y5hpx.streamlit.app)

---

## 🏗️ Architecture
User → Streamlit Cloud → FastAPI (Google Cloud Run) → Gemini 2.5 Flash + JSearch API → Supabase
| Layer | Technology | Purpose |
|---|---|---|
| Frontend | Streamlit Cloud | UI, auth flow, results display |
| Backend | FastAPI + Google Cloud Run | REST API, JWT validation, business logic |
| AI | Google Gemini 2.5 Flash | Resume parsing, job scoring |
| Jobs | JSearch API (RapidAPI) | Real Indian job listings |
| Database | Supabase PostgreSQL | User profiles, job cache, match history |
| Auth | Supabase Auth | Email/password, JWT tokens |

---

## ✨ Features

- **Resume Parsing** — Upload PDF → Gemini extracts skills, role, experience
- **Real Job Listings** — Fetches live jobs from Indian job boards via JSearch
- **AI Job Scoring** — Gemini scores each job 0-100 against your resume
- **Smart Caching** — Same search returns cached results instantly (1 hour TTL)
- **Match Breakdown** — See exactly which skills match and which are missing
- **Multi-user** — Complete data isolation with Supabase RLS policies
- **Production Ready** — Load tested with Locust (50 concurrent users, 0% failure rate)

---

## 🚀 Tech Stack

**Backend:**
- FastAPI (Python)
- Google Cloud Run (deployment)
- PyMuPDF (PDF text extraction)
- google-genai (Gemini 2.5 Flash)
- httpx (async HTTP)
- Supabase Python SDK

**Frontend:**
- Streamlit
- Streamlit Community Cloud (deployment)

**Database & Auth:**
- Supabase PostgreSQL
- Row Level Security (RLS)
- Supabase Auth (JWT)

---

## 📁 Project Structure
jobfit-ai/

├── backend/

│   ├── main.py                 # FastAPI app, CORS, router registration

│   ├── Dockerfile              # Cloud Run container config

│   ├── requirements.txt

│   ├── routers/

│   │   ├── upload.py           # POST /upload — resume upload

│   │   ├── jobs.py             # GET /jobs — job search with caching

│   │   └── match.py            # POST /match — AI job scoring

│   ├── services/

│   │   ├── pdf_extractor.py    # PyMuPDF text extraction

│   │   ├── gemini_service.py   # Gemini API with key rotation

│   │   ├── job_fetcher.py      # JSearch API integration

│   │   └── matcher.py          # Job scoring logic

│   ├── db/

│   │   ├── client.py           # Supabase client + authenticated client

│   │   ├── resume_repo.py      # resume_profiles table operations

│   │   ├── cache_repo.py       # job_cache table operations

│   │   └── match_repo.py       # job_matches table operations

│   └── auth/

│       └── jwt_validator.py    # JWT validation dependency

├── frontend/

│   ├── streamlit_app.py        # Home page + auth guard

│   └── pages/

│       ├── 1_login.py          # Login + signup

│       ├── 2_upload.py         # Resume upload

│       ├── 3_search.py         # Job search

│       └── 4_results.py        # Ranked results

└── database/

└── schema.sql              # Supabase table definitions + RLS policies
---

## 🗄️ Database Schema

```sql
resume_profiles   -- One per user, RLS enabled
job_cache         -- Shared cache, RLS disabled, 1hr TTL
job_matches       -- Per-user match history, RLS enabled
```

---

## ⚙️ Local Setup

### Prerequisites
- Python 3.11+
- Supabase account
- Google AI Studio API key
- RapidAPI JSearch subscription (free tier)

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

Create `backend/.env`:
SUPABASE_URL=your_supabase_url

SUPABASE_ANON_KEY=your_anon_key

GEMINI_KEY_1=your_gemini_key

JSEARCH_API_KEY=your_rapidapi_key
```bash
python -m uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
pip install -r requirements.txt
```

Create `frontend/.streamlit/secrets.toml`:
```toml
SUPABASE_URL = "your_supabase_url"
SUPABASE_ANON_KEY = "your_anon_key"
FASTAPI_URL = "http://127.0.0.1:8000"
```

```bash
streamlit run streamlit_app.py
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Health check |
| POST | `/upload` | Upload PDF resume, extract profile |
| GET | `/jobs` | Fetch jobs with cache |
| POST | `/match` | Score jobs against resume |

---

## 📊 Performance

Load tested with Locust — 50 concurrent users:

| Endpoint | Median | Failures |
|---|---|---|
| GET / | 3ms | 0% |
| GET /jobs | ~20s* | 0% |
| POST /match | ~24s* | 0% |

*Latency is from external APIs (JSearch + Gemini), not server processing time.

---

## 🔒 Security

- JWT validation on every protected endpoint
- Supabase RLS — users can only access their own data
- API keys stored as environment variables, never committed
- `.env` and `secrets.toml` in `.gitignore`

---

## 👩‍💻 Author

**Deepanjali Yadav**
- GitHub: [@deepanjali6111](https://github.com/deepanjali6111)
