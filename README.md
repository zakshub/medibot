# MediLoop

MediLoop is a domain-locked, self-learning medical video automation system. An operator supplies
an initial reviewed video dataset. The system uses that evidence to plan new videos, renders
guarded previews, schedules one to five posts per day, publishes through platform adapters, and
feeds normalized performance insights into the next topic, style, duration, and timing decision.

The system fails closed. It cannot approve unrendered media, leave the configured medical domain,
publish a silent preview, or make a live platform request without the required review records,
artifact hash, credentials, and platform configuration.

## Honest Status

- Local implementation: **65% done, 35% remaining**.
- Production readiness: **25% done, 75% remaining**.
- No live social-platform request has been made and no social API credits have been consumed.
- Local preview rendering is credit-free and runs through bundled FFmpeg/Pillow code.

Implemented now:

- strict domain profiles and blocked-topic enforcement;
- operator-supplied dataset manifests, source confinement, and duplicate hashing;
- SQLite persistence for videos, insights, approvals, and schedule decisions;
- reviewed-fact and source-gated script/storyboard generation;
- real vertical H.264 MP4 preview rendering;
- rendered/hash-verified medical approval transitions;
- explainable online learning and one-to-five daily anti-spam control;
- YouTube, Instagram, Facebook, and X adapter contracts;
- normalized platform insight ingestion;
- idempotent publication jobs with bounded retry behavior;
- responsive operator dashboard and authenticated operator API boundary.

Still required for a live deployment:

- a selected narration/voice provider and generated audio track;
- S3-compatible or another approved cloud artifact store;
- an always-on scheduler/worker process;
- operator-owned OAuth credentials, platform IDs, quotas, and app approvals;
- live adapter sandbox verification;
- policy revision history, revocation, audit export, and rollback UI;
- deployment, monitoring, backup, retention, and accountable medical review sign-off.

See [DOC/10_Status_Tracker.md](DOC/10_Status_Tracker.md) for workstream percentages and evidence.

## See The Result

Requires Python 3.11 or newer.

```powershell
python -m pip install -e ".[dev,media]"
python -m uvicorn medibot.main:app --reload
```

Open:

- `http://127.0.0.1:8000/` for the MediLoop video studio;
- `http://127.0.0.1:8000/docs` for the API contract;
- `http://127.0.0.1:8000/legacy` for the preserved earlier chatbot UI.

In the video studio:

1. Save the allowed medical domain.
2. Import the initial dataset JSON. Optional video files must exist under `data/dataset/`.
3. Supply reviewed facts and generate a local MP4 preview.
4. Inspect the MP4 and storyboard.
5. Approve only the rendered output.
6. Ask the learning planner to recommend and reserve the next slot.
7. Add platform insights through the API so the next decision can adapt.

Generated previews are stored under `data/artifacts/`; SQLite state is stored under
`data/runtime/`. Their generated contents are intentionally ignored by Git.

## Core Flow

```text
reviewed seed dataset
        |
        v
domain guard -> script + sources -> storyboard -> local MP4
        |                                      |
        |                                      v
        +-------------------------- medical approval
                                               |
                                               v
adaptive 1-5/day schedule -> platform adapter -> insights
             ^                                      |
             +--------------------------------------+
```

## Verification

```powershell
python -m ruff check .
python -m pytest -p no:asyncio --basetemp=.test-tmp
```

The tests cover domain rejection, duplicate content, path traversal, provenance, rendering,
exact MP4 dimensions, approval gates, schedule concurrency, learning behavior, platform request
contracts, retries, API authentication, desktop/mobile UI behavior, and legacy-route preservation.

## Repository Layout

```text
medic/
|-- src/medibot/       application, automation, adapters, and browser assets
|-- tests/             unit, integration, API, security, and UI tests
|-- data/dataset/      operator-owned seed videos (generated/private contents ignored)
|-- data/artifacts/    generated storyboards and MP4 files (ignored)
|-- data/runtime/      SQLite state and local logs (ignored)
|-- DOC/               numbered product and engineering documentation
|-- evaluations/       inherited synthetic safety evaluation fixtures
`-- scripts/           verification commands
```

## Safety Boundary

MediLoop generates educational media only from an explicit configured domain and reviewed facts.
It is not a medical device and must not generate diagnosis, emergency decisions, individualized
treatment, or unreviewed medical claims. Production activation requires accountable medical,
privacy, legal, security, and platform approval outside this codebase.
