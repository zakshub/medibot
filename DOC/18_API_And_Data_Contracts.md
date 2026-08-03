# 18 - API and Data Contracts

## 1. Status

- Status: Draft contract
- Transport and framework: TBD
- Authentication model: TBD
- Persistence: Not approved

Examples define behavior and structure, not an approved production API.

## 2. Contract Rules

- Use an explicit version prefix such as `/v1`.
- Accept and return JSON with UTF-8 encoding.
- Reject unknown oversized or malformed payloads before model calls.
- Never expose provider credentials, internal prompts, stack traces, or safety thresholds.
- Return a stable machine-readable error code and a safe user-facing message.
- Do not echo raw health input in errors.

## 3. Health Check

`GET /v1/health`

Response:

```json
{
  "status": "ok",
  "version": "string"
}
```

Public health checks must not reveal dependency names, environment details, or configuration secrets.

## 4. Conversation Request

`POST /v1/messages`

```json
{
  "message": "string",
  "locale": "en-PK",
  "country_code": "PK",
  "consent_version": "string",
  "session_id": "optional opaque string"
}
```

Validation:

- `message`: required, trimmed, non-empty, maximum length TBD;
- `locale`: allow-listed BCP 47 value;
- `country_code`: optional allow-listed ISO 3166-1 alpha-2 value;
- `consent_version`: required only when the approved flow requires consent;
- `session_id`: random opaque value, never a phone number, email, or medical identifier.

## 5. Conversation Response

```json
{
  "request_id": "random opaque identifier",
  "route": "information",
  "message": "bounded user-facing response",
  "limitations": "general information, not a diagnosis",
  "sources": [
    {
      "title": "approved source title",
      "url": "https://approved.example/resource",
      "reviewed_version": "string"
    }
  ],
  "next_step": "string",
  "policy_version": "string"
}
```

Allowed `route` values:

- `information`;
- `unsupported`;
- `prohibited`;
- `urgent`;
- `emergency`;
- `service_unavailable`.

Clients must not convert `route` into a diagnosis or hide emergency guidance.

## 6. Error Contract

```json
{
  "request_id": "random opaque identifier",
  "error": {
    "code": "INVALID_REQUEST",
    "message": "The request could not be processed."
  }
}
```

Initial error codes:

| Code | HTTP status | Meaning |
|---|---:|---|
| INVALID_REQUEST | 400 | Shape, type, or field validation failed |
| UNSUPPORTED_LOCALE | 400 | Locale is not approved |
| UNAUTHORIZED | 401 | Required authentication failed |
| RATE_LIMITED | 429 | Request limit exceeded |
| SAFETY_SERVICE_UNAVAILABLE | 503 | Required safety control unavailable |
| SERVICE_UNAVAILABLE | 503 | Normal response cannot be produced safely |

## 7. Minimal Internal Safety Decision

```json
{
  "request_id": "opaque identifier",
  "route": "information",
  "policy_version": "string",
  "trigger_categories": ["bounded category"],
  "decision_time_ms": 0
}
```

Raw user text, hidden reasoning, detailed safety thresholds, and provider credentials must not be included in audit events.

## 8. Data Model Boundaries

### RequestEvent

- request ID;
- timestamp;
- approved locale and optional country code;
- policy/model/content version identifiers;
- route category;
- status and bounded error code;
- timing metrics.

### ReviewedContent

- stable content ID;
- title and locale;
- source owner and canonical source URL;
- clinical reviewer and review date;
- effective and expiry dates;
- version and publication status;
- content body or template.

### PolicyVersion

- stable policy ID and version;
- effective date;
- approved routes and controls;
- reviewer identities;
- immutable publication record;
- rollback target.

No `User`, `Patient`, `MedicalRecord`, or `ConversationHistory` entity is approved at this stage.

## 9. Compatibility Rules

- Additive optional response fields may be introduced within a version.
- Required-field removal, type changes, and semantic changes require a new API version.
- Route and error enums require tolerant clients plus documented rollout.
- Safety behavior changes require evaluation evidence even when the JSON schema is unchanged.

## 10. Contract Verification

- JSON schema validation for every request and response example;
- malformed, oversized, missing, and unknown-field tests;
- stable route and error-code tests;
- tests proving raw input is absent from errors and audit events;
- compatibility tests against supported client versions;
- failure tests for unavailable model, content, safety, and audit dependencies.

