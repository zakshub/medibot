# 31. Message Orchestration

## 31.1 Purpose

`MessageOrchestrator` connects existing safety contracts without allowing configuration strings or partial dependencies to activate medical behavior. It supports a bounded emergency-resource path followed by bounded unsupported or prohibited handling. Normal medical information, diagnosis, treatment, and severity assessment remain disabled.

## 31.2 Gate Order

The orchestrator evaluates gates in this order:

1. Load active immutable policy ID `message.safety`.
2. Confirm the policy explicitly permits route `emergency`.
3. Require a validated country code before processing health text.
4. Evaluate the bounded emergency detector.
5. Confirm the exact detector version is permitted by the active policy.
6. Reject unavailable and no-signal decisions.
7. Load an approved resource for the exact country and locale.
8. Confirm the returned resource matches the requested country and locale.
9. Compose the bounded emergency response and stop processing; or, only after emergency `no_signal`, continue to scope detection.
10. Require an enabled scope route and evaluate the scope detector.
11. Confirm the exact scope-detector version and returned route are permitted by policy.
12. Return a bounded unsupported or prohibited response, otherwise fail closed.

The order is intentional. Policy, route, and location failures stop before detector processing. Resource lookup occurs only after a possible-emergency decision. Scope detection never runs for a possible emergency and cannot override emergency guidance.

## 31.3 HTTP Behavior

1. A complete approved chain returns HTTP `200` and route `emergency`.
2. Every incomplete, unavailable, inconsistent, or failed chain returns HTTP `503` and route `service_unavailable`.
3. Validation, body-limit, and rate-limit failures retain their bounded `422`, `413`, and `429` contracts.
4. The active repository policy version is returned when a policy exists; the validated configuration value is fallback metadata only.

## 31.4 Bounded Outcomes

Audit events may record only these orchestration outcomes:

1. `blocked_policy_unavailable`
2. `blocked_route_not_permitted`
3. `blocked_location_unavailable`
4. `blocked_detector_unavailable`
5. `blocked_detector_version_not_permitted`
6. `blocked_medical_guidance_unavailable`
7. `blocked_emergency_resource_unavailable`
8. `blocked_emergency_resource_mismatch`
9. `blocked_policy_dependency_failure`
10. `blocked_detector_dependency_failure`
11. `blocked_registry_dependency_failure`
12. `emergency_resource_returned`
13. `blocked_scope_detector_unavailable`
14. `blocked_scope_detector_version_not_permitted`
15. `blocked_scope_route_not_permitted`
16. `blocked_scope_dependency_failure`
17. `unsupported_returned`
18. `prohibited_returned`

No user message, detector match, category, resource instruction, or exception text enters the audit event.

## 31.5 Failure Containment

Policy repository, detector, and resource registry exceptions are contained at the orchestration boundary and converted to the same sanitized unavailable response. Their bounded outcomes identify only the failed component; exception text is not returned or added to the audit event.

The resource is rejected if its country or locale differs from the validated request, even if a registry adapter incorrectly returns it.

## 31.6 Current Activation State

The default application injects:

1. `EmptyPolicyRepository`;
2. `EmptyEmergencySignalDetector`;
3. `EmptyEmergencyResourceRegistry`.

The default scope detector is also unavailable. Therefore the default endpoint remains locked. Tests activate paths only with synthetic immutable policies, detector phrases, resources, clocks, and `example.invalid` sources.

## 31.7 Evidence and Remaining Work

Automated tests cover every gate, route consistency, category limits, detector-version pinning, dependency exceptions, resource mismatch, API status, response source, request ID, policy version, and absence of raw synthetic text from response and audit logs. The versioned synthetic evaluation harness separately measures detector behavior and exposes known keyword limitations.

Production activation still requires resolved product decisions, locale-specific clinical evaluation, jurisdiction-owned resources, legal/privacy review, operational monitoring, rollback evidence, and accountable approval.
