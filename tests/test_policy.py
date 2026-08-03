from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from medibot.policy import EmptyPolicyRepository, PolicyStatus, PolicyVersion


def approved_policy(**overrides) -> PolicyVersion:
    approved_at = datetime(2026, 8, 3, tzinfo=UTC)
    values = {
        "policy_id": "message.safety",
        "version": "1.0.0",
        "status": PolicyStatus.APPROVED,
        "permitted_routes": frozenset({"unsupported", "service_unavailable"}),
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

