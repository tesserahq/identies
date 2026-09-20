from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.commands.agents.claim_agent_command import ClaimAgentCommand
from app.commands.agents.delete_agent_command import DeleteAgentCommand
from app.commands.agents.revoke_agent_command import RevokeAgentCommand
from app.commands.agents.rotate_agent_credentials_command import (
    RotateAgentCredentialsCommand,
)
from app.config import get_settings
from app.events.client_events import CLIENT_REVOKED, CLIENT_ROTATED
from app.events.user_events import USER_DELETED
from app.exceptions.agent_error import (
    AgentClaimError,
    AgentNotClaimedError,
    AgentNotFoundError,
)
from app.models.api_key import ApiKey
from app.repositories.agent_repository import AgentRepository
from app.repositories.client_repository import ClientRepository
from app.repositories.user_repository import UserRepository
from app.utils.security import generate_api_key, hash_secret, parse_api_key


def can_mint(db, client, secret) -> bool:
    return ClientRepository(db).verify_client(client.client_id, secret) is not None


def event_types(publisher) -> list[str]:
    return [c.args[0].event_type for c in publisher.publish_sync.call_args_list]


# ---- rotate -------------------------------------------------------------------------


def test_rotate_replaces_the_secret_and_keeps_the_client_id(
    db, publisher, claimed_agent
):
    _, client, old_secret = claimed_agent
    client_id = client.client_id

    rotated, new_secret = RotateAgentCredentialsCommand(
        db, nats_publisher=publisher
    ).execute(client.owner_id)

    assert rotated.client_id == client_id
    assert new_secret != old_secret
    assert not can_mint(db, rotated, old_secret)
    assert can_mint(db, rotated, new_secret)


def test_rotate_restarts_the_expiry(db, publisher, claimed_agent):
    _, client, _ = claimed_agent
    client.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    db.commit()

    rotated, _ = RotateAgentCredentialsCommand(db, nats_publisher=publisher).execute(
        client.owner_id
    )

    expected = datetime.now(timezone.utc) + timedelta(
        days=get_settings().agent_client_secret_ttl_days
    )
    assert abs((rotated.expires_at - expected).total_seconds()) < 60


def test_rotate_restores_a_revoked_agent(db, publisher, claimed_agent):
    agent, client, _ = claimed_agent
    RevokeAgentCommand(db, nats_publisher=publisher).execute(agent.id)

    rotated, new_secret = RotateAgentCredentialsCommand(
        db, nats_publisher=publisher
    ).execute(agent.id)

    assert rotated.revoked is False
    assert can_mint(db, rotated, new_secret)


def test_rotate_renews_an_expired_secret(db, publisher, claimed_agent):
    agent, client, _ = claimed_agent
    client.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()

    rotated, new_secret = RotateAgentCredentialsCommand(
        db, nats_publisher=publisher
    ).execute(agent.id)

    assert can_mint(db, rotated, new_secret)


def test_rotate_refuses_an_unclaimed_agent(db, publisher, created_agent):
    agent, _, _ = created_agent

    with pytest.raises(AgentNotClaimedError):
        RotateAgentCredentialsCommand(db, nats_publisher=publisher).execute(agent.id)


def test_rotate_publishes_client_rotated_without_the_secret(
    db, publisher, claimed_agent
):
    agent, _, _ = claimed_agent

    _, new_secret = RotateAgentCredentialsCommand(db, nats_publisher=publisher).execute(
        agent.id
    )

    types = event_types(publisher)
    assert len(types) == 1 and types[0].endswith(CLIENT_ROTATED)
    assert new_secret not in str(publisher.publish_sync.call_args.args[0].event_data)


# ---- revoke -------------------------------------------------------------------------


def test_revoke_stops_the_agent_minting_tokens(db, publisher, claimed_agent):
    agent, client, secret = claimed_agent
    assert can_mint(db, client, secret)

    RevokeAgentCommand(db, nats_publisher=publisher).execute(agent.id)

    assert not can_mint(db, client, secret)
    assert AgentRepository(db).get_status(agent).state == "revoked"


def test_revoke_is_idempotent_and_publishes_once(db, publisher, claimed_agent):
    agent, _, _ = claimed_agent
    command = RevokeAgentCommand(db, nats_publisher=publisher)

    command.execute(agent.id)
    command.execute(agent.id)

    types = event_types(publisher)
    assert len(types) == 1 and types[0].endswith(CLIENT_REVOKED)


def test_revoke_invalidates_an_open_claim_code(db, publisher, created_agent):
    agent, code, _ = created_agent

    RevokeAgentCommand(db, nats_publisher=publisher).execute(agent.id)

    with pytest.raises(AgentClaimError):
        ClaimAgentCommand(db, nats_publisher=publisher).execute(code)


def test_revoke_also_revokes_any_api_key_the_agent_has(db, publisher, claimed_agent):
    from app.repositories.api_key_repository import ApiKeyRepository

    agent, _, _ = claimed_agent
    full_key, _ = generate_api_key()
    key_id, secret = parse_api_key(full_key)
    db.add(
        ApiKey(
            user_id=agent.id, key_id=key_id, secret_hash=hash_secret(secret), name="k"
        )
    )
    db.commit()
    assert ApiKeyRepository(db).verify_api_key(full_key) is not None

    RevokeAgentCommand(db, nats_publisher=publisher).execute(agent.id)

    assert ApiKeyRepository(db).verify_api_key(full_key) is None


# ---- delete -------------------------------------------------------------------------


def test_delete_soft_deletes_the_agent_and_cuts_off_its_credentials(
    db, publisher, claimed_agent
):
    agent, client, secret = claimed_agent
    agent_id = agent.id

    DeleteAgentCommand(db, nats_publisher=publisher).execute(agent_id)

    users = UserRepository(db)
    assert users.get_user(agent_id) is None
    tombstone = users.get_user(agent_id, include_deleted=True)
    assert tombstone is not None and tombstone.deleted_at is not None
    assert not can_mint(db, client, secret)


def test_delete_stops_an_unused_claim_code_working(db, publisher, created_agent):
    agent, code, _ = created_agent

    DeleteAgentCommand(db, nats_publisher=publisher).execute(agent.id)

    with pytest.raises(AgentClaimError):
        ClaimAgentCommand(db, nats_publisher=publisher).execute(code)


def test_delete_publishes_user_deleted_for_the_agent(db, publisher, claimed_agent):
    agent, _, _ = claimed_agent

    DeleteAgentCommand(db, nats_publisher=publisher).execute(agent.id)

    event = publisher.publish_sync.call_args.args[0]
    assert event.event_type.endswith(USER_DELETED)
    assert event.event_data["user"]["id"] == str(agent.id)
    assert event.event_data["user"]["kind"] == "agent"


def test_delete_cannot_be_used_on_a_human_or_service_account(
    db, publisher, setup_user, setup_service_account
):
    for user in (setup_user, setup_service_account):
        with pytest.raises(AgentNotFoundError):
            DeleteAgentCommand(db, nats_publisher=publisher).execute(user.id)
        assert UserRepository(db).get_user(user.id) is not None


def test_a_deleted_agent_is_not_found(db, publisher, claimed_agent):
    agent, _, _ = claimed_agent
    DeleteAgentCommand(db, nats_publisher=publisher).execute(agent.id)

    for command in (
        DeleteAgentCommand(db, nats_publisher=publisher),
        RevokeAgentCommand(db, nats_publisher=publisher),
        RotateAgentCredentialsCommand(db, nats_publisher=publisher),
    ):
        with pytest.raises(AgentNotFoundError):
            command.execute(agent.id)


@pytest.mark.parametrize(
    "command",
    [DeleteAgentCommand, RevokeAgentCommand, RotateAgentCredentialsCommand],
)
def test_lifecycle_commands_reject_unknown_ids(db, publisher, command):
    with pytest.raises(AgentNotFoundError):
        command(db, nats_publisher=publisher).execute(uuid4())


@pytest.mark.parametrize(
    "command",
    [DeleteAgentCommand, RevokeAgentCommand, RotateAgentCredentialsCommand],
)
def test_lifecycle_commands_reject_humans_and_service_accounts(
    db, publisher, setup_user, setup_service_account, command
):
    for user in (setup_user, setup_service_account):
        with pytest.raises(AgentNotFoundError):
            command(db, nats_publisher=publisher).execute(user.id)


# ---- status and last used -----------------------------------------------------------


def test_status_of_an_unclaimed_agent_shows_the_open_claim(db, created_agent):
    agent, _, claim_expires_at = created_agent

    status = AgentRepository(db).get_status(agent)

    assert status.state == "unclaimed"
    assert status.client is None
    assert status.claim_expires_at == claim_expires_at


def test_status_of_an_unclaimed_agent_without_an_open_claim(
    db, publisher, created_agent
):
    agent, _, _ = created_agent
    RevokeAgentCommand(db, nats_publisher=publisher).execute(agent.id)

    status = AgentRepository(db).get_status(agent)

    assert status.state == "unclaimed"
    assert status.claim_expires_at is None


def test_status_active_expired_and_revoked(db, publisher, claimed_agent):
    agent, client, _ = claimed_agent
    repository = AgentRepository(db)
    assert repository.get_status(agent).state == "active"

    client.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()
    assert repository.get_status(agent).state == "expired"

    RevokeAgentCommand(db, nats_publisher=publisher).execute(agent.id)
    assert repository.get_status(agent).state == "revoked"


def test_last_used_is_recorded_when_the_credentials_mint_a_token(db, claimed_agent):
    agent, client, secret = claimed_agent
    assert AgentRepository(db).get_status(agent).client.last_used_at is None

    assert can_mint(db, client, secret)

    last_used = AgentRepository(db).get_status(agent).client.last_used_at
    assert last_used is not None
    assert abs((datetime.now(timezone.utc) - last_used).total_seconds()) < 60


def test_a_failed_attempt_does_not_count_as_use(db, claimed_agent):
    agent, client, _ = claimed_agent

    assert not can_mint(db, client, "wrong-secret")

    assert AgentRepository(db).get_status(agent).client.last_used_at is None
