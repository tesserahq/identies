class OffboardingAlreadyScheduledError(Exception):
    """Raised when scheduling offboarding for a user that already has one pending."""

    pass


class OffboardingNotScheduledError(Exception):
    """Raised when cancelling offboarding for a user with none pending."""

    pass
