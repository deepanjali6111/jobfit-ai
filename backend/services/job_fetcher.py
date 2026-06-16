import os
import httpx
from dotenv import load_dotenv

load_dotenv()

JSEARCH_API_KEY = os.getenv("JSEARCH_API_KEY")
JSEARCH_BASE_URL = "https://jsearch.p.rapidapi.com/search"


def _normalize_jsearch(job: dict) -> dict:
    """Convert JSearch job object to our standard shape."""
    return {
        "title": job.get("job_title", ""),
        "company": job.get("employer_name", ""),
        "location": job.get("job_city") or job.get("job_country") or "India",
        "description": (job.get("job_description") or "")[:1000],
        "url": job.get("job_apply_link") or job.get("job_google_link", ""),
        "source": "jsearch"
    }


async def fetch_jsearch_jobs(role: str, location: str, count: int = 20) -> list[dict]:
    """Fetch jobs from JSearch API (RapidAPI)."""
    headers = {
        "X-RapidAPI-Key": JSEARCH_API_KEY,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }
    params = {
        "query": f"{role} in {location}",
        "num_pages": "2",
        "page": "1"
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                JSEARCH_BASE_URL,
                headers=headers,
                params=params
            )
            response.raise_for_status()
            data = response.json()
            jobs = data.get("data", [])
            print(f"[JSearch] Fetched {len(jobs)} jobs")
            return [_normalize_jsearch(j) for j in jobs[:count]]

    except httpx.ReadTimeout:
        print("[JSearch] Timeout — API too slow")
        return []
    except httpx.HTTPStatusError as e:
        print(f"[JSearch] HTTP error: {e.response.status_code}")
        return []
    except Exception as e:
        print(f"[JSearch] Unexpected error: {e}")
        return []


async def fetch_all_jobs(role: str, location: str) -> list[dict]:
    """
    Fetch up to 20 jobs from JSearch.
    JSearch covers Indian job boards — LinkedIn, Indeed, Naukri etc.
    """
    jobs = await fetch_jsearch_jobs(role, location, count=20)
    print(f"[JobFetcher] Total jobs fetched: {len(jobs)}")
    return jobs