from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from auth.jwt_validator import get_current_user
from services.pdf_extractor import extract_text_from_pdf
from services.gemini_service import parse_resume_with_gemini
from db.resume_repo import upsert_resume_profile

router = APIRouter()

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes


@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user)
):
    """
    Receives a PDF resume, extracts text, parses with Gemini,
    stores profile in database.

    Protected: requires valid JWT in Authorization header.
    """

    # ── Validate file type ───────────────────────────────────
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only PDF files are accepted."
        )

    # ── Read file bytes ──────────────────────────────────────
    file_bytes = await file.read()

    # ── Validate file size ───────────────────────────────────
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File too large. Maximum size is 10MB."
        )

    # ── Extract text from PDF ────────────────────────────────
    try:
        raw_text = extract_text_from_pdf(file_bytes)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )

    # ── Parse profile with Gemini ────────────────────────────
    try:
        profile = parse_resume_with_gemini(raw_text)
    except RuntimeError as e:
        # Quota exceeded
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except ValueError as e:
        # Gemini returned bad response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI parsing failed: {str(e)}"
        )

    # ── Store in database ────────────────────────────────────
    result = upsert_resume_profile(user_id, profile, raw_text)

    # ── Build response message ───────────────────────────────
    if result["is_update"]:
        message = (
            "Resume updated successfully. "
            "Previous job matches were cleared because they were based "
            "on your old resume. Search again to generate fresh recommendations."
        )
    else:
        message = "Resume uploaded successfully. Your profile has been saved."

    return {
        "skills":           profile["skills"],
        "role":             profile["role"],
        "experience_years": profile["experience_years"],
        "message":          message
    }