# 27. Emergency Resource Registry

## Purpose

The emergency resource registry defines how Medibot may store and select reviewed emergency-help instructions by country and locale.

This is a safety contract only. It does not activate emergency triage, medical advice, diagnosis, or real-time routing.

## Required Record Fields

1. `resource_id`: stable resource identifier
2. `version`: immutable content version
3. `country_code`: two-letter ISO-style country code
4. `locale`: locale for the instructions
5. `service_name`: reviewed public-facing service label
6. `contact_instructions`: reviewed instructions for the user
7. `source_url`: authoritative source
8. `source_owner`: source publisher or accountable owner
9. `status`: `draft`, `approved`, or `retired`
10. `approved_by`: accountable reviewer for approved records
11. `approved_at`: timezone-aware approval timestamp
12. `expires_at`: timezone-aware expiry timestamp

## Serving Rules

1. Draft and retired records are never servable.
2. Approved records require reviewer, approval timestamp, and expiry timestamp.
3. Expired records are never servable.
4. Country and locale selection must be exact after normalization.
5. Unknown country or locale must fail closed.
6. Duplicate country, locale, resource ID, and version combinations are rejected.
7. If multiple current approvals exist, the latest approval timestamp wins.

## Current Implementation Boundary

The application defaults to an empty emergency resource registry. This means no emergency resource can be returned unless an approved registry is explicitly injected.

Tests use synthetic examples only. The repository must not add real emergency phone numbers until source verification, jurisdiction review, update cadence, and legal ownership are approved.

## Release Gate

Before any emergency-facing behavior ships, the release evidence must include:

1. reviewed source ownership;
2. country and locale coverage list;
3. expiry and refresh procedure;
4. regression tests for unknown location;
5. monitoring for stale or missing emergency resources;
6. clinical, legal, and product approval.
