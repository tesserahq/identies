from fastapi import APIRouter, Depends, Request, HTTPException
from app.utils.auth import get_current_user
from app.schemas.user import UserUpdate, UserResponse
from app.db import get_db
from sqlalchemy.orm import Session
from app.services.user_service import UserService
from app.exceptions.service_account_error import ServiceAccountError
from uuid import UUID

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


@router.get(
    "/users/{user_id}", response_model=UserResponse, operation_id="get_user_by_id"
)
async def get_user_by_id(
    user_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Get a specific user by ID.

    Returns the user with the specified ID, or 404 if not found.
    """
    user_service = UserService(db)
    user = user_service.get_user(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


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
