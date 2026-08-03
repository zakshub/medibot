# Medibot

Medibot is an early-stage project repository for a medical-assistance bot. The repository currently contains the documentation and delivery controls needed before implementation begins.

> This project is not a medical device and must not be used for diagnosis, emergency decisions, or treatment recommendations until its intended use, clinical safety controls, and regulatory requirements are formally defined and validated.

## Current Status

- Documentation baseline: complete
- Application source code: not present yet
- Product requirements: pending
- Clinical safety review: pending
- Automated tests and deployment: pending
- Continuous integration: lint, tests, and package build enabled
- Executable API foundation: available, intentionally fails closed for health guidance

## Start Here

1. Read [DOC/00_INDEX.md](DOC/00_INDEX.md).
2. Confirm the intended users and permitted medical use cases.
3. Define the minimum viable product and explicit exclusions.
4. Select the implementation stack only after requirements are approved.
5. Track implementation using [DOC/13_Execution_Roadmap.md](DOC/13_Execution_Roadmap.md).
6. Review the draft architecture and contracts before adding application code.

## Repository Layout

```text
medibot/
|-- DOC/             Numbered project documentation
|-- CONTRIBUTING.md  Contribution and review rules
|-- README.md        Repository entry point
`-- .gitignore       Common generated and sensitive files
```

The target application folders described in `DOC/03_Recommended_Folder_Structure.md` should be created when the technology stack and product scope are confirmed.

## Local Development

Requires Python 3.11 or newer.

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m pytest
.venv\Scripts\python -m uvicorn medibot.main:app --reload
```

The message endpoint currently returns HTTP `503` by design. Health guidance remains disabled until product scope and required safety controls are approved and implemented.

The API rejects request bodies above 16 KB before schema validation and applies no-store and defensive browser security headers to every HTTP response.

Every response includes an opaque `X-Request-ID`. Audit events contain only that identifier, route, outcome, and policy version; user health text is excluded by the audit event type and regression tests.

Runtime configuration is validated at startup. Unknown environments, unsafe request-size limits, malformed policy versions, and production debug mode stop the application instead of silently using unsafe values.

`GET /v1/health` is a process-liveness check. `GET /v1/ready` is a separate traffic-readiness check and returns HTTP `503` while policy is unapproved or medical guidance remains unavailable. Changing only the policy-version string cannot create false readiness.

`POST /v1/messages` has a per-process fixed-window rate-limit backstop. Production still requires a trusted edge or shared-store limiter because in-process counters are not distributed across instances.

FastAPI publishes the versioned OpenAPI contract at `/openapi.json`. Regression tests pin the public routes, bounded error responses, strict request schema, and absence of raw health-input fields from error schemas.

## Automated Checks

Every push and pull request to `master` runs:

- Ruff lint checks;
- the pytest API suite;
- dependency consistency and known-vulnerability checks;
- an editable install and package-wheel build.

Security concerns should follow [SECURITY.md](SECURITY.md) and must not include real health data in public reports.

Dependabot checks Python and GitHub Actions dependencies weekly. Updates still require the full CI and safety review; automated version proposals are not automatic release approval.

The pytest command measures source coverage and fails below 90%. The current measured baseline is 100%; the floor prevents material regression without encouraging low-value tests solely to claim 100%.

Run the complete local verification sequence with one command:

```powershell
.\scripts\check.ps1
```

Linux and CI use `PYTHON=.venv/bin/python bash scripts/check.sh`. Both scripts run lint, tests/coverage, dependency consistency, vulnerability audit, and package build in the same order.

## Container

```powershell
docker build --tag medibot:local .
docker run --rm --publish 8000:8000 medibot:local
```

The image runs as a non-root user and its healthcheck verifies process liveness only. Deployment traffic must use `/v1/ready`; the service remains intentionally not ready for medical guidance.

For the hardened local baseline:

```powershell
docker compose up --build
```

Compose binds only to `127.0.0.1`, drops Linux capabilities, blocks privilege escalation, uses a read-only root filesystem, and applies bounded process, memory, and CPU limits. It is not a production orchestration manifest.

Operational startup, signal interpretation, privacy incidents, readiness bypass, rate-limit failure, and rollback procedures are defined in [DOC/22_Operational_Runbook.md](DOC/22_Operational_Runbook.md).

GitHub pull requests and issues use structured templates. Public submissions must use synthetic data; exploitable security or sensitive-data issues must use private vulnerability reporting.

Every release candidate must complete [DOC/23_Release_Evidence_Template.md](DOC/23_Release_Evidence_Template.md) against one immutable commit and image. The default release decision remains blocked while required evidence or approvals are missing.

Product decisions are tracked in [DOC/24_Product_Decision_Register.md](DOC/24_Product_Decision_Register.md). Reviewed content must satisfy [DOC/25_Content_Provenance_And_Approval.md](DOC/25_Content_Provenance_And_Approval.md); the current repository intentionally returns no medical content.

Safety policy must satisfy [DOC/26_Policy_Versioning_And_Approval.md](DOC/26_Policy_Versioning_And_Approval.md). The application defaults to an empty policy repository, and a policy-version environment string cannot activate medical behavior.

Emergency resources must satisfy [DOC/27_Emergency_Resource_Registry.md](DOC/27_Emergency_Resource_Registry.md). The application defaults to an empty emergency registry; unknown country or locale combinations return no resource, and tests use synthetic emergency examples only.

## Safety Boundary

Until a reviewed product specification exists, Medibot must:

- avoid presenting generated text as a diagnosis;
- direct emergencies to local emergency services;
- avoid storing health data without an approved privacy and retention design;
- clearly disclose that responses may be incomplete or incorrect;
- require qualified clinical review for medical content and decision logic.

## Documentation Rules

- Keep documents numbered and listed in `DOC/00_INDEX.md`.
- Record material changes in `DOC/12_Change_Log.md`.
- Do not mark implementation work complete without evidence or tests.
- Do not commit credentials, patient data, private medical records, or production secrets.
