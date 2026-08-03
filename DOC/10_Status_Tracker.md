# 10. Status Tracker

Last updated: 2026-08-03

## 10.1 Current Overall Status

Estimated implementation progress: **38% done, 62% remaining**.

These percentages are planning estimates, not release evidence. A high implementation percentage cannot replace product, clinical, privacy, security, or legal approval.

| Workstream | Done | Remaining | Current evidence |
| --- | ---: | ---: | --- |
| Documentation baseline | 95% | 5% | Numbered documentation, runbook, contracts, and release templates exist |
| Repository, CI, and testing | 90% | 10% | Automated lint, tests, audit, build, and container checks exist |
| Backend API foundation | 65% | 35% | Versioned health, readiness, message, validation, and audit contracts exist |
| Safety architecture | 55% | 45% | Fail-closed policy, content, emergency, and response boundaries exist |
| Emergency routing | 45% | 55% | Registry, detector contract, and composer exist but are not live on the endpoint |
| Medical content system | 30% | 70% | Reviewed-content repository exists; approved production content does not |
| Actual medical bot behavior | 10% | 90% | Live medical guidance remains intentionally disabled |
| Medical bot UI | 35% | 65% | Responsive chat/status scaffold exists; complete product flows do not |
| Product, clinical, and legal decisions | 15% | 85% | Decision register exists; accountable approvals are missing |
| Production readiness | 20% | 80% | Container and runbook exist; deployment evidence and approvals do not |

## 10.2 Completed

1. Created and maintained the numbered `DOC` set.
2. Added the typed FastAPI application and strict versioned contracts.
3. Added fail-closed medical behavior, privacy-safe audit events, request limits, and rate limiting.
4. Added reviewed-content, policy, emergency-resource, detector, and response contracts.
5. Added automated quality, package, dependency, and container checks.
6. Added a responsive browser UI connected to live health, readiness, and message endpoints.

## 10.3 In Progress

1. Connect approved emergency routing to the live message flow.
2. Add a bounded conversation-orchestration layer.
3. Build evaluation fixtures without real patient data.
4. Extend UI states for approved information, urgent, emergency, unsupported, and prohibited routes.

## 10.4 Blockers

1. Intended users and allowed medical function are not approved.
2. Supported jurisdictions and emergency-resource owners are not approved.
3. Clinical reviewers and production content sources are not assigned.
4. Privacy retention, deletion, consent, and processor decisions are not approved.
5. No release can honestly be marked ready until these accountable decisions exist.

## 10.5 Next Work Items

1. Integrate the fail-closed emergency decision pipeline without activating general medical guidance.
2. Add deterministic route orchestration and audit outcomes.
3. Add UI route-state tests and accessibility checks.
4. Replace synthetic resources only after named reviewers approve real jurisdiction data.
