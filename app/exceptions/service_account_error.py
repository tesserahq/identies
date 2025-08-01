class ServiceAccountError(Exception):
    """Exception raised when attempting to perform operations on service accounts that are not allowed."""

    def __init__(self, message: str = "Operation not allowed for service accounts"):
        self.message = message
        super().__init__(self.message)
