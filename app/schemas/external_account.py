"""Pydantic schemas for external accounts and link tokens."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import UserResponse


class LinkTokenCreateRequest(BaseModel):
    """Request body for creating a link token."""

    platform: str = Field(
        ..., min_length=1, description="External platform (e.g. telegram)"
    )
    external_user_id: str = Field(
        ..., min_length=1, description="External platform user id"
    )
    data: Optional[dict[str, Any]] = None
    """Optional payload to store with the linked account."""

    expires_in_seconds: Optional[int] = Field(
        default=600,
        ge=1,
        description="Token TTL in seconds; default 10 minutes.",
    )

    model_config = ConfigDict(from_attributes=True)


class LinkTokenResponse(BaseModel):
    """Response after creating a link token."""

    token: str
    expires_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LinkRequest(BaseModel):
    """Request body for linking an external account with a token."""

    token: str = Field(..., min_length=1)


class ExternalAccountResponse(BaseModel):
    """External account as returned by the API."""

    id: UUID
    user_id: UUID
    platform: str
    external_id: str
    data: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CheckRequest(BaseModel):
    """Request body for checking if an external account is linked."""

    platform: str = Field(
        ..., min_length=1, description="External platform (e.g. telegram)"
    )
    external_id: str = Field(..., min_length=1, description="External platform user id")


class CheckResponse(BaseModel):
    """Response when checking if an external account is linked."""

    linked: bool
    user: Optional[UserResponse] = None
    external_accounts: Optional[ExternalAccountResponse] = None

    model_config = ConfigDict(from_attributes=True)
