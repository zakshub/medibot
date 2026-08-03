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

## Automated Checks

Every push and pull request to `master` runs:

- Ruff lint checks;
- the pytest API suite;
- an editable install and package-wheel build.

Security concerns should follow [SECURITY.md](SECURITY.md) and must not include real health data in public reports.

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
