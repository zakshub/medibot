from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from medibot.models import MessageRoute


class EmergencySignalStatus(StrEnum):
    NO_SIGNAL = "no_signal"
    POSSIBLE_EMERGENCY = "possible_emergency"
    UNAVAILABLE = "unavailable"


class EmergencySignalDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: EmergencySignalStatus
    route: MessageRoute
    categories: frozenset[str] = Field(default_factory=frozenset)
    detector_version: str


class EmergencySignalDetector(Protocol):
    def evaluate(self, message: str, locale: str) -> EmergencySignalDecision: ...


class EmptyEmergencySignalDetector:
    """Fail-closed detector used until an approved safety classifier exists."""

    def evaluate(self, message: str, locale: str) -> EmergencySignalDecision:
        return EmergencySignalDecision(
            status=EmergencySignalStatus.UNAVAILABLE,
            route=MessageRoute.SERVICE_UNAVAILABLE,
            detector_version="unavailable",
        )


class KeywordEmergencySignalDetector:
    """Deterministic reference detector for synthetic tests and safety plumbing."""

    def __init__(
        self,
        keyword_categories: dict[str, frozenset[str]],
        detector_version: str,
    ) -> None:
        self._keyword_categories = {
            keyword.casefold(): categories
            for keyword, categories in keyword_categories.items()
        }
        self._detector_version = detector_version

    def evaluate(self, message: str, locale: str) -> EmergencySignalDecision:
        normalized_message = message.casefold()
        categories = frozenset(
            category
            for keyword, keyword_categories in self._keyword_categories.items()
            if keyword in normalized_message
            for category in keyword_categories
        )
        if categories:
            return EmergencySignalDecision(
                status=EmergencySignalStatus.POSSIBLE_EMERGENCY,
                route=MessageRoute.EMERGENCY,
                categories=categories,
                detector_version=self._detector_version,
            )

        return EmergencySignalDecision(
            status=EmergencySignalStatus.NO_SIGNAL,
            route=MessageRoute.INFORMATION,
            detector_version=self._detector_version,
        )
