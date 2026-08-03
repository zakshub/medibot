from datetime import UTC, datetime, timedelta

import pytest

from medibot.emergency import (
    EmergencyResource,
    EmergencyResourceStatus,
    EmptyEmergencyResourceRegistry,
    InMemoryEmergencyResourceRegistry,
)
from medibot.models import MessageRequest, MessageRoute
from medibot.orchestration import MessageOrchestrator, ProcessingOutcome
from medibot.policy import (
    EmptyPolicyRepository,
    InMemoryPolicyRepository,
    PolicyStatus,
    PolicyVersion,
)
from medibot.routing import EmptyEmergencySignalDetector, KeywordEmergencySignalDetector
from medibot.scope import EmptyScopeSignalDetector, KeywordScopeSignalDetector

NOW = datetime(2026, 8, 5, tzinfo=UTC)


def approved_policy(
    permitted_routes: frozenset[MessageRoute] = frozenset({MessageRoute.EMERGENCY}),
) -> PolicyVersion:
    approved_at = NOW - timedelta(days=2)
    return PolicyVersion(
        policy_id="message.safety",
        version="1.0.0",
        status=PolicyStatus.APPROVED,
        permitted_routes=permitted_routes,
        permitted_detector_versions=(
            frozenset({"synthetic-v1"})
            if MessageRoute.EMERGENCY in permitted_routes
            else frozenset()
        ),
        permitted_scope_detector_versions=(
            frozenset({"synthetic-scope-v1"})
            if permitted_routes
            & {MessageRoute.UNSUPPORTED, MessageRoute.PROHIBITED}
            else frozenset()
        ),
        approved_by="Synthetic safety reviewer",
        approved_at=approved_at,
        effective_at=approved_at,
        expires_at=NOW + timedelta(days=30),
    )


def approved_resource(**overrides) -> EmergencyResource:
    approved_at = NOW - timedelta(days=2)
    values = {
        "resource_id": "emergency.pk.synthetic",
        "version": "1.0.0",
        "country_code": "PK",
        "locale": "en-PK",
        "service_name": "Synthetic emergency service",
        "contact_instructions": "Use the approved synthetic emergency contact channel.",
        "source_url": "https://example.invalid/synthetic-emergency",
        "source_owner": "Synthetic safety authority",
        "status": EmergencyResourceStatus.APPROVED,
        "approved_by": "Synthetic safety reviewer",
        "approved_at": approved_at,
        "expires_at": NOW + timedelta(days=30),
    }
    values.update(overrides)
    return EmergencyResource(**values)


def policy_repository(
    permitted_routes: frozenset[MessageRoute] = frozenset({MessageRoute.EMERGENCY}),
) -> InMemoryPolicyRepository:
    return InMemoryPolicyRepository(
        [approved_policy(permitted_routes)],
        clock=lambda: NOW,
    )


def emergency_detector() -> KeywordEmergencySignalDetector:
    return KeywordEmergencySignalDetector(
        {"synthetic danger": frozenset({"immediate_help"})},
        detector_version="synthetic-v1",
    )


def emergency_registry(**resource_overrides) -> InMemoryEmergencyResourceRegistry:
    return InMemoryEmergencyResourceRegistry(
        [approved_resource(**resource_overrides)],
        clock=lambda: NOW,
    )


def scope_detector() -> KeywordScopeSignalDetector:
    return KeywordScopeSignalDetector(
        unsupported_keywords={
            "synthetic outside scope": frozenset({"outside_scope"})
        },
        prohibited_keywords={
            "synthetic prohibited": frozenset({"disallowed_request"})
        },
        detector_version="synthetic-scope-v1",
    )


def payload(**overrides) -> MessageRequest:
    values = {
        "message": "This is a synthetic danger example.",
        "locale": "en-PK",
        "country_code": "PK",
    }
    values.update(overrides)
    return MessageRequest(**values)


def orchestrator(
    *,
    policies=None,
    detector=None,
    registry=None,
    scope=None,
) -> MessageOrchestrator:
    return MessageOrchestrator(
        policy_repository=policies if policies is not None else policy_repository(),
        emergency_signal_detector=detector if detector is not None else emergency_detector(),
        emergency_registry=registry if registry is not None else emergency_registry(),
        scope_signal_detector=scope if scope is not None else EmptyScopeSignalDetector(),
        fallback_policy_version="unapproved",
    )


def test_orchestrator_fails_closed_without_active_policy() -> None:
    result = orchestrator(policies=EmptyPolicyRepository()).process(
        "request-123",
        payload(),
    )

    assert result.status_code == 503
    assert result.response.route == MessageRoute.SERVICE_UNAVAILABLE
    assert result.response.policy_version == "unapproved"
    assert result.outcome == ProcessingOutcome.POLICY_UNAVAILABLE


def test_orchestrator_requires_policy_route_permission() -> None:
    result = orchestrator(
        policies=policy_repository(frozenset({MessageRoute.SERVICE_UNAVAILABLE}))
    ).process("request-123", payload())

    assert result.status_code == 503
    assert result.outcome == ProcessingOutcome.ROUTE_NOT_PERMITTED
    assert result.response.policy_version == "1.0.0"


def test_orchestrator_requires_country_before_processing_health_text() -> None:
    result = orchestrator().process("request-123", payload(country_code=None))

    assert result.status_code == 503
    assert result.outcome == ProcessingOutcome.LOCATION_UNAVAILABLE


def test_orchestrator_fails_closed_when_detector_is_unavailable() -> None:
    result = orchestrator(detector=EmptyEmergencySignalDetector()).process(
        "request-123",
        payload(),
    )

    assert result.status_code == 503
    assert result.outcome == ProcessingOutcome.DETECTOR_UNAVAILABLE


def test_orchestrator_requires_policy_pinned_detector_version() -> None:
    detector = KeywordEmergencySignalDetector(
        {"synthetic danger": frozenset({"immediate_help"})},
        detector_version="unreviewed-v2",
    )

    result = orchestrator(detector=detector).process("request-123", payload())

    assert result.status_code == 503
    assert result.outcome == ProcessingOutcome.DETECTOR_VERSION_NOT_PERMITTED


def test_orchestrator_keeps_normal_medical_guidance_locked() -> None:
    result = orchestrator().process(
        "request-123",
        payload(message="Synthetic ordinary request."),
    )

    assert result.status_code == 503
    assert result.outcome == ProcessingOutcome.NO_EMERGENCY_SIGNAL
    assert result.response.route == MessageRoute.SERVICE_UNAVAILABLE


def test_orchestrator_returns_unsupported_after_emergency_no_signal() -> None:
    policies = policy_repository(
        frozenset({MessageRoute.EMERGENCY, MessageRoute.UNSUPPORTED})
    )
    result = orchestrator(policies=policies, scope=scope_detector()).process(
        "request-123",
        payload(message="Synthetic outside scope example."),
    )

    assert result.status_code == 200
    assert result.outcome == ProcessingOutcome.UNSUPPORTED_RETURNED
    assert result.response.route == MessageRoute.UNSUPPORTED
    assert result.response.sources == []


def test_orchestrator_returns_prohibited_after_emergency_no_signal() -> None:
    policies = policy_repository(
        frozenset({MessageRoute.EMERGENCY, MessageRoute.PROHIBITED})
    )
    result = orchestrator(policies=policies, scope=scope_detector()).process(
        "request-123",
        payload(message="Synthetic prohibited example."),
    )

    assert result.status_code == 200
    assert result.outcome == ProcessingOutcome.PROHIBITED_RETURNED
    assert result.response.route == MessageRoute.PROHIBITED


def test_orchestrator_requires_available_scope_detector() -> None:
    policies = policy_repository(
        frozenset({MessageRoute.EMERGENCY, MessageRoute.UNSUPPORTED})
    )
    result = orchestrator(policies=policies).process(
        "request-123",
        payload(message="Synthetic outside scope example."),
    )

    assert result.status_code == 503
    assert result.outcome == ProcessingOutcome.SCOPE_DETECTOR_UNAVAILABLE


def test_orchestrator_keeps_medical_guidance_locked_after_scope_no_signal() -> None:
    policies = policy_repository(
        frozenset({MessageRoute.EMERGENCY, MessageRoute.UNSUPPORTED})
    )
    result = orchestrator(policies=policies, scope=scope_detector()).process(
        "request-123",
        payload(message="Synthetic ordinary example."),
    )

    assert result.status_code == 503
    assert result.outcome == ProcessingOutcome.NO_EMERGENCY_SIGNAL
    assert result.response.route == MessageRoute.SERVICE_UNAVAILABLE


def test_orchestrator_requires_policy_pinned_scope_detector_version() -> None:
    policies = policy_repository(
        frozenset({MessageRoute.EMERGENCY, MessageRoute.UNSUPPORTED})
    )
    unreviewed_detector = KeywordScopeSignalDetector(
        unsupported_keywords={
            "synthetic outside scope": frozenset({"outside_scope"})
        },
        prohibited_keywords={},
        detector_version="unreviewed-scope-v2",
    )
    result = orchestrator(policies=policies, scope=unreviewed_detector).process(
        "request-123",
        payload(message="Synthetic outside scope example."),
    )

    assert result.status_code == 503
    assert result.outcome == ProcessingOutcome.SCOPE_DETECTOR_VERSION_NOT_PERMITTED


def test_orchestrator_requires_detected_scope_route_permission() -> None:
    policies = policy_repository(
        frozenset({MessageRoute.EMERGENCY, MessageRoute.UNSUPPORTED})
    )
    result = orchestrator(policies=policies, scope=scope_detector()).process(
        "request-123",
        payload(message="Synthetic prohibited example."),
    )

    assert result.status_code == 503
    assert result.outcome == ProcessingOutcome.SCOPE_ROUTE_NOT_PERMITTED


def test_orchestrator_contains_scope_detector_failure() -> None:
    class ExplodingScopeDetector:
        def evaluate(self, message: str, locale: str):
            raise RuntimeError(f"private scope detail: {message}")

    policies = policy_repository(
        frozenset({MessageRoute.EMERGENCY, MessageRoute.UNSUPPORTED})
    )
    result = orchestrator(policies=policies, scope=ExplodingScopeDetector()).process(
        "request-123",
        payload(message="Synthetic outside scope example."),
    )

    assert result.status_code == 503
    assert result.outcome == ProcessingOutcome.SCOPE_DEPENDENCY_FAILURE


def test_emergency_route_precedes_scope_detection() -> None:
    class ExplodingScopeDetector:
        def evaluate(self, message: str, locale: str):
            raise AssertionError("scope detector must not run for emergency signal")

    policies = policy_repository(
        frozenset({MessageRoute.EMERGENCY, MessageRoute.PROHIBITED})
    )
    result = orchestrator(policies=policies, scope=ExplodingScopeDetector()).process(
        "request-123",
        payload(message="Synthetic danger and synthetic prohibited example."),
    )

    assert result.status_code == 200
    assert result.outcome == ProcessingOutcome.EMERGENCY_RESOURCE_RETURNED
    assert result.response.route == MessageRoute.EMERGENCY


def test_orchestrator_requires_approved_emergency_resource() -> None:
    result = orchestrator(registry=EmptyEmergencyResourceRegistry()).process(
        "request-123",
        payload(),
    )

    assert result.status_code == 503
    assert result.outcome == ProcessingOutcome.RESOURCE_UNAVAILABLE


def test_orchestrator_rejects_resource_for_different_location() -> None:
    class MismatchedRegistry:
        def get_approved(self, country_code: str, locale: str) -> EmergencyResource:
            return approved_resource(country_code="GB", locale="en-GB")

    result = orchestrator(registry=MismatchedRegistry()).process(
        "request-123",
        payload(),
    )

    assert result.status_code == 503
    assert result.outcome == ProcessingOutcome.RESOURCE_MISMATCH


def test_orchestrator_returns_only_approved_emergency_resource() -> None:
    result = orchestrator().process("request-123", payload())

    assert result.status_code == 200
    assert result.outcome == ProcessingOutcome.EMERGENCY_RESOURCE_RETURNED
    assert result.response.route == MessageRoute.EMERGENCY
    assert result.response.policy_version == "1.0.0"
    assert result.response.next_step == (
        "Use the approved synthetic emergency contact channel."
    )
    assert result.response.sources[0]["title"] == "Synthetic emergency service"


@pytest.mark.parametrize("dependency", ["policy", "detector", "registry"])
def test_orchestrator_contains_dependency_failures(dependency: str) -> None:
    class ExplodingPolicyRepository:
        def get_active(self, policy_id: str):
            raise RuntimeError("synthetic policy failure")

    class ExplodingDetector:
        def evaluate(self, message: str, locale: str):
            raise RuntimeError("synthetic detector failure")

    class ExplodingRegistry:
        def get_approved(self, country_code: str, locale: str):
            raise RuntimeError("synthetic registry failure")

    dependencies = {
        "policies": ExplodingPolicyRepository() if dependency == "policy" else None,
        "detector": ExplodingDetector() if dependency == "detector" else None,
        "registry": ExplodingRegistry() if dependency == "registry" else None,
    }
    result = orchestrator(**dependencies).process("request-123", payload())

    assert result.status_code == 503
    expected_outcomes = {
        "policy": ProcessingOutcome.POLICY_DEPENDENCY_FAILURE,
        "detector": ProcessingOutcome.DETECTOR_DEPENDENCY_FAILURE,
        "registry": ProcessingOutcome.REGISTRY_DEPENDENCY_FAILURE,
    }
    assert result.outcome == expected_outcomes[dependency]
    assert result.response.route == MessageRoute.SERVICE_UNAVAILABLE
