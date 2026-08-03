# 25 - Content Provenance and Approval

## 1. Purpose

Medical-information content must be attributable, reviewed, versioned, locale-specific, time-bounded, and removable. Model output alone is not approved content.

## 2. Required Content Record

Every record requires:

- stable content ID and immutable version;
- locale;
- plain title and bounded body;
- canonical HTTPS source URL;
- authoritative source owner;
- draft, approved, or retired status;
- named clinical approver and timezone-aware approval timestamp when approved;
- timezone-aware expiry timestamp later than approval.

Unknown fields, missing approval evidence, naive timestamps, expired records, drafts, and retired records are not servable.

## 3. Current Implementation

`ReviewedContent` enforces the provenance and approval contract. `ContentRepository` defines the read boundary. `EmptyContentRepository` is the current implementation and always returns no content, preserving fail-closed behavior until an approved source exists.

## 4. Publication Workflow

1. Create a draft from an identified authoritative source.
2. Verify license/use permission and jurisdiction/locale applicability.
3. Review medical meaning, limitations, reading level, and harmful ambiguity.
4. Record approver, approval time, expiry, and version.
5. Run content, safety, localization, and source-link tests.
6. Publish immutably with rollback target.
7. Monitor source changes and expiry.
8. Retire or replace content; never silently mutate an approved version.

## 5. Release Gate

Normal medical-information responses remain blocked until the production repository, publication permissions, source allow-list, expiry process, reviewer ownership, localization review, tests, monitoring, and rollback are approved.

