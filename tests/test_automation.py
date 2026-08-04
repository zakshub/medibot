from datetime import UTC, datetime, timedelta

import pytest

from medibot.automation import AutomationPlanner, duration_bucket
from medibot.learning import DailyPerformance, LearningObservation
from medibot.video_system import DomainProfile, SchedulingPolicy, VideoCandidate


def profile() -> DomainProfile:
    return DomainProfile(
        "medical",
        frozenset({"sleep"}),
        frozenset({"sleep", "health"}),
    )


def candidates() -> list[VideoCandidate]:
    return [
        VideoCandidate(
            "sleep-1",
            "sleep",
            "Sleep health",
            "Sleep health facts",
            duration_seconds=25,
            style_tags=("explainer",),
        ),
        VideoCandidate(
            "sleep-2",
            "sleep",
            "Sleep schedule",
            "Sleep schedule health",
            duration_seconds=60,
            style_tags=("story",),
        ),
        VideoCandidate("crypto", "crypto", "Crypto", "Crypto trade"),
    ]


def test_planner_produces_domain_locked_explainable_schedule() -> None:
    now = datetime(2026, 1, 1, 8, tzinfo=UTC)
    planner = AutomationPlanner(default_hours=(9,))

    result = planner.recommend(
        profile=profile(),
        approved_candidates=candidates(),
        observations=[],
        existing_schedules=[],
        daily_performance=[],
        current_posts_per_day=1,
        now=now,
    )

    assert result.reason == "scheduled"
    assert result.schedule is not None
    assert result.schedule.candidate_id in {"sleep-1", "sleep-2"}
    assert result.schedule.publish_at.hour == 9
    assert "approved_candidate_only" in result.schedule.reasons
    assert result.frequency.posts_per_day == 1


def test_planner_blocks_daily_target_duplicate_and_missing_candidates() -> None:
    now = datetime(2026, 1, 1, 8, tzinfo=UTC)
    planner = AutomationPlanner(default_hours=(9,))
    common = {
        "profile": profile(),
        "observations": [],
        "daily_performance": [],
        "current_posts_per_day": 1,
        "now": now,
    }
    reached = planner.recommend(
        approved_candidates=candidates(),
        existing_schedules=[("other", now)],
        **common,
    )
    assert reached.reason == "daily_target_reached"

    no_candidate = planner.recommend(
        approved_candidates=[candidates()[0]],
        existing_schedules=[("sleep-1", now - timedelta(days=1))],
        **common,
    )
    assert no_candidate.reason == "no_unscheduled_approved_candidate"


def test_planner_respects_posting_window_and_minimum_gap() -> None:
    now = datetime(2026, 1, 1, 20, tzinfo=UTC)
    closed = AutomationPlanner(default_hours=(9, 18)).recommend(
        profile=profile(),
        approved_candidates=candidates(),
        observations=[],
        existing_schedules=[],
        daily_performance=[],
        current_posts_per_day=1,
        now=now,
    )
    assert closed.reason == "no_posting_window_today"

    now = datetime(2026, 1, 1, 21, tzinfo=UTC)
    deferred = AutomationPlanner(
        default_hours=(22,),
        scheduling=SchedulingPolicy(minimum_gap=timedelta(hours=3)),
    ).recommend(
        profile=profile(),
        approved_candidates=candidates(),
        observations=[],
        existing_schedules=[("old", now)],
        daily_performance=[DailyPerformance(1, 0.8)] * 3,
        current_posts_per_day=2,
        now=now,
    )
    assert deferred.reason == "minimum_gap_defers_to_tomorrow"


def test_planner_uses_observation_hours_and_learned_variant() -> None:
    now = datetime(2026, 1, 1, 8, tzinfo=UTC)
    variants_planner = AutomationPlanner(default_hours=(9,))
    initial = variants_planner.recommend(
        profile=profile(),
        approved_candidates=candidates(),
        observations=[],
        existing_schedules=[],
        daily_performance=[],
        current_posts_per_day=1,
        now=now,
    )
    assert initial.strategy is not None
    observed_variant = initial.strategy.variant
    observation = LearningObservation(observed_variant, 0.9)

    result = variants_planner.recommend(
        profile=profile(),
        approved_candidates=candidates(),
        observations=[observation],
        existing_schedules=[],
        daily_performance=[],
        current_posts_per_day=1,
        now=now,
    )
    assert result.strategy is not None
    assert result.strategy.variant.topic == "sleep"


def test_duration_buckets_and_configuration() -> None:
    assert duration_bucket(None) == "short"
    assert duration_bucket(30) == "short"
    assert duration_bucket(31) == "medium"
    assert duration_bucket(91) == "long"
    with pytest.raises(ValueError, match="posting hours"):
        AutomationPlanner(default_hours=())
    with pytest.raises(ValueError, match="posting hours"):
        AutomationPlanner(default_hours=(24,))

