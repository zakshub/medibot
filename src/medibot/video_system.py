"""Domain-locked dataset and adaptive scheduling foundation."""

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from statistics import fmean

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True, slots=True)
class DomainProfile:
    name: str
    allowed_topics: frozenset[str]
    allowed_keywords: frozenset[str]
    blocked_keywords: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class VideoCandidate:
    candidate_id: str
    topic: str
    title: str
    script: str


@dataclass(frozen=True, slots=True)
class PerformanceInsight:
    topic: str
    published_at: datetime
    impressions: int
    views: int
    average_watch_ratio: float
    likes: int = 0
    comments: int = 0
    shares: int = 0


@dataclass(frozen=True, slots=True)
class SchedulingPolicy:
    minimum_daily_posts: int = 1
    maximum_daily_posts: int = 5
    minimum_gap: timedelta = timedelta(hours=3)

    def __post_init__(self) -> None:
        if not 1 <= self.minimum_daily_posts <= self.maximum_daily_posts <= 5:
            raise ValueError("daily limits must satisfy 1 <= minimum <= maximum <= 5")
        if self.minimum_gap < timedelta(hours=1):
            raise ValueError("minimum gap must be at least one hour")


@dataclass(frozen=True, slots=True)
class ScheduleDecision:
    candidate_id: str
    publish_at: datetime
    score: float
    reasons: tuple[str, ...]


class DomainGuard:
    def __init__(self, profile: DomainProfile) -> None:
        if not profile.allowed_topics or not profile.allowed_keywords:
            raise ValueError("domain profile requires allowed topics and keywords")
        self.profile = profile

    def evaluate(self, candidate: VideoCandidate) -> tuple[bool, str]:
        tokens = frozenset(
            _TOKEN_PATTERN.findall(f"{candidate.title} {candidate.script}".casefold())
        )
        blocked = tokens.intersection(term.casefold() for term in self.profile.blocked_keywords)
        if blocked:
            return False, "blocked_term"
        if candidate.topic.strip().casefold() not in {
            topic.casefold() for topic in self.profile.allowed_topics
        }:
            return False, "topic_outside_domain"
        if not tokens.intersection(term.casefold() for term in self.profile.allowed_keywords):
            return False, "no_domain_evidence"
        return True, "domain_match"

    def require_allowed(self, candidate: VideoCandidate) -> None:
        allowed, reason = self.evaluate(candidate)
        if not allowed:
            raise ValueError(f"candidate rejected by domain guard: {reason}")


class DatasetCatalog:
    def __init__(self, guard: DomainGuard) -> None:
        self._guard = guard
        self._records: dict[str, tuple[VideoCandidate, str, datetime]] = {}
        self._hashes: set[str] = set()

    @staticmethod
    def content_hash(candidate: VideoCandidate) -> str:
        normalized = "\n".join(
            (
                candidate.topic.strip().casefold(),
                candidate.title.strip().casefold(),
                " ".join(candidate.script.split()).casefold(),
            )
        )
        return sha256(normalized.encode()).hexdigest()

    def register(
        self, candidate: VideoCandidate, *, imported_at: datetime | None = None
    ) -> tuple[VideoCandidate, str, datetime]:
        self._guard.require_allowed(candidate)
        if candidate.candidate_id in self._records:
            raise ValueError("candidate id already exists")
        digest = self.content_hash(candidate)
        if digest in self._hashes:
            raise ValueError("duplicate video content")
        record = (candidate, digest, imported_at or datetime.now(UTC))
        self._records[candidate.candidate_id] = record
        self._hashes.add(digest)
        return record

    def records(self) -> tuple[tuple[VideoCandidate, str, datetime], ...]:
        return tuple(self._records.values())


class AdaptiveScheduler:
    def __init__(self, guard: DomainGuard, policy: SchedulingPolicy | None = None) -> None:
        self._guard = guard
        self.policy = policy or SchedulingPolicy()

    @staticmethod
    def _score(item: PerformanceInsight) -> float:
        view_rate = item.views / max(item.impressions, 1)
        engagement = (item.likes + 2 * item.comments + 3 * item.shares) / max(item.views, 1)
        watch = min(max(item.average_watch_ratio, 0.0), 1.0)
        return 0.35 * view_rate + 0.4 * watch + 0.25 * engagement

    def recommend(
        self,
        candidates: list[VideoCandidate],
        insights: list[PerformanceInsight],
        existing_publish_times: list[datetime],
        *,
        now: datetime,
    ) -> ScheduleDecision | None:
        if sum(stamp.date() == now.date() for stamp in existing_publish_times) >= (
            self.policy.maximum_daily_posts
        ):
            return None
        last = max(existing_publish_times, default=None)
        earliest = now if last is None else max(now, last + self.policy.minimum_gap)
        if earliest.date() != now.date():
            return None
        eligible = [item for item in candidates if self._guard.evaluate(item)[0]]
        if not eligible:
            return None

        by_topic: dict[str, list[float]] = defaultdict(list)
        by_hour: dict[int, list[float]] = defaultdict(list)
        for insight in insights:
            score = self._score(insight)
            by_topic[insight.topic.casefold()].append(score)
            by_hour[insight.published_at.hour].append(score)
        topic_scores = {topic: fmean(scores) for topic, scores in by_topic.items()}
        chosen = max(
            eligible,
            key=lambda item: (topic_scores.get(item.topic.casefold(), 0.0), item.candidate_id),
        )
        hours = [hour for hour in by_hour if hour >= earliest.hour]
        if hours:
            hour = max(hours, key=lambda value: fmean(by_hour[value]))
            planned = earliest.replace(hour=hour, minute=0, second=0, microsecond=0)
            publish_at, timing = max(earliest, planned), "historical_best_hour"
        else:
            publish_at, timing = earliest, "safe_fallback_time"
        return ScheduleDecision(
            chosen.candidate_id,
            publish_at,
            topic_scores.get(chosen.topic.casefold(), 0.0),
            ("domain_verified", "topic_performance_score", timing),
        )

