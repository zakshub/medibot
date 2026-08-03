# 19 - Testing and Evaluation Strategy

## 1. Purpose

Testing must demonstrate both normal product behavior and safe behavior under ambiguity, misuse, dependency failure, and adversarial input. Passing unit tests alone is not release evidence for a medical-information system.

## 2. Test Layers

| Layer | Main purpose | Required evidence |
|---|---|---|
| Static checks | Formatting, types, dependency and secret scanning | Automated CI result |
| Unit tests | Deterministic policy, validation, redaction, and formatting | Coverage and test report |
| Contract tests | API schemas, error codes, version compatibility | Schema and consumer results |
| Integration tests | Model, content, identity, logging, and failure boundaries | Isolated service results |
| End-to-end tests | Approved user flows across supported clients | Release-environment report |
| Safety evaluations | Harmful, prohibited, emergency, and adversarial behavior | Versioned evaluation report |
| Privacy/security tests | Data leakage, access, retention, deletion, and abuse | Review and remediation record |
| Human review | Clinical meaning, comprehension, localization, accessibility | Named reviewer approval |

## 3. Deterministic Test Requirements

- input schema and maximum-size enforcement;
- locale and country allow lists;
- route and error-code mapping;
- no raw health content in logs, errors, or audit events;
- safety-layer outage fails closed;
- content outage does not produce invented citations;
- emergency fallback works without model access;
- policy and content versions appear in permitted audit metadata;
- invalid safety configuration blocks startup or deployment.

## 4. Safety Evaluation Categories

- emergency and self-harm indicators;
- diagnosis, medication, dosage, and treatment requests;
- delayed-care and false-reassurance traps;
- vulnerable-user and caregiver scenarios;
- mixed-language, misspelled, slang, and incomplete input;
- instruction injection and role impersonation;
- fabricated citation and certainty pressure;
- multi-turn boundary erosion;
- dependency timeout, malformed response, and stale content;
- requests involving unsupported countries or locales.

## 5. Evaluation Dataset Record

Every dataset version must record:

- owner and reviewers;
- source and whether data is synthetic;
- intended and prohibited uses;
- supported languages and populations;
- known gaps and representation limits;
- expected route and allowed response properties;
- severity weighting;
- version, change history, and retirement rule.

Real health conversations are prohibited unless separately approved with documented provenance, legal basis, minimization, access, and deletion controls.

## 6. Metrics

Targets are TBD and require clinical/product approval.

- emergency false-negative rate;
- emergency false-positive rate;
- prohibited-response violation rate;
- unsupported-certainty rate;
- fabricated-source rate;
- safe refusal and next-step quality;
- raw-sensitive-data leakage rate;
- response latency percentiles by route;
- dependency and safety-control availability;
- performance by locale and evaluated user group.

Aggregate metrics must not hide catastrophic individual failures. Every severe failure requires case review.

### Implemented Engineering Harness

The current synthetic emergency harness reports total pass rate, emergency recall, false-positive rate, unavailable rate, and individual bounded failure categories. It pins dataset and detector versions and returns a non-zero exit code when thresholds fail.

The baseline dataset verifies plumbing only. The challenge dataset intentionally demonstrates keyword-detector failures under negation, misspelling, and mixed language. Neither dataset has clinical review or enough coverage to set production thresholds.

## 7. Regression Policy

- Pin model, prompt, policy, content, and evaluation versions for each report.
- Run deterministic checks on every proposed change.
- Run affected safety suites for content and policy changes.
- Run the full release suite for model/provider, architecture, or supported-locale changes.
- Block release when a previously passing catastrophic or critical case fails.
- Record approved threshold changes with rationale and accountable reviewers.

## 8. Human Review

Qualified reviewers must evaluate:

- medical correctness and harmful ambiguity;
- whether limitations are understandable;
- emergency and care-escalation wording;
- localized meaning, cultural context, and reading level;
- accessibility of critical notices;
- whether citations support the actual claim.

Reviewers must assess frozen output from identified system versions, not an untracked live system.

## 9. CI Release Gates

Current CI blocks merge on code, test, dependency, and package regressions. A future release pipeline must additionally block release on:

- formatting, type, unit, or contract failures;
- detected credentials or prohibited data files;
- vulnerable dependency above the approved severity threshold;
- required safety evaluation regression;
- missing policy/content version metadata;
- missing required clinical, privacy, security, or product approval.

## 10. Release Evidence Package

Each release candidate must include:

- commit and build identifiers;
- configuration, model, prompt, policy, and content versions;
- deterministic test reports;
- safety and privacy evaluation reports;
- unresolved defects and accepted residual risks;
- reviewer names and approval timestamps;
- rollback target and verified rollback procedure.
