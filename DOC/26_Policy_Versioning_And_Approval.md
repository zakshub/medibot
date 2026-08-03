# 26 - Policy Versioning and Approval

## 1. Purpose

Safety and routing policy must be explicit evidence, not an environment string or mutable prompt. Every active policy requires an immutable identity, approved routes, accountable reviewer, and bounded effective window.

## 2. Policy Contract

`PolicyVersion` requires:

- stable policy ID and immutable version;
- draft, approved, or retired status;
- explicit permitted response routes;
- named approver;
- timezone-aware approval, effective, and expiry timestamps;
- effective time at or after approval;
- expiry later than effective time.

Only an approved policy inside its effective window is active. Draft, retired, incomplete, not-yet-effective, expired, or timezone-ambiguous policy is inactive.

## 3. Current Runtime

The application factory receives `PolicyRepository` explicitly and defaults to `EmptyPolicyRepository`, which returns no active policy. The existing `MEDIBOT_POLICY_VERSION` value is response metadata only and cannot activate policy or readiness.

## 4. Publication Gate

Before a non-empty production policy repository is connected:

- route semantics and emergency behavior are clinically approved;
- policy publication and rollback permissions are separated;
- versions are immutable and auditable;
- evaluation evidence is tied to the exact policy version;
- activation/expiry clocks and timezone behavior are tested;
- readiness requires both active policy and implemented medical behavior;
- rollback to a previously evaluated policy is verified.

