import io
from pathlib import Path

import pytest
from pydantic import ValidationError

from medibot.evaluation import (
    EmergencyEvaluationCase,
    EmergencyEvaluationDataset,
    EvaluationFailure,
    EvaluationReviewStatus,
    build_reference_detector,
    evaluate_emergency_detector,
    load_evaluation_dataset,
    main,
)
from medibot.routing import EmergencySignalStatus

EVALUATION_DIRECTORY = Path(__file__).resolve().parents[1] / "evaluations"
BASELINE_DATASET = EVALUATION_DIRECTORY / "emergency_signal_baseline.v1.json"
CHALLENGE_DATASET = EVALUATION_DIRECTORY / "emergency_signal_challenge.v1.json"


def load_baseline() -> EmergencyEvaluationDataset:
    return load_evaluation_dataset(BASELINE_DATASET)


def test_baseline_dataset_passes_reference_detector_thresholds() -> None:
    report = evaluate_emergency_detector(load_baseline(), build_reference_detector())

    assert report.meets_thresholds is True
    assert report.review_status == EvaluationReviewStatus.ENGINEERING_ONLY
    assert report.metrics.model_dump() == {
        "total_cases": 6,
        "passed_cases": 6,
        "failed_cases": 0,
        "emergency_cases": 3,
        "non_emergency_cases": 3,
        "true_positives": 3,
        "false_negatives": 0,
        "true_negatives": 3,
        "false_positives": 0,
        "unavailable_cases": 0,
        "case_pass_rate": 1.0,
        "emergency_recall": 1.0,
        "false_positive_rate": 0.0,
        "unavailable_rate": 0.0,
    }
    combined = next(
        result for result in report.results if result.case_id == "baseline.positive.combined"
    )
    assert combined.actual_categories == ("immediate_danger", "time_sensitive_help")


def test_challenge_dataset_exposes_reference_detector_limitations() -> None:
    dataset = load_evaluation_dataset(CHALLENGE_DATASET)
    report = evaluate_emergency_detector(dataset, build_reference_detector())

    assert report.meets_thresholds is False
    assert report.metrics.case_pass_rate == 0.25
    assert report.metrics.emergency_recall == 0.0
    assert report.metrics.false_positive_rate == 0.5
    assert report.metrics.false_negatives == 2
    assert report.metrics.false_positives == 1


def test_report_excludes_synthetic_message_text() -> None:
    dataset = load_baseline()
    report_json = evaluate_emergency_detector(
        dataset,
        build_reference_detector(),
    ).model_dump_json()

    for case in dataset.cases:
        assert case.message not in report_json
    assert "case_id" in report_json


def test_detector_exception_becomes_bounded_unavailable_result() -> None:
    class ExplodingDetector:
        def evaluate(self, message: str, locale: str):
            raise RuntimeError(f"private detector detail: {message}")

    dataset = load_baseline()
    report = evaluate_emergency_detector(dataset, ExplodingDetector())

    assert report.meets_thresholds is False
    assert report.metrics.unavailable_rate == 1.0
    assert report.results[0].failures == (
        EvaluationFailure.DETECTOR_EXCEPTION,
        EvaluationFailure.STATUS_MISMATCH,
        EvaluationFailure.CATEGORY_MISMATCH,
        EvaluationFailure.DETECTOR_VERSION_MISMATCH,
    )
    report_json = report.model_dump_json()
    assert "private detector detail" not in report_json
    assert dataset.cases[0].message not in report_json


def test_detector_version_mismatch_fails_every_case() -> None:
    detector = build_reference_detector()
    dataset = load_baseline().model_copy(
        update={"expected_detector_version": "different-v2"}
    )

    report = evaluate_emergency_detector(dataset, detector)

    assert report.meets_thresholds is False
    assert report.metrics.passed_cases == 0
    assert all(
        EvaluationFailure.DETECTOR_VERSION_MISMATCH in result.failures
        for result in report.results
    )


def test_case_contract_requires_categories_only_for_possible_emergency() -> None:
    with pytest.raises(ValidationError, match="requires expected categories"):
        EmergencyEvaluationCase(
            case_id="invalid.positive",
            synthetic=True,
            locale="en-PK",
            message="Synthetic positive example.",
            expected_status=EmergencySignalStatus.POSSIBLE_EMERGENCY,
        )

    with pytest.raises(ValidationError, match="only valid for possible emergencies"):
        EmergencyEvaluationCase(
            case_id="invalid.negative",
            synthetic=True,
            locale="en-PK",
            message="Synthetic negative example.",
            expected_status=EmergencySignalStatus.NO_SIGNAL,
            expected_categories=frozenset({"unexpected_category"}),
        )


def test_dataset_rejects_duplicate_or_incomplete_ground_truth() -> None:
    baseline = load_baseline()

    with pytest.raises(ValidationError, match="case IDs must be unique"):
        EmergencyEvaluationDataset.model_validate(
            baseline.model_dump() | {"cases": [baseline.cases[0], baseline.cases[0]]}
        )

    positive_cases = [
        case
        for case in baseline.cases
        if case.expected_status == EmergencySignalStatus.POSSIBLE_EMERGENCY
    ]
    with pytest.raises(ValidationError, match="requires possible-emergency and no-signal"):
        EmergencyEvaluationDataset.model_validate(
            baseline.model_dump() | {"cases": positive_cases}
        )


def test_dataset_rejects_unavailable_ground_truth() -> None:
    baseline = load_baseline()
    unavailable_case = baseline.cases[3].model_copy(
        update={"expected_status": EmergencySignalStatus.UNAVAILABLE}
    )

    with pytest.raises(ValidationError, match="not ground truth"):
        EmergencyEvaluationDataset.model_validate(
            baseline.model_dump() | {"cases": [baseline.cases[0], unavailable_case]}
        )


def test_clinically_reviewed_dataset_requires_named_reviewers() -> None:
    baseline = load_baseline()

    with pytest.raises(ValidationError, match="requires named reviewers"):
        EmergencyEvaluationDataset.model_validate(
            baseline.model_dump()
            | {
                "review_status": EvaluationReviewStatus.CLINICALLY_REVIEWED,
                "reviewers": [],
            }
        )


@pytest.mark.parametrize(
    ("dataset_path", "expected_exit_code", "expected_verdict"),
    [
        (BASELINE_DATASET, 0, '"meets_thresholds": true'),
        (CHALLENGE_DATASET, 1, '"meets_thresholds": false'),
    ],
)
def test_cli_returns_threshold_exit_code(
    dataset_path: Path,
    expected_exit_code: int,
    expected_verdict: str,
) -> None:
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = main([str(dataset_path)], stdout=stdout, stderr=stderr)

    assert exit_code == expected_exit_code
    assert expected_verdict in stdout.getvalue()
    assert stderr.getvalue() == ""


def test_cli_sanitizes_dataset_load_failure() -> None:
    invalid_dataset = EVALUATION_DIRECTORY / "private-missing-dataset.json"
    assert invalid_dataset.exists() is False
    stdout = io.StringIO()
    stderr = io.StringIO()

    exit_code = main([str(invalid_dataset)], stdout=stdout, stderr=stderr)

    assert exit_code == 2
    assert stdout.getvalue() == ""
    assert stderr.getvalue() == "Emergency evaluation could not load the dataset.\n"
    assert invalid_dataset.name not in stderr.getvalue()
