# 23 - Release Evidence Template

## 1. Release Identity

- Release candidate:
- Commit SHA:
- Immutable image digest:
- Build workflow/run identifier:
- Application version:
- Environment:
- Prepared by:
- Prepared at:

Mutable branch names, floating image tags, and local working-tree descriptions are not release identities.

## 2. Component Versions

| Component | Version or digest | Evidence link/ID | Owner |
|---|---|---|---|
| Application | | | |
| Base image | | | |
| Model/provider | Not enabled | | |
| Prompt/policy | Unapproved | | |
| Reviewed content | Not enabled | | |
| Evaluation dataset | | | |
| Deployment configuration | | | |

## 3. Product Scope

- Approved users:
- Approved countries/jurisdictions:
- Approved languages:
- Allowed use cases:
- Prohibited use cases:
- Explicit non-goals:
- Emergency behavior version:

Any unresolved field blocks medical-guidance release.

## 4. Automated Evidence

| Gate | Required result | Actual evidence | Status |
|---|---|---|---|
| Ruff | Pass | | Pending |
| Tests | All pass | | Pending |
| Coverage | At least 90% | | Pending |
| Dependency consistency | No broken requirements | | Pending |
| Dependency audit | No unaccepted known vulnerabilities | | Pending |
| Package build | Pass | | Pending |
| Container build | Pass | | Pending |
| Compose validation | Pass | | Pending |
| Secret/prohibited-data scan | Pass | | Pending |
| Image scan and SBOM | Pass | | Pending |

Do not replace missing evidence with verbal confirmation.

## 5. Safety Evaluation

- Safety evaluation version:
- Emergency false-negative result:
- Emergency false-positive result:
- Prohibited-response violation result:
- Fabricated-source result:
- Sensitive-data leakage result:
- Locale/population breakdown:
- Critical case failures:
- Clinical reviewer:
- Review timestamp:

Every critical or catastrophic failure requires disposition, owner, regression test, and explicit residual-risk decision.

## 6. Privacy and Security Evidence

- Data inventory version:
- Processor/subprocessor review:
- Retention/deletion verification:
- Access-control verification:
- Logging/redaction verification:
- Threat/abuse review:
- Incident-response exercise:
- Open vulnerabilities and exceptions:
- Privacy owner approval:
- Security owner approval:

## 7. Operational Evidence

- Liveness result:
- Readiness result:
- Request-ID verification:
- Rate-limit verification:
- Dependency-failure verification:
- Rollback target:
- Rollback command/procedure version:
- Rollback exercise result:
- Monitoring and alert ownership:

The current foundation is expected to report readiness `503`. It is not releasable for medical-guidance traffic.

## 8. Residual Risks

| Risk ID | Residual severity | Residual likelihood | Evidence | Acceptance owner | Decision |
|---|---:|---:|---|---|---|
| | | | | | |

Unowned risk, missing evidence, or unapproved catastrophic residual risk blocks release.

## 9. Required Approvals

| Role | Name | Decision | Timestamp | Evidence/record ID |
|---|---|---|---|---|
| Engineering | | Pending | | |
| Product | | Pending | | |
| Clinical safety | | Pending | | |
| Privacy | | Pending | | |
| Security | | Pending | | |
| Legal/compliance | | Pending | | |
| Operations | | Pending | | |

Only roles required by approved scope may be marked not applicable, with documented rationale and accountable owner.

## 10. Stop Conditions

Release is blocked when any of the following is true:

- `/v1/ready` does not match the approved release expectation;
- medical scope, jurisdiction, language, or emergency behavior is unresolved;
- required tests, scans, evaluations, or approvals are missing;
- raw personal/health data appears in errors, logs, metrics, evidence, or tickets;
- rollback has not been verified;
- a required safety control fails open;
- evidence references a different commit, image, policy, content, or configuration;
- an owner cannot explain and accept the remaining risk.

## 11. Final Decision

- Decision: Blocked / Approved
- Approved scope:
- Conditions:
- Decision owner:
- Decision timestamp:
- Immutable evidence record:

The default decision is `Blocked` until every required field and gate is complete.

