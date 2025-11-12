from pydantic import BaseModel, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime


class AccessRuleBase(BaseModel):
    """Base access rule model containing common access rule attributes."""

    kind: str
    """Type or category of the access rule (e.g., 'ip_whitelist', 'domain_restriction')."""

    value: str
    """The actual value for the access rule (e.g., IP address, domain name)."""

    note: Optional[str] = None
    """Optional note or description for the access rule."""


class AccessRuleCreate(AccessRuleBase):
    """Schema for creating a new access rule. Inherits all fields from AccessRuleBase."""

    pass


class AccessRuleUpdate(BaseModel):
    """Schema for updating an existing access rule. All fields are optional."""

    kind: Optional[str] = None
    """Updated type or category of the access rule."""

    value: Optional[str] = None
    """Updated value for the access rule."""

    note: Optional[str] = None
    """Updated note or description for the access rule."""


class AccessRuleInDB(AccessRuleBase):
    """Schema representing an access rule as stored in the database. Includes database-specific fields."""

    id: UUID
    """Unique identifier for the access rule in the database."""

    created_at: datetime
    """Timestamp when the access rule record was created."""

    updated_at: datetime
    """Timestamp when the access rule record was last updated."""

    model_config = ConfigDict(from_attributes=True)


class AccessRule(AccessRuleInDB):
    """Schema for access rule data returned in API responses. Inherits all fields from AccessRuleInDB."""

    pass
