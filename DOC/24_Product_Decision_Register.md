# 24 - Product Decision Register

## 1. Rule

Unknown product facts remain `TBD`. An engineering implementation, environment variable, or policy string cannot silently decide them.

## 2. Blocking Decisions

| ID | Decision | Required owners | Current status | Implementation unlocked when resolved |
|---|---|---|---|---|
| DEC-001 | Intended user groups and minimum age | Product + clinical | TBD | User flows and accessibility targets |
| DEC-002 | Exact allowed medical-information function | Product + clinical + legal | TBD | Normal response policy |
| DEC-003 | Supported countries/jurisdictions | Product + legal/privacy | TBD | Emergency resources and compliance controls |
| DEC-004 | Supported languages/locales | Product + clinical/localization | TBD | Localized reviewed content |
| DEC-005 | Whether accounts are required | Product + security/privacy | TBD | Authentication and user data model |
| DEC-006 | Whether conversation content is stored | Product + privacy/security | Default no | Persistence and deletion workflows |
| DEC-007 | Model/provider selection | Engineering + privacy/security + clinical | TBD | Model adapter and evaluation |
| DEC-008 | Approved health-content authorities | Clinical + legal/content | TBD | Content repository population |
| DEC-009 | Emergency trigger and wording policy | Clinical + legal + product | TBD | Emergency routing implementation |
| DEC-010 | Operating hours and human escalation | Operations + product + clinical | TBD | Support and incident commitments |

## 3. Decision Record Requirements

Every resolved decision must include:

- accountable owner and required reviewers;
- decision date and effective version;
- evidence and authoritative sources;
- alternatives considered and rejected;
- affected requirements, risks, data, architecture, tests, and documents;
- rollback or retirement condition;
- jurisdiction and locale scope;
- expiry/review date where the decision can become stale.

## 4. Current Effect

Because DEC-001 through DEC-010 are not fully resolved, Medibot remains fail closed. The application may expose liveness, readiness, schema, and bounded unavailable responses, but must not provide normal medical guidance.

