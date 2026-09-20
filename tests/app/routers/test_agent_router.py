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


@pytest.mark.parametrize(
    "payload", [HUMAN, UNKNOWN_SERVICE], ids=["human", "unknown-service"]
)
def test_only_an_allowed_service_can_call_agent_endpoints(make_client, payload):
    client = make_client(payload)

    for method, path, body in [
        ("post", "/agents", {"name": "Claude"}),
        ("post", "/agents/claim", {"code": "ac_x.y"}),
        ("post", "/agents/00000000-0000-0000-0000-000000000000/claim-codes", None),
    ]:
        response = getattr(client, method)(path, json=body)
        assert response.status_code == 403, path


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
    assert claimed.json()["api_key"].startswith("ak_")
    assert claimed.json()["user_id"] == body["agent"]["id"]

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
