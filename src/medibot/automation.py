"""Domain-safe automation planning that combines learning and anti-spam controls."""

from dataclasses import dataclass
from datetime import datetime

from medibot.learning import (
    ContentVariant,
    DailyFrequencyController,
    DailyPerformance,
    FrequencyDecision,
    LearningObservation,
    OnlineStrategyLearner,
    StrategyRecommendation,
)
from medibot.video_system import (
    DomainGuard,
    DomainProfile,
    ScheduleDecision,
    SchedulingPolicy,
    VideoCandidate,
)


@dataclass(frozen=True, slots=True)
class AutomationRecommendation:
    frequency: FrequencyDecision
    strategy: StrategyRecommendation | None
    schedule: ScheduleDecision | None
    reason: str


def duration_bucket(duration_seconds: float | None) -> str:
    if duration_seconds is None or duration_seconds <= 30:
        return "short"
    if duration_seconds <= 90:
        return "medium"
    return "long"


class AutomationPlanner:
    def __init__(
        self,
        *,
        learner: OnlineStrategyLearner | None = None,
        frequency: DailyFrequencyController | None = None,
        scheduling: SchedulingPolicy | None = None,
        default_hours: tuple[int, ...] = (9, 13, 18),
    ) -> None:
        if not default_hours or any(hour < 0 or hour > 23 for hour in default_hours):
            raise ValueError("default posting hours must be between 0 and 23")
        self.learner = learner or OnlineStrategyLearner()
        self.frequency = frequency or DailyFrequencyController()
        self.scheduling = scheduling or SchedulingPolicy()
        self.default_hours = tuple(sorted(set(default_hours)))

    def recommend(
        self,
        *,
        profile: DomainProfile,
        approved_candidates: list[VideoCandidate],
        observations: list[LearningObservation],
        existing_schedules: list[tuple[str, datetime]],
        daily_performance: list[DailyPerformance],
        current_posts_per_day: int,
        now: datetime,
    ) -> AutomationRecommendation:
        frequency = self.frequency.decide(current_posts_per_day, daily_performance)
        today = [
            (candidate_id, stamp)
            for candidate_id, stamp in existing_schedules
            if stamp.date() == now.date()
        ]
        if len(today) >= frequency.posts_per_day:
            return AutomationRecommendation(frequency, None, None, "daily_target_reached")

        guard = DomainGuard(profile)
        scheduled_ids = {candidate_id for candidate_id, _stamp in existing_schedules}
        candidates = [
            item
            for item in approved_candidates
            if item.candidate_id not in scheduled_ids and guard.evaluate(item)[0]
        ]
        if not candidates:
            return AutomationRecommendation(
                frequency, None, None, "no_unscheduled_approved_candidate"
            )

        observed_hours = {item.variant.posting_hour for item in observations}
        available_hours = sorted(set(self.default_hours).union(observed_hours))
        available_hours = [hour for hour in available_hours if hour >= now.hour]
        if not available_hours:
            return AutomationRecommendation(frequency, None, None, "no_posting_window_today")

        variants = [
            ContentVariant(
                candidate.topic,
                hour,
                candidate.style_tags[0] if candidate.style_tags else "default",
                duration_bucket(candidate.duration_seconds),
            )
            for candidate in candidates
            for hour in available_hours
        ]
        strategy = self.learner.recommend(variants, observations, profile)
        if strategy is None:
            return AutomationRecommendation(frequency, None, None, "no_domain_strategy")

        matching = [
            item
            for item in candidates
            if item.topic.casefold() == strategy.variant.topic.casefold()
            and (item.style_tags[0] if item.style_tags else "default")
            == strategy.variant.style
            and duration_bucket(item.duration_seconds) == strategy.variant.duration_bucket
        ]
        if not matching:
            return AutomationRecommendation(frequency, strategy, None, "no_matching_candidate")
        candidate = sorted(matching, key=lambda item: item.candidate_id)[0]

        publish_at = now.replace(
            hour=strategy.variant.posting_hour,
            minute=0,
            second=0,
            microsecond=0,
        )
        last_publish = max((stamp for _candidate_id, stamp in existing_schedules), default=None)
        if last_publish is not None:
            publish_at = max(publish_at, last_publish + self.scheduling.minimum_gap)
        if publish_at.date() != now.date():
            return AutomationRecommendation(
                frequency, strategy, None, "minimum_gap_defers_to_tomorrow"
            )

        schedule = ScheduleDecision(
            candidate.candidate_id,
            publish_at,
            strategy.score,
            (
                *strategy.reasons,
                f"frequency:{frequency.posts_per_day}",
                "approved_candidate_only",
                "duplicate_schedule_blocked",
            ),
        )
        return AutomationRecommendation(frequency, strategy, schedule, "scheduled")
