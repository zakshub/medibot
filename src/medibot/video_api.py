"""Operator API for the self-learning medical video system."""

import hmac
import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.responses import FileResponse
from fastapi.security import APIKeyHeader
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from medibot.artifact_store import LocalArtifactStore
from medibot.automation import AutomationPlanner
from medibot.config import Settings
from medibot.dataset import DatasetManifest, DatasetManifestImporter
from medibot.generation import (
    ApprovedFact,
    ContentBrief,
    ContentGenerationPipeline,
)
from medibot.learning import DailyPerformance
from medibot.media import LocalVerticalVideoRenderer
from medibot.video_store import VideoStore
from medibot.video_system import (
    DomainGuard,
    DomainProfile,
    PerformanceInsight,
    VideoCandidate,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class DomainUpdate(StrictModel):
    name: str = Field(min_length=1, max_length=100)
    allowed_topics: list[str] = Field(min_length=1, max_length=500)
    allowed_keywords: list[str] = Field(min_length=1, max_length=2_000)
    blocked_keywords: list[str] = Field(default_factory=list, max_length=2_000)


class ApprovedFactInput(StrictModel):
    text: str = Field(min_length=1, max_length=2_000)
    source_url: str = Field(pattern=r"^https?://", max_length=2_000)
    approval_id: str = Field(min_length=1, max_length=200)


class PreviewCreate(StrictModel):
    profile_name: str = Field(min_length=1, max_length=100)
    content_id: str = Field(pattern=r"^[A-Za-z0-9._-]+$", max_length=128)
    topic: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=300)
    hook: str = Field(min_length=1, max_length=1_000)
    facts: list[ApprovedFactInput] = Field(min_length=1, max_length=20)
    call_to_action: str = Field(min_length=1, max_length=1_000)
    target_duration_seconds: int = Field(default=6, ge=1, le=30)
    language: str = Field(default="en", pattern=r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
    style: str = Field(default="vertical-explainer", min_length=1, max_length=100)
    medical_review_approved: bool


class VideoApproval(StrictModel):
    medical_review_id: str = Field(min_length=1, max_length=200)
    approved_by: str = Field(min_length=1, max_length=200)


class InsightCreate(StrictModel):
    candidate_id: str = Field(min_length=1, max_length=128)
    platform: str = Field(pattern=r"^(youtube|instagram|facebook|x)$")
    published_at: AwareDatetime
    impressions: int = Field(ge=0)
    views: int = Field(ge=0)
    average_watch_ratio: float = Field(ge=0, le=1)
    likes: int = Field(default=0, ge=0)
    comments: int = Field(default=0, ge=0)
    shares: int = Field(default=0, ge=0)


class DailyPerformanceInput(StrictModel):
    posts: int = Field(ge=0, le=5)
    mean_reward: float = Field(ge=0, le=1)
    spam_or_policy_incidents: int = Field(default=0, ge=0)


class ScheduleCreate(StrictModel):
    profile_name: str = Field(min_length=1, max_length=100)
    current_posts_per_day: int = Field(default=1, ge=1, le=5)
    recent_performance: list[DailyPerformanceInput] = Field(default_factory=list, max_length=30)


def create_video_router(
    settings: Settings,
    store: VideoStore,
    artifacts: LocalArtifactStore,
    *,
    clock: Callable[[], datetime] | None = None,
    renderer_factory: Callable[[], LocalVerticalVideoRenderer] | None = None,
) -> APIRouter:
    now = clock or (lambda: datetime.now(UTC))
    make_renderer = renderer_factory or LocalVerticalVideoRenderer
    operator_key_header = APIKeyHeader(name="X-Operator-Key", auto_error=False)

    def authorize(
        supplied: Annotated[str | None, Security(operator_key_header)],
    ) -> None:
        expected = settings.operator_api_key
        if expected is None and settings.environment in {"local", "test"}:
            return
        if expected is None:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "Operator authentication is not configured.",
            )
        if supplied is None or not hmac.compare_digest(supplied, expected.get_secret_value()):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid operator credentials.")

    router = APIRouter(
        prefix="/v1/video",
        tags=["video automation"],
        dependencies=[Depends(authorize)],
    )

    @router.get("/status")
    def video_status() -> dict[str, object]:
        counts = store.counts()
        inventory = store.list_video_summaries()
        profiles = store.list_domain_profile_names()
        return {
            "status": "operational_local" if settings.environment != "production" else "configured",
            "product": "domain-locked self-learning medical video generator",
            "counts": counts,
            "domain_profiles": profiles,
            "videos_by_status": {
                name: sum(item["status"] == name for item in inventory)
                for name in (
                    "imported",
                    "rendered",
                    "approved",
                    "scheduled",
                    "published",
                    "failed",
                )
            },
            "capabilities": {
                "dataset_import": True,
                "domain_lock": True,
                "html_storyboard": True,
                "local_mp4_preview": True,
                "voice_generation": False,
                "adaptive_learning": True,
                "anti_spam_scheduler": True,
                "platform_adapters": ["youtube", "instagram", "facebook", "x"],
                "live_platform_credentials": False,
            },
            "implementation_percent": 65,
            "production_ready": False,
            "blocking_reasons": [
                "voice_provider_not_configured",
                "operator_platform_credentials_not_configured",
                "platform_app_approvals_not_verified",
            ],
        }

    @router.put("/domain")
    def update_domain(payload: DomainUpdate) -> dict[str, object]:
        profile = DomainProfile(
            payload.name,
            frozenset(item.casefold() for item in payload.allowed_topics),
            frozenset(item.casefold() for item in payload.allowed_keywords),
            frozenset(item.casefold() for item in payload.blocked_keywords),
        )
        try:
            store.save_domain_profile(profile, updated_at=now())
        except ValueError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
        return {"saved": True, "profile": payload.name}

    @router.post("/dataset", status_code=status.HTTP_201_CREATED)
    def import_dataset(payload: DatasetManifest) -> dict[str, object]:
        importer = DatasetManifestImporter(settings.dataset_directory)
        try:
            profile, candidates = importer.convert(payload)
            store.save_domain_profile(profile, updated_at=now())
            imported = store.register_candidates(profile, candidates, imported_at=now())
        except sqlite3.IntegrityError as exc:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Dataset contains existing records."
            ) from exc
        except (OSError, ValueError) as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
        return {"imported": imported, "profile": profile.name}

    @router.get("/videos")
    def list_videos() -> dict[str, object]:
        return {"videos": store.list_video_summaries()}

    @router.post("/previews", status_code=status.HTTP_201_CREATED)
    def create_preview(payload: PreviewCreate) -> dict[str, object]:
        if settings.environment not in {"local", "test"}:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "Local preview rendering is disabled outside local/test environments.",
            )
        profile = store.get_domain_profile(payload.profile_name)
        if profile is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Domain profile was not found.")
        if store.get_candidate(payload.content_id) is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Content ID already exists.")

        brief = ContentBrief(
            content_id=payload.content_id,
            topic=payload.topic,
            title=payload.title,
            hook=payload.hook,
            facts=tuple(
                ApprovedFact(item.text, item.source_url, item.approval_id) for item in payload.facts
            ),
            call_to_action=payload.call_to_action,
            target_duration_seconds=payload.target_duration_seconds,
            language=payload.language,
            style=payload.style,
            medical_review_approved=payload.medical_review_approved,
        )
        pipeline = ContentGenerationPipeline(
            DomainGuard(profile),
            artifacts,
        )
        try:
            generated = pipeline.generate(brief, generated_at=now())
            output_path = artifacts.root / "previews" / payload.content_id / "preview.mp4"
            rendered = make_renderer().render(
                generated.package,
                duration_seconds=payload.target_duration_seconds,
                output_path=output_path,
            )
            relative_path = output_path.relative_to(artifacts.root).as_posix()
            candidate = VideoCandidate(
                payload.content_id,
                payload.topic,
                payload.title,
                generated.package.narration,
                source_path=relative_path,
                duration_seconds=payload.target_duration_seconds,
                language=payload.language,
                style_tags=(payload.style,),
                asset_sha256=rendered.sha256,
            )
            store.register_candidates(
                profile,
                [candidate],
                imported_at=now(),
                initial_status="rendered",
            )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status.HTTP_409_CONFLICT, "Content already exists.") from exc
        except (OSError, RuntimeError, ValueError) as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
        return {
            "content_id": payload.content_id,
            "status": "rendered_preview",
            "preview_only": True,
            "storyboard_url": f"/v1/video/previews/{payload.content_id}/storyboard",
            "video_url": f"/artifacts/previews/{payload.content_id}/preview.mp4",
            "sha256": rendered.sha256,
            "size_bytes": rendered.size_bytes,
            "has_audio": rendered.has_audio,
            "publishable": rendered.publishable,
            "blocking_reasons": rendered.blocking_reasons,
        }

    @router.get("/previews/{content_id}/storyboard", response_class=FileResponse)
    def preview_storyboard(content_id: str) -> FileResponse:
        if not content_id.replace("-", "").replace("_", "").replace(".", "").isalnum():
            raise HTTPException(status.HTTP_404_NOT_FOUND)
        path = artifacts.root / "previews" / content_id / "index.html"
        if not path.is_file():
            raise HTTPException(status.HTTP_404_NOT_FOUND)
        return FileResponse(
            path,
            media_type="text/html",
            headers={
                "Content-Security-Policy": (
                    "default-src 'none'; style-src 'unsafe-inline'; "
                    "base-uri 'none'; frame-ancestors 'none'"
                )
            },
        )

    @router.post("/videos/{candidate_id}/approve")
    def approve_video(
        candidate_id: str,
        payload: VideoApproval,
    ) -> dict[str, object]:
        try:
            store.approve_video(
                candidate_id,
                medical_review_id=payload.medical_review_id,
                approved_by=payload.approved_by,
                approved_at=datetime.now(UTC),
            )
        except KeyError as exc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Video was not found.") from exc
        except ValueError as exc:
            raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
        return {"candidate_id": candidate_id, "status": "approved"}

    @router.post("/insights", status_code=status.HTTP_201_CREATED)
    def add_insight(payload: InsightCreate) -> dict[str, object]:
        candidate = store.get_candidate(payload.candidate_id)
        if candidate is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Video was not found.")
        insight = PerformanceInsight(
            candidate.topic,
            payload.published_at,
            payload.impressions,
            payload.views,
            payload.average_watch_ratio,
            payload.likes,
            payload.comments,
            payload.shares,
        )
        try:
            store.add_insight(
                payload.candidate_id,
                payload.platform,
                insight,
                collected_at=now(),
            )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(status.HTTP_409_CONFLICT, "Insight already exists.") from exc
        return {"saved": True, "candidate_id": payload.candidate_id}

    @router.post("/schedule/recommend")
    def recommend_schedule(
        payload: ScheduleCreate,
    ) -> dict[str, object]:
        profile = store.get_domain_profile(payload.profile_name)
        if profile is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Domain profile was not found.")
        planner = AutomationPlanner()
        recommendation = planner.recommend(
            profile=profile,
            approved_candidates=store.list_candidates(status="approved"),
            observations=store.list_learning_observations(),
            existing_schedules=store.list_schedule_entries(),
            daily_performance=[
                DailyPerformance(
                    item.posts,
                    item.mean_reward,
                    item.spam_or_policy_incidents,
                )
                for item in payload.recent_performance
            ],
            current_posts_per_day=payload.current_posts_per_day,
            now=now(),
        )
        if recommendation.schedule is not None:
            try:
                store.reserve_schedule_decision(recommendation.schedule, created_at=now())
            except (sqlite3.IntegrityError, ValueError) as exc:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "The selected video was already scheduled.",
                ) from exc
        return {
            "reason": recommendation.reason,
            "frequency": {
                "posts_per_day": recommendation.frequency.posts_per_day,
                "previous_posts_per_day": recommendation.frequency.previous_posts_per_day,
                "reason": recommendation.frequency.reason,
                "evidence_days": recommendation.frequency.evidence_days,
            },
            "strategy": (
                {
                    "topic": recommendation.strategy.variant.topic,
                    "posting_hour": recommendation.strategy.variant.posting_hour,
                    "style": recommendation.strategy.variant.style,
                    "duration_bucket": recommendation.strategy.variant.duration_bucket,
                    "score": recommendation.strategy.score,
                    "confidence": recommendation.strategy.confidence,
                    "mode": recommendation.strategy.mode,
                    "reasons": recommendation.strategy.reasons,
                }
                if recommendation.strategy
                else None
            ),
            "schedule": (
                {
                    "candidate_id": recommendation.schedule.candidate_id,
                    "publish_at": recommendation.schedule.publish_at.isoformat(),
                    "score": recommendation.schedule.score,
                    "reasons": recommendation.schedule.reasons,
                }
                if recommendation.schedule
                else None
            ),
        }

    return router
