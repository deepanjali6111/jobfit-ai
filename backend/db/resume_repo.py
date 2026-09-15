from supabase import Client


# ─────────────────────────────────────────────────────────────
# Insert / update resume profile
# ─────────────────────────────────────────────────────────────

def upsert_resume_profile(
    user_id: str,
    profile: dict,
    raw_text: str,
    client: Client
) -> dict:
    """
    Creates or updates the user's resume profile.

    experience_years is stored as a decimal value.

    Examples:
        0.50 = 6 months
        0.83 = 10 months
        1.00 = 1 year
        1.50 = 1 year 6 months
    """

    # Check whether the user already has a resume profile
    existing = (
        client
        .table("resume_profiles")
        .select("id")
        .eq("user_id", user_id)
        .execute()
    )

    is_update = len(existing.data) > 0

    # ─────────────────────────────────────────────────────────
    # Preserve decimal experience
    # ─────────────────────────────────────────────────────────

    experience_years = profile.get(
        "experience_years",
        0.0
    )

    try:

        experience_years = float(
            experience_years
        )

    except (ValueError, TypeError):

        experience_years = 0.0

    # ─────────────────────────────────────────────────────────
    # Upsert profile
    # ─────────────────────────────────────────────────────────

    result = (
        client
        .table("resume_profiles")
        .upsert(
            {
                "user_id": user_id,

                "extracted_skills": profile.get(
                    "skills",
                    []
                ),

                "experience_years": experience_years,

                "target_role": profile.get(
                    "role",
                    ""
                ),

                "raw_text": raw_text,
            },
            on_conflict="user_id"
        )
        .execute()
    )

    # ─────────────────────────────────────────────────────────
    # If resume was updated, old matches are no longer valid
    # ─────────────────────────────────────────────────────────

    if is_update:

        (
            client
            .table("job_matches")
            .delete()
            .eq("user_id", user_id)
            .execute()
        )

    return {
        "data": result.data,
        "is_update": is_update
    }


# ─────────────────────────────────────────────────────────────
# Get resume profile
# ─────────────────────────────────────────────────────────────

def get_resume_profile(
    user_id: str,
    client: Client
) -> dict | None:
    """
    Returns the user's stored resume profile.
    Returns None if no profile exists.
    """

    result = (
        client
        .table("resume_profiles")
        .select("*")
        .eq("user_id", user_id)
        .execute()
    )

    if not result.data:
        return None

    return result.data[0]
