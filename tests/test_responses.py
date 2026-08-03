from datetime import UTC, datetime, timedelta

from medibot.emergency import EmergencyResource, EmergencyResourceStatus
from medibot.models import MessageRoute
from medibot.responses import (
    emergency_response,
    prohibited_response,
    unsupported_response,
)
from medibot.routing import EmergencySignalDecision, EmergencySignalStatus


def approved_resource() -> EmergencyResource:
    approved_at = datetime(2026, 8, 3, tzinfo=UTC)
    return EmergencyResource(
        resource_id="emergency.pk.public",
        version="1.0.0",
        country_code="PK",
        locale="en-PK",
        service_name="Synthetic emergency service",
        contact_instructions="Use the locally approved emergency contact channel.",
        source_url="https://example.invalid/emergency-policy",
        source_owner="Synthetic Public Safety Authority",
        status=EmergencyResourceStatus.APPROVED,
        approved_by="Safety reviewer",
        approved_at=approved_at,
        expires_at=approved_at + timedelta(days=30),
    )


def possible_emergency_decision() -> EmergencySignalDecision:
    return EmergencySignalDecision(
        status=EmergencySignalStatus.POSSIBLE_EMERGENCY,
        route=MessageRoute.EMERGENCY,
        categories=frozenset({"time_sensitive_help"}),
        detector_version="synthetic-v1",
    )


def test_emergency_response_uses_bounded_reviewed_resource() -> None:
    response = emergency_response(
        request_id="request-123",
        policy_version="reviewed-v1",
        decision=possible_emergency_decision(),
        resource=approved_resource(),
    )

    assert response.route == MessageRoute.EMERGENCY
    assert response.request_id == "request-123"
    assert response.policy_version == "reviewed-v1"
    assert response.next_step == "Use the locally approved emergency contact channel."
    assert response.sources == [
        {
            "title": "Synthetic emergency service",
            "url": "https://example.invalid/emergency-policy",
            "reviewed_version": "1.0.0",
        }
    ]
    assert "diagnose" in response.limitations


def test_emergency_response_fails_closed_without_resource() -> None:
    response = emergency_response(
        request_id="request-123",
        policy_version="reviewed-v1",
        decision=possible_emergency_decision(),
        resource=None,
    )

    assert response.route == MessageRoute.SERVICE_UNAVAILABLE
    assert response.sources == []


def test_emergency_response_fails_closed_without_possible_emergency_signal() -> None:
    response = emergency_response(
        request_id="request-123",
        policy_version="reviewed-v1",
        decision=EmergencySignalDecision(
            status=EmergencySignalStatus.NO_SIGNAL,
            route=MessageRoute.INFORMATION,
            detector_version="synthetic-v1",
        ),
        resource=approved_resource(),
    )

    assert response.route == MessageRoute.SERVICE_UNAVAILABLE
    assert response.sources == []


def test_unsupported_response_is_bounded_and_non_medical() -> None:
    response = unsupported_response("request-123", "policy-v1")

    assert response.route == MessageRoute.UNSUPPORTED
    assert response.policy_version == "policy-v1"
    assert response.sources == []
    assert "diagnosis" in response.limitations


def test_prohibited_response_is_bounded_and_non_instructional() -> None:
    response = prohibited_response("request-123", "policy-v1")

    assert response.route == MessageRoute.PROHIBITED
    assert response.policy_version == "policy-v1"
    assert response.sources == []
    assert "No instructions" in response.limitations
