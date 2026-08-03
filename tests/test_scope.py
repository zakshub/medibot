import pytest
from pydantic import ValidationError

from medibot.models import MessageRoute
from medibot.scope import (
    EmptyScopeSignalDetector,
    KeywordScopeSignalDetector,
    ScopeSignalDecision,
    ScopeSignalStatus,
)


def detector() -> KeywordScopeSignalDetector:
    return KeywordScopeSignalDetector(
        unsupported_keywords={
            "synthetic outside scope": frozenset({"outside_scope"})
        },
        prohibited_keywords={
            "synthetic prohibited": frozenset({"disallowed_request"})
        },
        detector_version="synthetic-scope-v1",
    )


def test_empty_scope_detector_fails_closed() -> None:
    decision = EmptyScopeSignalDetector().evaluate("Synthetic message", "en-PK")

    assert decision.status == ScopeSignalStatus.UNAVAILABLE
    assert decision.route == MessageRoute.SERVICE_UNAVAILABLE
    assert decision.categories == frozenset()
    assert decision.detector_version == "unavailable"


def test_keyword_scope_detector_routes_unsupported() -> None:
    decision = detector().evaluate("A SYNTHETIC OUTSIDE SCOPE example.", "en-PK")

    assert decision.status == ScopeSignalStatus.UNSUPPORTED
    assert decision.route == MessageRoute.UNSUPPORTED
    assert decision.categories == frozenset({"outside_scope"})


def test_keyword_scope_detector_prioritizes_prohibited_match() -> None:
    decision = detector().evaluate(
        "Synthetic outside scope and synthetic prohibited example.",
        "en-PK",
    )

    assert decision.status == ScopeSignalStatus.PROHIBITED
    assert decision.route == MessageRoute.PROHIBITED
    assert decision.categories == frozenset({"disallowed_request"})
    assert "synthetic prohibited" not in decision.model_dump_json()


def test_keyword_scope_detector_allows_no_signal() -> None:
    decision = detector().evaluate("Synthetic ordinary example.", "en-PK")

    assert decision.status == ScopeSignalStatus.NO_SIGNAL
    assert decision.route == MessageRoute.INFORMATION
    assert decision.categories == frozenset()


def test_scope_decision_rejects_inconsistent_route() -> None:
    with pytest.raises(ValidationError, match="status and route are inconsistent"):
        ScopeSignalDecision(
            status=ScopeSignalStatus.UNSUPPORTED,
            route=MessageRoute.PROHIBITED,
            categories=frozenset({"outside_scope"}),
            detector_version="synthetic-scope-v1",
        )


def test_detected_scope_decision_requires_categories() -> None:
    with pytest.raises(ValidationError, match="requires bounded categories"):
        ScopeSignalDecision(
            status=ScopeSignalStatus.PROHIBITED,
            route=MessageRoute.PROHIBITED,
            detector_version="synthetic-scope-v1",
        )


def test_no_signal_scope_decision_rejects_categories() -> None:
    with pytest.raises(ValidationError, match="only valid for detected scope"):
        ScopeSignalDecision(
            status=ScopeSignalStatus.NO_SIGNAL,
            route=MessageRoute.INFORMATION,
            categories=frozenset({"unexpected"}),
            detector_version="synthetic-scope-v1",
        )


@pytest.mark.parametrize(
    "categories",
    [
        frozenset({"contains spaces"}),
        frozenset({"x" * 65}),
        frozenset(f"category_{index}" for index in range(17)),
    ],
)
def test_scope_categories_are_bounded(categories: frozenset[str]) -> None:
    with pytest.raises(ValidationError):
        ScopeSignalDecision(
            status=ScopeSignalStatus.UNSUPPORTED,
            route=MessageRoute.UNSUPPORTED,
            categories=categories,
            detector_version="synthetic-scope-v1",
        )
