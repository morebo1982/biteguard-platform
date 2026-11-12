from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        enable_decoding=False,
    )

    app_name: str = "BiteGuard Platform"
    app_env: Literal["development", "test", "staging", "production"] = "development"
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"

    auth_jwt_secret_key: str = ""
    auth_jwt_algorithm: str = "HS256"
    auth_access_token_minutes: int = 15
    auth_failed_attempts: int = 5
    auth_lockout_minutes: int = 15

    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )

    database_host: str | None = None
    database_port: int = 1433
    database_name: str | None = None
    database_user: str | None = None
    database_password: str | None = None
    database_driver: str = "ODBC Driver 18 for SQL Server"
    database_trust_server_certificate: bool = False
    database_windows_authentication: bool = False

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                return value
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def validate_production_database_tls(self):
        if self.app_env == "production" and len(self.auth_jwt_secret_key) < 32:
            raise ValueError("AUTH_JWT_SECRET_KEY must contain at least 32 characters in production.")
        if self.auth_jwt_algorithm != "HS256":
            raise ValueError("Only HS256 is currently supported for JWT signing.")
        if self.auth_access_token_minutes < 1 or self.auth_access_token_minutes > 60:
            raise ValueError("AUTH_ACCESS_TOKEN_MINUTES must be between 1 and 60.")
        if self.app_env == "production" and self.database_trust_server_certificate:
            raise ValueError("DATABASE_TRUST_SERVER_CERTIFICATE must be false in production.")
        return self

    @property
    def database_is_configured(self) -> bool:
        if not self.database_host or not self.database_name:
            return False

        if self.database_windows_authentication:
            return True

        return bool(self.database_user and self.database_password)


@lru_cache
def get_settings() -> Settings:
    return Settings()
