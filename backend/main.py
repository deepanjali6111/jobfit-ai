from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from auth.jwt_validator import get_current_user

app = FastAPI(title="JobFit AI")

# Allow Streamlit frontend to call this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health():
    return {"status": "healthy"}


@app.get("/protected-test")
def protected_test(user_id: str = Depends(get_current_user)):
    """
    Test endpoint — confirms JWT validation works.
    Remove this after Milestone 1 is verified.
    """
    return {
        "message": "Token is valid",
        "user_id": user_id
    }