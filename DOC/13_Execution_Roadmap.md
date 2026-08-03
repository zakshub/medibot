# 13 - Execution Roadmap

## Purpose

This roadmap turns the documentation baseline into ordered, verifiable implementation batches. A batch is complete only when its exit criteria are met.

## Batch 1 - Repository Foundation

Status: Complete

- Create the numbered documentation pack.
- Add the repository entry point and contribution rules.
- Add exclusions for secrets, generated files, and private data.
- Push a clean baseline to the remote repository.

Exit criteria: repository can be understood without verbal context.

## Batch 2 - Product Definition

Status: In progress

- Identify target users and supported languages.
- Define allowed use cases and prohibited use cases.
- Define emergency escalation behavior.
- Document functional and non-functional requirements.
- Establish measurable acceptance criteria.
- Resolve and approve the decisions recorded in `14_Product_Requirements.md`.

Exit criteria: an engineer and reviewer can independently describe the same product behavior.

## Batch 3 - Safety, Privacy, and Compliance

Status: Draft controls documented; approval blocked by product definition

- Create a medical-harm risk assessment.
- Define privacy, consent, retention, deletion, and access rules.
- Define human review and clinical content ownership.
- Select jurisdictions and identify applicable legal requirements.
- Define logging rules that exclude or protect sensitive information.
- Resolve and approve `15_Safety_Risk_Register.md` and `16_Data_Governance_And_Privacy.md`.

Exit criteria: identified risks have owners, controls, and verification methods.

## Batch 4 - Architecture and Technology Selection

Status: Blocked by Batches 2 and 3

- Select client, server, model, storage, and hosting technologies.
- Document trust boundaries and external processors.
- Define API contracts and data models.
- Create a testing and observability strategy.
- Record architecture decisions and rejected alternatives.

Exit criteria: the architecture supports approved requirements without bypassing safety controls.

## Batch 5 - Minimum Viable Implementation

Status: Blocked by Batch 4

- Create the agreed source structure.
- Implement the smallest end-to-end user flow.
- Add input validation, safe failure behavior, and emergency handling.
- Add unit, integration, and safety tests.
- Add local setup and verification commands.

Exit criteria: the approved flow runs locally and all required checks pass.

## Batch 6 - Evaluation and Release Readiness

Status: Blocked by Batch 5

- Build representative and adversarial evaluation datasets.
- Measure safety, quality, latency, and reliability.
- Complete security and privacy reviews.
- Define rollback, incident response, and support ownership.
- Obtain required product, clinical, and legal approvals.

Exit criteria: release evidence is recorded and accountable owners approve deployment.

## Immediate Inputs Needed

Implementation beyond the repository foundation requires factual product decisions, not guesses:

- intended users;
- intended medical function;
- countries or jurisdictions;
- supported channels and languages;
- data sources and model providers;
- whether personal health data will be stored.
