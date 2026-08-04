import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from medibot.dataset import DatasetManifest, DatasetManifestImporter
from medibot.video_store import VideoStore
from medibot.video_system import (
    DomainProfile,
    PerformanceInsight,
    ScheduleDecision,
    VideoCandidate,
)


def manifest_payload(source_path: str | None = None) -> dict[str, object]:
    video: dict[str, object] = {
        "candidate_id": "video-1",
        "topic": "sleep",
        "title": "Sleep health",
        "script": "Sleep health basics",
        "duration_seconds": 30,
        "style_tags": ["Short", " short "],
    }
    if source_path is not None:
        video["source_path"] = source_path
    return {
        "schema_version": 1,
        "domain": {
            "name": "medical",
            "allowed_topics": ["Sleep"],
            "allowed_keywords": ["Health", "Sleep"],
            "blocked_keywords": ["Casino"],
        },
        "videos": [video],
    }


def test_manifest_normalizes_and_converts_video(tmp_path: Path) -> None:
    asset = tmp_path / "sample.mp4"
    asset.write_bytes(b"synthetic-video")
    manifest = DatasetManifest.model_validate(manifest_payload("sample.mp4"))

    profile, videos = DatasetManifestImporter(tmp_path).convert(manifest)

    assert profile.allowed_topics == frozenset({"sleep"})
    assert videos[0].source_path == "sample.mp4"
    assert videos[0].asset_sha256 is not None
    assert videos[0].style_tags == ("short",)


def test_manifest_load_rejects_invalid_and_large_files(tmp_path: Path) -> None:
    valid = tmp_path / "manifest.json"
    valid.write_text(json.dumps(manifest_payload()), encoding="utf-8")
    assert DatasetManifestImporter.load(valid).schema_version == 1

    duplicate = manifest_payload()
    duplicate["videos"] = [duplicate["videos"][0], duplicate["videos"][0]]  # type: ignore[index]
    with pytest.raises(ValidationError, match="candidate IDs must be unique"):
        DatasetManifest.model_validate(duplicate)

    large = tmp_path / "large.json"
    large.write_bytes(b"x" * (5 * 1024 * 1024 + 1))
    with pytest.raises(ValueError, match="too large"):
        DatasetManifestImporter.load(large)


@pytest.mark.parametrize("source", ["../escape.mp4", "notes.txt", "missing.mp4"])
def test_manifest_rejects_unsafe_or_invalid_source(tmp_path: Path, source: str) -> None:
    if source == "notes.txt":
        (tmp_path / source).write_text("not video", encoding="utf-8")
    manifest = DatasetManifest.model_validate(manifest_payload(source))
    with pytest.raises(ValueError):
        DatasetManifestImporter(tmp_path).convert(manifest)


def test_video_store_persists_complete_learning_state(tmp_path: Path) -> None:
    store = VideoStore(tmp_path / "data" / "video.db")
    profile = DomainProfile("medical", frozenset({"sleep"}), frozenset({"sleep", "health"}))
    now = datetime(2026, 1, 1, 12, tzinfo=UTC)
    candidate = VideoCandidate(
        "video-1",
        "sleep",
        "Sleep health",
        "Sleep basics",
        duration_seconds=30,
        style_tags=("short",),
    )

    store.save_domain_profile(profile, updated_at=now)
    assert store.get_domain_profile("medical") == profile
    assert store.get_domain_profile("missing") is None
    assert store.register_candidates(profile, [candidate], imported_at=now) == 1
    assert store.list_candidates() == [candidate]
    assert store.list_candidates(status="imported") == [candidate]

    insight = PerformanceInsight("ignored", now, 100, 50, 0.75, 5, 2, 1)
    store.add_insight("video-1", "youtube", insight, collected_at=now)
    loaded = store.list_insights()
    assert loaded[0].topic == "sleep"
    assert loaded[0].views == 50

    decision = ScheduleDecision("video-1", now, 0.9, ("domain_verified",))
    store.record_schedule_decision(decision, created_at=now)
    assert store.list_publish_times() == [now]
    assert store.counts() == {"videos": 1, "insights": 1, "decisions": 1}

    with pytest.raises(ValueError, match="rendered, hash-verified"):
        store.approve_video(
            "video-1",
            medical_review_id="review-1",
            approved_by="reviewer",
            approved_at=now,
        )


def test_video_store_registration_is_atomic(tmp_path: Path) -> None:
    store = VideoStore(tmp_path / "video.db")
    profile = DomainProfile("medical", frozenset({"sleep"}), frozenset({"sleep"}))
    now = datetime(2026, 1, 1, tzinfo=UTC)
    items = [
        VideoCandidate("one", "sleep", "Sleep one", "Sleep advice"),
        VideoCandidate("two", "outside", "Sleep two", "Sleep advice"),
    ]
    with pytest.raises(ValueError, match="topic_outside_domain"):
        store.register_candidates(profile, items, imported_at=now)
    assert store.counts()["videos"] == 0


def test_store_rolls_back_database_errors(tmp_path: Path) -> None:
    store = VideoStore(tmp_path / "video.db")
    profile = DomainProfile("medical", frozenset({"sleep"}), frozenset({"sleep"}))
    now = datetime(2026, 1, 1, tzinfo=UTC)
    candidate = VideoCandidate("one", "sleep", "Sleep", "Sleep advice")
    store.register_candidates(profile, [candidate], imported_at=now)
    with pytest.raises(sqlite3.IntegrityError):
        store.register_candidates(profile, [candidate], imported_at=now)
    assert store.counts()["videos"] == 1


def test_render_approval_and_schedule_transitions_are_guarded(tmp_path: Path) -> None:
    store = VideoStore(tmp_path / "video.db")
    profile = DomainProfile("medical", frozenset({"sleep"}), frozenset({"sleep"}))
    now = datetime(2026, 1, 1, 8, tzinfo=UTC)
    candidate = VideoCandidate(
        "rendered-1",
        "sleep",
        "Sleep facts",
        "Sleep facts reviewed",
        source_path="previews/rendered-1/preview.mp4",
        duration_seconds=15,
        asset_sha256="a" * 64,
    )
    store.register_candidates(
        profile,
        [candidate],
        imported_at=now,
        initial_status="rendered",
    )

    store.approve_video(
        candidate.candidate_id,
        medical_review_id="review-1",
        approved_by="reviewer",
        approved_at=now,
    )
    assert store.list_candidates(status="approved") == [candidate]

    decision = ScheduleDecision(candidate.candidate_id, now, 0.8, ("reviewed",))
    store.reserve_schedule_decision(decision, created_at=now)
    assert store.list_candidates(status="scheduled") == [candidate]
    assert store.list_schedule_entries() == [(candidate.candidate_id, now)]

    with pytest.raises(ValueError, match="no longer available"):
        store.reserve_schedule_decision(decision, created_at=now)
    assert store.counts()["decisions"] == 1


def test_rendered_registration_requires_artifact_proof(tmp_path: Path) -> None:
    store = VideoStore(tmp_path / "video.db")
    profile = DomainProfile("medical", frozenset({"sleep"}), frozenset({"sleep"}))
    candidate = VideoCandidate("video-1", "sleep", "Sleep", "Sleep reviewed")

    with pytest.raises(ValueError, match="artifact path and SHA-256"):
        store.register_candidates(
            profile,
            [candidate],
            imported_at=datetime(2026, 1, 1, tzinfo=UTC),
            initial_status="rendered",
        )
