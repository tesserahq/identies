from fastapi import APIRouter, Depends, Request
from app.utils.auth import get_current_user
from app.schemas.user import UserUpdate, UserResponse
from app.db import get_db
from sqlalchemy.orm import Session
from app.services.user_service import UserService
from app.exceptions.service_account_error import ServiceAccountError

router = APIRouter(tags=["User"])


@router.get("/userinfo", response_model=UserResponse, operation_id="get_userinfo")
async def get_current_user_info(
    current_user=Depends(get_current_user),
):
    """
    Get information about the currently authenticated user.

    Returns the user profile information for the authenticated user making the request.
    """
    return current_user


@router.get("/user", response_model=UserResponse, operation_id="get_user")
async def get_user(
    current_user=Depends(get_current_user),
):
    """
    Get information about the currently authenticated user.

    Returns the user profile information for the authenticated user making the request.
    """
    return current_user


@router.put("/user", response_model=UserResponse, operation_id="update_user")
async def update_current_user_info(
    user_update: UserUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update information for the currently authenticated user.

    Allows the authenticated user to update their profile information.
    Only the fields provided in the request will be updated.
    Service accounts cannot be updated through this endpoint.
    """

    # Check if the user is a service account
    if current_user.service_account:
        raise ServiceAccountError(
            "Service accounts cannot be updated through this endpoint"
        )

    user_service = UserService(db)

    updated_user = user_service.update_user(current_user.id, user_update)
    return updated_user
