from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import get_settings
from app.constants.user_kinds import UserKind
from app.exceptions.agent_error import AgentAlreadyClaimedError, AgentNotFoundError
from app.repositories.agent_claim_repository import AgentClaimRepository
from app.repositories.user_repository import UserRepository


class IssueAgentClaimCommand:
    """
    Command to issue a new claim code for an existing, unclaimed agent.

    The previous open claim (if any) stops working. An agent that has already been
    claimed cannot be claimed again; rotating its key is the way to replace a credential.
    """

    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.claims = AgentClaimRepository(db)
        self.settings = get_settings()

    def execute(self, agent_id: UUID) -> tuple[str, datetime]:
        """
        Raises:
            AgentNotFoundError: no active agent with this id
            AgentAlreadyClaimedError: the agent already has a credential
        """
        agent = self.users.get_user(agent_id)
        if agent is None or agent.kind != UserKind.AGENT.value:
            raise AgentNotFoundError()
        if self.claims.has_been_claimed(agent_id):
            raise AgentAlreadyClaimedError()

        try:
            claim, code = self.claims.create_claim(
                agent_id, self.settings.agent_claim_ttl_minutes
            )
        except Exception:
            self.db.rollback()
            raise
        return code, claim.expires_at
