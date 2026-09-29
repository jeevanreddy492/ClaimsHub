"""Application settings.

All settings come from environment variables (or a local .env file).
Nothing secret is ever hard-coded here.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="CLAIMSHUB_", extra="ignore")

    app_name: str = "ClaimsHub"
    environment: str = Field(default="local", description="local | test | prod")
    log_level: str = "INFO"

    # Full SQLAlchemy URL. Examples:
    #   oracle+oracledb://claimshub:pw@localhost:1521/?service_name=FREEPDB1
    #   sqlite+pysqlite:///:memory:   (unit/API tests only)
    database_url: str = (
        "oracle+oracledb://claimshub:claimshub@localhost:1521/?service_name=FREEPDB1"
    )
    # Optional full Oracle connect string (for example the Autonomous Database TLS
    # string from the OCI console). When set, it is used instead of host/port in the URL:
    #   CLAIMSHUB_DATABASE_URL=oracle+oracledb://CLAIMSHUB:<password>@
    #   CLAIMSHUB_DATABASE_DSN=(description=(retry_count=20)...(security=(ssl_server_dn_match=yes)))
    database_dsn: str | None = None
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout_seconds: int = 30
    db_echo: bool = False

    jwt_secret: str = Field(default="change-me-in-env", min_length=16)
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    cors_origins: list[str] = ["http://localhost:5173"]

    @property
    def is_oracle(self) -> bool:
        return self.database_url.startswith("oracle")


@lru_cache
def get_settings() -> Settings:
    return Settings()
