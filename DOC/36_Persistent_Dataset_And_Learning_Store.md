# 36 - Persistent Dataset and Learning Store

## Scope

This batch adds the persistent foundation for an operator-supplied medical video dataset and
future platform-learning signals.

## Implemented

1. Versioned SQLite schema for domain profiles, video records, platform insights, and schedule
   decisions.
2. Atomic dataset registration. A rejected candidate leaves no partial import.
3. Persistent domain allowlists and blocked terms.
4. Safe JSON manifest schema with bounded field lengths and at most 1,000 videos per import.
5. Duplicate candidate-ID and normalized content detection.
6. Optional source-video hashing for exact asset duplicate detection.
7. Dataset-root confinement that rejects path traversal.
8. Explicit supported input types: MP4, MOV, MKV, and WebM.
9. Video lifecycle states from imported through published or failed.
10. Persisted engagement inputs and scheduling history for restart-safe learning.

## Manifest Shape

~~~json
{
  "schema_version": 1,
  "domain": {
    "name": "medical",
    "allowed_topics": ["sleep"],
    "allowed_keywords": ["sleep", "health"],
    "blocked_keywords": ["casino"]
  },
  "videos": [
    {
      "candidate_id": "sleep-001",
      "topic": "sleep",
      "title": "Sleep health basics",
      "script": "A reviewed script...",
      "source_path": "videos/sleep-001.mp4",
      "duration_seconds": 30,
      "language": "en",
      "style_tags": ["short", "explainer"]
    }
  ]
}
~~~

## Verification

- 153 full-suite tests passed.
- 99.71% total Python coverage.
- Ruff passed.
- Git diff whitespace verification passed after EOF normalization.

## Boundaries

- SQLite is the local/default store, not the final horizontally scaled production database.
- File metadata and hashes are extracted; visual/audio embeddings are not implemented yet.
- No dataset may become publishable solely because it imported successfully.
- Credentials and private source videos remain excluded from Git.

