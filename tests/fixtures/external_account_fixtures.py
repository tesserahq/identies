"""Fixtures for external accounts and link tokens."""

from datetime import datetime, timedelta, timezone

import pytest

from app.models.external_account import ExternalAccount
from app.models.link_token import LinkToken
from app.utils.security import generate_link_token


@pytest.fixture(scope="function")
def setup_external_account(db, setup_user, faker):
    """Create a test external account for the given user."""
    platform = "telegram"
    external_id = faker.numerify(text="##########")
    data = {}
    account = ExternalAccount(
        user_id=setup_user.id,
        platform=platform,
        external_id=external_id,
        data=data,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@pytest.fixture(scope="function")
def setup_link_token(db, faker):
    """Create a valid link token for testing (not yet used)."""
    token_value = generate_link_token()
    platform = "telegram"
    external_id = faker.numerify(text="##########")
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    link_token = LinkToken(
        token=token_value,
        platform=platform,
        external_id=external_id,
        data={},
        expires_at=expires_at,
    )
    db.add(link_token)
    db.commit()
    db.refresh(link_token)
    return link_token


@pytest.fixture(scope="function")
def setup_expired_link_token(db, faker):
    """Create an expired link token for testing."""
    token_value = generate_link_token()
    platform = "telegram"
    external_id = faker.numerify(text="##########")
    expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    link_token = LinkToken(
        token=token_value,
        platform=platform,
        external_id=external_id,
        data={},
        expires_at=expires_at,
    )
    db.add(link_token)
    db.commit()
    db.refresh(link_token)
    return link_token


@pytest.fixture(scope="function")
def setup_used_link_token(db, faker):
    """Create an already-used link token for testing."""
    token_value = generate_link_token()
    platform = "telegram"
    external_id = faker.numerify(text="##########")
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    used_at = datetime.now(timezone.utc)
    link_token = LinkToken(
        token=token_value,
        platform=platform,
        external_id=external_id,
        data={},
        expires_at=expires_at,
        used_at=used_at,
    )
    db.add(link_token)
    db.commit()
    db.refresh(link_token)
    return link_token
