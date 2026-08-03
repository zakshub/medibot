from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Protocol

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from medibot.models import MessageRoute


class PolicyStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    RETIRED = "retired"


DetectorVersion = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z0-9._-]+$",
    ),
]


class PolicyVersion(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    policy_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{2,99}$")
    version: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
    status: PolicyStatus = PolicyStatus.DRAFT
    permitted_routes: frozenset[MessageRoute] = Field(default_factory=frozenset)
    permitted_detector_versions: frozenset[DetectorVersion] = Field(
        default_factory=frozenset,
        max_length=32,
    )
    permitted_scope_detector_versions: frozenset[DetectorVersion] = Field(
        default_factory=frozenset,
        max_length=32,
    )
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

        emergency_permitted = MessageRoute.EMERGENCY in self.permitted_routes
        if emergency_permitted and not self.permitted_detector_versions:
            raise ValueError("emergency route requires permitted detector versions")
        if not emergency_permitted and self.permitted_detector_versions:
            raise ValueError("detector versions are only valid with the emergency route")

        scope_permitted = bool(
            self.permitted_routes
            & {MessageRoute.UNSUPPORTED, MessageRoute.PROHIBITED}
        )
        if scope_permitted and not self.permitted_scope_detector_versions:
            raise ValueError("scope routes require permitted scope detector versions")
        if not scope_permitted and self.permitted_scope_detector_versions:
            raise ValueError("scope detector versions require a scope route")
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


class InMemoryPolicyRepository:
    """Deterministic reference repository for immutable approved policies."""

    def __init__(
        self,
        records: Iterable[PolicyVersion],
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._clock = clock or (lambda: datetime.now(UTC))
        self._records: dict[str, list[PolicyVersion]] = {}
        versions: set[tuple[str, str]] = set()

        for record in records:
            version_key = (record.policy_id, record.version)
            if version_key in versions:
                raise ValueError("duplicate policy ID and version")
            versions.add(version_key)
            self._records.setdefault(record.policy_id, []).append(record)

    def get_active(self, policy_id: str) -> PolicyVersion | None:
        now = self._clock()
        candidates = [
            record
            for record in self._records.get(policy_id, [])
            if record.is_active(now)
        ]
        if not candidates:
            return None
        minimum = datetime.min.replace(tzinfo=UTC)
        return max(candidates, key=lambda record: record.effective_at or minimum)
