from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime

from app.schemas.user import UserResponse


class ApiKeyBase(BaseModel):
    """Base API key model containing common attributes."""

    name: str = Field(..., min_length=1, max_length=100)
    """User-chosen label for the API key."""

    expires_at: Optional[datetime] = None
    """Optional expiration date for the API key."""


class ApiKeyCreate(ApiKeyBase):
    """Schema for creating a new API key."""

    pass


class ApiKeyResponse(ApiKeyBase):
    """Schema for API key data returned in responses."""

    id: UUID
    """Unique identifier for the API key."""

    key_id: str
    """Public part of the API key."""

    created_at: datetime
    """Timestamp when the API key was created."""

    last_used_at: Optional[datetime] = None
    """Timestamp when the API key was last used."""

    expires_at: Optional[datetime] = None
    """Optional expiration date for the API key."""

    revoked: bool = False
    """Whether the API key has been revoked."""

    class Config:
        """Pydantic model configuration."""

        from_attributes = True


class ApiKeyCreateResponse(ApiKeyResponse):
    """Schema for API key creation response, includes the full key only once."""

    full_key: str
    """The complete API key (ak_<key_id>.<secret>). Only shown once during creation."""


class ApiKeyListResponse(BaseModel):
    """Schema for listing API keys."""

    data: list[ApiKeyResponse]
    """List of API keys for the current user."""


class ApiKeyCreateRequest(BaseModel):
    """Schema for API key creation request."""

    name: str = Field(..., min_length=1, description="Name for the API key")
    """Name for the API key."""

    expires_at: Optional[datetime] = None
    """Optional expiration date for the API key."""


class ApiKeyUpdateRequest(BaseModel):
    """Schema for updating an API key."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    """Updated name for the API key."""

    revoked: Optional[bool] = None
    """Updated revoked status for the API key."""

    class Config:
        """Pydantic model configuration."""

        from_attributes = True


class ApiKeyIntrospectResponse(BaseModel):
    """Schema for API key introspection response."""

    active: bool
    """Whether the API key is active (valid, not revoked, not expired)."""

    user_id: Optional[UUID] = None
    """User ID associated with the API key. Only present if active is True."""

    user: Optional[UserResponse] = None
    """User object associated with the API key. Only present if active is True."""

    key_id: Optional[str] = None
    """Public key ID. Only present if active is True."""

    scopes: Optional[list[str]] = None
    """Scopes/permissions for the API key. Only present if active is True."""

    expires_at: Optional[datetime] = None
    """Expiration date of the API key. Only present if active is True."""

    class Config:
        """Pydantic model configuration."""

        from_attributes = True
