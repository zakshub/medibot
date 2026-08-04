"""Explainable online learning for content strategy and posting frequency."""

import math
from dataclasses import dataclass
from statistics import fmean

from medibot.video_system import DomainProfile


@dataclass(frozen=True, slots=True, order=True)
class ContentVariant:
    topic: str
    posting_hour: int
    style: str
    duration_bucket: str

    def __post_init__(self) -> None:
        if not 0 <= self.posting_hour <= 23:
            raise ValueError("posting hour must be between 0 and 23")
        if not self.topic.strip() or not self.style.strip() or not self.duration_bucket.strip():
            raise ValueError("variant fields cannot be blank")


@dataclass(frozen=True, slots=True)
class LearningObservation:
    variant: ContentVariant
    reward: float

    def __post_init__(self) -> None:
        if not 0 <= self.reward <= 1:
            raise ValueError("reward must be between zero and one")

    @classmethod
    def from_metrics(
        cls,
        variant: ContentVariant,
        *,
        impressions: int,
        views: int,
        average_watch_ratio: float,
        likes: int = 0,
        comments: int = 0,
        shares: int = 0,
    ) -> "LearningObservation":
        if min(impressions, views, likes, comments, shares) < 0:
            raise ValueError("performance metrics cannot be negative")
        view_rate = min(views / max(impressions, 1), 1.0)
        engagement = min((likes + 2 * comments + 3 * shares) / max(views, 1), 1.0)
        watch = min(max(average_watch_ratio, 0.0), 1.0)
        reward = 0.35 * view_rate + 0.4 * watch + 0.25 * engagement
        return cls(variant, reward)


@dataclass(frozen=True, slots=True)
class StrategyRecommendation:
    variant: ContentVariant
    score: float
    mean_reward: float
    observations: int
    confidence: float
    mode: str
    reasons: tuple[str, ...]


class OnlineStrategyLearner:
    def __init__(
        self,
        *,
        exploration_weight: float = 0.35,
        confidence_observations: int = 10,
    ) -> None:
        if not 0 <= exploration_weight <= 2:
            raise ValueError("exploration weight must be between zero and two")
        if confidence_observations < 1:
            raise ValueError("confidence observations must be positive")
        self.exploration_weight = exploration_weight
        self.confidence_observations = confidence_observations

    def recommend(
        self,
        variants: list[ContentVariant],
        observations: list[LearningObservation],
        profile: DomainProfile,
    ) -> StrategyRecommendation | None:
        allowed_topics = {topic.casefold() for topic in profile.allowed_topics}
        eligible = sorted(
            {variant for variant in variants if variant.topic.casefold() in allowed_topics}
        )
        if not eligible:
            return None

        rewards: dict[ContentVariant, list[float]] = {variant: [] for variant in eligible}
        for observation in observations:
            if observation.variant in rewards:
                rewards[observation.variant].append(observation.reward)

        total = sum(len(values) for values in rewards.values())
        scored: list[tuple[float, ContentVariant, float, int]] = []
        for variant, values in rewards.items():
            count = len(values)
            mean = fmean(values) if values else 0.0
            if count == 0:
                score = 1.0 + self.exploration_weight
            else:
                bonus = self.exploration_weight * math.sqrt(math.log(total + 1) / count)
                score = mean + bonus
            scored.append((score, variant, mean, count))

        score, variant, mean, count = min(
            scored,
            key=lambda item: (
                -item[0],
                item[1].posting_hour,
                item[1].topic,
                item[1].style,
                item[1].duration_bucket,
            ),
        )
        mode = "explore" if count < self.confidence_observations else "exploit"
        confidence = min(count / self.confidence_observations, 1.0)
        reasons = (
            "domain_allowlist_enforced",
            "unseen_variant_exploration" if count == 0 else "ucb_performance_score",
            f"observation_count:{count}",
        )
        return StrategyRecommendation(variant, score, mean, count, confidence, mode, reasons)


@dataclass(frozen=True, slots=True)
class DailyPerformance:
    posts: int
    mean_reward: float
    spam_or_policy_incidents: int = 0

    def __post_init__(self) -> None:
        if not 0 <= self.posts <= 5:
            raise ValueError("daily posts must be between zero and five")
        if not 0 <= self.mean_reward <= 1:
            raise ValueError("daily reward must be between zero and one")
        if self.spam_or_policy_incidents < 0:
            raise ValueError("incident count cannot be negative")


@dataclass(frozen=True, slots=True)
class FrequencyDecision:
    posts_per_day: int
    previous_posts_per_day: int
    reason: str
    evidence_days: int


class DailyFrequencyController:
    def __init__(self, *, minimum: int = 1, maximum: int = 5, evidence_days: int = 3) -> None:
        if not 1 <= minimum <= maximum <= 5:
            raise ValueError("frequency limits must satisfy 1 <= minimum <= maximum <= 5")
        if evidence_days < 1:
            raise ValueError("evidence days must be positive")
        self.minimum = minimum
        self.maximum = maximum
        self.evidence_days = evidence_days

    def decide(
        self,
        current_posts_per_day: int,
        recent: list[DailyPerformance],
    ) -> FrequencyDecision:
        if not self.minimum <= current_posts_per_day <= self.maximum:
            raise ValueError("current frequency is outside configured limits")
        window = recent[-self.evidence_days :]
        if len(window) < self.evidence_days:
            target = min(current_posts_per_day, self.minimum)
            return FrequencyDecision(
                target, current_posts_per_day, "insufficient_evidence_safe_minimum", len(window)
            )

        if any(day.spam_or_policy_incidents for day in window):
            target = max(self.minimum, current_posts_per_day - 1)
            reason = "policy_or_spam_incident_decrease"
        else:
            mean_reward = fmean(day.mean_reward for day in window)
            if mean_reward >= 0.6:
                target = min(self.maximum, current_posts_per_day + 1)
                reason = "sustained_high_reward_increase"
            elif mean_reward < 0.25:
                target = max(self.minimum, current_posts_per_day - 1)
                reason = "sustained_low_reward_decrease"
            else:
                target = current_posts_per_day
                reason = "stable_reward_hold"
        return FrequencyDecision(target, current_posts_per_day, reason, len(window))
