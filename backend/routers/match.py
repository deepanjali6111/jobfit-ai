from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from auth.jwt_validator import get_current_user
from services.matcher import score_all_jobs
from db.match_repo import save_match_results
from db.client import get_authenticated_client

router = APIRouter()


class MatchRequest(BaseModel):
    jobs: list[dict]


def _get_resume_profile(user_id: str, jwt: str) -> dict | None:
    """Load user's resume profile from Supabase."""
    try:
        client = get_authenticated_client(jwt)
        response = (
            client
            .from_("resume_profiles")
            .select("extracted_skills, experience_years, target_role")
            .eq("user_id", user_id)
            .single()
            .execute()
        )
        return response.data
    except Exception as e:
        print(f"[Match] Error loading profile: {e}")
        return None


@router.post("/match")
async def match_jobs(
    request: MatchRequest,
    user_id: str = Depends(get_current_user),
    authorization: str = Header(...)
):
    jwt = authorization.split(" ")[1]

    profile = _get_resume_profile(user_id, jwt)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail="No resume profile found. Please upload your resume first."
        )

    # Only score first 10 jobs to stay within timeout
    jobs = request.jobs[:10]

    if not jobs:
        raise HTTPException(
            status_code=400,
            detail="No jobs provided to match."
        )

    print(f"[Match] Scoring {len(jobs)} jobs for user {user_id[:8]}...")

    try:
        ranked_jobs = score_all_jobs(profile, jobs)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"AI scoring failed. Please try again. ({str(e)})"
        )

    save_match_results(user_id, ranked_jobs, jwt)

    return {"ranked_jobs": ranked_jobs}