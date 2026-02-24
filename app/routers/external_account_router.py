"""Router for external accounts and link tokens."""

from typing import Optional, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy.orm import Session

from app.commands.external_accounts.create_link_token_command import (
    CreateLinkTokenCommand,
)
from app.commands.external_accounts.delete_external_account_command import (
    DeleteExternalAccountCommand,
)
from app.commands.external_accounts.link_external_account_command import (
    LinkExternalAccountCommand,
)
from app.db import get_db
from app.models.user import User
from app.models.user import User as UserModel
from app.schemas.user import UserResponse
from app.routers.utils.dependencies import get_current_user, get_user_by_id
from app.schemas.external_account import (
    CheckRequest,
    CheckResponse,
    ExternalAccountResponse,
    LinkRequest,
    LinkTokenCreateRequest,
    LinkTokenResponse,
)
from app.services.external_account_service import ExternalAccountService
from app.auth.rbac import build_rbac_dependencies

router = APIRouter(prefix="/external-accounts", tags=["External Accounts"])


async def infer_domain(_request: Request) -> str:
    return "*"


RESOURCE = "external_account"
rbac_external_account = build_rbac_dependencies(
    resource=RESOURCE,
    domain_resolver=infer_domain,
)

RESOURCE = "user"
rbac_user = build_rbac_dependencies(
    resource=RESOURCE,
    domain_resolver=infer_domain,
)


@router.post(
    "/link-tokens",
    response_model=LinkTokenResponse,
    operation_id="create_link_token",
)
async def create_link_token(
    body: LinkTokenCreateRequest,
    db: Session = Depends(get_db),
):
    """
    Create a short-lived, single-use link token.

    Intended for backend/webhook use (e.g. external platform creates token
    when user starts linking). Protect this endpoint at network or with
    API key if needed.
    """
    command = CreateLinkTokenCommand(db)
    token_value, expires_at = command.execute(body)
    return LinkTokenResponse(token=token_value, expires_at=expires_at)


@router.post(
    "/link",
    response_model=ExternalAccountResponse,
    operation_id="link_external_account",
)
async def link_external_account(
    body: LinkRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Link the current user to the external account referenced by the token.

    Validates token, creates ExternalAccount, invalidates token.
    Returns 400/404 if token is invalid, expired, or already used.
    Returns 409 if the external account is already linked to another user.
    """
    command = LinkExternalAccountCommand(db)
    account = command.execute(body, current_user)
    return ExternalAccountResponse.model_validate(account)


@router.post(
    "/check",
    response_model=CheckResponse,
    operation_id="check_external_account",
)
async def check_external_account(
    body: CheckRequest,
    db: Session = Depends(get_db),
    _rbac_external_account: bool = Depends(rbac_external_account["read"]),
):
    """
    Check if an external account (platform + external_id) is linked to a user.
    Returns linked status, user, and external_account when found.
    """
    service = ExternalAccountService(db)
    account = service.get_external_account_by_platform_and_external_id(
        body.platform, body.external_id
    )
    if account is None:
        return CheckResponse(linked=False, user=None, external_accounts=None)
    user = account.user
    return CheckResponse(
        linked=True,
        user=UserResponse.model_validate(user),
        external_accounts=ExternalAccountResponse.model_validate(account),
    )


@router.get(
    "",
    response_model=Page[ExternalAccountResponse],
    operation_id="list_external_accounts",
)
async def list_external_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    platform: Optional[str] = Query(
        None,
        description="Filter by platform (e.g. telegram)",
    ),
):
    """
    List external accounts for the current user (paginated).
    """
    service = ExternalAccountService(db)
    user_id = cast(UUID, current_user.id)
    query = service.get_external_accounts_query(user_id, platform=platform)
    return paginate(query)


@router.get(
    "/users/{user_id}",
    response_model=Page[ExternalAccountResponse],
    operation_id="list_user_external_accounts",
)
async def list_user_external_accounts(
    user: UserModel = Depends(get_user_by_id),
    _rbac_external_account: bool = Depends(rbac_external_account["read"]),
    _rbac_user: bool = Depends(rbac_user["read"]),
    db: Session = Depends(get_db),
    platform: Optional[str] = Query(
        None,
        description="Filter by platform (e.g. telegram)",
    ),
):
    """
    List external accounts for a specific user (paginated).
    """
    service = ExternalAccountService(db)
    user_id = cast(UUID, user.id)
    query = service.get_external_accounts_query(user_id, platform=platform)
    return paginate(query)


@router.delete(
    "/{external_account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_external_account",
)
async def delete_external_account(
    external_account_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Unlink an external account. Only the owner can delete.
    """
    command = DeleteExternalAccountCommand(db)
    command.execute(external_account_id, current_user)
