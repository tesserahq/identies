import contextlib

import pytest

from app.middleware.auth.exceptions import InviteOnlyAccessException
from app.middleware.auth.user_handler import UserHandler


@pytest.fixture()
def user_handler(monkeypatch, db):
    monkeypatch.setattr(
        "app.middleware.auth.user_handler.db_session",
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
