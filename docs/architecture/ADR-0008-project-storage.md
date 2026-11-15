# ADR-0008 — Project storage: versioned JSON + SQLite, atomic saves, recoverable by design

- **Status:** Accepted (Phase 1). **Source:** PRD §7.1, §10.2, FR-PROJ-001..004, FR-MEDIA-002..006; QG DATA-01..07, F-08, F-11.

## Decision
A **workspace** folder (default `~/StoryMotion Studio`, or `$STORYMOTION_WORKSPACE`) holds `index.sqlite` (a rebuildable project list),
`projects/<p-id>/` and `.trash/`. Each project folder has:
- `project.json` — the editable **document** (schema `1.0.0`: name, revision, video settings, script, notes, reserved `ext`). **Source of truth.**
- `project.sqlite` — the **asset index and job history** (hash, category, probe metadata, status, preview paths).
- `assets/` (copied media), `thumbs/`, `proxies/` (discardable previews).

Rules that make it safe:
1. **Atomic save.** `project.json` is never opened for writing: a finished temp file is renamed over it, after the previous version is copied
   to `project.json.bak`. A crash at any instant leaves a complete old or new file (FR-PROJ-002). Guarded by a deterministic test that fails if the
   live file is ever opened for writing, plus 20 random hard-kill iterations.
2. **Recovery, not repair-in-place.** A damaged `project.json` is quarantined (`project.json.corrupt-<stamp>`) and the `.bak` is restored without
   overwriting itself; if both are unreadable nothing is touched and the user is told to copy the folder.
3. **Optimistic concurrency.** Every save carries the revision it was based on; a stale save is rejected (409) rather than overwriting.
4. **Migrations.** `schemaVersion` + an ordered list of pure functions; the pre-migration file is kept; running again is a no-op; a *newer* major
   version is refused unchanged. (One real migration exists: the pre-release `title/created` layout → 1.0.0.)
5. **IDs and names.** Folder names are generated (`p-<12 hex>`); user text is only ever display text, never a path component.
6. **Lifecycle.** Create/duplicate build in `p-*.tmp` then rename (a project appears whole or not at all). Delete moves to `.trash/`; permanent
   deletion needs explicit confirmation and, in the UI, typing the name. Windows' transient "Access is denied" on folder renames (virus scanners)
   is retried briefly.
7. **Single writer.** One worker per workspace via an OS file lock (released by the OS if the process dies, so it can never go stale). Orphaned files
   from a crashed import are removed on first open.

## Media intake
Per file, committed independently: validate → SHA-256 → **duplicate check by hash** → ffprobe **plus a real decode** (headers alone pass some corrupt
files) → copy (verified by re-hash) or link → thumbnail → proxy → database row. Originals are only read. Missing/changed files are flagged, never
silently trusted; relink requires a byte-identical file (or a folder search matching size + hash).

## Known limits
Video decode check covers the first frame; damage later in a video is surfaced as a warning from the preview transcode, not as an import error.
Real disk-full/read-only conditions are **simulated** in tests. Linked-file `mtime` changes trigger a re-hash on check; a fast edit that preserves
size and mtime would not be noticed without "verify contents".

## Rejected
Only-SQLite projects (harder to inspect and recover by hand); only-JSON (no good place for the asset index/jobs); in-place JSON edits; global
asset library shared across projects (Phase 1 keeps projects self-contained and portable).
