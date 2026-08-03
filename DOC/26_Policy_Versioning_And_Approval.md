# 26 - Policy Versioning and Approval

## 1. Purpose

Safety and routing policy must be explicit evidence, not an environment string or mutable prompt. Every active policy requires an immutable identity, approved routes, accountable reviewer, and bounded effective window.

## 2. Policy Contract

`PolicyVersion` requires:

- stable policy ID and immutable version;
- draft, approved, or retired status;
- explicit permitted response routes;
- explicit permitted detector versions when the emergency route is enabled;
- explicit permitted scope-detector versions when unsupported or prohibited routes are enabled;
- named approver;
- timezone-aware approval, effective, and expiry timestamps;
- effective time at or after approval;
- expiry later than effective time.

Only an approved policy inside its effective window is active. Draft, retired, incomplete, not-yet-effective, expired, or timezone-ambiguous policy is inactive.

An emergency route without at least one pinned detector version is invalid. Detector versions cannot be attached to a policy that does not permit the emergency route. This prevents an arbitrary injected detector from becoming active under a route-only approval.

Unsupported or prohibited routes similarly require at least one pinned scope-detector version. Scope-detector versions are invalid without one of those routes. A detector decision still cannot return a route omitted from the active policy.

## 3. Current Runtime

The application factory receives `PolicyRepository` explicitly and defaults to `EmptyPolicyRepository`, which returns no active policy. `InMemoryPolicyRepository` provides deterministic immutable-policy plumbing for tests and reviewed static publication. It rejects duplicate policy ID/version pairs, filters inactive windows, and selects the most recently effective active version.

The existing `MEDIBOT_POLICY_VERSION` value is fallback response metadata only and cannot activate policy, readiness, or a route. When an injected repository has an active policy, that immutable policy version becomes the response and readiness version.

## 4. Publication Gate

Before a non-empty production policy repository is connected:

- route semantics and emergency behavior are clinically approved;
- policy publication and rollback permissions are separated;
- versions are immutable and auditable;
- evaluation evidence is tied to the exact policy version;
- activation/expiry clocks and timezone behavior are tested;
- readiness requires both active policy and implemented medical behavior;
- rollback to a previously evaluated policy is verified.
