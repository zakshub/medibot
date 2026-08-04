from datetime import UTC, datetime
from pathlib import Path

import pytest

from medibot.artifact_store import LocalArtifactStore
from medibot.generation import (
    ApprovedFact,
    ContentBrief,
    ContentGenerationPipeline,
    HtmlStoryboardRenderer,
    ReviewedTemplateScriptGenerator,
    ScriptPackage,
    brief_to_dict,
)
from medibot.video_system import DomainGuard, DomainProfile


def approved_brief(**overrides: object) -> ContentBrief:
    values: dict[str, object] = {
        "content_id": "sleep-001",
        "topic": "sleep",
        "title": "Sleep health",
        "hook": "Sleep supports health.",
        "facts": (
            ApprovedFact(
                "A consistent sleep schedule supports sleep health.",
                "https://example.test/sleep",
                "approval-1",
            ),
        ),
        "call_to_action": "Follow for reviewed sleep health education.",
        "target_duration_seconds": 30,
        "medical_review_approved": True,
    }
    values.update(overrides)
    return ContentBrief(**values)  # type: ignore[arg-type]


def guard() -> DomainGuard:
    return DomainGuard(
        DomainProfile(
            "medical",
            frozenset({"sleep"}),
            frozenset({"sleep", "health", "schedule"}),
            frozenset({"casino"}),
        )
    )


def test_artifact_store_is_atomic_and_path_locked(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path / "artifacts")
    result = store.write_text("preview/item.txt", "content", content_type="text/plain")
    assert result.path.read_text(encoding="utf-8") == "content"
    assert result.size_bytes == 7
    assert len(result.sha256) == 64

    for key in ("../escape.txt", "/absolute.txt", "bad folder/file.txt"):
        with pytest.raises(ValueError, match="artifact key"):
            store.write_text(key, "bad", content_type="text/plain")


def test_reviewed_script_requires_approval_facts_and_sources() -> None:
    generator = ReviewedTemplateScriptGenerator()
    with pytest.raises(ValueError, match="medical review"):
        generator.generate(approved_brief(medical_review_approved=False))
    with pytest.raises(ValueError, match="approved fact"):
        generator.generate(approved_brief(facts=()))
    with pytest.raises(ValueError, match="approval ID"):
        generator.generate(
            approved_brief(facts=(ApprovedFact("Sleep health", "file://local", ""),))
        )


def test_generation_writes_safe_visible_preview(tmp_path: Path) -> None:
    pipeline = ContentGenerationPipeline(guard(), LocalArtifactStore(tmp_path))
    now = datetime(2026, 1, 1, tzinfo=UTC)

    result = pipeline.generate(approved_brief(title="Sleep <health>"), generated_at=now)

    assert result.preview_only is True
    assert result.generated_at == now
    assert result.script.path.is_file()
    storyboard = result.storyboard.path.read_text(encoding="utf-8")
    assert '"preview_only": true' in storyboard
    preview = result.preview.path.read_text(encoding="utf-8")
    assert "Sleep &lt;health&gt;" in preview
    assert "Preview only" in preview
    assert "<health>" not in preview


def test_generation_rechecks_domain_after_script_generation(tmp_path: Path) -> None:
    pipeline = ContentGenerationPipeline(guard(), LocalArtifactStore(tmp_path))
    with pytest.raises(ValueError, match="topic_outside_domain"):
        pipeline.generate(
            approved_brief(topic="crypto"),
            generated_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
    with pytest.raises(ValueError, match="blocked_term"):
        pipeline.generate(
            approved_brief(hook="Casino sleep offer"),
            generated_at=datetime(2026, 1, 1, tzinfo=UTC),
        )


def test_renderer_escapes_scenes_sources_and_serializes_brief() -> None:
    package = ScriptPackage(
        "one",
        "<title>",
        "safe",
        ("<script>alert(1)</script>",),
        ("https://example.test/?x=<tag>",),
        ("approval",),
    )
    rendered = HtmlStoryboardRenderer().render(package)
    assert "<script>alert(1)</script>" not in rendered
    assert "&lt;script&gt;" in rendered
    assert "&lt;tag&gt;" in rendered
    assert brief_to_dict(approved_brief())["content_id"] == "sleep-001"

