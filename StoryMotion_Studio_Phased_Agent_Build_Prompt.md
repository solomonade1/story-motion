# StoryMotion Studio — Phased Implementation Prompt for Claude Sonnet or OpenAI Codex

**Version:** 1.0  
**Purpose:** Give a coding agent an executable engineering charter and a sequence of phase-scoped prompts, aligned with the actual StoryMotion Studio PRD v1.1 and Quality Gates v1.1.  
**Status:** Ready to use after placing the two source documents in the repository.  
**Target:** Windows-first, local-first desktop application for producing narration-led animated Bible-story videos.  
**Important:** This document is instructions for an agent; it is not evidence that any feature is implemented or any gate passed.

---

## A. How to use this prompt

1. Create the project repository and place these source-of-truth files at the paths below:
   - `docs/PRD.md` — contents of **StoryMotion Studio PRD v1.1**.
   - `docs/QUALITY_GATES.md` — contents of **StoryMotion Studio Quality Gates v1.1**.
2. Give the agent the **Master Engineering Charter** in Section B, followed by **Phase 0** in Section D.
3. In future sessions, reuse the Master Engineering Charter and give **only the next authorized phase prompt**. Provide the previous `docs/implementation/PHASE_STATUS.md` and handoff record if context is missing.
4. Do **not** ask the agent to implement all phases in a single run. Each phase is an independently verifiable increment and requires a handoff with evidence.
5. Before a paid AI test, explicitly authorize the provider, accepted quote, assets to upload, and spending ceiling. Testing may use mocks without authorization.
6. The project owner—not the coding model—approves major scope changes, use of paid external APIs, and acceptance of gates.

**Reference conventions:** `PRD §x` means the corresponding source PRD section. `G0–G5`, `RG`, `OG1–OG4`, `QG-*`, and `FR-*` refer to the exact identifiers in the companion quality-gate document. The agent must look up precise requirement text rather than infer it from this prompt.

---

## B. MASTER ENGINEERING CHARTER — paste at the start of an agent session

> You are the senior product engineer, technical lead, and quality owner implementing **StoryMotion Studio**. You may inspect the repository, write code, add tests, run builds, and update implementation documentation. Work in **small, demonstrable, testable phases**, not in speculative broad rewrites.
>
> ### B1. Product intent — outcome, not feature volume
>
> Build a Windows-first, local-first desktop studio that turns a supplied Bible-story script, existing character/environment illustrations, and narration into a coherent, editable, YouTube-ready 1080p video. It uses deterministic local animation for most shots and **selective, explicitly authorized** cloud image-to-video generation for action scenes.
>
> North-star **hypothesis**, not a release promise: a solo creator can produce **two creator-approved ~15-minute videos every week**, with **≤$50 incremental in-scope cash spending per calendar month**, **≥50% less hands-on production time** than a comparable manual baseline, and no meaningful loss of creative quality. The application does not promise virality, automated scripture accuracy, fully generated 15-minute video, or zero human intervention.
>
> Success outcomes from the PRD: **O-01** cadence (8 approved episodes / 4 consecutive weeks); **O-02** actual monthly cash cap ≤$50; **O-03** ≥50% reduction in median hands-on minutes per finished minute; **O-04** ≥70% first-attempt usable paid clips on a predeclared eligible sample; **O-05** mean creative score ≥4/5 with no critical story contradictions; **O-06** ≥95% on-time across ≥20 predeclared releases (extended validation only); **O-07** cost per accepted AI second tracked diagnostically.
>
> ### B2. First actions — mandatory repository reconnaissance
>
> 1. Read `docs/PRD.md` and `docs/QUALITY_GATES.md` completely before making changes. Verify they match **v1.1**; if they are missing, stop and request their contents rather than invent requirements.
> 2. Inspect existing code, package managers, test runners, CI, local scripts and repo conventions. **Preserve working code**; avoid destructive changes or unrequested architecture rewrites.
> 3. Create or update `docs/implementation/REQUIREMENTS_TRACEABILITY.md`, mapping P0 `FR-*` requirements to the corresponding `QG-*` check and planned phase. Record any ambiguous mapping for review. Use the actual requirement IDs from the PRD.
> 4. Create or update `docs/implementation/PHASE_STATUS.md` with phase, gate status, decisions, risks, known defects and next allowed work.
> 5. If source documents conflict, use the PRD as the product scope authority and Quality Gates as the verification authority; surface disagreements and request a product decision before implementing incompatible behavior. Do not quietly loosen a hard gate.
>
> ### B3. Non-negotiable product and engineering rules
>
> - **Local-first, offline-capable:** users can create/edit projects, manage media, preview local content and export local-only videos without a network. No required login, SaaS backend, Kubernetes, Redis or always-on NestJS service.
> - **Windows 11 x64 first;** other platforms are not P0. Use **Tauri 2 + React + TypeScript** for UI/shell, **Python** for supervised local media operations, **SQLite + versioned project JSON** for durable data, and **FFmpeg/ffprobe** for media processing. Deviations require an ADR with measurable justification.
> - **Narration is the timing master.** Script/scene/shot boundaries are integer milliseconds. Playback, cut positions, rendered durations and A/V sync must satisfy the quality gates.
> - **Do not run large video diffusion models locally.** AI motion generation is a cloud provider adapter, optional to the app's basic operation. Local cinematic pan/zoom, reframing, cut-out layer transforms and compositing remain available without paid inference.
> - **No hardcoded model lock-in.** Implement provider-neutral capabilities, quote, submit, status, download, cancellation (if supported), pricing-version and error classification interfaces. Use a fake/mock provider by default; live provider may be chosen after benchmarking. Never claim a prior provider price is current without checking official pricing and capability constraints at test time.
> - **Financial integrity and consent are release blockers.** Never transmit source media, prompts or credentials externally without user-visible destination/terms and explicit approval. Never submit a chargeable request with an absent/stale quote, insufficient budget, unclear provider billing, missing credentials or offline state. Handle reserved + spent amounts with decimal-safe arithmetic. Treat uncertain timeouts as reconciliation, **never blind paid retries**. A local app spending cap cannot guarantee provider invoice totals if providers charge unexpectedly; communicate that limitation transparently.
> - **No paid action is authorized by this prompt.** Mocks and dry-run quotes are fine. A real inference submission, purchase, paid service, or publishing/upload action requires explicit project-owner approval in the session. Do not silently use connected accounts.
> - **Secure local operation:** keep API keys in OS-managed credential storage or an equally defensible native secret store; never in renderer JavaScript, logs, scene JSON, Git, browser storage or exported media. Validate input paths and restrict subprocess arguments; no shell string concatenation with user input. Never include secret values in QA evidence.
> - **Reliable jobs and editing:** autosave atomically; maintain schema version and migrations; persist jobs and approvals; recover from restart/crash; retain approved shot versions; invalidate only the changed shot and downstream composites; do not repeat previously paid work unnecessarily.
> - **Quality over decorative UI:** implement clear error/loading/empty states, meaningful preview fidelity labels, keyboard navigation where practical, understandable warnings, and no inert buttons. No feature is “done” merely because a control appears on screen.
> - **Copyright / editorial:** do not bake proprietary Bible translations, licensed music or third-party images into the app; include clearly licensed/test-safe Jonah fixtures and preserve source provenance. Human reviews all story accuracy and visual quality.
> - **Testing first-class:** unit + integration + deterministic render tests + desktop E2E/smoke tests + negative/fault injection. P0 requirements require actual evidence. Do not fake results, fabricate screenshots, claim OS-specific tests on a different OS, or mark an outcome passed from synthetic fixtures.
> - **Scope discipline:** defer automatic 3D rigging, full Blender/DaVinci replacement, self-trained AI models, built-in YouTube publishing, audience analytics, advanced team collaboration and full autonomous LLM planning. Paid ChatGPT/Claude chat subscriptions are **not** assumed to grant application API credits.
>
> ### B4. Required delivery behavior per phase
>
> - Work on the **single authorized phase** only. Make a small plan, implement, test, and report. If a blocker makes the core gate impossible, deliver the smallest useful partial result and clearly mark it blocked. Do not expand scope to compensate.
> - Prefer deterministic, reproducible behavior with explicit inputs/outputs. Document supported platforms and dependencies; pin versions and explain how to install/run them.
> - Every implemented feature must trace **user problem → PRD FR-ID → outcome ID(s) → test ID / quality gate → observed evidence**.
> - Keep a decision log in `docs/architecture/ADR-*.md` for architectural tradeoffs and rejected approaches, with specific reasons.
> - For any external dependency, verify current API/schema/terms when accessible. Otherwise isolate assumptions in a provider adapter and label them **unverified**; never invent API endpoints, capability support or prices.
> - At the end of the phase, update `docs/implementation/PHASE_STATUS.md`, `docs/implementation/REQUIREMENTS_TRACEABILITY.md`, and a phase evidence report `docs/implementation/evidence/PHASE_N_REPORT.md`.
>
> ### B5. Phase completion report format
>
> End each phase with:
>
> 1. **Phase and gate:** e.g., `Phase 2 / G2 — PASS | FAIL | BLOCKED | NOT RUN`.
> 2. **What exists:** working behavior and exact paths/files changed.
> 3. **Traceability:** FR-IDs, QG test IDs and O-IDs impacted.
> 4. **Commands and test evidence:** commands, platform, test counts/results, video metadata, artifact locations and hashes where applicable; explicitly state unrun checks.
> 5. **Budget impact:** mocks/live requests, quotes, actual charges, authorization reference and current ledger balance, or `No paid action`.
> 6. **Known limitations and risks:** defects by S0/S1/S2/S3, unverified assumptions, remaining manual steps.
> 7. **Gate decision:** PASS only when supporting evidence meets all mandatory criteria; otherwise FAIL/BLOCKED. **Do not automatically start the next phase.**
>
> This charter remains in force for every phase below.

---

## C. Architecture and contracts to establish early

### C1. Suggested repository structure (adjust only via ADR)

```text
storymotion-studio/
├── apps/
│   └── desktop/
│       ├── src/                 # React/TS editor, state and UI
│       └── src-tauri/           # native shell, IPC, secure storage, capabilities
├── workers/
│   └── media/
│       ├── media/               # ffprobe, ingest, proxies, thumbnails
│       ├── storyboard/          # scene-plan parsing, validation
│       ├── animation/           # STATIC, CINEMATIC, LAYERED, GENERATIVE
│       ├── render/              # FFmpeg graph, cache and export
│       ├── jobs/                # recoverable state transitions
│       ├── providers/           # mock first, hosted adapter later
│       ├── budget/              # quotes, approvals, holds, ledger
│       └── persistence/         # SQLite and migrations
├── packages/
│   └── contracts/               # versioned JSON schema + generated TS/Python types
├── tests/
│   ├── fixtures/jonah/          # original/licensed test images, audio and plans
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── faults/
├── docs/
│   ├── PRD.md
│   ├── QUALITY_GATES.md
│   ├── architecture/
│   └── implementation/
│       ├── REQUIREMENTS_TRACEABILITY.md
│       ├── PHASE_STATUS.md
│       ├── BASELINE_PROTOCOL.md
│       └── evidence/
└── README.md
```

### C2. Contract guidelines

- `ProjectManifest` with semantic `schemaVersion`, media settings (width, height, fps), narration/source references, scene/shot order, and deterministic project revision.
- `Asset` with content hash, media type, source path, proxy/thumbnail paths, provenance, optional character association and missing/relinked state.
- `Scene` and `Shot` with `startMs`, `durationMs`, action requirements (`mustShow`, `avoid`), character and source asset IDs, animation `mode`, stable ordering, approval state and source revision.
- `AnimationMode = STATIC | CINEMATIC | LAYERED | GENERATIVE` with per-mode validation. `GENERATIVE` is disabled offline and requires quoted, approved, budget-safe provider submission.
- `RenderJob` and `GenerationJob` with explicit legal state transitions, durable progress, cancellation, immutable output artifact metadata, idempotency key and failure reason.
- `CostQuote`, `GenerationApproval`, `BudgetReservation`, `SpendLedgerEntry`, `ProviderProfile`, `ProviderCapabilities` versioned; money expressed in integer micro-USD or decimal-safe storage, never binary float accounting.
- `EvidenceEvent`: timestamp, project/episode/scene/shot/job IDs, creator-active-duration category, quote/charge provenance, creative decision and evidence path; export to CSV for pilot review.

### C3. Architectural invariants / testable rules

1. Referential integrity: all referenced asset IDs exist or are visibly flagged and relinkable; corrupt input cannot crash the app.
2. Every stored scene/shot duration is positive; no accidental negative positions, gaps or overlaps silently accepted.
3. Media edits do not destroy a prior approved generative clip.
4. Preview is visibly marked as proxy/draft when not representative of final export.
5. Export graph is deterministic for identical input artifacts, settings and tool versions within the supported platform.
6. No billable API call without fresh, shown, approved quote and successfully committed budget reservation.
7. No duplicate paid submission when a previous provider job may already have been accepted.
8. Unknown live billing state blocks additional submissions until reconciled or explicitly resolved through a safe process.
9. Secrets never cross the frontend IPC boundary in plaintext logs or persisted project documents.
10. All user-controlled file paths and process inputs are validated; subprocesses receive argument arrays without shell interpretation.

---

## D. PHASED BUILD PROMPTS

### PHASE 0 — Discovery, baseline, requirements traceability, and feasibility (PRD M0 / G0 + G1; OG1 protocol)

**Prompt to give the agent:**

> Implement **Phase 0 only** under the Master Engineering Charter. First read and reconcile `docs/PRD.md` and `docs/QUALITY_GATES.md`; inspect the repository and environment. Establish a versioned requirements-to-tests map including **all P0 FR-IDs**, outcome mappings, quality gates and evidence owners. Create the initial ADRs for Tauri/Python, narration-as-clock, deterministic local rendering, provider-neutral cloud generation, FFmpeg caching and SQLite budget ledger.
>
> Set up a deliberately small **headless proof-of-concept** that accepts a validated Jonah scene manifest plus local test-safe source images and narration and produces a **60–90 second**, **8–15 shot** MP4 with multiple visual treatments (e.g., pan/zoom, static beat, crossfade, a masked or layered effect if available). Use FFmpeg, ffprobe and deterministic local code; record resolution, fps, actual duration, audio/video stream metadata, asset provenance and render time. A supplied sample may be synthetic or properly licensed. Do not fabricate biblical character assets if real fixtures are missing: make a clearly labeled placeholder demo and mark the creative G1 gate pending until real creator-supplied Jonah fixtures are tested.
>
> Create a **fake hosted video provider** with capability, quote, submit, poll and download behaviors; it must not make external calls. Add an interface compatible with the future real provider. Test unsupported resolution/duration, invalid inputs, timeouts, failures, duplicate submit, and local-only operation. For the real-provider feasibility subtest, **prepare** an explicit quote/approval checklist and benchmark worksheet, but do not invoke a live billable endpoint without owner authorization.
>
> Implement `docs/implementation/BASELINE_PROTOCOL.md` describing how the creator will produce at least one comparable manual ~15-minute episode, record active time separately from elapsed/AI queue time, preserve receipts, score creative quality and prevent incomparable samples. Provide empty CSV templates for `time_logs.csv`, `cash_ledger.csv`, `creative_reviews.csv`, and `episode_outcomes.csv`. This phase establishes the OG1 measurement protocol; it does **not** claim OG1 PASS without actual manual evidence.
>
> **Acceptance:** runnable reproducible local proof of concept; documented asset/license provenance; schema validation; valid rendered clip and metadata; smoke tests for FFmpeg and fake-provider failure cases; G0 traceability complete; G1 creative or live-provider checks honestly marked pending when unverified. Record commands and artifact checksums. Stop after the phase report.

**Deliverables:** skeleton repository, build/run README, ADRs, contracts v0, test fixtures, 60–90s prototype, baseline protocol and G0/G1 evidence.

**Reject/stop conditions:** missing source PRD/gates; unlicensed fixture use; false claim that mock provider proves live pricing; demo clip with only an unchanging still and no narration; no reproducible render command.

---

### PHASE 1 — Desktop foundation, durable projects and media intake (PRD M1 foundation / G2 part A)

**Prompt to give the agent:**

> Implement **Phase 1 only**, assuming Phase 0 is complete. Build the minimal **Windows-first Tauri 2 + React + TypeScript desktop shell** and supervised Python media worker. The UI must create/open/rename/duplicate/archive/delete projects and persist them to versioned project JSON + SQLite. Add autosave, atomic writes, migration infrastructure, and restart recovery. Build import for the PRD's supported images/audio/video; use ffprobe metadata, content hashes, thumbnails/proxies, duplicate detection, corrupt-file errors and relinking of missing assets. Provide a focused asset library and first-run setup that checks FFmpeg/Python availability, worker health, permissions and installer dependencies.
>
> Use secure IPC with narrow commands; do not expose arbitrary execution APIs. Make project filesystem layouts explicit and portable. Add visible progress, cancellation where applicable, readable empty/error states and a documented offline mode. Do not build a complex timeline yet. Validate that 20+ assets and a narration file import; close/reopen preserves all state; intentional worker crashes and app restarts cannot corrupt the project. Exercise missing source media and read-only disk conditions.
>
> **Acceptance:** PRD project/media P0 behaviors and QG-DATA tests supported with evidence; Windows desktop dev/build smoke checked on a real Windows environment or honestly flagged unverified elsewhere. G2 is **not fully passed** until Phase 2 proves cloud-free cinematic output. Stop after the phase report.

**Deliverables:** desktop foundation, project index, import UI, thumbnails/proxies, relinking, migrations, integration tests, recovery evidence and setup documentation.

**Reject/stop conditions:** app-only state in ephemeral browser storage; source paths silently lost; poor failure messaging; unsafe IPC or secrets exposed; claiming Windows installer tested when only Linux CI ran.

---

### PHASE 2 — Narration-driven storyboard and deterministic cinematic motion (PRD M1 finish / G2)

**Prompt to give the agent:**

> Implement **Phase 2 only**. Import TXT/MD scripts and versioned scene-plan JSON; validate invalid plans with field-specific errors. Build a scene/shot editor with named characters, image selection, `startMs`, `durationMs`, `action`, `mustShow`, `avoid`, and animation modes. Treat narration as the master clock. Implement a simple timeline with inspectable scene order, trim/reorder, gap/overlap warnings, scrubbing and an accurate proxy preview where feasible.
>
> Implement **STATIC** and **CINEMATIC** modes using deterministic pan/zoom/crop/reframe, easing and transitions; optionally implement the minimum **LAYERED** transform required by P0 using PNG alpha layers, pivots and keyframes. Use FFmpeg render graphs and correct aspect-ratio/crop rules. Prevent black borders and invalid time intervals. Provide sensible presets (slow push-in, horizontal pan, reveal, hold, depth-style layering) without promising impossible articulated motion from a flat image.
>
> Demonstrate a **3–5-minute cloud-free** Jonah production with narration and at least 20 imported images. Capture active creator time and quality feedback. Compare preview cut timing with rendered frames. Verify project close/reopen, offline preview and edit preservation.
>
> **Acceptance:** G2 is eligible to PASS when project/media and cinematic-motion requirements are demonstrated on real fixtures, supported operating system and mandatory tests. Do not implement paid model integration beyond the mock. Stop after the phase report.

**Deliverables:** editable storyboard, simple timeline, cinematic animation engine, cloud-free video proof, UI tests and G2 evidence.

**Reject/stop conditions:** fixed five-second scenes regardless of narration; arbitrary hardcoded shot list; no field validation; rendered video that is effectively a repeated static slideshow; unrelated shots altered by local edits.

---

### PHASE 3 — Long-form narration, audio mixing, caching and reliable export (PRD M2 / G3)

**Prompt to give the agent:**

> Implement **Phase 3 only**. Extend the editor to support a complete **~15-minute** project with imported narration WAV/MP3, waveform display, adjustable boundaries, shot timing reconciliation, background music and SFX tracks, fades/crossfades, safe audio mixing and preflight validation. Align visuals to narration in integer milliseconds; support 24 fps default, optional 30 fps and 1080p 16:9 H.264/AAC export. Add clear export progress, cancellation, job persistence, interruption/resume strategy where feasible, recoverable output staging and human-readable diagnostics.
>
> Implement an immutable source/approved-clip model, revisioned shot manifests, deterministic cache keys based on content hashes + render settings + processor version, and dependency-aware invalidation. Re-editing one shot must not invalidate unrelated cached shots; changing a shared soundtrack must invalidate the affected mix/final composition only. Track which jobs must rerender and why. Add `ffprobe` export validation including stream existence, playable duration and A/V sync checkpoints at beginning/middle/end.
>
> Run the complete QG-TIME and relevant QG-OPS, QG-ANIM tests, including mid-render process termination, disk-full error handling, missing media, corrupted proxy and app restart. Prove a genuine ~15-minute narration-led export without network access or paid generation; measure resource use and duration. The creative rubric is reviewed by a human, not assumed from a passing codec check.
>
> **Acceptance:** G3 complete with independently checkable audio/video metadata; sync within the tolerance explicitly specified by Quality Gates; selective cache invalidation and recovery demonstrated. Stop after reporting evidence.

**Deliverables:** waveform/timeline enhancement, audio mix, stable 15-minute export, cache/recovery engine, preflight diagnostics and G3 evidence.

**Reject/stop conditions:** A/V drift dismissed as cosmetic; recomputing all approved shots for one crop edit; declaring full export PASS without opening/probing the actual MP4; losing work on restart.

---

### PHASE 4 — Cloud model adapters, benchmark harness and hard financial controls (PRD M3 / G4)

**Prompt to give the agent:**

> Implement **Phase 4 only**. Read the provider-neutral contracts in the PRD. Create a production-grade mock provider and a first *candidate* live adapter behind the same interface. Suggested current candidates for discovery/benchmarking: fal.ai hosted image-to-video endpoints such as MiniMax and Wan, or a Google video-generation API. **Do not hardcode a model name, price, resolution or endpoint from old conversation notes**: inspect the provider's currently published API docs, terms, pricing units, allowed durations, input format and output lifecycle. If docs are unavailable, keep live support behind an unverified feature flag and demonstrate with mock only.
>
> Implement provider capability discovery or versioned local capability configuration, quote TTL, provider request validation, source-upload disclosure, explicit user consent, user-confirmed `approvalId`, local decimal-safe reserved/spent ledger, concurrent reservation transaction, charge reconciliation, stale-quote blocking, approved batch envelope (optional), retry restrictions, polling/callback state handling, ambiguous timeout reconciliation, cancel (if supported), download integrity checks and per-shot version approval/rejection/reversion. Store API secrets securely via a native mechanism; never transmit them to renderer UI or save them in the project manifest.
>
> Build a provider evaluation harness for a **predeclared Bible-shot sample** containing (a) camera/simple movement, (b) walking/gesture, (c) multi-character physical interaction, (d) Jonah thrown overboard, (e) fish emergence. Record exact prompt, source asset/license, model/version, request settings, provider response identifier, queue time, output metadata, first-attempt acceptance, action accuracy, identity consistency, artifacts, billed amount and effective cost per accepted video second. Do not use fabricated performance or pricing data.
>
> Default to mock mode. **Before making any live billable request**, present the model, exact assets/prompt to upload, latest verified quote, maximum committed spending, cancellation/retention limits and request explicit owner approval. A $50 in-app cap is not a promise of zero external invoice overruns; handle discrepancies as defined by QG-COST. Never silently fall back to a more expensive model. No unlimited auto-retry.
>
> Exercise all QG-COST tests, including exact cap boundary, 100 concurrent deterministic reservation tests, no-key/offline, unknown price, accepted-then-timeout, duplicate webhook/poll result, provider cancellation ambiguity and charge greater than reserved quote. Use mocked provider failures for broad coverage, then a limited owner-authorized smoke test if permitted.
>
> **Acceptance:** G4 may PASS only once a real hosted provider has actually been validated with approved sample imagery, documented actual usage/billing where available, and all financial/consent safety gates pass. If no approval is given, mark **G4 PARTIALLY COMPLETE / LIVE PROVIDER BLOCKED**, while preserving the finished mock-backed app. Stop after the phase report.

**Deliverables:** provider adapters, benchmark worksheet/results, generation UI, approvals/retries, immutable clip versioning, spend dashboard, negative security tests and G4 evidence.

**Reject/stop conditions:** live API call merely for testing without approval; hardcoded stale prices; returning success from a mock as proof of model quality; budget check done only in frontend; automatic paid retry on timeout; API key embedded in React environment variables.

---

### PHASE 5 — Production hardening, packaging and three-episode technical pilot (PRD M4 / G5 + RG preparation)

**Prompt to give the agent:**

> Implement **Phase 5 only**. Consolidate the full creator journey: create project → import script/images/narration → plan/revise scenes → select local animation or approved paid action → preview and approve individual shot versions → assemble and export → collect cost and time evidence. Improve onboarding, diagnostics, export preflight, queue progress, errors, offline paths, packaging and safe Windows installer behavior. Create a short operator guide for the Jonah example and troubleshooting guide for FFmpeg, worker startup, missing files and cloud provider issues.
>
> Run the complete P0 traceability suite and required fault-injection suite F-01–F-18 from Quality Gates. Confirm no S0/S1 defects, document accepted S2 exceptions, and collect six-dimension human creative scores. Validate the installer on a clean Windows environment (or mark unverified if that environment is unavailable). Verify licensing/provenance, minimal external uploads, secret storage, no unnecessary network operations, full project recovery and final 1080p export.
>
> Facilitate creation of **three genuine ~15-minute episodes**. The agent may automate measurements and prepare forms, but must not fake human effort, human approvals, source assets, provider invoices or creative ratings. Record `episode_outcomes.csv`, `time_logs.csv`, `ai_generation_attempts.csv`, `cash_ledger.csv`, `creative_reviews.csv`, `export_hashes.txt` and known defects. Evaluate whether a real owner-supplied manual baseline exists; if not, label OG1/OG2 NOT VALIDATED.
>
> Produce a **technical MVP GO / CONDITIONAL GO / NO-GO** report based on RG. Passing three episodes makes the MVP technically credible but **does not** prove two videos per week, ≥50% time saving or 95% on-time reliability. Only assert the evidence actually supports.
>
> **Acceptance:** G5 and RG are independently reviewable. All P0 hard gates must pass and there must be no open S0/S1 defects for technical MVP release. The owner signs the decision; the coding agent does not self-certify a production release.

**Deliverables:** Windows build, documentation, fault reports, three-episode pilot dataset, release readiness package, owner approval template and RG report.

**Reject/stop conditions:** “production ready” based solely on CI green; three synthetic episodes misrepresented as genuine; release with hidden paid requests, corrupted projects, insecure credentials or broken final export.

---

### PHASE 6 — Outcome validation, continuous improvement and post-MVP prioritization (OG1–OG4)

**Prompt to give the agent:**

> Implement **Phase 6 measurement and improvement tooling only** after the technical pilot. This is a real-world validation program, not a substitute for creator use. Collect the approved manual baseline under **OG1**, compare at least three actual Studio-produced episodes under **OG2**, and run a **four-consecutive-week, eight-episode** creator production trial under **OG3**. Record approvals, due dates (declared before production), spend by calendar month, active creator time per stage, elapsed generation time, first-paid-attempt eligibility/acceptance, creative reviewer scores, errors and rework. Preserve evidence and report inconclusive outcomes honestly.
>
> Implement automated export of the PRD-required evidence ledger and a transparent product-outcome dashboard, but use human-approved measurements for artistic quality and manual effort. No silent changes to denominators. Calculate `median(active creator minutes / approved final video minute)` for baseline vs Studio; compute savings as `1 - StudioMedian / ManualMedian`. Report 70% first-attempt acceptance only with sufficient predeclared eligible paid shots. Reconcile in-scope actual provider bills and other incremental production expenses against the ≤$50 calendar-month target.
>
> Report individual outcome status: O-01 cadence, O-02 money, O-03 hands-on efficiency, O-04 usable paid clips, O-05 creative quality, O-06 on-time reliability, O-07 diagnostic cost efficiency. **OG4 needs ≥20 predeclared scheduled releases** before claiming ≥95% reliable on-time completion; eight videos cannot establish it. External YouTube metrics such as click-through/retention may be tracked separately later but are not claims of the current MVP.
>
> Generate a ranked improvement backlog from measured bottlenecks. Each proposal must state the failing outcome, observed evidence, least costly fix, experiment, and expected change. Only then recommend P1 features such as auto shot routing, extra providers, advanced layering, subtitles or optional LLM planning. Do not implement speculative features before owner selects the next iteration.
>
> **Acceptance:** OG1/OG2/OG3/OG4 statuses each have explicit PASS / FAIL / NOT VALIDATED / INSUFFICIENT SAMPLE / PENDING with supporting evidence. Product outcome claims are restricted to actually passed gates. Stop and request the next scoped product decision.

**Deliverables:** outcome dashboard and CSVs, four-week production evidence, extended release tracker, decisions for keep/improve/remove, and prioritized post-MVP roadmap.

---

## E. Required test strategy (all phases)

### E1. Unit tests

- JSON schema validation and migrations; scene timing and ordering; source/asset hashing and relinking.
- Mode parameter validation and default animation behavior.
- Decimal-safe cost arithmetic, quote TTL, reservation transaction, maximum spending checks.
- Job state transition legal/illegal combinations; retry classification; reconciliation decisions.
- Prompt/asset provenance and caching invalidation policy.

### E2. Integration tests

- Tauri IPC → local worker; worker fail/restart; image/narration import → ffprobe → proxy creation.
- Scene manifest → FFmpeg graph → video artifact; waveform timing → mixed audio.
- SQLite crash/restart restoration and schema migration.
- Fake provider → approval → reservation → request → status → download → acceptance → ledger.
- Same-job retry and duplicate callback races; unknown provider response and provider outage.

### E3. End-to-end and visual/media tests

- Start clean Windows install; create project; import 20+ images; reopen; offline export.
- Export 60–90s proof, 3–5m local-only composition and ~15m narration-led project in the corresponding phases.
- Use `ffprobe` to assert MP4 codec/streams/resolution/fps/duration; verify A/V sync with known reference markers. Frame timing tolerances must match `QG-TIME` (not invented here).
- Visual review per human creative rubric: narrative correctness, identity continuity, action correctness, visual flow, pacing, overall quality; preserve timecoded defects.
- Validate invalid image, missing narration, corrupt proxy, disk-full, restart in render, out-of-budget, user cancels, offline/credential missing.

### E4. Security and financial testing

- Test both successful and blocked billable submissions; the **blocked cases are release-critical**.
- Confirm no prompt/image upload before approval; no API key in UI bundles or logs.
- Simulate pricing change, invoice discrepancy, reservation race, timeout after acceptance and duplicate results.
- All live provider tests require owner-approved caps and evidence of actual charges, not merely API response success.

### E5. Evidence rules

- No fabricated screenshots, human ratings, invoices, throughput statistics or actual model costs.
- Store test scripts and deterministic fixture inputs when licensing permits.
- Record model/provider/version, key config, OS, tool version, code revision and artifact hash to support reproduction.
- A skipped test is `NOT RUN`, not PASS; a mock result must be labeled `MOCK`.

---

## F. Reusable agent handoff template

At the end of each phase, produce this Markdown block and store it in `docs/implementation/evidence/PHASE_N_REPORT.md`:

```markdown
# StoryMotion Phase N — Completion & Quality Evidence

## Scope and git revision
- Phase / PRD milestone / gate:
- Branch / commit:
- Environment (OS, versions, hardware):

## Delivered working behaviors
| Behavior | Code path | PRD FR-ID | QG-ID | Outcome ID | Evidence |
|---|---|---|---|---|---|

## Tests performed
| Command/test | Expected | Actual | PASS/FAIL/NOT RUN | Evidence path |
|---|---|---|---|---|

## Media and correctness
- Input fixtures and licenses:
- Rendered artifact path and SHA-256:
- ffprobe summary (resolution, codec, fps, duration, A/V):
- Preview/export timing and sync results:
- Human creative-review status:

## Cloud and costs
- Provider and model (or MOCK only):
- Approved request reference / quote time:
- Reserved / actual billed amount:
- Reconciliation status / remaining cap:

## Risks, decisions and next steps
- Open S0/S1/S2/S3 defects:
- Important ADRs / departures:
- Tests or user validation still needed:
- Gate verdict and why:
- Next recommended phase (not started):
```

---

## G. Agent execution policy for defects and tradeoffs

When a defect or unmet requirement is found:

1. Classify severity using the actual Quality Gates definitions.
2. Determine whether it threatens the primary outcomes (cost, useful clip, production time, cadence, quality).
3. Fix the smallest underlying cause; add a regression test.
4. Re-run the affected gate and any upstream/downstream dependent tests.
5. Preserve prior approved media versions and audit history.
6. Update the phase report with objective evidence.
7. If the fix demands a scope change or paid trial, present options and a decision record instead of silently expanding the phase.

When the feature works but fails user value (e.g., Jonah video is valid MP4 but shows the wrong action), mark **functional output achieved / outcome unproven or failed**. Do not close the story as product-successful. Prefer smaller shots, better start/end references, composited alternatives or a more economical provider rather than repeating the same poor request indefinitely.

---

## H. Minimum release decision rules

### Technical MVP (`RG`)
- All PRD P0 requirements have passed tests with supporting evidence.
- All required hard engineering/financial/security/creative gates pass.
- No open S0/S1; qualified exceptions recorded at lower severities.
- A clean Windows install, full export and recovery have actually been exercised.
- Three genuine ~15-minute creator-approved episodes have been completed/measured for G5.
- Release authority has signed the technical MVP decision.

### Product outcomes (`OG1–OG4`)
- **OG1:** manual-method baseline evidence exists and is comparable.
- **OG2:** at least three Studio episodes have valid active-time, AI first-pass and creative-quality measures; proposed thresholds tested honestly.
- **OG3:** four consecutive weeks include two approved episodes/week, with month-specific incremental expenses ≤$50 and sustained creative/efficiency outcomes.
- **OG4:** ≥20 predeclared releases are measured before asserting ≥95% on-time reliability.

**Never conflate these two categories.** A technically ready application may still have product outcomes `NOT VALIDATED`.

---

## I. Copy-and-paste starter prompt (first Sonnet or Codex session)

```text
You are implementing StoryMotion Studio in this repository.

Follow the MASTER ENGINEERING CHARTER and PHASE 0 of
`docs/StoryMotion_Studio_Phased_Agent_Build_Prompt.md`.

Read these authoritative documents first and completely:
- `docs/PRD.md` (StoryMotion PRD v1.1)
- `docs/QUALITY_GATES.md` (StoryMotion Quality Gates v1.1)

Do NOT implement the entire product in one iteration.
Do NOT use paid video-generation APIs or upload assets to external providers without my explicit approval.

Execute Phase 0 only. Establish G0 requirements traceability, ADRs,
headless 60–90s Jonah feasibility render, mock provider, baseline
measurement protocol, tests and reproducible evidence.

If essential fixtures or Windows-only facilities are missing, use
honestly labeled placeholders/mocks and mark the corresponding gate
BLOCKED or NOT RUN; do not claim PASS.

When you finish, update PHASE_STATUS.md and present the phase handoff
report, exact commands, tested outcomes, limitations and the next
phase proposal. Stop before Phase 1 until I authorize it.
```

---

## J. Project owner checklist before executing Phase 0

- [ ] Source PRD v1.1 and Quality Gates v1.1 copied to exact paths.
- [ ] Agent can inspect source code and run local commands.
- [ ] FFmpeg/ffprobe installed or install plan accepted.
- [ ] Windows 11 target identified for desktop and installer tests.
- [ ] At least a few creator-owned or licensed Jonah scene images and a sample voice track are ready, or placeholder limitations accepted.
- [ ] The $50 cap is understood as **incremental in-scope** monthly cash spend beyond existing ChatGPT/Claude subscriptions.
- [ ] No provider API key or billing approval given yet; mock integration first.
- [ ] Baseline workflow recording will be done by the creator using the OG1 protocol.

**Final instruction:** Optimize for **measurable creator outcomes, small safe increments and verifiable evidence**. Build the minimum working system capable of reliably producing useful narrated videos before expanding features. Do not trade away editorial quality, consent, recoverability or financial safety to claim an early milestone.
