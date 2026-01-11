"""
BOA SDK Exceptions
"""


class BOAError(Exception):
    """Base exception for BOA SDK."""
    pass


class BOAConnectionError(BOAError):
    """Failed to connect to BOA server."""
    pass


class BOANotFoundError(BOAError):
    """Resource not found."""
    
    def __init__(self, resource_type: str, resource_id: str):
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(f"{resource_type} {resource_id} not found")


class BOAValidationError(BOAError):
    """Validation error from server."""
    
    def __init__(self, message: str, details: dict | None = None):
        self.details = details or {}
        super().__init__(message)


class BOAServerError(BOAError):
    """Server error."""
    
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"Server error {status_code}: {message}")





