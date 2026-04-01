from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate

from app.commands.service_accounts.create_service_account_command import (
    CreateServiceAccountCommand,
)
from app.commands.service_accounts.update_service_account_command import (
    UpdateServiceAccountCommand,
)
from app.commands.service_accounts.delete_service_account_command import (
    DeleteServiceAccountCommand,
)
from app.commands.api_keys.create_api_key_command import CreateApiKeyCommand
from app.commands.clients.create_client_command import CreateClientCommand
from app.db import get_db
from app.repositories.client_repository import ClientRepository
from app.routers.utils.dependencies import get_current_user
from app.schemas.client import (
    ClientCreate,
    ClientCreateRequest,
    ClientCreateResponse,
    ClientResponse,
)
from app.schemas.service_account import (
    ServiceAccountCreateRequest,
    ServiceAccountUpdateRequest,
)
from app.schemas.user import UserResponse
from app.schemas.api_key import (
    ApiKeyCreate,
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeyResponse,
)
from app.repositories.user_repository import UserRepository
from app.repositories.api_key_repository import ApiKeyRepository
from app.models.user import User
from app.auth.rbac import build_rbac_dependencies

router = APIRouter(prefix="/service-accounts", tags=["Service Accounts"])


async def infer_domain(request: Request) -> Optional[str]:
    return "*"


RESOURCE = "service_account"
rbac = build_rbac_dependencies(
    resource=RESOURCE,
    domain_resolver=infer_domain,
)


@router.post("", response_model=UserResponse, operation_id="create_service_account")
async def create_service_account(
    service_account_data: ServiceAccountCreateRequest,
    _authorized: bool = Depends(rbac["create"]),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new service account.

    Service accounts are users with service_account=True and don't have passwords.
    They authenticate using API keys.
    """
    create_command = CreateServiceAccountCommand(db)
    try:
        service_account = create_command.execute(service_account_data)
        return service_account
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=Page[UserResponse], operation_id="list_service_accounts")
async def list_service_accounts(
    _authorized: bool = Depends(rbac["read"]),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all service accounts.

    Returns a paginated list of service accounts (users with service_account=True).
    """
    user_repository = UserRepository(db)
    query = user_repository.get_service_accounts_query()
    return paginate(query)


@router.get(
    "/{service_account_id}",
    response_model=UserResponse,
    operation_id="get_service_account",
)
async def get_service_account(
    service_account_id: UUID,
    _authorized: bool = Depends(rbac["read"]),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a specific service account by ID.

    Returns the service account details, or 404 if not found or not a service account.
    """
    user_repository = UserRepository(db)
    user = user_repository.get_user(service_account_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Service account not found"
        )

    if not user.service_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a service account",
        )

    return UserResponse.model_validate(user)


@router.put(
    "/{service_account_id}",
    response_model=UserResponse,
    operation_id="update_service_account",
)
async def update_service_account(
    service_account_id: UUID,
    service_account_update: ServiceAccountUpdateRequest,
    _authorized: bool = Depends(rbac["update"]),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update a service account by ID.

    Only the fields provided in the request will be updated.
    """
    update_command = UpdateServiceAccountCommand(db)
    try:
        updated_service_account = update_command.execute(
            service_account_id, service_account_update
        )
        return updated_service_account
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/{service_account_id}",
    operation_id="delete_service_account",
)
async def delete_service_account(
    service_account_id: UUID,
    _authorized: bool = Depends(rbac["delete"]),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a service account by ID.

    Permanently deletes the service account from the system.
    """
    delete_command = DeleteServiceAccountCommand(db)
    try:
        success = delete_command.execute(service_account_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Service account not found",
            )
        return {"message": "Service account deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/{service_account_id}/api-keys",
    response_model=Page[ApiKeyResponse],
    operation_id="list_service_account_api_keys",
)
async def list_service_account_api_keys(
    service_account_id: UUID,
    _authorized: bool = Depends(rbac["read"]),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all API keys for a specific service account.

    Returns a paginated list of API keys for the specified service account.
    """
    # Verify the service account exists
    user_repository = UserRepository(db)
    user = user_repository.get_user(service_account_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Service account not found"
        )

    if not user.service_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a service account",
        )

    api_key_repository = ApiKeyRepository(db)
    query = api_key_repository.get_user_api_keys_query(service_account_id)
    return paginate(query)


@router.post(
    "/{service_account_id}/api-keys",
    response_model=ApiKeyCreateResponse,
    operation_id="create_service_account_api_key",
)
async def create_service_account_api_key(
    service_account_id: UUID,
    api_key_data: ApiKeyCreateRequest,
    _authorized: bool = Depends(rbac["create"]),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new API key for a specific service account.

    Returns the new API key with the full key shown only once.
    """
    # Verify the service account exists
    user_repository = UserRepository(db)
    user = user_repository.get_user(service_account_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Service account not found"
        )

    if not user.service_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a service account",
        )

    create_api_key_command = CreateApiKeyCommand(db)

    # Create the API key
    api_key, full_key = create_api_key_command.execute(
        ApiKeyCreate(
            user_id=service_account_id,
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


@router.get(
    "/{service_account_id}/clients",
    response_model=list[ClientResponse],
    operation_id="list_service_account_clients",
)
async def list_service_account_clients(
    service_account_id: UUID,
    _authorized: bool = Depends(rbac["read"]),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_repository = UserRepository(db)
    user = user_repository.get_user(service_account_id)
    if not user or not user.service_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Service account not found"
        )

    return ClientRepository(db).list_by_owner(service_account_id)


@router.post(
    "/{service_account_id}/clients",
    response_model=ClientCreateResponse,
    operation_id="create_service_account_client",
    status_code=201,
)
async def create_service_account_client(
    service_account_id: UUID,
    body: ClientCreateRequest,
    _authorized: bool = Depends(rbac["create"]),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_repository = UserRepository(db)
    user = user_repository.get_user(service_account_id)
    if not user or not user.service_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Service account not found"
        )

    client, client_secret = CreateClientCommand(db).execute(
        ClientCreate(
            name=body.name, owner_id=service_account_id, created_by_id=current_user.id
        ),
        current_user,
    )
    response = ClientResponse.model_validate(client)
    return ClientCreateResponse(**response.model_dump(), client_secret=client_secret)
