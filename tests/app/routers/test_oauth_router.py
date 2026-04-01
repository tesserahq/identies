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
def oauth_env(monkeypatch, rsa_key_pair):
    private_pem, public_pem = rsa_key_pair
    monkeypatch.setenv("TOKEN_EXCHANGE_PRIVATE_KEY_PEM", private_pem)
    monkeypatch.setenv("TOKEN_EXCHANGE_PUBLIC_KEY_PEM", public_pem)
    monkeypatch.setenv("TOKEN_EXCHANGE_ISSUER", "identies")
    monkeypatch.setenv("TOKEN_EXCHANGE_AUDIENCE", "https://api.example.com")
    return {"private_pem": private_pem, "public_pem": public_pem}


@pytest.fixture()
def anon_client(db, oauth_env, monkeypatch):
    """TestClient with real middleware but no bearer token — for testing SKIP_AUTH_PATHS endpoints."""
    monkeypatch.setattr(TokenHandler, "verify", lambda self, token: {"sub": "test"})

    def override_get_db():
        yield db

    app = create_app(testing=False)
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_oauth_token_success(anon_client, setup_client, oauth_env):
    db_client, client_secret = setup_client
    response = anon_client.post(
        "/oauth/token",
        json={
            "grant_type": "client_credentials",
            "client_id": db_client.client_id,
            "client_secret": client_secret,
            "audience": "https://api.example.com",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "Bearer"
    assert data["expires_in"] == 900

    decoded = jwt.decode(
        data["access_token"],
        oauth_env["public_pem"],
        algorithms=["RS256"],
        audience="https://api.example.com",
        issuer="identies",
    )
    assert decoded["sub"] == str(db_client.owner_id)


def test_oauth_token_wrong_secret(anon_client, setup_client, oauth_env):
    db_client, _ = setup_client
    response = anon_client.post(
        "/oauth/token",
        json={
            "grant_type": "client_credentials",
            "client_id": db_client.client_id,
            "client_secret": "wrong_secret",
            "audience": "https://api.example.com",
        },
    )
    assert response.status_code == 401


def test_oauth_token_revoked_client(anon_client, setup_revoked_client, oauth_env):
    db_client, client_secret = setup_revoked_client
    response = anon_client.post(
        "/oauth/token",
        json={
            "grant_type": "client_credentials",
            "client_id": db_client.client_id,
            "client_secret": client_secret,
            "audience": "https://api.example.com",
        },
    )
    assert response.status_code == 401


def test_oauth_token_invalid_audience(anon_client, setup_client, oauth_env):
    db_client, client_secret = setup_client
    response = anon_client.post(
        "/oauth/token",
        json={
            "grant_type": "client_credentials",
            "client_id": db_client.client_id,
            "client_secret": client_secret,
            "audience": "https://invalid.example.com",
        },
    )
    assert response.status_code == 400


def test_oauth_token_unsupported_grant_type(anon_client, setup_client, oauth_env):
    db_client, client_secret = setup_client
    response = anon_client.post(
        "/oauth/token",
        json={
            "grant_type": "authorization_code",
            "client_id": db_client.client_id,
            "client_secret": client_secret,
            "audience": "https://api.example.com",
        },
    )
    assert response.status_code == 400
