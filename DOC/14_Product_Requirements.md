# 14 - Product Requirements

## 1. Document Status

- Status: Draft
- Product owner: TBD
- Clinical safety owner: TBD
- Privacy owner: TBD
- Engineering owner: TBD
- Approval date: TBD

No implementation requirement in this document is approved while its owner or required decision is marked `TBD`.

## 2. Product Intent

Medibot is intended to provide conversational health-information assistance within a deliberately limited, reviewed scope. Its exact medical function must be selected before application development begins.

Medibot is not assumed to diagnose, prescribe, replace a clinician, or manage emergencies.

## 3. Decisions Required

| ID | Decision | Required owner | Status |
|---|---|---|---|
| PRD-001 | Primary user group and minimum user age | Product + clinical | TBD |
| PRD-002 | Supported countries and jurisdictions | Product + legal | TBD |
| PRD-003 | Supported languages | Product + clinical | TBD |
| PRD-004 | Supported channels: web, mobile, messaging, or API | Product + engineering | TBD |
| PRD-005 | Allowed health-information use cases | Product + clinical | TBD |
| PRD-006 | Whether personal health data is stored | Privacy + security | TBD |
| PRD-007 | Model and health-content data providers | Engineering + privacy | TBD |
| PRD-008 | Emergency resources by user location | Clinical + legal | TBD |

## 4. Proposed Allowed Use Cases

These are candidates, not approved medical functions:

- explain general health terms in plain language;
- help users prepare non-diagnostic questions for a qualified clinician;
- summarize user-provided non-sensitive educational text;
- provide reviewed navigation to appropriate levels of care;
- provide reviewed wellness and prevention information from approved sources.

Each allowed use case requires a named owner, authoritative content sources, acceptance tests, and harmful-output tests.

## 5. Prohibited Use Cases

Unless formally approved through clinical, legal, privacy, and engineering review, Medibot must not:

- claim to diagnose or rule out a condition;
- prescribe medication, dosage, or treatment;
- tell a user to ignore or delay professional care;
- provide autonomous emergency triage;
- make decisions for children or vulnerable users without approved safeguards;
- process uploaded medical records or images;
- infer pregnancy, disability, mental-health status, or other sensitive traits;
- use user health information for advertising or unrelated profiling;
- present model output as reviewed by a clinician when it was not.

## 6. Core User Flow

1. Show the service scope, limitations, and privacy notice.
2. Obtain required consent before collecting any user input.
3. Accept a supported health-information question.
4. Check for emergency or prohibited-use indicators before generating a normal response.
5. For possible emergencies, stop the normal flow and show location-appropriate emergency guidance.
6. For supported questions, generate a bounded informational response with uncertainty disclosed.
7. Cite or identify the approved source basis where applicable.
8. Offer an appropriate next step, including professional care when warranted.
9. Apply the approved retention or deletion rule to conversation data.

## 7. Emergency Behavior

Emergency detection must be treated as a safety control, not proof that an emergency exists or does not exist.

When an emergency indicator is detected, the system must:

- avoid diagnosis and extended conversational questioning;
- advise the user to contact local emergency services or an available trusted person;
- display only verified location-specific numbers when location is known;
- provide a safe generic instruction when location is unknown;
- avoid implying that failure to detect an indicator means the situation is safe;
- log only the minimum approved event data without unnecessary health content.

Exact wording, trigger policy, supported locations, and clinical review evidence are TBD.

## 8. Functional Requirements

| ID | Requirement | Verification |
|---|---|---|
| FR-001 | The system displays scope and limitations before the first health interaction. | UI or API integration test |
| FR-002 | Unsupported requests receive a clear refusal and safe next step. | Policy test suite |
| FR-003 | Emergency indicators route to the approved emergency response. | Safety evaluation suite |
| FR-004 | Normal responses distinguish general information from medical advice. | Content evaluation |
| FR-005 | The system does not claim certainty unsupported by approved sources. | Adversarial evaluation |
| FR-006 | Users can request deletion where data is retained and deletion rights apply. | End-to-end privacy test |
| FR-007 | External data processors are disclosed before sensitive data transfer. | Privacy review + integration test |
| FR-008 | Safety-critical content changes are versioned and auditable. | Change-control audit |

## 9. Non-Functional Requirements

Numeric targets remain TBD until channel, model, hosting, and jurisdictions are selected.

- Availability: define target and maintenance behavior.
- Latency: define percentile targets for normal and emergency responses.
- Accessibility: select the required standard and test supported interfaces.
- Security: authenticate privileged access and protect data in transit and at rest.
- Privacy: minimize collection and enforce approved retention and deletion.
- Reliability: fail safely when models, content sources, or downstream services are unavailable.
- Observability: monitor failures and safety-control performance without leaking sensitive data.
- Localization: medically review translated safety and emergency content.

## 10. Acceptance Criteria for Product Definition

Batch 2 is complete only when:

- all decisions in Section 3 have named accountable owners and resolved values;
- allowed and prohibited use cases are approved;
- emergency behavior is reviewed for each supported jurisdiction and language;
- functional requirements have objective tests;
- privacy and retention decisions are recorded;
- product, clinical, legal/privacy, and engineering owners approve this document.

## 11. Explicit Non-Goals for the First Release

Until product owners replace this section with approved scope, the first release excludes:

- diagnosis and differential diagnosis;
- prescribing and medication dosing;
- autonomous triage;
- integration with electronic health records;
- analysis of medical images, laboratory reports, or uploaded records;
- continuous patient monitoring;
- unsupervised use as a clinical decision-support system.

