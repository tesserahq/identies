from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.commands.agents.claim_agent_command import ClaimAgentCommand
from app.commands.agents.create_agent_command import CreateAgentCommand
from app.commands.agents.delete_agent_command import DeleteAgentCommand
from app.commands.agents.issue_agent_claim_command import IssueAgentClaimCommand
from app.commands.agents.revoke_agent_command import RevokeAgentCommand
from app.commands.agents.rotate_agent_credentials_command import (
    RotateAgentCredentialsCommand,
)
from app.db import get_db
from app.exceptions.agent_error import (
    AgentAlreadyClaimedError,
    AgentClaimError,
    AgentNotClaimedError,
    AgentNotFoundError,
)
from app.repositories.agent_repository import AgentRepository
from app.schemas.agent import (
    AgentClaimCodeResponse,
    AgentClaimRequest,
    AgentCredentialsResponse,
    AgentCreateRequest,
    AgentCreateResponse,
    AgentStatusResponse,
)
from app.schemas.user import UserResponse

# These are privileged operations for a trusted service (Linden), which authorizes the
# human's request before calling them. "/agents" is in M2M_AUTH_PATHS in the
# authentication middleware: only a service-account token from an allowed client gets
# through, and no human user is resolved. Do not add a human-facing dependency here.
router = APIRouter(prefix="/agents", tags=["Agents"])


@router.post("", response_model=AgentCreateResponse, operation_id="create_agent")
async def create_agent(
    body: AgentCreateRequest,
    db: Session = Depends(get_db),
):
    """Create an agent principal and its first claim code (returned once)."""
    try:
        agent, code, expires_at = CreateAgentCommand(db).execute(body)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return AgentCreateResponse(
        agent=UserResponse.model_validate(agent),
        claim_code=code,
        expires_at=expires_at,
    )


@router.post(
    "/claim", response_model=AgentCredentialsResponse, operation_id="claim_agent"
)
async def claim_agent(
    body: AgentClaimRequest,
    db: Session = Depends(get_db),
):
    """Exchange a claim code for the agent's OAuth client credentials (returned once).

    Every failure returns the same 400 so a caller cannot tell an invalid code from an
    expired, used or locked one.
    """
    try:
        client, client_secret = ClaimAgentCommand(db).execute(body.code)
    except AgentClaimError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return AgentCredentialsResponse(
        client_id=client.client_id,
        client_secret=client_secret,
        user_id=client.owner_id,
        expires_at=client.expires_at,
    )


@router.post(
    "/{agent_id}/claim-codes",
    response_model=AgentClaimCodeResponse,
    operation_id="issue_agent_claim_code",
)
async def issue_agent_claim_code(
    agent_id: UUID,
    db: Session = Depends(get_db),
):
    """Issue a new claim code for an unclaimed agent; the previous code stops working."""
    try:
        code, expires_at = IssueAgentClaimCommand(db).execute(agent_id)
    except AgentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except AgentAlreadyClaimedError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    return AgentClaimCodeResponse(claim_code=code, expires_at=expires_at)


def _status_response(status) -> AgentStatusResponse:
    client = status.client
    return AgentStatusResponse(
        agent=UserResponse.model_validate(status.agent),
        status=status.state,
        client_id=client.client_id if client else None,
        client_expires_at=client.expires_at if client else None,
        last_used_at=client.last_used_at if client else None,
        claim_expires_at=status.claim_expires_at,
    )


@router.get("/{agent_id}", response_model=AgentStatusResponse, operation_id="get_agent")
async def get_agent(
    agent_id: UUID,
    db: Session = Depends(get_db),
):
    """Where an agent is in its lifecycle, including when its credentials were last used."""
    repository = AgentRepository(db)
    agent = repository.get_agent(agent_id)
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(AgentNotFoundError())
        )
    return _status_response(repository.get_status(agent))


@router.post(
    "/{agent_id}/rotate",
    response_model=AgentCredentialsResponse,
    operation_id="rotate_agent_credentials",
)
async def rotate_agent_credentials(
    agent_id: UUID,
    db: Session = Depends(get_db),
):
    """Replace the agent's client secret (returned once). Also restores a revoked agent.

    The old secret stops working immediately; tokens already minted stay valid until
    they expire (at most 15 minutes). 409 if the agent has not been claimed yet.
    """
    try:
        client, client_secret = RotateAgentCredentialsCommand(db).execute(agent_id)
    except AgentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except AgentNotClaimedError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    return AgentCredentialsResponse(
        client_id=client.client_id,
        client_secret=client_secret,
        user_id=client.owner_id,
        expires_at=client.expires_at,
    )


@router.post(
    "/{agent_id}/revoke",
    response_model=AgentStatusResponse,
    operation_id="revoke_agent",
)
async def revoke_agent(
    agent_id: UUID,
    db: Session = Depends(get_db),
):
    """Cut off the agent: its credentials can no longer mint tokens and open claim codes
    stop working. Idempotent. Tokens already minted stay valid until they expire (at
    most 15 minutes). Rotate the credentials to restore access."""
    try:
        RevokeAgentCommand(db).execute(agent_id)
    except AgentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    repository = AgentRepository(db)
    return _status_response(repository.get_status(repository.get_agent(agent_id)))


@router.delete(
    "/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="delete_agent",
)
async def delete_agent(
    agent_id: UUID,
    db: Session = Depends(get_db),
):
    """Delete an agent (soft delete; records it created keep resolving it). Only agents
    can be deleted here; any other id is a 404."""
    try:
        DeleteAgentCommand(db).execute(agent_id)
    except AgentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
