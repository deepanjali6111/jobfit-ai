import os
import json
import time
from datetime import datetime, date

from google import genai
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

GEMINI_KEYS = [k for k in GEMINI_KEYS if k]

if not GEMINI_KEYS:
    raise ValueError("At least one GEMINI_KEY must be set in .env")


# ─────────────────────────────────────────────────────────────
# Gemini API call with key rotation
# ─────────────────────────────────────────────────────────────

def call_gemini(prompt: str) -> str:
    """
    Calls Gemini with key rotation.

    Tries each available key in order.
    On rate-limit/quota errors, waits 5 seconds before trying
    the next key.
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


# ─────────────────────────────────────────────────────────────
# Calculate experience from employment dates
# ─────────────────────────────────────────────────────────────

def calculate_experience_years(
    experience_start: str,
    experience_end: str
) -> float:
    """
    Calculates professional experience in decimal years.

    Examples:
        6 months  -> 0.50
        10 months -> 0.83
        1 year    -> 1.00
        1 year 6 months -> 1.50

    Expected date format:
        YYYY-MM

    For ongoing employment:
        experience_end = "present"
    """

    if not experience_start:
        return 0.0

    try:
        start_date = datetime.strptime(
            experience_start,
            "%Y-%m"
        ).date()

        if str(experience_end).strip().lower() == "present":
            end_date = date.today()

        else:
            end_date = datetime.strptime(
                experience_end,
                "%Y-%m"
            ).date()

        if end_date < start_date:
            return 0.0

        months = (
            (end_date.year - start_date.year) * 12
            + (end_date.month - start_date.month)
        )

        return round(months / 12, 2)

    except (ValueError, TypeError):
        return 0.0


# ─────────────────────────────────────────────────────────────
# Resume parsing
# ─────────────────────────────────────────────────────────────

def parse_resume_with_gemini(resume_text: str) -> dict:
    """
    Extracts structured information from a resume.

    Gemini extracts:
        - skills
        - role
        - employment start date
        - employment end date

    Python calculates:
        - experience_years
    """

    prompt = f"""
You are a resume parser.

Extract information from the resume below.

Return ONLY a valid JSON object with exactly these fields:

{{
    "skills": ["skill1", "skill2", "..."],
    "role": "most suitable job title for this person",
    "experience_start": "YYYY-MM",
    "experience_end": "YYYY-MM"
}}

Rules:

- skills:
  Extract technical skills, programming languages, frameworks,
  libraries, tools, databases, cloud technologies, APIs,
  and relevant technical technologies.

- role:
  Choose the most suitable professional job title for the candidate.
  Examples:
  "AI Engineer"
  "GenAI Engineer"
  "Python Developer"
  "Backend Engineer"
  "Data Analyst"

- experience_start:
  Extract the start date of the candidate's professional employment.
  Use YYYY-MM format.

- experience_end:
  Extract the end date of the candidate's latest/current professional
  employment.
  Use YYYY-MM format.

- If the latest job is still ongoing, use:
  "present"

- Ignore:
  internships,
  academic projects,
  college activities,
  certifications,
  education,
  hackathons,
  and achievements
  when calculating professional employment dates.

- Use the employment dates written in the resume.
  Do not estimate or invent dates.

- If the candidate has no professional work experience:
  "experience_start": "",
  "experience_end": ""

- Return ONLY the JSON object.
- Do not return markdown.
- Do not return ```json.
- Do not add explanations.

Resume:
{resume_text}
"""

    raw = call_gemini(prompt)

    raw = raw.strip()

    # Handle accidental markdown code fences anyway
    if raw.startswith("```"):

        parts = raw.split("```")

        if len(parts) >= 2:
            raw = parts[1]

            if raw.startswith("json"):
                raw = raw[4:]

    raw = raw.strip()

    # Parse JSON
    try:

        parsed = json.loads(raw)

    except json.JSONDecodeError:

        raise ValueError(
            f"Gemini returned invalid JSON: {raw[:500]}"
        )

    # Validate required fields
    if "skills" not in parsed or "role" not in parsed:
        raise ValueError(
            f"Gemini response missing required fields: {parsed}"
        )

    # Make sure optional date fields exist
    experience_start = parsed.get(
        "experience_start",
        ""
    )

    experience_end = parsed.get(
        "experience_end",
        ""
    )

    # Calculate experience in Python
    # instead of trusting Gemini to calculate it.
    experience_years = calculate_experience_years(
        experience_start,
        experience_end
    )

    parsed["experience_years"] = experience_years

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
    Used in the /match endpoint.
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

    # Safely convert score
    try:
        parsed["score"] = int(parsed.get("score", 0))
    except (ValueError, TypeError):
        parsed["score"] = 0

    return parsed
