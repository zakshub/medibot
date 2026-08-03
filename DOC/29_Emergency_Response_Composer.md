# 29. Emergency Response Composer

## Purpose

The emergency response composer defines how a possible emergency signal and an approved emergency resource may become a bounded user-facing response.

This does not approve triage, diagnosis, severity assessment, treatment advice, or automatic emergency-service contact.

## Inputs

1. request ID;
2. policy version;
3. emergency signal decision;
4. approved emergency resource for the user's country and locale.

## Output Rules

1. Return `emergency` only when the decision status is `possible_emergency` and an approved resource is available.
2. Return `service_unavailable` when the detector is unavailable, the signal is absent, or no approved resource exists.
3. Include no raw user message, matched phrase, hidden threshold, or classifier reasoning.
4. Include only reviewed resource title, URL, version, and contact instructions.
5. State that Medibot cannot assess severity, diagnose, or confirm an emergency.

## Current Boundary

The composer is connected to the live message orchestration path. It returns an emergency response only when every policy, route permission, detector-version permission, location, detector, and approved-resource gate passes. The default application has empty policy, detector, and resource implementations, so it still returns `503` and cannot activate emergency or general medical behavior through configuration alone.

Normal health-information guidance remains unavailable. The guarded integration is implementation plumbing, not production approval.

## Required Evidence Before Endpoint Use

1. approved emergency signal detector;
2. approved emergency resource registry coverage;
3. locale-reviewed emergency wording;
4. synthetic unknown-country and dependency-failure tests;
5. audit events proving raw health text is excluded;
6. clinical, legal, and product approval.
