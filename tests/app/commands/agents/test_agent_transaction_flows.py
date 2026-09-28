"""Agent flows are atomic under the managed transaction boundary.

Each test runs a command the way an entry point does (``execution_boundary``:
commit on success, roll back on error) and injects a failure partway through.
"""

import pytest

from app.commands.agents.claim_agent_command import ClaimAgentCommand
from app.commands.agents.create_agent_command import CreateAgentCommand
from app.commands.agents.revoke_agent_command import RevokeAgentCommand
from app.exceptions.agent_error import AgentClaimError
from app.models.agent_claim import AgentClaim
from app.models.client import Client
from app.models.user import User
from app.schemas.agent import AgentCreateRequest


def test_agent_is_never_created_without_its_claim(
    db, execution_boundary, publisher, monkeypatch
):
    command = CreateAgentCommand(db, nats_publisher=publisher)
    agents_before = db.query(User).count()

    def fail_claim(*args, **kwargs):
        raise RuntimeError("claim insert failed")

    monkeypatch.setattr(command.claims, "create_claim", fail_claim)

    with pytest.raises(RuntimeError, match="claim insert failed"):
        with execution_boundary():
            command.execute(AgentCreateRequest(name="Orphan"))

    assert db.query(User).count() == agents_before
    publisher.publish_sync.assert_not_called()


def test_agent_created_event_is_published_only_after_commit(
    db, execution_boundary, publisher
):
    with execution_boundary():
        CreateAgentCommand(db, nats_publisher=publisher).execute(
            AgentCreateRequest(name="Announced")
        )
        publisher.publish_sync.assert_not_called()

    publisher.publish_sync.assert_called_once()


def test_wrong_secret_attempt_survives_the_rollback(
    db, execution_boundary, publisher, created_agent
):
    """The failed-attempt count is committed before AgentClaimError is raised, so
    the entry point's rollback cannot erase the brute-force lockout counter."""
    _, code, _ = created_agent
    claim_id = code[3:].split(".")[0]

    with pytest.raises(AgentClaimError):
        with execution_boundary():
            ClaimAgentCommand(db, nats_publisher=publisher).execute(
                f"ac_{claim_id}.wrong"
            )

    claim = db.query(AgentClaim).filter(AgentClaim.claim_id == claim_id).one()
    assert claim.failed_attempts == 1


def test_revoke_failure_leaves_claims_and_clients_untouched(
    db, execution_boundary, publisher, claimed_agent, monkeypatch
):
    agent, client, _ = claimed_agent
    command = RevokeAgentCommand(db, nats_publisher=publisher)

    def fail_revoke(*args, **kwargs):
        raise RuntimeError("client revoke failed")

    monkeypatch.setattr(command.clients, "revoke_all_for_owner", fail_revoke)

    with pytest.raises(RuntimeError, match="client revoke failed"):
        with execution_boundary():
            command.execute(agent.id)

    db.expire_all()
    assert db.query(Client).filter(Client.id == client.id).one().revoked is False
    publisher.publish_sync.assert_not_called()
