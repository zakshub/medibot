# 42 - Cloud Artifacts and Durable Workers

## Cloud Artifact Boundary

`S3ArtifactStore` mirrors local reviewed artifacts into an S3-compatible object store through an
injected client. Local rendering remains the staging boundary; cloud storage never receives an
artifact until its local byte length and SHA-256 match the stored record.

Every upload:

1. validates a relative path-safe object key;
2. reads and hashes the exact bytes being uploaded;
3. stores SHA-256 as object metadata;
4. requires AES-256 server-side encryption or a configured KMS key;
5. checks remote content length and SHA-256 metadata after upload;
6. returns a bounded `s3://` identity without credentials.

Downloads are accepted only when their bytes match an expected SHA-256. Signed download URLs are
limited to 60-3600 seconds and must be HTTPS unless an explicitly local-compatible store disables
that rule.

The optional `medibot[cloud]` extra provides boto3. Credentials are intentionally absent from the
artifact object, settings model, job payloads, database, logs, and test fixtures. A live client uses
the cloud provider's normal environment/role credential chain.

## Durable Queue States

```text
queued -> leased -> completed
             |  -> failed
             +  -> retry_wait -> leased
queued/retry_wait -> cancelled
expired leased -> leased by another worker
```

The SQLite queue provides:

- a unique idempotency key for every logical job;
- exclusive `BEGIN IMMEDIATE` claims across worker processes;
- 30-second to one-hour leases;
- recovery after a worker lease expires;
- maximum attempts from 1 to 20;
- future retry availability;
- heartbeats owned by the current worker only;
- cancellation only before active execution;
- bounded JSON payload/result size of 64 KiB;
- recursive rejection of token, password, secret, credential, and API-key fields;
- sanitized error codes instead of raw exception bodies.

Supported job kinds are render, cloud mirror, publish, and insight collection. The durable engine is
implemented; live handlers still require approved cloud/platform configuration and an always-on
worker deployment.

## Operator Routes

- `POST /v1/video/jobs`
- `GET /v1/video/jobs/counts`
- `GET /v1/video/jobs/{job_id}`
- `POST /v1/video/jobs/{job_id}/cancel`

These routes share the same production `X-Operator-Key` security scheme as the rest of the operator
API. OpenAPI documents that requirement.

## Verification

Tests prove idempotent enqueue, collision rejection, cross-instance exclusive claims, stale-lease
recovery, old-owner rejection, heartbeat extension, retry delay, attempt exhaustion, cancellation,
secret rejection, bounded unknown failures, cloud encryption arguments, local tamper detection,
remote metadata mismatch detection, download hash checks, and unsafe URL/key rejection.

No live S3 request, cloud credential, storage charge, or social API call was used by these tests.
