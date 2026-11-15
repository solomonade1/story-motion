# ADR-0007 — FFmpeg provisioning and licensing (dev machine)

- **Status:** Accepted for development only. **Source:** PRD §10.2 "Packaging decision".

## Decision
The dev machine had no FFmpeg. A **pinned** build was fetched project-locally to `tools/ffmpeg/` (git-ignored):
Gyan.dev `ffmpeg-9.0.2-full_build.zip` from the URL in the winget manifest, SHA-256
`759d0a9831c436a0eb331ad36f236c06cb04aaa0005da46571f0e9d3d9206f6b` (verified after download). No system PATH or
registry change. `get_toolchain()` finds it via `STORYMOTION_FFMPEG_DIR`, then `tools/ffmpeg/bin`, then `PATH`,
and checks that the required filters/encoders exist.

## Licensing
That build is **GPL-3.0** (includes x264 etc.). That is fine for local development, but **redistributing it inside
an installer is a Phase 5 licence-review item** (PRD §10.2): choose between a GPL-compliant bundle, an LGPL build,
or a detect/install first-run flow.
