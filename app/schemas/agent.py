from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import UserResponse


class AgentCreateRequest(BaseModel):
    """Request to create an agent principal. Sent by a trusted service, not by a human."""

    name: str = Field(..., min_length=1, max_length=100)
    """Display name of the agent (shown as its first name)."""


class AgentCreateResponse(BaseModel):
    """A newly created agent and the one-time claim code for its credential."""

    agent: UserResponse
    claim_code: str
    """Plaintext claim code. Returned only once; only a hash is stored."""

    expires_at: datetime
    """When the claim code stops working."""


class AgentClaimCodeResponse(BaseModel):
    """A freshly issued claim code for an existing, unclaimed agent."""

    claim_code: str
    expires_at: datetime


class AgentClaimRequest(BaseModel):
    code: str = Field(..., min_length=1)


class AgentCredentialsResponse(BaseModel):
    """The agent's OAuth client credentials. Returned only once.

    The agent exchanges them for short-lived JWT access tokens at ``/oauth/token``
    (client credentials grant).
    """

    client_id: str
    client_secret: str
    """Only its hash is stored."""

    user_id: UUID
    """The agent user; it is the ``sub`` of the tokens minted with these credentials."""

    expires_at: datetime | None = None
    """When the client secret stops working (rotate it before then)."""

    model_config = ConfigDict(from_attributes=True)


class AgentStatusResponse(BaseModel):
    """Where an agent is in its lifecycle, for an owner-facing list."""

    agent: UserResponse

    status: Literal["unclaimed", "active", "revoked", "expired"]
    """unclaimed: no credentials yet; active: can mint tokens; revoked: cut off (rotate
    to restore); expired: the client secret ran out (rotate to renew)."""

    client_id: str | None = None
    client_expires_at: datetime | None = None
    last_used_at: datetime | None = None
    """When the credentials last minted a token."""

    claim_expires_at: datetime | None = None
    """When the open claim code expires (only while unclaimed)."""
