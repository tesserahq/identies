from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from typing import Optional
from app.utils.auth import get_current_user
from app.schemas.user import UserUpdate, UserResponse
from app.schemas.api_key import (
    ApiKeyCreate,
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeyResponse,
)
from app.db import get_db
from sqlalchemy.orm import Session
from app.services.user_service import UserService
from app.services.api_key_service import ApiKeyService
from app.exceptions.service_account_error import ServiceAccountError
from app.commands.users.update_user_command import UpdateUserCommand
from app.commands.api_keys.create_api_key_command import CreateApiKeyCommand
from app.models.user import User
from app.auth.rbac import build_rbac_dependencies
from uuid import UUID

router = APIRouter(tags=["User"])


async def infer_domain(request: Request) -> Optional[str]:
    return "*"


RESOURCE = "user"
rbac = build_rbac_dependencies(
    resource=RESOURCE,
    domain_resolver=infer_domain,
)


@router.get(
    "/users/{user_id}", response_model=UserResponse, operation_id="get_user_by_id"
)
async def get_user_by_id(
    user_id: UUID,
    _authorized: bool = Depends(rbac["read"]),
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


@router.get("/users", response_model=Page[UserResponse], operation_id="list_users")
async def list_users(
    _authorized: bool = Depends(rbac["read"]),
    db: Session = Depends(get_db),
):
    """
    List all users.

    Returns a paginated list of all users.
    """
    user_service = UserService(db)
    query = user_service.get_users_query()
    return paginate(query)


@router.get(
    "/users/{user_id}/api-keys",
    response_model=Page[ApiKeyResponse],
    operation_id="list_user_api_keys",
)
async def list_user_api_keys(
    user_id: UUID,
    _authorized: bool = Depends(rbac["read"]),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all API keys for a specific user.

    Returns a paginated list of API keys for the specified user.
    """
    # Verify the user exists
    user_service = UserService(db)
    user = user_service.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    api_key_service = ApiKeyService(db)
    query = api_key_service.get_user_api_keys_query(user_id)
    return paginate(query)


@router.post(
    "/users/{user_id}/api-keys",
    response_model=ApiKeyCreateResponse,
    operation_id="create_user_api_key",
)
async def create_user_api_key(
    user_id: UUID,
    api_key_data: ApiKeyCreateRequest,
    _authorized: bool = Depends(rbac["create"]),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new API key for a specific user.

    Returns the new API key with the full key shown only once.
    """
    # Verify the user exists
    user_service = UserService(db)
    user = user_service.get_user(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    create_api_key_command = CreateApiKeyCommand(db)

    # Create the API key
    api_key, full_key = create_api_key_command.execute(
        ApiKeyCreate(
            user_id=user_id,
            name=api_key_data.name,
            expires_at=api_key_data.expires_at,
        ),
        current_user,
    )

    # Return the response with the full key
    response_data = ApiKeyResponse.model_validate(api_key)
    return ApiKeyCreateResponse(
        **response_data.model_dump(),
        full_key=full_key,
    )
