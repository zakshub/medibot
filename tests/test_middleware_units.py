import json

import pytest
from starlette.types import Message, Receive, Scope, Send

from medibot.middleware import RequestBodyLimitMiddleware, SecurityHeadersMiddleware
from medibot.rate_limit import FixedWindowRateLimitMiddleware, Window

pytestmark = pytest.mark.anyio


async def empty_receive() -> Message:
    return {"type": "http.request", "body": b"", "more_body": False}


async def noop_send(_message: Message) -> None:
    return None


async def noop_app(_scope: Scope, _receive: Receive, _send: Send) -> None:
    return None


def test_request_body_limit_requires_positive_limit() -> None:
    with pytest.raises(ValueError, match="max_body_bytes must be positive"):
        RequestBodyLimitMiddleware(noop_app, max_body_bytes=0)


def test_rate_limiter_requires_positive_values() -> None:
    with pytest.raises(ValueError, match="rate-limit values must be positive"):
        FixedWindowRateLimitMiddleware(
            noop_app,
            requests=0,
            window_seconds=60,
            paths=frozenset({"/v1/messages"}),
        )


async def test_chunked_body_overflow_is_rejected_without_content_length() -> None:
    sent: list[Message] = []
    chunks = iter(
        [
            {"type": "http.request", "body": b"1234", "more_body": True},
            {"type": "http.request", "body": b"5678", "more_body": False},
        ]
    )

    async def receive() -> Message:
        return next(chunks)

    async def consume_body(_scope: Scope, app_receive: Receive, _send: Send) -> None:
        while (await app_receive()).get("more_body", False):
            pass

    async def send(message: Message) -> None:
        sent.append(message)

    middleware = RequestBodyLimitMiddleware(consume_body, max_body_bytes=6)
    scope: Scope = {
        "type": "http",
        "method": "POST",
        "path": "/v1/messages",
        "headers": [],
        "state": {"request_id": "request-123"},
    }

    await middleware(scope, receive, send)

    assert sent[0]["status"] == 413
    body = json.loads(sent[1]["body"])
    assert body["request_id"] == "request-123"
    assert "12345678" not in json.dumps(body)


async def test_non_http_scopes_pass_through_both_middlewares() -> None:
    calls: list[str] = []

    async def app(scope: Scope, _receive: Receive, _send: Send) -> None:
        calls.append(scope["type"])

    scope: Scope = {"type": "lifespan", "state": {}}
    body_limiter = RequestBodyLimitMiddleware(app, max_body_bytes=10)
    security_headers = SecurityHeadersMiddleware(body_limiter)

    await security_headers(scope, empty_receive, noop_send)

    assert calls == ["lifespan"]


async def test_security_middleware_preserves_existing_header() -> None:
    sent: list[Message] = []

    async def app(_scope: Scope, _receive: Receive, send: Send) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"cache-control", b"private")],
            }
        )
        await send({"type": "http.response.body", "body": b""})

    middleware = SecurityHeadersMiddleware(app)
    scope: Scope = {"type": "http", "method": "GET", "path": "/", "headers": []}

    async def send(message: Message) -> None:
        sent.append(message)

    await middleware(scope, empty_receive, send)

    headers = dict(sent[0]["headers"])
    assert headers[b"cache-control"] == b"private"
    assert headers[b"x-content-type-options"] == b"nosniff"
    assert headers[b"x-request-id"]


async def test_expired_rate_limit_windows_are_discarded(monkeypatch: pytest.MonkeyPatch) -> None:
    limiter = FixedWindowRateLimitMiddleware(
        noop_app,
        requests=1,
        window_seconds=10,
        paths=frozenset({"/v1/messages"}),
    )
    limiter._windows["expired"] = Window(started_at=0, requests=1)
    monkeypatch.setattr("medibot.rate_limit.monotonic", lambda: 20.0)

    allowed, retry_after = await limiter._consume("new-client")

    assert allowed is True
    assert retry_after == 0
    assert "expired" not in limiter._windows
    assert "new-client" in limiter._windows
