from unittest.mock import MagicMock

import logging

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import get_db
from app.main import create_app
from app.middleware.authentication_middleware import AuthenticationMiddleware
from app.middleware.auth.exceptions import (
    AuthUpstreamException,
    InviteOnlyAccessException,
    UnauthorizedException,
)
from app.middleware.auth.token_handler import TokenHandler
from app.middleware.auth.user_handler import UserHandler

ACCOUNT_TYPE_CLAIM = "https://mylinden.family/account_type"
CLIENT_ID_CLAIM = "https://mylinden.family/client_id"
LOCAL_ISSUER = "identies"
AUTH0_ISSUER = "https://tenant.auth0.com/"


@pytest.fixture()
def middleware_env(monkeypatch):
    monkeypatch.setenv("TOKEN_EXCHANGE_ISSUER", LOCAL_ISSUER)
    monkeypatch.setenv("SERVICE_ACCOUNT_ACCOUNT_TYPE_CLAIM", ACCOUNT_TYPE_CLAIM)
    monkeypatch.setenv("SERVICE_ACCOUNT_ACCOUNT_TYPE_VALUE", "service_account")
    monkeypatch.setenv("SERVICE_ACCOUNT_CLIENT_ID_CLAIM", CLIENT_ID_CLAIM)


@pytest.fixture()
def middleware(middleware_env):
    return AuthenticationMiddleware(MagicMock())


def _sa_payload(
    *,
    iss: str,
    client_id: str = "new-client",
    account_type: str | None = "service_account",
) -> dict:
    payload = {
        "iss": iss,
        CLIENT_ID_CLAIM: client_id,
    }
    if account_type is not None:
        payload[ACCOUNT_TYPE_CLAIM] = account_type
    return payload


def test_local_service_account_allowed_without_allowlist(middleware, monkeypatch):
    monkeypatch.delenv("ALLOWED_SERVICE_ACCOUNT_CLIENT_IDS", raising=False)
    middleware.config = get_settings()

    payload = _sa_payload(iss=LOCAL_ISSUER, client_id="new-client")
    assert middleware._is_allowed_service_account_for_m2m(payload) is True


def test_auth0_service_account_allowed_when_in_allowlist(middleware, monkeypatch):
    monkeypatch.setenv("ALLOWED_SERVICE_ACCOUNT_CLIENT_IDS", "conversa-client")
    middleware.config = get_settings()

    payload = _sa_payload(iss=AUTH0_ISSUER, client_id="conversa-client")
    assert middleware._is_allowed_service_account_for_m2m(payload) is True


def test_auth0_service_account_denied_when_not_in_allowlist(middleware, monkeypatch):
    monkeypatch.delenv("ALLOWED_SERVICE_ACCOUNT_CLIENT_IDS", raising=False)
    middleware.config = get_settings()

    payload = _sa_payload(iss=AUTH0_ISSUER, client_id="unknown")
    assert middleware._is_allowed_service_account_for_m2m(payload) is False


def test_local_token_missing_service_account_claims(middleware):
    payload = {"iss": LOCAL_ISSUER, CLIENT_ID_CLAIM: "x"}
    assert middleware._is_allowed_service_account_for_m2m(payload) is False


def test_local_token_wrong_account_type(middleware):
    payload = _sa_payload(iss=LOCAL_ISSUER, account_type="user")
    assert middleware._is_allowed_service_account_for_m2m(payload) is False


def _client(db) -> TestClient:
    def override_get_db():
        yield db

    app = create_app(testing=False)
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


@pytest.fixture()
def capture_logs(caplog):
    """The app logger doesn't propagate to the root logger, so attach caplog's
    handler to it directly."""
    app_logger = logging.getLogger("uvicorn")
    app_logger.addHandler(caplog.handler)
    caplog.set_level(logging.DEBUG, logger="uvicorn")
    yield caplog
    app_logger.removeHandler(caplog.handler)


def _error_records(caplog):
    return [r for r in caplog.records if r.levelno >= logging.ERROR]


def test_client_token_failure_returns_401_without_error_log(
    db, monkeypatch, capture_logs
):
    def _raise(self, token):
        raise UnauthorizedException("Not enough segments")

    monkeypatch.setattr(TokenHandler, "verify", _raise)

    response = _client(db).get(
        "/me", headers={"Authorization": "Bearer e2e-fake-access-token"}
    )

    assert response.status_code == 401
    assert response.json() == {"error": "Unauthorized"}
    assert _error_records(capture_logs) == []
    warnings = [r for r in capture_logs.records if r.levelno == logging.WARNING]
    assert any("Not enough segments" in r.getMessage() for r in warnings)
    assert not any("e2e-fake-access-token" in r.getMessage() for r in warnings)


def test_upstream_token_failure_returns_401_with_error_log(
    db, monkeypatch, capture_logs
):
    def _raise(self, token):
        raise AuthUpstreamException("Fail to fetch data from the url")

    monkeypatch.setattr(TokenHandler, "verify", _raise)

    response = _client(db).get("/me", headers={"Authorization": "Bearer x.y.z"})

    assert response.status_code == 401
    assert response.json() == {"error": "Unauthorized"}
    assert len(_error_records(capture_logs)) == 1


def test_upstream_user_resolution_failure_logs_error(db, monkeypatch, capture_logs):
    monkeypatch.setattr(TokenHandler, "verify", lambda self, token: {"sub": "test"})

    def _raise(self, token, payload):
        raise AuthUpstreamException("Failed to fetch user info from oidc")

    monkeypatch.setattr(UserHandler, "resolve_user", _raise)

    response = _client(db).get("/me", headers={"Authorization": "Bearer x.y.z"})

    assert response.status_code == 401
    assert len(_error_records(capture_logs)) == 1


def test_invite_only_rejection_returns_403_not_500(db, monkeypatch, capture_logs):
    """Regression test: InviteOnlyAccessException raised during user resolution
    inside AuthenticationMiddleware.dispatch() must be converted to a 403
    JSONResponse instead of propagating as an unhandled 500."""
    monkeypatch.setattr(TokenHandler, "verify", lambda self, token: {"sub": "test"})

    def _raise_invite_only(self, token, payload):
        raise InviteOnlyAccessException(email="user@example.com")

    monkeypatch.setattr(UserHandler, "resolve_user", _raise_invite_only)

    def override_get_db():
        yield db

    app = create_app(testing=False)
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    response = client.get("/me", headers={"Authorization": "Bearer faketoken"})

    assert response.status_code == 403
    assert response.json() == {
        "detail": {
            "title": "Access not granted",
            "detail": "Invitation required to access this service.",
            "code": "INVITE_REQUIRED",
            "email": "user@example.com",
        }
    }
    assert _error_records(capture_logs) == []
