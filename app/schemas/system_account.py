from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Optional
from uuid import UUID
from datetime import datetime

from app.schemas.user import UserBase, UserResponse


class SystemAccountOnboard(UserBase):
    """Schema for onboarding a new system account.

    System accounts are users with service_account=True and use external_id
    as a unique identifier. They don't have passwords and authenticate via API keys.
    """

    external_id: str
    """Unique identifier for the system account. Typically in format 'system-{random}'."""

    service_account: bool = True
    """Whether this user is a service account. Always True for system accounts."""

    model_config = ConfigDict(from_attributes=True)


class SystemAccountCreateRequest(BaseModel):
    """Schema for creating a new system account."""

    email: EmailStr
    """Email address for the system account. Must be unique."""

    first_name: str = Field(..., min_length=1)
    """First name for the system account."""

    last_name: str = Field(..., min_length=1)
    """Last name for the system account."""

    username: Optional[str] = None
    """Optional username for the system account."""

    model_config = ConfigDict(from_attributes=True)


class SystemAccountUpdateRequest(BaseModel):
    """Schema for updating a system account."""

    email: Optional[EmailStr] = None
    """Updated email address."""

    first_name: Optional[str] = Field(None, min_length=1)
    """Updated first name."""

    last_name: Optional[str] = Field(None, min_length=1)
    """Updated last name."""

    username: Optional[str] = None
    """Updated username."""

    model_config = ConfigDict(from_attributes=True)


class SystemAccountListResponse(BaseModel):
    """Schema for listing system accounts."""

    data: list[UserResponse]
    """List of system accounts."""
