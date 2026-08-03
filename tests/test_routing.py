import pytest
from pydantic import ValidationError

from medibot.models import MessageRoute
from medibot.routing import (
    EmergencySignalDecision,
    EmergencySignalStatus,
    EmptyEmergencySignalDetector,
    KeywordEmergencySignalDetector,
)


def test_empty_emergency_signal_detector_fails_closed() -> None:
    decision = EmptyEmergencySignalDetector().evaluate(
        "synthetic message",
        "en-PK",
    )

    assert decision.status == EmergencySignalStatus.UNAVAILABLE
    assert decision.route == MessageRoute.SERVICE_UNAVAILABLE
    assert decision.categories == frozenset()
    assert decision.detector_version == "unavailable"


def test_keyword_emergency_signal_detector_flags_bounded_categories() -> None:
    detector = KeywordEmergencySignalDetector(
        {
            "urgent help": frozenset({"time_sensitive_help"}),
            "danger phrase": frozenset({"immediate_danger"}),
        },
        detector_version="synthetic-v1",
    )

    decision = detector.evaluate(
        "Please send URGENT HELP for this synthetic test.",
        "en-PK",
    )

    assert decision.status == EmergencySignalStatus.POSSIBLE_EMERGENCY
    assert decision.route == MessageRoute.EMERGENCY
    assert decision.categories == frozenset({"time_sensitive_help"})
    assert decision.detector_version == "synthetic-v1"


def test_keyword_emergency_signal_detector_combines_categories_without_raw_text() -> None:
    detector = KeywordEmergencySignalDetector(
        {
            "urgent help": frozenset({"time_sensitive_help"}),
            "danger phrase": frozenset({"immediate_danger"}),
        },
        detector_version="synthetic-v1",
    )

    decision = detector.evaluate(
        "Synthetic urgent help and danger phrase.",
        "en-PK",
    )

    assert decision.categories == frozenset(
        {"time_sensitive_help", "immediate_danger"}
    )
    assert "urgent help" not in decision.model_dump_json()
    assert "danger phrase" not in decision.model_dump_json()


def test_keyword_emergency_signal_detector_allows_no_signal() -> None:
    detector = KeywordEmergencySignalDetector(
        {"urgent help": frozenset({"time_sensitive_help"})},
        detector_version="synthetic-v1",
    )

    decision = detector.evaluate("Synthetic ordinary message.", "en-PK")

    assert decision.status == EmergencySignalStatus.NO_SIGNAL
    assert decision.route == MessageRoute.INFORMATION
    assert decision.categories == frozenset()


def test_emergency_signal_decision_rejects_inconsistent_route() -> None:
    with pytest.raises(ValidationError, match="status and route are inconsistent"):
        EmergencySignalDecision(
            status=EmergencySignalStatus.POSSIBLE_EMERGENCY,
            route=MessageRoute.INFORMATION,
            categories=frozenset({"synthetic_category"}),
            detector_version="synthetic-v1",
        )


def test_possible_emergency_decision_requires_bounded_category() -> None:
    with pytest.raises(ValidationError, match="requires bounded categories"):
        EmergencySignalDecision(
            status=EmergencySignalStatus.POSSIBLE_EMERGENCY,
            route=MessageRoute.EMERGENCY,
            detector_version="synthetic-v1",
        )


def test_non_emergency_decision_rejects_categories() -> None:
    with pytest.raises(ValidationError, match="only valid for possible emergency"):
        EmergencySignalDecision(
            status=EmergencySignalStatus.NO_SIGNAL,
            route=MessageRoute.INFORMATION,
            categories=frozenset({"synthetic_category"}),
            detector_version="synthetic-v1",
        )


@pytest.mark.parametrize(
    "categories",
    [
        frozenset({"contains spaces"}),
        frozenset({"x" * 65}),
        frozenset(f"category_{index}" for index in range(17)),
    ],
)
def test_emergency_categories_are_bounded(categories: frozenset[str]) -> None:
    with pytest.raises(ValidationError):
        EmergencySignalDecision(
            status=EmergencySignalStatus.POSSIBLE_EMERGENCY,
            route=MessageRoute.EMERGENCY,
            categories=categories,
            detector_version="synthetic-v1",
        )
