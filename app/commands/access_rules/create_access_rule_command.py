import logging
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.events.access_rule_events import build_access_rule_created_event
from app.exceptions.access_rule_error import AccessRuleAlreadyExistsError
from app.models.access_rule import AccessRule
from app.models.user import User
from app.repositories.access_rule_repository import AccessRuleRepository
from app.schemas.access_rule import AccessRuleCreate
from tessera_sdk.infra.events.nats_router import NatsEventPublisher


class CreateAccessRuleCommand:
    """
    Command to create an access rule.
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

    def execute(
        self, access_rule_data: AccessRuleCreate, created_by: User
    ) -> AccessRule:
        try:
            existing_rule = self.access_rule_service.get_access_rule_by_kind_value(
                access_rule_data.kind, access_rule_data.value
            )
            if existing_rule:
                raise self._already_exists_error(access_rule_data)

            access_rule = self.access_rule_service.create_access_rule(access_rule_data)
            self._publish_access_rule_created_event(access_rule, created_by)
            return access_rule

        except AccessRuleAlreadyExistsError:
            raise
        except IntegrityError:
            self.db.rollback()
            raise self._already_exists_error(access_rule_data)
        except Exception as e:
            self.db.rollback()
            raise Exception(f"Failed to create access rule: {str(e)}")

    def _publish_access_rule_created_event(
        self, access_rule: AccessRule, user: User
    ) -> None:
        event = build_access_rule_created_event(access_rule, user)

        if self.nats_publisher is not None:
            self.logger.info(
                f"Publishing access_rule-created event to NATS: {event.model_dump_json()}"
            )
            try:
                self.nats_publisher.publish_sync(event, event.event_type)
            except Exception:  # pragma: no cover - defensive logging
                self.logger.exception(
                    "Failed to publish access_rule-created event to NATS"
                )

    def _already_exists_error(
        self, access_rule_data: AccessRuleCreate
    ) -> AccessRuleAlreadyExistsError:
        return AccessRuleAlreadyExistsError(
            f"Access rule with kind '{access_rule_data.kind}' and value '{access_rule_data.value}' already exists"
        )
