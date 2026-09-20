from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.commands.agents.claim_agent_command import ClaimAgentCommand
from app.commands.agents.create_agent_command import CreateAgentCommand
from app.commands.agents.issue_agent_claim_command import IssueAgentClaimCommand
from app.db import get_db
from app.exceptions.agent_error import (
    AgentAlreadyClaimedError,
    AgentClaimError,
    AgentNotFoundError,
)
from app.schemas.agent import (
    AgentClaimCodeResponse,
    AgentClaimRequest,
    AgentClaimResponse,
    AgentCreateRequest,
    AgentCreateResponse,
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


@router.post("/claim", response_model=AgentClaimResponse, operation_id="claim_agent")
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

    return AgentClaimResponse(
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
