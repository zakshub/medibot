from dataclasses import replace
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from medibot.platforms import (
    ApiResponse,
    FacebookPublisher,
    InstagramPublisher,
    Platform,
    PlatformApiError,
    PlatformPending,
    PublicationResult,
    PublishCommand,
    XPublisher,
    YouTubePublisher,
)


class FakeTransport:
    def __init__(self, responses: list[ApiResponse]) -> None:
        self.responses = responses
        self.calls: list[dict[str, Any]] = []

    def request(self, method: str, url: str, **kwargs: object) -> ApiResponse:
        self.calls.append({"method": method, "url": url, **kwargs})
        return self.responses.pop(0)


@pytest.fixture
def command(tmp_path: Path) -> PublishCommand:
    path = tmp_path / "video.mp4"
    payload = b"\x00\x00\x00\x18ftypmp42" + b"x" * 2_000
    path.write_bytes(payload)
    return PublishCommand(
        "video-1",
        path,
        sha256(payload).hexdigest(),
        "Reviewed sleep health",
        "Reviewed sleep health education.",
        "publish-approval-1",
        "medical-review-1",
        True,
        public_video_url="https://media.example.test/video.mp4",
        publish_at=datetime(2026, 1, 2, tzinfo=UTC),
    )


def test_publish_command_fails_closed(command: PublishCommand) -> None:
    with pytest.raises(ValueError, match="audio"):
        replace(command, has_audio=False).validate()


def test_youtube_resumable_private_first(command: PublishCommand) -> None:
    transport = FakeTransport(
        [
            ApiResponse(200, headers={"Location": "https://www.googleapis.com/upload/session"}),
            ApiResponse(200, {"id": "youtube-1"}),
        ]
    )
    result = YouTubePublisher(transport).publish(command, access_token="secret")

    assert result == PublicationResult(Platform.YOUTUBE, "youtube-1", "uploaded_private")
    assert transport.calls[0]["json_body"]["status"]["privacyStatus"] == "private"
    assert transport.calls[0]["json_body"]["status"]["containsSyntheticMedia"] is True
    assert transport.calls[1]["body"].startswith(b"\x00\x00")


def test_youtube_sanitizes_errors_and_requires_location(command: PublishCommand) -> None:
    with pytest.raises(PlatformApiError, match="upload_session_failed") as error:
        YouTubePublisher(FakeTransport([ApiResponse(401, {"token": "secret"})])).publish(
            command, access_token="secret"
        )
    assert "secret" not in str(error.value)

    with pytest.raises(PlatformApiError, match="upload_location_missing"):
        YouTubePublisher(FakeTransport([ApiResponse(200)])).publish(
            command, access_token="secret"
        )


def test_instagram_container_status_and_publish(command: PublishCommand) -> None:
    transport = FakeTransport(
        [
            ApiResponse(200, {"id": "10001"}),
            ApiResponse(200, {"status_code": "FINISHED"}),
            ApiResponse(200, {"id": "30001"}),
        ]
    )
    result = InstagramPublisher(transport).publish(
        command, access_token="secret", instagram_user_id="12345"
    )
    assert result.remote_id == "30001"
    assert transport.calls[0]["params"]["media_type"] == "REELS"

    pending = FakeTransport(
        [ApiResponse(200, {"id": "10002"}), ApiResponse(200, {"status_code": "IN_PROGRESS"})]
    )
    with pytest.raises(PlatformPending, match="IN_PROGRESS"):
        InstagramPublisher(pending).publish(
            command, access_token="secret", instagram_user_id="12345"
        )


def test_instagram_requires_public_https_url(command: PublishCommand) -> None:
    values = {name: getattr(command, name) for name in command.__dataclass_fields__}
    values["public_video_url"] = "http://private.test/video.mp4"
    with pytest.raises(ValueError, match="public HTTPS"):
        InstagramPublisher(FakeTransport([])).publish(
            PublishCommand(**values), access_token="secret", instagram_user_id="12345"
        )


def test_facebook_start_upload_finish(command: PublishCommand) -> None:
    transport = FakeTransport(
        [
            ApiResponse(200, {"video_id": "20001", "upload_url": "https://rupload.facebook.com/video-upload/1"}),
            ApiResponse(200, {"success": True}),
            ApiResponse(200, {"success": True}),
        ]
    )
    result = FacebookPublisher(transport).publish(
        command, access_token="secret", page_id="12345"
    )
    assert result.remote_id == "20001"
    assert transport.calls[1]["headers"]["file_size"] == str(command.video_path.stat().st_size)
    assert transport.calls[2]["params"]["video_state"] == "PUBLISHED"


def test_x_chunked_upload_finalize_and_post(command: PublishCommand) -> None:
    transport = FakeTransport(
        [
            ApiResponse(200, {"data": {"id": "123"}}),
            ApiResponse(200),
            ApiResponse(200),
            ApiResponse(200, {"data": {"processing_info": {"state": "succeeded"}}}),
            ApiResponse(201, {"data": {"id": "post-1"}}),
        ]
    )
    result = XPublisher(transport, chunk_bytes=1_500).publish(
        command, access_token="secret"
    )
    assert result.remote_id == "post-1"
    append_calls = [call for call in transport.calls if call["url"].endswith("/append")]
    assert len(append_calls) == 2
    assert transport.calls[-1]["json_body"]["made_with_ai"] is True


def test_x_pending_and_chunk_validation(command: PublishCommand) -> None:
    transport = FakeTransport(
        [
            ApiResponse(200, {"data": {"id": "123"}}),
            ApiResponse(200),
            ApiResponse(200, {"data": {"processing_info": {"state": "pending"}}}),
        ]
    )
    with pytest.raises(PlatformPending, match="pending"):
        XPublisher(transport, chunk_bytes=5_000).publish(command, access_token="secret")
    with pytest.raises(ValueError, match="chunk size"):
        XPublisher(FakeTransport([]), chunk_bytes=0)

def test_adapters_reject_untrusted_hosts_and_identifiers(command: PublishCommand) -> None:
    youtube = FakeTransport([ApiResponse(200, headers={"Location": "https://evil.test/upload"})])
    with pytest.raises(PlatformApiError, match="untrusted_upload_location"):
        YouTubePublisher(youtube).publish(command, access_token="secret")

    facebook = FakeTransport(
        [ApiResponse(200, {"video_id": "1", "upload_url": "https://evil.test/upload"})]
    )
    with pytest.raises(PlatformApiError, match="untrusted_upload_location"):
        FacebookPublisher(facebook).publish(
            command, access_token="secret", page_id="12345"
        )

    with pytest.raises(ValueError, match="numeric"):
        InstagramPublisher(FakeTransport([])).publish(
            command, access_token="secret", instagram_user_id="../escape"
        )
    with pytest.raises(ValueError, match="API version"):
        FacebookPublisher(FakeTransport([]), api_version="../../bad")
