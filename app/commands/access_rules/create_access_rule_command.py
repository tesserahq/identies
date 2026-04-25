from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions.access_rule_error import AccessRuleAlreadyExistsError
from app.models.access_rule import AccessRule
from app.repositories.access_rule_repository import AccessRuleRepository
from app.schemas.access_rule import AccessRuleCreate


class CreateAccessRuleCommand:
    """
    Command to create an access rule.
    """

    def __init__(self, db: Session):
        self.db = db
        self.access_rule_service = AccessRuleRepository(db)

    def execute(self, access_rule_data: AccessRuleCreate) -> AccessRule:
        try:
            existing_rule = self.access_rule_service.get_access_rule_by_kind_value(
                access_rule_data.kind, access_rule_data.value
            )
            if existing_rule:
                raise self._already_exists_error(access_rule_data)

            return self.access_rule_service.create_access_rule(access_rule_data)

        except AccessRuleAlreadyExistsError:
            raise
        except IntegrityError:
            self.db.rollback()
            raise self._already_exists_error(access_rule_data)
        except Exception as e:
            self.db.rollback()
            raise Exception(f"Failed to create access rule: {str(e)}")

    def _already_exists_error(
        self, access_rule_data: AccessRuleCreate
    ) -> AccessRuleAlreadyExistsError:
        return AccessRuleAlreadyExistsError(
            f"Access rule with kind '{access_rule_data.kind}' and value '{access_rule_data.value}' already exists"
        )
