"""Tests for app.core.repr_mixin module."""

from dataclasses import dataclass
from datetime import datetime
from typing import NamedTuple
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict

from app.core.repr_mixin import ExceptionReprMixin, SecureReprMixin

# =============================================================================
# Test fixtures and helper classes
# =============================================================================


class SimplePydanticModel(SecureReprMixin, BaseModel):
    """Simple Pydantic model for testing."""

    id: UUID
    name: str
    value: int


class SensitiveFieldModel(SecureReprMixin, BaseModel):
    """Model with sensitive fields."""

    username: str
    password: str
    api_key: str | None = None


class CustomSensitiveModel(SecureReprMixin, BaseModel):
    """Model with custom sensitive fields."""

    _sensitive_fields = {"custom_secret"}

    name: str
    custom_secret: str


class ExplicitFieldsModel(SecureReprMixin, BaseModel):
    """Model with explicit repr fields."""

    _repr_fields = ["id", "name"]

    id: UUID
    name: str
    description: str
    internal_data: str


class ExcludedFieldsModel(SecureReprMixin, BaseModel):
    """Model with excluded fields."""

    _repr_exclude = {"internal_data"}

    id: UUID
    name: str
    internal_data: str


class CustomMaxLengthModel(SecureReprMixin, BaseModel):
    """Model with custom max length."""

    _repr_max_length = 10

    content: str


@dataclass(repr=False)
class DataclassModel(SecureReprMixin):
    """Dataclass for testing."""

    id: UUID
    name: str
    password: str


class NamedTupleBase(NamedTuple):
    """NamedTuple for testing."""

    id: UUID
    name: str


class NamedTupleModel(SecureReprMixin, NamedTupleBase):
    """NamedTuple with mixin for testing."""

    pass


class DictBasedModel(SecureReprMixin):
    """Plain class using __dict__ for testing."""

    def __init__(self, id: UUID, name: str, password: str):
        self.id = id
        self.name = name
        self.password = password
        self._private = "should not appear"


class EmptyModel(SecureReprMixin):
    """Model with no fields for testing edge case."""

    pass


class SampleException(ExceptionReprMixin, Exception):
    """Sample exception class for testing."""

    def __init__(self, message: str, entity_type: str | None = None, entity_id=None):
        super().__init__(message)
        self.message = message
        self.entity_type = entity_type
        self.entity_id = entity_id


class MinimalException(ExceptionReprMixin, Exception):
    """Exception with only message."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NoMessageException(ExceptionReprMixin, Exception):
    """Exception without message attribute."""

    pass


# =============================================================================
# SecureReprMixin Tests
# =============================================================================


class TestSecureReprMixinBasic:
    """Test basic SecureReprMixin functionality."""

    def test_simple_pydantic_model_repr(self):
        """Test repr for simple Pydantic model."""
        test_id = uuid4()
        model = SimplePydanticModel(id=test_id, name="test", value=42)
        result = repr(model)

        assert "SimplePydanticModel(" in result
        assert f"id='{test_id}'" in result
        assert "name='test'" in result
        assert "value=42" in result

    def test_sensitive_fields_masked(self):
        """Test that default sensitive fields are masked."""
        model = SensitiveFieldModel(
            username="john", password="secret123", api_key="key123"
        )
        result = repr(model)

        assert "username='john'" in result
        assert "password='***'" in result
        assert "api_key='***'" in result
        assert "secret123" not in result
        assert "key123" not in result

    def test_custom_sensitive_fields_masked(self):
        """Test that custom sensitive fields are masked."""
        model = CustomSensitiveModel(name="test", custom_secret="mysecret")
        result = repr(model)

        assert "name='test'" in result
        assert "custom_secret='***'" in result
        assert "mysecret" not in result

    def test_sensitive_field_none_value(self):
        """Test that None sensitive fields show None, not ***."""
        model = SensitiveFieldModel(username="john", password="secret", api_key=None)
        result = repr(model)

        assert "api_key=None" in result

    def test_explicit_repr_fields(self):
        """Test that only specified fields are included."""
        test_id = uuid4()
        model = ExplicitFieldsModel(
            id=test_id, name="test", description="desc", internal_data="internal"
        )
        result = repr(model)

        assert "id=" in result
        assert "name='test'" in result
        assert "description=" not in result
        assert "internal_data=" not in result

    def test_excluded_fields(self):
        """Test that excluded fields are not included."""
        test_id = uuid4()
        model = ExcludedFieldsModel(id=test_id, name="test", internal_data="internal")
        result = repr(model)

        assert "id=" in result
        assert "name='test'" in result
        assert "internal_data=" not in result


class TestSecureReprMixinTypeFormatting:
    """Test type-specific formatting in SecureReprMixin."""

    def test_uuid_formatting(self):
        """Test UUID values are formatted correctly."""
        test_id = uuid4()
        model = SimplePydanticModel(id=test_id, name="test", value=1)
        result = repr(model)

        assert f"'{test_id}'" in result

    def test_datetime_formatting(self):
        """Test datetime values use ISO format."""

        class DatetimeModel(SecureReprMixin, BaseModel):
            created: datetime

        dt = datetime(2024, 1, 15, 10, 30, 0)
        model = DatetimeModel(created=dt)
        result = repr(model)

        assert "2024-01-15T10:30:00" in result

    def test_none_value_formatting(self):
        """Test None values are formatted correctly."""

        class NullableModel(SecureReprMixin, BaseModel):
            value: str | None = None

        model = NullableModel()
        result = repr(model)

        assert "value=None" in result

    def test_bytes_short_formatting(self):
        """Test short bytes values are shown directly."""

        class BytesModel(SecureReprMixin, BaseModel):
            model_config = ConfigDict(arbitrary_types_allowed=True)
            data: bytes

        model = BytesModel(data=b"short")
        result = repr(model)

        assert "b'short'" in result

    def test_bytes_long_formatting(self):
        """Test long bytes values show byte count."""

        class BytesModel(SecureReprMixin, BaseModel):
            model_config = ConfigDict(arbitrary_types_allowed=True)
            data: bytes

        model = BytesModel(data=b"this is a longer byte string")
        result = repr(model)

        assert "<28 bytes>" in result

    def test_string_truncation(self):
        """Test long strings are truncated."""
        long_content = "x" * 100
        model = CustomMaxLengthModel(content=long_content)
        result = repr(model)

        assert "xxxxxxxxxx..." in result
        assert "x" * 100 not in result

    def test_string_no_truncation_when_short(self):
        """Test short strings are not truncated."""
        model = CustomMaxLengthModel(content="short")
        result = repr(model)

        assert "content='short'" in result
        assert "..." not in result

    def test_list_short_formatting(self):
        """Test short lists are shown directly."""

        class ListModel(SecureReprMixin, BaseModel):
            items: list[int]

        model = ListModel(items=[1, 2, 3])
        result = repr(model)

        assert "[1, 2, 3]" in result

    def test_list_long_formatting(self):
        """Test long lists show item count."""

        class ListModel(SecureReprMixin, BaseModel):
            items: list[int]

        model = ListModel(items=[1, 2, 3, 4, 5])
        result = repr(model)

        assert "<5 items>" in result

    def test_tuple_formatting(self):
        """Test tuples are formatted like lists."""

        class TupleModel(SecureReprMixin, BaseModel):
            items: tuple[int, ...]

        model = TupleModel(items=(1, 2, 3, 4, 5))
        result = repr(model)

        assert "<5 items>" in result

    def test_dict_short_formatting(self):
        """Test short dicts are shown directly."""

        class DictModel(SecureReprMixin, BaseModel):
            data: dict[str, int]

        model = DictModel(data={"a": 1, "b": 2})
        result = repr(model)

        assert "'a': 1" in result
        assert "'b': 2" in result

    def test_dict_long_formatting(self):
        """Test long dicts show key count."""

        class DictModel(SecureReprMixin, BaseModel):
            data: dict[str, int]

        model = DictModel(data={"a": 1, "b": 2, "c": 3, "d": 4})
        result = repr(model)

        assert "<4 keys>" in result


class TestSecureReprMixinClassTypes:
    """Test SecureReprMixin with different class types."""

    def test_dataclass_repr(self):
        """Test repr for dataclass."""
        test_id = uuid4()
        model = DataclassModel(id=test_id, name="test", password="secret")
        result = repr(model)

        assert "DataclassModel(" in result
        assert "name='test'" in result
        assert "password='***'" in result
        assert "secret" not in result

    def test_namedtuple_repr(self):
        """Test repr for NamedTuple."""
        test_id = uuid4()
        model = NamedTupleModel(id=test_id, name="test")
        result = repr(model)

        assert "NamedTupleModel(" in result
        assert "name='test'" in result

    def test_dict_based_model_repr(self):
        """Test repr for plain class using __dict__."""
        test_id = uuid4()
        model = DictBasedModel(id=test_id, name="test", password="secret")
        result = repr(model)

        assert "DictBasedModel(" in result
        assert "name='test'" in result
        assert "password='***'" in result
        # Private attributes should not appear
        assert "_private" not in result

    def test_empty_model_repr(self):
        """Test repr for model with no fields."""
        model = EmptyModel()
        result = repr(model)

        assert result == "EmptyModel()"

    def test_model_without_dict(self):
        """Test repr for model without __dict__ attribute."""

        class NoDictModel(SecureReprMixin):
            """Model using __slots__ without __dict__."""

            __slots__ = ()

        model = NoDictModel()
        result = repr(model)

        assert result == "NoDictModel()"


class TestSecureReprMixinEdgeCases:
    """Test edge cases for SecureReprMixin."""

    def test_all_default_sensitive_fields(self):
        """Test all default sensitive fields are masked."""

        # Create a model with all default sensitive field names
        class AllSensitiveModel(SecureReprMixin, BaseModel):
            password: str = "password_val"
            secret_key: str = "secretkey_val"
            access_token: str = "accesstoken_val"
            refresh_token: str = "refreshtoken_val"
            credential_id: str = "credentialid_val"
            public_key: str = "publickey_val"
            aaguid: str = "aaguid_val"
            db_password: str = "dbpassword_val"
            verification_token: str = "verificationtoken_val"
            token: str = "token_val"
            secret: str = "secret_val"
            api_key: str = "apikey_val"
            private_key: str = "privatekey_val"

        model = AllSensitiveModel()
        result = repr(model)

        # None of the actual values should appear
        for value in [
            "password_val",
            "secretkey_val",
            "accesstoken_val",
            "refreshtoken_val",
            "credentialid_val",
            "publickey_val",
            "aaguid_val",
            "dbpassword_val",
            "verificationtoken_val",
            "token_val",
            "secret_val",
            "apikey_val",
            "privatekey_val",
        ]:
            assert value not in result

        # All should be masked
        assert result.count("'***'") == 13

    def test_integer_and_float_values(self):
        """Test integer and float values are formatted correctly."""

        class NumericModel(SecureReprMixin, BaseModel):
            integer: int
            floating: float

        model = NumericModel(integer=42, floating=3.14)
        result = repr(model)

        assert "integer=42" in result
        assert "floating=3.14" in result

    def test_boolean_values(self):
        """Test boolean values are formatted correctly."""

        class BoolModel(SecureReprMixin, BaseModel):
            flag: bool

        model = BoolModel(flag=True)
        result = repr(model)

        assert "flag=True" in result

    def test_nested_model(self):
        """Test nested model values."""

        class Inner(BaseModel):
            value: int

        class Outer(SecureReprMixin, BaseModel):
            inner: Inner

        model = Outer(inner=Inner(value=42))
        result = repr(model)

        assert "inner=" in result

    def test_inaccessible_field_skipped(self):
        """Test that fields that raise exceptions are skipped."""

        class ProblematicModel(SecureReprMixin):
            _repr_fields = ["good", "bad"]

            def __init__(self):
                self.good = "value"

            @property
            def bad(self):
                raise RuntimeError("Cannot access")

        model = ProblematicModel()
        result = repr(model)

        assert "good='value'" in result
        assert "bad=" not in result


# =============================================================================
# ExceptionReprMixin Tests
# =============================================================================


class SampleExceptionReprMixin:
    """Test ExceptionReprMixin functionality."""

    def test_full_exception_repr(self):
        """Test exception with all fields."""
        test_id = uuid4()
        exc = SampleException(
            message="Test error", entity_type="user", entity_id=test_id
        )
        result = repr(exc)

        assert "SampleException(" in result
        assert "message='Test error'" in result
        assert "entity_type='user'" in result
        assert f"entity_id='{test_id}'" in result

    def test_exception_with_string_entity_id(self):
        """Test exception with string entity_id."""
        exc = SampleException(
            message="Test error", entity_type="user", entity_id="john"
        )
        result = repr(exc)

        assert "entity_id='john'" in result

    def test_exception_without_entity_type(self):
        """Test exception without entity_type."""
        exc = SampleException(message="Test error", entity_id="123")
        result = repr(exc)

        assert "message='Test error'" in result
        assert "entity_type=" not in result
        assert "entity_id='123'" in result

    def test_exception_without_entity_id(self):
        """Test exception without entity_id."""
        exc = SampleException(message="Test error", entity_type="user")
        result = repr(exc)

        assert "message='Test error'" in result
        assert "entity_type='user'" in result
        assert "entity_id=" not in result

    def test_minimal_exception(self):
        """Test exception with only message."""
        exc = MinimalException(message="Simple error")
        result = repr(exc)

        assert "MinimalException(message='Simple error')" == result

    def test_exception_without_message_attribute(self):
        """Test exception without message attribute."""
        exc = NoMessageException()
        result = repr(exc)

        assert result == "NoMessageException()"

    def test_long_message_truncation(self):
        """Test that long messages are truncated."""
        long_message = "x" * 150
        exc = SampleException(message=long_message)
        result = repr(exc)

        assert "x" * 100 + "..." in result
        assert "x" * 150 not in result

    def test_none_entity_type_not_shown(self):
        """Test that None entity_type is not shown."""
        exc = SampleException(message="Error", entity_type=None)
        result = repr(exc)

        assert "entity_type=" not in result

    def test_none_entity_id_not_shown(self):
        """Test that None entity_id is not shown."""
        exc = SampleException(message="Error", entity_id=None)
        result = repr(exc)

        assert "entity_id=" not in result


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests with actual application classes."""

    def test_with_real_exception(self):
        """Test with real domain exception."""
        from app.core.exceptions.domain_exceptions import UserNotFoundException

        exc = UserNotFoundException(username="testuser")
        result = repr(exc)

        assert "UserNotFoundException(" in result
        assert "message=" in result
        assert "entity_type='user'" in result

    def test_with_real_model(self):
        """Test with real database model."""
        from app.models import KOrganization

        org = KOrganization(
            name="Test Org",
            alias="testorg",
            created_by=uuid4(),
            last_modified_by=uuid4(),
        )
        result = repr(org)

        assert "KOrganization(" in result
        assert "name='Test Org'" in result
        assert "alias='testorg'" in result

    def test_with_sensitive_model(self):
        """Test with model containing sensitive fields."""
        from app.models import KPrincipalIdentity

        identity = KPrincipalIdentity(
            principal_id=uuid4(),
            password="hashed_password",
            created_by=uuid4(),
            last_modified_by=uuid4(),
        )
        result = repr(identity)

        assert "KPrincipalIdentity(" in result
        assert "password='***'" in result
        assert "hashed_password" not in result

    def test_with_fido2_credential(self):
        """Test FIDO2 credential masks binary sensitive fields."""
        from app.models import KFido2Credential

        cred = KFido2Credential(
            principal_id=uuid4(),
            credential_id=b"credential_bytes_here",
            public_key=b"public_key_bytes",
            aaguid=b"aaguid_bytes",
            created_by=uuid4(),
            last_modified_by=uuid4(),
        )
        result = repr(cred)

        assert "KFido2Credential(" in result
        # These should be masked
        assert "credential_id='***'" in result
        assert "public_key='***'" in result
        assert "aaguid='***'" in result

    def test_with_schema(self):
        """Test with Pydantic schema."""
        from app.schemas.user import UserCreate

        user = UserCreate(
            username="testuser",
            password="secret123",
            primary_email="test@example.com",
            first_name="Test",
            last_name="User",
            display_name="Test User",
        )
        result = repr(user)

        assert "UserCreate(" in result
        assert "username='testuser'" in result
        assert "password='***'" in result
        assert "secret123" not in result

    def test_with_token_schema(self):
        """Test Token schema masks tokens."""
        from app.schemas.user import Token

        token = Token(
            access_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            token_type="bearer",
            refresh_token="refresh_token_value",
        )
        result = repr(token)

        assert "Token(" in result
        assert "access_token='***'" in result
        assert "refresh_token='***'" in result
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result
