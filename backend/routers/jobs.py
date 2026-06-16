from fastapi import APIRouter, Depends, HTTPException, Query, Header
from auth.jwt_validator import get_current_user
from services.job_fetcher import fetch_all_jobs
from db.cache_repo import generate_query_hash, get_cached_jobs, save_jobs_to_cache
from db.client import get_authenticated_client

router = APIRouter()


def _check_resume_exists(user_id: str, jwt: str) -> bool:
    """Check if user has an uploaded resume profile."""
    try:
        client = get_authenticated_client(jwt)
        response = (
            client
            .from_("resume_profiles")
            .select("id")
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        return response.data is not None
    except Exception:
        return False


@router.get("/jobs")
async def get_jobs(
    role: str = Query(..., min_length=2, description="Job role to search for"),
    location: str = Query(..., min_length=2, description="Location to search in"),
    user_id: str = Depends(get_current_user),
    authorization: str = Header(...)
):
    """
    Fetch job listings for a given role and location.
    Checks cache first. Fetches from JSearch + Remotive on cache miss.
    Requires a resume to be uploaded first.
    """
    # Extract JWT from Authorization header
    jwt = authorization.split(" ")[1]

    # Guard: must have uploaded resume before searching
    if not _check_resume_exists(user_id, jwt):
        raise HTTPException(
            status_code=400,
            detail="Please upload your resume before searching for jobs."
        )

    # Generate cache key
    query_hash = generate_query_hash(role, location)

    # Try cache first
    cached = get_cached_jobs(query_hash)
    if cached:
        return {
            "jobs": cached,
            "from_cache": True
        }

    # Cache miss — fetch from APIs
    jobs = await fetch_all_jobs(role, location)

    if not jobs:
        raise HTTPException(
            status_code=503,
            detail="Could not fetch jobs at this time. Please try again shortly."
        )

    # Save to cache for next request
    save_jobs_to_cache(query_hash, jobs)

    return {
        "jobs": jobs,
        "from_cache": False
    }