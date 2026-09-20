import os
from pydantic import AliasChoices, Field, model_validator
from typing import Optional
from pydantic_settings import BaseSettings
from sqlalchemy.engine.url import make_url, URL

DEFAULT_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/identies"
DEFAULT_TEST_DATABASE_URL = (
    "postgresql://postgres:postgres@localhost:5432/identies_test"
)

SERVICE_NAME = "identies-api"


class Settings(BaseSettings):
    app_name: str = SERVICE_NAME
    otel_enabled: bool = Field(default=False, json_schema_extra={"env": "OTEL_ENABLED"})
    database_url: Optional[str] = None  # Will be set dynamically
    environment: str = Field(
        default="development",
        validation_alias=AliasChoices("ENV", "ENVIRONMENT"),
    )
    log_level: str = Field(default="INFO", json_schema_extra={"env": "LOG_LEVEL"})
    disable_auth: bool = Field(default=False, json_schema_extra={"env": "DISABLE_AUTH"})
    rollbar_access_token: Optional[str] = Field(
        default=None, json_schema_extra={"env": "ROLLBAR_ACCESS_TOKEN"}
    )  # Optional field
    super_user_email: Optional[str] = Field(
        default=None, json_schema_extra={"env": "SUPER_USER_EMAIL"}
    )  # Optional field for super user setup
    vaulta_api_url: str = Field(
        default="http://localhost:8000", json_schema_extra={"env": "VAULTA_API_URL"}
    )
    vaulta_client_id: str = Field(
        default="", json_schema_extra={"env": "VAULTA_CLIENT_ID"}
    )
    vaulta_client_secret: str = Field(
        default="", json_schema_extra={"env": "VAULTA_CLIENT_SECRET"}
    )

    oidc_domain: str = "test.oidc.com"
    oidc_api_audience: str = "https://test-api"
    oidc_issuer: str = "https://test.oidc.com/"
    oidc_algorithms: str = "RS256"
    oidc_jwks_urls: Optional[str] = Field(
        default=None, json_schema_extra={"env": "OIDC_JWKS_URLS"}
    )
    oidc_userinfo_timeout: float = Field(
        default=5.0, json_schema_extra={"env": "OIDC_USERINFO_TIMEOUT"}
    )

    token_exchange_private_key_pem: Optional[str] = Field(
        default=None,
        json_schema_extra={"env": "TOKEN_EXCHANGE_PRIVATE_KEY_PEM"},
    )
    token_exchange_public_key_pem: Optional[str] = Field(
        default=None,
        json_schema_extra={"env": "TOKEN_EXCHANGE_PUBLIC_KEY_PEM"},
    )
    token_exchange_key_id: Optional[str] = Field(
        default=None,
        json_schema_extra={"env": "TOKEN_EXCHANGE_KEY_ID"},
    )
    token_exchange_issuer: str = Field(
        default="https://identies.tessera.com/",
        json_schema_extra={"env": "TOKEN_EXCHANGE_ISSUER"},
    )
    token_exchange_audience: str = Field(
        default="https://identies.tessera.com/",
        json_schema_extra={"env": "TOKEN_EXCHANGE_AUDIENCE"},
    )
    token_exchange_ttl_seconds: int = Field(
        default=600,
        json_schema_extra={"env": "TOKEN_EXCHANGE_TTL_SECONDS"},
    )
    token_exchange_required_scope: Optional[str] = Field(
        default=None,
        json_schema_extra={"env": "TOKEN_EXCHANGE_REQUIRED_SCOPE"},
    )

    # Service account detection (Auth0 M2M custom claims)
    service_account_account_type_claim: str = Field(
        default="https://mylinden.family/account_type",
        json_schema_extra={"env": "SERVICE_ACCOUNT_ACCOUNT_TYPE_CLAIM"},
    )
    service_account_account_type_value: str = Field(
        default="service_account",
        json_schema_extra={"env": "SERVICE_ACCOUNT_ACCOUNT_TYPE_VALUE"},
    )
    service_account_client_id_claim: str = Field(
        default="https://mylinden.family/client_id",
        json_schema_extra={"env": "SERVICE_ACCOUNT_CLIENT_ID_CLAIM"},
    )
    service_account_client_name_claim: str = Field(
        default="https://mylinden.family/client_name",
        json_schema_extra={"env": "SERVICE_ACCOUNT_CLIENT_NAME_CLAIM"},
    )

    allowed_service_account_client_ids: Optional[str] = Field(
        default=None, json_schema_extra={"env": "ALLOWED_SERVICE_ACCOUNT_CLIENT_IDS"}
    )

    # Agents (users with kind=agent, created by a trusted service on behalf of a human)
    agent_email_domain: str = Field(
        default="agents.example",
        json_schema_extra={"env": "AGENT_EMAIL_DOMAIN"},
    )
    """Domain for the synthetic email given to agents. It must pass email validation
    but must never deliver: the reserved .example TLD does both. (.invalid, .test and
    .localhost are rejected by the email validator.)"""
    agent_claim_ttl_minutes: int = Field(
        default=15, json_schema_extra={"env": "AGENT_CLAIM_TTL_MINUTES"}
    )
    agent_claim_max_failed_attempts: int = Field(
        default=5, json_schema_extra={"env": "AGENT_CLAIM_MAX_FAILED_ATTEMPTS"}
    )
    agent_client_secret_ttl_days: int = Field(
        default=30, json_schema_extra={"env": "AGENT_CLIENT_SECRET_TTL_DAYS"}
    )

    otel_exporter_otlp_endpoint: str = "http://localhost:4318"
    otel_service_name: str = SERVICE_NAME.lower()
    redis_host: str = Field(
        default="localhost", json_schema_extra={"env": "REDIS_HOST"}
    )
    redis_port: int = Field(default=6379, json_schema_extra={"env": "REDIS_PORT"})
    redis_namespace: str = Field(
        default="llama_index", json_schema_extra={"env": "REDIS_NAMESPACE"}
    )
    invite_only_access: bool = Field(
        default=False, json_schema_extra={"env": "INVITE_ONLY_ACCESS"}
    )
    port: int = Field(default=8000, json_schema_extra={"env": "PORT"})
    database_pool_size: int = Field(
        default=10, json_schema_extra={"env": "DATABASE_POOL_SIZE"}
    )
    database_max_overflow: int = Field(
        default=5, json_schema_extra={"env": "DATABASE_MAX_OVERFLOW"}
    )
    db_app_name: str = Field(
        default="identies-api", json_schema_extra={"env": "DB_APP_NAME"}
    )

    def get_allowed_service_account_client_ids(self) -> list[str]:
        """
        Parse allowed_service_account_client_ids as a comma-separated string from env.
        """
        env_val = self.allowed_service_account_client_ids
        if env_val:
            return [v.strip() for v in env_val.split(",") if v.strip()]
        return []

    def get_token_exchange_audiences(self) -> list[str]:
        """
        Parse token_exchange_audience as a comma-separated string from env.
        """
        env_val = self.token_exchange_audience
        if env_val:
            return [v.strip() for v in env_val.split(",") if v.strip()]
        return []

    def get_oidc_jwks_urls(self) -> list[str]:
        """
        Parse OIDC_JWKS_URLS as a comma-separated string from env, fallback to oidc_domain.
        """
        if self.oidc_jwks_urls:
            return [v.strip() for v in self.oidc_jwks_urls.split(",") if v.strip()]
        if self.oidc_domain:
            return [f"https://{self.oidc_domain}/.well-known/jwks.json"]
        return []

    @model_validator(mode="before")
    def set_database_url(cls, values):
        """Set the database_url dynamically based on the environment field."""
        environment = values.get("environment", os.getenv("ENV", "development"))
        if environment.lower() == "test":
            values["database_url"] = os.getenv(
                "TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL
            )
        else:
            values["database_url"] = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)

        return values

    @property
    def is_production(self) -> bool:
        """Check if the current environment is production."""
        return self.environment.lower() == "production"

    @property
    def is_test(self) -> bool:
        """Check if the current environment is test."""
        return self.environment.lower() == "test"

    @property
    def database_url_obj(self) -> URL:
        """Return the database URL as a URL object using sqlalchemy's make_url."""
        if not self.database_url:
            raise ValueError("Database URL is not set.")
        return make_url(self.database_url)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "allow"  # Allow extra environment variables


def get_settings() -> Settings:
    """Get application settings with required environment variables."""
    return Settings()
