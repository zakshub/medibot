from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MessageRoute(StrEnum):
    INFORMATION = "information"
    UNSUPPORTED = "unsupported"
    PROHIBITED = "prohibited"
    URGENT = "urgent"
    EMERGENCY = "emergency"
    SERVICE_UNAVAILABLE = "service_unavailable"


class MessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    message: str = Field(min_length=1, max_length=4_000)
    locale: str = Field(pattern=r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
    country_code: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    consent_version: str | None = Field(default=None, max_length=100)
    session_id: str | None = Field(default=None, min_length=16, max_length=128)

    @field_validator("country_code", mode="before")
    @classmethod
    def normalize_country_code(cls, value: object) -> object:
        return value.upper() if isinstance(value, str) else value


class HealthResponse(BaseModel):
    status: str
    version: str


class MessageResponse(BaseModel):
    request_id: str
    route: MessageRoute
    message: str
    limitations: str
    sources: list[dict[str, str]] = Field(default_factory=list)
    next_step: str
    policy_version: str

