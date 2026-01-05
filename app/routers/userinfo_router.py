from fastapi import APIRouter, Depends, Request
from typing import Optional
from app.utils.auth import get_current_user
from app.schemas.user import UserResponse

router = APIRouter(tags=["UserInfo"])


@router.get("/userinfo", response_model=UserResponse, operation_id="get_userinfo")
async def get_current_user_info(
    current_user=Depends(get_current_user),
):
    """
    Get information about the currently authenticated user.

    Returns the user profile information for the authenticated user making the request.
    """
    return current_user
