from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from medibot.audit import AuditEvent, emit_audit_event
from medibot.config import Settings, get_settings
from medibot.middleware import RequestBodyLimitMiddleware, SecurityHeadersMiddleware
from medibot.models import (
    ErrorResponse,
    HealthResponse,
    MessageRequest,
    MessageResponse,
    ReadinessResponse,
)
from medibot.rate_limit import FixedWindowRateLimitMiddleware
from medibot.responses import unavailable_response


def create_app(app_settings: Settings | None = None) -> FastAPI:
    settings = app_settings or get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Safety-first Medibot API foundation.",
        debug=settings.debug,
    )
    application.state.settings = settings
    application.add_middleware(
        RequestBodyLimitMiddleware,
        max_body_bytes=settings.max_request_body_bytes,
    )
    application.add_middleware(
        FixedWindowRateLimitMiddleware,
        requests=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
        paths=frozenset({"/v1/messages"}),
    )
    application.add_middleware(SecurityHeadersMiddleware)

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request,
        _exc: RequestValidationError,
    ) -> JSONResponse:
        # FastAPI's default validation response can echo rejected health data.
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "request_id": request.state.request_id,
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "The request could not be processed.",
                },
            },
        )

    @application.get("/v1/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", version=settings.app_version)

    @application.get(
        "/v1/ready",
        response_model=ReadinessResponse,
        responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadinessResponse}},
    )
    def readiness() -> JSONResponse:
        reasons = ["medical_guidance_unavailable"]
        if settings.policy_version == "unapproved":
            reasons.insert(0, "policy_unapproved")

        response = ReadinessResponse(
            status="not_ready",
            version=settings.app_version,
            policy_version=settings.policy_version,
            reasons=reasons,
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=response.model_dump(),
        )

    @application.post(
        "/v1/messages",
        response_model=MessageResponse,
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        responses={
            status.HTTP_413_CONTENT_TOO_LARGE: {"model": ErrorResponse},
            status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse},
            status.HTTP_429_TOO_MANY_REQUESTS: {"model": ErrorResponse},
        },
    )
    def create_message(request: Request, payload: MessageRequest) -> JSONResponse:
        # Product scope and safety controls are not approved, so the API must fail closed.
        response = unavailable_response(
            request_id=request.state.request_id,
            policy_version=settings.policy_version,
        )
        emit_audit_event(
            AuditEvent(
                request_id=response.request_id,
                route=response.route,
                outcome="blocked_unavailable",
                policy_version=response.policy_version,
            )
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=response.model_dump(),
        )

    return application


app = create_app()
