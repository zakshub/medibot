from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator


class EmergencyResourceStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    RETIRED = "retired"


class EmergencyResource(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )

    resource_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{2,99}$")
    version: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
    country_code: str = Field(pattern=r"^[A-Z]{2}$")
    locale: str = Field(pattern=r"^[A-Z]{2,3}(?:-[A-Z0-9]{2,8})*$")
    service_name: str = Field(min_length=1, max_length=200)
    contact_instructions: str = Field(min_length=1, max_length=1_000)
    source_url: HttpUrl
    source_owner: str = Field(min_length=1, max_length=200)
    status: EmergencyResourceStatus = EmergencyResourceStatus.DRAFT
    approved_by: str | None = Field(default=None, max_length=200)
    approved_at: datetime | None = None
    expires_at: datetime | None = None

    @field_validator("country_code", "locale", mode="before")
    @classmethod
    def normalize_lookup_fields(cls, value: str) -> str:
        return value.upper()

    @model_validator(mode="after")
    def validate_approval_evidence(self) -> "EmergencyResource":
        evidence = (self.approved_by, self.approved_at, self.expires_at)
        if self.status == EmergencyResourceStatus.APPROVED and any(
            value is None for value in evidence
        ):
            raise ValueError("approved emergency resource requires complete evidence")
        if self.status != EmergencyResourceStatus.APPROVED and any(
            value is not None for value in evidence
        ):
            raise ValueError("approval evidence is only valid for approved emergency resource")
        if self.approved_at is not None and self.approved_at.tzinfo is None:
            raise ValueError("approval timestamp must include a timezone")
        if self.expires_at is not None and self.expires_at.tzinfo is None:
            raise ValueError("expiry timestamp must include a timezone")
        if (
            self.approved_at is not None
            and self.expires_at is not None
            and self.expires_at <= self.approved_at
        ):
            raise ValueError("expiry must be later than approval")
        return self

    def is_servable(self, at: datetime | None = None) -> bool:
        now = at or datetime.now(UTC)
        if now.tzinfo is None:
            raise ValueError("serving time must include a timezone")
        return (
            self.status == EmergencyResourceStatus.APPROVED
            and self.expires_at is not None
            and now < self.expires_at
        )


class EmergencyResourceRegistry(Protocol):
    def get_approved(self, country_code: str, locale: str) -> EmergencyResource | None: ...


class EmptyEmergencyResourceRegistry:
    """Fail-closed registry used until approved emergency resources exist."""

    def get_approved(self, country_code: str, locale: str) -> None:
        return None


class InMemoryEmergencyResourceRegistry:
    """Deterministic reference registry for tests and approved static resources."""

    def __init__(
        self,
        records: Iterable[EmergencyResource],
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._clock = clock or (lambda: datetime.now(UTC))
        self._records: dict[tuple[str, str], list[EmergencyResource]] = {}
        versions: set[tuple[str, str, str, str]] = set()

        for record in records:
            version_key = (
                record.country_code,
                record.locale,
                record.resource_id,
                record.version,
            )
            if version_key in versions:
                raise ValueError("duplicate country, locale, resource ID, and version")
            versions.add(version_key)
            self._records.setdefault((record.country_code, record.locale), []).append(record)

    def get_approved(self, country_code: str, locale: str) -> EmergencyResource | None:
        now = self._clock()
        normalized_key = (country_code.upper(), locale.upper())
        candidates = [
            record
            for record in self._records.get(normalized_key, [])
            if record.is_servable(now)
        ]
        if not candidates:
            return None
        minimum = datetime.min.replace(tzinfo=UTC)
        return max(candidates, key=lambda record: record.approved_at or minimum)
