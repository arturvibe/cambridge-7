from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from app.core.services import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])

class SessionLoginRequest(BaseModel):
    id_token: str

@router.post("/session-login", status_code=status.HTTP_200_OK)
async def session_login(
    request: SessionLoginRequest,
    auth_service: AuthService = Depends(AuthService),
):
    """
    Verifies the magic link and creates a session.
    """
    try:
        session_cookie = auth_service.create_session_cookie(id_token=request.id_token)
        response = JSONResponse(content={"message": "Session created successfully."})
        response.set_cookie(
            key="session",
            value=session_cookie,
            httponly=True,
            secure=True,
            samesite="strict",
        )
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {e}",
        )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout():
    """
    Logs the user out by clearing the session cookie.
    """
    response = JSONResponse(content={"message": "Logged out successfully."})
    response.delete_cookie(key="session")
    return response


router_users = APIRouter(prefix="/users", tags=["Users"])

@router_users.get("/me")
async def get_user_profile(
    current_user: dict = Depends(AuthService().get_current_user),
):
    """
    Returns the profile of the currently authenticated user.
    """
    return current_user
