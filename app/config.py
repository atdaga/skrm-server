from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = Field(default="Python Server", description="Application name")
    debug: bool = Field(default=False, description="Debug mode")
    host: str = Field(default="0.0.0.0", description="Host to bind to")
    port: int = Field(default=8000, description="Port to bind to")
    log_level: str = Field(default="DEBUG", description="Logging level")

    # Database configuration
    db_host: str = Field(default="127.0.0.1", description="Database host")
    db_port: int = Field(default=5432, description="Database port")
    db_name: str = Field(default="skrm_local", description="Database name")
    db_user: str = Field(default="skrm_user", description="Database user")
    db_password: str = Field(default="P@ssword12", description="Database password")

    # Security configuration
    secret_key: str = Field(default="fccd6f72cca5af6c24e6fbff3c106f0f27a6e0d77f56ac505416f894da6a5cbf", description="Secret key for JWT tokens")
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, description="Access token expiration in minutes")
    refresh_token_expire_days: int = Field(default=7, description="Refresh token expiration in days")
    
    @property
    def database_url(self) -> str:
        """Construct the PostgreSQL database URL."""
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


settings = Settings()
