import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from medibot.middleware import SecurityHeadersMiddleware
from medibot.rate_limit import FixedWindowRateLimitMiddleware

pytestmark = pytest.mark.anyio


def build_limited_app() -> FastAPI:
    app = FastAPI()

    @app.post("/v1/messages")
    def message() -> dict[str, str]:
        return {"status": "accepted"}

    app.add_middleware(
        FixedWindowRateLimitMiddleware,
        requests=1,
        window_seconds=60,
        paths=frozenset({"/v1/messages"}),
    )
    app.add_middleware(SecurityHeadersMiddleware)
    return app


async def test_rate_limit_returns_sanitized_429_with_retry_after() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=build_limited_app()),
        base_url="http://test",
    ) as client:
        assert (await client.post("/v1/messages")).status_code == 200
        response = await client.post(
            "/v1/messages",
            headers={"X-Forwarded-For": "sensitive-user-identifier"},
        )

    assert response.status_code == 429
    assert int(response.headers["retry-after"]) >= 1
    assert response.json() == {
        "request_id": response.headers["x-request-id"],
        "error": {
            "code": "RATE_LIMITED",
            "message": "Too many requests. Try again later.",
        },
    }
    assert "sensitive-user-identifier" not in response.text
    assert response.headers["cache-control"] == "no-store"


async def test_rate_limit_does_not_apply_to_unlisted_paths() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=build_limited_app()),
        base_url="http://test",
    ) as client:
        for _attempt in range(3):
            assert (await client.get("/openapi.json")).status_code == 200

