"""
Utilities for building system account-related CloudEvents payloads.
"""

from __future__ import annotations

from typing import Dict, Any
from uuid import UUID

from app.models.user import User as UserModel
from app.schemas.user import UserBase as UserSchema
from tessera_sdk.events.event import Event, event_type, event_source

# System account events
SYSTEM_ACCOUNT_CREATED = "system_account.created"
SYSTEM_ACCOUNT_UPDATED = "system_account.updated"
SYSTEM_ACCOUNT_DELETED = "system_account.deleted"


def build_system_account_created_event(user: UserModel) -> Event:
    """Create a CloudEvent for system account creation."""
    user_schema = UserSchema.model_validate(user)

    return Event(
        source=event_source(f"/system-accounts/{user.id}"),
        event_type=event_type(SYSTEM_ACCOUNT_CREATED),
        event_data={"system_account": user_schema.model_dump(mode="json")},
        subject=f"/system-account/{user.id}",
        user_id=str(user.id),
        labels={
            "system_account_id": str(user.id),
            "user_id": str(user.id),
        },
        tags=[
            f"system_account_id:{str(user.id)}",
            f"user_id:{str(user.id)}",
        ],
    )


def build_system_account_deleted_event(user: UserModel, user_id: UUID) -> Event:
    """Create a CloudEvent for system account deletion."""
    user_schema = UserSchema.model_validate(user)

    return Event(
        source=event_source(f"/system-accounts/{user.id}"),
        event_type=event_type(SYSTEM_ACCOUNT_DELETED),
        event_data={"system_account": user_schema.model_dump(mode="json")},
        subject=f"/system-account/{user.id}",
        user_id=str(user_id),
        labels={
            "system_account_id": str(user.id),
            "user_id": str(user.id),
        },
        tags=[
            f"system_account_id:{str(user.id)}",
            f"user_id:{str(user.id)}",
        ],
    )


def build_system_account_updated_event(user: UserModel, user_id: UUID) -> Event:
    """Create a CloudEvent for system account updates."""
    user_schema = UserSchema.model_validate(user)

    return Event(
        source=event_source(f"/system-accounts/{user.id}"),
        event_type=event_type(SYSTEM_ACCOUNT_UPDATED),
        event_data={"system_account": user_schema.model_dump(mode="json")},
        subject=f"/system-account/{user.id}",
        user_id=str(user_id),
        labels={
            "system_account_id": str(user.id),
            "user_id": str(user.id),
        },
        tags=[
            f"system_account_id:{str(user.id)}",
            f"user_id:{str(user.id)}",
        ],
    )
