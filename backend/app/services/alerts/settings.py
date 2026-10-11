from pathlib import Path

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AlertsSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ALERTS_", env_file=Path(__file__).resolve().parents[3] / ".env", extra="ignore"
    )
    ingest_token: SecretStr = SecretStr("")
    admin_token: SecretStr = SecretStr("")
    pseudonym_secret: SecretStr = SecretStr("")
    min_independent_submissions: int = Field(default=3, ge=2, le=100)
    trend_window_hours: int = Field(default=24, ge=1, le=168)
    baseline_days: int = Field(default=7, ge=1, le=30)
    growth_ratio: float = Field(default=2, ge=1.1, le=20)
    evidence_max_age_hours: int = Field(default=48, ge=1, le=168)
    draft_ttl_hours: int = Field(default=12, ge=1, le=48)
    retention_days: int = Field(default=14, ge=2, le=90)
    purge_interval_seconds: int = Field(default=60, ge=1, le=3600)
    max_observations: int = Field(default=5000, ge=10, le=50000)
    max_clusters: int = Field(default=1000, ge=10, le=10000)
    max_drafts: int = Field(default=2000, ge=10, le=10000)
    embedding_similarity: float = Field(default=0.93, ge=0.85, le=1)

    @model_validator(mode="after")
    def validate_configuration(self):
        secrets = [
            s.get_secret_value()
            for s in (self.ingest_token, self.admin_token, self.pseudonym_secret)
        ]
        if any(secrets) and (any(len(s) < 32 for s in secrets) or len(set(secrets)) != 3):
            raise ValueError("Configure three distinct alerts secrets of at least 32 characters.")
        if self.retention_days < self.baseline_days + self.trend_window_hours / 24:
            raise ValueError("Retention must cover the baseline and observation window.")
        return self

    @property
    def configured(self) -> bool:
        return bool(
            self.ingest_token.get_secret_value()
            and self.admin_token.get_secret_value()
            and self.pseudonym_secret.get_secret_value()
        )
