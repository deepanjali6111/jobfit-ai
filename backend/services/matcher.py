import json
from services.gemini_service import call_gemini


def _build_scoring_prompt(profile: dict, job: dict) -> str:
    """Build the prompt sent to Gemini for scoring one job against the resume."""
    skills = ", ".join(profile.get("extracted_skills", []))
    role = profile.get("target_role", "")
    experience = profile.get("experience_years", 0)

    job_title = job.get("title", "")
    job_company = job.get("company", "")
    job_description = job.get("description", "")

    return f"""
You are a job matching assistant. Score how well a candidate's resume matches a job listing.

CANDIDATE PROFILE:
- Target Role: {role}
- Experience: {experience} years
- Skills: {skills}

JOB LISTING:
- Title: {job_title}
- Company: {job_company}
- Description: {job_description}

TASK:
Analyze the match and respond with ONLY a valid JSON object in this exact format:
{{
  "match_score": <integer 0-100>,
  "matching_skills": [<list of skills from candidate that match the job>],
  "missing_skills": [<list of important skills the job needs that the candidate lacks>]
}}

SCORING GUIDE:
- 80-100: Excellent match, candidate is well qualified
- 60-79: Good match, candidate meets most requirements  
- 40-59: Partial match, candidate meets some requirements
- 0-39: Poor match, significant skill gaps

Do not include any explanation. Return only the JSON object.
""".strip()


def _parse_gemini_response(response_text: str) -> dict:
    """
    Safely parse Gemini's JSON response.
    Falls back to default values if parsing fails.
    """
    try:
        text = response_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1])

        parsed = json.loads(text)

        return {
            "match_score": max(0, min(100, int(parsed.get("match_score", 0)))),
            "matching_skills": parsed.get("matching_skills", []),
            "missing_skills": parsed.get("missing_skills", [])
        }

    except Exception as e:
        print(f"[Matcher] Failed to parse Gemini response: {e}")
        print(f"[Matcher] Raw response: {response_text}")
        return {
            "match_score": 0,
            "matching_skills": [],
            "missing_skills": []
        }


def score_job(profile: dict, job: dict) -> dict:
    """
    Score a single job against the resume profile using Gemini.
    Returns the job dict enriched with match_score, matching_skills, missing_skills.
    """
    prompt = _build_scoring_prompt(profile, job)
    response_text = call_gemini(prompt)

    if not response_text:
        print(f"[Matcher] No response from Gemini for job: {job.get('title')}")
        scores = {
            "match_score": 0,
            "matching_skills": [],
            "missing_skills": []
        }
    else:
        scores = _parse_gemini_response(response_text)

    return {
        "title": job.get("title", ""),
        "company": job.get("company", ""),
        "location": job.get("location", ""),
        "url": job.get("url", ""),
        "source": job.get("source", ""),
        "match_score": scores["match_score"],
        "matching_skills": scores["matching_skills"],
        "missing_skills": scores["missing_skills"]
    }


def score_all_jobs(profile: dict, jobs: list[dict]) -> list[dict]:
    """
    Score all jobs against the resume profile.
    Returns jobs sorted by match_score descending.
    """
    scored = []

    for i, job in enumerate(jobs):
        print(f"[Matcher] Scoring job {i + 1}/{len(jobs)}: {job.get('title')}")
        result = score_job(profile, job)
        scored.append(result)

    scored.sort(key=lambda x: x["match_score"], reverse=True)

    print(f"[Matcher] Done. Top score: {scored[0]['match_score'] if scored else 0}")
    return scored