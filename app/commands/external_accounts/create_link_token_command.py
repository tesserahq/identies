"""Command to create a short-lived link token."""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session
from tessera_sdk.events.nats_router import NatsEventPublisher

from app.events.external_account_events import (
    build_link_token_created_event,
)
from app.schemas.external_account import LinkTokenCreateRequest
from app.repositories.external_account_repository import ExternalAccountRepository


class CreateLinkTokenCommand:
    """
    Command to create a short-lived, single-use link token.

    Intended for backend/webhook use (e.g. external platform creates token
    when user starts linking).
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

    def execute(self, body: LinkTokenCreateRequest) -> tuple[str, datetime]:
        """
        Execute the command to create a link token.

        Args:
            body: The link token creation request

        Returns:
            tuple[str, datetime]: (token_value, expires_at)
        """
        token_value, expires_at = self.service.create_link_token(
            platform=body.platform,
            external_user_id=body.external_user_id,
            data=body.data,
            expires_in_seconds=body.expires_in_seconds or 600,
        )

        self._publish_link_token_created_event(
            platform=body.platform,
            external_user_id=body.external_user_id,
            expires_at=expires_at,
            data=body.data,
        )

        return token_value, expires_at

    def _publish_link_token_created_event(
        self,
        platform: str,
        external_user_id: str,
        expires_at: datetime,
        data: Optional[dict] = None,
    ) -> None:
        """Publish a link token created event to NATS."""
        event = build_link_token_created_event(
            platform=platform,
            external_user_id=external_user_id,
            expires_at=expires_at,
            data=data,
        )

        if self.nats_publisher is not None:
            self.logger.info(
                f"Publishing link_token-created event to NATS: {event.model_dump_json()}"
            )
            try:
                self.nats_publisher.publish_sync(event, event.event_type)
            except Exception:  # pragma: no cover - defensive logging
                self.logger.exception(
                    "Failed to publish link_token-created event to NATS"
                )
