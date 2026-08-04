import pytest

from medibot.learning import (
    ContentVariant,
    DailyFrequencyController,
    DailyPerformance,
    LearningObservation,
    OnlineStrategyLearner,
)
from medibot.video_system import DomainProfile


def profile() -> DomainProfile:
    return DomainProfile(
        "medical",
        frozenset({"sleep", "nutrition"}),
        frozenset({"sleep", "nutrition", "health"}),
    )


def variants() -> list[ContentVariant]:
    return [
        ContentVariant("sleep", 9, "explainer", "short"),
        ContentVariant("sleep", 18, "story", "medium"),
        ContentVariant("crypto", 12, "hype", "short"),
    ]


def test_reward_is_bounded_and_weighted() -> None:
    variant = variants()[0]
    result = LearningObservation.from_metrics(
        variant,
        impressions=100,
        views=80,
        average_watch_ratio=0.75,
        likes=10,
        comments=3,
        shares=2,
    )
    assert 0 < result.reward <= 1
    saturated = LearningObservation.from_metrics(
        variant,
        impressions=1,
        views=10,
        average_watch_ratio=4,
        likes=100,
    )
    assert saturated.reward == 1
    with pytest.raises(ValueError, match="negative"):
        LearningObservation.from_metrics(
            variant, impressions=-1, views=0, average_watch_ratio=0
        )
    with pytest.raises(ValueError, match="between zero"):
        LearningObservation(variant, 1.1)


def test_learner_explores_unseen_allowed_variant() -> None:
    first, second, _outside = variants()
    observations = [LearningObservation(first, 0.9)]

    result = OnlineStrategyLearner().recommend(variants(), observations, profile())

    assert result is not None
    assert result.variant == second
    assert result.mode == "explore"
    assert result.observations == 0
    assert "domain_allowlist_enforced" in result.reasons


def test_learner_exploits_after_enough_evidence_and_excludes_domain() -> None:
    first, second, outside = variants()
    observations = [
        *(LearningObservation(first, 0.9) for _ in range(4)),
        *(LearningObservation(second, 0.1) for _ in range(4)),
        *(LearningObservation(outside, 1.0) for _ in range(50)),
    ]
    learner = OnlineStrategyLearner(exploration_weight=0, confidence_observations=4)

    result = learner.recommend(variants(), observations, profile())

    assert result is not None
    assert result.variant == first
    assert result.mode == "exploit"
    assert result.confidence == 1
    assert result.mean_reward == pytest.approx(0.9)
    assert learner.recommend([outside], observations, profile()) is None


def test_learner_and_variant_configuration_is_bounded() -> None:
    with pytest.raises(ValueError, match="posting hour"):
        ContentVariant("sleep", 24, "one", "short")
    with pytest.raises(ValueError, match="blank"):
        ContentVariant("sleep", 1, "", "short")
    with pytest.raises(ValueError, match="exploration"):
        OnlineStrategyLearner(exploration_weight=3)
    with pytest.raises(ValueError, match="positive"):
        OnlineStrategyLearner(confidence_observations=0)


def test_frequency_cold_start_increase_hold_and_decrease() -> None:
    controller = DailyFrequencyController(evidence_days=3)
    cold = controller.decide(3, [DailyPerformance(1, 0.8)])
    assert cold.posts_per_day == 1
    assert cold.reason == "insufficient_evidence_safe_minimum"

    high = controller.decide(2, [DailyPerformance(2, 0.8)] * 3)
    assert high.posts_per_day == 3
    assert high.reason == "sustained_high_reward_increase"

    stable = controller.decide(3, [DailyPerformance(3, 0.4)] * 3)
    assert stable.posts_per_day == 3

    low = controller.decide(3, [DailyPerformance(3, 0.1)] * 3)
    assert low.posts_per_day == 2

    incident = controller.decide(
        2,
        [DailyPerformance(2, 0.9), DailyPerformance(2, 0.9, 1), DailyPerformance(2, 0.9)],
    )
    assert incident.posts_per_day == 1
    assert incident.reason == "policy_or_spam_incident_decrease"


def test_frequency_never_leaves_limits_or_accepts_bad_data() -> None:
    controller = DailyFrequencyController()
    assert controller.decide(5, [DailyPerformance(5, 1)] * 3).posts_per_day == 5
    assert controller.decide(1, [DailyPerformance(1, 0)] * 3).posts_per_day == 1
    with pytest.raises(ValueError, match="current frequency"):
        controller.decide(0, [])
    with pytest.raises(ValueError, match="frequency limits"):
        DailyFrequencyController(maximum=6)
    with pytest.raises(ValueError, match="daily posts"):
        DailyPerformance(6, 0.5)
    with pytest.raises(ValueError, match="daily reward"):
        DailyPerformance(1, 2)
    with pytest.raises(ValueError, match="incident"):
        DailyPerformance(1, 0.5, -1)

