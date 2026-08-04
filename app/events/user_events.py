"""
Utilities for building user-related CloudEvents payloads.

These events are a projection contract: downstream Tessera services upsert a local
user row by Identies ``id`` from ``event_data["user"]``. See docs/user_events.md.
"""

from __future__ import annotations

from uuid import UUID

from app.models.user import User as UserModel
from app.schemas.user import User as UserSchema
from tessera_sdk.infra.events.event import Event, event_type, event_source

# User events
USER_CREATED = "user.created"
USER_UPDATED = "user.updated"
USER_DELETED = "user.deleted"
USER_OFFBOARDING_SCHEDULED = "user.offboarding_scheduled"


def build_user_created_event(user: UserModel) -> Event:
    """Create a CloudEvent for user creation."""
    user_schema = UserSchema.model_validate(user)

    return Event(
        source=event_source(),
        event_type=event_type(USER_CREATED),
        event_data={"user": user_schema.model_dump(mode="json")},
        subject=f"/users/{user.id}",
        user_id=str(user.id),
        labels={
            "user_id": str(user.id),
        },
        tags=[
            f"user_id:{str(user.id)}",
        ],
    )


def build_user_deleted_event(user: UserModel, user_id: UUID) -> Event:
    """Create a CloudEvent for user deletion."""
    user_schema = UserSchema.model_validate(user)

    return Event(
        source=event_source(),
        event_type=event_type(USER_DELETED),
        event_data={"user": user_schema.model_dump(mode="json")},
        subject=f"/users/{user.id}",
        user_id=str(user_id),
        labels={
            "user_id": str(user.id),
        },
        tags=[f"user_id:{str(user.id)}"],
    )


def build_user_offboarding_scheduled_event(
    user: UserModel, scheduled_by: UUID
) -> Event:
    """Create a CloudEvent for a scheduled (not yet executed) user offboarding."""
    user_schema = UserSchema.model_validate(user)

    return Event(
        source=event_source(),
        event_type=event_type(USER_OFFBOARDING_SCHEDULED),
        event_data={
            "user": user_schema.model_dump(mode="json"),
            "offboarding_scheduled_at": (
                user.offboarding_scheduled_at.isoformat()
                if user.offboarding_scheduled_at
                else None
            ),
            "offboarding_scheduled_by": str(scheduled_by),
        },
        subject=f"/users/{user.id}",
        user_id=str(scheduled_by),
        labels={
            "user_id": str(user.id),
        },
        tags=[f"user_id:{str(user.id)}"],
    )


def build_user_updated_event(user: UserModel, user_id: UUID) -> Event:
    """Create a CloudEvent for user updates."""
    user_schema = UserSchema.model_validate(user)

    return Event(
        source=event_source(),
        event_type=event_type(USER_UPDATED),
        event_data={"user": user_schema.model_dump(mode="json")},
        subject=f"/users/{user.id}",
        user_id=str(user_id),
        labels={
            "user_id": str(user.id),
        },
        tags=[f"user_id:{str(user.id)}"],
    )
