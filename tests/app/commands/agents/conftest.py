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
