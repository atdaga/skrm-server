from fastapi import HTTPException, status


class UnauthorizedException(HTTPException):
    """Exception for unauthorized access."""

    def __init__(self, detail: str = "User not authenticated"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )

    def __repr__(self) -> str:
        return f"UnauthorizedException(status_code={self.status_code}, detail={self.detail!r})"


class ForbiddenException(HTTPException):
    """Exception for forbidden access."""

    def __init__(self, detail: str = "Access forbidden"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )

    def __repr__(self) -> str:
        return f"ForbiddenException(status_code={self.status_code}, detail={self.detail!r})"


class RateLimitException(HTTPException):
    """Exception for rate limit exceeded."""

    def __init__(self, detail: str = "Rate limit exceeded"):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
        )

    def __repr__(self) -> str:
        return f"RateLimitException(status_code={self.status_code}, detail={self.detail!r})"
