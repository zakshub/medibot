# 38 - Local Vertical MP4 Renderer

## Purpose

Provide a real, credit-free local MP4 preview path while keeping production publishing
fail-closed until voice and operator approval exist.

## Implemented

1. Optional `media` dependency group with Pillow and imageio-ffmpeg.
2. Vertical frame rendering with configurable even dimensions and frame rate.
3. Scene sequencing, title treatment, progress indicator, and safe text drawing.
4. H.264 MP4 output with YUV420p compatibility and fast-start metadata.
5. Output container signature, minimum size, and SHA-256 verification.
6. Explicit audio and publishability metadata.
7. Publishing guard that rejects silent/unapproved preview videos.
8. Duration cap of five minutes and bounded frame-rate validation.

## Result Form

The renderer creates a real `.mp4` file. The current renderer is intentionally a silent
storyboard preview and reports:

- `has_audio=false`
- `publishable=false`
- `voice_track_missing`
- `operator_publish_approval_missing`

## Verification

A test performs a real short MP4 encode and verifies the output container, dimensions, hash,
size, publishability gate, invalid jobs, and invalid renderer configuration.

## Remaining Media Work

- Voice synthesis provider.
- AI or licensed visual provider.
- Caption burn-in and audio normalization.
- Production render profile.
- Operator approval that changes a reviewed render to publishable.

