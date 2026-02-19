from fastapi import APIRouter, Depends, Request, Query
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from typing import Optional

from app.auth.rbac import build_rbac_dependencies
from app.commands.api_keys.create_api_key_command import CreateApiKeyCommand
from app.db import get_db
from app.models.user import User as UserModel
from app.schemas.user import User
from app.routers.utils.dependencies import get_current_user, get_user_by_id
from app.schemas.api_key import (
    ApiKeyCreate,
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeyResponse,
)
from app.schemas.external_account import ExternalAccountResponse
from app.schemas.user import UserResponse
from app.services.api_key_service import ApiKeyService
from app.services.external_account_service import ExternalAccountService
from app.services.user_service import UserService
from sqlalchemy.orm import Session

router = APIRouter(tags=["User"])


async def infer_domain(_request: Request) -> Optional[str]:
    return "*"


RESOURCE = "user"
rbac = build_rbac_dependencies(
    resource=RESOURCE,
    domain_resolver=infer_domain,
)


RESOURCE = "external_account"
rbac_external_account = build_rbac_dependencies(
    resource=RESOURCE,
    domain_resolver=infer_domain,
)


@router.get(
    "/users/{user_id}", response_model=UserResponse, operation_id="get_user_by_id"
)
async def read_user(
    user: UserModel = Depends(get_user_by_id),
    _authorized: bool = Depends(rbac["read"]),
):
    """
    Get a specific user by ID.

    Returns the user with the specified ID, or 404 if not found.
    """
    return user


@router.get(
    "/internal/users/{user_id}",
    response_model=UserResponse,
    operation_id="get_user_by_id",
)
async def read_internal_user(
    user: UserModel = Depends(get_user_by_id),
):
    """
    Get a specific user by ID.

    Returns the user with the specified ID, or 404 if not found.
    """
    return user


@router.get("/users", response_model=Page[UserResponse], operation_id="list_users")
async def list_users(
    q: str | None = Query(
        default=None, description="Search by first_name, last_name, or email"
    ),
    _authorized: bool = Depends(rbac["read"]),
    db: Session = Depends(get_db),
):
    """
    List all users.

    Returns a paginated list of all users.
    """
    user_service = UserService(db)
    query = user_service.get_users_query(q=q)
    return paginate(query)


@router.get(
    "/users/{user_id}/api-keys",
    response_model=Page[ApiKeyResponse],
    operation_id="list_user_api_keys",
)
async def list_user_api_keys(
    user: UserModel = Depends(get_user_by_id),
    _authorized: bool = Depends(rbac["read"]),
    db: Session = Depends(get_db),
):
    """
    List all API keys for a specific user.

    Returns a paginated list of API keys for the specified user.
    """
    api_key_service = ApiKeyService(db)
    query = api_key_service.get_user_api_keys_query(user.id)
    return paginate(query)


@router.get(
    "/users/{user_id}/external-accounts",
    response_model=Page[ExternalAccountResponse],
    operation_id="list_user_external_accounts",
)
async def list_user_external_accounts(
    user: UserModel = Depends(get_user_by_id),
    _rbac_external_account: bool = Depends(rbac_external_account["read"]),
    platform: Optional[str] = Query(
        None,
        description="Filter by platform (e.g. telegram)",
    ),
    _authorized: bool = Depends(rbac["read"]),
    db: Session = Depends(get_db),
):
    """
    List external accounts for a specific user (paginated).
    """
    external_account_service = ExternalAccountService(db)
    query = external_account_service.get_external_accounts_query(
        user.id, platform=platform
    )
    return paginate(query)


@router.post(
    "/users/{user_id}/api-keys",
    response_model=ApiKeyCreateResponse,
    operation_id="create_user_api_key",
)
async def create_user_api_key(
    api_key_data: ApiKeyCreateRequest,
    user: UserModel = Depends(get_user_by_id),
    _authorized: bool = Depends(rbac["create"]),
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
            user_id=user.id,
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
