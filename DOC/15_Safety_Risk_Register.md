# 15 - Safety Risk Register

## 1. Purpose

This register tracks foreseeable harm from Medibot's product behavior, content, models, integrations, and operational processes. It does not replace qualified clinical, security, privacy, or legal review.

## 2. Scoring Method

- Severity: `1` negligible, `2` minor, `3` serious, `4` critical, `5` catastrophic.
- Likelihood: `1` rare, `2` unlikely, `3` possible, `4` likely, `5` frequent.
- Initial risk score: severity multiplied by likelihood before controls.
- Residual risk: reassessed after controls are implemented and verified.

Scores are planning aids. A low numeric score does not automatically make a medical risk acceptable.

## 3. Risk Register

| ID | Hazard and potential harm | S | L | Score | Required controls | Verification evidence | Owner | Status |
|---|---|---:|---:|---:|---|---|---|---|
| SAFE-001 | Incorrect diagnosis-like output causes delayed or harmful care | 5 | 4 | 20 | Prohibit diagnosis; bounded prompts; output policy; clinician-reviewed tests; safe escalation | Adversarial evaluation and clinical sign-off | Clinical safety | Open |
| SAFE-002 | Emergency language is missed and normal chat continues | 5 | 3 | 15 | Layered detection; conservative escalation; fail-safe response; monitored false negatives | Emergency scenario suite by language | Clinical + ML | Open |
| SAFE-003 | False emergency escalation creates distress or unnecessary service use | 3 | 3 | 9 | Calibrated policy; neutral wording; separate urgent and emergency routes | False-positive evaluation | Clinical + product | Open |
| SAFE-004 | Medication or dosage advice causes adverse effects | 5 | 3 | 15 | Refuse prescribing/dosing; detect medication requests; reviewed informational boundaries | Medication challenge set | Clinical safety | Open |
| SAFE-005 | Hallucinated source, clinician, or certainty misleads the user | 4 | 4 | 16 | Approved retrieval sources; citation validation; uncertainty disclosure; no fabricated attribution | Groundedness and citation tests | Content + ML | Open |
| SAFE-006 | Advice ignores age, pregnancy, allergies, disability, or comorbidity | 5 | 3 | 15 | Exclude personalized treatment; disclose limits; escalate context-dependent questions | Vulnerable-user safety suite | Clinical safety | Open |
| SAFE-007 | Translation changes medical or emergency meaning | 5 | 3 | 15 | Clinically reviewed translations; locale-specific content; no unreviewed machine-only safety text | Bilingual clinical review | Localization + clinical | Open |
| SAFE-008 | User interprets general information as clinician-reviewed advice | 4 | 4 | 16 | Persistent role disclosure; plain-language limitations; response structure separating information and next steps | Comprehension testing | Product + clinical | Open |
| SAFE-009 | Model or dependency outage removes a safety control | 5 | 2 | 10 | Safety checks outside optional model path; fail closed; static emergency fallback | Dependency-failure tests | Engineering | Open |
| SAFE-010 | Sensitive health data is disclosed, breached, or exposed in logs | 5 | 3 | 15 | Data minimization; encryption; access control; redaction; retention limits; incident response | Privacy and security testing | Privacy + security | Open |
| SAFE-011 | Prompt injection or retrieved content bypasses safety policy | 5 | 3 | 15 | Treat external content as untrusted; isolate instructions; output enforcement; adversarial testing | Injection evaluation suite | Security + ML | Open |
| SAFE-012 | Safety content changes without review or traceability | 4 | 3 | 12 | Version control; required reviewers; audit log; rollback; release gates | Change-control audit | Engineering + clinical | Open |

## 4. Release Rule

A risk may move from `Open` only when:

1. an accountable owner accepts responsibility;
2. controls are implemented or the exposure is removed;
3. verification evidence is recorded and reviewable;
4. residual severity and likelihood are reassessed;
5. the authorized clinical/product authority documents acceptance of residual medical risk.

No release is permitted with an unowned risk, missing verification evidence for a required control, or an unapproved catastrophic residual risk.

## 5. Evaluation Coverage

The safety evaluation set must include:

- direct and indirect emergency statements;
- misspellings, slang, mixed languages, and short messages;
- requests for diagnosis, dosage, and treatment;
- attempts to override policy or impersonate a clinician;
- ambiguous symptoms and missing context;
- vulnerable-user and caregiver scenarios;
- model, retrieval, network, and configuration failures;
- repeated turns that gradually move from allowed to prohibited scope.

Evaluation data must be synthetic or approved for its documented use.

