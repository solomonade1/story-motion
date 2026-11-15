# ADR-0005 — FFmpeg segment caching (design only; implemented in Phase 3)

- **Status:** Proposed. **Source:** PRD §10.4, FR-RENDER-006; QG OPS-06, ANIM-04, F-16.

## Design
Cache key per shot segment = `sha256(canonical(shot JSON) + source asset SHA-256s + video spec + PROCESSOR_VERSION
+ FFmpeg version string)`. Segment files live in a content-addressed directory; the compose step keys on the
ordered list of segment keys + narration hash + transition parameters. Editing one shot changes one segment key
and the compose key only. Approved generated clips are immutable inputs identified by hash and are never keyed
on anything that a local edit changes.

## Phase 0 status
`PROCESSOR_VERSION` exists and segments are already independent files, but **no cache is implemented**: every
render rebuilds all segments. OPS-06 / F-16 are NOT RUN.
