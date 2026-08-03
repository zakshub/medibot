import json
import logging
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from medibot.config import Settings
from medibot.content import EmptyContentRepository, InMemoryContentRepository
from medibot.emergency import (
    EmergencyResource,
    EmergencyResourceStatus,
    EmptyEmergencyResourceRegistry,
    InMemoryEmergencyResourceRegistry,
)
from medibot.main import app, create_app
from medibot.models import MessageRoute
from medibot.policy import (
    EmptyPolicyRepository,
    InMemoryPolicyRepository,
    PolicyStatus,
    PolicyVersion,
)
from medibot.routing import (
    EmptyEmergencySignalDetector,
    KeywordEmergencySignalDetector,
)
from medibot.scope import EmptyScopeSignalDetector, KeywordScopeSignalDetector

pytestmark = pytest.mark.anyio
TEST_NOW = datetime(2026, 8, 5, tzinfo=UTC)


def synthetic_emergency_policy() -> PolicyVersion:
    approved_at = TEST_NOW - timedelta(days=2)
    return PolicyVersion(
        policy_id="message.safety",
        version="synthetic-policy-v1",
        status=PolicyStatus.APPROVED,
        permitted_routes=frozenset({MessageRoute.EMERGENCY}),
        permitted_detector_versions=frozenset({"synthetic-detector-v1"}),
        approved_by="Synthetic safety reviewer",
        approved_at=approved_at,
        effective_at=approved_at,
        expires_at=TEST_NOW + timedelta(days=30),
    )


def synthetic_emergency_resource() -> EmergencyResource:
    approved_at = TEST_NOW - timedelta(days=2)
    return EmergencyResource(
        resource_id="emergency.pk.synthetic",
        version="1.0.0",
        country_code="PK",
        locale="en-PK",
        service_name="Synthetic emergency service",
        contact_instructions="Use the approved synthetic emergency contact channel.",
        source_url="https://example.invalid/synthetic-emergency",
        source_owner="Synthetic safety authority",
        status=EmergencyResourceStatus.APPROVED,
        approved_by="Synthetic safety reviewer",
        approved_at=approved_at,
        expires_at=TEST_NOW + timedelta(days=30),
    )


def synthetic_scope_policy() -> PolicyVersion:
    approved_at = TEST_NOW - timedelta(days=2)
    return PolicyVersion(
        policy_id="message.safety",
        version="synthetic-scope-policy-v1",
        status=PolicyStatus.APPROVED,
        permitted_routes=frozenset(
            {MessageRoute.EMERGENCY, MessageRoute.UNSUPPORTED}
        ),
        permitted_detector_versions=frozenset({"synthetic-detector-v1"}),
        permitted_scope_detector_versions=frozenset({"synthetic-scope-v1"}),
        approved_by="Synthetic safety reviewer",
        approved_at=approved_at,
        effective_at=approved_at,
        expires_at=TEST_NOW + timedelta(days=30),
    )


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as value:
        yield value


async def test_health_contract(client: AsyncClient) -> None:
    response = await client.get("/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}
    assert response.headers["x-request-id"]


def test_app_factory_defaults_to_empty_content_repository() -> None:
    configured_app = create_app(Settings(_env_file=None))

    assert isinstance(configured_app.state.content_repository, EmptyContentRepository)
    assert isinstance(configured_app.state.policy_repository, EmptyPolicyRepository)
    assert isinstance(
        configured_app.state.emergency_registry,
        EmptyEmergencyResourceRegistry,
    )
    assert isinstance(
        configured_app.state.emergency_signal_detector,
        EmptyEmergencySignalDetector,
    )
    assert isinstance(configured_app.state.scope_signal_detector, EmptyScopeSignalDetector)


def test_app_factory_preserves_injected_content_repository() -> None:
    repository = InMemoryContentRepository([])
    configured_app = create_app(Settings(_env_file=None), content_repository=repository)

    assert configured_app.state.content_repository is repository


async def test_responses_include_security_headers(client: AsyncClient) -> None:
    response = await client.get("/v1/health")

    assert response.headers["cache-control"] == "no-store"
    assert response.headers["content-security-policy"] == (
        "default-src 'none'; "
        "connect-src 'self'; "
        "script-src 'self'; "
        "style-src 'self'; "
        "base-uri 'none'; "
        "form-action 'self'; "
        "frame-ancestors 'none'"
    )
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"


async def test_readiness_fails_closed_for_unapproved_policy(client: AsyncClient) -> None:
    response = await client.get("/v1/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "version": "0.1.0",
        "policy_version": "unapproved",
        "reasons": ["policy_unapproved", "medical_guidance_unavailable"],
    }
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-request-id"]


async def test_policy_version_string_does_not_create_false_readiness() -> None:
    configured_app = create_app(
        Settings(policy_version="reviewed-v1", app_version="1.2.3", _env_file=None)
    )
    async with AsyncClient(
        transport=ASGITransport(app=configured_app),
        base_url="http://test",
    ) as configured_client:
        health_response = await configured_client.get("/v1/health")
        readiness_response = await configured_client.get("/v1/ready")

    assert health_response.json()["version"] == "1.2.3"
    assert readiness_response.status_code == 503
    assert readiness_response.json() == {
        "status": "not_ready",
        "version": "1.2.3",
        "policy_version": "reviewed-v1",
        "reasons": ["policy_unapproved", "medical_guidance_unavailable"],
    }


async def test_active_policy_is_reported_without_claiming_medical_readiness() -> None:
    policies = InMemoryPolicyRepository(
        [synthetic_emergency_policy()],
        clock=lambda: TEST_NOW,
    )
    configured_app = create_app(
        Settings(policy_version="metadata-only", _env_file=None),
        policy_repository=policies,
    )
    async with AsyncClient(
        transport=ASGITransport(app=configured_app),
        base_url="http://test",
    ) as configured_client:
        response = await configured_client.get("/v1/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "version": "0.1.0",
        "policy_version": "synthetic-policy-v1",
        "reasons": ["medical_guidance_unavailable"],
    }


async def test_readiness_fails_closed_when_policy_repository_raises() -> None:
    class ExplodingPolicyRepository:
        def get_active(self, policy_id: str):
            raise RuntimeError("synthetic private dependency detail")

    configured_app = create_app(
        Settings(policy_version="fallback-v1", _env_file=None),
        policy_repository=ExplodingPolicyRepository(),
    )
    async with AsyncClient(
        transport=ASGITransport(app=configured_app),
        base_url="http://test",
    ) as configured_client:
        response = await configured_client.get("/v1/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "version": "0.1.0",
        "policy_version": "fallback-v1",
        "reasons": ["policy_unavailable", "medical_guidance_unavailable"],
    }
    assert "private dependency detail" not in response.text


async def test_messages_fail_closed_without_approved_safety_controls(
    client: AsyncClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="medibot.audit"):
        response = await client.post(
            "/v1/messages",
            json={"message": "I have a headache", "locale": "en-PK", "country_code": "pk"},
        )

    assert response.status_code == 503
    payload = response.json()
    assert payload["route"] == "service_unavailable"
    assert payload["sources"] == []
    assert payload["policy_version"] == "unapproved"
    assert payload["request_id"] == response.headers["x-request-id"]
    assert "headache" not in response.text.lower()
    assert "headache" not in caplog.text.lower()

    event = json.loads(caplog.records[-1].message)
    assert event == {
        "outcome": "blocked_policy_unavailable",
        "policy_version": "unapproved",
        "request_id": payload["request_id"],
        "route": "service_unavailable",
    }


async def test_messages_return_emergency_only_with_complete_approved_chain(
    caplog: pytest.LogCaptureFixture,
) -> None:
    policies = InMemoryPolicyRepository(
        [synthetic_emergency_policy()],
        clock=lambda: TEST_NOW,
    )
    resources = InMemoryEmergencyResourceRegistry(
        [synthetic_emergency_resource()],
        clock=lambda: TEST_NOW,
    )
    detector = KeywordEmergencySignalDetector(
        {"synthetic danger": frozenset({"immediate_help"})},
        detector_version="synthetic-detector-v1",
    )
    configured_app = create_app(
        Settings(policy_version="metadata-only", _env_file=None),
        policy_repository=policies,
        emergency_registry=resources,
        emergency_signal_detector=detector,
    )

    with caplog.at_level(logging.INFO, logger="medibot.audit"):
        async with AsyncClient(
            transport=ASGITransport(app=configured_app),
            base_url="http://test",
        ) as configured_client:
            response = await configured_client.post(
                "/v1/messages",
                json={
                    "message": "This is a synthetic danger example.",
                    "locale": "en-PK",
                    "country_code": "PK",
                },
            )

    assert response.status_code == 200
    payload = response.json()
    assert payload["route"] == "emergency"
    assert payload["policy_version"] == "synthetic-policy-v1"
    assert payload["next_step"] == (
        "Use the approved synthetic emergency contact channel."
    )
    assert payload["request_id"] == response.headers["x-request-id"]
    assert "synthetic danger" not in response.text.lower()
    assert "synthetic danger" not in caplog.text.lower()

    event = json.loads(caplog.records[-1].message)
    assert event == {
        "outcome": "emergency_resource_returned",
        "policy_version": "synthetic-policy-v1",
        "request_id": payload["request_id"],
        "route": "emergency",
    }


async def test_messages_return_unsupported_only_after_emergency_no_signal(
    caplog: pytest.LogCaptureFixture,
) -> None:
    policies = InMemoryPolicyRepository(
        [synthetic_scope_policy()],
        clock=lambda: TEST_NOW,
    )
    emergency_detector = KeywordEmergencySignalDetector(
        {"synthetic danger": frozenset({"immediate_help"})},
        detector_version="synthetic-detector-v1",
    )
    scope_detector = KeywordScopeSignalDetector(
        unsupported_keywords={
            "synthetic outside scope": frozenset({"outside_scope"})
        },
        prohibited_keywords={},
        detector_version="synthetic-scope-v1",
    )
    configured_app = create_app(
        Settings(policy_version="metadata-only", _env_file=None),
        policy_repository=policies,
        emergency_signal_detector=emergency_detector,
        scope_signal_detector=scope_detector,
    )

    with caplog.at_level(logging.INFO, logger="medibot.audit"):
        async with AsyncClient(
            transport=ASGITransport(app=configured_app),
            base_url="http://test",
        ) as configured_client:
            response = await configured_client.post(
                "/v1/messages",
                json={
                    "message": "This is a synthetic outside scope example.",
                    "locale": "en-PK",
                    "country_code": "PK",
                },
            )

    assert response.status_code == 200
    payload = response.json()
    assert payload["route"] == "unsupported"
    assert payload["policy_version"] == "synthetic-scope-policy-v1"
    assert payload["request_id"] == response.headers["x-request-id"]
    assert payload["sources"] == []
    assert "synthetic outside scope" not in response.text.lower()
    assert "synthetic outside scope" not in caplog.text.lower()

    event = json.loads(caplog.records[-1].message)
    assert event == {
        "outcome": "unsupported_returned",
        "policy_version": "synthetic-scope-policy-v1",
        "request_id": payload["request_id"],
        "route": "unsupported",
    }


async def test_messages_reject_unknown_fields(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/messages",
        json={"message": "hello", "locale": "en-PK", "unexpected": "not allowed"},
    )

    assert response.status_code == 422
    assert "hello" not in response.text.lower()
    assert response.json()["request_id"] == response.headers["x-request-id"]


async def test_messages_reject_oversized_input_without_echoing_it(
    client: AsyncClient,
) -> None:
    oversized = "private-health-data-" * 250
    response = await client.post(
        "/v1/messages",
        json={"message": oversized, "locale": "en-PK"},
    )

    assert response.status_code == 422
    assert oversized not in response.text


async def test_request_body_limit_rejects_payload_before_validation(
    client: AsyncClient,
) -> None:
    private_payload = "private-health-data-" * 1_000
    response = await client.post(
        "/v1/messages",
        json={"message": private_payload, "locale": "en-PK"},
    )

    assert response.status_code == 413
    assert response.json() == {
        "request_id": response.headers["x-request-id"],
        "error": {
            "code": "REQUEST_TOO_LARGE",
            "message": "The request body is too large.",
        },
    }
    assert private_payload not in response.text
    assert response.headers["cache-control"] == "no-store"
