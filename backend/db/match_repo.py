from db.client import get_authenticated_client


def save_match_results(user_id: str, ranked_jobs: list[dict], jwt: str) -> None:
    """
    Save top 20 ranked job matches to job_matches table.
    Clears previous matches for this user before saving new ones.
    Uses authenticated client because RLS is enabled on job_matches.
    """
    client = get_authenticated_client(jwt)

    try:
        # Clear old matches for this user first
        client.from_("job_matches") \
            .delete() \
            .eq("user_id", user_id) \
            .execute()

        print(f"[MatchRepo] Cleared old matches for user {user_id[:8]}...")

        # Prepare rows to insert
        rows = []
        for job in ranked_jobs[:20]:  # Store top 20 max
            rows.append({
                "user_id": user_id,
                "job_title": job.get("title", ""),
                "company": job.get("company", ""),
                "match_score": job.get("match_score", 0),
                "job_url": job.get("url", "")
            })

        if rows:
            client.from_("job_matches").insert(rows).execute()
            print(f"[MatchRepo] Saved {len(rows)} matches for user {user_id[:8]}...")

    except Exception as e:
        print(f"[MatchRepo] Error saving matches: {e}")


def get_saved_matches(user_id: str, jwt: str) -> list[dict]:
    """
    Retrieve saved job matches for a user, sorted by match_score descending.
    Uses authenticated client because RLS is enabled on job_matches.
    """
    client = get_authenticated_client(jwt)

    try:
        response = (
            client
            .from_("job_matches")
            .select("job_title, company, match_score, job_url, found_at")
            .eq("user_id", user_id)
            .order("match_score", desc=True)
            .execute()
        )
        return response.data or []

    except Exception as e:
        print(f"[MatchRepo] Error fetching matches: {e}")
        return []