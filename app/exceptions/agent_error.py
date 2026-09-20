class AgentClaimError(Exception):
    """A claim code was invalid, expired, already used or locked.

    Deliberately carries no detail: callers must not learn which of those it was.
    """

    def __init__(self):
        super().__init__("Invalid or expired claim code")


class AgentNotFoundError(Exception):
    """The agent does not exist (or is deleted, or is not an agent)."""

    def __init__(self):
        super().__init__("Agent not found")


class AgentAlreadyClaimedError(Exception):
    """A claim code cannot be issued because the agent already has a credential."""

    def __init__(self):
        super().__init__("Agent has already been claimed")


class AgentNotClaimedError(Exception):
    """The agent has no credentials yet (issue a claim code instead)."""

    def __init__(self):
        super().__init__("Agent has not been claimed")
