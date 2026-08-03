from medibot.models import MessageResponse, MessageRoute


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

