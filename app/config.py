from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.repr_mixin import SecureReprMixin


class Settings(SecureReprMixin, BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Sensitive fields to mask in repr
    _sensitive_fields = {"secret_key", "db_password"}

    app_name: str = Field(default="sKrm Server", description="Application name")
    debug: bool = Field(
        default=False,
        description="Debug mode (enables FastAPI debug mode, auto-reload, and SQL query logging)",
    )
    host: str = Field(default="0.0.0.0", description="Host to bind to")
    port: int = Field(default=8000, description="Port to bind to")
    log_level: str = Field(
        default="DEBUG",
        description="Logging level. Valid values: DEBUG, INFO, WARNING, ERROR, CRITICAL (case-insensitive)",
    )
    log_format: Literal["console", "json"] = Field(
        default="json",
        description="Log output format. Valid values: 'console' (human-readable with colors) or 'json' (structured JSON)",
    )

    # Database configuration
    db_host: str = Field(default="127.0.0.1", description="Database host")
    db_port: int = Field(default=5432, description="Database port")
    db_name: str = Field(default="skrm_local", description="Database name")
    db_user: str = Field(default="skrm_user", description="Database user")
    db_password: str = Field(default="P@ssword12", description="Database password")

    # Security configuration
    secret_key: str = Field(
        default="fccd6f72cca5af6c24e6fbff3c106f0f27a6e0d77f56ac505416f894da6a5cbf",
        description="Secret key for JWT tokens",
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(
        default=30, description="Access token expiration in minutes"
    )
    refresh_token_expire_days: int = Field(
        default=7, description="Refresh token expiration in days"
    )
    refresh_token_absolute_expire_months: int = Field(
        default=1,
        description="Absolute refresh token expiration in months from session start",
    )
    cookie_secure: bool = Field(
        default=True,
        description="Set Secure flag on cookies (True for HTTPS, False for HTTP in development). Auto-set to False when debug=True",
    )

    # FIDO2/WebAuthn configuration
    rp_id: str = Field(
        default="localhost", description="Relying Party ID (domain name)"
    )
    rp_name: str = Field(default="sKrm Server", description="Relying Party name")
    rp_origin: str = Field(
        default="http://localhost:8000",
        description="Relying Party origin URL (must match browser origin)",
    )
    fido2_timeout: int = Field(
        default=60000, description="FIDO2 operation timeout in milliseconds"
    )
    fido2_require_resident_key: bool = Field(
        default=False,
        description="Require resident key (discoverable credential) for registration",
    )

    # CORS configuration
    cors_origins: list[str] = Field(
        default=["http://localhost:3000"],
        description="Allowed CORS origins (comma-separated string in env)",
    )
    cors_allow_credentials: bool = Field(
        default=True,
        description="Allow credentials (cookies, authorization headers) in CORS requests",
    )
    cors_allow_methods: list[str] = Field(
        default=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        description="Allowed HTTP methods for CORS requests",
    )
    cors_allow_headers: list[str] = Field(
        default=["*"], description="Allowed headers for CORS requests"
    )
    cors_max_age: int = Field(
        default=600, description="Maximum age (in seconds) for CORS preflight cache"
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Parse comma-separated origins string into list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("cors_allow_methods", mode="before")
    @classmethod
    def parse_cors_methods(cls, v: str | list[str]) -> list[str]:
        """Parse comma-separated methods string into list."""
        if isinstance(v, str):
            return [method.strip().upper() for method in v.split(",") if method.strip()]
        return v

    @field_validator("cors_allow_headers", mode="before")
    @classmethod
    def parse_cors_headers(cls, v: str | list[str]) -> list[str]:
        """Parse comma-separated headers string into list."""
        if isinstance(v, str):
            return [header.strip() for header in v.split(",") if header.strip()]
        return v

    @model_validator(mode="before")
    @classmethod
    def filter_alembic_fields(cls, data: dict) -> dict:
        """Remove alembic-specific fields from environment variables.

        Alembic fields are only used by migration tooling and should be ignored by the app.
        """
        return {k: v for k, v in data.items() if not k.startswith("alembic_")}

    @model_validator(mode="after")
    def set_cookie_secure_from_debug(self) -> Settings:
        """Auto-set cookie_secure to False when in debug mode (for HTTP development)."""
        if self.debug and self.cookie_secure:
            # In debug mode, allow HTTP cookies for local development
            self.cookie_secure = False
        return self

    @property
    def database_url(self) -> str:
        """Construct the PostgreSQL database URL."""
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


settings = Settings()
