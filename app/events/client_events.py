from __future__ import annotations

from app.models.client import Client as ClientModel
from app.models.user import User as UserModel
from app.schemas.client import ClientResponse as ClientSchema
from app.schemas.user import UserResponse as UserSchema
from tessera_sdk.infra.events.event import Event, event_source, event_type

CLIENT_CREATED = "client.created"
CLIENT_REVOKED = "client.revoked"
CLIENT_DELETED = "client.deleted"


def _build_client_event(
    event_type_str: str, client: ClientModel, user: UserModel
) -> Event:
    return Event(
        source=event_source(),
        event_type=event_type(event_type_str),
        event_data={
            "client": ClientSchema.model_validate(client).model_dump(mode="json"),
            "user": UserSchema.model_validate(user).model_dump(mode="json"),
        },
        subject=f"/clients/{client.id}",
        user_id=str(user.id),
        labels={"client_id": str(client.id)},
        tags=[f"client_id:{str(client.id)}"],
    )


def build_client_created_event(client: ClientModel, user: UserModel) -> Event:
    return _build_client_event(CLIENT_CREATED, client, user)


def build_client_revoked_event(client: ClientModel, user: UserModel) -> Event:
    return _build_client_event(CLIENT_REVOKED, client, user)


def build_client_deleted_event(client: ClientModel, user: UserModel) -> Event:
    return _build_client_event(CLIENT_DELETED, client, user)
