"""
Utilities for building service account-related CloudEvents payloads.
"""

from __future__ import annotations

from uuid import UUID

from app.models.user import User as UserModel
from app.schemas.user import UserBase as UserSchema
from tessera_sdk.infra.events.event import Event, event_type, event_source

# Service account events
SERVICE_ACCOUNT_CREATED = "service_account.created"
SERVICE_ACCOUNT_UPDATED = "service_account.updated"
SERVICE_ACCOUNT_DELETED = "service_account.deleted"


def build_service_account_created_event(user: UserModel) -> Event:
    """Create a CloudEvent for service account creation."""
    user_schema = UserSchema.model_validate(user)

    return Event(
        source=event_source(),
        event_type=event_type(SERVICE_ACCOUNT_CREATED),
        event_data={"service_account": user_schema.model_dump(mode="json")},
        subject=f"/service-accounts/{user.id}",
        user_id=str(user.id),
        labels={
            "service_account_id": str(user.id),
            "user_id": str(user.id),
        },
        tags=[
            f"service_account_id:{str(user.id)}",
            f"user_id:{str(user.id)}",
        ],
    )


def build_service_account_deleted_event(user: UserModel, user_id: UUID) -> Event:
    """Create a CloudEvent for service account deletion."""
    user_schema = UserSchema.model_validate(user)

    return Event(
        source=event_source(),
        event_type=event_type(SERVICE_ACCOUNT_DELETED),
        event_data={"service_account": user_schema.model_dump(mode="json")},
        subject=f"/service-accounts/{user.id}",
        user_id=str(user_id),
        labels={
            "service_account_id": str(user.id),
            "user_id": str(user.id),
        },
        tags=[
            f"service_account_id:{str(user.id)}",
            f"user_id:{str(user.id)}",
        ],
    )


def build_service_account_updated_event(user: UserModel, user_id: UUID) -> Event:
    """Create a CloudEvent for service account updates."""
    user_schema = UserSchema.model_validate(user)

    return Event(
        source=event_source(),
        event_type=event_type(SERVICE_ACCOUNT_UPDATED),
        event_data={"service_account": user_schema.model_dump(mode="json")},
        subject=f"/service-accounts/{user.id}",
        user_id=str(user_id),
        labels={
            "service_account_id": str(user.id),
            "user_id": str(user.id),
        },
        tags=[
            f"service_account_id:{str(user.id)}",
            f"user_id:{str(user.id)}",
        ],
    )
