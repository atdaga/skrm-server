"""Tests for application configuration (app/config.py)."""

from app.config import Settings


class TestSettingsValidators:
    """Test Settings field validators for CORS configuration."""

    def test_parse_cors_origins_from_string(self):
        """Test parsing comma-separated CORS origins from string."""
        settings = Settings(cors_origins="http://localhost:3000,http://localhost:5173")
        assert settings.cors_origins == [
            "http://localhost:3000",
            "http://localhost:5173",
        ]

    def test_parse_cors_origins_from_string_with_spaces(self):
        """Test parsing CORS origins handles extra spaces."""
        settings = Settings(
            cors_origins="http://localhost:3000 , http://example.com , http://app.com"
        )
        assert settings.cors_origins == [
            "http://localhost:3000",
            "http://example.com",
            "http://app.com",
        ]

    def test_parse_cors_origins_from_string_single_origin(self):
        """Test parsing single CORS origin from string."""
        settings = Settings(cors_origins="http://localhost:3000")
        assert settings.cors_origins == ["http://localhost:3000"]

    def test_parse_cors_origins_from_list(self):
        """Test CORS origins validator passes through list unchanged."""
        origins_list = ["http://localhost:3000", "http://example.com"]
        settings = Settings(cors_origins=origins_list)
        assert settings.cors_origins == origins_list

    def test_parse_cors_origins_filters_empty_strings(self):
        """Test parsing CORS origins filters out empty strings."""
        settings = Settings(cors_origins="http://localhost:3000,,http://example.com,")
        assert settings.cors_origins == [
            "http://localhost:3000",
            "http://example.com",
        ]

    def test_parse_cors_methods_from_string(self):
        """Test parsing comma-separated HTTP methods from string."""
        settings = Settings(cors_allow_methods="get,post,put,delete")
        assert settings.cors_allow_methods == ["GET", "POST", "PUT", "DELETE"]

    def test_parse_cors_methods_from_string_with_spaces(self):
        """Test parsing HTTP methods handles extra spaces."""
        settings = Settings(cors_allow_methods="get , post , put")
        assert settings.cors_allow_methods == ["GET", "POST", "PUT"]

    def test_parse_cors_methods_from_string_mixed_case(self):
        """Test parsing HTTP methods normalizes to uppercase."""
        settings = Settings(cors_allow_methods="Get,POST,pUt,PaTcH")
        assert settings.cors_allow_methods == ["GET", "POST", "PUT", "PATCH"]

    def test_parse_cors_methods_from_list(self):
        """Test HTTP methods validator passes through list unchanged."""
        methods_list = ["GET", "POST", "PUT"]
        settings = Settings(cors_allow_methods=methods_list)
        assert settings.cors_allow_methods == methods_list

    def test_parse_cors_methods_filters_empty_strings(self):
        """Test parsing HTTP methods filters out empty strings."""
        settings = Settings(cors_allow_methods="GET,,POST,")
        assert settings.cors_allow_methods == ["GET", "POST"]

    def test_parse_cors_headers_from_string(self):
        """Test parsing comma-separated headers from string."""
        settings = Settings(cors_allow_headers="Content-Type,Authorization,X-Custom")
        assert settings.cors_allow_headers == [
            "Content-Type",
            "Authorization",
            "X-Custom",
        ]

    def test_parse_cors_headers_from_string_with_spaces(self):
        """Test parsing headers handles extra spaces."""
        settings = Settings(
            cors_allow_headers="Content-Type , Authorization , X-Api-Key"
        )
        assert settings.cors_allow_headers == [
            "Content-Type",
            "Authorization",
            "X-Api-Key",
        ]

    def test_parse_cors_headers_from_string_wildcard(self):
        """Test parsing headers with wildcard."""
        settings = Settings(cors_allow_headers="*")
        assert settings.cors_allow_headers == ["*"]

    def test_parse_cors_headers_from_list(self):
        """Test headers validator passes through list unchanged."""
        headers_list = ["Content-Type", "Authorization"]
        settings = Settings(cors_allow_headers=headers_list)
        assert settings.cors_allow_headers == headers_list

    def test_parse_cors_headers_filters_empty_strings(self):
        """Test parsing headers filters out empty strings."""
        settings = Settings(cors_allow_headers="Content-Type,,Authorization,")
        assert settings.cors_allow_headers == ["Content-Type", "Authorization"]


class TestSettingsProperties:
    """Test Settings computed properties."""

    def test_database_url_property(self):
        """Test database_url property constructs correct PostgreSQL URL."""
        settings = Settings(
            db_user="testuser",
            db_password="testpass",
            db_host="testhost",
            db_port=5433,
            db_name="testdb",
        )
        expected_url = "postgresql+asyncpg://testuser:testpass@testhost:5433/testdb"
        assert settings.database_url == expected_url

    def test_database_url_property_with_defaults(self):
        """Test database_url property with default values."""
        settings = Settings()
        expected_url = (
            "postgresql+asyncpg://skrm_user:P@ssword12@127.0.0.1:5432/skrm_local"
        )
        assert settings.database_url == expected_url


class TestSettingsDefaults:
    """Test Settings default values."""

    def test_default_cors_settings(self):
        """Test default CORS configuration values."""
        settings = Settings()
        assert settings.cors_origins == ["http://localhost:3000"]
        assert settings.cors_allow_credentials is True
        assert settings.cors_allow_methods == [
            "GET",
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
            "OPTIONS",
        ]
        assert settings.cors_allow_headers == ["*"]
        assert settings.cors_max_age == 600

    def test_default_app_settings(self):
        """Test default application configuration values."""
        settings = Settings()
        assert settings.app_name == "sKrm Server"
        assert settings.debug is False
        assert settings.host == "0.0.0.0"
        assert settings.port == 8000
        assert settings.log_level == "DEBUG"

    def test_default_database_settings(self):
        """Test default database configuration values."""
        settings = Settings()
        assert settings.db_host == "127.0.0.1"
        assert settings.db_port == 5432
        assert settings.db_name == "skrm_local"
        assert settings.db_user == "skrm_user"
        assert settings.db_password == "P@ssword12"

    def test_default_security_settings(self):
        """Test default security configuration values."""
        settings = Settings()
        assert settings.algorithm == "HS256"
        assert settings.access_token_expire_minutes == 30
        assert settings.refresh_token_expire_days == 7
        assert settings.refresh_token_absolute_expire_months == 1

    def test_default_fido2_settings(self):
        """Test default FIDO2/WebAuthn configuration values."""
        settings = Settings()
        assert settings.rp_id == "localhost"
        assert settings.rp_name == "sKrm Server"
        assert settings.rp_origin == "http://localhost:8000"
        assert settings.fido2_timeout == 60000
        assert settings.fido2_require_resident_key is False


class TestSettingsModelValidator:
    """Test Settings model validators."""

    def test_cookie_secure_auto_set_to_false_when_debug_true(self):
        """Test that cookie_secure is automatically set to False when debug=True."""
        # When debug=True and cookie_secure=True (default), it should be set to False
        settings = Settings(debug=True, cookie_secure=True)
        assert settings.debug is True
        assert settings.cookie_secure is False

    def test_cookie_secure_not_changed_when_debug_false(self):
        """Test that cookie_secure is not changed when debug=False."""
        settings = Settings(debug=False, cookie_secure=True)
        assert settings.debug is False
        assert settings.cookie_secure is True

    def test_cookie_secure_not_changed_when_already_false(self):
        """Test that cookie_secure is not changed when already False."""
        settings = Settings(debug=True, cookie_secure=False)
        assert settings.debug is True
        assert settings.cookie_secure is False
