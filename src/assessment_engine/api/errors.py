"""API error classes."""


class APIError(Exception):
    """Base API error."""

    def __init__(self, message: str, code: str = None, status_code: int = 400):
        self.message = message
        self.code = code or "error"
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(APIError):
    """Resource not found."""

    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            message=f"{resource} '{resource_id}' not found",
            code="not_found",
            status_code=404,
        )


class ValidationError(APIError):
    """Validation error."""

    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="validation_error",
            status_code=422,
        )


class ConflictError(APIError):
    """Resource conflict."""

    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="conflict",
            status_code=409,
        )
