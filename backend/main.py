from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from auth.jwt_validator import get_current_user
from routers.upload import router as upload_router
from routers.jobs import router as jobs_router
from routers.match import router as match_router

app = FastAPI(title="JobFit AI")

# ── CORS — allows Streamlit to call FastAPI ──────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────
app.include_router(upload_router)
app.include_router(jobs_router)
app.include_router(match_router)


# ── Health check ─────────────────────────────────────────────
@app.get("/")
def health():
    return {"status": "healthy"}


# ── Protected test endpoint ──────────────────────────────────
@app.get("/me")
async def get_me(user_id: str = Depends(get_current_user)):
    return {
        "user_id": user_id,
        "message": "Token is valid. Auth working correctly."
    }