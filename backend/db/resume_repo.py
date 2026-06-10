from supabase import Client


def upsert_resume_profile(user_id: str, profile: dict, raw_text: str, client: Client) -> dict:
    existing = client.table("resume_profiles") \
        .select("id") \
        .eq("user_id", user_id) \
        .execute()

    is_update = len(existing.data) > 0

    result = client.table("resume_profiles").upsert({
        "user_id":          user_id,
        "extracted_skills": profile["skills"],
        "experience_years": profile["experience_years"],
        "target_role":      profile["role"],
        "raw_text":         raw_text,
    }, on_conflict="user_id").execute()

    if is_update:
        client.table("job_matches") \
            .delete() \
            .eq("user_id", user_id) \
            .execute()

    return {
        "data": result.data,
        "is_update": is_update
    }


def get_resume_profile(user_id: str, client: Client) -> dict | None:
    result = client.table("resume_profiles") \
        .select("*") \
        .eq("user_id", user_id) \
        .execute()

    if not result.data:
        return None

    return result.data[0]