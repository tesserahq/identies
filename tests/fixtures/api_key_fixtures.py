import pytest
from datetime import datetime, timezone, timedelta
from app.models.api_key import ApiKey
from app.utils.security import generate_api_key, hash_secret, parse_api_key


@pytest.fixture
def api_key_data(faker):
    """Create sample API key data for testing."""
    return {
        "name": faker.word(),
        "expires_at": datetime.now(timezone.utc) + timedelta(days=30),
    }


@pytest.fixture
def api_key_data_no_expiry(faker):
    """Create sample API key data without expiry for testing."""
    return {
        "name": faker.word(),
        "expires_at": None,
    }


@pytest.fixture(scope="function")
def setup_api_key(db, setup_user, faker):
    """Create a test API key for use in tests."""
    full_key, key_id = generate_api_key()
    key_id_part, secret_part = parse_api_key(full_key)

    api_key_data = {
        "user_id": setup_user.id,
        "key_id": key_id_part,
        "secret_hash": hash_secret(secret_part),
        "name": faker.word(),
        "expires_at": datetime.now(timezone.utc) + timedelta(days=30),
    }

    api_key = ApiKey(**api_key_data)
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return api_key, full_key


@pytest.fixture(scope="function")
def setup_expired_api_key(db, setup_user, faker):
    """Create an expired test API key for use in tests."""
    full_key, key_id = generate_api_key()
    key_id_part, secret_part = parse_api_key(full_key)

    api_key_data = {
        "user_id": setup_user.id,
        "key_id": key_id_part,
        "secret_hash": hash_secret(secret_part),
        "name": faker.word(),
        "expires_at": datetime.now(timezone.utc)
        - timedelta(days=1),  # Expired yesterday
    }

    api_key = ApiKey(**api_key_data)
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return api_key, full_key


@pytest.fixture(scope="function")
def setup_revoked_api_key(db, setup_user, faker):
    """Create a revoked test API key for use in tests."""
    full_key, key_id = generate_api_key()
    key_id_part, secret_part = parse_api_key(full_key)

    api_key_data = {
        "user_id": setup_user.id,
        "key_id": key_id_part,
        "secret_hash": hash_secret(secret_part),
        "name": faker.word(),
        "expires_at": datetime.now(timezone.utc) + timedelta(days=30),
        "revoked": True,
    }

    api_key = ApiKey(**api_key_data)
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return api_key, full_key


@pytest.fixture(scope="function")
def setup_another_user_api_key(db, setup_another_user, faker):
    """Create a test API key for another user for testing authorization."""
    full_key, key_id = generate_api_key()
    key_id_part, secret_part = parse_api_key(full_key)

    api_key_data = {
        "user_id": setup_another_user.id,
        "key_id": key_id_part,
        "secret_hash": hash_secret(secret_part),
        "name": faker.word(),
        "expires_at": datetime.now(timezone.utc) + timedelta(days=30),
    }

    api_key = ApiKey(**api_key_data)
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return api_key, full_key
