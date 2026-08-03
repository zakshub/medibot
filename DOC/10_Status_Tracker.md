# 10. Status Tracker

Last updated: 2026-08-03

## 10.1 Current Overall Status

Estimated implementation progress: **50% done, 50% remaining**.

These percentages are planning estimates, not release evidence. A high implementation percentage cannot replace product, clinical, privacy, security, or legal approval.

| Workstream | Done | Remaining | Current evidence |
| --- | ---: | ---: | --- |
| Documentation baseline | 97% | 3% | Numbered documentation, runbook, contracts, evaluation, routing, and release templates exist |
| Repository, CI, and testing | 93% | 7% | Automated lint, tests, audit, build, container, evaluation, and UI structure checks exist |
| Backend API foundation | 80% | 20% | Versioned health, readiness, message, validation, emergency/scope orchestration, and audit contracts exist |
| Safety architecture | 72% | 28% | Fail-closed policy, content, emergency, scope, orchestration, response, and evaluation boundaries exist |
| Emergency routing | 70% | 30% | Guarded pipeline and engineering evaluation exist; production detector, resources, and approval do not |
| Safety evaluation | 35% | 65% | Versioned synthetic harness exists; representative clinically reviewed suites and thresholds do not |
| Scope and refusal routing | 55% | 45% | Guarded unsupported/prohibited contracts exist; approved real scope definitions and evaluation do not |
| Medical content system | 30% | 70% | Reviewed-content repository exists; approved production content does not |
| Actual medical bot behavior | 25% | 75% | Guarded emergency and refusal routing exist; normal medical guidance remains disabled |
| Medical bot UI | 45% | 55% | Responsive accessible chat/status shell exists; approved complete product flows do not |
| Product, clinical, and legal decisions | 15% | 85% | Decision register exists; accountable approvals are missing |
| Production readiness | 27% | 73% | Container, runbook, bounded route handling, reports, and UI privacy controls exist; release evidence and approvals do not |

## 10.2 Completed

1. Created and maintained the numbered `DOC` set.
2. Added the typed FastAPI application and strict versioned contracts.
3. Added fail-closed medical behavior, privacy-safe audit events, request limits, and rate limiting.
4. Added reviewed-content, policy, emergency-resource, detector, and response contracts.
5. Added automated quality, package, dependency, and container checks.
6. Added a responsive browser UI connected to live health, readiness, and message endpoints.
7. Connected guarded emergency orchestration behind active-policy, location, detector, and approved-resource gates.
8. Added versioned synthetic emergency datasets, metrics, threshold verdicts, and privacy-safe reports.
9. Removed assumed user location and added UI accessibility, privacy, status-isolation, and tablet-layout regression controls.
10. Added emergency-first, policy-pinned unsupported and prohibited routing with bounded responses and audits.

## 10.3 In Progress

1. Expand emergency challenges by approved locale without real patient data.
2. Define and evaluate real unsupported and prohibited categories after product approval.
3. Extend UI interaction evidence for approved emergency, unsupported, and prohibited routes.
4. Define production adapter publication and rollback controls.

## 10.4 Blockers

1. Intended users and allowed medical function are not approved.
2. Supported jurisdictions and emergency-resource owners are not approved.
3. Clinical reviewers and production content sources are not assigned.
4. Privacy retention, deletion, consent, and processor decisions are not approved.
5. No release can honestly be marked ready until these accountable decisions exist.

## 10.5 Next Work Items

1. Add clinically owned evaluation taxonomy and severity weighting after product scope approval.
2. Add end-to-end UI route-state interaction tests and human accessibility review.
3. Add adapter health signals without exposing dependency details publicly.
4. Replace synthetic resources only after named reviewers approve real jurisdiction data.
