from medibot.emergency import EmergencyResource
from medibot.models import MessageResponse, MessageRoute
from medibot.routing import EmergencySignalDecision, EmergencySignalStatus


def unavailable_response(request_id: str, policy_version: str) -> MessageResponse:
    return MessageResponse(
        request_id=request_id,
        route=MessageRoute.SERVICE_UNAVAILABLE,
        message="Medibot is not available for health guidance yet.",
        limitations="No medical information, diagnosis, or treatment is provided.",
        next_step=(
            "If this may be an emergency, contact local emergency services "
            "or a trusted person now."
        ),
        policy_version=policy_version,
    )


def unsupported_response(request_id: str, policy_version: str) -> MessageResponse:
    return MessageResponse(
        request_id=request_id,
        route=MessageRoute.UNSUPPORTED,
        message="This request is outside Medibot's approved scope.",
        limitations="No medical information, diagnosis, or treatment is provided.",
        next_step="Use an appropriate qualified professional or trusted service.",
        policy_version=policy_version,
    )


def prohibited_response(request_id: str, policy_version: str) -> MessageResponse:
    return MessageResponse(
        request_id=request_id,
        route=MessageRoute.PROHIBITED,
        message="Medibot cannot help with this request.",
        limitations="No instructions or medical guidance are provided.",
        next_step="Use a safe and lawful source of support.",
        policy_version=policy_version,
    )


def emergency_response(
    request_id: str,
    policy_version: str,
    decision: EmergencySignalDecision,
    resource: EmergencyResource | None,
) -> MessageResponse:
    if decision.status != EmergencySignalStatus.POSSIBLE_EMERGENCY or resource is None:
        return unavailable_response(
            request_id=request_id,
            policy_version=policy_version,
        )

    return MessageResponse(
        request_id=request_id,
        route=MessageRoute.EMERGENCY,
        message=(
            "This may need urgent in-person help. "
            "Use the approved local emergency instructions now."
        ),
        limitations="Medibot cannot assess severity, diagnose, or confirm an emergency.",
        sources=[
            {
                "title": resource.service_name,
                "url": str(resource.source_url),
                "reviewed_version": resource.version,
            }
        ],
        next_step=resource.contact_instructions,
        policy_version=policy_version,
    )
