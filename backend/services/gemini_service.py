import os
import json
import time
from datetime import datetime, date

from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()


# ─────────────────────────────────────────────────────────────
# Load all available Gemini keys
# ─────────────────────────────────────────────────────────────

GEMINI_KEYS = [
    os.getenv("GEMINI_KEY_1"),
    os.getenv("GEMINI_KEY_2"),
    os.getenv("GEMINI_KEY_3"),
]

GEMINI_KEYS = [key for key in GEMINI_KEYS if key]

if not GEMINI_KEYS:
    raise ValueError("At least one GEMINI_KEY must be set in .env")


# ─────────────────────────────────────────────────────────────
# Gemini API call with key rotation
# ─────────────────────────────────────────────────────────────

def call_gemini(prompt: str) -> str:
    """
    Calls Gemini with API key rotation.

    Tries each key in order.
    If a key hits a rate/quota error, waits 5 seconds and
    tries the next available key.
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

            if (
                "429" in str(e)
                or "quota" in error_str
                or "rate" in error_str
            ):
                wait = 5 if i < len(GEMINI_KEYS) - 1 else 0

                if wait:
                    time.sleep(wait)

                continue

            raise e

    raise RuntimeError(
        "Daily AI quota reached. Results available again after midnight. "
        "Your resume profile is saved — just come back tomorrow."
    )


# ─────────────────────────────────────────────────────────────
# Date parsing helper
# ─────────────────────────────────────────────────────────────

def parse_year_month(value: str) -> date | None:
    """
    Converts YYYY-MM into a Python date.

    Example:
        "2025-11" -> date(2025, 11, 1)

    Returns None for invalid/empty values.
    """

    if not value:
        return None

    value = str(value).strip()

    try:
        parsed = datetime.strptime(
            value,
            "%Y-%m"
        )

        return parsed.date()

    except ValueError:
        return None


# ─────────────────────────────────────────────────────────────
# Calculate total professional experience
# ─────────────────────────────────────────────────────────────

def calculate_experience_years(
    employment_periods: list[dict]
) -> float:
    """
    Calculates total professional experience from employment periods.

    Each period should contain:

        {
            "start_date": "YYYY-MM",
            "end_date": "YYYY-MM" or "present"
        }

    Multiple overlapping periods are merged so that the same month
    is not counted twice.

    Example:

        Nov 2025 -> present
        = approximately 10 months as of Sep 2026
        = approximately 0.83 years
    """

    intervals = []

    today = date.today()

    for period in employment_periods:
        if not isinstance(period, dict):
            continue

        start_value = period.get("start_date", "")
        end_value = period.get("end_date", "")

        start_date = parse_year_month(start_value)

        if start_date is None:
            continue

        if str(end_value).strip().lower() == "present":
            end_date = today
        else:
            end_date = parse_year_month(end_value)

        if end_date is None:
            continue

        if end_date < start_date:
            continue

        # Convert dates to month numbers so we can calculate
        # experience at month precision.
        start_month = start_date.year * 12 + start_date.month
        end_month = end_date.year * 12 + end_date.month

        intervals.append((start_month, end_month))

    if not intervals:
        return 0.0

    # Sort intervals by start month
    intervals.sort(key=lambda x: x[0])

    # Merge overlapping or adjacent employment periods
    merged = []

    current_start, current_end = intervals[0]

    for next_start, next_end in intervals[1:]:
        if next_start <= current_end + 1:
            current_end = max(current_end, next_end)
        else:
            merged.append((current_start, current_end))
            current_start = next_start
            current_end = next_end

    merged.append((current_start, current_end))

    total_months = 0

    for start_month, end_month in merged:
        total_months += end_month - start_month

    return round(total_months / 12, 2)


# ─────────────────────────────────────────────────────────────
# Resume parsing
# ─────────────────────────────────────────────────────────────

def parse_resume_with_gemini(resume_text: str) -> dict:
    """
    Extracts resume information using Gemini.

    Gemini extracts:
        - skills
        - role
        - employment periods

    Python calculates:
        - experience_years
    """

    prompt = f"""
You are a resume parser.

Read the resume and extract the candidate's professional information.

Important:
Do NOT calculate total years of experience yourself.

Instead, identify every genuine professional employment period
and return its start and end dates.

Rules:

1. skills
   - Extract technical skills, programming languages, frameworks,
     libraries, databases, cloud technologies, APIs, tools,
     and other relevant technical technologies.
   - Do not invent skills.

2. role
   - Return the most suitable professional job title for the candidate.
   - Examples:
     "AI Engineer"
     "GenAI Engineer"
     "Python Developer"
     "Backend Engineer"

3. employment_periods
   - Extract actual professional employment.
   - Ignore:
       * education
       * academic projects
       * certifications
       * hackathons
       * achievements
       * college activities
   - Include internships only when clearly presented as professional
     work experience.
   - Use YYYY-MM format.
   - For an ongoing job, use "present".
   - Do not invent dates.
   - Extract ALL genuine employment periods.

Example:

If the resume contains:

Cognizant Technology Solutions
Nov 2025 – Present

return:

[
    {{
        "start_date": "2025-11",
        "end_date": "present"
    }}
]

If there is no professional work experience, return an empty list.

Resume:
{resume_text}
"""

    # Structured output schema
    response_schema = {
        "type": "OBJECT",
        "properties": {
            "skills": {
                "type": "ARRAY",
                "items": {
                    "type": "STRING"
                }
            },
            "role": {
                "type": "STRING"
            },
            "employment_periods": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "start_date": {
                            "type": "STRING"
                        },
                        "end_date": {
                            "type": "STRING"
                        }
                    },
                    "required": [
                        "start_date",
                        "end_date"
                    ]
                }
            }
        },
        "required": [
            "skills",
            "role",
            "employment_periods"
        ]
    }

    last_error = None

    for i, key in enumerate(GEMINI_KEYS):
        try:
            client = genai.Client(api_key=key)

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=response_schema
                )
            )

            raw = response.text.strip()

            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                raise ValueError(
                    f"Gemini returned invalid structured JSON: {raw[:500]}"
                )

            break

        except Exception as e:
            last_error = e
            error_str = str(e).lower()

            if (
                "429" in str(e)
                or "quota" in error_str
                or "rate" in error_str
            ):
                wait = 5 if i < len(GEMINI_KEYS) - 1 else 0

                if wait:
                    time.sleep(wait)

                continue

            raise e

    else:
        raise RuntimeError(
            "Daily AI quota reached. Results available again after midnight. "
            "Your resume profile is saved — just come back tomorrow."
        )

    # Validate required fields
    if "skills" not in parsed:
        raise ValueError(
            f"Gemini response missing skills: {parsed}"
        )

    if "role" not in parsed:
        raise ValueError(
            f"Gemini response missing role: {parsed}"
        )

    if "employment_periods" not in parsed:
        raise ValueError(
            f"Gemini response missing employment periods: {parsed}"
        )

    # Ensure correct types
    if not isinstance(parsed["skills"], list):
        parsed["skills"] = []

    if not isinstance(parsed["employment_periods"], list):
        parsed["employment_periods"] = []

    # ─────────────────────────────────────────────────────────
    # Calculate experience in Python
    # ─────────────────────────────────────────────────────────

    experience_years = calculate_experience_years(
        parsed["employment_periods"]
    )

    parsed["experience_years"] = experience_years

    # Useful temporary backend diagnostic
    print(
        "Resume experience extraction:",
        parsed["employment_periods"],
        "=>",
        experience_years,
        "years"
    )

    return parsed


# ─────────────────────────────────────────────────────────────
# Job matching
# ─────────────────────────────────────────────────────────────

def match_job_with_gemini(
    resume_profile: dict,
    job: dict
) -> dict:
    """
    Scores a single job against the resume profile.
    """

    prompt = f"""
You are a job match analyzer.

Given this candidate profile and job description,
return a match score.

Candidate profile:

- Skills:
{', '.join(resume_profile.get('extracted_skills', []))}

- Role:
{resume_profile.get('target_role', '')}

- Experience:
{resume_profile.get('experience_years', 0)} years


Job:

- Title:
{job.get('title', '')}

- Company:
{job.get('company', '')}

- Description:
{job.get('description', '')[:1000]}


Return ONLY a valid JSON object with exactly these fields:

{{
    "score": <integer 0-100>,
    "matching_skills": ["skill1", "skill2", "..."],
    "missing_skills": ["skill1", "skill2", "..."]
}}

Rules:

- score:
  0 = no match
  100 = perfect match

- matching_skills:
  Skills from the candidate that match the job requirements.

- missing_skills:
  Skills the job wants that the candidate does not have.

- Return ONLY the JSON object.
- No explanation.
- No markdown.
"""

    raw = call_gemini(prompt)

    raw = raw.strip()

    if raw.startswith("```"):
        parts = raw.split("```")

        if len(parts) >= 2:
            raw = parts[1]

            if raw.startswith("json"):
                raw = raw[4:]

    raw = raw.strip()

    try:
        parsed = json.loads(raw)

    except json.JSONDecodeError:
        return {
            "score": 0,
            "matching_skills": [],
            "missing_skills": []
        }

    try:
        parsed["score"] = int(parsed.get("score", 0))
    except (ValueError, TypeError):
        parsed["score"] = 0

    if not isinstance(
        parsed.get("matching_skills"),
        list
    ):
        parsed["matching_skills"] = []

    if not isinstance(
        parsed.get("missing_skills"),
        list
    ):
        parsed["missing_skills"] = []

    return parsed
