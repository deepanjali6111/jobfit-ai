from db.client import supabase


def upsert_resume_profile(user_id: str, profile: dict, raw_text: str) -> dict:
    """
    Inserts or updates resume profile for a user.
    If user already has a profile, replaces it and clears old job matches.

    Args:
        user_id:  UUID string from JWT
        profile:  Parsed profile from Gemini
                  {"skills": [...], "role": "...", "experience_years": 0}
        raw_text: Full resume text for future re-parsing if needed

    Returns:
        The upserted record from Supabase
    """

    # Check if user already has a resume
    existing = supabase.table("resume_profiles") \
        .select("id") \
        .eq("user_id", user_id) \
        .execute()

    is_update = len(existing.data) > 0

    # UPSERT — insert if new, update if exists
    result = supabase.table("resume_profiles").upsert({
        "user_id":          user_id,
        "extracted_skills": profile["skills"],
        "experience_years": profile["experience_years"],
        "target_role":      profile["role"],
        "raw_text":         raw_text,
    }, on_conflict="user_id").execute()

    # If update — delete old job matches since scores are now stale
    if is_update:
        supabase.table("job_matches") \
            .delete() \
            .eq("user_id", user_id) \
            .execute()

    return {
        "data": result.data,
        "is_update": is_update
    }


def get_resume_profile(user_id: str) -> dict | None:
    """
    Fetches stored resume profile for a user.

    Returns:
        Profile dict if found, None if user has no resume yet
    """
    result = supabase.table("resume_profiles") \
        .select("*") \
        .eq("user_id", user_id) \
        .execute()

    if not result.data:
        return None

    return result.data[0]