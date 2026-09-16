import os
import json
import time
from datetime import date
from google import genai
from dotenv import load_dotenv

load_dotenv()

# ── Load all available Gemini keys ───────────────────────────
GEMINI_KEYS = [
    os.getenv("GEMINI_KEY_1"),
    os.getenv("GEMINI_KEY_2"),
    os.getenv("GEMINI_KEY_3"),
]
GEMINI_KEYS = [k for k in GEMINI_KEYS if k]

if not GEMINI_KEYS:
    raise ValueError("At least one GEMINI_KEY must be set in .env")


def call_gemini(prompt: str) -> str:
    """
    Calls Gemini with key rotation.
    Tries each key in order, waits 5s before moving to next on rate limit.
    """
    last_error = None

    for i, key in enumerate(GEMINI_KEYS):
        try:
            client = genai.Client(api_key=key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            return response.text

        except Exception as e:
            last_error = e
            error_str = str(e).lower()

            if "429" in str(e) or "quota" in error_str or "rate" in error_str:
                wait = 5 if i < len(GEMINI_KEYS) - 1 else 0
                if wait:
                    time.sleep(wait)
                continue

            raise e

    raise RuntimeError(
        "Daily AI quota reached. Results available again after midnight. "
        "Your resume profile is saved — just come back tomorrow."
    )


def parse_resume_with_gemini(resume_text: str) -> dict:
    """
    Sends resume text to Gemini and extracts structured profile.

    Returns:
        {
            "skills": ["Python", "FastAPI", ...],
            "role": "Backend Engineer",
            "experience_years": 2
        }
    """
    # Anchor "today" explicitly — Gemini can't reliably know the current
    # date on its own, so date-math (start date → now) needs this passed in.
    current_date = date.today().isoformat()

    prompt = f"""
You are a resume parser. Extract information from the resume below.

TODAY'S DATE IS: {current_date}

Return ONLY a valid JSON object with exactly these fields:
{{
    "skills": ["skill1", "skill2", ...],
    "role": "most suitable job title for this person",
    "experience_years": <number>
}}

Rules:
- skills: list of technical skills, tools, frameworks, languages only
- role: a specific job title like "Python Developer" or "GenAI Engineer"
- experience_years: follow these rules strictly, in this priority order:
  1. First, look at the work experience / internship section for explicit
     date ranges (e.g. "Nov 2024 – Present", "Jan 2023 – Jun 2023",
     "March 2022 - Current").
     - For any entry ending in "Present" / "Current" / "Ongoing", calculate
       the exact duration by computing the difference between that entry's
       START DATE and TODAY'S DATE ({current_date}) given above.
     - For past (non-current) roles with both a start and end date,
       calculate the duration between those two dates directly.
     - If there are multiple such entries, sum their durations (treat
       overlapping periods as counted once, not double-counted).
  2. If NO explicit date range can be found anywhere in the resume, but the
     resume explicitly states a duration in words (e.g. "10 months of
     experience", "1.5 years experience", "6-month internship"), use that
     stated duration directly instead of defaulting to 0. Do not assume
     "fresher" just because dates are missing — only use 0 if there is
     truly no experience of any kind mentioned (no dates AND no stated
     duration AND no job/internship history at all).
  3. Convert the final duration to decimal years, rounded to 2 decimal
     places (e.g. 10 months = 0.83, 1 year 6 months = 1.5, 2 years = 2.0).
  * Always return a number, never a string
- Return ONLY the JSON object, no explanation, no markdown, no extra text

Resume:
{resume_text}
"""

    raw = call_gemini(prompt)

    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        raise ValueError(f"Gemini returned invalid JSON: {raw[:200]}")

    if "skills" not in parsed or "role" not in parsed:
        raise ValueError(f"Gemini response missing required fields: {parsed}")

    # Safely convert experience to float then store as float
    try:
        parsed["experience_years"] = float(parsed.get("experience_years", 0))
    except (ValueError, TypeError):
        parsed["experience_years"] = 0.0

    return parsed


def match_job_with_gemini(resume_profile: dict, job: dict) -> dict:
    """
    Scores a single job against the resume profile.
    Used in Milestone 4 — GET /match endpoint.
    """
    prompt = f"""
You are a job match analyzer.

Given this candidate profile and job description, return a match score.

Candidate profile:
- Skills: {', '.join(resume_profile.get('extracted_skills', []))}
- Role: {resume_profile.get('target_role', '')}
- Experience: {resume_profile.get('experience_years', 0)} years

Job:
- Title: {job.get('title', '')}
- Company: {job.get('company', '')}
- Description: {job.get('description', '')[:1000]}

Return ONLY a valid JSON object with exactly these fields:
{{
    "score": <integer 0-100>,
    "matching_skills": ["skill1", "skill2", ...],
    "missing_skills": ["skill1", "skill2", ...]
}}

Rules:
- score: 0 = no match, 100 = perfect match
- matching_skills: skills from candidate that match job requirements
- missing_skills: skills the job wants that candidate doesn't have
- Return ONLY the JSON object, no explanation, no markdown, no extra text
"""

    raw = call_gemini(prompt)

    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {"score": 0, "matching_skills": [], "missing_skills": []}

    parsed["score"] = int(parsed.get("score", 0))
    return parsed
