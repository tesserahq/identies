from typing import List, Optional
from uuid import UUID
from sqlalchemy import or_
from sqlalchemy.orm import Session, Query
from app.models.api_key import ApiKey
from app.models.client import Client
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, UserOnboard
from app.schemas.service_account import ServiceAccountOnboard
from datetime import datetime, timezone
from app.utils.db.filtering import apply_filters


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_user(self, user_id: UUID, include_deleted: bool = False) -> Optional[User]:
        query = self.db.query(User).filter(User.id == user_id)
        if not include_deleted:
            query = query.filter(User.deleted_at.is_(None))
        return query.first()

    def get_user_by_email(self, email: str) -> Optional[User]:
        return (
            self.db.query(User)
            .filter(User.email == email, User.deleted_at.is_(None))
            .first()
        )

    def get_user_by_id_or_external_id(self, id: str) -> User | None:
        try:
            uuid_id = UUID(str(id))
            return (
                self.db.query(User)
                .filter(
                    or_(User.id == uuid_id, User.external_id == str(id)),
                    User.deleted_at.is_(None),
                )
                .first()
            )
        except (ValueError, TypeError):
            # Not a valid UUID, only match on external_id
            return (
                self.db.query(User)
                .filter(User.external_id == str(id), User.deleted_at.is_(None))
                .first()
            )

    def get_user_by_external_id(self, external_id: str) -> Optional[User]:
        return (
            self.db.query(User)
            .filter(User.external_id == external_id, User.deleted_at.is_(None))
            .first()
        )

    def get_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        return (
            self.db.query(User)
            .filter(User.deleted_at.is_(None))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create_user(self, user: UserCreate) -> User:
        db_user = User(**user.model_dump())
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def onboard_user(self, user: UserOnboard) -> User:
        db_user = User(**user.model_dump())
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def onboard_service_account(self, service_account: ServiceAccountOnboard) -> User:
        """Onboard a service account.

        Args:
            service_account: The service account onboarding data

        Returns:
            User: The created service account
        """
        db_user = User(**service_account.model_dump())
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def update_user(self, user_id: UUID, user: UserUpdate) -> Optional[User]:
        db_user = self.get_user(user_id)
        if db_user:
            update_data = user.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(db_user, key, value)
            self.db.commit()
            self.db.refresh(db_user)
        return db_user

    def delete_user(self, user_id: UUID) -> bool:
        """Soft-delete a user and revoke everything that can authenticate as them.

        The row is kept (as a tombstone for records that reference it); it is only
        hidden from lookups. API keys and OAuth clients owned by the user are
        revoked so no credential keeps working after deletion.
        """
        db_user = self.get_user(user_id)
        if not db_user:
            return False

        db_user.deleted_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        self.db.query(ApiKey).filter(
            ApiKey.user_id == user_id, ApiKey.revoked.is_(False)
        ).update({"revoked": True}, synchronize_session=False)
        self.db.query(Client).filter(
            Client.owner_id == user_id, Client.revoked.is_(False)
        ).update({"revoked": True}, synchronize_session=False)
        self.db.commit()
        return True

    def schedule_offboarding(
        self, user_id: UUID, scheduled_at: datetime, scheduled_by: UUID
    ) -> Optional[User]:
        db_user = self.db.query(User).filter(User.id == user_id).first()
        if db_user:
            db_user.offboarding_scheduled_at = scheduled_at  # type: ignore[assignment]
            db_user.offboarding_scheduled_by = scheduled_by  # type: ignore[assignment]
            self.db.commit()
            self.db.refresh(db_user)
        return db_user

    def cancel_offboarding(self, user_id: UUID) -> Optional[User]:
        db_user = self.db.query(User).filter(User.id == user_id).first()
        if db_user:
            db_user.offboarding_scheduled_at = None  # type: ignore[assignment]
            db_user.offboarding_scheduled_by = None  # type: ignore[assignment]
            self.db.commit()
            self.db.refresh(db_user)
        return db_user

    def verify_user(self, user_id: UUID) -> Optional[User]:
        db_user = self.get_user(user_id)
        if db_user:
            db_user.verified = True  # type: ignore[assignment]
            db_user.verified_at = datetime.now(timezone.utc)  # type: ignore[assignment]
            self.db.commit()
            self.db.refresh(db_user)
        return db_user

    def search(self, filters: dict) -> List[User]:
        """
        Search users based on dynamic filter criteria.

        Args:
            filters: A dictionary where keys are field names and values are either:
                - A direct value (e.g. {"email": "test@example.com"})
                - A dictionary with 'operator' and 'value' keys (e.g. {"email": {"operator": "ilike", "value": "%@example.com"}})

        Returns:
            List[User]: Filtered list of users matching the criteria.
        """
        query = self.db.query(User).filter(User.deleted_at.is_(None))
        query = apply_filters(query, User, filters)
        return query.all()

    def get_service_accounts_query(self) -> Query:
        """
        Get a query for service accounts (users with service_account=True).

        Returns:
            Query: SQLAlchemy query object for service accounts.
        """
        return self.db.query(User).filter(
            User.service_account == True, User.deleted_at.is_(None)  # noqa: E712
        )

    def get_users_query(self, q: str | None = None) -> Query:
        """
        Get a query object for users that can be used with pagination.

        If q is provided, results are filtered by a case-insensitive "contains"
        match on first_name, last_name, or email.

        Returns:
            Query: SQLAlchemy query object for users.
        """
        query = self.db.query(User).filter(
            User.service_account == False, User.deleted_at.is_(None)  # noqa: E712
        )

        q_normalized = (q or "").strip()
        if q_normalized:
            # Escape SQL LIKE wildcards so "john_doe" doesn't match "johnXdoe" etc.
            escaped = (
                q_normalized.replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_")
            )
            pattern = f"%{escaped}%"

            query = query.filter(
                or_(
                    User.first_name.ilike(pattern, escape="\\"),
                    User.last_name.ilike(pattern, escape="\\"),
                    User.email.ilike(pattern, escape="\\"),
                )
            )

        return query.order_by(User.updated_at.desc())
