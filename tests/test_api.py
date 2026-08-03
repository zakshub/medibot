from fastapi.testclient import TestClient

from medibot.main import app

client = TestClient(app)


def test_health_contract() -> None:
    response = client.get("/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}


def test_messages_fail_closed_without_approved_safety_controls() -> None:
    response = client.post(
        "/v1/messages",
        json={"message": "I have a headache", "locale": "en-PK", "country_code": "pk"},
    )

    assert response.status_code == 503
    payload = response.json()
    assert payload["route"] == "service_unavailable"
    assert payload["sources"] == []
    assert payload["policy_version"] == "unapproved"
    assert "headache" not in response.text.lower()


def test_messages_reject_unknown_fields() -> None:
    response = client.post(
        "/v1/messages",
        json={"message": "hello", "locale": "en-PK", "unexpected": "not allowed"},
    )

    assert response.status_code == 422
    assert "hello" not in response.text.lower()


def test_messages_reject_oversized_input_without_echoing_it() -> None:
    oversized = "private-health-data-" * 250
    response = client.post(
        "/v1/messages",
        json={"message": oversized, "locale": "en-PK"},
    )

    assert response.status_code == 422
    assert oversized not in response.text

