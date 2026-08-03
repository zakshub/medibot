from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from medibot.policy import (
    EmptyPolicyRepository,
    InMemoryPolicyRepository,
    PolicyStatus,
    PolicyVersion,
)


def approved_policy(**overrides) -> PolicyVersion:
    approved_at = datetime(2026, 8, 3, tzinfo=UTC)
    values = {
        "policy_id": "message.safety",
        "version": "1.0.0",
        "status": PolicyStatus.APPROVED,
        "permitted_routes": frozenset({"service_unavailable"}),
        "approved_by": "Safety reviewer",
        "approved_at": approved_at,
        "effective_at": approved_at + timedelta(hours=1),
        "expires_at": approved_at + timedelta(days=30),
    }
    values.update(overrides)
    return PolicyVersion(**values)


def test_approved_policy_requires_complete_evidence() -> None:
    with pytest.raises(ValidationError, match="requires complete"):
        approved_policy(approved_by=None)


def test_draft_policy_rejects_approval_evidence() -> None:
    with pytest.raises(ValidationError, match="only valid for approved"):
        approved_policy(status=PolicyStatus.DRAFT)


def test_policy_timestamps_require_timezone() -> None:
    with pytest.raises(ValidationError, match="must include a timezone"):
        approved_policy(effective_at=datetime(2026, 8, 3, 1))


def test_policy_window_order_is_enforced() -> None:
    approved_at = datetime(2026, 8, 3, tzinfo=UTC)
    with pytest.raises(ValidationError, match="before approval"):
        approved_policy(effective_at=approved_at - timedelta(seconds=1))

    with pytest.raises(ValidationError, match="later than"):
        approved_policy(effective_at=approved_at, expires_at=approved_at)


def test_emergency_policy_requires_pinned_detector_versions() -> None:
    with pytest.raises(ValidationError, match="requires permitted detector versions"):
        approved_policy(permitted_routes=frozenset({"emergency"}))


def test_detector_versions_require_emergency_route() -> None:
    with pytest.raises(ValidationError, match="only valid with the emergency route"):
        approved_policy(permitted_detector_versions=frozenset({"synthetic-v1"}))


def test_scope_policy_requires_pinned_scope_detector_versions() -> None:
    with pytest.raises(ValidationError, match="require permitted scope detector"):
        approved_policy(permitted_routes=frozenset({"unsupported"}))


def test_scope_detector_versions_require_scope_route() -> None:
    with pytest.raises(ValidationError, match="require a scope route"):
        approved_policy(
            permitted_scope_detector_versions=frozenset({"synthetic-scope-v1"})
        )


def test_scope_policy_accepts_explicit_detector_version() -> None:
    policy = approved_policy(
        permitted_routes=frozenset({"unsupported", "prohibited"}),
        permitted_scope_detector_versions=frozenset({"synthetic-scope-v1"}),
    )

    assert policy.permitted_scope_detector_versions == frozenset(
        {"synthetic-scope-v1"}
    )


def test_only_current_approved_policy_is_active() -> None:
    policy = approved_policy()

    assert policy.is_active(datetime(2026, 8, 4, tzinfo=UTC)) is True
    assert policy.is_active(datetime(2026, 9, 3, tzinfo=UTC)) is False
    assert policy.model_copy(update={"status": PolicyStatus.RETIRED}).is_active(
        datetime(2026, 8, 4, tzinfo=UTC)
    ) is False

    with pytest.raises(ValueError, match="evaluation time"):
        policy.is_active(datetime(2026, 8, 4))


def test_empty_policy_repository_fails_closed() -> None:
    assert EmptyPolicyRepository().get_active("message.safety") is None


def test_in_memory_policy_repository_returns_latest_active_policy() -> None:
    first = approved_policy(
        version="1.0.0",
        effective_at=datetime(2026, 8, 3, 1, tzinfo=UTC),
    )
    second = approved_policy(
        version="1.1.0",
        effective_at=datetime(2026, 8, 4, tzinfo=UTC),
    )
    repository = InMemoryPolicyRepository(
        [first, second],
        clock=lambda: datetime(2026, 8, 5, tzinfo=UTC),
    )

    assert repository.get_active("message.safety") == second


def test_in_memory_policy_repository_filters_inactive_policies() -> None:
    repository = InMemoryPolicyRepository(
        [approved_policy(expires_at=datetime(2026, 8, 4, tzinfo=UTC))],
        clock=lambda: datetime(2026, 8, 5, tzinfo=UTC),
    )

    assert repository.get_active("message.safety") is None
    assert repository.get_active("unknown.policy") is None


def test_in_memory_policy_repository_rejects_duplicate_versions() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        InMemoryPolicyRepository([approved_policy(), approved_policy()])
