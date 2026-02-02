"""Exceptions for external account operations."""


class InvalidLinkTokenError(Exception):
    """Raised when a link token is invalid, expired, or already used."""

    pass


class ExternalAccountAlreadyLinkedError(Exception):
    """Raised when the external account is already linked to another user."""

    pass
