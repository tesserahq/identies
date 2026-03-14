"""Command to link an external account to the current user."""

import logging
from typing import Optional

from sqlalchemy.orm import Session
from tessera_sdk.events.nats_router import NatsEventPublisher

from app.events.external_account_events import (
    build_external_account_linked_event,
)
from app.exceptions.external_account_error import (
    ExternalAccountAlreadyLinkedError,
    InvalidLinkTokenError,
)
from app.models.external_account import ExternalAccount
from app.models.user import User
from app.schemas.external_account import LinkRequest
from app.repositories.external_account_repository import ExternalAccountRepository


class LinkExternalAccountCommand:
    """
    Command to link the current user to the external account referenced by the token.

    Validates token, creates ExternalAccount, invalidates token.
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

    def execute(self, body: LinkRequest, current_user: User) -> ExternalAccount:
        """
        Execute the command to link an external account.

        Args:
            body: The link request containing the token
            current_user: The authenticated user to link the account to

        Returns:
            ExternalAccount: The created or existing external account

        Raises:
            InvalidLinkTokenError: If token is invalid, expired, or already used
            ExternalAccountAlreadyLinkedError: If account is linked to another user
        """
        link_token = self.service.consume_link_token(body.token)
        if not link_token:
            raise InvalidLinkTokenError("Invalid, expired, or already used link token")

        external_id: str = link_token.external_id
        existing = self.service.get_external_account_by_external_id(external_id)
        if existing:
            if existing.user_id == current_user.id:
                self._publish_external_account_linked_event(existing, current_user)
                return existing
            raise ExternalAccountAlreadyLinkedError(
                "This external account is already linked to another user"
            )

        platform: str = link_token.platform
        data: dict = link_token.data or {}
        account = self.service.create_external_account(
            user_id=current_user.id,
            platform=platform,
            external_id=external_id,
            data=data,
        )

        self._publish_external_account_linked_event(account, current_user)
        return account

    def _publish_external_account_linked_event(
        self, external_account: ExternalAccount, current_user: User
    ) -> None:
        """Publish an external account linked event to NATS."""
        event = build_external_account_linked_event(external_account, current_user)

        if self.nats_publisher is not None:
            self.logger.info(
                f"Publishing external_account-linked event to NATS: {event.model_dump_json()}"
            )
            try:
                self.nats_publisher.publish_sync(event, event.event_type)
            except Exception:  # pragma: no cover - defensive logging
                self.logger.exception(
                    "Failed to publish external_account-linked event to NATS"
                )
