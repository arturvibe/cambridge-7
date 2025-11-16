from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyCookie
from firebase_admin import auth

cookie_scheme = APIKeyCookie(name="session", auto_error=False)

async def get_current_user(session: str = Depends(cookie_scheme)):
    """
    Dependency to verify the session cookie and return the user.
    """
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    try:
        decoded_claims = auth.verify_session_cookie(session, check_revoked=True)
        return decoded_claims
    except auth.InvalidSessionCookieError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session cookie",
        )
