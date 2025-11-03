"""Unit tests for HTTP exception classes."""

import pytest
from fastapi import status

from app.core.exceptions.http_exceptions import (
    ForbiddenException,
    RateLimitException,
    UnauthorizedException,
)


class TestUnauthorizedException:
    """Test suite for UnauthorizedException."""

    def test_unauthorized_exception_default_message(self):
        """Test UnauthorizedException with default message."""
        exception = UnauthorizedException()

        assert exception.status_code == status.HTTP_401_UNAUTHORIZED
        assert exception.detail == "User not authenticated"
        assert exception.headers == {"WWW-Authenticate": "Bearer"}

    def test_unauthorized_exception_custom_message(self):
        """Test UnauthorizedException with custom message."""
        custom_message = "Invalid credentials provided"
        exception = UnauthorizedException(detail=custom_message)

        assert exception.status_code == status.HTTP_401_UNAUTHORIZED
        assert exception.detail == custom_message
        assert exception.headers == {"WWW-Authenticate": "Bearer"}

    def test_unauthorized_exception_empty_message(self):
        """Test UnauthorizedException with empty message."""
        exception = UnauthorizedException(detail="")

        assert exception.status_code == status.HTTP_401_UNAUTHORIZED
        assert exception.detail == ""
        assert exception.headers == {"WWW-Authenticate": "Bearer"}

    def test_unauthorized_exception_long_message(self):
        """Test UnauthorizedException with long message."""
        long_message = "A" * 1000
        exception = UnauthorizedException(detail=long_message)

        assert exception.status_code == status.HTTP_401_UNAUTHORIZED
        assert exception.detail == long_message
        assert len(exception.detail) == 1000

    def test_unauthorized_exception_raises_correctly(self):
        """Test that UnauthorizedException can be raised."""
        with pytest.raises(UnauthorizedException) as exc_info:
            raise UnauthorizedException("Test exception")

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "Test exception"

    def test_unauthorized_exception_inherits_from_http_exception(self):
        """Test that UnauthorizedException inherits from HTTPException."""
        from fastapi import HTTPException

        exception = UnauthorizedException()
        assert isinstance(exception, HTTPException)


class TestForbiddenException:
    """Test suite for ForbiddenException."""

    def test_forbidden_exception_default_message(self):
        """Test ForbiddenException with default message."""
        exception = ForbiddenException()

        assert exception.status_code == status.HTTP_403_FORBIDDEN
        assert exception.detail == "Access forbidden"

    def test_forbidden_exception_custom_message(self):
        """Test ForbiddenException with custom message."""
        custom_message = "You do not have permission to access this resource"
        exception = ForbiddenException(detail=custom_message)

        assert exception.status_code == status.HTTP_403_FORBIDDEN
        assert exception.detail == custom_message

    def test_forbidden_exception_empty_message(self):
        """Test ForbiddenException with empty message."""
        exception = ForbiddenException(detail="")

        assert exception.status_code == status.HTTP_403_FORBIDDEN
        assert exception.detail == ""

    def test_forbidden_exception_raises_correctly(self):
        """Test that ForbiddenException can be raised."""
        with pytest.raises(ForbiddenException) as exc_info:
            raise ForbiddenException("Insufficient permissions")

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert exc_info.value.detail == "Insufficient permissions"

    def test_forbidden_exception_inherits_from_http_exception(self):
        """Test that ForbiddenException inherits from HTTPException."""
        from fastapi import HTTPException

        exception = ForbiddenException()
        assert isinstance(exception, HTTPException)

    def test_forbidden_exception_no_auth_headers(self):
        """Test that ForbiddenException doesn't set WWW-Authenticate headers."""
        exception = ForbiddenException()
        # Headers might be None or an empty dict
        assert exception.headers is None or exception.headers == {}


class TestRateLimitException:
    """Test suite for RateLimitException."""

    def test_rate_limit_exception_default_message(self):
        """Test RateLimitException with default message."""
        exception = RateLimitException()

        assert exception.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert exception.detail == "Rate limit exceeded"

    def test_rate_limit_exception_custom_message(self):
        """Test RateLimitException with custom message."""
        custom_message = "Too many requests. Please try again in 60 seconds."
        exception = RateLimitException(detail=custom_message)

        assert exception.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert exception.detail == custom_message

    def test_rate_limit_exception_empty_message(self):
        """Test RateLimitException with empty message."""
        exception = RateLimitException(detail="")

        assert exception.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert exception.detail == ""

    def test_rate_limit_exception_raises_correctly(self):
        """Test that RateLimitException can be raised."""
        with pytest.raises(RateLimitException) as exc_info:
            raise RateLimitException("Request quota exceeded")

        assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert exc_info.value.detail == "Request quota exceeded"

    def test_rate_limit_exception_inherits_from_http_exception(self):
        """Test that RateLimitException inherits from HTTPException."""
        from fastapi import HTTPException

        exception = RateLimitException()
        assert isinstance(exception, HTTPException)

    def test_rate_limit_exception_with_retry_info(self):
        """Test RateLimitException with retry information."""
        message_with_retry = "Rate limit exceeded. Retry after 120 seconds."
        exception = RateLimitException(detail=message_with_retry)

        assert exception.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "Retry after 120 seconds" in exception.detail


class TestExceptionDifferentiation:
    """Test suite for differentiating between exception types."""

    def test_different_status_codes(self):
        """Test that each exception has a unique status code."""
        unauthorized = UnauthorizedException()
        forbidden = ForbiddenException()
        rate_limit = RateLimitException()

        assert unauthorized.status_code != forbidden.status_code
        assert forbidden.status_code != rate_limit.status_code
        assert unauthorized.status_code != rate_limit.status_code

    def test_exception_type_checking(self):
        """Test that exception types can be distinguished."""
        unauthorized = UnauthorizedException()
        forbidden = ForbiddenException()
        rate_limit = RateLimitException()

        assert type(unauthorized).__name__ == "UnauthorizedException"
        assert type(forbidden).__name__ == "ForbiddenException"
        assert type(rate_limit).__name__ == "RateLimitException"

    def test_catch_specific_exception_types(self):
        """Test that specific exception types can be caught."""
        # Test catching UnauthorizedException
        with pytest.raises(UnauthorizedException):
            raise UnauthorizedException()

        # Test catching ForbiddenException
        with pytest.raises(ForbiddenException):
            raise ForbiddenException()

        # Test catching RateLimitException
        with pytest.raises(RateLimitException):
            raise RateLimitException()

    def test_catch_as_http_exception(self):
        """Test that all custom exceptions can be caught as HTTPException."""
        from fastapi import HTTPException

        # Test UnauthorizedException
        with pytest.raises(HTTPException):
            raise UnauthorizedException()

        # Test ForbiddenException
        with pytest.raises(HTTPException):
            raise ForbiddenException()

        # Test RateLimitException
        with pytest.raises(HTTPException):
            raise RateLimitException()
