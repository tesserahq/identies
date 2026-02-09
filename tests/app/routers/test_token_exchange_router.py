import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.db import get_db
from app.main import create_app
from app.middleware.auth.token_handler import TokenHandler


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
def token_exchange_env(monkeypatch, rsa_key_pair):
    private_pem, public_pem = rsa_key_pair
    monkeypatch.setenv("TOKEN_EXCHANGE_PRIVATE_KEY_PEM", private_pem)
    monkeypatch.setenv("TOKEN_EXCHANGE_PUBLIC_KEY_PEM", public_pem)
    monkeypatch.setenv("TOKEN_EXCHANGE_ISSUER", "identies")
    monkeypatch.setenv("TOKEN_EXCHANGE_AUDIENCE", "linden")
    monkeypatch.setenv("TOKEN_EXCHANGE_REQUIRED_SCOPE", "token:exchange")
    monkeypatch.setenv("ALLOWED_SERVICE_ACCOUNT_CLIENT_IDS", "conversa-client")
    return {"private_pem": private_pem, "public_pem": public_pem}


@pytest.fixture()
def m2m_client(db, setup_user, token_exchange_env, monkeypatch):
    payload = {
        "scope": "token:exchange",
        "azp": "conversa-client",
        "https://mylinden.family/account_type": "service_account",
        "https://mylinden.family/client_id": "conversa-client",
    }

    monkeypatch.setattr(TokenHandler, "verify", lambda self, token: payload)

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app = create_app(testing=False)
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    client.headers.update({"Authorization": "Bearer test"})
    return client


def test_jwks_endpoint_returns_keyset(client, token_exchange_env):
    response = client.get("/.well-known/jwks.json")
    assert response.status_code == 200
    data = response.json()
    assert "keys" in data
    assert len(data["keys"]) == 1
    assert data["keys"][0]["kty"] == "RSA"


def test_token_exchange_rejects_invalid_audience(m2m_client, setup_user):
    response = m2m_client.post(
        "/oauth/token-exchange",
        json={
            "user_id": str(setup_user.id),
            "requested_audience": "invalid",
            "requested_scope": "linden:read",
        },
    )
    assert response.status_code == 400


def test_token_exchange_success(m2m_client, setup_user, token_exchange_env):
    response = m2m_client.post(
        "/oauth/token-exchange",
        json={
            "user_id": str(setup_user.id),
            "requested_audience": "linden",
            "requested_scope": "linden:read",
        },
    )
    assert response.status_code == 200

    data = response.json()
    token = data["access_token"]
    public_pem = token_exchange_env["public_pem"]

    decoded = jwt.decode(
        token,
        public_pem,
        algorithms=["RS256"],
        audience="linden",
        issuer="identies",
    )

    assert decoded["sub"] == str(setup_user.id)
    assert decoded["act"] == "conversa-client"
    assert decoded["scope"] == "linden:read"
