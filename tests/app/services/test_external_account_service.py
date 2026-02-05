"""Tests for ExternalAccountService."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.models.external_account import ExternalAccount
from app.services.external_account_service import ExternalAccountService


def test_create_link_token_expires_at_approx_10_min(db, faker):
    """Create link token and check expires_at is ~10 min from now."""
    service = ExternalAccountService(db)
    token_value, expires_at = service.create_link_token(
        platform="telegram",
        external_user_id=faker.numerify(text="##########"),
        data=None,
        expires_in_seconds=600,
    )
    assert token_value
    now = datetime.now(timezone.utc)
    assert expires_at > now
    assert (expires_at - now).total_seconds() <= 601
    assert (expires_at - now).total_seconds() >= 599


def test_create_link_token_custom_ttl(db, faker):
    """Create link token with custom expires_in_seconds."""
    service = ExternalAccountService(db)
    token_value, expires_at = service.create_link_token(
        platform="telegram",
        external_user_id=faker.numerify(text="##########"),
        data=None,
        expires_in_seconds=120,
    )
    assert token_value
    now = datetime.now(timezone.utc)
    assert (expires_at - now).total_seconds() <= 121
    assert (expires_at - now).total_seconds() >= 119


def test_consume_link_token_creates_external_account(db, setup_user, setup_link_token):
    """Consume valid token and create ExternalAccount for user."""
    service = ExternalAccountService(db)
    link_token = setup_link_token
    consumed = service.consume_link_token(link_token.token)
    assert consumed is not None
    assert consumed.used_at is not None
    account = service.create_external_account(
        user_id=setup_user.id,
        platform=consumed.platform,
        external_id=consumed.external_id,
        data=consumed.data or {},
    )
    assert account.user_id == setup_user.id
    assert account.platform == link_token.platform
    assert account.external_id == link_token.external_id


def test_consume_link_token_twice_second_fails(db, setup_link_token):
    """Consuming the same token twice: second returns None."""
    service = ExternalAccountService(db)
    token = setup_link_token.token
    first = service.consume_link_token(token)
    assert first is not None
    second = service.consume_link_token(token)
    assert second is None


def test_consume_expired_token_returns_none(db, setup_expired_link_token):
    """Expired token cannot be consumed."""
    service = ExternalAccountService(db)
    consumed = service.consume_link_token(setup_expired_link_token.token)
    assert consumed is None


def test_consume_used_token_returns_none(db, setup_used_link_token):
    """Already-used token cannot be consumed again."""
    service = ExternalAccountService(db)
    consumed = service.consume_link_token(setup_used_link_token.token)
    assert consumed is None


def test_get_external_account_scoped_to_user(
    db, setup_user, setup_another_user, setup_external_account
):
    """get_external_account returns account only when user_id matches."""
    service = ExternalAccountService(db)
    account = setup_external_account
    found = service.get_external_account(account.id, setup_user.id)
    assert found is not None
    assert found.id == account.id
    found_other = service.get_external_account(account.id, setup_another_user.id)
    assert found_other is None


def test_get_external_accounts_query_returns_only_user_accounts(
    db, setup_user, setup_another_user, setup_external_account
):
    """get_external_accounts_query returns only accounts for given user."""
    service = ExternalAccountService(db)
    account = setup_external_account
    query = service.get_external_accounts_query(setup_user.id)
    items = query.all()
    assert len(items) >= 1
    assert any(a.id == account.id for a in items)
    query_other = service.get_external_accounts_query(setup_another_user.id)
    items_other = query_other.all()
    assert not any(a.id == account.id for a in items_other)


def test_delete_external_account_owner_succeeds(db, setup_user, setup_external_account):
    """delete_external_account succeeds when user is owner."""
    service = ExternalAccountService(db)
    account = setup_external_account
    ok = service.delete_external_account(account.id, setup_user.id)
    assert ok is True
    found = service.get_external_account(account.id, setup_user.id)
    assert found is None


def test_delete_external_account_non_owner_fails(
    db, setup_user, setup_another_user, setup_external_account
):
    """delete_external_account returns False when user is not owner."""
    service = ExternalAccountService(db)
    account = setup_external_account
    ok = service.delete_external_account(account.id, setup_another_user.id)
    assert ok is False
    found = service.get_external_account(account.id, setup_user.id)
    assert found is not None
