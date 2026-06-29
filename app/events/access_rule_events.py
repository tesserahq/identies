"""
Utilities for building access_rule-related CloudEvents payloads.
"""

from __future__ import annotations

from app.models.access_rule import AccessRule as AccessRuleModel
from app.models.user import User as UserModel
from app.schemas.access_rule import AccessRule as AccessRuleSchema
from app.schemas.user import UserResponse as UserSchema
from tessera_sdk.infra.events.event import Event, event_source, event_type

ACCESS_RULE_CREATED = "access_rule.created"
ACCESS_RULE_UPDATED = "access_rule.updated"
ACCESS_RULE_DELETED = "access_rule.deleted"


def build_access_rule_created_event(
    access_rule: AccessRuleModel, user: UserModel
) -> Event:
    """Create a CloudEvent for access rule creation."""
    access_rule_schema = AccessRuleSchema.model_validate(access_rule)
    user_schema = UserSchema.model_validate(user)

    return Event(
        source=event_source(),
        event_type=event_type(ACCESS_RULE_CREATED),
        event_data={
            "access_rule": access_rule_schema.model_dump(mode="json"),
            "user": user_schema.model_dump(mode="json"),
        },
        subject=f"/access-rules/{access_rule.id}",
        user_id=str(user.id),
        labels={
            "access_rule_id": str(access_rule.id),
        },
        tags=[
            f"access_rule_id:{str(access_rule.id)}",
        ],
    )


def build_access_rule_updated_event(
    access_rule: AccessRuleModel, user: UserModel
) -> Event:
    """Create a CloudEvent for access rule update."""
    access_rule_schema = AccessRuleSchema.model_validate(access_rule)
    user_schema = UserSchema.model_validate(user)

    return Event(
        source=event_source(),
        event_type=event_type(ACCESS_RULE_UPDATED),
        event_data={
            "access_rule": access_rule_schema.model_dump(mode="json"),
            "user": user_schema.model_dump(mode="json"),
        },
        subject=f"/access-rules/{access_rule.id}",
        user_id=str(user.id),
        labels={
            "access_rule_id": str(access_rule.id),
        },
        tags=[f"access_rule_id:{str(access_rule.id)}"],
    )


def build_access_rule_deleted_event(
    access_rule: AccessRuleModel, user: UserModel
) -> Event:
    """Create a CloudEvent for access rule deletion."""
    access_rule_schema = AccessRuleSchema.model_validate(access_rule)
    user_schema = UserSchema.model_validate(user)

    return Event(
        source=event_source(),
        event_type=event_type(ACCESS_RULE_DELETED),
        event_data={
            "access_rule": access_rule_schema.model_dump(mode="json"),
            "user": user_schema.model_dump(mode="json"),
        },
        subject=f"/access-rules/{access_rule.id}",
        user_id=str(user.id),
        labels={
            "access_rule_id": str(access_rule.id),
        },
        tags=[f"access_rule_id:{str(access_rule.id)}"],
    )
