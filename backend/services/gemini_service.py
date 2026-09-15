import os
import json
import time
import re
from datetime import datetime, date

from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()


# ─────────────────────────────────────────────────────────────
# Gemini API keys
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
# Parse YYYY-MM
# ─────────────────────────────────────────────────────────────

def parse_year_month(value: str) -> date | None:
    """
    Converts YYYY-MM into a Python date.
    """

    if not value:
        return None

    value = str(value).strip()

    try:
        return datetime.strptime(value, "%Y-%m").date()
    except ValueError:
        return None


# ─────────────────────────────────────────────────────────────
# Convert month names to YYYY-MM
# ─────────────────────────────────────────────────────────────

def normalize_month_date(value: str) -> str:
    """
    Converts common date formats into YYYY-MM.

    Examples:
        Nov 2025       -> 2025-11
        November 2025  -> 2025-11
        11/2025        -> 2025-11
        2025-11        -> 2025-11
    """

    if not value:
        return ""

    value = str(value).strip()

    if value.lower() == "present":
        return "present"

    formats = [
        "%Y-%m",
        "%b %Y",
        "%B %Y",
        "%m/%Y",
        "%m-%Y",
    ]

    for fmt in formats:
        try:
            parsed = datetime.strptime(value, fmt)
            return parsed.strftime("%Y-%m")
        except ValueError:
            continue

    return ""


# ─────────────────────────────────────────────────────────────
# Detect employment dates directly from resume text
# ─────────────────────────────────────────────────────────────

def extract_employment_periods_from_text(
    resume_text: str
) -> list[dict]:
    """
    Deterministic fallback for employment dates.

    Looks for patterns such as:

        Nov 2025 - Present
        Nov 2025 – Present
        November 2025 - Present
        Nov 2025 to Present
        Nov 2025 - Sep 2026
    """

    text = resume_text.replace("–", "-").replace("—", "-")

    month_pattern = (
        r"(Jan(?:uary)?|"
        r"Feb(?:ruary)?|"
        r"Mar(?:ch)?|"
        r"Apr(?:il)?|"
        r"May|"
        r"Jun(?:e)?|"
        r"Jul(?:y)?|"
        r"Aug(?:ust)?|"
        r"Sep(?:tember)?|"
        r"Oct(?:ober)?|"
        r"Nov(?:ember)?|"
        r"Dec(?:ember)?)"
    )

    date_pattern = rf"{month_pattern}\s+\d{{4}}"

    range_pattern = rf"({date_pattern})\s*(?:-|to)\s*(Present|{date_pattern})"

    matches = re.findall(
        range_pattern,
        text,
        flags=re.IGNORECASE
    )

    periods = []

    for start_value, end_value in matches:

        start_normalized = normalize_month_date(
            start_value
        )

        end_normalized = normalize_month_date(
            end_value
        )

        if start_normalized:

            periods.append(
                {
                    "start_date": start_normalized,
                    "end_date": end_normalized
                }
            )

    return periods


# ─────────────────────────────────────────────────────────────
# Calculate professional experience
# ─────────────────────────────────────────────────────────────

def calculate_experience_years(
    employment_periods: list[dict]
) -> float:
    """
    Calculates total professional experience.

    Overlapping employment periods are merged so that
    the same months are not counted twice.
    """

    intervals = []

    today = date.today()

    for period in employment_periods:

        if not isinstance(period, dict):
            continue

        start_value = normalize_month_date(
            period.get("start_date", "")
        )

        end_value = normalize_month_date(
            period.get("end_date", "")
        )

        start_date = parse_year_month(start_value)

        if start_date is None:
            continue

        if end_value == "present":
            end_date = today
        else:
            end_date = parse_year_month(end_value)

        if end_date is None:
            continue

        if end_date < start_date:
            continue

        start_month = (
            start_date.year * 12
            + start_date.month
        )

        end_month = (
            end_date.year * 12
            + end_date.month
        )

        intervals.append(
            (start_month, end_month)
        )

    if not intervals:
        return 0.0

    intervals.sort(key=lambda x: x[0])

    merged = []

    current_start, current_end = intervals[0]

    for next_start, next_end in intervals[1:]:

        if next_start <= current_end + 1:

            current_end = max(
                current_end,
                next_end
            )

        else:

            merged.append(
                (current_start, current_end)
            )

            current_start = next_start
            current_end = next_end

    merged.append(
        (current_start, current_end)
    )

    total_months = 0

    for start_month, end_month in merged:

        total_months += (
            end_month - start_month
        )

    return round(
        total_months / 12,
        2
    )


# ─────────────────────────────────────────────────────────────
# Resume parser
# ─────────────────────────────────────────────────────────────

def parse_resume_with_gemini(
    resume_text: str
) -> dict:

    prompt = f"""
You are a resume parser.

Extract the candidate's professional information.

Return ONLY valid JSON matching this structure:

{{
    "skills": ["skill1", "skill2"],
    "role": "most suitable professional job title",
    "employment_periods": [
        {{
            "start_date": "YYYY-MM",
            "end_date": "YYYY-MM or present"
        }}
    ]
}}

Rules:

1. skills
   Extract technical skills, programming languages, frameworks,
   libraries, databases, APIs, cloud technologies and tools.

2. role
   Return the most suitable professional title.

3. employment_periods
   Extract ALL genuine professional employment periods.

   IMPORTANT:
   - Look specifically at the EXPERIENCE / WORK EXPERIENCE section.
   - Do not use education dates.
   - Do not use project dates.
   - Do not use certification dates.
   - Do not use achievement dates.
   - Do not calculate total experience.
   - Extract the dates exactly from the resume.
   - Convert dates to YYYY-MM.
   - Use "present" for ongoing employment.

Example:

"Cognizant Technology Solutions
Nov 2025 - Present"

must produce:

[
    {{
        "start_date": "2025-11",
        "end_date": "present"
    }}
]

Resume:
{resume_text}
"""

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

    parsed = None

    for i, key in enumerate(GEMINI_KEYS):

        try:

            client = genai.Client(
                api_key=key
            )

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=response_schema
                )
            )

            raw = response.text.strip()

            parsed = json.loads(raw)

            break

        except Exception as e:

            error_str = str(e).lower()

            if (
                "429" in str(e)
                or "quota" in error_str
                or "rate" in error_str
            ):

                if i < len(GEMINI_KEYS) - 1:
                    time.sleep(5)
                    continue

            raise e

    if not parsed:
        raise ValueError(
            "Gemini failed to return resume information."
        )

    # Validate fields
    if "skills" not in parsed:
        parsed["skills"] = []

    if "role" not in parsed:
        parsed["role"] = ""

    if "employment_periods" not in parsed:
        parsed["employment_periods"] = []

    # ─────────────────────────────────────────────────────────
    # Normalize Gemini employment dates
    # ─────────────────────────────────────────────────────────

    normalized_periods = []

    for period in parsed["employment_periods"]:

        if not isinstance(period, dict):
            continue

        start_date = normalize_month_date(
            period.get("start_date", "")
        )

        end_date = normalize_month_date(
            period.get("end_date", "")
        )

        if start_date:

            normalized_periods.append(
                {
                    "start_date": start_date,
                    "end_date": end_date
                }
            )

    # ─────────────────────────────────────────────────────────
    # Deterministic fallback
    #
    # If Gemini failed to extract employment dates,
    # inspect the actual resume text.
    # ─────────────────────────────────────────────────────────

    if not normalized_periods:

        normalized_periods = (
            extract_employment_periods_from_text(
                resume_text
            )
        )

    # ─────────────────────────────────────────────────────────
    # Calculate experience
    # ─────────────────────────────────────────────────────────

    experience_years = calculate_experience_years(
        normalized_periods
    )

    parsed["employment_periods"] = normalized_periods
    parsed["experience_years"] = experience_years

    # Temporary diagnostic
    print(
        "\n========== RESUME EXPERIENCE DEBUG =========="
    )

    print(
        "Employment periods:",
        normalized_periods
    )

    print(
        "Calculated experience:",
        experience_years,
        "years"
    )

    print(
        "=============================================\n"
    )

    return parsed


# ─────────────────────────────────────────────────────────────
# Job matching
# ─────────────────────────────────────────────────────────────

def match_job_with_gemini(
    resume_profile: dict,
    job: dict
) -> dict:

    prompt = f"""
You are a job match analyzer.

Given this candidate profile and job description,
return a match score.

Candidate profile:

- Skills:
{', '.join(
    resume_profile.get(
        'extracted_skills',
        []
    )
)}

- Role:
{resume_profile.get(
    'target_role',
    ''
)}

- Experience:
{resume_profile.get(
    'experience_years',
    0
)} years

Job:

- Title:
{job.get(
    'title',
    ''
)}

- Company:
{job.get(
    'company',
    ''
)}

- Description:
{job.get(
    'description',
    ''
)[:1000]}

Return ONLY valid JSON:

{{
    "score": <integer 0-100>,
    "matching_skills": ["skill1"],
    "missing_skills": ["skill1"]
}}

Rules:

- score: 0 to 100
- matching_skills: candidate skills matching the job
- missing_skills: job skills not present in candidate
- Return only JSON.
"""

    raw = call_gemini(prompt)

    raw = raw.strip()

    if raw.startswith("```"):

        parts = raw.split("```")

        if len(parts) >= 2:

            raw = parts[1]

            if raw.startswith("json"):
                raw = raw[4:]

    try:

        parsed = json.loads(
            raw.strip()
        )

    except json.JSONDecodeError:

        return {
            "score": 0,
            "matching_skills": [],
            "missing_skills": []
        }

    try:

        parsed["score"] = int(
            parsed.get(
                "score",
                0
            )
        )

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
