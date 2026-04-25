from uuid import UUID

from sqlalchemy.orm import Session

from app.exceptions.resource_not_found_error import ResourceNotFoundError
from app.repositories.access_rule_repository import AccessRuleRepository


class DeleteAccessRuleCommand:
    """
    Command to delete an access rule.
    """

    def __init__(self, db: Session):
        self.db = db
        self.access_rule_service = AccessRuleRepository(db)

    def execute(self, access_rule_id: UUID) -> bool:
        try:
            success = self.access_rule_service.delete_access_rule(access_rule_id)
            if not success:
                raise ResourceNotFoundError("Access rule not found")
            return success

        except ResourceNotFoundError:
            raise
        except Exception as e:
            self.db.rollback()
            raise Exception(f"Failed to delete access rule: {str(e)}")
