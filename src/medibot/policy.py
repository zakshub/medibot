from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from medibot.models import MessageRoute


class PolicyStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    RETIRED = "retired"


class PolicyVersion(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    policy_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{2,99}$")
    version: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
    status: PolicyStatus = PolicyStatus.DRAFT
    permitted_routes: frozenset[MessageRoute] = Field(default_factory=frozenset)
    approved_by: str | None = Field(default=None, max_length=200)
    approved_at: datetime | None = None
    effective_at: datetime | None = None
    expires_at: datetime | None = None

    @model_validator(mode="after")
    def validate_approval_window(self) -> "PolicyVersion":
        evidence = (
            self.approved_by,
            self.approved_at,
            self.effective_at,
            self.expires_at,
        )
        if self.status == PolicyStatus.APPROVED and any(value is None for value in evidence):
            raise ValueError("approved policy requires complete approval and time-window evidence")
        if self.status != PolicyStatus.APPROVED and any(value is not None for value in evidence):
            raise ValueError("approval evidence is only valid for approved policy")

        timestamps = (self.approved_at, self.effective_at, self.expires_at)
        if any(value is not None and value.tzinfo is None for value in timestamps):
            raise ValueError("policy timestamps must include a timezone")
        if (
            self.approved_at is not None
            and self.effective_at is not None
            and self.effective_at < self.approved_at
        ):
            raise ValueError("policy cannot become effective before approval")
        if (
            self.effective_at is not None
            and self.expires_at is not None
            and self.expires_at <= self.effective_at
        ):
            raise ValueError("policy expiry must be later than its effective time")
        return self

    def is_active(self, at: datetime | None = None) -> bool:
        now = at or datetime.now(UTC)
        if now.tzinfo is None:
            raise ValueError("policy evaluation time must include a timezone")
        return (
            self.status == PolicyStatus.APPROVED
            and self.effective_at is not None
            and self.expires_at is not None
            and self.effective_at <= now < self.expires_at
        )


class PolicyRepository(Protocol):
    def get_active(self, policy_id: str) -> PolicyVersion | None: ...


class EmptyPolicyRepository:
    """Fail-closed policy repository used until approved publication exists."""

    def get_active(self, policy_id: str) -> None:
        return None

