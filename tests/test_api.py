import json
import logging
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from medibot.config import Settings
from medibot.main import app, create_app

pytestmark = pytest.mark.anyio


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as value:
        yield value


async def test_health_contract(client: AsyncClient) -> None:
    response = await client.get("/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}
    assert response.headers["x-request-id"]


async def test_responses_include_security_headers(client: AsyncClient) -> None:
    response = await client.get("/v1/health")

    assert response.headers["cache-control"] == "no-store"
    assert response.headers["content-security-policy"] == (
        "default-src 'none'; frame-ancestors 'none'"
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


async def test_approved_policy_does_not_create_false_readiness() -> None:
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
        "reasons": ["medical_guidance_unavailable"],
    }


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
        "outcome": "blocked_unavailable",
        "policy_version": "unapproved",
        "request_id": payload["request_id"],
        "route": "service_unavailable",
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
