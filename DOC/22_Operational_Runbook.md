# 22 - Operational Runbook

## 1. Scope

This runbook covers the current fail-closed API foundation. It does not authorize medical guidance, production health-data processing, or emergency-service operation.

## 2. Ownership

- Primary operational owner: TBD
- Security incident owner: TBD
- Privacy incident owner: TBD
- Clinical safety incident owner: TBD
- Product decision owner: TBD
- Escalation contact and operating hours: TBD

Deployment is blocked until accountable contacts and escalation availability are recorded.

## 3. Pre-Start Checks

1. Confirm the intended commit and immutable image identifier.
2. Confirm `MEDIBOT_ENVIRONMENT=production` and `MEDIBOT_DEBUG=false`.
3. Confirm policy version is expected; `unapproved` must remain not ready.
4. Confirm no `.env`, credentials, health records, or conversation exports exist in the image or mounted paths.
5. Confirm root filesystem is read-only, capabilities are dropped, and privilege escalation is blocked.
6. Confirm ingress TLS, trusted proxy chain, request limits, and external rate limiter where applicable.
7. Confirm the previous known-good image and rollback command are available.

## 4. Startup Verification

1. Start the service in the isolated target environment.
2. Call `/v1/health`; expect HTTP `200`, version, no-store headers, and `X-Request-ID`.
3. Call `/v1/ready`; expect HTTP `503` for the current foundation.
4. Confirm the readiness reason includes `medical_guidance_unavailable`.
5. Send a synthetic message request; expect bounded HTTP `503` without input echo.
6. Send an invalid synthetic request; expect bounded HTTP `422` without input echo.
7. Confirm no synthetic message text appears in application or platform logs.
8. Do not route user traffic while readiness is not `200`.

## 5. Signal Interpretation

| Signal | Meaning | Required action |
|---|---|---|
| Health 200, readiness 503 | Process is alive but must not receive product traffic | Keep traffic disabled; inspect bounded readiness reasons |
| Health non-200 or timeout | Process, network, or runtime failure | Remove instance from service and inspect bounded operational metadata |
| Elevated 413 | Oversized request attempts or client defect | Inspect aggregate counts; never collect rejected bodies |
| Elevated 422 | Invalid clients, probing, or contract mismatch | Inspect route/version aggregates; verify client contract |
| Elevated 429 | High request volume or insufficient distributed limiting | Verify edge limits and capacity; do not log limiter keys |
| Missing request ID | Middleware/configuration regression | Block release or remove affected instance |
| Raw health text in logs | Privacy incident | Stop affected logging path and begin incident response |

## 6. Safe Log Inspection

Allowed operational fields:

- opaque request ID;
- route and bounded outcome;
- policy, application, model, and content versions;
- bounded error code;
- coarse timing and aggregate count.

Do not search, copy, paste, export, or attach raw prompts, responses, symptoms, medication details, names, addresses, tokens, IP addresses, or account identifiers to tickets or chat systems.

## 7. Incident: Raw Health Data in Logs

1. Disable the affected logging/export path without deleting evidence.
2. Restrict access to the affected destination.
3. Record time range, systems, data categories, and approved incident identifier without copying content.
4. Notify privacy and security owners through the approved private channel.
5. Rotate credentials if logs may contain secrets or authorization material.
6. Determine retention, deletion, backup, and legal-notification requirements.
7. Add a synthetic regression test reproducing the leakage mechanism.
8. Resume only after controls are verified and authorized owners approve.

## 8. Incident: Safety or Readiness Bypass

1. Remove the affected version from traffic.
2. Roll back to the last version with verified readiness behavior.
3. Preserve commit, image, configuration, policy, and request IDs.
4. Do not preserve raw health content unless explicitly authorized for the incident.
5. Identify whether configuration, code, dependency, proxy, or orchestration caused the bypass.
6. Add regression coverage and rerun the full release evidence suite.
7. Require engineering, clinical safety, privacy/security, and product approval before restoration.

## 9. Incident: Rate-Limit Failure

1. Confirm whether the edge/shared limiter or per-process backstop failed.
2. Apply conservative ingress limits or disable the affected route.
3. Avoid switching to user-provided forwarding headers as identity.
4. Verify retry behavior is not amplifying load.
5. Record aggregate counts, regions, versions, and bounded limiter outcomes.
6. Restore only after concurrency and multi-instance behavior are tested.

## 10. Rollback

1. Stop new traffic to the affected version.
2. Select the recorded immutable previous image, never a mutable tag.
3. Apply the compatible previous configuration, policy, and content versions.
4. Start isolated instances and repeat Section 4 checks.
5. Route traffic only when the approved readiness expectation is met.
6. Monitor bounded error, health, readiness, and rate-limit signals.
7. Record rollback evidence and link it to the incident/change record.

## 11. Evidence Package

Capture without sensitive content:

- commit and immutable image digest;
- deployment and rollback timestamps;
- configuration names and version identifiers, not secret values;
- health/readiness results and request IDs;
- CI, coverage, audit, image-scan, and dependency-scan results;
- approver identities and decision timestamps;
- unresolved risks and assigned owners.

## 12. Current Stop Condition

The current service intentionally reports not ready. No operator may override readiness, rewrite the probe to liveness, or route medical-guidance traffic merely to make a deployment appear healthy.

