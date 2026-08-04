# 37 - Provenance-Gated Content Generation

## Purpose

Create visible content previews from reviewed medical facts without allowing the generator to
invent unsourced medical claims or bypass the configured domain.

## Implemented

1. Content briefs with topic, hook, approved facts, CTA, duration, language, and style.
2. Mandatory medical-review approval before script generation.
3. Mandatory HTTP source and approval ID for every medical fact.
4. Deterministic script assembly from approved material.
5. A second domain-guard check after the final narration is assembled.
6. Atomic project-local artifact storage with path traversal protection.
7. Script text, machine-readable storyboard JSON, and browser-openable HTML preview artifacts.
8. HTML escaping for titles, scenes, and source text.
9. Explicit `preview_only=true` metadata. A storyboard is never reported as a rendered video.

## Visible Output

Generated previews are stored under:

`data/artifacts/previews/<content-id>/index.html`

That file can be opened directly in a browser after a brief is generated through the upcoming
operator API/dashboard.

## Verification

- Approval, source, domain, path, and HTML-safety tests pass.
- Full-suite regression and coverage are required before commit.

## Not Yet Claimed

- No voice synthesis provider is configured.
- No image/video generation provider is configured.
- No MP4 renderer is configured.
- No preview can be published to a social platform.

