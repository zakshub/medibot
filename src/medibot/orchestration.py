from dataclasses import dataclass
from enum import StrEnum

from medibot.emergency import EmergencyResourceRegistry
from medibot.models import MessageRequest, MessageResponse, MessageRoute
from medibot.policy import PolicyRepository
from medibot.responses import emergency_response, unavailable_response
from medibot.routing import EmergencySignalDetector, EmergencySignalStatus

MESSAGE_POLICY_ID = "message.safety"


class ProcessingOutcome(StrEnum):
    POLICY_UNAVAILABLE = "blocked_policy_unavailable"
    ROUTE_NOT_PERMITTED = "blocked_route_not_permitted"
    LOCATION_UNAVAILABLE = "blocked_location_unavailable"
    DETECTOR_UNAVAILABLE = "blocked_detector_unavailable"
    DETECTOR_VERSION_NOT_PERMITTED = "blocked_detector_version_not_permitted"
    NO_EMERGENCY_SIGNAL = "blocked_medical_guidance_unavailable"
    RESOURCE_UNAVAILABLE = "blocked_emergency_resource_unavailable"
    RESOURCE_MISMATCH = "blocked_emergency_resource_mismatch"
    POLICY_DEPENDENCY_FAILURE = "blocked_policy_dependency_failure"
    DETECTOR_DEPENDENCY_FAILURE = "blocked_detector_dependency_failure"
    REGISTRY_DEPENDENCY_FAILURE = "blocked_registry_dependency_failure"
    EMERGENCY_RESOURCE_RETURNED = "emergency_resource_returned"


@dataclass(frozen=True, slots=True)
class MessageProcessingResult:
    response: MessageResponse
    outcome: ProcessingOutcome

    @property
    def status_code(self) -> int:
        return 200 if self.response.route == MessageRoute.EMERGENCY else 503


class MessageOrchestrator:
    """Route one message through explicit policy and emergency safety gates."""

    def __init__(
        self,
        policy_repository: PolicyRepository,
        emergency_signal_detector: EmergencySignalDetector,
        emergency_registry: EmergencyResourceRegistry,
        fallback_policy_version: str,
    ) -> None:
        self._policy_repository = policy_repository
        self._emergency_signal_detector = emergency_signal_detector
        self._emergency_registry = emergency_registry
        self._fallback_policy_version = fallback_policy_version

    def process(
        self,
        request_id: str,
        payload: MessageRequest,
    ) -> MessageProcessingResult:
        try:
            policy = self._policy_repository.get_active(MESSAGE_POLICY_ID)
        except Exception:
            return self._unavailable(
                request_id,
                self._fallback_policy_version,
                ProcessingOutcome.POLICY_DEPENDENCY_FAILURE,
            )

        if policy is None:
            return self._unavailable(
                request_id,
                self._fallback_policy_version,
                ProcessingOutcome.POLICY_UNAVAILABLE,
            )

        if MessageRoute.EMERGENCY not in policy.permitted_routes:
            return self._unavailable(
                request_id,
                policy.version,
                ProcessingOutcome.ROUTE_NOT_PERMITTED,
            )

        if payload.country_code is None:
            return self._unavailable(
                request_id,
                policy.version,
                ProcessingOutcome.LOCATION_UNAVAILABLE,
            )

        try:
            decision = self._emergency_signal_detector.evaluate(
                payload.message,
                payload.locale,
            )
        except Exception:
            return self._unavailable(
                request_id,
                policy.version,
                ProcessingOutcome.DETECTOR_DEPENDENCY_FAILURE,
            )

        if decision.status == EmergencySignalStatus.UNAVAILABLE:
            return self._unavailable(
                request_id,
                policy.version,
                ProcessingOutcome.DETECTOR_UNAVAILABLE,
            )
        if decision.detector_version not in policy.permitted_detector_versions:
            return self._unavailable(
                request_id,
                policy.version,
                ProcessingOutcome.DETECTOR_VERSION_NOT_PERMITTED,
            )
        if decision.status == EmergencySignalStatus.NO_SIGNAL:
            return self._unavailable(
                request_id,
                policy.version,
                ProcessingOutcome.NO_EMERGENCY_SIGNAL,
            )

        try:
            resource = self._emergency_registry.get_approved(
                payload.country_code,
                payload.locale,
            )
        except Exception:
            return self._unavailable(
                request_id,
                policy.version,
                ProcessingOutcome.REGISTRY_DEPENDENCY_FAILURE,
            )

        if resource is None:
            return self._unavailable(
                request_id,
                policy.version,
                ProcessingOutcome.RESOURCE_UNAVAILABLE,
            )
        if (
            resource.country_code != payload.country_code.upper()
            or resource.locale != payload.locale.upper()
        ):
            return self._unavailable(
                request_id,
                policy.version,
                ProcessingOutcome.RESOURCE_MISMATCH,
            )

        return MessageProcessingResult(
            response=emergency_response(
                request_id=request_id,
                policy_version=policy.version,
                decision=decision,
                resource=resource,
            ),
            outcome=ProcessingOutcome.EMERGENCY_RESOURCE_RETURNED,
        )

    @staticmethod
    def _unavailable(
        request_id: str,
        policy_version: str,
        outcome: ProcessingOutcome,
    ) -> MessageProcessingResult:
        return MessageProcessingResult(
            response=unavailable_response(
                request_id=request_id,
                policy_version=policy_version,
            ),
            outcome=outcome,
        )
