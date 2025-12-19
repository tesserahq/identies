import logging
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from app.schemas.system_account import SystemAccountUpdateRequest
from app.schemas.user import UserUpdate
from app.services.user_service import UserService
from app.models.user import User
from app.events.system_account_events import build_system_account_updated_event
from tessera_sdk.events.nats_router import NatsEventPublisher


class UpdateSystemAccountCommand:
    """
    Command to update a system account.
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

    def execute(
        self, system_account_id: UUID, system_account_update: SystemAccountUpdateRequest
    ) -> User:
        """
        Execute the command to update a system account.

        Args:
            system_account_id: The ID of the system account to update
            system_account_update: The update data containing fields to update

        Returns:
            User: The updated system account

        Raises:
            Exception: If system account update fails
        """
        try:
            # Verify it's a system account
            user = self.user_service.get_user(system_account_id)
            if not user:
                raise Exception("System account not found")

            if not user.service_account:
                raise Exception("User is not a system account")

            # Check if email is being updated and if it already exists
            if system_account_update.email:
                existing_user = self.user_service.get_user_by_email(
                    system_account_update.email
                )
                if existing_user and existing_user.id != system_account_id:
                    raise Exception(
                        f"User with email {system_account_update.email} already exists"
                    )

            # Convert SystemAccountUpdateRequest to UserUpdate
            # Only include fields that are actually being updated (not None)
            update_dict = {}
            if system_account_update.email is not None:
                update_dict["email"] = system_account_update.email
            if system_account_update.first_name is not None:
                update_dict["first_name"] = system_account_update.first_name
            if system_account_update.last_name is not None:
                update_dict["last_name"] = system_account_update.last_name
            if system_account_update.username is not None:
                update_dict["username"] = system_account_update.username

            # If no fields to update, return the user as-is
            if not update_dict:
                return user

            user_update = UserUpdate(**update_dict)

            # Update the system account
            updated_user = self.user_service.update_user(system_account_id, user_update)

            if not updated_user:
                raise Exception("System account not found")

            self._publish_system_account_updated_event(updated_user, system_account_id)

            return updated_user

        except Exception as e:
            # Rollback the transaction if something goes wrong
            self.db.rollback()
            raise Exception(f"Failed to update system account: {str(e)}")

    def _publish_system_account_updated_event(self, user: User, user_id: UUID) -> None:
        """
        Publish a system account updated event.

        Args:
            user: The updated system account
            user_id: The ID of the system account that was updated
        """
        event = build_system_account_updated_event(user, user_id)

        if self.nats_publisher is not None:
            self.logger.info(
                f"Publishing system-account-updated event to NATS: {event.model_dump_json()}"
            )
            try:
                self.nats_publisher.publish_sync(event, event.event_type)
            except Exception:  # pragma: no cover - defensive logging
                self.logger.exception(
                    "Failed to publish system-account-updated event to NATS"
                )
