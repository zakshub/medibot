from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from medibot.content import ContentStatus, EmptyContentRepository, ReviewedContent
from medibot.responses import unavailable_response


def approved_content(**overrides) -> ReviewedContent:
    approved_at = datetime(2026, 8, 3, tzinfo=UTC)
    values = {
        "content_id": "general.notice",
        "version": "1.0.0",
        "locale": "en-PK",
        "title": "Reviewed notice",
        "body": "Synthetic reviewed information.",
        "source_url": "https://example.org/health-source",
        "source_owner": "Example authority",
        "status": ContentStatus.APPROVED,
        "approved_by": "Clinical reviewer",
        "approved_at": approved_at,
        "expires_at": approved_at + timedelta(days=30),
    }
    values.update(overrides)
    return ReviewedContent(**values)


def test_approved_content_requires_complete_evidence() -> None:
    with pytest.raises(ValidationError, match="requires approver"):
        approved_content(approved_by=None)


def test_draft_content_rejects_approval_evidence() -> None:
    with pytest.raises(ValidationError, match="only valid for approved"):
        approved_content(status=ContentStatus.DRAFT)


def test_content_timestamps_must_be_timezone_aware() -> None:
    with pytest.raises(ValidationError, match="approval timestamp"):
        approved_content(approved_at=datetime(2026, 8, 3))

    with pytest.raises(ValidationError, match="expiry timestamp"):
        approved_content(expires_at=datetime(2026, 9, 3))


def test_expiry_must_follow_approval() -> None:
    approved_at = datetime(2026, 8, 3, tzinfo=UTC)
    with pytest.raises(ValidationError, match="expiry must be later"):
        approved_content(approved_at=approved_at, expires_at=approved_at)


def test_only_current_approved_content_is_servable() -> None:
    content = approved_content()

    assert content.is_servable(datetime(2026, 8, 4, tzinfo=UTC)) is True
    assert content.is_servable(datetime(2026, 9, 3, tzinfo=UTC)) is False
    assert content.model_copy(update={"status": ContentStatus.RETIRED}).is_servable(
        datetime(2026, 8, 4, tzinfo=UTC)
    ) is False

    with pytest.raises(ValueError, match="serving time must include a timezone"):
        content.is_servable(datetime(2026, 8, 4))


def test_empty_repository_fails_closed() -> None:
    repository = EmptyContentRepository()

    assert repository.get_approved("general.notice", "en-PK") is None


def test_unavailable_response_remains_deterministic_and_non_medical() -> None:
    response = unavailable_response("request-1", "unapproved")

    assert response.route == "service_unavailable"
    assert response.sources == []
    assert response.request_id == "request-1"
    assert "diagnosis" in response.limitations

