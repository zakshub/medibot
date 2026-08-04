from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="Medibot", min_length=1, max_length=100)
    app_version: str = Field(default="0.1.0", pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")
    environment: Literal["local", "test", "staging", "production"] = "local"
    policy_version: str = Field(
        default="unapproved",
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z0-9._-]+$",
    )
    max_request_body_bytes: int = Field(default=16_384, ge=1_024, le=1_048_576)
    rate_limit_requests: int = Field(default=60, ge=1, le=10_000)
    rate_limit_window_seconds: int = Field(default=60, ge=1, le=3_600)
    debug: bool = False
    video_database_path: Path = Path("data/runtime/video.sqlite3")
    job_database_path: Path = Path("data/runtime/jobs.sqlite3")
    dataset_directory: Path = Path("data/dataset")
    artifact_directory: Path = Path("data/artifacts")
    operator_api_key: SecretStr | None = None

    model_config = SettingsConfigDict(
        env_prefix="MEDIBOT_",
        env_file=".env",
        extra="ignore",
    )

    @model_validator(mode="after")
    def reject_production_debug(self) -> "Settings":
        if self.environment == "production" and self.debug:
            raise ValueError("debug mode is prohibited in production")
        if self.environment == "production" and self.operator_api_key is None:
            raise ValueError("operator API key is required in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
