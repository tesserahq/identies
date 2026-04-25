from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions.access_rule_error import AccessRuleAlreadyExistsError
from app.exceptions.resource_not_found_error import ResourceNotFoundError
from app.models.access_rule import AccessRule
from app.repositories.access_rule_repository import AccessRuleRepository
from app.schemas.access_rule import AccessRuleUpdate


class UpdateAccessRuleCommand:
    """
    Command to update an access rule.
    """

    def __init__(self, db: Session):
        self.db = db
        self.access_rule_service = AccessRuleRepository(db)

    def execute(
        self, access_rule: AccessRule, access_rule_data: AccessRuleUpdate
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

    def _already_exists_error(
        self, kind: str, value: str
    ) -> AccessRuleAlreadyExistsError:
        return AccessRuleAlreadyExistsError(
            f"Access rule with kind '{kind}' and value '{value}' already exists"
        )
