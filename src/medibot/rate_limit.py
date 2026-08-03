import asyncio
from dataclasses import dataclass
from time import monotonic

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


@dataclass(slots=True)
class Window:
    started_at: float
    requests: int


class FixedWindowRateLimitMiddleware:
    """Per-process backstop; production still requires an edge or shared-store limiter."""

    def __init__(
        self,
        app: ASGIApp,
        requests: int,
        window_seconds: int,
        paths: frozenset[str],
    ) -> None:
        if requests < 1 or window_seconds < 1:
            raise ValueError("rate-limit values must be positive")
        self.app = app
        self.requests = requests
        self.window_seconds = window_seconds
        self.paths = paths
        self._windows: dict[str, Window] = {}
        self._lock = asyncio.Lock()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path") not in self.paths:
            await self.app(scope, receive, send)
            return

        client = scope.get("client")
        client_host = client[0] if client else "unknown"
        allowed, retry_after = await self._consume(client_host)
        if not allowed:
            request_id = scope.get("state", {}).get("request_id")
            response = JSONResponse(
                status_code=429,
                headers={"Retry-After": str(retry_after)},
                content={
                    "request_id": request_id,
                    "error": {
                        "code": "RATE_LIMITED",
                        "message": "Too many requests. Try again later.",
                    },
                },
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)

    async def _consume(self, client_host: str) -> tuple[bool, int]:
        now = monotonic()
        async with self._lock:
            window = self._windows.get(client_host)
            if window is None or now - window.started_at >= self.window_seconds:
                self._windows[client_host] = Window(started_at=now, requests=1)
                self._discard_expired(now)
                return True, 0

            if window.requests >= self.requests:
                retry_after = max(1, int(self.window_seconds - (now - window.started_at)) + 1)
                return False, retry_after

            window.requests += 1
            return True, 0

    def _discard_expired(self, now: float) -> None:
        expired = [
            client_host
            for client_host, window in self._windows.items()
            if now - window.started_at >= self.window_seconds
        ]
        for client_host in expired:
            del self._windows[client_host]

