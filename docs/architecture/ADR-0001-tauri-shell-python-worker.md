# ADR-0001 — Tauri 2 shell + supervised Python media worker

- **Status:** Accepted (Phase 0). Shell implementation deferred to Phase 1.
- **Source:** PRD §10.1–10.3; Charter B3.

## Decision
Desktop shell = Tauri 2 + React/TypeScript (Phase 1). All media work (ffprobe, FFmpeg graphs, provider I/O)
lives in a **Python 3.11+ worker** (`workers/media/storymotion_media`) that the shell will launch as a
supervised subprocess with narrow commands. No HTTP service, no hosted backend, no Redis/Kubernetes.

## Phase 0 consequence
Phase 0 is **headless**: the worker is driven by a CLI (`python -m storymotion_media ...`). Building the Tauri
shell now would be Phase 1 scope. The Rust toolchain is also not installed on the dev machine (see
IMPLEMENTATION_STATUS), so Phase 1 must install and pin it.

## Why
Python has the media/provider SDK ecosystem; a subprocess is simpler to package than a loopback service and
keeps UI hangs away from rendering. The worker already has a clean module seam (contracts / ingest / render /
providers) so the shell can call it later without a rewrite.

## Rejected
Electron (larger footprint, PRD chose Tauri); Node-only worker (weaker media/ML ecosystem); always-on server.
