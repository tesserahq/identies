from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Optional
from uuid import UUID
from datetime import datetime

from app.schemas.user import UserBase, UserResponse


class ServiceAccountOnboard(UserBase):
    """Schema for onboarding a new service account.

    Service accounts are users with service_account=True and use external_id
    as a unique identifier. They don't have passwords and authenticate via API keys.
    """

    external_id: str
    """Unique identifier for the service account. Typically in format 'system-{random}'."""

    service_account: bool = True
    """Whether this user is a service account. Always True for service accounts."""

    model_config = ConfigDict(from_attributes=True)


class ServiceAccountCreateRequest(BaseModel):
    """Schema for creating a new service account."""

    email: EmailStr
    """Email address for the service account. Must be unique."""

    first_name: str = Field(..., min_length=1)
    """First name for the service account."""

    last_name: str = Field(..., min_length=1)
    """Last name for the service account."""

    username: Optional[str] = None
    """Optional username for the service account."""

    model_config = ConfigDict(from_attributes=True)


class ServiceAccountUpdateRequest(BaseModel):
    """Schema for updating a service account."""

    email: Optional[EmailStr] = None
    """Updated email address."""

    first_name: Optional[str] = Field(None, min_length=1)
    """Updated first name."""

    last_name: Optional[str] = Field(None, min_length=1)
    """Updated last name."""

    username: Optional[str] = None
    """Updated username."""

    model_config = ConfigDict(from_attributes=True)


class ServiceAccountListResponse(BaseModel):
    """Schema for listing service accounts."""

    data: list[UserResponse]
    """List of service accounts."""
