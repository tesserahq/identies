from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate

from app.commands.system_accounts.create_system_account_command import (
    CreateSystemAccountCommand,
)
from app.commands.system_accounts.update_system_account_command import (
    UpdateSystemAccountCommand,
)
from app.commands.system_accounts.delete_system_account_command import (
    DeleteSystemAccountCommand,
)
from app.commands.api_keys.create_api_key_command import CreateApiKeyCommand
from app.db import get_db
from app.utils.auth import get_current_user
from app.schemas.system_account import (
    SystemAccountCreateRequest,
    SystemAccountUpdateRequest,
)
from app.schemas.user import UserResponse
from app.schemas.api_key import (
    ApiKeyCreate,
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeyResponse,
)
from app.services.user_service import UserService
from app.services.api_key_service import ApiKeyService
from app.models.user import User

router = APIRouter(prefix="/system-accounts", tags=["System Accounts"])


@router.post("", response_model=UserResponse, operation_id="create_system_account")
async def create_system_account(
    system_account_data: SystemAccountCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new system account.

    System accounts are users with service_account=True and don't have passwords.
    They authenticate using API keys.
    """
    create_command = CreateSystemAccountCommand(db)
    try:
        system_account = create_command.execute(system_account_data)
        return system_account
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("", response_model=Page[UserResponse], operation_id="list_system_accounts")
async def list_system_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all system accounts.

    Returns a paginated list of system accounts (users with service_account=True).
    """
    user_service = UserService(db)
    query = user_service.get_system_accounts_query()
    return paginate(query)


@router.get(
    "/{system_account_id}",
    response_model=UserResponse,
    operation_id="get_system_account",
)
async def get_system_account(
    system_account_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a specific system account by ID.

    Returns the system account details, or 404 if not found or not a system account.
    """
    user_service = UserService(db)
    user = user_service.get_user(system_account_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="System account not found"
        )

    if not user.service_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a system account",
        )

    return UserResponse.model_validate(user)


@router.put(
    "/{system_account_id}",
    response_model=UserResponse,
    operation_id="update_system_account",
)
async def update_system_account(
    system_account_id: UUID,
    system_account_update: SystemAccountUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update a system account by ID.

    Only the fields provided in the request will be updated.
    """
    update_command = UpdateSystemAccountCommand(db)
    try:
        updated_system_account = update_command.execute(
            system_account_id, system_account_update
        )
        return updated_system_account
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/{system_account_id}",
    operation_id="delete_system_account",
)
async def delete_system_account(
    system_account_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a system account by ID.

    Permanently deletes the system account from the system.
    """
    delete_command = DeleteSystemAccountCommand(db)
    try:
        success = delete_command.execute(system_account_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="System account not found",
            )
        return {"message": "System account deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/{system_account_id}/api-keys",
    response_model=Page[ApiKeyResponse],
    operation_id="list_system_account_api_keys",
)
async def list_system_account_api_keys(
    system_account_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all API keys for a specific system account.

    Returns a paginated list of API keys for the specified system account.
    """
    # Verify the system account exists
    user_service = UserService(db)
    user = user_service.get_user(system_account_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="System account not found"
        )

    if not user.service_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a system account",
        )

    api_key_service = ApiKeyService(db)
    query = api_key_service.get_user_api_keys_query(system_account_id)
    return paginate(query)


@router.post(
    "/{system_account_id}/api-keys",
    response_model=ApiKeyCreateResponse,
    operation_id="create_system_account_api_key",
)
async def create_system_account_api_key(
    system_account_id: UUID,
    api_key_data: ApiKeyCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new API key for a specific system account.

    Returns the new API key with the full key shown only once.
    """
    # Verify the system account exists
    user_service = UserService(db)
    user = user_service.get_user(system_account_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="System account not found"
        )

    if not user.service_account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not a system account",
        )

    create_api_key_command = CreateApiKeyCommand(db)

    # Create the API key
    api_key, full_key = create_api_key_command.execute(
        ApiKeyCreate(
            user_id=system_account_id,
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
