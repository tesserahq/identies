from uuid import uuid4

import pytest

from app.commands.agents.claim_agent_command import ClaimAgentCommand
from app.commands.agents.issue_agent_claim_command import IssueAgentClaimCommand
from app.exceptions.agent_error import (
    AgentAlreadyClaimedError,
    AgentClaimError,
    AgentNotFoundError,
)
from app.repositories.user_repository import UserRepository


def test_new_code_replaces_the_previous_one(db, publisher, created_agent):
    agent, old_code, _ = created_agent

    new_code, _ = IssueAgentClaimCommand(db).execute(agent.id)

    assert new_code != old_code
    with pytest.raises(AgentClaimError):
        ClaimAgentCommand(db, nats_publisher=publisher).execute(old_code)
    _, key = ClaimAgentCommand(db, nats_publisher=publisher).execute(new_code)
    assert key.startswith("ak_")


def test_cannot_issue_a_code_for_a_claimed_agent(db, publisher, created_agent):
    agent, code, _ = created_agent
    ClaimAgentCommand(db, nats_publisher=publisher).execute(code)

    with pytest.raises(AgentAlreadyClaimedError):
        IssueAgentClaimCommand(db).execute(agent.id)


def test_unknown_or_non_agent_users_are_not_found(
    db, setup_user, setup_service_account
):
    command = IssueAgentClaimCommand(db)

    for user_id in (uuid4(), setup_user.id, setup_service_account.id):
        with pytest.raises(AgentNotFoundError):
            command.execute(user_id)


def test_deleted_agent_is_not_found(db, created_agent):
    agent, _, _ = created_agent
    UserRepository(db).delete_user(agent.id)

    with pytest.raises(AgentNotFoundError):
        IssueAgentClaimCommand(db).execute(agent.id)
