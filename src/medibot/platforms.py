"""Credential-safe publishing adapters for YouTube, Meta, and X."""

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlparse

import httpx


class Platform(StrEnum):
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    X = "x"


class ApiTransportError(RuntimeError):
    pass


class PlatformApiError(RuntimeError):
    def __init__(self, platform: Platform, status_code: int, code: str) -> None:
        super().__init__(f"{platform.value} API failed: {code} ({status_code})")
        self.platform = platform
        self.status_code = status_code
        self.code = code


class PlatformPending(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ApiResponse:
    status_code: int
    json_body: dict[str, Any] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)


class ApiTransport(Protocol):
    def request(
        self,
        method: str,
        url: str,
        *,
        token: str,
        params: dict[str, object] | None = None,
        json_body: dict[str, object] | None = None,
        body: bytes | None = None,
        file_field: tuple[str, str, bytes, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> ApiResponse: ...


class HttpxApiTransport:
    def __init__(self, *, timeout_seconds: float = 60) -> None:
        self.timeout_seconds = timeout_seconds

    def request(
        self,
        method: str,
        url: str,
        *,
        token: str,
        params: dict[str, object] | None = None,
        json_body: dict[str, object] | None = None,
        body: bytes | None = None,
        file_field: tuple[str, str, bytes, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> ApiResponse:
        request_headers = {"Authorization": f"Bearer {token}", **(headers or {})}
        files = None
        if file_field is not None:
            field_name, filename, payload, content_type = file_field
            files = {field_name: (filename, payload, content_type)}
        try:
            response = httpx.request(
                method,
                url,
                params=params,
                json=json_body,
                content=body,
                files=files,
                headers=request_headers,
                timeout=self.timeout_seconds,
                follow_redirects=False,
            )
        except httpx.HTTPError as exc:
            raise ApiTransportError("platform API transport failed") from exc
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        return ApiResponse(response.status_code, payload, dict(response.headers))


@dataclass(frozen=True, slots=True)
class PublishCommand:
    candidate_id: str
    video_path: Path
    artifact_sha256: str
    title: str
    caption: str
    publish_approval_id: str
    medical_review_id: str
    has_audio: bool
    contains_synthetic_media: bool = True
    public_video_url: str | None = None
    publish_at: datetime | None = None

    def validate(self) -> bytes:
        if not self.publish_approval_id.strip() or not self.medical_review_id.strip():
            raise ValueError("medical review and publish approval are required")
        if not self.has_audio:
            raise ValueError("a narration audio track is required for publishing")
        if self.video_path.suffix.casefold() != ".mp4" or not self.video_path.is_file():
            raise ValueError("a readable MP4 video is required")
        payload = self.video_path.read_bytes()
        if b"ftyp" not in payload[:64]:
            raise ValueError("video is not a valid MP4 container")
        if sha256(payload).hexdigest() != self.artifact_sha256:
            raise ValueError("approved artifact hash does not match the video")
        if not self.title.strip() or not self.caption.strip():
            raise ValueError("title and caption are required")
        return payload


@dataclass(frozen=True, slots=True)
class PublicationResult:
    platform: Platform
    remote_id: str
    state: str


def _require_identifier(value: str, label: str) -> str:
    if not value.isdigit() or len(value) > 30:
        raise ValueError(f"{label} must be a numeric platform identifier")
    return value


def _require_api_version(value: str) -> str:
    if not re.fullmatch(r"v[0-9]+[.][0-9]+", value):
        raise ValueError("Meta API version is invalid")
    return value


def _require_upload_host(
    url: str,
    allowed_hosts: frozenset[str],
    platform: Platform,
) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in allowed_hosts:
        raise PlatformApiError(platform, 200, "untrusted_upload_location")
    return url


def _require(
    response: ApiResponse,
    expected: set[int],
    platform: Platform,
    code: str,
) -> dict[str, Any]:
    if response.status_code not in expected:
        raise PlatformApiError(platform, response.status_code, code)
    return response.json_body


class YouTubePublisher:
    start_url = "https://www.googleapis.com/upload/youtube/v3/videos"

    def __init__(self, transport: ApiTransport) -> None:
        self.transport = transport

    def publish(self, command: PublishCommand, *, access_token: str) -> PublicationResult:
        payload = command.validate()
        status: dict[str, object] = {
            "privacyStatus": "private",
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": command.contains_synthetic_media,
        }
        if command.publish_at is not None:
            status["publishAt"] = command.publish_at.isoformat()
        start = self.transport.request(
            "POST",
            self.start_url,
            token=access_token,
            params={"uploadType": "resumable", "part": "snippet,status"},
            json_body={
                "snippet": {
                    "title": command.title,
                    "description": command.caption,
                    "categoryId": "27",
                },
                "status": status,
            },
            headers={
                "X-Upload-Content-Type": "video/mp4",
                "X-Upload-Content-Length": str(len(payload)),
            },
        )
        _require(start, {200}, Platform.YOUTUBE, "upload_session_failed")
        upload_url = next(
            (value for key, value in start.headers.items() if key.casefold() == "location"),
            None,
        )
        if not upload_url:
            raise PlatformApiError(Platform.YOUTUBE, 200, "upload_location_missing")
        trusted_url = _require_upload_host(
            upload_url,
            frozenset({"www.googleapis.com", "upload.youtube.com"}),
            Platform.YOUTUBE,
        )
        uploaded = self.transport.request(
            "PUT",
            trusted_url,
            token=access_token,
            body=payload,
            headers={"Content-Type": "video/mp4"},
        )
        body = _require(uploaded, {200, 201}, Platform.YOUTUBE, "video_upload_failed")
        remote_id = str(body.get("id", ""))
        if not remote_id:
            raise PlatformApiError(Platform.YOUTUBE, uploaded.status_code, "remote_id_missing")
        return PublicationResult(Platform.YOUTUBE, remote_id, "uploaded_private")


class InstagramPublisher:
    def __init__(self, transport: ApiTransport, *, api_version: str = "v23.0") -> None:
        self.transport = transport
        self.api_version = _require_api_version(api_version)

    def publish(
        self,
        command: PublishCommand,
        *,
        access_token: str,
        instagram_user_id: str,
    ) -> PublicationResult:
        command.validate()
        _require_identifier(instagram_user_id, "Instagram user ID")
        if not command.public_video_url or not command.public_video_url.startswith("https://"):
            raise ValueError("Instagram publishing requires a public HTTPS video URL")
        base = f"https://graph.facebook.com/{self.api_version}"
        created = self.transport.request(
            "POST",
            f"{base}/{instagram_user_id}/media",
            token=access_token,
            params={
                "media_type": "REELS",
                "video_url": command.public_video_url,
                "caption": command.caption,
                "share_to_feed": "true",
            },
        )
        container = str(
            _require(created, {200}, Platform.INSTAGRAM, "container_create_failed").get("id", "")
        )
        if not container:
            raise PlatformApiError(Platform.INSTAGRAM, 200, "container_id_missing")
        _require_identifier(container, "Instagram container ID")
        status = self.transport.request(
            "GET",
            f"{base}/{container}",
            token=access_token,
            params={"fields": "status_code"},
        )
        state = str(
            _require(status, {200}, Platform.INSTAGRAM, "container_status_failed").get(
                "status_code", ""
            )
        )
        if state != "FINISHED":
            raise PlatformPending(f"Instagram container is {state or 'not_ready'}")
        published = self.transport.request(
            "POST",
            f"{base}/{instagram_user_id}/media_publish",
            token=access_token,
            params={"creation_id": container},
        )
        remote_id = str(
            _require(published, {200}, Platform.INSTAGRAM, "container_publish_failed").get(
                "id", ""
            )
        )
        if not remote_id:
            raise PlatformApiError(Platform.INSTAGRAM, 200, "remote_id_missing")
        return PublicationResult(Platform.INSTAGRAM, remote_id, "published")


class FacebookPublisher:
    def __init__(self, transport: ApiTransport, *, api_version: str = "v23.0") -> None:
        self.transport = transport
        self.api_version = _require_api_version(api_version)

    def publish(
        self,
        command: PublishCommand,
        *,
        access_token: str,
        page_id: str,
    ) -> PublicationResult:
        payload = command.validate()
        _require_identifier(page_id, "Facebook page ID")
        endpoint = f"https://graph.facebook.com/{self.api_version}/{page_id}/video_reels"
        started = self.transport.request(
            "POST",
            endpoint,
            token=access_token,
            params={"upload_phase": "start"},
        )
        start_body = _require(started, {200}, Platform.FACEBOOK, "reel_start_failed")
        video_id = str(start_body.get("video_id", ""))
        upload_url = str(start_body.get("upload_url", ""))
        if not video_id or not upload_url:
            raise PlatformApiError(Platform.FACEBOOK, 200, "upload_session_invalid")
        _require_identifier(video_id, "Facebook video ID")
        trusted_url = _require_upload_host(
            upload_url,
            frozenset({"rupload.facebook.com"}),
            Platform.FACEBOOK,
        )
        uploaded = self.transport.request(
            "POST",
            trusted_url,
            token=access_token,
            body=payload,
            headers={
                "file_size": str(len(payload)),
                "Content-Type": "application/octet-stream",
            },
        )
        _require(uploaded, {200}, Platform.FACEBOOK, "reel_upload_failed")
        finished = self.transport.request(
            "POST",
            endpoint,
            token=access_token,
            params={
                "video_id": video_id,
                "upload_phase": "finish",
                "video_state": "PUBLISHED",
                "description": command.caption,
                "title": command.title,
            },
        )
        _require(finished, {200}, Platform.FACEBOOK, "reel_publish_failed")
        return PublicationResult(Platform.FACEBOOK, video_id, "published")


class XPublisher:
    def __init__(self, transport: ApiTransport, *, chunk_bytes: int = 4 * 1024 * 1024) -> None:
        if not 1 <= chunk_bytes <= 5 * 1024 * 1024:
            raise ValueError("X upload chunk size must be between one byte and five MiB")
        self.transport = transport
        self.chunk_bytes = chunk_bytes

    def publish(self, command: PublishCommand, *, access_token: str) -> PublicationResult:
        payload = command.validate()
        initialized = self.transport.request(
            "POST",
            "https://api.x.com/2/media/upload/initialize",
            token=access_token,
            json_body={
                "media_category": "tweet_video",
                "media_type": "video/mp4",
                "shared": False,
                "total_bytes": len(payload),
            },
        )
        init_body = _require(initialized, {200}, Platform.X, "media_initialize_failed")
        media_id = str(init_body.get("data", {}).get("id", ""))
        if not media_id:
            raise PlatformApiError(Platform.X, 200, "media_id_missing")
        _require_identifier(media_id, "X media ID")
        for segment, offset in enumerate(range(0, len(payload), self.chunk_bytes)):
            chunk = payload[offset : offset + self.chunk_bytes]
            appended = self.transport.request(
                "POST",
                f"https://api.x.com/2/media/upload/{media_id}/append",
                token=access_token,
                params={"segment_index": segment},
                file_field=("media", command.video_path.name, chunk, "video/mp4"),
            )
            _require(appended, {200}, Platform.X, "media_append_failed")
        finalized = self.transport.request(
            "POST",
            f"https://api.x.com/2/media/upload/{media_id}/finalize",
            token=access_token,
        )
        finalize_body = _require(finalized, {200}, Platform.X, "media_finalize_failed")
        state = str(finalize_body.get("data", {}).get("processing_info", {}).get("state", ""))
        if state not in {"", "succeeded"}:
            raise PlatformPending(f"X media processing is {state}")
        posted = self.transport.request(
            "POST",
            "https://api.x.com/2/tweets",
            token=access_token,
            json_body={
                "text": command.caption,
                "media": {"media_ids": [media_id]},
                "made_with_ai": command.contains_synthetic_media,
            },
        )
        post_body = _require(posted, {201}, Platform.X, "post_create_failed")
        remote_id = str(post_body.get("data", {}).get("id", ""))
        if not remote_id:
            raise PlatformApiError(Platform.X, 201, "remote_id_missing")
        return PublicationResult(Platform.X, remote_id, "published")

