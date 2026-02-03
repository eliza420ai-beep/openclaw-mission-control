from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "dev"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/openclaw_agency"
    redis_url: str = "redis://localhost:6379/0"

    # Clerk auth (auth only; roles stored in DB)
    clerk_jwks_url: str = ""
    clerk_verify_iat: bool = True
    clerk_leeway: float = 10.0

    # OpenClaw Gateway
    openclaw_gateway_url: str = ""
    openclaw_gateway_token: str = ""
    openclaw_main_session_key: str = "agent:main:main"
    openclaw_workspace_root: str = "~/.openclaw/workspaces"

    cors_origins: str = ""
    base_url: str = ""

    # Database lifecycle
    db_auto_migrate: bool = False


settings = Settings()
