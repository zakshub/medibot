# 41 - Operator Dashboard and API

## Purpose

The root page is the operator surface for the domain-locked self-learning medical video system.
It replaces the earlier chatbot as the primary visible product without deleting that earlier work.
The chatbot remains available at `/legacy`.

## Browser Routes

| Route | Purpose |
| --- | --- |
| `/` | MediLoop video operator studio |
| `/video` | Alias for the video operator studio |
| `/legacy` | Preserved earlier chatbot UI |
| `/docs` | OpenAPI explorer |

## Operator API

| Method and route | Result |
| --- | --- |
| `GET /v1/video/status` | Counts, capabilities, blockers, and implementation estimate |
| `PUT /v1/video/domain` | Saves the explicit allowed and blocked medical domain |
| `POST /v1/video/dataset` | Imports a strict initial dataset manifest |
| `GET /v1/video/videos` | Lists seed, rendered, approved, scheduled, and published states |
| `POST /v1/video/previews` | Builds reviewed artifacts and a real local MP4 preview |
| `GET /v1/video/previews/{id}/storyboard` | Opens the CSP-restricted storyboard |
| `POST /v1/video/videos/{id}/approve` | Approves only rendered, hash-verified output |
| `POST /v1/video/insights` | Adds normalized performance evidence |
| `POST /v1/video/schedule/recommend` | Recommends and atomically reserves the next safe slot |
| `POST /v1/video/jobs` | Enqueues an idempotent durable automation job |
| `GET /v1/video/jobs/counts` | Returns queue counts by state |
| `GET /v1/video/jobs/{id}` | Returns bounded job state without credentials |
| `POST /v1/video/jobs/{id}/cancel` | Cancels only queued or retry-wait work |

## Security Boundary

- Local and test environments can use the operator API without a key for development.
- Production startup requires `MEDIBOT_OPERATOR_API_KEY`.
- Production operator reads and mutations require `X-Operator-Key`.
- Local artifact mounting is disabled outside local/test environments.
- Silent local previews remain non-publishable.
- Imported seed examples cannot be promoted directly into the publish queue.
- Only rendered output with an artifact path and SHA-256 can receive medical approval.
- Scheduling changes `approved` to `scheduled` in the same database transaction as reservation.

## Visual Verification

The UI was rendered against the live ASGI application in headless Edge through Playwright.

| Viewport | Client width | Scroll width | Result |
| --- | ---: | ---: | --- |
| Desktop | 1440 | 1440 | No horizontal overflow |
| Mobile | 390 | 390 | No horizontal overflow |

Both views loaded `OPERATIONAL LOCAL` status and the implementation estimate from the live API.
Generated QA screenshots remain under `data/artifacts/qa/` locally and are ignored by Git.

## Tested Workflow

1. Save a medical domain profile.
2. Import a seed example.
3. Prove that the unrendered seed cannot be approved.
4. Generate a one-second real MP4 and storyboard from reviewed facts.
5. Verify the MP4 container and exact dimensions.
6. Approve the rendered/hash-verified candidate.
7. Reserve the earliest cold-start schedule slot.
8. Add YouTube performance evidence.
9. Verify persisted video, insight, and schedule counts.
10. Verify production endpoints fail closed without the operator key.

## Remaining Boundary

The dashboard does not claim live production readiness. Voice/audio, live cloud configuration,
always-on worker handlers, platform credentials/app approvals, policy rollback, and live publishing
controls remain separate required workstreams.
