from app.commands.agents.create_agent_command import CreateAgentCommand
from app.config import get_settings
from app.events.user_events import USER_CREATED
from app.models.agent_claim import AgentClaim
from app.schemas.agent import AgentCreateRequest
from app.schemas.user import UserResponse
from app.utils.security import parse_agent_claim_code


def test_creates_a_verified_agent_with_a_synthetic_email(db, created_agent):
    agent, code, expires_at = created_agent

    assert agent.kind == "agent"
    assert agent.first_name == "Claude"
    assert agent.verified is True
    assert agent.external_id.startswith("agent-")
    assert agent.email == f"agent-{agent.id}@{get_settings().agent_email_domain}"
    assert code.startswith("ac_")
    assert expires_at > agent.created_at.replace(tzinfo=expires_at.tzinfo)


def test_agent_email_passes_email_validation(created_agent):
    """.invalid/.test/.localhost are rejected by the validator, which would break every
    UserResponse and user event. The default agent domain must validate."""
    agent, _, _ = created_agent

    response = UserResponse.model_validate(agent)

    assert response.email == agent.email
    assert response.kind == "agent"
    assert response.service_account is True


def test_claim_is_stored_hashed_and_open(db, created_agent):
    agent, code, _ = created_agent
    claim_id, secret = parse_agent_claim_code(code)

    claim = db.query(AgentClaim).filter(AgentClaim.agent_user_id == agent.id).one()

    assert claim.claim_id == claim_id
    assert secret not in claim.secret_hash
    assert code not in claim.secret_hash
    assert claim.is_open()


def test_publishes_user_created_with_kind_agent(publisher, created_agent):
    agent, _, _ = created_agent

    publisher.publish_sync.assert_called_once()
    event = publisher.publish_sync.call_args.args[0]
    assert event.event_type.endswith(USER_CREATED)
    assert event.event_data["user"]["id"] == str(agent.id)
    assert event.event_data["user"]["kind"] == "agent"


def test_each_agent_gets_its_own_email_and_external_id(db, publisher):
    command = CreateAgentCommand(db, nats_publisher=publisher)
    first, _, _ = command.execute(AgentCreateRequest(name="One"))
    second, _, _ = command.execute(AgentCreateRequest(name="Two"))

    assert first.email != second.email
    assert first.external_id != second.external_id
