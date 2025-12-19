from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.commands.system_accounts.create_system_account_command import (
    CreateSystemAccountCommand,
)
from app.commands.system_accounts.update_system_account_command import (
    UpdateSystemAccountCommand,
)
from app.commands.system_accounts.delete_system_account_command import (
    DeleteSystemAccountCommand,
)
from app.db import get_db
from app.utils.auth import get_current_user
from app.schemas.system_account import (
    SystemAccountCreateRequest,
    SystemAccountUpdateRequest,
    SystemAccountListResponse,
)
from app.schemas.user import UserResponse
from app.services.user_service import UserService
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


@router.get(
    "", response_model=SystemAccountListResponse, operation_id="list_system_accounts"
)
async def list_system_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
):
    """
    List all system accounts.

    Returns a paginated list of system accounts (users with service_account=True).
    """
    user_service = UserService(db)
    # Filter users by service_account=True
    filters = {"service_account": True}
    system_accounts = user_service.search(filters)

    # Apply pagination
    paginated_accounts = system_accounts[skip : skip + limit]

    return SystemAccountListResponse(
        data=[UserResponse.model_validate(account) for account in paginated_accounts]
    )


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
