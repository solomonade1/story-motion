# StoryMotion Studio — Quality Gates, Acceptance Scorecard & Release Readiness

**Version:** 1.1 — Outcome-aligned quality gates  
**Date:** 14 November 2026  
**Status:** Proposed verification standard (to be baselined before implementation)  
**Source of truth:** `StoryMotion_Studio_PRD.md`, v1.1, 14 November 2026  
**Scope:** Windows 11 x64 P0 MVP, three-episode technical pilot, and outcome validation (manual baseline + four-week/eight-episode production pilot)  
**Owner:** Product owner; execution by engineering, QA and creative reviewer  
**Release decision:** Product owner signs off; engineering/QA supply technical evidence and creative/operations owners supply observed outcome evidence

> **Purpose.** Define objective, reproducible release gates that answer: *Does StoryMotion Studio meet the PRD's product promise, work reliably, protect the creator's money and files, and produce an acceptable finished video?* A completed feature or a passing unit test alone is not proof of product success.

## 0. How to interpret this document

- **[PRD]** A requirement or exit condition directly specified in PRD v1.1. It cannot be waived casually or scored away.
- **[QA proposal]** A numerical threshold or test protocol introduced here to make a qualitative PRD objective measurable. **[Outcome proposal]** refers to target O-01–O-07 pending baseline approval. Product owner must approve or revise before its first formal use.
- **P0 / P1 / P2** refer to the PRD's priority, **not** failure severity.
- **Critical blocker (S0/S1)** means release is **NO-GO** regardless of aggregate score.
- **M0–M4** refer to the PRD's delivery milestones; **RG** denotes the final release gate.
- **No evidence = Not Tested**, not Pass. An unverified criterion cannot be marked successful.
- Financial gate tests must use provider-confirmed charging semantics where available. A successful mock only proves app logic, not provider billing behavior.

---

# 1. Product success contract

The MVP passes only if **all** of the following are demonstrably true:

1. **[PRD] Complete workflow:** A creator can create/open a local project; import script, narration and illustrations; edit a narration-aligned storyboard; animate with cinematic/layered methods; selectively request an approved AI action shot; preview; and export a complete ~15-minute 1080p MP4.
2. **[PRD] No surprise spend:** Every chargeable AI *creative attempt* requires explicit approval (or an explicitly pre-approved capped batch); the app enforces the configured monthly/project/provider caps, including active reservations, and fails closed on unknown pricing.
3. **[PRD] Local-first operation:** The local editing, preview and export pipeline works without internet or API credentials. No source media is silently uploaded.
4. **[PRD] Editability and recovery:** A single changed shot can be re-rendered without regenerating unrelated approved AI clips; local files, project state and jobs survive recoverable interruption.
5. **[PRD] Playback and export:** A full-length 16:9 H.264/AAC MP4 passes technical validation; narration remains synchronized; relevant scene constraints have creator approval.
6. **[PRD] Content and cost proof:** The Jonah technical spike, offline assembly proof, 15-minute pipeline proof, budgeted AI proof and three-episode pilot satisfy PRD milestone exits.
7. **[QA proposal] Stable and understandable:** No open S0/S1 defects; usability and creative review thresholds in sections 4–6 are met; evidence is archived for every gate.

**Non-success criteria:** Trending/viral views, monetization or retention rate are *not* promises of this MVP. A demo showing only a 5-second generated clip does *not* pass the product gate. A 15-minute exported file that is merely a static slideshow with no adequate narrative-visual treatment does *not* pass the creative gate.

# 2. Release-gate decision model

## 2.1 Required gates

| Gate | Stage | What it proves | Exit / decision |
|---|---|---|---|
| **G0 — Requirements baseline** | Before build | Scope, contracts, risks, test fixtures and thresholds are agreed | All P0 mapped to tests; cost assumptions tagged; owner approves baseline |
| **G1 — Feasibility** | PRD M0 | 60–90s Jonah slice, multiple visual techniques, measured provider cost | Pilot clip plays, is narratively intelligible and provider assumptions checked |
| **G2 — Local editing foundation** | PRD M1 | Desktop/offline project, import, cinematic motion, 3–5m composition | 20+ imported images + narration produce coherent cloud-free output |
| **G3 — Narration-led long form** | PRD M2 | Real ~15m timeline, caching, failure recovery, final export | Valid 15m output, offline editing and restart tests pass |
| **G4 — Budgeted generative actions** | PRD M3 | Safe cloud quote, approval, accounting, single-shot regeneration | No over-cap submission; output review; retry/idempotency scenarios pass |
| **G5 — Technical product pilot** | PRD M4 | Complete creator workflow and initial value signals | Three ~15m episodes measured and creatively approved; **does not establish cadence** |
| **RG — Technical MVP release readiness** | Before MVP release | All P0 + quality, security and package checks | Gate scoring + zero blocker policy + signed go/no-go record; outcome status labelled separately |

**Engineering gate dependency:** G0 → G1 → G2 → G3 → G4 → G5 → RG. **Outcome gate dependency:** OG1 → OG2 → OG3; OG3 may proceed after RG or as a controlled internal pilot. Prototypes may be built in parallel, but a later gate cannot be formally passed until its prerequisites pass. G4 can be tested before G3 for engineering convenience, not accepted as a substitute for G3.

## 2.2 Severity and disposition

| Severity | Definition | Required action |
|---|---|---|
| **S0 — Catastrophic** | Data loss without recovery; credentials exposed; hidden or uncontrolled chargeable generation; arbitrary command execution | Immediate stop; **NO-GO** |
| **S1 — Critical** | Budget bypass; silent third-party upload; unable to export valid output; broken recovery for normal use; materially wrong approved video output | **NO-GO** until fixed and retested |
| **S2 — Major** | Significant workflow degradation with manual workaround; timing error; one supported format consistently fails | Fix before RG unless explicitly accepted with owner rationale and workaround |
| **S3 — Minor** | Cosmetic, discoverability or rare low-impact defect | Record and prioritize; may ship with owner approval |

**Scoring cannot override blockers:** an overall 98/100 with one hidden billable API retry is still NO-GO.

# 3. Measurement system and evidence

## 3.1 Minimum test fixtures

| Fixture ID | Content | Purpose |
|---|---|---|
| **FX-01** | Jonah 60–90s narrated sequence, 8–15 shots, varied static/layered/action assets | M0 vertical slice |
| **FX-02** | 20+ unique PNG/JPEG/WebP illustrations, narration WAV/MP3, background music and SFX | Media import / M1 |
| **FX-03** | ~15-minute narration and complete scene-plan JSON; ≥ 60 shots recommended [QA proposal] | Long-form timeline and export |
| **FX-04** | One difficult Jonah action: thrown from ship; fish approaches/swallowing as multiple shots | Generative control / human approval |
| **FX-05** | Fault assets: corrupt media, duplicate images, missing/moved files, malicious filenames, invalid JSON | Negative/security testing |
| **FX-06** | Mock provider with deterministic quote, pending/failed/success, lost response, 429, outage, cancellation and billing events | Cost and job resilience |
| **FX-07** | Three independently storyboarded ~15-minute episodes with fresh narration and selected reusable assets | M4 creative and operational pilot |
| **FX-08** | A project with one modified scene and several approved generated clips | Dependency invalidation |

Store sample assets with permission for test use, hashes, output expectations, and a provenance manifest. Never commit paid API keys or unlicensed assets to the repository.

## 3.2 Evidence record required per test

Each pass/fail must have: test case ID; mapped PRD requirement(s); build/commit hash; OS and machine profile; fixture ID/hash; date; tester; steps or automation command; expected vs observed result; screenshots or MP4/ffprobe logs if relevant; cost ledger and provider receipt/job ID where relevant; result **PASS / FAIL / BLOCKED / NOT TESTED**; defect link; retest result.

Suggested evidence layout:

```text
quality/evidence/<build-id>/
  manifest.json
  unit-and-integration/
  e2e/
  exports/ffprobe/
  exports/av-sync/
  budget/mock-ledger/
  budget/real-provider/
  security/
  crash-recovery/
  creative-reviews/
  pilot-metrics.csv
  signoff.md
```

Test files are *evidence*, not a substitute for readable findings. Log secrets and personally identifiable data only in redacted form.

# 4. P0 hard gates and quantitative thresholds

The values labelled **[QA proposal]** establish an initial measurable standard, not claims already made by the PRD. Confirm tolerances after an instrumented M0/M1 benchmark; any change requires a documented baseline update.

## 4.1 Project integrity and media handling — QG-DATA

| ID | Test / measurement | Pass threshold | PRD mapping |
|---|---|---|---|
| DATA-01 | Project create, rename, open, duplicate, archive/delete; reopened data matches saved state | **100% of required actions succeed** [PRD] | FR-PROJ-001 |
| DATA-02 | Kill application during autosave; restart and inspect manifest/SQLite | Last valid saved state recoverable; no corrupt active state [PRD]; ≤ 10s of committed UI edits lost in controlled tests [QA proposal] | FR-PROJ-002,004 |
| DATA-03 | Move/delete one source asset; reopen and relink | Missing source flagged; unaffected scenes preserved; repair succeeds [PRD] | FR-PROJ-003 |
| DATA-04 | Import supported image/audio/video formats and corrupt samples | Supported cases pass; unsupported/corrupt files fail with actionable error, never crash [PRD] | FR-MEDIA-001,002,006 |
| DATA-05 | Import exact duplicate bytes twice | Duplicate recognized by hash; no unnecessary duplicate source copy [PRD] | FR-MEDIA-002,006 |
| DATA-06 | Thumbnail/proxy generation, asset category metadata | Every valid fixture import produces correct metadata and usable preview [PRD] | FR-MEDIA-003,004 |
| DATA-07 | Open schema-v1 project after migration test | Old project preserved, migration repeatable, schema version recorded [PRD] | FR-PROJ-004 |

## 4.2 Storyboard, audio and timeline — QG-TIME

| ID | Test / measurement | Pass threshold | PRD mapping |
|---|---|---|---|
| TIME-01 | Import TXT/MD script and valid/invalid JSON scene plans | Valid import editable; invalid JSON has field/location diagnostics [PRD] | FR-SCRIPT-001–003 |
| TIME-02 | Create/edit shot with named characters, action, duration, animation mode; attach narration span | State survives save/reopen; timestamps remain within narration duration [PRD] | FR-SCRIPT-003,004 |
| TIME-03 | Narration waveform, drag boundary, scrub, trim, crossfade and multiple tracks | Required controls work; no unreported overlapping/gap/negative shot intervals [PRD] | FR-TIME-001–004, FR-AUDIO-001,002 |
| TIME-04 | Preview against exported timeline at 24/30 fps | Median visual cut deviation ≤ 1 output frame; max ≤ 2 frames [QA proposal] | FR-TIME-005, FR-RENDER-002 |
| TIME-05 | Narration sync at beginning/middle/end of ~15m export | A/V offset ≤ 100 ms at each checkpoint; no cumulative drift > 100 ms [QA proposal] | FR-AUDIO-001,003,004; PRD §3.3 |
| TIME-06 | Mix narration + music + SFX, run audio preflight | No unintended missing narration; no digital clipping in approved final output [QA proposal]; appropriate warning if source clips [PRD] | FR-AUDIO-002–004 |
| TIME-07 | Offline preview with proxy sources | Playback works with no network and explicitly indicates proxy/final fidelity differences [PRD] | FR-TIME-005; PRD §3.3, §9.2 |

## 4.3 Animation correctness and editability — QG-ANIM

| ID | Test / measurement | Pass threshold | PRD mapping |
|---|---|---|---|
| ANIM-01 | Pan/zoom/crop/reframe/easing on still illustration | Visible, directionally correct movement with no broken borders or unintended black areas in 10 fixture shots [QA proposal] | FR-ANIM-001 |
| ANIM-02 | Apply transforms to separate alpha layers and props | Anchors, pivot points, easing and layer ordering reproduced after save/reopen [PRD] | FR-ANIM-002 |
| ANIM-03 | Set STATIC/CINEMATIC/LAYERED/GENERATIVE; unsupported mode fallback | Correct capability warning and working fallback, never silently changing a paid mode [PRD] | FR-ANIM-003,004 |
| ANIM-04 | Change one approved shot or its crop | Only changed shot and dependent composite invalidated; unrelated approved generated clips unchanged [PRD] | FR-ANIM-005, FR-RENDER-006 |
| ANIM-05 | Approve, reject, regenerate, revert a generated shot | Immutable prior approved version remains selectable; no unapproved render silently substituted [PRD] | FR-ANIM-005, FR-AI-006 |
| ANIM-06 | Jonah action visual review | Every **explicit critical action** is present in its accepted shot(s), or the storyboard explicitly uses an approved alternate depiction; no severe identity/anatomy artifacts [PRD] | PRD §4.3, §14.2 |

**Interpretation:** a good-looking clip that depicts Jonah jumping voluntarily when the story requires sailors to throw him fails *action accuracy*. A creator-approved silhouette/cutaway solution may pass if it deliberately communicates the correct story beat.

## 4.4 Cloud provider, consent and financial integrity — QG-COST (release-blocking)

| ID | Test / measurement | Pass threshold | PRD mapping |
|---|---|---|---|
| COST-01 | Show provider/model, source uploads, prompt, resolution/duration and cost quote before submission | All material terms visible; no network upload before explicit approval [PRD] | FR-AI-001–003, FR-BUD-002,005 |
| COST-02 | Price unavailable/stale/ambiguous; retry requested | **0 chargeable submissions** while quote cannot be validated [PRD] | FR-BUD-007 |
| COST-03 | Boundary: spent + reserved + new quote = cap and cap + $0.01 | Equality allowed, exceeding **blocked**; precise decimal arithmetic [QA test encoding PRD rule] | FR-BUD-001,003,004 |
| COST-04 | Two simultaneous requests sharing near-exhausted budget | **0 over-cap acceptances** in 100 deterministic concurrent test runs [QA proposal] | FR-BUD-003,004 |
| COST-05 | Creative retry after failed result | **0 new chargeable attempts without renewed user authorization**, except authorized batch envelope [PRD] | FR-AI-005, FR-BUD-005 |
| COST-06 | Timeout after provider accepts request | Recover original job where possible; if uncertain, freeze/reconcile before new billable attempt; no blind resubmission [PRD] | FR-AI-004,005 |
| COST-07 | Approval, reject, cancel, download, validate clip | Exact stored provider job ID, result file hash, status and review decision [PRD] | FR-AI-004,006 |
| COST-08 | Ledger spent/reserved/actual and warning thresholds | Balance matches independent oracle to nearest $0.01; 50/75/90/100% notices fire [QA proposal + PRD] | FR-BUD-006,008 |
| COST-09 | Provider rounded billing minimum vs request duration | Quote uses provider-configured rounding/minimum and valid capabilities [PRD] | FR-AI-002, FR-BUD-002 |
| COST-10 | App has zero balance/no API key/offline | Local creative operations remain available; paid generation clearly unavailable [PRD] | PRD §1.1, §3.3 |
| COST-11 | Actual provider cost greater than reserved quote | Record discrepancy, stop future submissions if ceiling cannot be assured; never claim external invoice control beyond available provider guarantees [PRD-based safety interpretation] | FR-BUD-003,006,007 |

**Critical nuance:** a $50 **in-app submission cap** cannot guarantee a provider will never bill beyond $50 if its pricing changes, requests bill unexpectedly or external account activity occurs. Call it an *application-enforced authorization cap*, audit actual charges where supported, and configure provider-side spending alerts/limits separately if offered. The financial gate must never claim to control invoices it cannot read.

## 4.5 Rendering, recovery, offline use and packaging — QG-OPS

| ID | Test / measurement | Pass threshold | PRD mapping |
|---|---|---|---|
| OPS-01 | Final export technical probe | 1920×1080, 16:9, H.264, 24/30 fps, AAC audio, MP4, approximately 15m, playable [PRD] | FR-RENDER-001–005 |
| OPS-02 | Final export duration vs narration target | Absolute mismatch ≤ 250 ms unless intentionally padded/trimmed [QA proposal] | FR-AUDIO-004, FR-RENDER-005 |
| OPS-03 | Export integrity and completeness | `ffprobe` valid; no unplanned black frames, missing audio blocks or truncated tail in spot/automated checks [QA proposal] | FR-RENDER-005 |
| OPS-04 | Run draft/final, pause/cancel where supported; terminate FFmpeg | Job states coherent; no broken published export; retry/restart possible [PRD] | FR-RENDER-003,004 |
| OPS-05 | Kill app mid-project and mid-provider job; reopen | Durable local state; provider ID recovered/reconciled, no duplicate paid submission [PRD] | FR-PROJ-002; FR-AI-004,005 |
| OPS-06 | Edit shot then export again | Cached independent shots reused; only dependent work re-rendered [PRD] | FR-RENDER-006 |
| OPS-07 | Disconnect network for full local project journey | Import, edit, preview, local render/export operate without Internet [PRD] | PRD §1, §3.3, §13 |
| OPS-08 | Windows 11 x64 clean-machine installation | App launches; dependencies detected; guided test export works; no separate hosted service needed [PRD] | PRD §5.1, §10.2, §13.4 |
| OPS-09 | Interactive UI while FFmpeg renders | Controls remain responsive; no sustained UI freeze > 2 seconds on benchmark machine [QA proposal] | PRD §13.1 |
| OPS-10 | Export failure: full disk, missing codec, worker crash | Error actionable; partial temp files managed safely; prior finished export and originals preserved [PRD] | PRD §13.2 |

## 4.6 Security, privacy, legal and beginner UX — QG-TRUST

| ID | Test / measurement | Pass threshold | PRD mapping |
|---|---|---|---|
| TRUST-01 | Search logs, manifest, crash reports and bundle for test API secrets | **0 plaintext leaked secrets** [PRD] | PRD §13.3 |
| TRUST-02 | Attempt path traversal, hostile file names, shell characters and malicious remote URLs | **0 successful traversal, arbitrary execution or unapproved remote reads/uploads** [PRD] | PRD §13.3 |
| TRUST-03 | Observe requests with network monitor before/after consent | **0 unapproved media uploads**; every approved job identifies destination and assets [PRD] | PRD §9.2, §13.3 |
| TRUST-04 | First-time user follows Import → Storyboard → Animate → Review → Export | Can finish a short guided clip without knowledge of FFmpeg or diffusion [PRD]; ≤ 30 minutes and ≤ 2 moderator interventions [QA proposal] | PRD §9.2, §13.5 |
| TRUST-05 | Keyboard navigation, contrast, non-color-only statuses, recovery messages | All major controls operable via keyboard and status distinguishable without color [PRD] | PRD §13.5 |
| TRUST-06 | Licensed music/footage metadata and AI provenance | Usage reminder visible; supplied attribution/license data preserved; AI-shot provenance accessible [PRD] | PRD §13.6 |
| TRUST-07 | No telemetry without opt-in | No analytics data transmitted by default [PRD] | PRD §13.3 |

# 5. Human creative-quality gate

**Review unit:** each accepted shot plus the assembled episode. The reviewer should evaluate actual exported material, not merely source stills or promising prompts. Use the PRD's six 1–5 dimensions:

| Dimension | 1 = unacceptable | 3 = acceptable with issues | 5 = excellent |
|---|---|---|---|
| **Story/action accuracy** | Contradicts script or action | Story beat clear, minor missing detail | Exact intended narrative beat |
| **Character continuity** | Character changes identity/clothes | Mostly consistent, minor drift | Consistent identity and art direction |
| **Motion coherence** | Severe warping/jumping/flicker | Motion usable, minor artifacts | Controlled, smooth and believable |
| **Framing/readability** | Action unclear/cropped | Main subject understandable | Purposeful, clear composition |
| **Narration fit** | Visual unrelated/out of sync | Mostly aligned | Visual enhances spoken beat |
| **Variety/emotional impact** | Repetitive/slideshow fatigue | Adequate rhythm and variety | Strong paced, memorable storytelling |

**Hard creative rejection [PRD]:** critical action constraint unmet; severe anatomy/identity issue; shot contradicts the narrated event; unapproved generated output. All must be corrected or replaced with an intentionally approved alternate shot.

**Technical acceptance baseline [QA proposal]:** (a) each accepted critical-action shot scores ≥ 4/5 in accuracy and ≥ 3/5 in all other dimensions; (b) each completed episode has an average ≥ 3.5/5 across all six dimensions; (c) zero hard rejections remain; (d) editor explicitly approves the full 15-minute episode. Scores must include written reasons and timecoded evidence for any dimension < 4.

**Outcome gate raises the episode mean to ≥4.0/5 across all six dimensions (OG2/OG3); the technical 3.5/5 minimum remains a separate build-quality floor.**

**Reviewer protocol:** ideally two independent reviewers for the M4 pilot; if only one creator is available, retain a second-pass review after a break and mark evidence `single reviewer`. A disagreement of ≥ 2 points on a dimension prompts adjudication. Review scripture/story fidelity manually; the software does not claim doctrinal verification.

# 6. Product KPIs and pilot success measurement

Collect **per scene, per shot, per episode and per calendar month**. Do not use illustrative provider price as recorded spend; use actual provider charges or clearly labelled estimates.

| Metric | Definition / formula | Initial benchmark or gate |
|---|---|---|
| Monthly incremental cash spend | Sum of incremental paid APIs/assets/voices and other in-scope production expenses | **≤ $50** target [PRD], excluding existing subscriptions and exclusions stated in PRD |
| Application-approved cloud spend | Sum of confirmed charges and explicitly tracked corrections for jobs initiated by this app | **≤ configured authorization cap** [PRD] |
| Episode budget | Monthly $50 divided by average 8.67 episodes | **≈ $5.77/episode** planning ceiling [PRD-derived], not an independent guarantee |
| Finished episode duration | Final playable output length | **~15m** [PRD]; 14:30–15:30 target [QA proposal] when story allows |
| AI footage ratio | Approved generated-video seconds / finished episode seconds | **~5% / ~45s** design target [PRD Appendix A]; a guideline, not hard functional failure |
| Video attempts per accepted clip | Billable creative generations / approved usable clips | Measure [PRD]; also measure **O-04 ≥70% first-attempt usable** [Outcome proposal]; >2 attempts planning alert [QA proposal] |
| Cost per usable AI second | Actual cloud spend / accepted generative footage seconds | Record and compare providers [PRD] |
| Editing effort | Hands-on creator minutes / finished-video minute | **O-03: ≥50% reduction** vs OG1 manual baseline, measured on ≥3 Studio episodes [Outcome proposal] |
| Render success rate | Valid completed renders / attempted renders | ≥ 95% on 20 controlled representative renders [QA proposal]; no unresolved systematic failure |
| Project recovery success | Recoverable forced-interruption tests passing / attempted | 100% of mandatory recovery tests [QA proposal] |
| Cache effectiveness | Eligible unchanged shots served from cache / eligible unchanged shots | ≥ 90% in dedicated unchanged-project rerender [QA proposal] |
| Manual shot correction | Shots requiring manual changes / total shots | Track and categorize [PRD] |
| Creator approval | Episodes fully reviewed and approved / submitted pilot episodes | 3/3 [PRD M4 + QA acceptance]; **O-05 ≥4.0/5** outcome creative target [Outcome proposal] |
| Cadence readiness | Completed approved ~15m episodes in predeclared production weeks | **O-01: 2/week × 4 consecutive weeks** [Outcome proposal]; **not** assert met from three-episode pilot |

**Cost-envelope example [illustrative, not an API quotation]:** Nine episodes × 9 AI clips × 2 billable attempts × $0.10/attempt = **$16.20** video generation. A working plan could allocate $16.20 video, $5 narration, $3 assets, $10 contingency = $34.20. Do not pass the financial gate from this projection; the final result requires itemized actual costs and provider-rate verification.

## 6.1 Cadence validation is distinct from MVP acceptance

- **M4 pilot:** Build and assess **three** complete ~15-minute episodes, capturing total production effort. This is the PRD's formal pilot.
- **Operational validation after pilot:** Record at least **four consecutive weeks** of publishing-ready production with the target **two episodes per week** [QA proposal]. Count approved video files, not uploaded/published YouTube metrics.
- If the first three episodes pass but four-week cadence is unproven, mark **MVP TECHNICALLY READY / OUTCOME UNVALIDATED**, not “2 videos/week achieved.”
- If three videos cannot be completed within the cost envelope, record the shortfall and identify bottleneck, instead of weakening cost or quality assertions.

## 6.2 Outcome gates — separate from engineering completion

The technical quality gates ensure StoryMotion works safely. **Outcome gates** determine whether it solves the creator's actual problem. Passing RG is required for a technical release; **RG alone never authorizes the claim that the two-videos/week or 50%-faster outcome has been proven**.

| Gate | Required evidence | Proposed PASS rule | Failure/unknown handling |
|---|---|---|---|
| **OG1 — Problem and baseline validation** | At least one comparable manual ~15m episode (preferably ≥2), with stage time logs, costs, creative rubric and input-complexity record | Baseline reconstructable and signed by owner before evaluating time savings | Missing or incomparable baseline = NOT VALIDATED; redo measurement |
| **OG2 — Creator value validation** | ≥3 real Studio ~15m episodes, comparative active-time rate, paid-clip first-pass outcomes, six-dimension reviews and costs | O-03 improvement **≥50%** against baseline; O-04 first-pass usable **≥70%** on predefined eligible paid-shot sample; O-05 average **≥4/5** with no critical contradictions; actual costs logged | If insufficient eligible shots, record O-04 INSUFFICIENT SAMPLE; no invented pass |
| **OG3 — Production viability** | Four consecutive weeks, 8 creator-approved episodes, predeclared weekly deadlines, receipts/monthly reconciliation and time logs | O-01 **2 episodes/week for 4 weeks**; O-02 **≤$50** per calendar month; sustain O-03 and O-05 across cohort | One missed weekly target or overspend = FAIL; missing receipts = NOT VALIDATED |
| **OG4 — Extended deadline reliability** | ≥20 predeclared scheduled releases with due/approval times | O-06 **≥95% on-time** (≥19/20 if exactly 20) | PENDING until sample threshold reached; not required for initial OG3 claim, but required to state 95% reliability validated |

All thresholds marked **[Outcome proposal]** originate in the v1.1 outcome alignment exercise and require an owner-approved baseline decision. O-07 (cost/accepted AI second) is diagnostic at v1.1; do not imply a numerical pass threshold without data.

### Measurement definitions and anti-gaming rules

- **Hands-on time rate:** active creator minutes / final approved episode minutes. Include scene planning, asset prep, animation operation, edits, QA/rework, and export troubleshooting for both workflows; report queue/wall-clock time separately. Improvement = `1 - median(Studio rates)/median(Manual rates)`.
- **First-attempt usable AI rate:** `eligible shots accepted on their first paid generation / all eligible shots receiving a first paid generation`. Lock eligibility and sample definition before testing. If a shot never reaches a generation request, exclude and report separately; don't remove failed first attempts from the denominator. Review acceptance against the scripted action, not simply valid MP4 status.
- **Creative quality:** average of the six 1–5 PRD rubric dimensions per approved episode, with **≥4.0 overall** as the outcome gate (stricter than the original technical gate of 3.5). Critical story contradictions, identity failures in essential actions or unapproved outputs are automatic creative failures regardless of average score. Prefer two reviewers; identify single-reviewer bias.
- **Financial cap:** sum **actual** incremental in-scope spend across all production work, including charges made outside the app for these videos, attributed to calendar months. Exclude previously purchased ChatGPT/Claude subscriptions, hardware, electricity, internet and creator labor per PRD. Compare actual bills against app ledger; unreconciled material charges prevent PASS. A technical simulation passing its budget guard does not prove the real-world $50 limit.
- **Cadence:** measure completed **approved** artifacts (not project starts or exported drafts), grouped by predeclared production weeks; require two each week, not simply eight produced on the last day. Record late outputs honestly.
- **On-time reliability:** on-time approvals / predeclared scheduled releases; assess only after ≥20 releases. Initial eight-video run must publish its raw count and cannot statistically establish a 95% claim.
- **No silent denominator changes:** retain rejected generations, retries, dropped scenes, reshoots and partial episodes in the evidence log. Report `NOT TESTED`, `INSUFFICIENT SAMPLE`, `FAILED`, and `PASSED` distinctly.

### Required experiment artifacts

`baseline_manifest.json`, `episode_outcomes.csv`, `ai_generation_attempts.csv`, `time_logs.csv`, `cash_ledger.csv`, `creative_reviews.csv`, `release_schedule.csv`, `export_hashes.txt`, `outcome_decision.md`. Each must have traceable episode/shot/job IDs and a named evidence owner. Avoid including API secrets or personal/payment credentials.

## 6.3 Output-to-outcome acceptance matrix

| Shipped output | Functional test (necessary) | Outcome test (value) | Relevant IDs |
|---|---|---|---|
| Storyboard importer | Valid script-to-scenes JSON imported/edited | Median planning time reduced; narration-to-visual clarity retained | O-01, O-03, O-05 |
| Reusable asset library | Assets load, relink, version and cache correctly | Fewer repeat setup minutes without losing distinct art direction | O-03, O-05 |
| Cinematic/controlled animation | Local effects render correctly | Acceptable visual variety with lower spend/rework | O-02, O-03, O-05 |
| Cloud image-to-video adapter | Quote, authorization, job result and retry logic work | ≥70% usable first attempt; cost per usable second evaluated | O-02, O-04, O-05, O-07 |
| Narration timeline + export | Valid 1080p MP4 with sync and recovery | Faster publishable output; deadlines met | O-01, O-03, O-06 |
| Spend dashboard + safeguards | No over-cap authorized app submissions | Reconciled monthly spend ≤$50 including external production costs | O-02 |

**Worked decision:** An image-to-video provider may return valid video in 100% of API tests yet produce a Jonah throw that contradicts the script in 50% of first attempts. The technical output passes, but O-04/O-05 fail; improve prompt/shot decomposition, switch provider or use deterministic fallback before calling the feature outcome-successful.

## 6.4 Pilot review cadence and decisions

- **Before engineering:** OG1 baseline, source material complexity classification, proposed threshold sign-off.
- **After first 3 Studio episodes:** OG2 report; choose **KEEP / IMPROVE / REPLACE / DEFER** for major features, with evidence and product-owner signature.
- **Each pilot week:** compare planned vs approved episodes, active effort, charge ledger, creative reviews, and cost/runway. Do not relax financial or quality constraints to manufacture cadence success.
- **After 4 weeks:** OG3 decision and a separately labelled O-06 follow-up plan.
- **After ≥20 releases:** OG4 reliability assessment. YouTube views, retention and CTR may be logged as exploratory audience metrics, not as an MVP outcome gate.

# 7. Mandatory negative and fault-injection test suite

| Test ID | Failure injected | Expected outcome |
|---|---|---|
| F-01 | No internet before opening | All local operations work; cloud features clearly unavailable |
| F-02 | Invalid/expired API key | No repeated billable submissions; actionable auth error |
| F-03 | Provider price unset/expired or unknown minimum | Fail closed before upload/chargeable submission |
| F-04 | Network times out after accepted provider request | Reconcile using saved job ID if possible; no blind retry |
| F-05 | Two concurrent jobs race against remaining $0.10 budget | At most permitted quote gets reserved/submitted |
| F-06 | Provider cancellation unsupported or charge still applies | UI explicitly warns and ledger preserves potential charge |
| F-07 | Provider returns incompatible format, truncated file or wrong duration | Reject artifact, preserve original and budget accounting |
| F-08 | Kill process during manifest save | Open prior valid manifest, diagnose recovery |
| F-09 | Kill worker during FFmpeg render | Pending/failed job recoverable; approved output untouched |
| F-10 | Disk fills at 95–100% of export | Preflight warns if detectable; failure preserves files and reports cleanup |
| F-11 | Source file moved, removed or modified externally | Clear relink/invalidated cache state; no stale approved render used silently |
| F-12 | Deliberately malformed scene JSON or negative shot time | Import blocked with location-specific validation errors |
| F-13 | Filename containing shell characters/path traversal | No command execution, out-of-root read/write or security exception |
| F-14 | Provider job says complete but download hash differs | Reject clip and log integrity error |
| F-15 | App restarts with active budget reservations | Restored ledger, no overspend or orphaned silent retry |
| F-16 | Modify one of 80 independent shots | No unrelated AI regeneration or unnecessary segment re-render |
| F-17 | FFmpeg executable missing or incompatible | First-run/readiness or render preflight shows clear corrective action |
| F-18 | Cloud generation output differs from original subject | Creator can reject and retain previous approved take, with no hidden chargeable retry |

Run F-01 through F-18 for release qualification with mocks/fixtures; rerun F-03 through F-07 against the actual provider in a **small explicitly authorized, capped** smoke test where available. Simulated provider bills do not validate real pricing.

# 8. Milestone-specific exit checklists

## G0 — Baseline and test readiness

- [ ] PRD v1.1 copied or linked in repository and immutable baseline identified.
- [ ] Every P0 functional requirement has at least one named test and evidence owner (Appendix A).
- [ ] Numerical **[QA proposal]** thresholds approved or explicitly modified in a decision record.
- [ ] Scene-plan schema, budget policy, local project storage layout and renderer contract versioned.
- [ ] Fixture copyrights/licensing checked; provider pricing source and quote TTL documented.
- [ ] S0/S1 definitions, incident response and approval roles agreed.

## G1 — M0 technical feasibility

- [ ] 60–90s Jonah proof-of-concept includes narration, still animation and ≥1 advanced action representation.
- [ ] 8–15 shots demonstrate visually different but coherent scene construction.
- [ ] FFmpeg command, assets, settings and resulting artifact reproducible.
- [ ] Cloud provider test (if used) records actual quote, paid attempts, resulting quality and supported duration/resolution.
- [ ] Creator approves the narrative clarity and marks limitations requiring fallback shots.

## G2 — M1 local foundation

- [ ] Windows desktop install completes on a clean test environment.
- [ ] 20+ image assets and narration imported; metadata and proxies usable.
- [ ] Create/open/save/autosave and missing-file repair verified.
- [ ] 3–5m cloud-free video generated with meaningful cinematic movement.
- [ ] Offline operation tested end-to-end; no secrets or telemetry leaked.

## G3 — M2 narration pipeline

- [ ] Import/modify validated scene-plan JSON, map scenes to waveform.
- [ ] Preview across beginning/middle/end of 15-minute timeline.
- [ ] Export 1080p H.264/AAC MP4 with preflight, integrity and sync checks.
- [ ] Cache test confirms independent shots remain cached after targeted edit.
- [ ] Mid-render termination and restart/recovery tests pass.

## G4 — M3 budgeted AI generation

- [ ] At least one hosted image-to-video provider validated on actual sample imagery.
- [ ] Quote, approved source uploads, authorized submission and async status work.
- [ ] Review, reject, accept, revert and targeted re-generation demonstrated.
- [ ] Concurrent reservations, cap boundary, unknown pricing and creative retry tests pass.
- [ ] No duplicate chargeable attempt during timeouts/restart reconciliation.
- [ ] Actual provider invoice/usage evidence checked where available; unknown costs clearly labelled.

## G5 — M4 pilot

- [ ] Three complete ~15m episodes produced from genuine scripts, narration and assets; label this a **technical/initial-value** pilot, not OG3.
- [ ] All three technically valid, creatively reviewed, and approved.
- [ ] Actual cash costs, generated seconds, attempts, rework, hands-on time and failures recorded per episode.
- [ ] Product owner reviews whether workflow meets intended quality under ≤ $50/month incremental envelope (or documents measured inability and remedies); OG1 baseline and OG2 comparison are reported separately.
- [ ] Known limitations, tutorials, licensing and contingency/fallback workflows documented.

## RG — Final ship checklist

- [ ] **100% of P0 requirements PASS** with evidence; P1/P2 explicitly excluded from release obligation.
- [ ] **0 open S0 / S1** defects; S2 exceptions formally approved and documented.
- [ ] All mandatory fault-injection and security tests pass.
- [ ] Creative and long-form video gates pass.
- [ ] Financial gate passes with actual/appropriately reconciled ledger evidence.
- [ ] Installer, OS compatibility, dependency/license notices and first-run UX verified.
- [ ] Scorecard meets threshold **and** all hard gates pass.
- [ ] Product owner, engineering and QA sign **technical MVP** release record; attach `OG1/OG2/OG3/OG4` status and explicitly prohibit unvalidated outcome claims.

# 9. Weighted quality scorecard (secondary to hard gates)

Weights and thresholds in this section are **[QA proposal]**, intended for comparative decision-making; they must never waive P0 failures.

| Category | Weight | Inputs |
|---|---:|---|
| Functional completeness & editability | 20 | DATA, TIME, ANIM |
| Reliable rendering, integrity & recovery | 20 | OPS, F-08–F-11, F-15–F-17 |
| Budget safety & provider integrity | 20 | COST, F-02–F-07 |
| Creative quality & narration fit | 20 | Shot rubric, three final episodes |
| Security, privacy & legal hygiene | 10 | TRUST, fault injections |
| Usability & production efficiency | 10 | Guided user task, workload metrics |
| **Total** | **100** | |

**Scoring method:** For each category, compute `verified passed applicable checks / total applicable checks × category weight`. For creative category use the normalized six-dimension episode rubric plus mandatory approval. Record `NOT TESTED` separately; do not shrink the denominator to hide untested mandatory cases. Partial credit may be used internally for trend analysis, never to call a mandatory check Passed.

- **GO:** All P0 PASS; all hard gates PASS; zero S0/S1; weighted score **≥ 90/100** [QA proposal]; signed decision.
- **CONDITIONAL GO:** All P0/hard gates PASS and zero S0/S1, score **85–89**, only explicitly accepted S2/S3 concerns; restricted beta, not public release [QA proposal].
- **NO-GO:** Any P0/hard-gate failure; any S0/S1; missing material financial/security evidence; score **< 85**; or missing sign-off.

# 10. Worked example: Jonah pilot gate evidence

**Scenario:** Import a 15-minute Jonah narration, one scene-plan JSON and character/environment images. Build mostly cinematic scenes; use layered animation for a ship rocking and sailors' silhouettes; generate a few paid clips for the throw and giant fish; render the episode.

| Checkpoint | Example observed evidence | Expected |
|---|---|---|
| Import | `project_manifest.json`, 25 imported media records, hashes and thumbnails | No missing required asset and no duplicate copies |
| Storyboard | Shot timeline spans 00:00 through 15:00, mapped to narration | No unintended gaps/overlaps |
| Preview | Start/mid/end playback, waveform and camera movement | Story beat understandable |
| Jonah action | Two or three distinct shots with explicit throw and fish beat | Accuracy/identity gate, human approved |
| Cost | Quote screenshots, approvals, provider job IDs, ledger | No silent paid calls or cap breach |
| Rerender | Changed fish shot, before/after dependency hashes | Unrelated approved clips unchanged |
| Export | MP4, ffprobe JSON, A/V sync checks, playthrough checklist | Correct codecs, dimensions, duration and content |
| Recovery | Kill/restart log, restored project/job state | No media loss or duplicate billable call |
| Final review | Timecoded creative rubric + product-owner signoff | Meets creative thresholds |

These are **required evidence types**, not claims that the application has passed them already.

# 11. CI/CD, release controls and test cadence

| Trigger | Minimum checks |
|---|---|
| Every commit / PR | Typecheck/lint; scene-schema unit tests; cost arithmetic/race-safe reservation tests; path validation; targeted UI tests |
| Merge to main | Integration tests with mocked provider; representative short FFmpeg render; database migration; cache invalidation |
| Nightly or benchmark machine | Longer render, concurrent jobs, crash injection, offline e2e, Windows installer smoke |
| Before release candidate | Full FX fixture suite; all F-01–F-18; 15-minute technical export; security scan; provider capped smoke |
| M4 pilot review | Three full creative reviews, measured provider spending and creator workload |

Maintain a reproducible Windows 11 x64 benchmark machine profile (CPU, RAM, GPU, disk, encoder, FFmpeg build, runtime versions). Performance numbers from a developer machine are not portable across all hardware.

# 12. Go / no-go decision template

```markdown
# StoryMotion Release Decision
Build / commit:
PRD baseline: v1.1 (2026-11-14)
Quality gates document version:
Platform / test machine:
Date:

G0 [PASS/FAIL]  G1 [PASS/FAIL]  G2 [PASS/FAIL]
G3 [PASS/FAIL]  G4 [PASS/FAIL]  G5 [PASS/FAIL]

P0 requirements: __ passed / __ total; __ blocked; __ not tested
S0 open: __    S1 open: __    S2 exceptions: __
Weighted score: __ / 100
15-minute export: [PASS/FAIL] (artifact ID/hash)
Narration A/V sync: __ ms max measured
Creative acceptance: __ / 3 pilot episodes
Financial cap test: [PASS/FAIL]
Actual incremental cash expenditure during pilot: $__
Provider billed spend reconciled: [YES/NO/PARTIAL]
OG1 baseline: [PASS / FAIL / NOT VALIDATED]
OG2 value: [PASS / FAIL / INSUFFICIENT SAMPLE / NOT VALIDATED]
OG3 4-week/8-episode viability: [PASS / FAIL / NOT VALIDATED]
OG4 ≥20-release deadline reliability: [PASS / FAIL / PENDING]
Manual baseline active minutes/finished minute: __
Studio active minutes/finished minute (median): __
Measured active time reduction: __%
AI first-attempt usable: __ / __ = __%
Episode creative mean across six criteria: __ / 5
Calendar-month incremental spend: $__ with reconciliation evidence
Cadence 2/week for 4 weeks: [VALIDATED / NOT YET TESTED / FAILED]

Technical release decision: [GO / CONDITIONAL GO / NO-GO]
Product outcome claim: [VALIDATED / NOT VALIDATED / PARTIALLY VALIDATED]
Exceptions and mitigations:
Evidence manifest path:
Engineering approver:
QA approver:
Product owner approver:
```

---

# Appendix A — P0 requirement traceability matrix

This checklist is generated from the P0 requirement IDs in the PRD. Every row must be mapped to evidence and given a final result. A unit-test result by itself does not demonstrate completion of the end-to-end user workflow.

| PRD requirement | Verification gate / evidence focus | Result | Evidence link |
|---|---|---|---|
| `FR-PROJ-001` | QG-DATA / DATA-01–03,07 | NOT TESTED | — |
| `FR-PROJ-002` | QG-DATA / DATA-01–03,07 | NOT TESTED | — |
| `FR-PROJ-003` | QG-DATA / DATA-01–03,07 | NOT TESTED | — |
| `FR-PROJ-004` | QG-DATA / DATA-01–03,07 | NOT TESTED | — |
| `FR-MEDIA-001` | QG-DATA / DATA-04–06 | NOT TESTED | — |
| `FR-MEDIA-002` | QG-DATA / DATA-04–06 | NOT TESTED | — |
| `FR-MEDIA-003` | QG-DATA / DATA-04–06 | NOT TESTED | — |
| `FR-MEDIA-004` | QG-DATA / DATA-04–06 | NOT TESTED | — |
| `FR-MEDIA-006` | QG-DATA / DATA-04–06 | NOT TESTED | — |
| `FR-SCRIPT-001` | QG-TIME / TIME-01–02 | NOT TESTED | — |
| `FR-SCRIPT-002` | QG-TIME / TIME-01–02 | NOT TESTED | — |
| `FR-SCRIPT-003` | QG-TIME / TIME-01–02 | NOT TESTED | — |
| `FR-SCRIPT-004` | QG-TIME / TIME-01–02 | NOT TESTED | — |
| `FR-TIME-001` | QG-TIME / TIME-03–04,07 | NOT TESTED | — |
| `FR-TIME-002` | QG-TIME / TIME-03–04,07 | NOT TESTED | — |
| `FR-TIME-003` | QG-TIME / TIME-03–04,07 | NOT TESTED | — |
| `FR-TIME-004` | QG-TIME / TIME-03–04,07 | NOT TESTED | — |
| `FR-TIME-005` | QG-TIME / TIME-03–04,07 | NOT TESTED | — |
| `FR-ANIM-004` | QG-ANIM / ANIM-01–05 | NOT TESTED | — |
| `FR-ANIM-005` | QG-ANIM / ANIM-01–05 | NOT TESTED | — |
| `FR-AI-001` | QG-COST / COST-01,05–07 | NOT TESTED | — |
| `FR-AI-002` | QG-COST / COST-01,05–07 | NOT TESTED | — |
| `FR-AI-003` | QG-COST / COST-01,05–07 | NOT TESTED | — |
| `FR-AI-004` | QG-COST / COST-01,05–07 | NOT TESTED | — |
| `FR-AI-005` | QG-COST / COST-01,05–07 | NOT TESTED | — |
| `FR-AI-006` | QG-COST / COST-01,05–07 | NOT TESTED | — |
| `FR-AI-007` | QG-COST / COST-01,05–07 | NOT TESTED | — |
| `FR-BUD-001` | QG-COST / COST-01–11 | NOT TESTED | — |
| `FR-BUD-002` | QG-COST / COST-01–11 | NOT TESTED | — |
| `FR-BUD-003` | QG-COST / COST-01–11 | NOT TESTED | — |
| `FR-BUD-004` | QG-COST / COST-01–11 | NOT TESTED | — |
| `FR-BUD-005` | QG-COST / COST-01–11 | NOT TESTED | — |
| `FR-BUD-006` | QG-COST / COST-01–11 | NOT TESTED | — |
| `FR-BUD-007` | QG-COST / COST-01–11 | NOT TESTED | — |
| `FR-BUD-008` | QG-COST / COST-01–11 | NOT TESTED | — |
| `FR-AUDIO-001` | QG-TIME / TIME-03,05–06 | NOT TESTED | — |
| `FR-AUDIO-002` | QG-TIME / TIME-03,05–06 | NOT TESTED | — |
| `FR-AUDIO-003` | QG-TIME / TIME-03,05–06 | NOT TESTED | — |
| `FR-AUDIO-004` | QG-TIME / TIME-03,05–06 | NOT TESTED | — |
| `FR-RENDER-001` | QG-OPS / OPS-01–06 | NOT TESTED | — |
| `FR-RENDER-002` | QG-OPS / OPS-01–06 | NOT TESTED | — |
| `FR-RENDER-003` | QG-OPS / OPS-01–06 | NOT TESTED | — |
| `FR-RENDER-004` | QG-OPS / OPS-01–06 | NOT TESTED | — |
| `FR-RENDER-005` | QG-OPS / OPS-01–06 | NOT TESTED | — |
| `FR-RENDER-006` | QG-OPS / OPS-01–06 | NOT TESTED | — |
| `FR-ANIM-001` | QG-ANIM / ANIM-01–05 | NOT TESTED | — |
| `FR-ANIM-002` | QG-ANIM / ANIM-01–05 | NOT TESTED | — |
| `FR-ANIM-003` | QG-ANIM / ANIM-01–05 | NOT TESTED | — |

**Coverage:** 48 distinct PRD P0 requirements mapped. This matrix needs one-to-many test case links in the test management system as implementation progresses.

# Appendix B — P1/P2 follow-on quality gates (non-blocking for MVP)

P1 should later introduce separate gates for structured LLM planning with token-cost accounting, captions, depth/segmentation quality, reusable presets, transcription alignment, provider invoice reconciliation, multiple provider comparison, optional local inference, pack/unpack, hardware acceleration, accessibility enhancements, and automatic QA heuristics. P2 adds rig/motion-guided animation and continuity scoring, collaboration, publishing, and TTS. **Do not mark P0 complete by building P1/P2 capabilities instead.**

# Appendix C — Change control and maintenance

1. Maintain a change log for PRD requirement amendments, thresholds and provider contracts.
2. Any change to price configuration, permission/approval, budget reservations, asset upload, or FFmpeg execution triggers a targeted regression of **QG-COST** and/or **QG-TRUST**.
3. Rebaseline benchmark timings when changing hardware, codecs, frame rate, or preview pipeline; do not rewrite test history.
4. When a requirement moves from P1 to P0, add its acceptance test and hard gate before release planning.
5. Archive a signed scorecard, three pilot outputs, hashes, actual cost report and known-issues summary for each release candidate.

**Final principle:** StoryMotion Studio is successful when it reliably produces *approved, narration-aligned, editable 15-minute stories under creator-controlled spending*, not simply when it can call a video AI model.

# Appendix D — Outcome validation sign-off template

```markdown
# StoryMotion Product Outcome Decision
PRD version: 1.1
Technical build / release ID:
Baseline dataset ID and manual method:
Four-week evaluation dates / calendar month(s):
Eligible AI-shot cohort definition and count:

O-01 8 episodes / 4 weeks, 2 each week: PASS / FAIL / UNKNOWN
O-02 incremental monthly cash <= $50: PASS / FAIL / UNKNOWN
O-03 >=50% hands-on-time reduction: PASS / FAIL / UNKNOWN
O-04 >=70% first-attempt usable paid clips: PASS / FAIL / INSUFFICIENT SAMPLE
O-05 >=4.0/5 and zero critical creative defects: PASS / FAIL / UNKNOWN
O-06 >=95% on time across >=20 scheduled releases: PASS / FAIL / PENDING
O-07 cost per accepted AI second: $___ (monitoring)

Engineering release status:
OG1 status:   OG2 status:   OG3 status:   OG4 status:

Evidence archive / artifact hashes:
Changes needed / Keep-Improve-Replace-Defer decisions:
Outcome claim permitted: YES / NO
Product owner signature / date:
Creative reviewer signature / date:
QA/engineering reviewer signature / date:
```

## Change log

- **v1.1 (2026-11-14):** Added OG1–OG4, O-01–O-07 outcome contracts, strict time-baseline comparison, first-pass usability measurement, ≥4/5 narrative-quality target, four-week/eight-episode publishing-viability validation, ≥20-release on-time assessment, evidence schemas and output-to-outcome traceability. Retained all existing P0 hard safety/reliability gates and 90-point technical release score.
