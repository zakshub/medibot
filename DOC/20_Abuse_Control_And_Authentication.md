# 20 - Abuse Control and Authentication

## 1. Status

- Status: Draft
- Authentication owner: TBD
- Edge rate-limit provider: TBD
- Shared limiter store: TBD

## 2. Current Backstop

The application includes a per-process fixed-window limiter for `/v1/messages`. It:

- uses the direct network peer address;
- ignores user-controlled forwarding headers;
- returns a bounded `429 RATE_LIMITED` response;
- includes `Retry-After`, `X-Request-ID`, and no-store headers;
- uses an asynchronous lock to keep increments consistent inside one process;
- removes expired client windows during new-window creation.

This limiter is defense in depth only. Counts are not shared across processes, hosts, regions, or restarts.

## 3. Production Requirement

Production must add a trusted edge or shared-store limiter that:

- identifies the client only after trusted-proxy processing;
- enforces global and endpoint-specific limits across all instances;
- supports bounded burst and sustained limits;
- does not use health content as a rate-limit key;
- has timeout and outage behavior defined;
- exposes aggregate metrics without raw IP or health content;
- is tested for concurrency and distributed consistency.

## 4. Proxy Boundary

The application must not trust `X-Forwarded-For`, `Forwarded`, or similar headers from arbitrary clients. A production deployment must define the exact trusted proxy chain and strip externally supplied forwarding headers before adding verified values.

## 5. Authentication Boundary

The public health-information flow is not assumed to require an account. Administrative functions must require strong authentication and authorization before they are created.

Minimum administrative controls:

- phishing-resistant multi-factor authentication where available;
- least-privilege roles separated by content, clinical approval, and deployment duties;
- short-lived sessions and credential rotation;
- immutable audit records for policy/content publication and rollback;
- no authorization decision based only on client-supplied role or identity fields.

## 6. Rate-Limit Contract

```json
{
  "request_id": "opaque identifier",
  "error": {
    "code": "RATE_LIMITED",
    "message": "Too many requests. Try again later."
  }
}
```

The response uses HTTP `429` and a positive integer `Retry-After` header. It must not echo the request, client address, account identifier, or limiter key.

## 7. Abuse Categories

- high-volume automated requests;
- distributed requests intended to bypass per-client limits;
- prompt injection and safety-boundary probing;
- credential stuffing against future authenticated endpoints;
- oversized, malformed, or slow request bodies;
- repeated emergency-flow triggering intended to exhaust services;
- scraping reviewed content or source metadata;
- attempts to force sensitive data into logs, metrics, or error responses.

## 8. Release Gate

Before normal medical-information responses are enabled:

- trusted proxy behavior is configured and tested;
- distributed rate limiting is enabled;
- administrative authentication and authorization are reviewed;
- abuse alerts, escalation ownership, and retention are documented;
- limiter failure behavior is tested;
- privacy review confirms limiter keys and telemetry are minimized.

