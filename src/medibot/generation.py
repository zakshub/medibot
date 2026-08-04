"""Provenance-gated content planning and browser-preview generation."""

import html
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Protocol

from medibot.artifact_store import LocalArtifactStore, StoredArtifact
from medibot.video_system import DomainGuard, VideoCandidate


@dataclass(frozen=True, slots=True)
class ApprovedFact:
    text: str
    source_url: str
    approval_id: str


@dataclass(frozen=True, slots=True)
class ContentBrief:
    content_id: str
    topic: str
    title: str
    hook: str
    facts: tuple[ApprovedFact, ...]
    call_to_action: str
    target_duration_seconds: int
    language: str = "en"
    style: str = "vertical-explainer"
    medical_review_approved: bool = False


@dataclass(frozen=True, slots=True)
class ScriptPackage:
    content_id: str
    title: str
    narration: str
    scenes: tuple[str, ...]
    source_urls: tuple[str, ...]
    approval_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GenerationResult:
    content_id: str
    package: ScriptPackage
    script: StoredArtifact
    storyboard: StoredArtifact
    preview: StoredArtifact
    preview_only: bool
    generated_at: datetime


class ScriptGenerator(Protocol):
    def generate(self, brief: ContentBrief) -> ScriptPackage: ...


class ReviewedTemplateScriptGenerator:
    def generate(self, brief: ContentBrief) -> ScriptPackage:
        if not brief.medical_review_approved:
            raise ValueError("medical review approval is required")
        if not brief.facts:
            raise ValueError("at least one approved fact is required")
        if any(
            not fact.approval_id.strip() or not fact.source_url.startswith(("https://", "http://"))
            for fact in brief.facts
        ):
            raise ValueError("every fact requires an approval ID and HTTP source")

        scenes = (brief.hook, *(fact.text for fact in brief.facts), brief.call_to_action)
        narration = " ".join(part.strip() for part in scenes if part.strip())
        return ScriptPackage(
            content_id=brief.content_id,
            title=brief.title,
            narration=narration,
            scenes=tuple(part.strip() for part in scenes if part.strip()),
            source_urls=tuple(dict.fromkeys(fact.source_url for fact in brief.facts)),
            approval_ids=tuple(dict.fromkeys(fact.approval_id for fact in brief.facts)),
        )


class HtmlStoryboardRenderer:
    def render(self, package: ScriptPackage) -> str:
        scene_markup = "".join(
            f'<article class="scene"><span>{index:02d}</span><p>{html.escape(scene)}</p></article>'
            for index, scene in enumerate(package.scenes, start=1)
        )
        source_markup = "".join(f"<li>{html.escape(source)}</li>" for source in package.source_urls)
        return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(package.title)} - preview</title>
<style>
:root {{ color-scheme: dark; font-family: Georgia, serif; }}
body {{ margin: 0; background: #081c1b; color: #f4eddb; }}
main {{ width: min(92vw, 540px); margin: 32px auto; }}
header {{ border-left: 8px solid #e5b94b; padding: 12px 20px; }}
.scene {{ min-height: 160px; margin: 18px 0; padding: 24px; display: grid;
  grid-template-columns: 48px 1fr; align-items: center; background: #123331;
  border-radius: 4px; box-shadow: 8px 8px 0 #e5b94b; }}
.scene span {{ color: #e5b94b; font: 700 18px monospace; }}
.scene p {{ font-size: 24px; line-height: 1.3; }}
footer {{ margin-top: 32px; color: #b9cbc6; font: 14px sans-serif; }}
</style>
</head>
<body><main><header><small>STORYBOARD PREVIEW</small>
<h1>{html.escape(package.title)}</h1></header>{scene_markup}
<footer><strong>Sources</strong><ul>{source_markup}</ul>
<p>Preview only. Not rendered or approved for publishing.</p></footer></main></body>
</html>"""


class ContentGenerationPipeline:
    def __init__(
        self,
        guard: DomainGuard,
        artifacts: LocalArtifactStore,
        script_generator: ScriptGenerator | None = None,
        renderer: HtmlStoryboardRenderer | None = None,
    ) -> None:
        self.guard = guard
        self.artifacts = artifacts
        self.script_generator = script_generator or ReviewedTemplateScriptGenerator()
        self.renderer = renderer or HtmlStoryboardRenderer()

    def generate(self, brief: ContentBrief, *, generated_at: datetime) -> GenerationResult:
        package = self.script_generator.generate(brief)
        candidate = VideoCandidate(
            candidate_id=brief.content_id,
            topic=brief.topic,
            title=brief.title,
            script=package.narration,
            duration_seconds=brief.target_duration_seconds,
            language=brief.language,
            style_tags=(brief.style,),
        )
        self.guard.require_allowed(candidate)

        prefix = f"previews/{brief.content_id}"
        script = self.artifacts.write_text(
            f"{prefix}/script.txt", package.narration, content_type="text/plain"
        )
        storyboard_payload = json.dumps(
            {
                "content_id": package.content_id,
                "title": package.title,
                "scenes": list(package.scenes),
                "sources": list(package.source_urls),
                "approval_ids": list(package.approval_ids),
                "target_duration_seconds": brief.target_duration_seconds,
                "preview_only": True,
            },
            indent=2,
            sort_keys=True,
        )
        storyboard = self.artifacts.write_text(
            f"{prefix}/storyboard.json",
            storyboard_payload,
            content_type="application/json",
        )
        preview = self.artifacts.write_text(
            f"{prefix}/index.html",
            self.renderer.render(package),
            content_type="text/html",
        )
        return GenerationResult(
            brief.content_id,
            package,
            script,
            storyboard,
            preview,
            True,
            generated_at,
        )


def brief_to_dict(brief: ContentBrief) -> dict[str, object]:
    return asdict(brief)
