import json
import logging
from dataclasses import asdict, dataclass

logger = logging.getLogger("medibot.audit")


@dataclass(frozen=True, slots=True)
class AuditEvent:
    request_id: str
    route: str
    outcome: str
    policy_version: str


def emit_audit_event(event: AuditEvent) -> None:
    """Emit bounded metadata only; user and generated health content are excluded by type."""
    logger.info("%s", json.dumps(asdict(event), separators=(",", ":"), sort_keys=True))

