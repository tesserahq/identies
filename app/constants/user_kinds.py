"""User kind constants."""

from enum import Enum


class UserKind(str, Enum):
    """The kind of principal a user row represents.

    Identies models the principal only. Relationships between principals (for
    example which human is responsible for an agent) belong to the products that
    own them, not to Identies.
    """

    HUMAN = "human"
    """A person who signs in interactively."""

    AGENT = "agent"
    """An AI agent invited by a human. Authenticates with an API key only."""

    SERVICE_ACCOUNT = "service_account"
    """A trusted machine client (client credentials / token exchange)."""

    @classmethod
    def values(cls) -> list[str]:
        return [kind.value for kind in cls]
