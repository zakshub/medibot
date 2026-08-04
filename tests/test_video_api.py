from collections.abc import AsyncIterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from medibot.config import Settings
from medibot.main import create_app
from medibot.media import LocalVerticalVideoRenderer

pytestmark = pytest.mark.anyio
TEST_NOW = datetime(2026, 8, 5, 8, tzinfo=UTC)
STATIC_DIRECTORY = Path(__file__).resolve().parents[1] / "src" / "medibot" / "static"


def settings_for(tmp_path: Path, **overrides: object) -> Settings:
    values: dict[str, object] = {
        "environment": "test",
        "video_database_path": tmp_path / "runtime" / "video.sqlite3",
        "job_database_path": tmp_path / "runtime" / "jobs.sqlite3",
        "dataset_directory": tmp_path / "dataset",
        "artifact_directory": tmp_path / "artifacts",
        "_env_file": None,
    }
    values.update(overrides)
    return Settings(**values)


@pytest.fixture
async def video_client(tmp_path: Path) -> AsyncIterator[AsyncClient]:
    application = create_app(
        settings_for(tmp_path),
        video_clock=lambda: TEST_NOW,
    )
    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://test",
    ) as client:
        yield client


def domain_payload() -> dict[str, object]:
    return {
        "name": "medical",
        "allowed_topics": ["sleep health"],
        "allowed_keywords": ["sleep", "health", "medical", "reviewed"],
        "blocked_keywords": ["casino", "crypto", "gambling"],
    }


def preview_payload(content_id: str = "sleep-preview-001") -> dict[str, object]:
    return {
        "profile_name": "medical",
        "content_id": content_id,
        "topic": "sleep health",
        "title": "Reviewed sleep health facts",
        "hook": "Safe medical videos begin with reviewed sleep facts.",
        "facts": [
            {
                "text": "This synthetic sleep fact has medical review approval.",
                "source_url": "https://example.invalid/reviewed-sleep-source",
                "approval_id": "fact-review-001",
            }
        ],
        "call_to_action": "Follow for reviewed medical education.",
        "target_duration_seconds": 1,
        "language": "en",
        "style": "vertical-explainer",
        "medical_review_approved": True,
    }


async def test_video_dashboard_and_assets_are_served(video_client: AsyncClient) -> None:
    page = await video_client.get("/video")
    css = await video_client.get("/assets/video.css")
    javascript = await video_client.get("/assets/video.js")

    assert page.status_code == 200
    assert "SELF-LEARNING VIDEO STUDIO" in page.text
    assert 'id="preview-form"' in page.text
    assert css.status_code == 200
    assert "--forest:" in css.text
    assert javascript.status_code == 200
    assert 'api("/v1/video/previews"' in javascript.text
    assert "media-src 'self'" in page.headers["content-security-policy"]


def test_video_dashboard_avoids_unsafe_browser_persistence_and_dom_sinks() -> None:
    html = (STATIC_DIRECTORY / "video.html").read_text(encoding="utf-8")
    javascript = (STATIC_DIRECTORY / "video.js").read_text(encoding="utf-8")
    stylesheet = (STATIC_DIRECTORY / "video.css").read_text(encoding="utf-8")

    assert "<style" not in html
    assert "<script>" not in html
    for prohibited in (
        "innerHTML",
        "outerHTML",
        "insertAdjacentHTML",
        "localStorage",
        "sessionStorage",
        "document.cookie",
    ):
        assert prohibited not in javascript
    assert "replaceChildren" in javascript
    assert ":focus-visible" in stylesheet
    assert "prefers-reduced-motion" in stylesheet
    assert "@media (max-width: 720px)" in stylesheet


async def test_operator_workflow_from_seed_to_learning(video_client: AsyncClient) -> None:
    saved = await video_client.put("/v1/video/domain", json=domain_payload())
    assert saved.status_code == 200

    imported = await video_client.post(
        "/v1/video/dataset",
        json={
            "schema_version": 1,
            "domain": domain_payload(),
            "videos": [
                {
                    "candidate_id": "sleep-seed-001",
                    "topic": "sleep health",
                    "title": "Reviewed sleep workflow",
                    "script": "Medical sleep health content needs review.",
                    "duration_seconds": 8,
                    "language": "en",
                    "style_tags": ["vertical-explainer"],
                }
            ],
        },
    )
    assert imported.status_code == 201
    assert imported.json()["imported"] == 1

    rejected_seed = await video_client.post(
        "/v1/video/videos/sleep-seed-001/approve",
        json={"medical_review_id": "review-001", "approved_by": "Synthetic Reviewer"},
    )
    assert rejected_seed.status_code == 409

    preview = await video_client.post("/v1/video/previews", json=preview_payload())
    assert preview.status_code == 201
    rendered = preview.json()
    assert rendered["preview_only"] is True
    assert rendered["publishable"] is False
    assert rendered["has_audio"] is False
    assert rendered["blocking_reasons"] == [
        "voice_track_missing",
        "operator_publish_approval_missing",
    ]

    video = await video_client.get(rendered["video_url"])
    storyboard = await video_client.get(rendered["storyboard_url"])
    assert video.status_code == 200
    assert video.headers["content-type"] == "video/mp4"
    assert b"ftyp" in video.content[:64]
    assert storyboard.status_code == 200
    assert "STORYBOARD PREVIEW" in storyboard.text
    assert "unsafe-inline" in storyboard.headers["content-security-policy"]

    approved = await video_client.post(
        "/v1/video/videos/sleep-preview-001/approve",
        json={"medical_review_id": "review-002", "approved_by": "Synthetic Reviewer"},
    )
    assert approved.status_code == 200

    scheduled = await video_client.post(
        "/v1/video/schedule/recommend",
        json={
            "profile_name": "medical",
            "current_posts_per_day": 1,
            "recent_performance": [],
        },
    )
    assert scheduled.status_code == 200
    assert scheduled.json()["reason"] == "scheduled"
    assert scheduled.json()["schedule"]["candidate_id"] == "sleep-preview-001"
    assert scheduled.json()["schedule"]["publish_at"] == "2026-08-05T09:00:00+00:00"

    insight = await video_client.post(
        "/v1/video/insights",
        json={
            "candidate_id": "sleep-preview-001",
            "platform": "youtube",
            "published_at": "2026-08-05T09:00:00Z",
            "impressions": 100,
            "views": 55,
            "average_watch_ratio": 0.72,
            "likes": 8,
            "comments": 2,
            "shares": 1,
        },
    )
    assert insight.status_code == 201

    status = await video_client.get("/v1/video/status")
    inventory = await video_client.get("/v1/video/videos")
    assert status.json()["counts"] == {"videos": 2, "insights": 1, "decisions": 1}
    assert status.json()["domain_profiles"] == ["medical"]
    states = {item["candidate_id"]: item["status"] for item in inventory.json()["videos"]}
    assert states == {
        "sleep-seed-001": "imported",
        "sleep-preview-001": "scheduled",
    }


async def test_preview_rejects_duplicates_and_out_of_domain_content(
    video_client: AsyncClient,
) -> None:
    await video_client.put("/v1/video/domain", json=domain_payload())
    first = await video_client.post("/v1/video/previews", json=preview_payload())
    duplicate = await video_client.post("/v1/video/previews", json=preview_payload())
    outside = preview_payload("outside-preview-001")
    outside["topic"] = "crypto"
    rejected = await video_client.post("/v1/video/previews", json=outside)

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert rejected.status_code == 422
    inventory = await video_client.get("/v1/video/videos")
    assert [item["candidate_id"] for item in inventory.json()["videos"]] == ["sleep-preview-001"]


async def test_operator_can_manage_durable_jobs(video_client: AsyncClient) -> None:
    request = {
        "kind": "mirror_artifact",
        "payload": {"artifact_key": "previews/video-1/preview.mp4"},
        "idempotency_key": "mirror:video-1",
        "max_attempts": 3,
    }
    created = await video_client.post("/v1/video/jobs", json=request)
    assert created.status_code == 201
    job = created.json()
    assert job["status"] == "queued"
    assert job["attempts"] == 0

    same = await video_client.post("/v1/video/jobs", json=request)
    loaded = await video_client.get(f"/v1/video/jobs/{job['job_id']}")
    counts = await video_client.get("/v1/video/jobs/counts")
    cancelled = await video_client.post(f"/v1/video/jobs/{job['job_id']}/cancel")

    assert same.json()["job_id"] == job["job_id"]
    assert loaded.json()["idempotency_key"] == "mirror:video-1"
    assert counts.json() == {"counts": {"queued": 1}}
    assert cancelled.json()["status"] == "cancelled"

    secret = await video_client.post(
        "/v1/video/jobs",
        json={
            "kind": "publish",
            "payload": {"access_token": "must-not-persist"},
            "idempotency_key": "publish:secret-test",
        },
    )
    assert secret.status_code == 422


async def test_failed_renderer_does_not_register_video(tmp_path: Path) -> None:
    class FailingRenderer(LocalVerticalVideoRenderer):
        def render(self, *args: object, **kwargs: object):
            raise RuntimeError("synthetic renderer failure")

    application = create_app(
        settings_for(tmp_path),
        video_clock=lambda: TEST_NOW,
        video_renderer_factory=FailingRenderer,
    )
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        await client.put("/v1/video/domain", json=domain_payload())
        failed = await client.post("/v1/video/previews", json=preview_payload())
        inventory = await client.get("/v1/video/videos")

    assert failed.status_code == 422
    assert inventory.json() == {"videos": []}


async def test_production_operator_endpoints_fail_closed(tmp_path: Path) -> None:
    settings = settings_for(
        tmp_path,
        environment="production",
        operator_api_key="synthetic-operator-secret",
    )
    application = create_app(settings, video_clock=lambda: TEST_NOW)
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        missing = await client.get("/v1/video/status")
        wrong = await client.get("/v1/video/videos", headers={"X-Operator-Key": "wrong"})
        authorized = await client.get(
            "/v1/video/status",
            headers={"X-Operator-Key": "synthetic-operator-secret"},
        )
        artifact = await client.get("/artifacts/private-preview.mp4")
        preview = await client.post(
            "/v1/video/previews",
            headers={"X-Operator-Key": "synthetic-operator-secret"},
            json=preview_payload(),
        )

    assert missing.status_code == 401
    assert wrong.status_code == 401
    assert authorized.status_code == 200
    assert artifact.status_code == 404
    assert preview.status_code == 503
