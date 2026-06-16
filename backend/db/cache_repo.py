import hashlib
import json
from datetime import datetime, timezone
from db.client import supabase


def generate_query_hash(role: str, location: str) -> str:
    """
    Generate a SHA256 hash from role + location.
    This is the cache key — same search = same hash = cache hit.
    """
    raw = f"{role.strip().lower()}:{location.strip().lower()}"
    return hashlib.sha256(raw.encode()).hexdigest()


def get_cached_jobs(query_hash: str) -> list[dict] | None:
    """
    Check job_cache for a valid (unexpired) result.
    Returns the jobs list if cache hit, None if miss or expired.
    """
    try:
        response = (
            supabase
            .from_("job_cache")
            .select("results, expires_at")
            .eq("query_hash", query_hash)
            .single()
            .execute()
        )

        row = response.data
        if not row:
            return None

        # Check expiry
        expires_at = datetime.fromisoformat(row["expires_at"])

        # Make both timezone-aware for comparison
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)

        if now > expires_at:
            print(f"[Cache] Expired for hash {query_hash[:8]}...")
            return None

        print(f"[Cache] HIT for hash {query_hash[:8]}...")
        return row["results"]  # Already a list — Supabase parses JSONB

    except Exception as e:
        print(f"[Cache] Read error: {e}")
        return None


def save_jobs_to_cache(query_hash: str, jobs: list[dict]) -> None:
    """
    Save job results to job_cache with 1-hour expiry.
    Uses UPSERT so re-running the same search refreshes the cache.
    """
    from datetime import timedelta

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=1)

    row = {
        "query_hash": query_hash,
        "results": jobs,  # Supabase accepts list[dict] directly for JSONB
        "cached_at": now.isoformat(),
        "expires_at": expires_at.isoformat()
    }

    try:
        supabase.from_("job_cache").upsert(row, on_conflict="query_hash").execute()
        print(f"[Cache] Saved {len(jobs)} jobs for hash {query_hash[:8]}...")

    except Exception as e:
        print(f"[Cache] Write error: {e}")