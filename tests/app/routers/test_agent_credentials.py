"""An agent's own credentials must never open the privileged (M2M) endpoints.

These tests use real tokens: an agent-owned OAuth client mints a JWT through
/oauth/token, and the JWT is then presented to the real authentication middleware.
"""

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.constants.user_kinds import UserKind
from app.db import get_db
from app.main import create_app
from app.models.user import User
from app.repositories.client_repository import ClientRepository
from app.schemas.client import ClientCreate

AUDIENCE = "https://api.example.com"
ACCOUNT_TYPE_CLAIM = "https://mylinden.family/account_type"


@pytest.fixture(scope="module")
def rsa_key_pair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("utf-8")
    )
    return private_pem, public_pem


@pytest.fixture()
def real_app_client(db, monkeypatch, rsa_key_pair):
    """The real middleware and token verification, signing keys set for this test."""
    private_pem, public_pem = rsa_key_pair
    monkeypatch.setenv("TOKEN_EXCHANGE_PRIVATE_KEY_PEM", private_pem)
    monkeypatch.setenv("TOKEN_EXCHANGE_PUBLIC_KEY_PEM", public_pem)
    monkeypatch.setenv("TOKEN_EXCHANGE_ISSUER", "identies")
    monkeypatch.setenv("TOKEN_EXCHANGE_AUDIENCE", AUDIENCE)
    monkeypatch.delenv("ALLOWED_SERVICE_ACCOUNT_CLIENT_IDS", raising=False)

    def override_get_db():
        yield db

    app = create_app(testing=False)
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def _mint(client: TestClient, db_client, secret) -> str:
    response = client.post(
        "/oauth/token",
        json={
            "grant_type": "client_credentials",
            "client_id": db_client.client_id,
            "client_secret": secret,
            "audience": AUDIENCE,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture()
def agent_client(db, faker):
    agent = User(
        email=f"agent-{faker.uuid4()}@agents.example",
        first_name="Claude",
        last_name="Agent",
        kind=UserKind.AGENT,
    )
    db.add(agent)
    db.commit()
    client, secret = ClientRepository(db).create_client(
        ClientCreate(
            name="Agent credentials", owner_id=agent.id, created_by_id=agent.id
        )
    )
    return agent, client, secret


def test_agent_token_carries_no_service_account_claims(
    real_app_client, agent_client, rsa_key_pair
):
    agent, client, secret = agent_client
    token = _mint(real_app_client, client, secret)

    decoded = jwt.decode(
        token,
        rsa_key_pair[1],
        algorithms=["RS256"],
        audience=AUDIENCE,
        issuer="identies",
    )
    assert decoded["sub"] == str(agent.id)
    assert ACCOUNT_TYPE_CLAIM not in decoded
    assert "https://mylinden.family/client_id" not in decoded


AGENT_ID = "00000000-0000-0000-0000-000000000000"


@pytest.mark.parametrize(
    "method, path, body",
    [
        ("POST", "/agents", {"name": "Escalation"}),
        ("POST", "/agents/claim", {"code": "ac_x.y"}),
        ("POST", f"/agents/{AGENT_ID}/claim-codes", None),
        ("GET", f"/agents/{AGENT_ID}", None),
        ("POST", f"/agents/{AGENT_ID}/rotate", None),
        ("POST", f"/agents/{AGENT_ID}/revoke", None),
        ("DELETE", f"/agents/{AGENT_ID}", None),
        (
            "POST",
            "/oauth/token-exchange",
            {"user_id": "x", "requested_audience": AUDIENCE},
        ),
    ],
)
def test_agent_token_cannot_call_privileged_endpoints(
    real_app_client, agent_client, method, path, body
):
    _, client, secret = agent_client
    token = _mint(real_app_client, client, secret)

    response = real_app_client.request(
        method, path, json=body, headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403


def test_service_account_token_still_reaches_privileged_endpoints(
    real_app_client, setup_service_account_client
):
    """The gate is not simply closed: a real service account still gets through."""
    client, secret = setup_service_account_client
    token = _mint(real_app_client, client, secret)

    response = real_app_client.post(
        "/agents",
        json={"name": "Claude"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["agent"]["kind"] == "agent"


def test_full_flow_claim_then_mint_a_token_that_is_only_an_agent(
    real_app_client, setup_service_account_client, rsa_key_pair
):
    """A service creates and claims an agent; the agent's credentials mint a JWT whose
    subject is the agent, with no service-account claims and no privileged access."""
    service_client, service_secret = setup_service_account_client
    service_token = _mint(real_app_client, service_client, service_secret)
    service = {"Authorization": f"Bearer {service_token}"}

    created = real_app_client.post(
        "/agents", json={"name": "Claude"}, headers=service
    ).json()
    claimed = real_app_client.post(
        "/agents/claim", json={"code": created["claim_code"]}, headers=service
    )
    assert claimed.status_code == 200
    credentials = claimed.json()

    token_response = real_app_client.post(
        "/oauth/token",
        json={
            "grant_type": "client_credentials",
            "client_id": credentials["client_id"],
            "client_secret": credentials["client_secret"],
            "audience": AUDIENCE,
        },
    )
    assert token_response.status_code == 200
    agent_token = token_response.json()["access_token"]

    decoded = jwt.decode(
        agent_token,
        rsa_key_pair[1],
        algorithms=["RS256"],
        audience=AUDIENCE,
        issuer="identies",
    )
    assert decoded["sub"] == created["agent"]["id"] == credentials["user_id"]
    assert ACCOUNT_TYPE_CLAIM not in decoded

    denied = real_app_client.post(
        "/agents",
        json={"name": "Chain"},
        headers={"Authorization": f"Bearer {agent_token}"},
    )
    assert denied.status_code == 403


def test_a_deleted_agent_can_no_longer_mint_tokens(db, real_app_client, agent_client):
    from app.repositories.user_repository import UserRepository

    agent, client, secret = agent_client
    assert _mint(real_app_client, client, secret)

    UserRepository(db).delete_user(agent.id)

    response = real_app_client.post(
        "/oauth/token",
        json={
            "grant_type": "client_credentials",
            "client_id": client.client_id,
            "client_secret": secret,
            "audience": AUDIENCE,
        },
    )
    assert response.status_code == 401


def _token_request(client, credentials):
    return client.post(
        "/oauth/token",
        json={
            "grant_type": "client_credentials",
            "client_id": credentials["client_id"],
            "client_secret": credentials["client_secret"],
            "audience": AUDIENCE,
        },
    )


def test_lifecycle_controls_who_can_mint_tokens(
    real_app_client, setup_service_account_client
):
    """rotate / revoke / delete, checked against what the agent can actually do."""
    service_client, service_secret = setup_service_account_client
    service = {
        "Authorization": f"Bearer {_mint(real_app_client, service_client, service_secret)}"
    }
    created = real_app_client.post(
        "/agents", json={"name": "Claude"}, headers=service
    ).json()
    agent_id = created["agent"]["id"]
    credentials = real_app_client.post(
        "/agents/claim", json={"code": created["claim_code"]}, headers=service
    ).json()

    assert _token_request(real_app_client, credentials).status_code == 200
    status = real_app_client.get(f"/agents/{agent_id}", headers=service).json()
    assert status["last_used_at"] is not None  # recorded by the token mint above

    # Rotate: the old secret stops minting, the new one works.
    rotated = real_app_client.post(f"/agents/{agent_id}/rotate", headers=service).json()
    assert _token_request(real_app_client, credentials).status_code == 401
    assert _token_request(real_app_client, rotated).status_code == 200

    # Revoke: cut off; rotate restores.
    real_app_client.post(f"/agents/{agent_id}/revoke", headers=service)
    assert _token_request(real_app_client, rotated).status_code == 401
    restored = real_app_client.post(
        f"/agents/{agent_id}/rotate", headers=service
    ).json()
    assert _token_request(real_app_client, restored).status_code == 200

    # Delete: gone for good.
    assert (
        real_app_client.delete(f"/agents/{agent_id}", headers=service).status_code
        == 204
    )
    assert _token_request(real_app_client, restored).status_code == 401
