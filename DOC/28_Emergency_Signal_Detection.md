# 28. Emergency Signal Detection

## Purpose

Emergency signal detection defines the internal contract for identifying possible emergency language before any normal medical response is considered.

This contract does not approve diagnosis, triage, treatment, or a complete emergency workflow.

## Decision Shape

1. `status`: `no_signal`, `possible_emergency`, or `unavailable`
2. `route`: bounded API route category
3. `categories`: bounded synthetic category names only
4. `detector_version`: immutable detector version

Raw user text, matched phrases, hidden thresholds, and model reasoning must not be included in the decision object.

The runtime model rejects inconsistent status/route pairs. A possible-emergency decision requires 1 to 16 machine categories; each category is limited to 64 lowercase letters, digits, dots, underscores, or hyphens. Non-emergency decisions cannot carry categories.

## Default Behavior

The default detector is unavailable and routes to `service_unavailable`. This keeps the app fail-closed until an approved classifier and evaluation suite exist.

## Reference Detector

The keyword detector is a deterministic reference implementation for tests and plumbing. It is not enough for production emergency detection because keyword lists miss paraphrases, multilingual phrasing, slang, negation, and context.

## Required Evidence Before Activation

1. emergency scenario suite by supported locale;
2. false-negative and false-positive evaluation;
3. mixed-language and misspelling coverage;
4. clinician-reviewed escalation copy;
5. emergency resource registry integration;
6. monitoring for unavailable detector state;
7. rollback plan for detector or policy failures.

## Current Evaluation Evidence

The engineering-only synthetic baseline passes the deterministic keyword reference detector. The synthetic challenge suite fails as intended with `0%` emergency recall, `50%` false-positive rate, and `25%` case pass rate. This is direct evidence that the keyword implementation is plumbing, not an approved detector.

See `32_Emergency_Evaluation_Harness.md` for commands, report boundaries, and remaining evidence.
