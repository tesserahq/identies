"""Command to delete (unlink) an external account."""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session
from tessera_sdk.events.nats_router import NatsEventPublisher

from app.events.external_account_events import (
    build_external_account_deleted_event,
)
from app.exceptions.forbidden_error import ForbiddenError
from app.exceptions.resource_not_found_error import ResourceNotFoundError
from app.models.external_account import ExternalAccount
from app.models.user import User
from app.repositories.external_account_repository import ExternalAccountRepository


class DeleteExternalAccountCommand:
    """
    Command to unlink an external account.

    Only the owner can delete their external account.
    """

    def __init__(
        self, db: Session, nats_publisher: Optional[NatsEventPublisher] = None
    ):
        self.db = db
        self.service = ExternalAccountRepository(db)
        self.nats_publisher = (
            nats_publisher if nats_publisher is not None else NatsEventPublisher()
        )
        self.logger = logging.getLogger(__name__)

    def execute(self, external_account_id: UUID, current_user: User) -> bool:
        """
        Execute the command to delete an external account.

        Args:
            external_account_id: The ID of the external account to delete
            current_user: The authenticated user (for ownership verification)

        Returns:
            bool: True if the external account was deleted

        Raises:
            ResourceNotFoundError: If the external account is not found
        """
        account = self.service.get_external_account(
            external_account_id, current_user.id
        )

        if not account:
            raise ResourceNotFoundError("External account not found")

        if account.user_id != current_user.id:
            raise ForbiddenError("You are not allowed to delete this external account")

        self.service.delete_external_account(external_account_id, current_user.id)

        self._publish_external_account_deleted_event(account, current_user)
        return True

    def _publish_external_account_deleted_event(
        self, external_account: ExternalAccount, current_user: User
    ) -> None:
        """Publish an external account deleted event to NATS."""
        event = build_external_account_deleted_event(external_account, current_user)

        if self.nats_publisher is not None:
            self.logger.info(
                f"Publishing external_account-deleted event to NATS: {event.model_dump_json()}"
            )
            try:
                self.nats_publisher.publish_sync(event, event.event_type)
            except Exception:  # pragma: no cover - defensive logging
                self.logger.exception(
                    "Failed to publish external_account-deleted event to NATS"
                )
