from enum import StrEnum
from typing import Annotated, Protocol

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from medibot.models import MessageRoute


class ScopeSignalStatus(StrEnum):
    NO_SIGNAL = "no_signal"
    UNSUPPORTED = "unsupported"
    PROHIBITED = "prohibited"
    UNAVAILABLE = "unavailable"


ScopeCategory = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=64,
        pattern=r"^[a-z0-9][a-z0-9._-]*$",
    ),
]


class ScopeSignalDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: ScopeSignalStatus
    route: MessageRoute
    categories: frozenset[ScopeCategory] = Field(
        default_factory=frozenset,
        max_length=16,
    )
    detector_version: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z0-9._-]+$",
    )

    @model_validator(mode="after")
    def validate_status_contract(self) -> "ScopeSignalDecision":
        expected_routes = {
            ScopeSignalStatus.NO_SIGNAL: MessageRoute.INFORMATION,
            ScopeSignalStatus.UNSUPPORTED: MessageRoute.UNSUPPORTED,
            ScopeSignalStatus.PROHIBITED: MessageRoute.PROHIBITED,
            ScopeSignalStatus.UNAVAILABLE: MessageRoute.SERVICE_UNAVAILABLE,
        }
        if self.route != expected_routes[self.status]:
            raise ValueError("scope signal status and route are inconsistent")
        detected = self.status in {
            ScopeSignalStatus.UNSUPPORTED,
            ScopeSignalStatus.PROHIBITED,
        }
        if detected and not self.categories:
            raise ValueError("detected scope decision requires bounded categories")
        if not detected and self.categories:
            raise ValueError("categories are only valid for detected scope decisions")
        return self


class ScopeSignalDetector(Protocol):
    def evaluate(self, message: str, locale: str) -> ScopeSignalDecision: ...


class EmptyScopeSignalDetector:
    """Fail-closed detector used until scope definitions are approved."""

    def evaluate(self, message: str, locale: str) -> ScopeSignalDecision:
        return ScopeSignalDecision(
            status=ScopeSignalStatus.UNAVAILABLE,
            route=MessageRoute.SERVICE_UNAVAILABLE,
            detector_version="unavailable",
        )


class KeywordScopeSignalDetector:
    """Deterministic reference detector for synthetic routing tests only."""

    def __init__(
        self,
        unsupported_keywords: dict[str, frozenset[str]],
        prohibited_keywords: dict[str, frozenset[str]],
        detector_version: str,
    ) -> None:
        self._unsupported_keywords = {
            keyword.casefold(): categories
            for keyword, categories in unsupported_keywords.items()
        }
        self._prohibited_keywords = {
            keyword.casefold(): categories
            for keyword, categories in prohibited_keywords.items()
        }
        self._detector_version = detector_version

    def evaluate(self, message: str, locale: str) -> ScopeSignalDecision:
        normalized_message = message.casefold()
        prohibited_categories = self._match_categories(
            normalized_message,
            self._prohibited_keywords,
        )
        if prohibited_categories:
            return ScopeSignalDecision(
                status=ScopeSignalStatus.PROHIBITED,
                route=MessageRoute.PROHIBITED,
                categories=prohibited_categories,
                detector_version=self._detector_version,
            )

        unsupported_categories = self._match_categories(
            normalized_message,
            self._unsupported_keywords,
        )
        if unsupported_categories:
            return ScopeSignalDecision(
                status=ScopeSignalStatus.UNSUPPORTED,
                route=MessageRoute.UNSUPPORTED,
                categories=unsupported_categories,
                detector_version=self._detector_version,
            )

        return ScopeSignalDecision(
            status=ScopeSignalStatus.NO_SIGNAL,
            route=MessageRoute.INFORMATION,
            detector_version=self._detector_version,
        )

    @staticmethod
    def _match_categories(
        message: str,
        keyword_categories: dict[str, frozenset[str]],
    ) -> frozenset[str]:
        return frozenset(
            category
            for keyword, categories in keyword_categories.items()
            if keyword in message
            for category in categories
        )
