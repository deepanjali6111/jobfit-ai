from fastapi import Header, HTTPException, status
from db.client import supabase


async def get_current_user(authorization: str = Header(...)) -> str:
    """
    Extracts and validates JWT from Authorization header.
    Returns user_id string if valid.
    Raises 401 if token is missing or invalid.
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization format. Expected: Bearer <token>"
        )

    token = authorization.split(" ")[1]

    try:
        response = supabase.auth.get_user(token)

        if not response or not response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token."
            )

        return response.user.id

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token."
        )