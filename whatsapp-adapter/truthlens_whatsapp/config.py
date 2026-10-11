import os
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    bot_env: str = "test"
    response_mode: str = "development"
    meta_outbound_enabled: bool = False
    backend_enabled: bool = False
    provider_credentials_rotated: bool = False
    provider_key_revocation_waived: bool = False
    messaging_provider: str = "meta"
    twilio_outbound_enabled: bool = False
    twilio_account_sid: str = ""
    twilio_auth_token: SecretStr = SecretStr("")
    twilio_whatsapp_number: str = ""
    twilio_public_base_url: str = ""
    whatsapp_access_token: SecretStr = SecretStr("")
    whatsapp_phone_number_id: str = ""
    whatsapp_waba_id: str = ""
    whatsapp_verify_token: SecretStr = SecretStr("")
    meta_app_secret: SecretStr = SecretStr("")
    graph_api_version: str = ""
    truthlens_backend_url: str = "http://127.0.0.1:8000"
    truthlens_backend_token: SecretStr = SecretStr("")
    database_url: SecretStr = SecretStr("sqlite:///state/bot.sqlite3")
    state_encryption_key: SecretStr = SecretStr("")
    identity_hash_secret: SecretStr = SecretStr("")
    support_url: str = ""
    max_media_bytes: int = Field(default=10485760, ge=1024, le=10485760)
    max_webhook_bytes: int = Field(default=262144, ge=1024, le=1048576)
    max_queue_jobs: int = Field(default=1000, ge=1, le=10000)
    per_sender_per_minute: int = Field(default=10, ge=1, le=60)
    backend_timeout_seconds: int = Field(default=180, ge=1, le=300)
    job_lease_seconds: int = Field(default=1800, ge=900, le=3600)
    content_retention_hours: int = Field(default=24, ge=1, le=24)
    dedup_retention_days: int = Field(default=8, ge=8, le=30)

    @model_validator(mode="after")
    def validate_settings(self):
        import re

        if self.bot_env not in {"test", "production"} or self.response_mode not in {
            "development",
            "backend",
        }:
            raise ValueError("Unsupported environment or response mode")
        if self.messaging_provider not in {"meta", "twilio"}:
            raise ValueError("Unsupported messaging provider")
        if self.messaging_provider == "meta":
            if (
                not self.meta_app_secret.get_secret_value()
                or not self.whatsapp_verify_token.get_secret_value()
            ):
                raise ValueError("Configure webhook secrets privately")
            if not self.whatsapp_phone_number_id or not self.whatsapp_waba_id:
                raise ValueError("Configure the intended phone and WABA IDs")
            if self.twilio_outbound_enabled:
                raise ValueError("Twilio sending cannot be enabled on a Meta instance")
        else:
            if self.bot_env != "test":
                raise ValueError("Twilio connector is for local Sandbox testing only")
            if self.meta_outbound_enabled:
                raise ValueError("Meta sending cannot be enabled on a Twilio instance")
            if not re.fullmatch(r"AC[0-9a-fA-F]{32}", self.twilio_account_sid):
                raise ValueError("Configure the Twilio Account SID")
            if not self.twilio_auth_token.get_secret_value():
                raise ValueError("Configure the Twilio primary Auth Token privately")
            if not re.fullmatch(r"whatsapp:\+[1-9][0-9]{5,14}", self.twilio_whatsapp_number):
                raise ValueError("Configure the actual Twilio WhatsApp sender")
            public = urlsplit(self.twilio_public_base_url)
            if (
                public.scheme != "https"
                or not public.hostname
                or public.username
                or public.password
                or public.port not in {None, 443}
                or public.path not in {"", "/"}
                or public.query
                or public.fragment
            ):
                raise ValueError("Configure the exact HTTPS tunnel origin without a path")
            self.twilio_public_base_url = self.twilio_public_base_url.rstrip("/")
        if len(self.identity_hash_secret.get_secret_value()) < 32:
            raise ValueError("Configure a stable identity hashing secret of at least 32 characters")
        if not self.state_encryption_key.get_secret_value():
            raise ValueError("Configure a Fernet state encryption key")
        if self.meta_outbound_enabled and (
            not self.whatsapp_access_token.get_secret_value()
            or not re.fullmatch(r"v\d+\.\d+", self.graph_api_version)
        ):
            raise ValueError("Sending needs an access token and confirmed Graph version")
        url = urlsplit(self.truthlens_backend_url)
        if (
            url.scheme not in {"http", "https"}
            or not url.hostname
            or url.username
            or url.password
            or url.query
            or url.fragment
        ):
            raise ValueError("Configure a fixed backend origin without credentials")
        if self.response_mode == "backend" and not (
            self.backend_enabled and self.provider_credentials_authorized
        ):
            raise ValueError(
                "Backend mode requires provider approval and confirmed key rotation "
                "or an explicit test-only revocation waiver"
            )
        if self.bot_env == "production":
            if not self.database_url.get_secret_value().startswith("postgresql://"):
                raise ValueError("Production needs durable PostgreSQL storage")
            if self.response_mode != "backend" or not self.support_url.startswith("https://"):
                raise ValueError("Production needs backend mode and a real support URL")
        return self

    @property
    def provider_credentials_authorized(self):
        return self.provider_credentials_rotated or (
            self.bot_env == "test" and self.provider_key_revocation_waived
        )

    @property
    def outbound_enabled(self):
        return (
            self.twilio_outbound_enabled
            if self.messaging_provider == "twilio"
            else self.meta_outbound_enabled
        )

    def sqlite_path(self):
        path = Path(self.database_url.get_secret_value().removeprefix("sqlite:///"))
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


def load_settings():
    return Settings(_env_file=os.environ.get("TRUTHLENS_ENV_FILE", ".env"))
