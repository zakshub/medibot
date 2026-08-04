from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from medibot.artifact_store import LocalArtifactStore
from medibot.audit import AuditEvent, emit_audit_event
from medibot.config import Settings, get_settings
from medibot.content import ContentRepository, EmptyContentRepository
from medibot.emergency import EmergencyResourceRegistry, EmptyEmergencyResourceRegistry
from medibot.job_queue import DurableJobQueue
from medibot.media import LocalVerticalVideoRenderer
from medibot.middleware import RequestBodyLimitMiddleware, SecurityHeadersMiddleware
from medibot.models import (
    ErrorResponse,
    HealthResponse,
    MessageRequest,
    MessageResponse,
    ReadinessResponse,
)
from medibot.orchestration import MESSAGE_POLICY_ID, MessageOrchestrator
from medibot.policy import EmptyPolicyRepository, PolicyRepository
from medibot.rate_limit import FixedWindowRateLimitMiddleware
from medibot.routing import EmergencySignalDetector, EmptyEmergencySignalDetector
from medibot.scope import EmptyScopeSignalDetector, ScopeSignalDetector
from medibot.video_api import create_video_router
from medibot.video_store import VideoStore


def create_app(
    app_settings: Settings | None = None,
    content_repository: ContentRepository | None = None,
    policy_repository: PolicyRepository | None = None,
    emergency_registry: EmergencyResourceRegistry | None = None,
    emergency_signal_detector: EmergencySignalDetector | None = None,
    scope_signal_detector: ScopeSignalDetector | None = None,
    video_store: VideoStore | None = None,
    artifact_store: LocalArtifactStore | None = None,
    job_queue: DurableJobQueue | None = None,
    video_clock: Callable[[], datetime] | None = None,
    video_renderer_factory: Callable[[], LocalVerticalVideoRenderer] | None = None,
) -> FastAPI:
    settings = app_settings or get_settings()
    videos = video_store or VideoStore(settings.video_database_path)
    video_artifacts = artifact_store or LocalArtifactStore(settings.artifact_directory)
    jobs = job_queue or DurableJobQueue(settings.job_database_path)
    repository = content_repository if content_repository is not None else EmptyContentRepository()
    policies = policy_repository if policy_repository is not None else EmptyPolicyRepository()
    emergency_resources = (
        emergency_registry if emergency_registry is not None else EmptyEmergencyResourceRegistry()
    )
    emergency_detector = (
        emergency_signal_detector
        if emergency_signal_detector is not None
        else EmptyEmergencySignalDetector()
    )
    scope_detector = (
        scope_signal_detector if scope_signal_detector is not None else EmptyScopeSignalDetector()
    )
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Safety-first Medibot API foundation.",
        debug=settings.debug,
    )
    application.state.settings = settings
    application.state.content_repository = repository
    application.state.policy_repository = policies
    application.state.emergency_registry = emergency_resources
    application.state.emergency_signal_detector = emergency_detector
    application.state.scope_signal_detector = scope_detector
    application.state.video_store = videos
    application.state.video_artifacts = video_artifacts
    application.state.job_queue = jobs
    application.state.message_orchestrator = MessageOrchestrator(
        policy_repository=policies,
        emergency_signal_detector=emergency_detector,
        emergency_registry=emergency_resources,
        scope_signal_detector=scope_detector,
        fallback_policy_version=settings.policy_version,
    )
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

    static_directory = Path(__file__).resolve().parent / "static"
    application.mount(
        "/assets",
        StaticFiles(directory=static_directory),
        name="assets",
    )
    if settings.environment in {"local", "test"}:
        application.mount(
            "/artifacts",
            StaticFiles(directory=video_artifacts.root),
            name="artifacts",
        )

    @application.get("/", include_in_schema=False, response_class=FileResponse)
    def user_interface() -> FileResponse:
        return FileResponse(static_directory / "video.html", media_type="text/html")

    @application.get("/video", include_in_schema=False, response_class=FileResponse)
    def video_interface() -> FileResponse:
        return FileResponse(static_directory / "video.html", media_type="text/html")

    @application.get("/legacy", include_in_schema=False, response_class=FileResponse)
    def legacy_interface() -> FileResponse:
        return FileResponse(static_directory / "index.html", media_type="text/html")

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
        policy_reason = "policy_unapproved"
        try:
            active_policy = policies.get_active(MESSAGE_POLICY_ID)
        except Exception:
            active_policy = None
            policy_reason = "policy_unavailable"

        reasons = ["medical_guidance_unavailable"]
        if active_policy is None:
            reasons.insert(0, policy_reason)

        response = ReadinessResponse(
            status="not_ready",
            version=settings.app_version,
            policy_version=(
                active_policy.version if active_policy is not None else settings.policy_version
            ),
            reasons=reasons,
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=response.model_dump(),
        )

    @application.post(
        "/v1/messages",
        response_model=MessageResponse,
        responses={
            status.HTTP_413_CONTENT_TOO_LARGE: {"model": ErrorResponse},
            status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse},
            status.HTTP_429_TOO_MANY_REQUESTS: {"model": ErrorResponse},
            status.HTTP_503_SERVICE_UNAVAILABLE: {"model": MessageResponse},
        },
    )
    def create_message(request: Request, payload: MessageRequest) -> JSONResponse:
        result = application.state.message_orchestrator.process(
            request_id=request.state.request_id,
            payload=payload,
        )
        emit_audit_event(
            AuditEvent(
                request_id=result.response.request_id,
                route=result.response.route,
                outcome=result.outcome,
                policy_version=result.response.policy_version,
            )
        )
        return JSONResponse(
            status_code=result.status_code,
            content=result.response.model_dump(),
        )

    application.include_router(
        create_video_router(
            settings,
            videos,
            video_artifacts,
            jobs,
            clock=video_clock,
            renderer_factory=video_renderer_factory,
        )
    )
    return application


app = create_app()
