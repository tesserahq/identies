"""
Utilities for building api_key-related CloudEvents payloads.
"""

from __future__ import annotations

from ast import List
from typing import Dict, Any
from uuid import UUID

from app.models.api_key import ApiKey as ApiKeyModel
from app.schemas.api_key import ApiKeyBase as ApiKeySchema
from tessera_sdk.events.event import Event, event_type, event_source

# ApiKey events
API_KEY_CREATED = "api_key.created"
API_KEY_UPDATED = "api_key.updated"
API_KEY_DELETED = "api_key.deleted"


def build_api_key_created_event(api_key: ApiKeyModel) -> Event:
    """Create a CloudEvent for api_key-related operations."""
    api_key_schema = ApiKeySchema.model_validate(api_key)

    return Event(
        source=event_source(f"/api_keys/{api_key.id}"),
        event_type=event_type(API_KEY_CREATED),
        event_data={"api_key": api_key_schema.model_dump(mode="json")},
        subject=f"/api_key/{api_key.id}",
        user_id=str(api_key.user_id),
        labels={
            "api_key_id": str(api_key.id),
        },
        tags=[
            f"api_key_id:{str(api_key.id)}",
        ],
    )


def build_api_key_deleted_event(api_key: ApiKeyModel, user_id: UUID) -> Event:
    """Create a CloudEvent for api_key-related operations."""
    api_key_schema = ApiKeySchema.model_validate(api_key)

    return Event(
        source=event_source(f"/api_keys/{api_key.id}"),
        event_type=event_type(API_KEY_DELETED),
        event_data={"api_key": api_key_schema.model_dump(mode="json")},
        subject=f"/api_key/{api_key.id}",
        user_id=str(user_id),
        labels={
            "api_key_id": str(api_key.id),
        },
        tags=[f"api_key_id:{str(api_key.id)}"],
    )


def build_api_key_updated_event(api_key: ApiKeyModel, user_id: UUID) -> Event:
    """Create a CloudEvent for api_key-related operations."""
    api_key_schema = ApiKeySchema.model_validate(api_key)

    return Event(
        source=event_source(f"/api_keys/{api_key.id}"),
        event_type=event_type(API_KEY_UPDATED),
        event_data={"api_key": api_key_schema.model_dump(mode="json")},
        subject=f"/api_key/{api_key.id}",
        user_id=str(user_id),
        labels={
            "api_key_id": str(api_key.id),
        },
        tags=[f"api_key_id:{str(api_key.id)}"],
    )
