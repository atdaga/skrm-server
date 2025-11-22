"""
Mixin classes for secure and consistent __repr__ implementations.

Provides automatic field masking for sensitive data and consistent
formatting across all model and schema classes.
"""

from datetime import datetime
from typing import Any, ClassVar
from uuid import UUID


class SecureReprMixin:
    """
    Mixin that provides a secure __repr__ implementation.

    Automatically masks sensitive fields and truncates long strings
    for readable, debug-friendly output.

    Class Attributes:
        _repr_fields: Optional list of field names to include in repr.
                      If None, all public fields are included.
        _repr_exclude: Optional list of field names to exclude from repr.
        _sensitive_fields: Fields to mask with '***' in repr output.
        _repr_max_length: Maximum length for string values before truncation.

    Example:
        class User(SecureReprMixin, SQLModel):
            _sensitive_fields = {'password', 'api_key'}

            id: UUID
            username: str
            password: str

        >>> user = User(id=uuid4(), username='john', password='secret')
        >>> repr(user)
        "User(id=UUID('...'), username='john', password='***')"
    """

    # Default sensitive field names to mask
    _default_sensitive_fields: ClassVar[set[str]] = {
        "password",
        "secret_key",
        "access_token",
        "refresh_token",
        "credential_id",
        "public_key",
        "aaguid",
        "db_password",
        "verification_token",
        "token",
        "secret",
        "api_key",
        "private_key",
    }

    # Class-level overrides (can be set by subclasses)
    _repr_fields: ClassVar[list[str] | None] = None
    _repr_exclude: ClassVar[set[str]] = set()
    _sensitive_fields: ClassVar[set[str]] = set()
    _repr_max_length: ClassVar[int] = 50

    def __repr__(self) -> str:
        """Generate a secure, readable repr string."""
        class_name = self.__class__.__name__

        # Get all sensitive fields (default + class-specific)
        sensitive = self._default_sensitive_fields | self._sensitive_fields

        # Determine which fields to include
        if self._repr_fields is not None:
            field_names = self._repr_fields
        else:
            # Get fields from the object
            field_names = self._get_field_names()

        # Filter out excluded fields
        field_names = [f for f in field_names if f not in self._repr_exclude]

        # Build field representations
        field_reprs = []
        for name in field_names:
            try:
                value = getattr(self, name, None)
                formatted = self._format_value(name, value, sensitive)
                field_reprs.append(f"{name}={formatted}")
            except Exception:
                # Skip fields that can't be accessed
                continue

        return f"{class_name}({', '.join(field_reprs)})"

    def _get_field_names(self) -> list[str]:
        """Get field names for repr, supporting various class types."""
        # For Pydantic/SQLModel classes - check class attribute
        if hasattr(self.__class__, "model_fields"):
            return list(self.__class__.model_fields.keys())

        # For dataclasses - check class attribute
        if hasattr(self.__class__, "__dataclass_fields__"):
            return list(self.__class__.__dataclass_fields__.keys())

        # For NamedTuples
        if hasattr(self, "_fields"):
            return list(self._fields)

        # Fallback: use __dict__ but filter private attributes
        if hasattr(self, "__dict__"):
            return [k for k in self.__dict__.keys() if not k.startswith("_")]

        return []  # pragma: no cover

    def _format_value(self, name: str, value: Any, sensitive: set[str]) -> str:
        """Format a single value for repr output."""
        # Mask sensitive fields
        if name in sensitive:
            if value is None:
                return "None"
            return "'***'"

        # Handle None
        if value is None:
            return "None"

        # Handle bytes (binary data)
        if isinstance(value, bytes):
            if len(value) > 8:
                return f"<{len(value)} bytes>"
            return repr(value)

        # Handle UUIDs - show full value
        if isinstance(value, UUID):
            return repr(str(value))

        # Handle datetime - use ISO format
        if isinstance(value, datetime):
            return repr(value.isoformat())

        # Handle strings - truncate if too long
        if isinstance(value, str):
            if len(value) > self._repr_max_length:
                truncated = value[: self._repr_max_length]
                return repr(f"{truncated}...")
            return repr(value)

        # Handle lists/dicts - show count if too large
        if isinstance(value, (list, tuple)):
            if len(value) > 3:
                return f"<{len(value)} items>"
            return repr(value)

        if isinstance(value, dict):
            if len(value) > 3:
                return f"<{len(value)} keys>"
            return repr(value)

        # Default: use standard repr
        return repr(value)


class ExceptionReprMixin:
    """
    Mixin for exception classes to provide consistent __repr__.

    Designed to work with exception classes that have message
    and optional entity information.
    """

    def __repr__(self) -> str:
        """Generate repr for exception classes."""
        class_name = self.__class__.__name__

        parts = []

        # Include message if available
        if hasattr(self, "message"):
            msg = getattr(self, "message", "")
            if len(msg) > 100:
                msg = f"{msg[:100]}..."
            parts.append(f"message={repr(msg)}")

        # Include entity_type if available
        if hasattr(self, "entity_type"):
            entity_type = getattr(self, "entity_type", None)
            if entity_type:
                parts.append(f"entity_type={repr(entity_type)}")

        # Include entity_id if available
        if hasattr(self, "entity_id"):
            entity_id = getattr(self, "entity_id", None)
            if entity_id:
                if isinstance(entity_id, UUID):
                    parts.append(f"entity_id={repr(str(entity_id))}")
                else:
                    parts.append(f"entity_id={repr(entity_id)}")

        return f"{class_name}({', '.join(parts)})"
