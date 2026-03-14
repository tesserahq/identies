"""Repository for external accounts and link tokens."""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Query, Session

from app.models.external_account import ExternalAccount
from app.models.link_token import LinkToken
from app.utils.security import generate_link_token


class ExternalAccountRepository:
    """Repository for external account CRUD and link token create/consume."""

    def __init__(self, db: Session):
        self.db = db

    def get_external_account(
        self, external_account_id: UUID, user_id: UUID
    ) -> Optional[ExternalAccount]:
        """Fetch a single external account by id scoped to user."""
        return (
            self.db.query(ExternalAccount)
            .filter(
                ExternalAccount.id == external_account_id,
                ExternalAccount.user_id == user_id,
            )
            .first()
        )

    def get_external_account_by_external_id(
        self, external_id: str
    ) -> Optional[ExternalAccount]:
        """Fetch external account by external_id (unique globally)."""
        return (
            self.db.query(ExternalAccount)
            .filter(ExternalAccount.external_id == external_id)
            .first()
        )

    def get_external_account_by_platform_and_external_id(
        self, platform: str, external_id: str
    ) -> Optional[ExternalAccount]:
        """Fetch external account by platform and external_id."""
        return (
            self.db.query(ExternalAccount)
            .filter(
                ExternalAccount.platform == platform,
                ExternalAccount.external_id == external_id,
            )
            .first()
        )

    def get_external_accounts_query(
        self, user_id: UUID, platform: Optional[str] = None
    ) -> Query:
        """Query for the current user's external accounts (for pagination)."""
        query = (
            self.db.query(ExternalAccount)
            .filter(ExternalAccount.user_id == user_id)
            .order_by(ExternalAccount.created_at.desc())
        )
        if platform is not None:
            query = query.filter(ExternalAccount.platform == platform)
        return query

    def create_external_account(
        self,
        user_id: UUID,
        platform: str,
        external_id: str,
        data: Optional[dict[str, Any]] = None,
    ) -> ExternalAccount:
        """Create an external account; data defaults to {}."""
        payload = data if data is not None else {}
        account = ExternalAccount(
            user_id=user_id,
            platform=platform,
            external_id=external_id,
            data=payload,
        )
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        return account

    def delete_external_account(self, external_account_id: UUID, user_id: UUID) -> bool:
        """Delete an external account only if owned by user."""
        account = self.get_external_account(external_account_id, user_id)
        if account:
            self.db.delete(account)
            self.db.commit()
            return True
        return False

    def create_link_token(
        self,
        platform: str,
        external_user_id: str,
        data: Optional[dict[str, Any]] = None,
        expires_in_seconds: int = 600,
    ) -> tuple[str, datetime]:
        """
        Create a short-lived link token. Returns (token, expires_at).
        """
        token_value = generate_link_token()
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)
        payload = data if data is not None else {}
        link_token = LinkToken(
            token=token_value,
            platform=platform,
            external_id=external_user_id,
            data=payload,
            expires_at=expires_at,
        )
        self.db.add(link_token)
        self.db.commit()
        self.db.refresh(link_token)
        return token_value, expires_at

    def consume_link_token(self, token: str) -> Optional[LinkToken]:
        """
        Find token, validate (not expired, not used), set used_at, commit.
        Returns the LinkToken row if valid, None otherwise.
        """
        link_token = self.db.query(LinkToken).filter(LinkToken.token == token).first()
        if not link_token:
            return None
        if link_token.used_at is not None:
            return None
        if link_token.expires_at <= datetime.now(timezone.utc):
            return None
        link_token.used_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(link_token)
        return link_token
