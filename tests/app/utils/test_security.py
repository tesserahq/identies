import pytest
from app.utils.security import (
    generate_api_key,
    hash_secret,
    verify_api_key_secret,
    parse_api_key,
)


def test_generate_api_key():
    """Test API key generation."""
    full_key, key_id = generate_api_key()

    # Assertions
    assert full_key.startswith("ak_")
    assert "." in full_key
    assert key_id in full_key

    # Verify format: ak_<key_id>.<secret>
    parts = full_key[3:].split(".", 1)  # Remove 'ak_' prefix
    assert len(parts) == 2
    assert parts[0] == key_id
    assert len(parts[1]) > 0  # Secret should not be empty


def test_generate_api_key_uniqueness():
    """Test that generated API keys are unique."""
    keys = set()
    key_ids = set()

    # Generate multiple keys
    for _ in range(100):
        full_key, key_id = generate_api_key()

        # Check uniqueness
        assert full_key not in keys, "Generated duplicate full key"
        assert key_id not in key_ids, "Generated duplicate key_id"

        keys.add(full_key)
        key_ids.add(key_id)


def test_hash_secret():
    """Test secret hashing."""
    secret = "test_secret_123"
    hash1 = hash_secret(secret)
    hash2 = hash_secret(secret)

    # Assertions
    assert hash1 == hash2  # Same input should produce same hash
    assert len(hash1) == 64  # SHA256 produces 64-character hex string
    assert hash1 != secret  # Hash should be different from original
    assert hash1.isalnum()  # Should be alphanumeric


def test_hash_secret_different_inputs():
    """Test that different inputs produce different hashes."""
    secret1 = "secret1"
    secret2 = "secret2"

    hash1 = hash_secret(secret1)
    hash2 = hash_secret(secret2)

    # Assertions
    assert hash1 != hash2  # Different inputs should produce different hashes


def test_verify_api_key_secret():
    """Test secret verification."""
    secret = "test_secret_123"
    secret_hash = hash_secret(secret)

    # Test correct secret
    assert verify_api_key_secret(secret, secret_hash) is True

    # Test wrong secret
    assert verify_api_key_secret("wrong_secret", secret_hash) is False

    # Test with different secret
    different_secret = "different_secret"
    different_hash = hash_secret(different_secret)
    assert verify_api_key_secret(secret, different_hash) is False


def test_parse_api_key():
    """Test API key parsing."""
    full_key = "ak_test123.secret456"
    key_id, secret = parse_api_key(full_key)

    # Assertions
    assert key_id == "test123"
    assert secret == "secret456"


def test_parse_api_key_invalid_format():
    """Test parsing API keys with invalid formats."""
    # Test missing 'ak_' prefix
    with pytest.raises(ValueError, match="Invalid API key format"):
        parse_api_key("test123.secret456")

    # Test missing secret part
    with pytest.raises(ValueError, match="Invalid API key format"):
        parse_api_key("ak_test123")

    # Test multiple dots
    with pytest.raises(ValueError, match="Invalid API key format"):
        parse_api_key("ak_test123.secret.extra")

    # Test empty key
    with pytest.raises(ValueError, match="Invalid API key format"):
        parse_api_key("")


def test_parse_api_key_edge_cases():
    """Test parsing API keys with edge cases."""
    # Test with empty key_id
    with pytest.raises(ValueError, match="Invalid API key format"):
        parse_api_key("ak_.secret")

    # Test with empty secret
    with pytest.raises(ValueError, match="Invalid API key format"):
        parse_api_key("ak_test123.")


def test_integration_generate_and_parse():
    """Test integration between generation and parsing."""
    full_key, expected_key_id = generate_api_key()
    parsed_key_id, parsed_secret = parse_api_key(full_key)

    # Assertions
    assert parsed_key_id == expected_key_id
    assert len(parsed_secret) > 0


def test_integration_generate_hash_verify():
    """Test integration between generation, hashing, and verification."""
    full_key, key_id = generate_api_key()
    key_id_part, secret_part = parse_api_key(full_key)

    # Hash the secret
    secret_hash = hash_secret(secret_part)

    # Verify the secret
    assert verify_api_key_secret(secret_part, secret_hash) is True

    # Verify with wrong secret
    assert verify_api_key_secret("wrong_secret", secret_hash) is False


def test_secret_character_encoding():
    """Test that secrets work with various character encodings."""
    # Test with unicode characters
    unicode_secret = "test_🚀_secret_ñ"
    hash_result = hash_secret(unicode_secret)

    assert verify_api_key_secret(unicode_secret, hash_result) is True
    assert verify_api_key_secret("wrong", hash_result) is False


def test_key_id_and_secret_lengths():
    """Test that generated key IDs and secrets have reasonable lengths."""
    full_key, key_id = generate_api_key()
    key_id_part, secret_part = parse_api_key(full_key)

    # Assertions
    assert len(key_id_part) >= 8  # Should be at least 8 characters
    assert len(secret_part) >= 32  # Should be at least 32 characters
    assert len(key_id_part) <= 50  # Should not be excessively long
    assert len(secret_part) <= 100  # Should not be excessively long
