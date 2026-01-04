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

router = APIRouter(tags=["Me"])


async def infer_domain(request: Request) -> Optional[str]:
    return "*"


RESOURCE = "self"
rbac = build_rbac_dependencies(
    resource=RESOURCE,
    domain_resolver=infer_domain,
)


@router.get("/me", response_model=UserResponse, operation_id="get_me")
async def get_me(
    _authorized: bool = Depends(rbac["read"]),
    current_user=Depends(get_current_user),
):
    """
    Get information about the currently authenticated user.

    Returns the user profile information for the authenticated user making the request.
    """
    return current_user


@router.get(
    "/user",
    response_model=UserResponse,
    operation_id="get_user",
    deprecated=True,
)
async def get_user(
    _authorized: bool = Depends(rbac["read"]),
    current_user=Depends(get_current_user),
):
    """
    Get information about the currently authenticated user.

    Returns the user profile information for the authenticated user making the request.
    """
    return current_user


@router.put("/me", response_model=UserResponse, operation_id="update_me")
async def update_me(
    user_update: UserUpdate,
    _authorized: bool = Depends(rbac["update"]),
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

    # Update the user using the command
    update_user_command = UpdateUserCommand(db)
    try:
        updated_user = update_user_command.execute(current_user.id, user_update)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

    return updated_user


@router.put(
    "/user", response_model=UserResponse, operation_id="update_user", deprecated=True
)
async def update_current_user_info(
    user_update: UserUpdate,
    _authorized: bool = Depends(rbac["update"]),
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

    # Update the user using the command
    update_user_command = UpdateUserCommand(db)
    try:
        updated_user = update_user_command.execute(current_user.id, user_update)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

    return updated_user


########################################################
# API Keys
########################################################

RESOURCE = "self.api_key"
rbac_api_key = build_rbac_dependencies(
    resource=RESOURCE,
    domain_resolver=infer_domain,
)


@router.get(
    "/me/api-keys",
    response_model=Page[ApiKeyResponse],
    operation_id="list_user_api_keys",
)
async def list_me_api_keys(
    _authorized: bool = Depends(rbac_api_key["read"]),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all API keys for a specific user.

    Returns a paginated list of API keys for the specified user.
    """
    api_key_service = ApiKeyService(db)
    query = api_key_service.get_user_api_keys_query(current_user.id)
    return paginate(query)


@router.post(
    "/me/api-keys",
    response_model=ApiKeyCreateResponse,
    operation_id="create_me_api_key",
)
async def create_me_api_key(
    api_key_data: ApiKeyCreateRequest,
    _authorized: bool = Depends(rbac_api_key["create"]),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new API key for a specific user.

    Returns the new API key with the full key shown only once.
    """

    create_api_key_command = CreateApiKeyCommand(db)

    # Create the API key
    api_key, full_key = create_api_key_command.execute(
        ApiKeyCreate(
            user_id=current_user.id,
            name=api_key_data.name,
            expires_at=api_key_data.expires_at,
        )
    )

    # Return the response with the full key
    response_data = ApiKeyResponse.model_validate(api_key)
    return ApiKeyCreateResponse(
        **response_data.model_dump(),
        full_key=full_key,
    )


## Deprecated
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
        )
    )

    # Return the response with the full key
    response_data = ApiKeyResponse.model_validate(api_key)
    return ApiKeyCreateResponse(
        **response_data.model_dump(),
        full_key=full_key,
    )
