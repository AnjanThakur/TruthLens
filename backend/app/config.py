from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        env_file_encoding="utf-8-sig",
        extra="ignore",
    )
    gemini_api_key: SecretStr = SecretStr("")
    tavily_api_key: SecretStr = SecretStr("")
    gemini_model: str = "gemini-3.8-flash"
    gemini_audio_model: str = ""
    provider_max_attempts: int = Field(default=2, ge=1, le=3)
    provider_max_retry_wait_seconds: float = Field(default=3, ge=0, le=30)
    verification_cache_ttl_seconds: int = Field(default=120, ge=0, le=300)
    verification_cache_entries: int = Field(default=32, ge=1, le=128)
    document_chunk_chars: int = Field(default=6000, ge=100, le=12000)
    max_document_chunks: int = Field(default=8, ge=1, le=32)
    source_excerpt_chars: int = Field(default=3000, ge=900, le=5000)
    llm_timeout_seconds: float | None = Field(default=None, ge=1, le=120)
    url_timeout_seconds: float | None = Field(default=None, ge=1, le=60)
    max_prompt_chars: int = Field(default=65000, ge=1000, le=100000)
    search_depth: str = Field(default="basic", pattern=r"^(basic|advanced)$")
    max_search_queries_per_claim: int = Field(default=4, ge=1, le=4)
    max_search_attempts_per_check: int = Field(default=8, ge=1, le=24)
    max_llm_attempts_per_check: int = Field(default=12, ge=1, le=32)
    search_cache_ttl_seconds: int = Field(default=900, ge=0, le=3600)
    search_cache_entries: int = Field(default=128, ge=1, le=512)
    max_audio_seconds: int = Field(default=300, ge=1, le=600)
    cors_origins: str = "http://localhost:3000,http://localhost:5173"
    external_timeout_seconds: float = Field(default=20, ge=1, le=60)
    request_timeout_seconds: float = Field(default=180, ge=5, le=300)
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, ge=1024, le=25 * 1024 * 1024)
    max_url_bytes: int = Field(default=2 * 1024 * 1024, ge=1024, le=5 * 1024 * 1024)
    max_text_chars: int = Field(default=24000, ge=100, le=50000)
    max_pdf_pages: int = Field(default=8, ge=1, le=20)
    max_claims: int = Field(default=8, ge=1, le=12)
    max_evidence: int = Field(default=6, ge=1, le=10)
    verify_concurrency: int = Field(default=2, ge=1, le=4)
    tesseract_cmd: str = ""
    tessdata_dir: str = ""
    ffmpeg_cmd: str = ""
    ffprobe_cmd: str = ""
    ocr_languages: str = "eng+hin+mar"

    @field_validator("cors_origins")
    @classmethod
    def require_allowlist(cls, value: str) -> str:
        if "*" in value:
            raise ValueError("CORS_ORIGINS must be an explicit allow-list, not a wildcard.")
        return value

    @property
    def origins(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]
