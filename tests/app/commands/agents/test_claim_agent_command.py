import threading
import time
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.commands.agents import claim_agent_command as claim_module
from app.commands.agents.claim_agent_command import ClaimAgentCommand
from app.commands.agents.create_agent_command import CreateAgentCommand
from app.config import get_settings
from app.events.api_key_events import API_KEY_CREATED
from app.exceptions.agent_error import AgentClaimError
from app.models.agent_claim import AgentClaim
from app.models.api_key import ApiKey
from app.models.user import User
from app.repositories.api_key_repository import ApiKeyRepository
from app.repositories.user_repository import UserRepository
from app.schemas.agent import AgentCreateRequest


def test_claim_returns_a_working_key_for_the_agent(db, publisher, created_agent):
    agent, code, _ = created_agent

    api_key, full_key = ClaimAgentCommand(db, nats_publisher=publisher).execute(code)

    assert full_key.startswith("ak_")
    assert api_key.user_id == agent.id
    verified = ApiKeyRepository(db).verify_api_key(full_key)
    assert verified is not None and verified.user_id == agent.id


def test_key_expires_after_the_configured_ttl(db, publisher, created_agent):
    _, code, _ = created_agent
    api_key, _ = ClaimAgentCommand(db, nats_publisher=publisher).execute(code)

    expected = datetime.now(timezone.utc) + timedelta(
        days=get_settings().agent_api_key_ttl_days
    )
    expires_at = api_key.expires_at.replace(
        tzinfo=api_key.expires_at.tzinfo or timezone.utc
    )
    assert abs((expires_at - expected).total_seconds()) < 60


def test_the_secret_is_never_stored(db, publisher, created_agent):
    _, code, _ = created_agent
    _, full_key = ClaimAgentCommand(db, nats_publisher=publisher).execute(code)

    stored = db.query(ApiKey).filter(ApiKey.key_id == full_key[3:].split(".")[0]).one()
    assert full_key.split(".")[1] not in stored.secret_hash


def test_a_code_works_only_once(db, publisher, created_agent):
    _, code, _ = created_agent
    command = ClaimAgentCommand(db, nats_publisher=publisher)
    command.execute(code)

    with pytest.raises(AgentClaimError):
        command.execute(code)
    assert db.query(ApiKey).count() == 1


def test_expired_code_is_rejected(db, publisher, created_agent):
    agent, code, _ = created_agent
    claim = db.query(AgentClaim).filter(AgentClaim.agent_user_id == agent.id).one()
    claim.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()

    with pytest.raises(AgentClaimError):
        ClaimAgentCommand(db, nats_publisher=publisher).execute(code)
    assert db.query(ApiKey).count() == 0


@pytest.mark.parametrize(
    "bad_code",
    ["", "garbage", "ac_", "ac_.", "ac_abc", "ac_abc.", "ac_.secret", "ak_abc.def"],
)
def test_malformed_codes_are_rejected(db, publisher, bad_code):
    with pytest.raises(AgentClaimError):
        ClaimAgentCommand(db, nats_publisher=publisher).execute(bad_code)


def test_unknown_claim_id_is_rejected(db, publisher):
    with pytest.raises(AgentClaimError):
        ClaimAgentCommand(db, nats_publisher=publisher).execute("ac_nope.nope")


def test_every_failure_is_indistinguishable(db, publisher, created_agent):
    agent, code, _ = created_agent
    claim_id = code[3:].split(".")[0]
    command = ClaimAgentCommand(db, nats_publisher=publisher)

    messages = set()
    for attempt in ("nope", f"ac_{claim_id}.wrong", "ac_x.y"):
        with pytest.raises(AgentClaimError) as error:
            command.execute(attempt)
        messages.add(str(error.value))
    command.execute(code)
    with pytest.raises(AgentClaimError) as error:
        command.execute(code)
    messages.add(str(error.value))

    assert len(messages) == 1


def test_claim_locks_after_too_many_wrong_secrets(db, publisher, created_agent):
    _, code, _ = created_agent
    claim_id = code[3:].split(".")[0]
    command = ClaimAgentCommand(db, nats_publisher=publisher)

    for _ in range(get_settings().agent_claim_max_failed_attempts):
        with pytest.raises(AgentClaimError):
            command.execute(f"ac_{claim_id}.wrong")

    # Even the correct code no longer works once the claim is locked.
    with pytest.raises(AgentClaimError):
        command.execute(code)
    assert db.query(ApiKey).count() == 0


def test_wrong_secrets_below_the_limit_do_not_lock_the_claim(
    db, publisher, created_agent
):
    _, code, _ = created_agent
    claim_id = code[3:].split(".")[0]
    command = ClaimAgentCommand(db, nats_publisher=publisher)

    with pytest.raises(AgentClaimError):
        command.execute(f"ac_{claim_id}.wrong")

    _, full_key = command.execute(code)
    assert full_key.startswith("ak_")


def test_deleted_agent_cannot_be_claimed(db, publisher, created_agent):
    agent, code, _ = created_agent
    UserRepository(db).delete_user(agent.id)

    with pytest.raises(AgentClaimError):
        ClaimAgentCommand(db, nats_publisher=publisher).execute(code)
    assert db.query(ApiKey).count() == 0


def test_claim_publishes_api_key_created(db, publisher, created_agent):
    agent, code, _ = created_agent
    publisher.reset_mock()

    ClaimAgentCommand(db, nats_publisher=publisher).execute(code)

    publisher.publish_sync.assert_called_once()
    event = publisher.publish_sync.call_args.args[0]
    assert event.event_type.endswith(API_KEY_CREATED)
    assert event.event_data["user"]["id"] == str(agent.id)
    assert "secret" not in str(event.event_data)


def test_concurrent_claims_of_one_code_mint_exactly_one_key(engine, monkeypatch):
    """Real concurrency: separate sessions/connections racing on the same code.

    The shared `db` fixture wraps everything in one transaction, so this test uses its
    own engine, commits, and cleans up after itself.
    """
    # Widen the critical section (the secret check runs while the claim row is locked)
    # so that, without the row lock, every thread would pass the "is it open?" check
    # before any of them consumed the claim.
    real_secrets_match = claim_module.secrets_match

    def slow_secrets_match(secret, secret_hash):
        time.sleep(0.3)
        return real_secrets_match(secret, secret_hash)

    monkeypatch.setattr(claim_module, "secrets_match", slow_secrets_match)

    own_engine = create_engine(get_settings().database_url)
    Session = sessionmaker(bind=own_engine)

    setup = Session()
    from unittest.mock import MagicMock

    agent, code, _ = CreateAgentCommand(setup, nats_publisher=MagicMock()).execute(
        AgentCreateRequest(name="Racer")
    )
    agent_id = agent.id
    setup.close()

    results: list[str] = []
    barrier = threading.Barrier(4)

    def claim():
        session = Session()
        try:
            # Open the connection first: connecting is slow and serialized, and without
            # this the threads would reach the database one after another, not together.
            session.execute(text("SELECT 1"))
            barrier.wait()
            _, key = ClaimAgentCommand(session, nats_publisher=MagicMock()).execute(
                code
            )
            results.append("ok")
        except AgentClaimError:
            results.append("rejected")
        finally:
            session.close()

    threads = [threading.Thread(target=claim) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    check = Session()
    try:
        keys = check.query(ApiKey).filter(ApiKey.user_id == agent_id).count()
        assert sorted(results) == ["ok", "rejected", "rejected", "rejected"]
        assert keys == 1
    finally:
        check.query(ApiKey).filter(ApiKey.user_id == agent_id).delete()
        check.query(AgentClaim).filter(AgentClaim.agent_user_id == agent_id).delete()
        check.query(User).filter(User.id == agent_id).delete()
        check.commit()
        check.close()
        own_engine.dispose()
