import secrets
import hashlib
from typing import Tuple


def generate_api_key() -> Tuple[str, str]:
    """
    Generate a new API key in the format 'ak_<key_id>.<secret>'.

    Returns:
        Tuple[str, str]: A tuple containing (full_key, key_id)
    """
    # Generate a random key ID (8 characters)
    key_id = secrets.token_urlsafe(8)

    # Generate a random secret (32 characters)
    secret = secrets.token_urlsafe(32)

    # Create the full key
    full_key = f"ak_{key_id}.{secret}"

    return full_key, key_id


def hash_secret(secret: str) -> str:
    """
    Hash a secret using SHA256.

    Args:
        secret: The secret to hash

    Returns:
        str: The SHA256 hash of the secret
    """
    return hashlib.sha256(secret.encode()).hexdigest()


def verify_api_key_secret(secret: str, secret_hash: str) -> bool:
    """
    Verify an API key secret against its hash.

    Args:
        secret: The secret to verify
        secret_hash: The stored hash to compare against

    Returns:
        bool: True if the secret matches the hash, False otherwise
    """
    return hash_secret(secret) == secret_hash


def parse_api_key(full_key: str) -> Tuple[str, str]:
    """
    Parse a full API key into its key_id and secret components.

    Args:
        full_key: The full API key in format 'ak_<key_id>.<secret>'

    Returns:
        Tuple[str, str]: A tuple containing (key_id, secret)

    Raises:
        ValueError: If the key format is invalid
    """
    if not full_key or not full_key.startswith("ak_"):
        raise ValueError("Invalid API key format")

    # Remove 'ak_' prefix
    key_part = full_key[3:]

    # Check for exactly one dot
    if key_part.count(".") != 1:
        raise ValueError("Invalid API key format")

    # Split on the dot
    parts = key_part.split(".", 1)
    key_id, secret = parts

    # Validate that both parts are not empty
    if not key_id or not secret:
        raise ValueError("Invalid API key format")

    return key_id, secret


def generate_client_credentials() -> Tuple[str, str]:
    """
    Generate new client credentials in the format 'cs_<client_id>' and a separate secret.

    Returns:
        Tuple[str, str]: A tuple containing (client_id, client_secret)
    """
    client_id = f"cs_{secrets.token_urlsafe(8)}"
    client_secret = secrets.token_urlsafe(32)
    return client_id, client_secret


def generate_link_token() -> str:
    """
    Generate a short-lived, single-use link token for external account linking.

    Returns:
        str: A URL-safe random token (no hashing; looked up by value).
    """
    return secrets.token_urlsafe(32)
