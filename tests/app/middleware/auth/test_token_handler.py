import jwt
import pytest
from fastapi.testclient import TestClient

from app.db import get_db
from app.main import create_app
from app.middleware.auth.exceptions import UnauthorizedException
from app.middleware.auth.token_handler import TokenHandler


@pytest.fixture()
def token_handler(monkeypatch):
    monkeypatch.setenv("TOKEN_EXCHANGE_PRIVATE_KEY_PEM", "")
    monkeypatch.setenv("TOKEN_EXCHANGE_PUBLIC_KEY_PEM", "")
    return TokenHandler()


def test_verify_jwt_wraps_jwks_connection_error_as_unauthorized(
    token_handler, monkeypatch
):
    """Regression test: a JWKS fetch timeout/connection error must surface as
    UnauthorizedException, not propagate as an unhandled PyJWKClientError."""

    def _raise_timeout(self, token):
        raise jwt.exceptions.PyJWKClientConnectionError(
            'Fail to fetch data from the url, err: "The read operation timed out"'
        )

    monkeypatch.setattr(jwt.PyJWKClient, "get_signing_key_from_jwt", _raise_timeout)

    with pytest.raises(UnauthorizedException) as exc_info:
        token_handler.verify("some.jwt.token")

    assert "read operation timed out" in str(exc_info.value)


def test_verify_jwt_wraps_decode_error_as_unauthorized(token_handler, monkeypatch):
    def _raise_decode_error(self, token):
        raise jwt.exceptions.DecodeError("Invalid token")

    monkeypatch.setattr(
        jwt.PyJWKClient, "get_signing_key_from_jwt", _raise_decode_error
    )

    with pytest.raises(UnauthorizedException):
        token_handler.verify("some.jwt.token")


def test_jwks_client_is_reused_across_requests(db, test_user, monkeypatch):
    """Regression test: the middleware must not reconstruct TokenHandler (and
    therefore the JWKS client) on every request, so the JWKS client's own
    key cache is effective instead of hitting the IDP on every request."""

    call_count = {"jwks_client_constructions": 0}
    original_init = TokenHandler.__init__

    def counting_init(self, *args, **kwargs):
        call_count["jwks_client_constructions"] += 1
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(TokenHandler, "__init__", counting_init)
    monkeypatch.setattr(TokenHandler, "verify", lambda self, token: {"sub": "test"})

    from app.middleware.auth.user_handler import UserHandler
    from app.schemas.user import User

    resolved_user = User.model_validate(test_user)
    monkeypatch.setattr(
        UserHandler,
        "resolve_user",
        lambda self, token, payload: resolved_user,
    )

    def override_get_db():
        yield db

    app = create_app(testing=False)
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    client.get("/me", headers={"Authorization": "Bearer faketoken"})
    client.get("/me", headers={"Authorization": "Bearer faketoken"})
    client.get("/me", headers={"Authorization": "Bearer faketoken"})

    assert call_count["jwks_client_constructions"] == 1
