from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from app.models.api_key import ApiKey
from app.utils.security import generate_api_key, hash_secret, parse_api_key
from datetime import datetime, timezone


class ApiKeyService:
    def __init__(self, db: Session):
        self.db = db

    def create_api_key(
        self, user_id: UUID, name: str, expires_at: Optional[datetime] = None
    ) -> tuple[ApiKey, str]:
        """
        Create a new API key for a user.

        Args:
            user_id: The ID of the user creating the API key
            name: The name for the API key
            expires_at: Optional expiration date for the API key

        Returns:
            tuple[ApiKey, str]: A tuple containing (api_key_model, full_key)
        """
        # Generate the API key
        full_key, key_id = generate_api_key()
        key_id_part, secret_part = parse_api_key(full_key)

        # Create the API key model
        db_api_key = ApiKey(
            user_id=user_id,
            key_id=key_id_part,
            secret_hash=hash_secret(secret_part),
            name=name,
            expires_at=expires_at,
        )

        self.db.add(db_api_key)
        self.db.commit()
        self.db.refresh(db_api_key)

        return db_api_key, full_key

    def get_api_key_by_id(self, api_key_id: UUID) -> Optional[ApiKey]:
        """Get an API key by its ID."""
        return self.db.query(ApiKey).filter(ApiKey.id == api_key_id).first()

    def get_api_key_by_key_id(self, key_id: str) -> Optional[ApiKey]:
        """Get an API key by its key_id."""
        return self.db.query(ApiKey).filter(ApiKey.key_id == key_id).first()

    def get_user_api_keys(self, user_id: UUID) -> List[ApiKey]:
        """Get all API keys for a specific user."""
        return (
            self.db.query(ApiKey)
            .filter(ApiKey.user_id == user_id)
            .order_by(ApiKey.created_at.desc())
            .all()
        )

    def revoke_api_key(self, api_key_id: UUID, user_id: UUID) -> bool:
        """
        Revoke an API key.

        Args:
            api_key_id: The ID of the API key to revoke
            user_id: The ID of the user (for security)

        Returns:
            bool: True if the key was revoked, False if not found or not owned by user
        """
        db_api_key = (
            self.db.query(ApiKey)
            .filter(ApiKey.id == api_key_id, ApiKey.user_id == user_id)
            .first()
        )

        if db_api_key:
            setattr(db_api_key, "revoked", True)
            self.db.commit()
            return True
        return False

    def verify_api_key(self, full_key: str) -> Optional[ApiKey]:
        """
        Verify an API key and return the associated user's API key record.

        Args:
            full_key: The full API key to verify

        Returns:
            Optional[ApiKey]: The API key record if valid, None otherwise
        """
        try:
            key_id, secret = parse_api_key(full_key)
        except ValueError:
            return None

        # Get the API key from the database with user relationship
        db_api_key = self.db.query(ApiKey).filter(ApiKey.key_id == key_id).first()
        if not db_api_key:
            return None

        # Check if the key is valid (not revoked and not expired)
        if not db_api_key.is_valid():
            return None

        # Verify the secret
        if not self._verify_secret(secret, db_api_key.secret_hash):
            return None

        # Update last_used_at
        setattr(db_api_key, "last_used_at", datetime.now(timezone.utc))
        self.db.commit()

        return db_api_key

    def _verify_secret(self, secret: str, secret_hash: str) -> bool:
        """Verify a secret against its hash."""
        from app.utils.security import verify_api_key_secret

        return verify_api_key_secret(secret, secret_hash)

    def delete_api_key(self, api_key_id: UUID, user_id: UUID) -> bool:
        """
        Delete an API key.

        Args:
            api_key_id: The ID of the API key to delete
            user_id: The ID of the user (for security)

        Returns:
            bool: True if the key was deleted, False if not found or not owned by user
        """
        db_api_key = (
            self.db.query(ApiKey)
            .filter(ApiKey.id == api_key_id, ApiKey.user_id == user_id)
            .first()
        )

        if db_api_key:
            self.db.delete(db_api_key)
            self.db.commit()
            return True
        return False
