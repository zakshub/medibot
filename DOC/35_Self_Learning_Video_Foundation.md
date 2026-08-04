# 35 - Self-Learning Video Foundation

## Purpose

This batch realigns Medibot toward a domain-locked, self-learning medical video automation system.

The initial video dataset will be supplied by the operator. The system uses approved domain
configuration and observed platform performance to improve future scheduling decisions.

## Implemented

1. **Domain profile**
   - Explicit allowed topics.
   - Explicit domain keywords.
   - Explicit blocked keywords.
   - Empty allowlists are rejected.

2. **Fail-closed domain guard**
   - A candidate must use an allowed topic.
   - Its title or script must contain domain evidence.
   - Any blocked term rejects the candidate.
   - Out-of-domain candidates cannot enter the dataset or scheduler.

3. **Initial dataset catalog**
   - Registers approved video metadata.
   - Stores an import timestamp.
   - Rejects duplicate candidate IDs.
   - Normalizes topic, title, script whitespace, and case before hashing.
   - Rejects duplicate content under a different ID.

4. **Adaptive scheduler foundation**
   - Scores topics using view rate, average watch ratio, and weighted engagement.
   - Learns preferred posting hours from historical insights.
   - Uses a safe fallback time when evidence is absent.
   - Enforces a one-to-five posts-per-day policy.
   - Enforces at least a one-hour configurable gap.
   - Never overrides the domain guard.

## Verification

- Full suite: 145 tests passed.
- Total Python coverage: 99.88%.
- Ruff: clean.
- Git diff whitespace check: clean.

## Honest Limitations

This is a deterministic learning foundation, not a trained generative model.

The following are not implemented yet:

- Persistent SQL database.
- Video file upload and cloud object storage.
- Feature extraction from the operator''s initial videos.
- Script, voice, image, or rendered video generation.
- YouTube, Instagram, Facebook, or X publishing adapters.
- Platform insight ingestion.
- Exploration versus exploitation controls.
- Model/version rollback and learning audit history.
- Admin dashboard and approval workflow.

## Next Batch

1. Add SQLite persistence and migrations.
2. Add dataset manifest import.
3. Persist videos, insights, decisions, and domain-policy versions.
4. Expose guarded API endpoints for dataset registration and schedule recommendations.

