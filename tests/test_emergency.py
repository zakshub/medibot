from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from medibot.emergency import (
    EmergencyResource,
    EmergencyResourceStatus,
    EmptyEmergencyResourceRegistry,
    InMemoryEmergencyResourceRegistry,
)
from medibot.main import create_app


def approved_resource(**overrides) -> EmergencyResource:
    approved_at = datetime(2026, 8, 3, tzinfo=UTC)
    values = {
        "resource_id": "emergency.pk.public",
        "version": "1.0.0",
        "country_code": "PK",
        "locale": "en-PK",
        "service_name": "Synthetic emergency service",
        "contact_instructions": "Use the locally approved emergency contact channel.",
        "source_url": "https://example.invalid/emergency-policy",
        "source_owner": "Synthetic Public Safety Authority",
        "status": EmergencyResourceStatus.APPROVED,
        "approved_by": "Safety reviewer",
        "approved_at": approved_at,
        "expires_at": approved_at + timedelta(days=30),
    }
    values.update(overrides)
    return EmergencyResource(**values)


def test_approved_emergency_resource_requires_complete_evidence() -> None:
    with pytest.raises(ValidationError, match="requires complete evidence"):
        approved_resource(approved_by=None)


def test_draft_emergency_resource_rejects_approval_evidence() -> None:
    with pytest.raises(ValidationError, match="only valid for approved"):
        approved_resource(status=EmergencyResourceStatus.DRAFT)


def test_emergency_resource_timestamps_require_timezone() -> None:
    with pytest.raises(ValidationError, match="must include a timezone"):
        approved_resource(approved_at=datetime(2026, 8, 3))

    with pytest.raises(ValidationError, match="must include a timezone"):
        approved_resource(expires_at=datetime(2026, 9, 3))


def test_emergency_resource_expiry_must_follow_approval() -> None:
    approved_at = datetime(2026, 8, 3, tzinfo=UTC)

    with pytest.raises(ValidationError, match="later than approval"):
        approved_resource(approved_at=approved_at, expires_at=approved_at)


def test_only_current_approved_emergency_resource_is_servable() -> None:
    resource = approved_resource()

    assert resource.is_servable(datetime(2026, 8, 4, tzinfo=UTC)) is True
    assert resource.is_servable(datetime(2026, 9, 3, tzinfo=UTC)) is False
    assert resource.model_copy(
        update={"status": EmergencyResourceStatus.RETIRED}
    ).is_servable(datetime(2026, 8, 4, tzinfo=UTC)) is False

    with pytest.raises(ValueError, match="serving time"):
        resource.is_servable(datetime(2026, 8, 4))


def test_empty_emergency_registry_fails_closed() -> None:
    assert EmptyEmergencyResourceRegistry().get_approved("PK", "en-PK") is None


def test_in_memory_emergency_registry_returns_latest_valid_approval() -> None:
    first = approved_resource(
        version="1.0.0",
        approved_at=datetime(2026, 8, 3, tzinfo=UTC),
        expires_at=datetime(2026, 8, 20, tzinfo=UTC),
    )
    second = approved_resource(
        version="1.1.0",
        approved_at=datetime(2026, 8, 4, tzinfo=UTC),
        expires_at=datetime(2026, 8, 20, tzinfo=UTC),
    )
    registry = InMemoryEmergencyResourceRegistry(
        [first, second],
        clock=lambda: datetime(2026, 8, 5, tzinfo=UTC),
    )

    assert registry.get_approved("pk", "en-pk") == second


def test_in_memory_emergency_registry_isolates_country_and_locale() -> None:
    registry = InMemoryEmergencyResourceRegistry(
        [
            approved_resource(country_code="PK", locale="en-PK"),
            approved_resource(country_code="GB", locale="en-GB"),
        ],
        clock=lambda: datetime(2026, 8, 5, tzinfo=UTC),
    )

    assert registry.get_approved("PK", "en-GB") is None
    assert registry.get_approved("GB", "en-PK") is None


def test_in_memory_emergency_registry_filters_expired_resources() -> None:
    registry = InMemoryEmergencyResourceRegistry(
        [approved_resource(expires_at=datetime(2026, 8, 4, tzinfo=UTC))],
        clock=lambda: datetime(2026, 8, 5, tzinfo=UTC),
    )

    assert registry.get_approved("PK", "en-PK") is None


def test_in_memory_emergency_registry_rejects_duplicate_versions() -> None:
    first = approved_resource()
    duplicate = approved_resource()

    with pytest.raises(ValueError, match="duplicate"):
        InMemoryEmergencyResourceRegistry([first, duplicate])


def test_app_factory_preserves_injected_emergency_registry() -> None:
    registry = InMemoryEmergencyResourceRegistry([])
    configured_app = create_app(emergency_registry=registry)

    assert configured_app.state.emergency_registry is registry
