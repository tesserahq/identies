import pytest
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from app.services.api_key_service import ApiKeyService
from app.schemas.api_key import ApiKeyCreate
from app.utils.security import parse_api_key, verify_api_key_secret


@pytest.fixture
def sample_api_key_data():
    """Create sample API key data for testing."""
    return {
        "name": "Test API Key",
        "expires_at": datetime.now(timezone.utc) + timedelta(days=30),
    }


@pytest.fixture
def sample_api_key_data_no_expiry():
    """Create sample API key data without expiry for testing."""
    return {
        "name": "Test API Key No Expiry",
        "expires_at": None,
    }


def test_create_api_key(db, setup_user, sample_api_key_data):
    """Test creating a new API key."""
    api_key_service = ApiKeyService(db)

    # Create API key
    api_key_data = ApiKeyCreate(
        user_id=setup_user.id,
        name=sample_api_key_data["name"],
        expires_at=sample_api_key_data["expires_at"],
    )
    api_key, full_key = api_key_service.create_api_key(api_key_data)

    # Assertions
    assert api_key.id is not None
    assert api_key.user_id == setup_user.id
    assert api_key.name == sample_api_key_data["name"]
    # Compare timestamps (handle timezone differences)
    assert api_key.expires_at.replace(tzinfo=None) == sample_api_key_data[
        "expires_at"
    ].replace(tzinfo=None)
    assert api_key.revoked is False
    assert api_key.created_at is not None
    assert api_key.updated_at is not None

    # Verify full key format
    assert full_key.startswith("ak_")
    assert "." in full_key

    # Parse the key to verify structure
    key_id, secret = parse_api_key(full_key)
    assert key_id == api_key.key_id
    assert verify_api_key_secret(secret, api_key.secret_hash)


def test_create_api_key_no_expiry(db, setup_user, sample_api_key_data_no_expiry):
    """Test creating an API key without expiry."""
    api_key_service = ApiKeyService(db)

    # Create API key
    api_key_data = ApiKeyCreate(
        user_id=setup_user.id,
        name=sample_api_key_data_no_expiry["name"],
        expires_at=sample_api_key_data_no_expiry["expires_at"],
    )
    api_key, full_key = api_key_service.create_api_key(api_key_data)

    # Assertions
    assert api_key.id is not None
    assert api_key.user_id == setup_user.id
    assert api_key.name == sample_api_key_data_no_expiry["name"]
    assert api_key.expires_at is None
    assert api_key.revoked is False


def test_get_api_key_by_id(db, setup_api_key):
    """Test getting an API key by ID."""
    api_key, _ = setup_api_key
    api_key_service = ApiKeyService(db)

    # Get API key
    retrieved_api_key = api_key_service.get_api_key_by_id(api_key.id)

    # Assertions
    assert retrieved_api_key is not None
    assert retrieved_api_key.id == api_key.id
    assert retrieved_api_key.key_id == api_key.key_id


def test_get_api_key_by_key_id(db, setup_api_key):
    """Test getting an API key by key_id."""
    api_key, _ = setup_api_key
    api_key_service = ApiKeyService(db)

    # Get API key
    retrieved_api_key = api_key_service.get_api_key_by_key_id(api_key.key_id)

    # Assertions
    assert retrieved_api_key is not None
    assert retrieved_api_key.id == api_key.id
    assert retrieved_api_key.key_id == api_key.key_id


def test_get_user_api_keys(db, setup_user, setup_api_key):
    """Test getting all API keys for a user."""
    api_key, _ = setup_api_key
    api_key_service = ApiKeyService(db)

    # Get user API keys
    api_keys = api_key_service.get_user_api_keys(setup_user.id)

    # Assertions
    assert len(api_keys) >= 1
    assert any(ak.id == api_key.id for ak in api_keys)


def test_revoke_api_key(db, setup_user, setup_api_key):
    """Test revoking an API key."""
    api_key, _ = setup_api_key
    api_key_service = ApiKeyService(db)

    # Revoke API key
    success = api_key_service.revoke_api_key(api_key.id, setup_user.id)

    # Assertions
    assert success is True

    # Verify the key is revoked
    revoked_api_key = api_key_service.get_api_key_by_id(api_key.id)
    assert revoked_api_key.revoked is True


def test_revoke_api_key_wrong_user(db, setup_another_user, setup_api_key):
    """Test revoking an API key with wrong user (should fail)."""
    api_key, _ = setup_api_key
    api_key_service = ApiKeyService(db)

    # Try to revoke API key with wrong user
    success = api_key_service.revoke_api_key(api_key.id, setup_another_user.id)

    # Assertions
    assert success is False


def test_verify_api_key(db, setup_api_key):
    """Test verifying a valid API key."""
    api_key, full_key = setup_api_key
    api_key_service = ApiKeyService(db)

    # Verify API key
    verified_api_key = api_key_service.verify_api_key(full_key)

    # Assertions
    assert verified_api_key is not None
    assert verified_api_key.id == api_key.id
    assert verified_api_key.last_used_at is not None


def test_verify_api_key_invalid_format(db):
    """Test verifying an API key with invalid format."""
    api_key_service = ApiKeyService(db)

    # Verify invalid API key
    verified_api_key = api_key_service.verify_api_key("invalid_key")

    # Assertions
    assert verified_api_key is None


def test_verify_api_key_not_found(db):
    """Test verifying a non-existent API key."""
    api_key_service = ApiKeyService(db)

    # Verify non-existent API key
    verified_api_key = api_key_service.verify_api_key("ak_nonexistent.secret")

    # Assertions
    assert verified_api_key is None


def test_verify_api_key_expired(db, setup_expired_api_key):
    """Test verifying an expired API key."""
    api_key, full_key = setup_expired_api_key
    api_key_service = ApiKeyService(db)

    # Verify expired API key
    verified_api_key = api_key_service.verify_api_key(full_key)

    # Assertions
    assert verified_api_key is None


def test_verify_api_key_revoked(db, setup_revoked_api_key):
    """Test verifying a revoked API key."""
    api_key, full_key = setup_revoked_api_key
    api_key_service = ApiKeyService(db)

    # Verify revoked API key
    verified_api_key = api_key_service.verify_api_key(full_key)

    # Assertions
    assert verified_api_key is None


def test_verify_api_key_wrong_secret(db, setup_api_key):
    """Test verifying an API key with wrong secret."""
    api_key, _ = setup_api_key
    api_key_service = ApiKeyService(db)

    # Create a key with wrong secret
    key_id, _ = parse_api_key("ak_test.wrong_secret")
    wrong_key = f"ak_{api_key.key_id}.wrong_secret"

    # Verify with wrong secret
    verified_api_key = api_key_service.verify_api_key(wrong_key)

    # Assertions
    assert verified_api_key is None


def test_delete_api_key(db, setup_user, setup_api_key):
    """Test deleting an API key."""
    api_key, _ = setup_api_key
    api_key_service = ApiKeyService(db)

    # Delete API key
    success = api_key_service.delete_api_key(api_key.id, setup_user.id)

    # Assertions
    assert success is True

    # Verify the key is deleted
    deleted_api_key = api_key_service.get_api_key_by_id(api_key.id)
    assert deleted_api_key is None


def test_delete_api_key_wrong_user(db, setup_another_user, setup_api_key):
    """Test deleting an API key with wrong user (should fail)."""
    api_key, _ = setup_api_key
    api_key_service = ApiKeyService(db)

    # Try to delete API key with wrong user
    success = api_key_service.delete_api_key(api_key.id, setup_another_user.id)

    # Assertions
    assert success is False


def test_api_key_not_found_cases(db, setup_user):
    """Test various not found cases."""
    api_key_service = ApiKeyService(db)
    non_existent_id = uuid4()

    # Get non-existent API key by ID
    assert api_key_service.get_api_key_by_id(non_existent_id) is None

    # Get by non-existent key_id
    assert api_key_service.get_api_key_by_key_id("nonexistent") is None

    # Revoke non-existent API key
    assert api_key_service.revoke_api_key(non_existent_id, setup_user.id) is False

    # Delete non-existent API key
    assert api_key_service.delete_api_key(non_existent_id, setup_user.id) is False


def test_api_key_model_methods(
    db, setup_api_key, setup_expired_api_key, setup_revoked_api_key
):
    """Test API key model helper methods."""
    # Test valid API key
    valid_api_key, _ = setup_api_key
    assert valid_api_key.is_valid() is True
    assert valid_api_key.is_expired() is False

    # Test expired API key
    expired_api_key, _ = setup_expired_api_key
    assert expired_api_key.is_expired() is True
    assert expired_api_key.is_valid() is False

    # Test revoked API key
    revoked_api_key, _ = setup_revoked_api_key
    assert revoked_api_key.revoked is True
    assert revoked_api_key.is_valid() is False
