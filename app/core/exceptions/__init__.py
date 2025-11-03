"""Exception classes for the application."""

from .domain_exceptions import (
    DomainException,
    InsufficientPrivilegesException,
    InvalidCredentialsException,
    InvalidTokenException,
    InvalidUserIdException,
    TeamAlreadyExistsException,
    TeamNotFoundException,
    TeamUpdateConflictException,
    TokenNotFoundException,
    UserNotFoundException,
)
from .http_exceptions import (
    ForbiddenException,
    RateLimitException,
    UnauthorizedException,
)

__all__ = [
    # Domain exceptions
    "DomainException",
    "InsufficientPrivilegesException",
    "InvalidCredentialsException",
    "InvalidTokenException",
    "InvalidUserIdException",
    "TeamAlreadyExistsException",
    "TeamNotFoundException",
    "TeamUpdateConflictException",
    "TokenNotFoundException",
    "UserNotFoundException",
    # HTTP exceptions
    "ForbiddenException",
    "RateLimitException",
    "UnauthorizedException",
]

