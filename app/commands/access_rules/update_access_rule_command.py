import logging
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.events.access_rule_events import build_access_rule_updated_event
from app.exceptions.access_rule_error import AccessRuleAlreadyExistsError
from app.exceptions.resource_not_found_error import ResourceNotFoundError
from app.models.access_rule import AccessRule
from app.models.user import User
from app.repositories.access_rule_repository import AccessRuleRepository
from app.schemas.access_rule import AccessRuleUpdate
from tessera_sdk.infra.events.nats_router import NatsEventPublisher


class UpdateAccessRuleCommand:
    """
    Command to update an access rule.
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
        self,
        access_rule: AccessRule,
        access_rule_data: AccessRuleUpdate,
        updated_by: User,
    ) -> AccessRule:
        try:
            if access_rule_data.kind is not None or access_rule_data.value is not None:
                new_kind = str(
                    access_rule_data.kind
                    if access_rule_data.kind is not None
                    else access_rule.kind
                )
                new_value = str(
                    access_rule_data.value
                    if access_rule_data.value is not None
                    else access_rule.value
                )

                duplicate_rule = self.access_rule_service.get_access_rule_by_kind_value(
                    new_kind, new_value
                )
                if duplicate_rule and duplicate_rule.id != access_rule.id:
                    raise self._already_exists_error(new_kind, new_value)

            updated_rule = self.access_rule_service.update_access_rule(
                access_rule.id, access_rule_data
            )
            if not updated_rule:
                raise ResourceNotFoundError("Access rule not found")

            self._publish_access_rule_updated_event(updated_rule, updated_by)
            return updated_rule

        except (AccessRuleAlreadyExistsError, ResourceNotFoundError):
            raise
        except IntegrityError:
            self.db.rollback()
            new_kind = str(
                access_rule_data.kind
                if access_rule_data.kind is not None
                else access_rule.kind
            )
            new_value = str(
                access_rule_data.value
                if access_rule_data.value is not None
                else access_rule.value
            )
            raise self._already_exists_error(new_kind, new_value)
        except Exception as e:
            self.db.rollback()
            raise Exception(f"Failed to update access rule: {str(e)}")

    def _publish_access_rule_updated_event(
        self, access_rule: AccessRule, user: User
    ) -> None:
        event = build_access_rule_updated_event(access_rule, user)

        if self.nats_publisher is not None:
            self.logger.info(
                f"Publishing access_rule-updated event to NATS: {event.model_dump_json()}"
            )
            try:
                self.nats_publisher.publish_sync(event, event.event_type)
            except Exception:  # pragma: no cover - defensive logging
                self.logger.exception(
                    "Failed to publish access_rule-updated event to NATS"
                )

    def _already_exists_error(
        self, kind: str, value: str
    ) -> AccessRuleAlreadyExistsError:
        return AccessRuleAlreadyExistsError(
            f"Access rule with kind '{kind}' and value '{value}' already exists"
        )
