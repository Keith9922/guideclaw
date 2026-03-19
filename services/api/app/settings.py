from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_FILE = Path(__file__).resolve().parents[1] / ".env.local"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    guideclaw_env: str = "development"
    guideclaw_allowed_origins_raw: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        validation_alias="GUIDECLAW_ALLOWED_ORIGINS",
    )
    guideclaw_api_base_url: str = "http://127.0.0.1:8000"
    guideclaw_database_path: Path = Path(__file__).resolve().parents[3] / "data" / "guideclaw.db"
    guideclaw_upload_root: Path = Path(__file__).resolve().parents[3] / "data" / "uploads"
    guideclaw_openclaw_binary: str = "openclaw"
    guideclaw_openclaw_profile: str = "guideclaw"
    guideclaw_openclaw_agent: str = "main"

    bohrium_openapi_base_url: str = "https://openapi.dp.tech/openapi/v1"
    bohrium_access_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("BOHRIUM_ACCESS_KEY", "ACCESS_KEY"),
    )

    minimax_base_url: str = Field(
        default="https://api.minimaxi.com/v1",
        validation_alias=AliasChoices("MINIMAX_BASE_URL", "OPENROUTER_BASE_URL"),
    )
    minimax_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("MINIMAX_API_KEY", "OPENROUTER_API_KEY"),
    )
    minimax_model: str | None = Field(
        default="MiniMax-M2.7",
        validation_alias=AliasChoices("MINIMAX_MODEL", "OPENROUTER_MODEL"),
    )

    @property
    def guideclaw_allowed_origins(self) -> list[str]:
        return [item.strip() for item in self.guideclaw_allowed_origins_raw.split(",") if item.strip()]

    @property
    def minimax_ready(self) -> bool:
        return bool(self.minimax_api_key and self.minimax_model)

    @property
    def bohrium_ready(self) -> bool:
        return bool(self.bohrium_access_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
