from fastapi import APIRouter, Depends, Request
from app.utils.auth import get_current_user
from app.schemas.user import User, UserUpdate, UserResponse
from app.db import get_db
from sqlalchemy.orm import Session
from app.services.user_service import UserService
from app.exceptions.service_account_error import ServiceAccountError

router = APIRouter(tags=["User"])


@router.get("/userinfo", response_model=UserResponse)
async def get_current_user_info(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Get information about the currently authenticated user.

    Returns the user profile information for the authenticated user making the request.
    """
    user = await get_current_user(request)

    return user


@router.get("/user", response_model=UserResponse)
async def get_user(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Get information about the currently authenticated user.

    Returns the user profile information for the authenticated user making the request.
    """
    user = await get_current_user(request)

    return user


@router.put("/user", response_model=UserResponse)
async def update_current_user_info(
    user_update: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Update information for the currently authenticated user.

    Allows the authenticated user to update their profile information.
    Only the fields provided in the request will be updated.
    Service accounts cannot be updated through this endpoint.
    """
    current_user = await get_current_user(request)

    # Check if the user is a service account
    if current_user.service_account:
        raise ServiceAccountError(
            "Service accounts cannot be updated through this endpoint"
        )

    user_service = UserService(db)

    updated_user = user_service.update_user(current_user.id, user_update)
    return updated_user
