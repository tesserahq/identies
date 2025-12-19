import logging
import secrets
from typing import Optional
from sqlalchemy.orm import Session
from app.schemas.system_account import (
    SystemAccountCreateRequest,
    SystemAccountOnboard,
)
from app.services.user_service import UserService
from app.models.user import User
from app.events.system_account_events import build_system_account_created_event
from tessera_sdk.events.nats_router import NatsEventPublisher


class CreateSystemAccountCommand:
    """
    Command to create a new system account.
    System accounts are users with service_account=True and don't have passwords.
    """

    def __init__(
        self, db: Session, nats_publisher: Optional[NatsEventPublisher] = None
    ):
        self.db = db
        self.user_service = UserService(db)
        self.nats_publisher = (
            nats_publisher if nats_publisher is not None else NatsEventPublisher()
        )
        self.logger = logging.getLogger(__name__)

    def execute(self, system_account_data: SystemAccountCreateRequest) -> User:
        """
        Execute the command to create a system account.

        Args:
            system_account_data: The system account creation data

        Returns:
            User: The created system account

        Raises:
            Exception: If system account creation fails
        """
        try:
            # Check if email already exists
            existing_user = self.user_service.get_user_by_email(
                system_account_data.email
            )
            if existing_user:
                raise Exception(
                    f"User with email {system_account_data.email} already exists"
                )

            # Create the system account using SystemAccountOnboard schema
            # System accounts use external_id as a unique identifier
            # We'll use a format like "system-{random}" to generate a unique external_id
            external_id = f"system-{secrets.token_urlsafe(16)}"

            system_account_onboard = SystemAccountOnboard(
                email=system_account_data.email,
                first_name=system_account_data.first_name,
                last_name=system_account_data.last_name,
                username=system_account_data.username,
                external_id=external_id,
                service_account=True,
            )

            # Create the system account
            user = self.user_service.onboard_system_account(system_account_onboard)

            if not user:
                raise Exception("Failed to create system account")

            self._publish_system_account_created_event(user)

            return user

        except Exception as e:
            # Rollback the transaction if something goes wrong
            self.db.rollback()
            raise Exception(f"Failed to create system account: {str(e)}")

    def _publish_system_account_created_event(self, user: User) -> None:
        """
        Publish a system account created event.

        Args:
            user: The created system account
        """
        event = build_system_account_created_event(user)

        if self.nats_publisher is not None:
            self.logger.info(
                f"Publishing system-account-created event to NATS: {event.model_dump_json()}"
            )
            try:
                self.nats_publisher.publish_sync(event, event.event_type)
            except Exception:  # pragma: no cover - defensive logging
                self.logger.exception(
                    "Failed to publish system-account-created event to NATS"
                )
