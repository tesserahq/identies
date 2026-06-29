import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.events.access_rule_events import build_access_rule_deleted_event
from app.exceptions.resource_not_found_error import ResourceNotFoundError
from app.models.access_rule import AccessRule
from app.models.user import User
from app.repositories.access_rule_repository import AccessRuleRepository
from tessera_sdk.infra.events.nats_router import NatsEventPublisher


class DeleteAccessRuleCommand:
    """
    Command to delete an access rule.
    """

    def __init__(
        self, db: Session, nats_publisher: Optional[NatsEventPublisher] = None
    ):
        self.db = db
        self.access_rule_service = AccessRuleRepository(db)
        self.nats_publisher = (
            nats_publisher if nats_publisher is not None else NatsEventPublisher()
        )
        self.logger = logging.getLogger(__name__)

    def execute(self, access_rule_id: UUID, deleted_by: User) -> bool:
        try:
            access_rule = self.access_rule_service.get_access_rule(access_rule_id)
            if not access_rule:
                raise ResourceNotFoundError("Access rule not found")

            success = self.access_rule_service.delete_access_rule(access_rule_id)
            if not success:
                raise ResourceNotFoundError("Access rule not found")

            self._publish_access_rule_deleted_event(access_rule, deleted_by)
            return success

        except ResourceNotFoundError:
            raise
        except Exception as e:
            self.db.rollback()
            raise Exception(f"Failed to delete access rule: {str(e)}")

    def _publish_access_rule_deleted_event(
        self, access_rule: AccessRule, user: User
    ) -> None:
        event = build_access_rule_deleted_event(access_rule, user)

        if self.nats_publisher is not None:
            self.logger.info(
                f"Publishing access_rule-deleted event to NATS: {event.model_dump_json()}"
            )
            try:
                self.nats_publisher.publish_sync(event, event.event_type)
            except Exception:  # pragma: no cover - defensive logging
                self.logger.exception(
                    "Failed to publish access_rule-deleted event to NATS"
                )
