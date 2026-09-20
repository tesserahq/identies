from unittest.mock import MagicMock

import pytest

from app.commands.agents.create_agent_command import CreateAgentCommand
from app.schemas.agent import AgentCreateRequest


@pytest.fixture
def publisher():
    return MagicMock()


@pytest.fixture
def created_agent(db, publisher):
    """An unclaimed agent: (agent, plaintext claim code, expires_at)."""
    return CreateAgentCommand(db, nats_publisher=publisher).execute(
        AgentCreateRequest(name="Claude")
    )


@pytest.fixture
def claimed_agent(db, publisher, created_agent):
    """A claimed agent: (agent, client, plaintext client secret)."""
    from app.commands.agents.claim_agent_command import ClaimAgentCommand

    agent, code, _ = created_agent
    client, secret = ClaimAgentCommand(db, nats_publisher=publisher).execute(code)
    publisher.reset_mock()
    return agent, client, secret
