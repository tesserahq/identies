import contextlib

import pytest
import requests

from app.middleware.auth.exceptions import (
    AuthUpstreamException,
    InviteOnlyAccessException,
    UnauthorizedException,
)
from app.middleware.auth.user_handler import UserHandler


@pytest.fixture()
def user_handler(monkeypatch, db):
    monkeypatch.setattr(
        "app.middleware.auth.user_handler.session_scope",
        lambda: contextlib.nullcontext(db),
    )
    monkeypatch.setenv("INVITE_ONLY_ACCESS", "true")
    handler = UserHandler()
    handler.config.invite_only_access = True
    return handler


def test_handle_user_onboarding_invite_only_rejection_includes_name(user_handler):
    """Regression test: the invite-only rejection must carry first_name/last_name
    so the UI can show who was denied access, not just their email."""
    userinfo = {
        "email": "jane.doe@example.com",
        "name": "Jane Doe",
    }

    with pytest.raises(InviteOnlyAccessException) as exc_info:
        user_handler.handle_user_onboarding({"sub": "user-1"}, userinfo)

    detail = exc_info.value.detail
    assert detail["email"] == "jane.doe@example.com"
    assert detail["first_name"] == "Jane"
    assert detail["last_name"] == "Doe"


def test_handle_user_onboarding_invite_only_rejection_without_email(user_handler):
    """When userinfo has no email, first_name/last_name are still surfaced."""
    userinfo = {"name": "Jane Doe"}

    with pytest.raises(InviteOnlyAccessException) as exc_info:
        user_handler.handle_user_onboarding({"sub": "user-1"}, userinfo)

    detail = exc_info.value.detail
    assert "email" not in detail
    assert detail["first_name"] == "Jane"
    assert detail["last_name"] == "Doe"


def test_handle_user_onboarding_invite_only_rejection_single_word_name(user_handler):
    """A single-word name must not crash resolving last_name."""
    userinfo = {"email": "cher@example.com", "name": "Cher"}

    with pytest.raises(InviteOnlyAccessException) as exc_info:
        user_handler.handle_user_onboarding({"sub": "user-1"}, userinfo)

    detail = exc_info.value.detail
    assert detail["first_name"] == "Cher"
    assert "last_name" not in detail


class _FakeResponse:
    def __init__(self, status_code: int, text: str = ""):
        self.status_code = status_code
        self.text = text

    def json(self):
        return {}


def test_fetch_user_info_connection_error_is_upstream_failure(
    user_handler, monkeypatch
):
    def _raise(*args, **kwargs):
        raise requests.exceptions.ConnectTimeout("timed out")

    monkeypatch.setattr("app.middleware.auth.user_handler.requests.get", _raise)

    with pytest.raises(AuthUpstreamException):
        user_handler.fetch_user_info_from_oidc("token")


def test_fetch_user_info_server_error_is_upstream_failure(user_handler, monkeypatch):
    monkeypatch.setattr(
        "app.middleware.auth.user_handler.requests.get",
        lambda *a, **k: _FakeResponse(503, "unavailable"),
    )

    with pytest.raises(AuthUpstreamException):
        user_handler.fetch_user_info_from_oidc("token")


def test_fetch_user_info_rejected_token_is_client_failure(user_handler, monkeypatch):
    monkeypatch.setattr(
        "app.middleware.auth.user_handler.requests.get",
        lambda *a, **k: _FakeResponse(401, "invalid token"),
    )

    with pytest.raises(UnauthorizedException) as exc_info:
        user_handler.fetch_user_info_from_oidc("token")

    assert not isinstance(exc_info.value, AuthUpstreamException)
