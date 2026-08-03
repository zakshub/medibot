from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Medibot"
    app_version: str = "0.1.0"
    environment: str = "local"
    policy_version: str = "unapproved"

    model_config = SettingsConfigDict(
        env_prefix="MEDIBOT_",
        env_file=".env",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

