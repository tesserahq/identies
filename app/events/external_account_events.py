"""
Utilities for building external account and link token CloudEvents payloads.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from app.models.external_account import ExternalAccount as ExternalAccountModel
from app.models.user import User as UserModel
from app.schemas.external_account import ExternalAccountResponse
from app.schemas.user import UserResponse as UserSchema
from tessera_sdk.events.event import Event, event_source, event_type

# External account and link token events
LINK_TOKEN_CREATED = "link_token.created"
EXTERNAL_ACCOUNT_LINKED = "external_account.linked"
EXTERNAL_ACCOUNT_DELETED = "external_account.deleted"


def build_link_token_created_event(
    platform: str,
    external_user_id: str,
    expires_at: datetime,
    data: Optional[dict[str, Any]] = None,
) -> Event:
    """Create a CloudEvent for link token creation (backend/webhook flow, no user)."""
    return Event(
        source=event_source(),
        event_type=event_type(LINK_TOKEN_CREATED),
        event_data={
            "platform": platform,
            "external_user_id": external_user_id,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "data": data or {},
        },
        subject=f"/link-tokens/{platform}/{external_user_id}",
        user_id="system",
        labels={
            "platform": platform,
            "external_user_id": external_user_id,
        },
        tags=[
            f"platform:{platform}",
            f"external_user_id:{external_user_id}",
        ],
    )


def build_external_account_linked_event(
    external_account: ExternalAccountModel,
    user: UserModel,
) -> Event:
    """Create a CloudEvent for external account linking."""
    account_schema = ExternalAccountResponse.model_validate(external_account)
    user_schema = UserSchema.model_validate(user)

    return Event(
        source=event_source(),
        event_type=event_type(EXTERNAL_ACCOUNT_LINKED),
        event_data={
            "external_account": account_schema.model_dump(mode="json"),
            "user": user_schema.model_dump(mode="json"),
        },
        subject=f"/external-accounts/{external_account.id}",
        user_id=str(user.id),
        labels={
            "external_account_id": str(external_account.id),
            "user_id": str(user.id),
            "platform": external_account.platform,
        },
        tags=[
            f"external_account_id:{str(external_account.id)}",
            f"user_id:{str(user.id)}",
            f"platform:{external_account.platform}",
        ],
    )


def build_external_account_deleted_event(
    external_account: ExternalAccountModel,
    user: UserModel,
) -> Event:
    """Create a CloudEvent for external account deletion."""
    account_schema = ExternalAccountResponse.model_validate(external_account)
    user_schema = UserSchema.model_validate(user)

    return Event(
        source=event_source(),
        event_type=event_type(EXTERNAL_ACCOUNT_DELETED),
        event_data={
            "external_account": account_schema.model_dump(mode="json"),
            "user": user_schema.model_dump(mode="json"),
        },
        subject=f"/external-accounts/{external_account.id}",
        user_id=str(user.id),
        labels={
            "external_account_id": str(external_account.id),
            "user_id": str(user.id),
            "platform": external_account.platform,
        },
        tags=[
            f"external_account_id:{str(external_account.id)}",
            f"user_id:{str(user.id)}",
            f"platform:{external_account.platform}",
        ],
    )
