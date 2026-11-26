from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    groq_api_key: SecretStr
    groq_model: str = "openai/gpt-oss-120b"
    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173"
    )
    groq_timeout_seconds: float = 25.0

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("groq_api_key")
    @classmethod
    def reject_empty_api_key(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().strip():
            raise ValueError("GROQ_API_KEY must not be empty.")
        return value

    @field_validator("groq_model")
    @classmethod
    def reject_empty_model(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("GROQ_MODEL must not be empty.")
        return value.strip()

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
