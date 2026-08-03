from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from medibot.config import get_settings
from medibot.middleware import RequestBodyLimitMiddleware, SecurityHeadersMiddleware
from medibot.models import HealthResponse, MessageRequest, MessageResponse, MessageRoute

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Safety-first Medibot API foundation.",
)
app.add_middleware(RequestBodyLimitMiddleware, max_body_bytes=settings.max_request_body_bytes)
app.add_middleware(SecurityHeadersMiddleware)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    _request: Request,
    _exc: RequestValidationError,
) -> JSONResponse:
    # FastAPI's default validation response can echo rejected health data.
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "request_id": str(uuid4()),
            "error": {
                "code": "INVALID_REQUEST",
                "message": "The request could not be processed.",
            },
        },
    )


@app.get("/v1/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", version=settings.app_version)


@app.post(
    "/v1/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
)
def create_message(request: MessageRequest) -> JSONResponse:
    # Product scope and safety controls are not approved, so the API must fail closed.
    response = MessageResponse(
        request_id=str(uuid4()),
        route=MessageRoute.SERVICE_UNAVAILABLE,
        message="Medibot is not available for health guidance yet.",
        limitations="No medical information, diagnosis, or treatment is provided.",
        next_step=(
            "If this may be an emergency, contact local emergency services or a trusted person now."
        ),
        policy_version=settings.policy_version,
    )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=response.model_dump(),
    )
