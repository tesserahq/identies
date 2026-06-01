from unittest.mock import MagicMock

import pytest

from app.config import get_settings
from app.middleware.authentication_middleware import AuthenticationMiddleware

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
