# ADR-0003 — Deterministic local rendering with FFmpeg (segments → compose)

- **Status:** Accepted. **Source:** PRD §10.4, FR-RENDER-001/005; QG OPS-01..03.

## Decision
Pipeline: per-shot **segment encode** (CRF 14, x264) → single **compose** pass (concat/xfade chain + narration
mux, H.264 CRF 18, AAC 48 kHz stereo) → **verify** (ffprobe streams, exact frame count, full decode with
`-xerror`, `blackdetect`) → **atomic publish** (`os.replace` from a temp file only after validation).

- Cinematic motion: the source is upscaled 2× and `zoompan` runs with `d=1`, so sub-pixel jitter is at most
  0.5 output px. Camera `scale ≥ 1` is enforced by the contract, which prevents black borders by construction.
- Layered motion: `rotate` + `overlay` with per-frame expressions of `t`; only numbers enter filtergraphs.
- Determinism: `-fflags +bitexact -flags +bitexact -map_metadata -1`, fixed filter expressions, no timestamps.
  **Scope: same machine + same FFmpeg build.** Cross-machine bit-equality is not claimed.
  **Defect found and fixed during Phase 0:** the first two full-length renders had different SHA-256s even
  though a short mini-project test had passed twice. Per-segment comparison isolated two shots; hashing the raw
  filter output (`-f framemd5`, before x264) showed 23–204 of ~200 frames differing run to run. Bisecting the
  graph showed the cause was `rotate=...:c=none` (leaves unwritten pixels in the rotated RGBA layer); an explicit
  `c=black@0` gives 0 differing frames. Things that were tried and did **not** help: single-threaded filters/x264,
  timestamp normalisation, overlay options. The background is also pinned to RGBA before `overlay`.
  Guards: `test_jonah_layered_shots_are_pixel_reproducible_before_encoding` (mutation-checked: it fails if
  `c=none` is restored) and `scripts/determinism_probe.py` (all shots, N runs).
- Safety: argv lists (no shell), `-protocol_whitelist file` before every input, per-step timeouts, source files
  are never written, output is never overwritten without `overwrite=True`.
- JPEG sources are normalised to limited-range BT.709 so output is plain `yuv420p`.
- Black frames are accepted only inside declared fades (fade-in/out, `fadeblack` transitions). The first full
  run failed validation on exactly this (a planned `fadeblack`), which is why the allowance is derived from the
  manifest rather than a blanket threshold.

## Known limits
Two encode generations (segment + final) cost a little quality; acceptable for Phase 0, revisit with caching
(ADR-0005). No hardware encoder detection yet (FR-RENDER-007 is P1).
