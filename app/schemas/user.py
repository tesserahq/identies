from pydantic import BaseModel, ConfigDict, EmailStr, model_validator
from typing import Optional
from uuid import UUID
from datetime import datetime

from app.config import get_settings
from app.constants.user_kinds import UserKind
from vaulta_client.utils import sign_serve_url


class UserBase(BaseModel):
    """Base user model containing common user attributes."""

    email: Optional[EmailStr] = None
    """User's email address. Must be a valid email format."""

    avatar_url: Optional[str] = None
    """URL to the user's profile picture or avatar."""

    avatar_asset_id: Optional[str] = None
    """Asset ID of the user's profile picture or avatar."""

    first_name: str
    """User's first name. Required field."""

    last_name: str
    """User's last name. Required field."""

    preferred_name: Optional[str] = None
    """User's preferred display name. Optional."""

    provider: Optional[str] = None
    """Authentication provider (e.g., 'google', 'github', etc.) if user signed up via OAuth."""

    confirmed_at: Optional[datetime] = None
    """Timestamp when the user confirmed their email address."""

    verified: bool = False
    """Whether the user's account has been verified. Defaults to False."""

    verified_at: Optional[datetime] = None
    """Timestamp when the user's account was verified."""

    theme_preference: Optional[str] = "system"
    """User's theme preference. Can be 'system', 'dark', or 'light'. Defaults to 'system'."""

    model_config = ConfigDict(from_attributes=True)


class UserCreate(UserBase):
    """Schema for creating a new user. Inherits all fields from UserBase."""

    pass


class UserOnboard(UserBase):
    """Schema for onboarding a new user with external authentication."""

    external_id: str
    """Unique identifier from the external authentication provider."""

    service_account: bool = False
    """Computed from ``kind``: true for agents and service accounts. Kept for compatibility; prefer ``kind``."""


class UserUpdate(BaseModel):
    """Schema for updating an existing user. All fields are optional."""

    email: Optional[EmailStr] = None
    """Updated email address. Must be a valid email format."""

    avatar_asset_id: Optional[str] = None
    """Updated avatar asset ID."""

    first_name: Optional[str] = None
    """Updated first name."""

    last_name: Optional[str] = None
    """Updated last name."""

    preferred_name: Optional[str] = None
    """Updated preferred display name."""

    provider: Optional[str] = None
    """Updated authentication provider."""

    verified: Optional[bool] = None
    """Updated verification status."""

    verified_at: Optional[datetime] = None
    """Updated verification timestamp."""

    theme_preference: Optional[str] = None
    """Updated theme preference. Can be 'system', 'dark', or 'light'."""


class UserOffboardingScheduleRequest(BaseModel):
    """Schema for scheduling a user's offboarding."""

    scheduled_at: Optional[datetime] = None
    """When offboarding should take effect. Defaults to 24 hours from now if omitted."""


class UserInDB(UserBase):
    """Schema representing a user as stored in the database. Includes database-specific fields."""

    id: UUID
    """Unique identifier for the user in the database."""

    created_at: datetime
    """Timestamp when the user record was created."""

    updated_at: datetime
    """Timestamp when the user record was last updated."""

    model_config = ConfigDict(from_attributes=True)


class User(UserInDB):
    """Schema for user data returned in API responses. Inherits all fields from UserInDB."""

    external_id: Optional[str] = None
    """External ID of the user."""

    service_account: bool = False
    """Computed from ``kind``: true for agents and service accounts. Kept for compatibility; prefer ``kind``."""

    kind: UserKind = UserKind.HUMAN
    """What kind of principal this is: human, agent or service_account."""


class UserResponse(BaseModel):
    """Schema for user data returned in API responses, prioritizing avatar_asset_id over avatar_url."""

    id: UUID
    """Unique identifier for the user in the database."""

    email: Optional[EmailStr] = None
    """User's email address. Must be a valid email format."""

    avatar_url: Optional[str] = None
    """URL to the user's profile picture or avatar. Returns avatar_asset_id if present, otherwise avatar_url."""

    avatar_asset_id: Optional[str] = None
    """Asset ID of the user's profile picture or avatar."""

    first_name: str
    """User's first name. Required field."""

    last_name: str
    """User's last name. Required field."""

    preferred_name: Optional[str] = None
    """User's preferred display name. Optional."""

    provider: Optional[str] = None
    """Authentication provider (e.g., 'google', 'github', etc.) if user signed up via OAuth."""

    confirmed_at: Optional[datetime] = None
    """Timestamp when the user confirmed their email address."""

    verified: bool = False
    """Whether the user's account has been verified. Defaults to False."""

    verified_at: Optional[datetime] = None
    """Timestamp when the user's account was verified."""

    theme_preference: Optional[str] = "system"
    """User's theme preference. Can be 'system', 'dark', or 'light'. Defaults to 'system'."""

    created_at: datetime
    """Timestamp when the user record was created."""

    updated_at: datetime
    """Timestamp when the user record was last updated."""

    external_id: Optional[str] = None
    """External ID of the user."""

    service_account: bool = False
    """Computed from ``kind``: true for agents and service accounts. Kept for compatibility; prefer ``kind``."""

    kind: UserKind = UserKind.HUMAN
    """What kind of principal this is: human, agent or service_account."""

    offboarding_scheduled_at: Optional[datetime] = None
    """When the user is scheduled to be offboarded, if any."""

    offboarding_scheduled_by: Optional[UUID] = None
    """ID of the admin who scheduled the offboarding, if any."""

    @model_validator(mode="after")
    def set_avatar_url_from_asset_id(self):
        """Set avatar_url to signed URL from avatar_asset_id if avatar_asset_id is present."""
        if self.avatar_asset_id:
            settings = get_settings()
            self.avatar_url = sign_serve_url(
                asset_id=self.avatar_asset_id,
                client_id=settings.vaulta_client_id,
                client_secret=settings.vaulta_client_secret,
                host_url=settings.vaulta_api_url,
            )
        return self

    model_config = ConfigDict(from_attributes=True)


class UserDetails(BaseModel):
    """Schema for detailed user information, typically used in profile views."""

    id: UUID
    """Unique identifier for the user."""

    email: EmailStr
    """User's email address. Required and must be a valid email format."""

    avatar_url: Optional[str] = None
    """URL to the user's profile picture or avatar."""

    first_name: str
    """User's first name. Required field."""

    last_name: str
    """User's last name. Required field."""

    preferred_name: Optional[str] = None
    """User's preferred display name. Optional."""

    provider: Optional[str] = None
    """Authentication provider used by the user."""

    verified: bool = False
    """Whether the user's account has been verified. Defaults to False."""

    verified_at: Optional[datetime] = None
    """Timestamp when the user's account was verified."""

    theme_preference: Optional[str] = "system"
    """User's theme preference. Can be 'system', 'dark', or 'light'. Defaults to 'system'."""

    model_config = ConfigDict(from_attributes=True)
