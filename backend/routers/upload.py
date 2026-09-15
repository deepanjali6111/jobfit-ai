from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status, Header

from auth.jwt_validator import get_current_user
from services.pdf_extractor import extract_text_from_pdf
from services.gemini_service import parse_resume_with_gemini
from db.resume_repo import upsert_resume_profile
from db.client import get_authenticated_client


router = APIRouter()


MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    authorization: str = Header(...),
    user_id: str = Depends(get_current_user)
):

    print("\n========== UPLOAD START ==========")
    print("Filename:", file.filename)
    print("User ID:", user_id)

    # ─────────────────────────────────────────────────────────
    # Validate authorization header
    # ─────────────────────────────────────────────────────────

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header."
        )

    jwt = authorization.split(" ", 1)[1]

    # ─────────────────────────────────────────────────────────
    # Validate file type
    # ─────────────────────────────────────────────────────────

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No file was provided."
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only PDF files are accepted."
        )

    # ─────────────────────────────────────────────────────────
    # Read file
    # ─────────────────────────────────────────────────────────

    file_bytes = await file.read()

    print("Uploaded file size:", len(file_bytes), "bytes")

    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File too large. Maximum size is 10MB."
        )

    # ─────────────────────────────────────────────────────────
    # Extract PDF text
    # ─────────────────────────────────────────────────────────

    try:

        raw_text = extract_text_from_pdf(file_bytes)

        print(
            "Extracted resume text length:",
            len(raw_text)
        )

        print(
            "Resume text preview:",
            raw_text[:500].replace("\n", " ")
        )

    except ValueError as e:

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )

    # ─────────────────────────────────────────────────────────
    # Parse resume with Gemini
    # ─────────────────────────────────────────────────────────

    try:

        profile = parse_resume_with_gemini(raw_text)

        print("\n========== PARSED PROFILE ==========")
        print("Role:", profile.get("role"))
        print("Experience:", profile.get("experience_years"))
        print("Skills count:", len(profile.get("skills", [])))
        print(
            "Employment periods:",
            profile.get("employment_periods")
        )
        print("====================================\n")

    except RuntimeError as e:

        print("Gemini RuntimeError:", str(e))

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )

    except ValueError as e:

        print("Gemini ValueError:", str(e))

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI parsing failed: {str(e)}"
        )

    except Exception as e:

        print(
            "Unexpected parsing error:",
            repr(e)
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected resume parsing error: {str(e)}"
        )

    # ─────────────────────────────────────────────────────────
    # Get authenticated Supabase client
    # ─────────────────────────────────────────────────────────

    try:

        auth_client = get_authenticated_client(jwt)

    except Exception as e:

        print(
            "Supabase client error:",
            repr(e)
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create authenticated database client."
        )

    # ─────────────────────────────────────────────────────────
    # Save profile
    # ─────────────────────────────────────────────────────────

    try:

        result = upsert_resume_profile(
            user_id,
            profile,
            raw_text,
            auth_client
        )

        print("\n========== DATABASE RESULT ==========")
        print(
            "Saved experience:",
            profile.get("experience_years")
        )
        print(
            "Is update:",
            result.get("is_update")
        )
        print("=====================================\n")

    except Exception as e:

        print(
            "Database error:",
            repr(e)
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save resume profile: {str(e)}"
        )

    # ─────────────────────────────────────────────────────────
    # Success message
    # ─────────────────────────────────────────────────────────

    if result["is_update"]:

        message = (
            "Resume updated successfully. "
            "Previous job matches were cleared because they were based "
            "on your old resume. Search again to generate fresh recommendations."
        )

    else:

        message = (
            "Resume uploaded successfully. "
            "Your profile has been saved."
        )

    print("========== UPLOAD COMPLETE ==========\n")

    # ─────────────────────────────────────────────────────────
    # Response
    # ─────────────────────────────────────────────────────────

    return {
        "skills": profile.get("skills", []),
        "role": profile.get("role", ""),
        "experience_years": profile.get(
            "experience_years",
            0.0
        ),
        "employment_periods": profile.get(
            "employment_periods",
            []
        ),
        "message": message
    }
