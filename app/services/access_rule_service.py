from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from app.models.access_rule import AccessRule
from app.schemas.access_rule import AccessRuleCreate, AccessRuleUpdate
from app.utils.db.filtering import apply_filters
from app.constants.access_rule_types import AccessRuleTypes


class AccessRuleService:
    def __init__(self, db: Session):
        self.db = db

    def get_access_rule(self, access_rule_id: UUID) -> Optional[AccessRule]:
        """Get a single access rule by ID."""
        return self.db.query(AccessRule).filter(AccessRule.id == access_rule_id).first()

    def get_access_rule_by_kind_value(
        self, kind: str, value: str
    ) -> Optional[AccessRule]:
        """Get an access rule by kind and value combination."""
        return (
            self.db.query(AccessRule)
            .filter(AccessRule.kind == kind, AccessRule.value == value)
            .first()
        )

    def get_access_rules(self, skip: int = 0, limit: int = 100) -> List[AccessRule]:
        """Get a list of access rules with pagination."""
        return self.db.query(AccessRule).offset(skip).limit(limit).all()

    def create_access_rule(self, access_rule: AccessRuleCreate) -> AccessRule:
        """Create a new access rule."""
        db_access_rule = AccessRule(**access_rule.model_dump())
        self.db.add(db_access_rule)
        self.db.commit()
        self.db.refresh(db_access_rule)
        return db_access_rule

    def update_access_rule(
        self, access_rule_id: UUID, access_rule: AccessRuleUpdate
    ) -> Optional[AccessRule]:
        """Update an existing access rule."""
        db_access_rule = (
            self.db.query(AccessRule).filter(AccessRule.id == access_rule_id).first()
        )
        if db_access_rule:
            update_data = access_rule.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(db_access_rule, key, value)
            self.db.commit()
            self.db.refresh(db_access_rule)
        return db_access_rule

    def delete_access_rule(self, access_rule_id: UUID) -> bool:
        """Delete an access rule by ID."""
        db_access_rule = (
            self.db.query(AccessRule).filter(AccessRule.id == access_rule_id).first()
        )
        if db_access_rule:
            self.db.delete(db_access_rule)
            self.db.commit()
            return True
        return False

    def search(self, filters: dict) -> List[AccessRule]:
        """
        Search access rules based on dynamic filter criteria.

        Args:
            filters: A dictionary where keys are field names and values are either:
                - A direct value (e.g. {"kind": "ip_whitelist"})
                - A dictionary with 'operator' and 'value' keys (e.g. {"kind": {"operator": "ilike", "value": "%ip%"}})

        Returns:
            List[AccessRule]: Filtered list of access rules matching the criteria.
        """
        query = self.db.query(AccessRule)
        query = apply_filters(query, AccessRule, filters)
        return query.all()

    def evaluate_email_access(self, email: str) -> bool:
        """
        Evaluate if an email is allowed by any valid access rules.

        This method checks if the provided email matches any access rules of type
        'email' (exact match) or 'domain' (domain match).

        Args:
            email (str): The email address to evaluate

        Returns:
            bool: True if the email is allowed by any access rule, False otherwise
        """
        if not email or not isinstance(email, str) or "@" not in email:
            return False

        # Extract domain from email
        domain = email.split("@")[1].lower()
        email_lower = email.lower()

        # Get all active access rules
        access_rules = self.db.query(AccessRule).all()

        for rule in access_rules:
            rule_value_lower = rule.value.lower()

            if rule.kind == AccessRuleTypes.EMAIL:
                # Exact email match
                if rule_value_lower == email_lower:
                    return True
            elif rule.kind == AccessRuleTypes.DOMAIN:
                # Domain match - check if email domain matches rule value
                if rule_value_lower == domain:
                    return True

        return False
