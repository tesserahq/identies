import logging
import secrets
from typing import Optional
from sqlalchemy.orm import Session
from app.schemas.service_account import (
    ServiceAccountCreateRequest,
    ServiceAccountOnboard,
)
from app.repositories.user_repository import UserRepository
from app.models.user import User
from app.events.service_account_events import build_service_account_created_event
from tessera_sdk.events.nats_router import NatsEventPublisher


class CreateServiceAccountCommand:
    """
    Command to create a new service account.
    Service accounts are users with service_account=True and don't have passwords.
    """

    def __init__(
        self, db: Session, nats_publisher: Optional[NatsEventPublisher] = None
    ):
        self.db = db
        self.user_repository = UserRepository(db)
        self.nats_publisher = (
            nats_publisher if nats_publisher is not None else NatsEventPublisher()
        )
        self.logger = logging.getLogger(__name__)

    def execute(self, service_account_data: ServiceAccountCreateRequest) -> User:
        """
        Execute the command to create a service account.

        Args:
            service_account_data: The service account creation data

        Returns:
            User: The created service account

        Raises:
            Exception: If service account creation fails
        """
        try:
            # Check if email already exists
            existing_user = self.user_repository.get_user_by_email(
                service_account_data.email
            )
            if existing_user:
                raise Exception(
                    f"User with email {service_account_data.email} already exists"
                )

            # Create the service account using ServiceAccountOnboard schema
            # Service accounts use external_id as a unique identifier
            # We'll use a format like "system-{random}" to generate a unique external_id
            external_id = f"system-{secrets.token_urlsafe(16)}"

            service_account_onboard = ServiceAccountOnboard(
                email=service_account_data.email,
                first_name=service_account_data.first_name,
                last_name=service_account_data.last_name,
                username=service_account_data.username,
                external_id=external_id,
                service_account=True,
            )

            # Create the service account
            user = self.user_repository.onboard_service_account(service_account_onboard)

            if not user:
                raise Exception("Failed to create service account")

            self._publish_service_account_created_event(user)

            return user

        except Exception as e:
            # Rollback the transaction if something goes wrong
            self.db.rollback()
            raise Exception(f"Failed to create service account: {str(e)}")

    def _publish_service_account_created_event(self, user: User) -> None:
        """
        Publish a service account created event.

        Args:
            user: The created service account
        """
        event = build_service_account_created_event(user)

        if self.nats_publisher is not None:
            self.logger.info(
                f"Publishing service-account-created event to NATS: {event.model_dump_json()}"
            )
            try:
                self.nats_publisher.publish_sync(event, event.event_type)
            except Exception:  # pragma: no cover - defensive logging
                self.logger.exception(
                    "Failed to publish service-account-created event to NATS"
                )
