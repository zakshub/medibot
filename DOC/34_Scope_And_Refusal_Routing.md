# 34. Scope and Refusal Routing

## 34.1 Purpose

Scope routing provides bounded `unsupported` and `prohibited` responses after emergency processing. It does not define the real product scope, decide what conduct is prohibited, or activate normal medical guidance.

The current categories and keywords are synthetic test plumbing only. DEC-002 and the related clinical, product, legal, and safety decisions remain unresolved.

## 34.2 Decision Contract

`ScopeSignalDecision` contains only:

1. status: `no_signal`, `unsupported`, `prohibited`, or `unavailable`;
2. matching route: `information`, `unsupported`, `prohibited`, or `service_unavailable`;
3. one to sixteen bounded machine categories only for detected scope outcomes;
4. immutable detector version.

Status and route combinations are validated. Categories allow only lowercase letters, digits, dots, underscores, and hyphens up to 64 characters. Raw text, matched phrases, thresholds, and reasoning are excluded.

## 34.3 Default and Reference Detectors

`EmptyScopeSignalDetector` always returns unavailable and is the application default.

`KeywordScopeSignalDetector` exists only for deterministic synthetic tests. If synthetic unsupported and prohibited phrases both match, prohibited takes precedence. This precedence is test plumbing, not an approved real policy.

## 34.4 Policy Gates

1. Scope routing requires an active immutable `message.safety` policy.
2. The policy must still permit emergency routing and pin the emergency detector version.
3. Unsupported or prohibited routes require explicit policy permission.
4. At least one exact scope-detector version must be pinned when either scope route is enabled.
5. A detected route not listed in policy fails closed.
6. Configuration metadata alone cannot permit a route or detector.

## 34.5 Processing Order

1. Validate policy, emergency permission, country, and emergency detector.
2. Return emergency immediately for a valid possible-emergency decision and approved matching resource.
3. Continue only when the emergency detector returns `no_signal`.
4. If no scope route is enabled, keep normal medical guidance unavailable.
5. Evaluate the scope detector and verify its exact policy-pinned version.
6. Return only the policy-permitted unsupported or prohibited response.

This ordering prevents a refusal classifier from hiding or replacing emergency guidance.

## 34.6 Response Boundaries

### Unsupported

1. States that the request is outside approved scope.
2. Provides no medical answer, diagnosis, treatment, or source.
3. Directs the user to an appropriate qualified professional or trusted service.

### Prohibited

1. States that Medibot cannot help with the request.
2. Provides no instructions, medical guidance, or source.
3. Directs the user to a safe and lawful source of support.

Both are HTTP `200` handled responses only after every gate passes. Missing permissions, unavailable detectors, version mismatches, route mismatches, and exceptions return sanitized HTTP `503`.

## 34.7 Audit and Privacy

Audit events contain request ID, returned route, bounded outcome, and active policy version only. Scope categories, user text, matched keywords, detector exceptions, and response text are excluded.

Bounded outcomes distinguish unavailable detector, unpermitted version, unpermitted route, dependency failure, unsupported response, and prohibited response.

## 34.8 Evidence

Automated tests cover:

1. status, route, category, and version validation;
2. unavailable default behavior;
3. synthetic unsupported, prohibited, no-signal, and precedence decisions;
4. policy detector-version requirements;
5. emergency-first processing;
6. unavailable, unpinned, unpermitted, and failing dependencies;
7. bounded response fields and no sources;
8. HTTP status, request ID, active policy version, audit outcome, and raw-text exclusion.

## 34.9 Remaining Work

1. Approve exact intended use and excluded use cases.
2. Approve prohibited categories and refusal wording.
3. Build clinically and legally reviewed multilingual evaluation cases.
4. Evaluate emergency interactions, ambiguity, negation, and adversarial phrasing.
5. Pin a production detector adapter and immutable version.
6. Obtain product, clinical, legal, privacy, security, and operations approval.
