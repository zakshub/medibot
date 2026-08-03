# 17 - System Architecture

## 1. Status

- Status: Draft
- Architecture owner: TBD
- Security owner: TBD
- Clinical safety owner: TBD
- Approved technology stack: TBD

This document defines required boundaries and responsibilities without prematurely selecting vendors or frameworks.

## 2. Architecture Principles

1. Safety controls must not depend only on the generative model.
2. Sensitive data collection must be minimized before storage is considered.
3. Untrusted user, model, and retrieved content must remain separated from system instructions.
4. Failure of an optional dependency must produce a bounded safe response.
5. Safety-critical policy and content must be versioned, testable, and reversible.
6. Logs and metrics must remain useful without containing raw health content.

## 3. Logical Components

| Component | Responsibility | Must not do |
|---|---|---|
| Client | Display notices, collect supported input, render responses and emergency guidance | Store secrets or independently decide medical risk |
| API gateway | Request limits, request IDs, authentication where required, size validation | Log raw health content by default |
| Conversation service | Orchestrate one interaction and enforce approved flow | Bypass safety checks or persist data implicitly |
| Input safety layer | Detect prohibited scope, emergency indicators, injection attempts, and invalid input | Claim clinical certainty |
| Response engine | Generate or assemble bounded health information | Diagnose, prescribe, or invent sources |
| Output safety layer | Enforce response policy, source rules, disclaimers, and safe next steps | Treat model self-evaluation as sufficient evidence |
| Approved content service | Provide versioned, reviewed health and emergency content | Import unreviewed internet content into production |
| Audit service | Record minimal version, outcome, and control-event metadata | Store raw conversations unless separately approved |
| Administration service | Manage reviewed policy/content versions and rollback | Allow unreviewed production publication |

## 4. Request Flow

1. Client displays scope and privacy notice.
2. API gateway validates request shape, size, and rate limits.
3. Conversation service assigns a random request identifier.
4. Input safety layer classifies emergency, prohibited, unsupported, or supported scope.
5. Emergency and prohibited routes return controlled responses without normal generation.
6. Supported requests retrieve only approved content when retrieval is enabled.
7. Response engine creates a candidate response.
8. Output safety layer validates policy, claims, source handling, and next-step wording.
9. Client receives the bounded response and relevant notices.
10. Audit service receives only approved minimal event metadata.

## 5. Trust Boundaries

### Untrusted Zone

- user input and uploads;
- model output;
- retrieved documents and external API responses;
- client-controlled metadata;
- webhook and integration payloads.

### Controlled Application Zone

- request orchestration;
- deterministic safety policies;
- approved content retrieval;
- response templates;
- identity and authorization enforcement.

### Restricted Administration Zone

- policy and emergency-content publication;
- model/provider configuration;
- audit access;
- credential management;
- release and rollback controls.

Movement between zones requires validation, authorization, minimization, and an auditable policy decision.

## 6. Data Stores

No persistent conversation store is approved yet.

Potential stores, subject to privacy approval:

| Store | Proposed data | Default retention |
|---|---|---|
| Policy repository | Versioned rules and response templates | Project lifetime |
| Content repository | Reviewed health and emergency content | Project lifetime with version history |
| Operational metrics | Aggregated timing, status, and bounded error codes | TBD |
| Audit events | Request ID, policy/model version, route category, timestamp | TBD |
| User/account store | Only if an approved requirement needs accounts | Not approved |
| Conversation store | Raw input and output | Prohibited by default |

## 7. External Dependencies

Every model, hosting, analytics, monitoring, identity, or content provider must have:

- documented data fields and transfer regions;
- timeout, retry, and circuit-breaker behavior;
- approved retention and training-use settings;
- credential rotation and revocation;
- failure-mode and data-leakage tests;
- an exit or replacement plan.

## 8. Failure Behavior

- Model unavailable: return a controlled service-unavailable message and emergency fallback.
- Content source unavailable: do not fabricate content or citations.
- Safety layer unavailable: fail closed and do not call normal generation.
- Audit sink unavailable: follow an approved fail-open or fail-closed rule based on event class; decision TBD.
- Unknown user location: never guess an emergency number.
- Invalid configuration: block startup or deployment for safety-critical settings.

## 9. Deployment Environments

- Local: synthetic data only; no production credentials.
- Test: isolated services and synthetic evaluation datasets.
- Staging: production-like controls; no real user health data unless separately approved.
- Production: approved providers, regions, access controls, monitoring, rollback, and incident response.

Configuration and credentials must not be shared across environments.

## 10. Architecture Approval Gate

Architecture is approved only after:

- product scope and jurisdictions are resolved;
- data inventory and processor review are complete;
- safety controls have independent failure paths;
- API and data contracts are versioned;
- testing and observability plans cover every safety control;
- clinical, privacy, security, product, and engineering owners sign off.

