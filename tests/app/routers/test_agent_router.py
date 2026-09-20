"""The agent endpoints are privileged: only a service-account token gets through.

These tests run the real authentication middleware (not the test mock) so they check
who is actually allowed to call the endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from app.db import get_db
from app.main import create_app
from app.middleware.auth.token_handler import TokenHandler

ACCOUNT_TYPE_CLAIM = "https://mylinden.family/account_type"
CLIENT_ID_CLAIM = "https://mylinden.family/client_id"
LOCAL_ISSUER = "identies"

HUMAN = {"sub": "auth0|human", "iss": "https://tenant.auth0.com/"}
ALLOWED_SERVICE = {
    "iss": LOCAL_ISSUER,
    ACCOUNT_TYPE_CLAIM: "service_account",
    CLIENT_ID_CLAIM: "linden-api",
}
UNKNOWN_SERVICE = {
    "iss": "https://tenant.auth0.com/",
    ACCOUNT_TYPE_CLAIM: "service_account",
    CLIENT_ID_CLAIM: "someone-else",
}


@pytest.fixture
def make_client(db, monkeypatch):
    monkeypatch.setenv("TOKEN_EXCHANGE_ISSUER", LOCAL_ISSUER)
    monkeypatch.setenv("SERVICE_ACCOUNT_ACCOUNT_TYPE_CLAIM", ACCOUNT_TYPE_CLAIM)
    monkeypatch.setenv("SERVICE_ACCOUNT_ACCOUNT_TYPE_VALUE", "service_account")
    monkeypatch.setenv("SERVICE_ACCOUNT_CLIENT_ID_CLAIM", CLIENT_ID_CLAIM)
    monkeypatch.setenv("ALLOWED_SERVICE_ACCOUNT_CLIENT_IDS", "linden-api")

    def _make(payload: dict) -> TestClient:
        monkeypatch.setattr(TokenHandler, "verify", lambda self, token: payload)

        def override_get_db():
            yield db

        app = create_app(testing=False)
        app.dependency_overrides[get_db] = override_get_db
        return TestClient(app, headers={"Authorization": "Bearer faketoken"})

    return _make


ANY_ID = "00000000-0000-0000-0000-000000000000"
ALL_AGENT_ENDPOINTS = [
    ("POST", "/agents", {"name": "Claude"}),
    ("POST", "/agents/claim", {"code": "ac_x.y"}),
    ("POST", f"/agents/{ANY_ID}/claim-codes", None),
    ("GET", f"/agents/{ANY_ID}", None),
    ("POST", f"/agents/{ANY_ID}/rotate", None),
    ("POST", f"/agents/{ANY_ID}/revoke", None),
    ("DELETE", f"/agents/{ANY_ID}", None),
]


@pytest.mark.parametrize(
    "payload", [HUMAN, UNKNOWN_SERVICE], ids=["human", "unknown-service"]
)
def test_only_an_allowed_service_can_call_agent_endpoints(make_client, payload):
    client = make_client(payload)

    for method, path, body in ALL_AGENT_ENDPOINTS:
        response = client.request(method, path, json=body)
        assert response.status_code == 403, (method, path)


def test_agent_endpoints_require_a_token(make_client):
    client = make_client(ALLOWED_SERVICE)
    client.headers.pop("Authorization")

    assert client.post("/agents", json={"name": "Claude"}).status_code == 401


def test_service_creates_claims_and_reissues(make_client):
    client = make_client(ALLOWED_SERVICE)

    created = client.post("/agents", json={"name": "Claude"})
    assert created.status_code == 200
    body = created.json()
    assert body["agent"]["kind"] == "agent"
    assert body["agent"]["first_name"] == "Claude"
    assert body["claim_code"].startswith("ac_")

    reissued = client.post(f"/agents/{body['agent']['id']}/claim-codes")
    assert reissued.status_code == 200
    assert reissued.json()["claim_code"] != body["claim_code"]

    old = client.post("/agents/claim", json={"code": body["claim_code"]})
    assert old.status_code == 400

    claimed = client.post("/agents/claim", json={"code": reissued.json()["claim_code"]})
    assert claimed.status_code == 200
    assert claimed.json()["client_id"].startswith("cs_")
    assert claimed.json()["client_secret"]
    assert claimed.json()["user_id"] == body["agent"]["id"]
    assert "api_key" not in claimed.json()

    again = client.post(f"/agents/{body['agent']['id']}/claim-codes")
    assert again.status_code == 409


def test_claim_failures_all_look_the_same(make_client):
    client = make_client(ALLOWED_SERVICE)
    created = client.post("/agents", json={"name": "Claude"}).json()
    code = created["claim_code"]
    claim_id = code[3:].split(".")[0]

    bodies = {
        client.post("/agents/claim", json={"code": "garbage"}).text,
        client.post("/agents/claim", json={"code": "ac_nope.nope"}).text,
        client.post("/agents/claim", json={"code": f"ac_{claim_id}.wrong"}).text,
    }
    client.post("/agents/claim", json={"code": code})
    used = client.post("/agents/claim", json={"code": code})

    assert used.status_code == 400
    bodies.add(used.text)
    assert len(bodies) == 1


def test_reissuing_for_an_unknown_agent_is_404(make_client):
    client = make_client(ALLOWED_SERVICE)

    response = client.post("/agents/00000000-0000-0000-0000-000000000000/claim-codes")

    assert response.status_code == 404


def test_create_agent_validates_the_name(make_client):
    client = make_client(ALLOWED_SERVICE)

    assert client.post("/agents", json={"name": ""}).status_code == 422
    assert client.post("/agents", json={}).status_code == 422


def test_lifecycle_status_rotate_revoke_delete(make_client):
    client = make_client(ALLOWED_SERVICE)
    created = client.post("/agents", json={"name": "Claude"}).json()
    agent_id = created["agent"]["id"]

    unclaimed = client.get(f"/agents/{agent_id}").json()
    assert unclaimed["status"] == "unclaimed"
    assert unclaimed["claim_expires_at"] is not None
    assert unclaimed["client_id"] is None

    # Nothing to rotate before the agent has been claimed.
    assert client.post(f"/agents/{agent_id}/rotate").status_code == 409

    claimed = client.post("/agents/claim", json={"code": created["claim_code"]}).json()
    active = client.get(f"/agents/{agent_id}").json()
    assert active["status"] == "active"
    assert active["client_id"] == claimed["client_id"]
    assert active["last_used_at"] is None
    assert "client_secret" not in str(active)

    rotated = client.post(f"/agents/{agent_id}/rotate")
    assert rotated.status_code == 200
    assert rotated.json()["client_id"] == claimed["client_id"]
    assert rotated.json()["client_secret"] != claimed["client_secret"]

    revoked = client.post(f"/agents/{agent_id}/revoke")
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "revoked"
    assert client.post(f"/agents/{agent_id}/revoke").json()["status"] == "revoked"

    restored = client.post(f"/agents/{agent_id}/rotate")
    assert restored.status_code == 200
    assert client.get(f"/agents/{agent_id}").json()["status"] == "active"

    assert client.delete(f"/agents/{agent_id}").status_code == 204
    for method, path in [
        ("GET", f"/agents/{agent_id}"),
        ("POST", f"/agents/{agent_id}/rotate"),
        ("POST", f"/agents/{agent_id}/revoke"),
        ("DELETE", f"/agents/{agent_id}"),
        ("POST", f"/agents/{agent_id}/claim-codes"),
    ]:
        assert client.request(method, path).status_code == 404, (method, path)


def test_the_agent_endpoints_cannot_touch_humans_or_service_accounts(
    make_client, setup_user, setup_service_account
):
    client = make_client(ALLOWED_SERVICE)

    for user in (setup_user, setup_service_account):
        for method, path in [
            ("GET", f"/agents/{user.id}"),
            ("POST", f"/agents/{user.id}/rotate"),
            ("POST", f"/agents/{user.id}/revoke"),
            ("DELETE", f"/agents/{user.id}"),
        ]:
            assert client.request(method, path).status_code == 404, (method, path)
