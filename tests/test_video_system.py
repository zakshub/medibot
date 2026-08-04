from datetime import UTC, datetime, timedelta

import pytest

from medibot.video_system import (
    AdaptiveScheduler,
    DatasetCatalog,
    DomainGuard,
    DomainProfile,
    PerformanceInsight,
    SchedulingPolicy,
    VideoCandidate,
)


@pytest.fixture
def guard() -> DomainGuard:
    return DomainGuard(
        DomainProfile(
            "medical",
            frozenset({"nutrition", "sleep"}),
            frozenset({"nutrition", "sleep", "health"}),
            frozenset({"casino"}),
        )
    )


def test_guard_is_domain_locked(guard: DomainGuard) -> None:
    assert guard.evaluate(VideoCandidate("1", "sleep", "Sleep health", "Sleep tips"))[0]
    assert guard.evaluate(VideoCandidate("2", "crypto", "Sleep", "Sleep token"))[1] == (
        "topic_outside_domain"
    )
    assert guard.evaluate(VideoCandidate("3", "sleep", "Update", "General tips"))[1] == (
        "no_domain_evidence"
    )
    assert guard.evaluate(VideoCandidate("4", "sleep", "Sleep casino", "Sleep"))[1] == (
        "blocked_term"
    )


def test_guard_requires_allowlists() -> None:
    with pytest.raises(ValueError, match="requires allowed"):
        DomainGuard(DomainProfile("empty", frozenset(), frozenset()))


def test_catalog_rejects_duplicate_and_outside_domain(guard: DomainGuard) -> None:
    catalog = DatasetCatalog(guard)
    item = VideoCandidate("1", "nutrition", "Nutrition health", "Nutrition basics")
    imported = datetime(2026, 1, 1, tzinfo=UTC)
    assert catalog.register(item, imported_at=imported)[2] == imported
    assert len(catalog.records()) == 1
    with pytest.raises(ValueError, match="duplicate video content"):
        catalog.register(
            VideoCandidate("2", "NUTRITION", "nutrition HEALTH", " nutrition  basics ")
        )
    with pytest.raises(ValueError, match="candidate id"):
        catalog.register(VideoCandidate("1", "sleep", "Sleep health", "Sleep basics"))
    with pytest.raises(ValueError, match="topic_outside_domain"):
        catalog.register(VideoCandidate("3", "crypto", "Health", "Health token"))


def test_scheduler_learns_topic_and_hour(guard: DomainGuard) -> None:
    scheduler = AdaptiveScheduler(guard)
    now = datetime(2026, 1, 2, 8, tzinfo=UTC)
    candidates = [
        VideoCandidate("sleep", "sleep", "Sleep health", "Sleep basics"),
        VideoCandidate("food", "nutrition", "Nutrition health", "Nutrition basics"),
    ]
    insights = [
        PerformanceInsight("sleep", now.replace(hour=10), 1000, 200, 0.2),
        PerformanceInsight("nutrition", now.replace(hour=15), 1000, 700, 0.8, shares=30),
    ]
    decision = scheduler.recommend(candidates, insights, [], now=now)
    assert decision is not None
    assert decision.candidate_id == "food"
    assert decision.publish_at.hour == 15
    assert "historical_best_hour" in decision.reasons


def test_scheduler_enforces_cap_gap_domain_and_policy(guard: DomainGuard) -> None:
    now = datetime(2026, 1, 2, 12, tzinfo=UTC)
    candidate = VideoCandidate("sleep", "sleep", "Sleep health", "Sleep basics")
    capped = AdaptiveScheduler(guard, SchedulingPolicy(maximum_daily_posts=2))
    assert capped.recommend([candidate], [], [now - timedelta(hours=4), now], now=now) is None

    decision = AdaptiveScheduler(guard).recommend(
        [candidate], [], [now - timedelta(minutes=30)], now=now
    )
    assert decision is not None
    assert decision.publish_at == now + timedelta(hours=2, minutes=30)
    assert (
        AdaptiveScheduler(guard).recommend(
            [VideoCandidate("x", "crypto", "Crypto", "Trading")], [], [], now=now
        )
        is None
    )
    with pytest.raises(ValueError, match="daily limits"):
        SchedulingPolicy(maximum_daily_posts=6)
    with pytest.raises(ValueError, match="at least one hour"):
        SchedulingPolicy(minimum_gap=timedelta(minutes=30))

