"""Application settings, loaded from environment variables (never hardcoded)."""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    database_url: str = "postgresql+psycopg://localhost/patient_registration"

    # Admin credential for the REST API and the dashboard login.
    api_key: str = "dev-api-key-change-me"
    # Signs dashboard session cookies.
    secret_key: str = "dev-secret-key-change-me"
    # Shared secret Vapi sends in the X-Vapi-Secret header on every webhook.
    vapi_webhook_secret: str = "dev-vapi-secret-change-me"

    # Comma-separated list of extra origins allowed by CORS (dashboard is same-origin).
    cors_origins: str = ""
    # When false (default), patient PII is masked in log output.
    log_pii: bool = False
    # IANA timezone used to tell the agent "today" (for date-of-birth reasoning).
    clinic_timezone: str = "America/New_York"

    @field_validator("database_url")
    @classmethod
    def _use_psycopg_driver(cls, value: str) -> str:
        # Railway/Heroku style URLs come as postgres:// or postgresql://.
        if value.startswith("postgres://"):
            value = "postgresql://" + value[len("postgres://"):]
        if value.startswith("postgresql://"):
            value = "postgresql+psycopg://" + value[len("postgresql://"):]
        return value

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
