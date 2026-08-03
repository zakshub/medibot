from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class ContentStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    RETIRED = "retired"


class ReviewedContent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    content_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{2,99}$")
    version: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
    locale: str = Field(pattern=r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=20_000)
    source_url: HttpUrl
    source_owner: str = Field(min_length=1, max_length=200)
    status: ContentStatus = ContentStatus.DRAFT
    approved_by: str | None = Field(default=None, max_length=200)
    approved_at: datetime | None = None
    expires_at: datetime | None = None

    @model_validator(mode="after")
    def validate_approval_evidence(self) -> "ReviewedContent":
        evidence = (self.approved_by, self.approved_at)
        if self.status == ContentStatus.APPROVED and any(value is None for value in evidence):
            raise ValueError("approved content requires approver and approval timestamp")
        if self.status != ContentStatus.APPROVED and any(value is not None for value in evidence):
            raise ValueError("approval evidence is only valid for approved content")
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
            self.status == ContentStatus.APPROVED
            and self.expires_at is not None
            and now < self.expires_at
        )


class ContentRepository(Protocol):
    def get_approved(self, content_id: str, locale: str) -> ReviewedContent | None: ...


class EmptyContentRepository:
    """Fail-closed repository used until an approved content source exists."""

    def get_approved(self, content_id: str, locale: str) -> None:
        return None

