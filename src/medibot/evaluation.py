import argparse
import sys
from collections.abc import Sequence
from enum import StrEnum
from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from medibot.routing import (
    EmergencyCategory,
    EmergencySignalDecision,
    EmergencySignalDetector,
    EmergencySignalStatus,
    KeywordEmergencySignalDetector,
)

REFERENCE_DETECTOR_VERSION = "synthetic-reference-v1"
REFERENCE_KEYWORD_CATEGORIES = {
    "synthetic urgent help": frozenset({"time_sensitive_help"}),
    "synthetic danger phrase": frozenset({"immediate_danger"}),
}


class EvaluationReviewStatus(StrEnum):
    ENGINEERING_ONLY = "engineering_only"
    CLINICALLY_REVIEWED = "clinically_reviewed"


class EvaluationFailure(StrEnum):
    STATUS_MISMATCH = "status_mismatch"
    CATEGORY_MISMATCH = "category_mismatch"
    DETECTOR_VERSION_MISMATCH = "detector_version_mismatch"
    DETECTOR_EXCEPTION = "detector_exception"


class EmergencyEvaluationThresholds(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    min_case_pass_rate: float = Field(default=1.0, ge=0.0, le=1.0)
    min_emergency_recall: float = Field(default=1.0, ge=0.0, le=1.0)
    max_false_positive_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    max_unavailable_rate: float = Field(default=0.0, ge=0.0, le=1.0)


class EmergencyEvaluationCase(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )

    case_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{2,99}$")
    synthetic: Literal[True]
    locale: str = Field(pattern=r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
    message: str = Field(min_length=1, max_length=4_000)
    expected_status: EmergencySignalStatus
    expected_categories: frozenset[EmergencyCategory] = Field(
        default_factory=frozenset,
        max_length=16,
    )

    @model_validator(mode="after")
    def validate_expected_categories(self) -> "EmergencyEvaluationCase":
        if (
            self.expected_status == EmergencySignalStatus.POSSIBLE_EMERGENCY
            and not self.expected_categories
        ):
            raise ValueError("possible emergency case requires expected categories")
        if (
            self.expected_status != EmergencySignalStatus.POSSIBLE_EMERGENCY
            and self.expected_categories
        ):
            raise ValueError("expected categories are only valid for possible emergencies")
        return self


class EmergencyEvaluationDataset(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )

    dataset_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{2,99}$")
    version: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
    expected_detector_version: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z0-9._-]+$",
    )
    synthetic: Literal[True]
    owner: str = Field(min_length=1, max_length=200)
    review_status: EvaluationReviewStatus
    reviewers: tuple[str, ...] = Field(default_factory=tuple, max_length=50)
    source_description: str = Field(min_length=1, max_length=1_000)
    intended_use: str = Field(min_length=1, max_length=1_000)
    prohibited_uses: tuple[str, ...] = Field(min_length=1, max_length=50)
    known_gaps: tuple[str, ...] = Field(min_length=1, max_length=50)
    thresholds: EmergencyEvaluationThresholds = Field(
        default_factory=EmergencyEvaluationThresholds
    )
    cases: tuple[EmergencyEvaluationCase, ...] = Field(min_length=2, max_length=10_000)

    @model_validator(mode="after")
    def validate_dataset_shape(self) -> "EmergencyEvaluationDataset":
        case_ids = [case.case_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("evaluation case IDs must be unique")

        statuses = {case.expected_status for case in self.cases}
        if EmergencySignalStatus.UNAVAILABLE in statuses:
            raise ValueError("unavailable is a detector outcome, not ground truth")
        required = {
            EmergencySignalStatus.NO_SIGNAL,
            EmergencySignalStatus.POSSIBLE_EMERGENCY,
        }
        if not required.issubset(statuses):
            raise ValueError("dataset requires possible-emergency and no-signal cases")
        if (
            self.review_status == EvaluationReviewStatus.CLINICALLY_REVIEWED
            and not self.reviewers
        ):
            raise ValueError("clinically reviewed dataset requires named reviewers")
        return self


class EmergencyEvaluationCaseResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str
    passed: bool
    expected_status: EmergencySignalStatus
    actual_status: EmergencySignalStatus
    expected_categories: tuple[EmergencyCategory, ...]
    actual_categories: tuple[EmergencyCategory, ...]
    detector_version: str
    failures: tuple[EvaluationFailure, ...] = Field(default_factory=tuple)


class EmergencyEvaluationMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    total_cases: int
    passed_cases: int
    failed_cases: int
    emergency_cases: int
    non_emergency_cases: int
    true_positives: int
    false_negatives: int
    true_negatives: int
    false_positives: int
    unavailable_cases: int
    case_pass_rate: float
    emergency_recall: float
    false_positive_rate: float
    unavailable_rate: float


class EmergencyEvaluationReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    dataset_id: str
    dataset_version: str
    expected_detector_version: str
    review_status: EvaluationReviewStatus
    thresholds: EmergencyEvaluationThresholds
    metrics: EmergencyEvaluationMetrics
    meets_thresholds: bool
    results: tuple[EmergencyEvaluationCaseResult, ...]


class EvaluationOutput(Protocol):
    def write(self, value: str) -> object: ...


def load_evaluation_dataset(path: Path) -> EmergencyEvaluationDataset:
    return EmergencyEvaluationDataset.model_validate_json(path.read_text(encoding="utf-8"))


def build_reference_detector() -> KeywordEmergencySignalDetector:
    return KeywordEmergencySignalDetector(
        REFERENCE_KEYWORD_CATEGORIES,
        detector_version=REFERENCE_DETECTOR_VERSION,
    )


def evaluate_emergency_detector(
    dataset: EmergencyEvaluationDataset,
    detector: EmergencySignalDetector,
) -> EmergencyEvaluationReport:
    results = tuple(_evaluate_case(dataset, detector, case) for case in dataset.cases)
    metrics = _calculate_metrics(results)
    thresholds = dataset.thresholds
    meets_thresholds = (
        metrics.case_pass_rate >= thresholds.min_case_pass_rate
        and metrics.emergency_recall >= thresholds.min_emergency_recall
        and metrics.false_positive_rate <= thresholds.max_false_positive_rate
        and metrics.unavailable_rate <= thresholds.max_unavailable_rate
    )
    return EmergencyEvaluationReport(
        dataset_id=dataset.dataset_id,
        dataset_version=dataset.version,
        expected_detector_version=dataset.expected_detector_version,
        review_status=dataset.review_status,
        thresholds=thresholds,
        metrics=metrics,
        meets_thresholds=meets_thresholds,
        results=results,
    )


def _evaluate_case(
    dataset: EmergencyEvaluationDataset,
    detector: EmergencySignalDetector,
    case: EmergencyEvaluationCase,
) -> EmergencyEvaluationCaseResult:
    failures: list[EvaluationFailure] = []
    try:
        decision = detector.evaluate(case.message, case.locale)
    except Exception:
        decision = EmergencySignalDecision(
            status=EmergencySignalStatus.UNAVAILABLE,
            route="service_unavailable",
            detector_version="unavailable",
        )
        failures.append(EvaluationFailure.DETECTOR_EXCEPTION)

    if decision.status != case.expected_status:
        failures.append(EvaluationFailure.STATUS_MISMATCH)
    if decision.categories != case.expected_categories:
        failures.append(EvaluationFailure.CATEGORY_MISMATCH)
    if decision.detector_version != dataset.expected_detector_version:
        failures.append(EvaluationFailure.DETECTOR_VERSION_MISMATCH)

    return EmergencyEvaluationCaseResult(
        case_id=case.case_id,
        passed=not failures,
        expected_status=case.expected_status,
        actual_status=decision.status,
        expected_categories=tuple(sorted(case.expected_categories)),
        actual_categories=tuple(sorted(decision.categories)),
        detector_version=decision.detector_version,
        failures=tuple(failures),
    )


def _calculate_metrics(
    results: tuple[EmergencyEvaluationCaseResult, ...],
) -> EmergencyEvaluationMetrics:
    emergency_cases = sum(
        result.expected_status == EmergencySignalStatus.POSSIBLE_EMERGENCY
        for result in results
    )
    non_emergency_cases = sum(
        result.expected_status == EmergencySignalStatus.NO_SIGNAL for result in results
    )
    true_positives = sum(
        result.expected_status == EmergencySignalStatus.POSSIBLE_EMERGENCY
        and result.actual_status == EmergencySignalStatus.POSSIBLE_EMERGENCY
        for result in results
    )
    false_negatives = emergency_cases - true_positives
    false_positives = sum(
        result.expected_status == EmergencySignalStatus.NO_SIGNAL
        and result.actual_status == EmergencySignalStatus.POSSIBLE_EMERGENCY
        for result in results
    )
    true_negatives = sum(
        result.expected_status == EmergencySignalStatus.NO_SIGNAL
        and result.actual_status == EmergencySignalStatus.NO_SIGNAL
        for result in results
    )
    unavailable_cases = sum(
        result.actual_status == EmergencySignalStatus.UNAVAILABLE for result in results
    )
    passed_cases = sum(result.passed for result in results)
    total_cases = len(results)

    return EmergencyEvaluationMetrics(
        total_cases=total_cases,
        passed_cases=passed_cases,
        failed_cases=total_cases - passed_cases,
        emergency_cases=emergency_cases,
        non_emergency_cases=non_emergency_cases,
        true_positives=true_positives,
        false_negatives=false_negatives,
        true_negatives=true_negatives,
        false_positives=false_positives,
        unavailable_cases=unavailable_cases,
        case_pass_rate=_rate(passed_cases, total_cases),
        emergency_recall=_rate(true_positives, emergency_cases),
        false_positive_rate=_rate(false_positives, non_emergency_cases),
        unavailable_rate=_rate(unavailable_cases, total_cases),
    )


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate the synthetic reference emergency detector.",
    )
    parser.add_argument("dataset", type=Path, help="Path to a synthetic JSON dataset.")
    return parser


def main(
    argv: Sequence[str] | None = None,
    stdout: EvaluationOutput = sys.stdout,
    stderr: EvaluationOutput = sys.stderr,
) -> int:
    args = _build_parser().parse_args(argv)
    try:
        dataset = load_evaluation_dataset(args.dataset)
    except (OSError, ValidationError):
        stderr.write("Emergency evaluation could not load the dataset.\n")
        return 2

    report = evaluate_emergency_detector(dataset, build_reference_detector())
    stdout.write(report.model_dump_json(indent=2) + "\n")
    return 0 if report.meets_thresholds else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
