import logging
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from app.schemas.service_account import ServiceAccountUpdateRequest
from app.schemas.user import UserUpdate
from app.repositories.user_repository import UserRepository
from app.models.user import User
from app.events.service_account_events import build_service_account_updated_event
from tessera_sdk.events.nats_router import NatsEventPublisher


class UpdateServiceAccountCommand:
    """
    Command to update a service account.
    """

    def __init__(
        self, db: Session, nats_publisher: Optional[NatsEventPublisher] = None
    ):
        self.db = db
        self.user_service = UserRepository(db)
        self.nats_publisher = (
            nats_publisher if nats_publisher is not None else NatsEventPublisher()
        )
        self.logger = logging.getLogger(__name__)

    def execute(
        self,
        service_account_id: UUID,
        service_account_update: ServiceAccountUpdateRequest,
    ) -> User:
        """
        Execute the command to update a service account.

        Args:
            service_account_id: The ID of the service account to update
            service_account_update: The update data containing fields to update

        Returns:
            User: The updated service account

        Raises:
            Exception: If service account update fails
        """
        try:
            # Verify it's a service account
            user = self.user_service.get_user(service_account_id)
            if not user:
                raise Exception("Service account not found")

            if not user.service_account:
                raise Exception("User is not a service account")

            # Check if email is being updated and if it already exists
            if service_account_update.email:
                existing_user = self.user_service.get_user_by_email(
                    service_account_update.email
                )
                if existing_user and existing_user.id != service_account_id:
                    raise Exception(
                        f"User with email {service_account_update.email} already exists"
                    )

            # Convert ServiceAccountUpdateRequest to UserUpdate
            # Only include fields that are actually being updated (not None)
            update_dict = {}
            if service_account_update.email is not None:
                update_dict["email"] = service_account_update.email
            if service_account_update.first_name is not None:
                update_dict["first_name"] = service_account_update.first_name
            if service_account_update.last_name is not None:
                update_dict["last_name"] = service_account_update.last_name

            # If no fields to update, return the user as-is
            if not update_dict:
                return user

            user_update = UserUpdate(**update_dict)

            # Update the service account
            updated_user = self.user_service.update_user(
                service_account_id, user_update
            )

            if not updated_user:
                raise Exception("Service account not found")

            self._publish_service_account_updated_event(
                updated_user, service_account_id
            )

            return updated_user

        except Exception as e:
            # Rollback the transaction if something goes wrong
            self.db.rollback()
            raise Exception(f"Failed to update service account: {str(e)}")

    def _publish_service_account_updated_event(self, user: User, user_id: UUID) -> None:
        """
        Publish a service account updated event.

        Args:
            user: The updated service account
            user_id: The ID of the service account that was updated
        """
        event = build_service_account_updated_event(user, user_id)

        if self.nats_publisher is not None:
            self.logger.info(
                f"Publishing service-account-updated event to NATS: {event.model_dump_json()}"
            )
            try:
                self.nats_publisher.publish_sync(event, event.event_type)
            except Exception:  # pragma: no cover - defensive logging
                self.logger.exception(
                    "Failed to publish service-account-updated event to NATS"
                )
