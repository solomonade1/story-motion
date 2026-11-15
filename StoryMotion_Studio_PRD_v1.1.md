# StoryMotion Studio
## Product Requirements Document (PRD)

**Version:** 1.1 — Outcome-aligned build specification  
**Date:** 14 November 2026  
**Status:** Proposed / outcome thresholds pending product-owner baseline approval  
**Product category:** Local-first, narration-driven storytelling and video production studio  
**Initial niche:** Animated Bible stories; extensible to history, education, documentaries, and other narrative content  
**Target platform:** Windows desktop first; macOS later  
**Target cadence:** 2 × 15-minute videos per week (approximately 8–9/month)  
**Incremental cash operating budget:** Hard cap of **US$50/month**, excluding existing ChatGPT/Claude subscriptions, hardware, electricity, labor, and internet access  
**Primary user:** Solo faceless YouTube storyteller / small content team
**Companion acceptance contract:** `StoryMotion_Studio_Quality_Gates.md` v1.1

> **Product promise:** Turn a prepared narrative, narration audio, and static character/scene illustrations into an editable, polished, YouTube-ready video through reusable cinematic motion, optional controlled animation, and highly selective cloud AI-generated action clips—without requiring persistent hosting or full-frame generative video for the entire runtime.

---

# 1. Executive summary

StoryMotion Studio is a **local-first desktop video-production application** that transforms narrative scripts, narration audio, and visual assets into finished storytelling videos. Its differentiator is a **narration-first, budget-aware animation pipeline** that routes each shot to the least expensive technique capable of communicating the narrative:

1. **Cinematic still animation:** pan/zoom, reframing, 2.5D depth parallax, layered effects, light and atmospheric motion.
2. **Controlled 2D animation:** sprite/layer transforms, reusable animation presets, simple cut-out/rig workflows when assets permit.
3. **Generative action animation:** optional paid image-to-video API for visually complex actions (throwing, running, storms, miracles, creatures), with approvals, retry limits, and strict budget enforcement.

Rather than promise a fully autonomous 3D animated movie, StoryMotion aims to **automate assembly and repetitive editing while preserving human creative approval**. It should generate complete 15-minute episodes using mostly original still illustrations and controlled motion, with only a small proportion of actual generative video. The tool must remain useful **with no API key or internet connection**, except for explicitly cloud-dependent features.

## 1.1 Critical product assumptions

- Existing paid ChatGPT and Claude subscriptions are used *manually* for research, scriptwriting, illustration planning, and structured scene-plan preparation. Their chat subscriptions **do not imply included API access** for this app.
- The producer already has or can supply static character illustrations; the MVP is not required to create them.
- Narration audio is supplied by the user; first-party TTS is **not** an MVP dependency.
- AI image-to-video pricing, supported duration, output size, queue time, and availability can change. Providers and prices are configured—not hardcoded as product guarantees.
- A single flat image **cannot** be reliably converted into arbitrary articulated body motion using traditional rigging alone; the system must distinguish animation capability by asset type.
- The $50 target is a **spending ceiling**, not a guaranteed outcome. It is met only if shot allocation and cloud-generation volume stay within budget.
- At 2 × 15 minutes weekly, the application targets roughly 130 finished minutes per average month (52/12 × 2 × 15), with an average incremental spend of **≤$5.77 per video** at $50/month.

---

# 2. Problem definition

## 2.1 User problem

Creators can readily obtain engaging illustrations and write compelling Bible-story scripts, but producing coherent moving footage for 15-minute episodes is labor-intensive and expensive. Image-to-video systems can animate individual scenes but often:

- consume a paid API budget per generation and retry;
- fail to follow exact physical action requirements;
- alter a character's face, clothing, identity, or scale;
- produce discontinuities between scenes;
- lack reusable editing and narration-alignment workflows;
- make it hard to produce consistent episodes on a twice-weekly schedule.

Conventional video editors can assemble footage but typically require manual creation of every shot, animation keyframe, transition, and timing adjustment.

## 2.2 Core problem statement

**How might we turn a script, voice narration, and static character illustrations into cohesive, narration-synchronized 15-minute animated storytelling episodes—at a sustainable output of two videos per week—while keeping additional monthly cash production expenses below $50 and ensuring creators can inspect, alter, and approve every important scene?**

## 2.3 Jobs to be done

- **When** I finish researching and writing a Bible story, **I want** to import the script and narration and turn them into an editable scene timeline, **so** I can start visual production without redoing the breakdown manually.
- **When** I have static illustrations, **I want** the tool to animate them with cinematic movement and effects, **so** the video does not feel like an unedited slideshow.
- **When** a story requires dramatic physical action, **I want** to generate a short AI action shot, **so** key moments feel dynamic without generating the entire episode with AI.
- **When** I replace an illustration or retry one shot, **I want** to render only the affected portions, **so** I avoid wasting time and money.
- **When** I approach my monthly budget cap, **I want** accurate estimates and enforced limits, **so** the application never initiates a chargeable request without my approval.
- **When** I export a completed episode, **I want** synchronized audio, consistent aspect ratio, and a reliable MP4, **so** the output is ready for YouTube review and upload.

---

# 3. Product vision, principles, and goals

## 3.1 Vision

A personal animation production assistant that makes high-quality illustrated storytelling accessible without film-studio workflows, powerful local video-model hardware, or unpredictable cloud invoices.

## 3.2 Product principles

1. **Narration first:** Timing and visual changes serve the story and voiceover.
2. **Local first:** Projects, assets, edits, and renders stay on the creator's machine by default.
3. **Budget before beauty:** Default to no-cost techniques; request paid generation only when its storytelling value justifies it.
4. **Deterministic whenever possible:** Edits to pan, crop, transitions, audio, and layered motion should not require another AI generation.
5. **Editable, not black-box:** Store shot-level instructions and timelines in inspectable formats.
6. **Human approval for costly actions:** No surprise API calls or silent retries.
7. **Asset-aware control:** Do not imply flattened illustrations have hidden skeletons or 3D geometry.
8. **Repeatable production:** Reuse templates, character references, effects, scene patterns, caches and export presets.
9. **Model/provider neutrality:** User may replace AI inference provider without migrating the project structure.
10. **Credible, not magical:** Clearly show limitations, fallback paths, failures, and estimated output quality.

## 3.3 Measurable goals

| Goal | MVP acceptance / target | Method |
|---|---|---|
| End-to-end output | Export a complete ~15-minute 1080p 16:9 episode from script, narration, and imported assets | Jonah pilot acceptance test |
| Unit of rework | Re-render an edited shot or section without regenerating unrelated approved AI clips | Cache/provenance test |
| Spend control | No chargeable generation is submitted if it would cross the configured hard spending cap | Automated budget gate test |
| Offline usefulness | Edit, preview, and export local-asset projects without a network connection | Offline smoke test |
| Assembly reliability | Project and pending render jobs survive app restart/crash | Recovery test |
| Audio sync | Exported narration and scene timing remain within defined frame/timeline tolerance | Automated A/V checks and review |
| Human approval | User can review and approve/reject proposed costly video generations | UX/functional test |
| Output cadence | Support repeatable production of 2 episodes/week with creator review | Pilot measured over 4 weeks (aspirational, not guaranteed) |
| Incremental monthly spend | ≤$50 by explicit user cap; user can choose lower budget | Cost ledger audit |

**Non-goals for the MVP:** guarantee viral traction, guarantee audience retention, automatic scripture truth verification, perfect physics, pixel-exact character consistency from generic video models, replacement for Blender/Resolve, fully automated publishing, and guaranteed production time savings before real-world measurement.

---

## 3.4 North-star outcome and product success hypothesis

**North-star outcome (O-01):** A solo creator can consistently complete **two publishable ~15-minute Bible-story episodes per week**, with **incremental in-scope cash spend ≤ US$50 per calendar month**, **≥50% lower hands-on production time** against a comparable manual baseline, and **no meaningful decline in editorial/visual quality**.

This is a **hypothesis to validate**, not a guaranteed characteristic of the shipped software. Technical correctness enables the outcome; creator workflow and viewer-facing quality determine whether it is realized.

**Outcome hierarchy:**

1. **Business/operational:** sustainable weekly publishing cadence and bounded monthly cost.
2. **Creator value:** faster delivery, less rework, editable output, useful generated motion.
3. **Capabilities (outputs):** scene planning, asset reuse, cinematic animation, selective paid actions, narration timeline, export and spend guardrails.
4. **Engineering safeguards:** accurate accounting, predictable jobs, recoverability, security, reproducible exports.

## 3.5 Outcome success criteria and ownership

All numeric targets below are **proposed outcome thresholds** until baselined in an approved decision record. They are distinct from the existing **P0 feature requirements** and **engineering release checks**.

| ID | Desired outcome | Proposed threshold | Measurement / evidence | Owner |
|---|---|---|---|---|
| **O-01** | Consistent creator delivery | **8 approved ~15-minute episodes across 4 consecutive weeks**, planned at 2/week | dated episode approval logs and exported artifact hashes; scheduled week and actual completion | Product owner / creator |
| **O-02** | Affordable production | **≤$50 actual incremental in-scope cash spend per calendar month**, including all planned and unexpected billable attempts and other in-scope purchases | provider invoices/usage, receipts and reconciled local ledger, attributed to month | Product owner / finance owner |
| **O-03** | Material reduction in creator effort | **≥50% reduction in hands-on minutes per finished minute** relative to a comparable manual workflow, using median episode-level rates | activity timer/time log with included tasks defined below; baseline vs studio comparison | Product owner / creator |
| **O-04** | Efficient AI generation | **≥70% of paid generation attempts yield a first-attempt usable clip** on the predefined eligible-shot sample; separately track all attempts and creative rejects | first-attempt clip review records with rubric and accepted/rejected flags | Creative reviewer / QA |
| **O-05** | Adequate story and visual quality | **≥4.0/5 mean episode score** across the six-dimension rubric, **no critical story/action failures**, and creator approval | reviewer scoring sheets, timecoded defects, approved exports | Creative reviewer |
| **O-06** | Operational publishing reliability | **≥95% on-time completions over an extended pilot of ≥20 scheduled releases**; during the initial 8-video pilot record raw on-time count, not a 95% claim | predeclared scheduled due dates and approval timestamps | Product owner / QA |
| **O-07** | Efficient useful AI footage | cost per accepted AI second decreases or remains within the approved shot allocation; **measured rather than hard-gated initially** | actual charges / accepted, unique generated seconds | Product owner / engineering |

**Publishable** means a creator-approved, technically valid, narratively coherent exported file ready for YouTube review/upload; it does **not** require a YouTube upload or guarantee audience performance. **On time** means approved before the creator's predeclared release deadline, not a timestamp reconstructed after completion.

## 3.6 Manual baseline and experiment design (OG1)

Before claiming time savings, conduct and document a **manual-method baseline**:

- Produce at least **one representative ~15-minute episode** (preferably two or more) using the creator's current workflow **without StoryMotion's automation**. Reuse permitted existing ChatGPT/Claude subscriptions and comparable asset inputs for both conditions.
- Freeze the script complexity, approximate shot count, supplied narration length, intended quality rubric, asset availability and starting-state assumptions; log material differences and confounders.
- Count **active creator minutes** spent on storyboarding, media preparation, visual motion, clip generation oversight, editing, review, correction and export troubleshooting. Separately record elapsed wall-clock time and model/API queue time; never substitute one for the other.
- Record direct cash cost, revisions, accepted clips, final duration, six-dimension quality scores and number of failed exports. Keep invoices, activity logs and an anonymized artifact reference.
- Use **median hands-on minutes / finished-video minute** as the comparison statistic. Compute reduction as `1 - (Studio median rate / Manual baseline median rate)`. A negative value indicates regression.
- Log prompt-writing, asset sourcing and human intervention equally in both workflows; previously created source images and paid subscriptions must be treated consistently. If tasks are excluded, document exclusions explicitly.
- During OG2, compare a **minimum three Studio-produced episodes** against the baseline. Flag sample-size uncertainty; do not infer causal improvement from unbalanced tasks or solely from self-reported impressions.

If a credible baseline cannot be produced, report O-03 **NOT VALIDATED**, not PASS.

## 3.7 Product decisions driven by outcome evidence

Each substantial feature or epic must document: **user problem → intended outcome ID → smallest capability → leading indicator → evaluation experiment → keep/improve/remove decision**. No epic is considered *outcome-successful* solely because its implementation or P0 tests pass.

| Capability / epic | Outcome(s) supported | Leading indicator | Decision question |
|---|---|---|---|
| Script-to-storyboard / E3 | O-01, O-03, O-05 | minutes to first reviewed storyboard; visual-to-narration defect rate | Does it reduce planning time without damaging storytelling? |
| Asset library / E2 | O-03, O-05 | reusable shot/asset ratio; continuity corrections | Does reuse save effort while preserving distinct episodes? |
| Cinematic + controlled animation / E4 | O-02, O-03, O-05 | local-shot acceptance rate; active correction minutes | Can this replace paid AI without slideshow fatigue? |
| Paid action generation / E5 | O-02, O-04, O-05, O-07 | first-attempt usable rate, charged attempts, effective cost/accepted second | Does this provider improve accepted actions enough to justify spend? |
| Narration timeline and exports / E2–E3 | O-01, O-03, O-05, O-06 | time to approved export; narration alignment/re-export rate | Does it reduce finishing effort and protect deadlines? |
| Cost dashboard / E6 | O-02, O-07 | reconciled spend; unauthorized/over-cap attempts | Does it prevent surprise charges and guide cheaper decisions? |
| Recovery and error handling / E1–E7 | O-01, O-03, O-06 | lost active minutes; recoverable incidents | Does reliability preserve production throughput? |

**Example:** A cloud adapter that successfully returns an MP4 has achieved a functional **output**. It has **not** delivered O-04/O-05 if Jonah's identity drifts or sailors fail to throw him. Replace the shot, improve conditioning or use a controlled fallback; do not close the outcome as PASS merely because the API succeeded.

## 3.8 Success states, leading/lagging indicators and boundaries

- **MVP TECHNICALLY READY:** all P0 functionality and required engineering/creative safety checks pass; three-episode pilot measured. Does not imply throughput or time-savings validated.
- **VALUE SIGNAL OBSERVED:** baseline exists; three Studio episodes show promising, measured cost/time/quality improvement. Record uncertainty and unmet metrics.
- **OUTCOME VALIDATED:** OG1–OG3 pass, including four consecutive weeks, eight approved episodes, reconciled monthly cash cap, time-saving threshold, AI clip usefulness and creative quality. O-06 remains **EXTENDED VALIDATION PENDING** until ≥20 scheduled releases are observed.
- **OUTCOME NOT VALIDATED:** objective threshold fails or material evidence is missing. Shipping may still be a labelled internal/limited MVP where safety gates pass, but not marketed as a proven twice-weekly, half-time workflow.

**Avoid conflating creator workflow outcomes with YouTube audience outcomes.** Click-through rate, retention, repeat viewing and revenue are separate post-publication learning measures. Record them if available, without making virality or monetization an MVP release promise.

---

# 4. Personas, use cases, and scenarios

## 4.1 Persona A — Solo animated Bible-story creator (primary)

- Produces 15-minute stories with an existing image-generation workflow.
- Already pays for ChatGPT and Claude; additional cash budget is constrained.
- Comfortable with a scene editor but not sophisticated 3D rigging.
- Wants predictable progress, simple controls, and 16:9 YouTube exports.

## 4.2 Persona B — Small narration/documentary team (secondary, later)

- One person writes/voices; another reviews visuals.
- Needs portable project bundles, shot status, approved drafts, and editorial handoff.

## 4.3 Reference user story: Jonah and the great fish

Input: original story script, narration WAV/MP3, images of Jonah, ship, sailors, storm, sea, giant fish. The editor automatically drafts a storyboard aligned with narration; applies low-cost motion to atmospheric/dialogue scenes; identifies the throwing/swallowing sequence as a paid action candidate; requests explicit approval for any cloud AI generation; and assembles the resulting short clips into a coherent 15-minute export.

A complex action such as **sailors throwing Jonah into the water while a fish swallows him** should be represented by **multiple editable shots** rather than a single mandatory 5-second generation.

---

# 5. Scope and release strategy

## 5.1 P0 — First usable MVP (must-have)

- Local Windows desktop app, project create/open/save/duplicate/delete.
- Import audio, script (TXT/Markdown), images, and video clips.
- Manual scene plan import (JSON) plus a guided editor for scenes/shots.
- Waveform-backed narration-first timeline and duration editing.
- Cinematic still motions (pan, zoom, crop/reframe, simple parallax where layers exist).
- Scene/asset library with thumbnails and tags.
- Simple title/card, crossfade, cut, basic overlays and ambient layers.
- Provider abstraction with **one** optional image-to-video cloud adapter.
- Exact per-job budget estimate, user approval, monthly cap, retry cap, spending ledger.
- Generate, poll/cancel where supported, preview, approve, or reject cloud clip.
- Asynchronous render jobs with progress, cancellation, recovery and diagnostics.
- FFmpeg-based 1080p H.264 + AAC MP4 export and reusable YouTube preset.
- Cache by inputs/settings; invalidation of edited scenes only.
- Local filesystem and SQLite, with no dedicated hosted backend.

## 5.2 P1 — Workflow acceleration (after pilot)

- Optional low-cost LLM API auto-storyboard with structured output and tokens/cost logs.
- Audio transcription/word timestamps via opt-in external or local adapter.
- Template library: ocean, storm, desert, ancient town, prayer, crowd, battlefield.
- Character reference packs, appearance descriptions, recurring shot setups.
- Multi-layer cut-out animation: separated body parts, anchors, pivots, easing.
- Smart action routing and pre-generation shot-cost suggestions.
- Image segmentation and depth estimates as *optional* on-demand tasks.
- Quality checks for black frames, silence, aspect ratio, and visual anomalies.
- Batch project pack/unpack and archive.

## 5.3 P2 — Advanced animation (defer)

- Motion-conditioned video generation and pose-control adapters.
- Blender headless rig animation and reference motion rendering.
- Character identity tracking, shot-transition continuity scoring.
- Automatic re-timing of visuals to narration.
- Multiple providers and provider comparison mode.
- Team collaboration, shared storage, asset approvals.
- Direct YouTube publishing and analytics integration.
- Automated music/voice generation, licensing management.

## 5.4 Explicit non-scope

- Training/fine-tuning video foundation models.
- Full non-linear editor feature parity (Resolve/Premiere/Kdenlive).
- Automatic creation of faithful 3D character rigs from one flattened image.
- Generating all 15 minutes with image-to-video inference by default.
- Always-on cloud infrastructure or subscription-based backend.
- Automated bulk upload/publishing in the MVP.

---

# 6. End-to-end user journey

1. **Create project:** Enter title, target 16:9, output duration, frame rate (24/30), and monthly/project budget.
2. **Import source material:** Add script, voice narration, character images, backgrounds, sound effects, and any approved AI clips.
3. **Prepare storyboard:** Import scene-plan JSON generated with ChatGPT/Claude, or create/edit scenes manually; later optionally run an LLM planner.
4. **Map scenes to narration:** Place boundaries on the waveform; adjust scene timings; assign each narration span to scene/shot.
5. **Assign assets:** Reuse named character/environment assets; pick crops and visual style; preview matching shots.
6. **Choose animation mode:** The system suggests CINEMATIC, LAYERED, or GENERATIVE; user can override.
7. **Edit cinematic shots:** Set framing, camera path, speed/easing, depth layers and effects; preview instantly or via fast render.
8. **Generate action shots:** Show model/provider, source images, prompt, duration, quality, *known or estimated charge*, retry policy, and current budget remaining. Require approval before chargeable submission.
9. **Review outputs:** Approve/replace/regenerate individual shots; preserve source versions and generation provenance.
10. **Add polish:** Music, atmospheres, cuts, transitions, titles, subtitles (optional phase), sound levels.
11. **Preflight:** Missing asset checks, timeline gaps, audio clipping checks, aspect/resolution validation, budget report, and export-space check.
12. **Export:** Choose YouTube preset; render locally; show progress and logs; save final MP4.
13. **Duplicate/template next episode:** Keep reusable presets and character references without retaining storyline-specific assets incorrectly.

---

# 7. Functional requirements

Priority: **P0** must ship for first useful MVP; **P1** recommended next; **P2** optional. Acceptance criteria use *Given / When / Then* where useful.

## 7.1 Projects and filesystem

**FR-PROJ-001 [P0]** Create, rename, open, duplicate, archive, and delete a project.  
**FR-PROJ-002 [P0]** Autosave after meaningful edits, with crash-safe atomic writes and at least one recoverable prior manifest.  
**FR-PROJ-003 [P0]** Persist relative asset references where feasible; show repair workflow for missing media.  
**FR-PROJ-004 [P0]** Maintain project schema version and migrations.  
**FR-PROJ-005 [P1]** Export/import portable project archive with assets, manifest, and thumbnails.

**Acceptance:** Given an edited project, when the app terminates unexpectedly, then reopening offers the most recent valid saved state; corrupt/absent media is clearly diagnosed rather than causing data loss.

## 7.2 Import and media analysis

**FR-MEDIA-001 [P0]** Import PNG/JPEG/WebP images; WAV/MP3/AAC audio; MP4/MOV where supported by local decoding.  
**FR-MEDIA-002 [P0]** Extract dimensions, duration, audio sample rate, frame rate where relevant, size, and file hash.  
**FR-MEDIA-003 [P0]** Generate thumbnails and compressed preview proxies.  
**FR-MEDIA-004 [P0]** Provide asset categories: character, environment, prop, audio, generated video, effect.  
**FR-MEDIA-005 [P1]** Support masks, alpha layers, PSD/PNG sequence, segmentation outputs, and depth maps.  
**FR-MEDIA-006 [P0]** Handle duplicate file detection, file import failures, and non-destructive linking/copying options.

**Acceptance:** Reimporting identical bytes does not create redundant source files unless explicitly requested; unusable media surfaces a clear error.

## 7.3 Script and storyboard

**FR-SCRIPT-001 [P0]** Import TXT/Markdown scripts and edit text.  
**FR-SCRIPT-002 [P0]** Import validated StoryMotion scene-plan JSON; show schema errors with location and field.  
**FR-SCRIPT-003 [P0]** Create/edit scenes, shots, narration text, characters, instructions, priority, proposed animation mode and expected duration.  
**FR-SCRIPT-004 [P0]** Bind scenes to specific narration time ranges.  
**FR-SCRIPT-005 [P1]** Optional LLM planner using provider adapter and structured output with approval prior to replacing existing plan.  
**FR-SCRIPT-006 [P1]** Store provenance for model, prompt and token usage for LLM planning.  
**FR-SCRIPT-007 [P1]** Warn for scenes without matching narration or scenes significantly longer/shorter than their allotted time.

**Acceptance:** User can import a manually generated scene plan, edit it without API calls, and render from its timeline entries.

## 7.4 Timeline and preview

**FR-TIME-001 [P0]** Narration master track, visual shot track, background music track, sound effects track, titles/overlays track.  
**FR-TIME-002 [P0]** Waveform for narration, playback scrubber, snap-to-boundary, and editable shot start/end.  
**FR-TIME-003 [P0]** Cuts, crossfades, fade-to-black, per-shot trim, scale/position/crop and opacity.  
**FR-TIME-004 [P0]** Resolve timeline conflicts: overlaps, gaps, negative durations, and missing references.  
**FR-TIME-005 [P0]** Preview using proxies or pre-rendered segments; clearly label preview fidelity differences.  
**FR-TIME-006 [P1]** Undo/redo command history, multi-select, keyboard shortcuts, marker annotations.  
**FR-TIME-007 [P1]** Captions/subtitle import and export.

**Acceptance:** A 15-minute project plays continuously using proxies without requiring GPU diffusion inference; exported composition has no unintended black timeline gaps.

## 7.5 Animation modes

**FR-ANIM-001 [P0] — CINEMATIC:** Render Ken Burns pan/zoom, crop/reframe, easing, foreground overlay, particle-like effects and simple scene camera movement from static images.  
**FR-ANIM-002 [P0] — LAYERED BASIC:** Translate/rotate/scale alpha-enabled subject layers and props using keyframes, anchors and easing; no assumption of inferred body skeleton.  
**FR-ANIM-003 [P0] — GENERATIVE:** Submit an image and prompt to the selected image-to-video provider, with model-specific capabilities validated.  
**FR-ANIM-004 [P0]** Mark a shot as STATIC, CINEMATIC, LAYERED or GENERATIVE, along with fallback if unsupported.  
**FR-ANIM-005 [P0]** Let user override recommendation and retain approved result as immutable version.  
**FR-ANIM-006 [P1]** Depth-aware 2.5D parallax, mask previews and segmentation import.  
**FR-ANIM-007 [P1]** Preset library: ship sway, waves, handheld shake, walking sprite cycle, praying pose, lightning, floating fabric.  
**FR-ANIM-008 [P2]** Blender rig control and motion-driven video generation.

**Acceptance:** For each shot, UI shows the chosen mode, technical limitations, and whether generation is deterministic/free or remote/paid.

## 7.6 Generative provider adapter

**FR-AI-001 [P0]** One cloud video provider implemented behind generic adapter methods; no provider-specific fields leak into core story/timeline entities.  
**FR-AI-002 [P0]** Capabilities discovery/configuration: supported image formats, durations, resolutions, aspect ratios, frame controls, reference inputs, price model, cancellation and progress support.  
**FR-AI-003 [P0]** Create a validated generation request containing source images, prompt, negative prompt where supported, duration/resolution, style references, seed if supported, and metadata.  
**FR-AI-004 [P0]** Support asynchronous submission, polling, retry with backoff on transient network failure, provider job ID, download, hash validation and durable job state.  
**FR-AI-005 [P0]** Distinguish a *transport retry* of the same idempotent provider job (if supported) from a *new billable creative attempt*. No silent new billable attempts.  
**FR-AI-006 [P0]** Allow user to approve/reject and regenerate only targeted shots.  
**FR-AI-007 [P0]** Display provider warnings when character/physics constraints may not be strictly enforceable.  
**FR-AI-008 [P1]** Multiple providers / model benchmark comparison.  
**FR-AI-009 [P1]** Local inference provider optional; not required by MVP.

**Acceptance:** If the provider is offline, unsupported, or rate-limited, the project remains editable; failed generation does not corrupt approved outputs or trigger an unapproved chargeable retry.

## 7.7 Budget guardrails and accounting

**FR-BUD-001 [P0]** User configures monthly hard cap (default $50), project cap, provider cap, and currency (USD baseline).  
**FR-BUD-002 [P0]** Calculate a cost quote before submission from the active price configuration, including provider duration rounding/minimums and model settings.  
**FR-BUD-003 [P0]** Reserve estimated budget for pending jobs; account for committed charges upon completion or provider charge event.  
**FR-BUD-004 [P0]** Refuse submissions exceeding cap using **spent + active reservations + new estimate > cap**.  
**FR-BUD-005 [P0]** Require explicit confirmation before every billable attempt (or user-configured approved batch envelope).  
**FR-BUD-006 [P0]** Track quote, provider job ID, timestamp, model/config, estimated amount, charged amount if known, currency, and discrepancy.  
**FR-BUD-007 [P0]** Unknown pricing or ambiguous charging rules **fail closed**—no automatic submission.  
**FR-BUD-008 [P0]** Show remaining budget and warnings at 50%, 75%, 90% and 100%.  
**FR-BUD-009 [P1]** Reconcile actual provider bills where API billing data is available; otherwise allow explicit manual adjustments.  
**FR-BUD-010 [P1]** Suggest lower-cost alternatives for shots, including cinematic instead of generative mode.

**Caveat:** A local application cannot guarantee the user's total vendor bill when charges may occur outside StoryMotion or when provider price/status data is unavailable. The hard cap governs **jobs initiated by the application based on available pricing and reservations**; its scope is shown clearly.

**Acceptance:** Given $49 already spent/reserved and a $2 estimated new generation, the application blocks the submission even if the user presses Generate; the user must change a valid cap configuration consciously (never silent override).

## 7.8 Narration/audio

**FR-AUDIO-001 [P0]** Import narration and display waveform; narration length provides a timeline duration baseline.  
**FR-AUDIO-002 [P0]** Overlay music and SFX tracks with volume, fade-in/out and trim.  
**FR-AUDIO-003 [P0]** Export audio at 48 kHz AAC stereo unless user changes supported preset.  
**FR-AUDIO-004 [P0]** Warn on missing narration, obvious clipping, or significant output duration mismatch.  
**FR-AUDIO-005 [P1]** Auto ducking and loudness normalization.  
**FR-AUDIO-006 [P1]** Optional transcription/timestamp alignment.  
**FR-AUDIO-007 [P2]** Text-to-speech integration; not necessary when voiceover is supplied.

## 7.9 Export/render

**FR-RENDER-001 [P0]** Render using local FFmpeg subprocess with explicit validated commands and temp outputs.  
**FR-RENDER-002 [P0]** Standard output preset: 1920×1080, 16:9, H.264, 24 or 30 fps, AAC audio, MP4, reasonable configurable quality settings.  
**FR-RENDER-003 [P0]** Provide low-resolution draft export and final export.  
**FR-RENDER-004 [P0]** Show progress, estimated remaining workload (not guaranteed time), log excerpts, cancel, resume/restart safe operations.  
**FR-RENDER-005 [P0]** Validate output existence, duration, dimensions, codecs, audio track and file integrity before marking complete.  
**FR-RENDER-006 [P0]** Cache intermediate render segments and invalidate only dependent content using source/dependency hashes.  
**FR-RENDER-007 [P1]** Hardware encoder detection with fallback to software x264.

**Acceptance:** A completed export opens in standard players, has synchronized narration, no unintended blank frames, and can be reproduced without repeating unrelated cloud generation.

---

# 8. Story planning and scene-routing design

## 8.1 Scene hierarchy

- **Project:** One finished video episode.
- **Narrative segment:** Script/narration span with a narrative purpose.
- **Scene:** Coherent location/time/story action.
- **Shot:** Timed visual unit with assets, camera/animation instructions, and renderer/provider selection.
- **Asset:** Source image, layer, background, video, voice, music, SFX, mask, or reference.
- **Render:** Materialized video/audio corresponding to a fixed version of a shot.

## 8.2 Routing rules (first release)

- **STATIC/CINEMATIC default:** Dialogue, reflection, exposition, landscapes, transitions, prayer, location establishing shots.
- **LAYERED where inputs support it:** Ship rocking, floating props, separately isolated character entrance, waving fabric, clouds, smoke, foreground occluders.
- **GENERATIVE opt-in:** Throwing, falling, swallowing, fighting, close physical interaction, complex creatures, highly dynamic motion.
- **Manual override:** User always chooses; suggestions are not automatic spending authorization.
- **Long complex action:** Split into short shots with explicit states and continuity references; do not expect one prompt to produce multiple exact interactions reliably.

## 8.3 Shot decision score (P1)

A transparent heuristic may combine:

`need_for_motion × narrative_importance × expected_model_success ÷ estimated_cost`

This is a **ranking heuristic**, not an actual quality guarantee. The system must separately honor the hard budget and creator overrides. A deterministic alternative (e.g., 2.5D parallax) is always offered when available.

## 8.4 Jonah example

- Shot A: ship in thunderstorm → CINEMATIC + layered waves/lightning.
- Shot B: Jonah looks toward sailors → CINEMATIC, plus layered head/silhouette if source permits.
- Shot C: sailors lift and throw Jonah → GENERATIVE or rig-guided P2.
- Shot D: Jonah falls toward sea → GENERATIVE short clip.
- Shot E: giant fish emerges/swallowing → GENERATIVE short clip or stylized silhouette composite.
- Shot F: underwater darkness/narration → CINEMATIC / environmental visual effects.

User may allocate only 1–3 AI action clips to the whole sequence by creative editing (cutaways, silhouettes, sound, reaction shots); no need to render every event explicitly.

---

# 9. Information architecture and screens

## 9.1 Required screens

1. **Projects:** Recent projects, create/open/duplicate, local storage location, export status.
2. **Import Wizard:** Script, audio, images, videos, media health warnings.
3. **Storyboard:** Scenes and shots with order, narration span, text, image reference, animation mode, review status.
4. **Editor:** Media bin, central preview, inspector, multi-track timeline, narration waveform.
5. **Shot Inspector:** Source assets, crop, camera, layers, transitions, FX and generation prompt/settings.
6. **AI Generation Review:** Cost preview, provider, generation settings, remaining budget, submit/approve/reject/history.
7. **Budget:** Month/project spend, reservations, API provider rates, discrepancy warnings.
8. **Render Queue:** Active/queued/failed/cancelled/completed jobs, logs, retry, artifact paths.
9. **Settings:** API secrets, local paths, FFmpeg detection, hardware acceleration, templates, privacy, export presets.

## 9.2 UX requirements

- Default guided flow: **Import → Storyboard → Animate → Review → Export**.
- A creator should be able to complete the core pipeline without learning a node-based compositor.
- Clearly label **AI-required** vs **local/no API charge** operations.
- Never silently transmit media to third-party APIs; reveal selected files, destination provider and cost.
- Provide a **revert to last approved render** action for generated shots.
- Show three statuses distinctly: *draft*, *approved*, *out-of-date after source changes*.
- Provide a simple preview quality switch to avoid costly full-resolution work during editorial iteration.

---

# 10. Proposed architecture

## 10.1 System boundaries

```text
┌────────────────────────────────────────────────────────────────┐
│ StoryMotion Desktop (Tauri 2 + React/TypeScript)               │
│ Projects · Assets · Storyboard · Editor · Timeline · Budget UI │
└─────────────────────────────┬──────────────────────────────────┘
                              │ Tauri commands / localhost IPC
┌─────────────────────────────▼──────────────────────────────────┐
│ Local orchestration workers (Python, supervised by Tauri)      │
│ - Project validation + shot graph                              │
│ - Media probing / thumbnails / proxies                         │
│ - Local render DAG + FFmpeg invocation                         │
│ - AI provider adapters + job polling                           │
│ - Cost quote/reservation/ledger                                 │
│ - Cache, version history, retries, cancellation                 │
└───────────────┬───────────────────────┬────────────────────────┘
                │                       │
       Local filesystem/SQLite      Optional HTTPS requests
                │                       │
       Assets/cache/exports       Cloud image-to-video provider
       FFmpeg / optional Blender  (signed uploads / API jobs)
```

**Implementation note:** Running Python as a supervised subprocess simplifies packaging compared with deploying an HTTP service. A loopback-only API is acceptable when operationally necessary, with a random session token and strict local binding. Tauri commands must validate paths and reject arbitrary command execution.

## 10.2 Technology choices

| Layer | MVP choice | Rationale |
|---|---|---|
| UI | React + TypeScript + Tailwind/shadcn/ui | Rapid desktop-style editor development |
| Shell | Tauri 2 | Smaller wrapper, OS integration, secure IPC |
| State | Zustand for editor + TanStack Query for async state (or equivalent) | Separate interactive editor from operations |
| Timeline | Custom purpose-built timeline + Canvas/WebGL where necessary | Avoid building entire NLE immediately |
| Media playback | Native HTML video/audio with low-res proxies | Low-complexity preview |
| Orchestration | Python 3.11+ | Strong media/ML compatibility and provider SDKs |
| Local DB | SQLite (WAL where appropriate) | Offline indexing, job ledger, asset relationships |
| Render | FFmpeg / ffprobe | Media probe, filters, audio mix, H.264/AAC export |
| Animation | FFmpeg filters + transform/layer graph | Deterministic low-cost movement |
| Optional later | Blender headless | Rigging and controlled 3D reference rendering |
| Cloud inference | Adapter for one selected supported provider | No GPU inference required on laptop |
| Secrets | OS credential store / secure keychain-backed storage | Keep API keys out of files and UI bundle |

### Packaging decision

**MVP:** Desktop app includes or installs a pinned compatible FFmpeg distribution, plus a supervised Python worker with versioned dependencies. The installer should have a first-run readiness check. Packaging/license review is required for bundled FFmpeg builds and any other third-party binaries; do not assume all redistributions have the same obligations.

## 10.3 Execution and processing split

- **UI process:** user actions, lightweight timeline, previews, media selection.
- **Worker processes:** thumbnails, ffprobe, effects/render, scene checks, cloud job I/O; isolated from UI to prevent hangs.
- **Cloud provider:** remote inference only after explicit authorization.
- **Storage:** original assets immutable by default; generated clips versioned; preview proxies discardable.

## 10.4 Render graph

`source asset → optional crop/mask/depth layer → camera/transform animation → overlays/FX → segment encode → transitions/composition → audio mix → final mux → verification`

Cache nodes by content hashes and settings, including worker/encoder version where output changes. Modifying a single shot invalidates that shot and dependent final composition, not independent renders or previously approved AI clips.

## 10.5 Jobs and state machines

**Local render:** `queued → preparing → rendering → validating → completed`; terminal alternate `failed | cancelled`.

**Cloud video:** `draft → quote_ready → approval_required → reserved → submitting → provider_queued → generating → retrieving → validating → ready_for_review → approved`; alternate `rejected | failed | cancelled | expired`.

All transitions are persisted and idempotent where possible. On restart, provider jobs are reconciled using stored provider job IDs rather than blindly resubmitted.

---

# 11. Data model and API contracts

## 11.1 Core entities

| Entity | Key fields |
|---|---|
| Project | id, title, schemaVersion, videoSpec, budgetPolicy, createdAt, updatedAt |
| Asset | id, type, localUri, sha256, metadata, tags, characterId, sourceInfo |
| Character | id, displayName, referenceAssetIds, styleNotes, visualConsistencyNotes |
| Scene | id, projectId, sequence, title, narrationStartMs, narrationEndMs, location, description |
| Shot | id, sceneId, order, startMs, durationMs, animationMode, assetRefs, instructions, renderVersion |
| AnimationConfig | engine, crop, cameraKeyframes, layerKeyframes, transition, effects, seed |
| ProviderProfile | id, model, capabilities, pricingConfigVersion, authRef |
| GenerationJob | id, shotId, requestHash, providerJobId, status, quoteId, version, results |
| BudgetReservation | id, jobId, quoteUsd, heldUsd, lifecycleStatus |
| SpendLedger | id, jobId, estimateUsd, chargedUsd?, source, status, timestamp |
| ExportJob | id, projectRevision, preset, status, artifactUri, diagnostics |

## 11.2 Example scene contract

```json
{
  "schemaVersion": "1.0.0",
  "projectId": "jonah-001",
  "video": { "width": 1920, "height": 1080, "fps": 24 },
  "scene": {
    "id": "scene-07",
    "title": "Jonah Overboard",
    "narration": { "startMs": 315000, "endMs": 323000 },
    "characterIds": ["jonah", "sailor-a", "sailor-b"],
    "shotIds": ["shot-07a", "shot-07b"]
  },
  "shots": [
    {
      "id": "shot-07a",
      "startMs": 315000,
      "durationMs": 5000,
      "mode": "GENERATIVE",
      "sourceAssetIds": ["ship-jpg", "jonah-reference-png"],
      "action": "Two sailors throw Jonah over the railing",
      "mustShow": ["Jonah crosses the railing", "Jonah moves outward and downward"],
      "avoid": ["face replacement", "duplicated limbs"],
      "generation": { "providerProfileId": "video-primary", "quality": "draft" },
      "approval": "pending"
    },
    {
      "id": "shot-07b",
      "startMs": 320000,
      "durationMs": 3000,
      "mode": "CINEMATIC",
      "sourceAssetIds": ["stormy-ocean-png"],
      "camera": {
        "start": { "scale": 1.0, "x": 0.5, "y": 0.5 },
        "end": { "scale": 1.15, "x": 0.48, "y": 0.55 },
        "easing": "easeInOut"
      },
      "approval": "approved"
    }
  ]
}
```

**Validation rules:** All timestamps integer milliseconds; durations positive; no unintentional overlaps or gaps; referenced assets must exist; valid animation engine for asset type; project time bounds explicit; cloud generation requires quote + authorization + reserved funds.

## 11.3 Provider interface (illustrative)

```ts
interface VideoGenerationProvider {
  id: string;
  getCapabilities(): Promise<ProviderCapabilities>;
  quote(input: AnimationRequest): Promise<CostQuote>;
  submit(input: AnimationRequest, approvalId: string): Promise<RemoteJobRef>;
  getStatus(ref: RemoteJobRef): Promise<GenerationStatus>;
  download(ref: RemoteJobRef): Promise<LocalArtifact>;
  cancel?(ref: RemoteJobRef): Promise<CancelResult>;
}
```

**Security:** `approvalId` is created only after explicit UI confirmation and validation against a server-independent local budget ledger. Never embed provider secret material in app-generated scene manifests or exports.

---

# 12. Cost model and production constraints

## 12.1 Monthly envelope

- Output: 2/week × 52/12 ≈ **8.67 videos/month**.
- Total: 8.67 × 15 ≈ **130 finished minutes/month**.
- $50 total incremental cash cap = **~$5.77 per finished video**.
- Stronger operational target: **$30/month** cloud video generation, **$10** other incremental costs, **$10** contingency.

### Illustrative video-generation budget

Assume **9 five-second paid action clips per completed video**, **2 billable attempts per clip**, and an illustrative quote of **$0.10 per clip**:

`8.67 videos × 9 clips × 2 attempts × $0.10 ≈ $15.60/month`.

This creates ~45 seconds of *approved AI action* per 15-minute video, or ~5% of total running time, not counting regenerated discarded footage. Provider duration, billing granularity, retry policy, and available pricing must be checked at time of use; examples are not guaranteed vendor prices.

If provider cost doubles or average attempts increase, the tool must lower allowed clip count or flag the projected budget overrun before scheduling jobs.

## 12.2 The budget is not the total cost of doing business

Excluded from incremental ceiling unless explicitly switched on: existing ChatGPT/Claude subscription fees, device depreciation, electricity, internet, labor, paid sound/music licensing, sales tax, international payment fees, and optional cloud storage. The budget screen must list these exclusions.

## 12.3 Budget allocation design

- Month spending cap and remaining headroom visible in editor.
- Separate **estimated**, **reserved**, **confirmed**, and **unknown/unreconciled** amounts.
- Per project cost estimate from planned generative shots.
- A warning if narrative coverage implies too many paid shots; alternatives highlighted.
- Batch approval can allocate a maximum charge amount, maximum clip count and retry policy.
- Provider quotation freshness/expiration enforced.

---

# 13. Nonfunctional requirements

## 13.1 Performance

- User interface remains responsive while render or network jobs run.
- Import and scene editing work without cloud availability.
- Preview proxies and incremental renders reduce repeated decoding.
- One heavy local export at a time by default; background work concurrency configurable.
- 15-minute timeline supported without loading all full-resolution frames simultaneously.
- Large source media should stream or be processed in chunks where feasible.

## 13.2 Reliability

- Atomic manifest writes, resilient SQLite transactions, durable job queue.
- Restart recovery for queued and provider-running jobs.
- No double-submission after network timeout if provider job can be recovered; otherwise require manual resolution before retry.
- Logs include job IDs, stage, provider response code/error category, no secrets.
- Failed render leaves original assets and last approved project export untouched.

## 13.3 Security and privacy

- Cloud uploads opt-in and per-job; clearly identify affected source images/prompts.
- OS credential storage for API keys; never in renderer logs, plaintext project JSON, or git-tracked config.
- No analytics/telemetry by default in MVP; if later added, opt-in and explain collected data.
- Use sanitized file paths and safe FFmpeg argument arrays; no shell string interpolation.
- Validate uploads/downloads, file types, source URL domains, content length and checksums.
- Avoid automatically sharing protected characters, private narration, or user files beyond the chosen provider.
- Provide **Delete remote artifacts where supported** and document provider retention boundaries; cannot promise provider-side deletion without supporting API.

## 13.4 Portability and maintainability

- Windows 11 x64 first, with explicit macOS support as later milestone.
- Project manifests versioned; migrations tested.
- Provider packages swappable without changing editor data format.
- Media-processing worker pinned versions with reproducible builds.
- No hosted backend required for ordinary project use.

## 13.5 Accessibility and UX

- Keyboard access for major editor controls.
- Readable contrast and non-color-only status markers.
- Tooltips and beginner-friendly defaults.
- Visual loading states, clear errors and recovery actions.
- A novice can create a project and export a test clip from the guided flow without understanding diffusion, GPU memory or FFmpeg syntax.

## 13.6 Legal/creative quality

- Only import media the creator has rights to use; display reminder for copyrighted music/footage.
- Maintain attribution/license metadata for acquired sound/music assets where supplied.
- Preserve original creative decisions and distinct episode storyboards; no guarantee of YouTube monetization or performance.
- Flag AI-generated media in local provenance; creator remains responsible for applicable platform disclosures.
- No automated doctrinal or historical accuracy claims; scripts require editorial review.

---

# 14. Quality assurance and evaluation framework

## 14.1 Automated tests

- Unit: scene schema, time conversion, budget quotes/rounding, media hash, cap enforcement, dependency graph.
- Integration: provider mocked submission/poll/recovery, cancellation, deduplicated retries, cache invalidation, export pipeline.
- End-to-end: import Jonah assets → add scenes → render cinematic clips → approve AI asset → compose → export → validate.
- Fault injection: no network, invalid API key, timeout, price unavailable, disk full, out-of-memory, ffmpeg process crash, app kill mid-render, asset moved/deleted.
- Security: path traversal, malicious media filename, URL injection, secret leakage in logs, unexpected cloud upload.

## 14.2 Creative quality rubric (human-in-the-loop)

Rate each shot on a 1–5 scale:

1. Script/action accuracy.
2. Character continuity and clothing identity.
3. Motion smoothness and temporal coherence.
4. Framing and visual readability.
5. Fit to narration and surrounding shots.
6. Visual variety and emotional impact.

**Approval rule (configurable):** All critical action constraints pass; no severe body/identity artifacts; creator approves before use. Quality score does not automatically authorize billable retries.

## 14.3 Pilot measurement and outcome evidence

Measure across the first **three complete 15-minute episodes**:

- Median editing time per minute of finished video.
- Cloud generation attempts / usable clip.
- Generative seconds / episode.
- Effective cloud cost / usable second and / finished episode.
- Render failure and cache-hit rates.
- Number of shots needing manual correction.
- Export reliability and narration sync defects.
- Creator satisfaction with visual style and workflow.

No automatic claim of meeting twice-weekly throughput or 50% time savings until OG1 baseline and OG3 four-week evidence exist. Use the outcome definitions and formulas in Sections 3.5–3.8; record both first-pass AI acceptance and all-attempt cost, plus reviewer-rated quality and on-time deadlines.

---

# 15. Delivery plan and milestones

Delivery is organized by **exit criteria**, not speculative calendar commitments.

## Milestone 0 — Technical feasibility spike

**Build:** FFmpeg render prototype, a 10–20-shot sample timeline, source image animation, narration mix, one hosted video provider test and cost quote.

**Exit:** One 60–90-second polished Jonah proof-of-concept with reusable assets and measured direct cash cost. Confirm provider duration, billing, input compatibility and generation quality before locking adapter.

## Milestone 1 — Desktop skeleton and local video composition

**Build:** Tauri/React app, SQLite projects, asset ingest, scene editor, basic timeline, FFmpeg render/export, autosave.

**Exit:** User imports 20+ images and a narration track and exports a coherent 3–5-minute piece using no cloud AI.

## Milestone 2 — Narration-driven 15-minute pipeline

**Build:** Scene-plan import, waveform, boundaries, proxies, render cache, timeline gap detection, templates.

**Exit:** 15-minute end-to-end export from imported assets and audio with editable shot timing and stable restart recovery.

## Milestone 3 — Budgeted AI generation

**Build:** Provider adapter, quotes, approval screen, reservations/ledger, async jobs, cancellation, per-shot version approvals and retry policies.

**Exit:** A user generates one difficult Jonah action, approves/rejects it, and proves the app blocks out-of-budget calls and preserves successful shots.

## Milestone 4 — Pilot production hardening

**Build:** Crash handling, progress/error UX, diagnostics, export preflight, basic effects library, packaging and onboarding.

**Exit (technical pilot):** Three complete episodes produced and measured with a documented actual cash budget, creative quality, active creator effort, and operational issues. This establishes technical MVP readiness, **not** proof of O-01 / O-03. Follow with a separate four-week, eight-episode outcome-validation pilot (OG3) and extended O-06 scheduling validation.

## Milestone 5 — Later expansion

Explore optional LLM scene planner, cut-out automation, visual continuity checks, Blender motion control, additional providers, subtitles and advanced project templates only after pilot data supports their value.

---

# 16. Suggested engineering work breakdown

## Epic E1 — Project Foundation
- Initialize Tauri + React + TS app.
- Define SQLite migrations and project manifest schema.
- Implement asset and project repositories.
- Bootstrap Python worker with secure IPC and job supervision.
- Add logging, settings and exception handling.

## Epic E2 — Media Pipeline
- ffprobe metadata extraction.
- Thumbnail and proxy jobs.
- Original media immutability, hash cache and path resolution.
- FFmpeg segment render pipeline, video transitions and audio mix.
- Export verification.

## Epic E3 — Storyboard & Timeline
- Scene-plan import/export validator.
- Storyboard card editor.
- Shot inspector for framing/animation.
- Waveform + narration mapping.
- Timeline tracks, preview and undo/redo (basic first, full later).

## Epic E4 — Animation
- CINEMATIC keyframe presets.
- LAYERED alpha-transform renderer.
- Effect assets for storms/waves/dust/light.
- Per-shot render versioning and dependency caching.

## Epic E5 — Cloud Provider
- Provider contract and one adapter.
- Cost metadata/pricing config and guardrails.
- Upload/submission, async status, result validation.
- Review/approve/reject, safe retry and cancellation.
- Secrets/keychain integration.

## Epic E6 — Budget & Production Dashboard
- Monthly/project budget policy.
- Estimate/reservation/reconciliation ledger.
- Approval dialogues and generation cost preview.
- Project scene coverage and planned generative seconds.
- Pilot metrics reporting.

## Epic E7 — Quality and Release
- Unit/integration/E2E tests.
- Crash/restart and offline tests.
- Windows installer and first-run dependency checks.
- Guided Jonah demo project.
- Documentation, data policy and third-party licenses.

---

# 17. Major risks and mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| AI cannot reliably perform complex multi-character motion | High | Shorter shots, cutaways, reference frames, manual approve and alternative cinematic composition |
| Video clips look inconsistent with illustrations | High | Reference packs, shot style notes, approve/reject, fixed art direction and reuse of approved outputs |
| $50 cap insufficient for chosen visual standard | High | Strict 5% approximate generative coverage target, measured retry rate, cheaper fallback modes, explicit trade-off communicated |
| Provider changes model or pricing | High | Capability/price config, quote expiry, fail-closed charging, adapter interface |
| Full editor scope overwhelms small development team | High | MVP limited to narration, storyboard, cinematic motion, single provider, export |
| 15-minute editor playback becomes slow | Medium | Proxies, lazy loading, segment caching and worker isolation |
| Local FFmpeg packaging/platform issues | Medium | Pinned builds, capability detection, software fallback, first-run checks |
| Broken timing after scene changes | Medium | Millisecond timeline validation, render graph and preflight checks |
| Unexpected billable retries/duplicate jobs | High | Idempotent job IDs, reservations, durable provider job reconciliation, approval on fresh attempt |
| Voice/music licensing issues | Medium | Imported user-supplied audio by default, license metadata, no bundled copyrighted media |
| Laptop overheating or heavy rendering | Medium | Limit local concurrency, use proxies, optional hardware encoder, monitoring |
| Creator workload still too high | High | Track editing minutes, template reuse, refine largest bottleneck using actual pilot metrics |

---

# 18. Open decisions and recommended defaults

| Decision | Recommended default | Validation |
|---|---|---|
| OS | Windows 11 x64 first | Confirm primary development/test laptop |
| App shell | Tauri 2 | Prototype IPC and bundling of worker |
| Backend runtime | Python supervised process | Check packaging/antivirus constraints |
| Project document | JSON manifest + SQLite index | Migration and crash tests |
| Video provider | One hosted image-to-video model via adapter | Benchmark Jonah shots and current provider pricing |
| Editing features | Targeted scene editor, not full NLE | User pilot productivity |
| Narration | User-supplied WAV/MP3 | Verify real production workflow |
| FPS | 24 by default; 30 optional | Test final YouTube edit needs |
| Output | 1080p MP4 H.264/AAC | Export compatibility checks |
| Monthly cap | $50 incremental USD | Confirm whether subscription costs are excluded |
| Approval | Manual before each billable job or explicitly capped batch | UX pilot |
| Initial AI footage | Up to ~45 seconds per 15-minute episode at plan target | Quality and budget pilot |
| Distribution | Local installer, no accounts | Assess update mechanism later |

---

# 19. Definition of done

The MVP is considered **usable** when a solo creator can:

- start an offline project and import a script, narration track and visual assets;
- build and modify a narration-aligned storyboard;
- animate static images with pans/zooms and selected layered effects;
- selectively submit a short clip to one hosted model after seeing the price and authorizing the charge;
- cancel, reject, replace, or approve an individual generated shot without redoing others;
- view planned/actual spend and operate within a $50 per-month configured app budget;
- preview the project and export a valid full-length 1080p MP4;
- close/reopen the project without losing decisions, source links or completed renders;
- produce the Jonah pilot as a full 15-minute episode using mostly locally rendered cinematic illustration shots.

**Technical readiness is necessary but not sufficient for proven product success.** Full product outcome validation additionally requires the approved manual baseline, observed creator time reduction, four-week production cadence, demonstrated cost ceiling, and creative-quality evidence (Sections 3.4–3.8; companion quality gates OG1–OG3). Feature count and passing unit tests are not proxies for those outcomes.

---

# 20. Immediate implementation checklist

1. Create repo with `apps/desktop`, `workers/media`, `packages/contracts`, `tests/fixtures`.
2. Pin project JSON schema and shot/asset/job contracts before building UI.
3. Implement asset import, ffprobe and image-to-video *local cinematic motion* proof of concept.
4. Build the Jonah 60–90-second vertical slice with narration, 8–15 shots and one optional paid AI action shot.
5. Record real-generation cost and approval flow before choosing provider.
6. Add SQLite, resumable queue and cost ledger as first-class components—not late add-ons.
7. Implement full narration timeline and 15-minute exporter.
8. Validate the three-episode technical pilot, then complete OG1 baseline + OG2 value comparison + OG3 four-week/eight-episode outcome pilot before claiming the north-star outcome or prioritizing costly P1 expansion.

---

# Appendix A — Example production recipe (15-minute episode)

This is an **illustrative allocation**; the creator may vary it per story:

| Technique | Runtime target | Rendering cost pattern |
|---|---:|---|
| Cinematic stills and reframing | 8m 15s (55%) | Local compute only |
| Layered motion and reusable effects | 4m 30s (30%) | Local compute only |
| Cloud AI action clips | 0m 45s (5%) | Pay per generation, retries counted |
| Atmosphere, text, cutaways and other sequences | 1m 30s (10%) | Mostly local compute |
| **Total** | **15 minutes** | **Mixed** |

The percentages should not create four isolated chunks; interleave techniques across the narration for visual variety. Use scene-specific art direction and sound to maintain interest. All audio/music must be appropriately licensed or original.

# Appendix B — Illustrative prompt used outside the app

For a paid ChatGPT/Claude chat workflow, the user can request structured scene data:

```text
You are the storyboard planner for an animated Bible-story video.
Given the script and narration timestamps I provide, return valid JSON only.
For each scene, include an ID, narration start/end in milliseconds, purpose,
visual description, named existing character assets, 1–3 short shots, and
recommended animation mode: CINEMATIC, LAYERED or GENERATIVE.

Use GENERATIVE only for actions that cannot be communicated convincingly by
camera motion, layer transforms, environment effects or editorial cutaways.
Prefer reusable characters, environments and camera presets. Do not assume
that a flattened image can be fully rigged. Return any missing visuals as
asset requests rather than inventing that they already exist.

Narration timing must add up, with no unintended gaps or overlaps.
Preserve biblical facts and distinguish interpretation from source text.
Do not invent words said by characters unless marked as dramatization.
```

# Appendix C — Suggested repository organization

```text
storymotion/
├── apps/
│   └── desktop/
│       ├── src/                       # React/editor UI
│       └── src-tauri/                 # Tauri shell, permissions, IPC
├── workers/
│   └── media/
│       ├── assets/                    # Probing, proxies, thumbnails
│       ├── storyboard/                # Validation and planning
│       ├── animation/                 # Cinematic and layered renderers
│       ├── providers/                 # Cloud generation adapter(s)
│       ├── budget/                    # Quotes/reservations/ledger
│       ├── render/                    # FFmpeg render DAG
│       └── jobs/                      # Durable state machine
├── packages/
│   └── contracts/                     # Shared JSON schemas/types
├── tests/
│   ├── fixtures/jonah/               # Licensed sample assets
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docs/
│   ├── architecture/
│   ├── api/
│   └── operations/
└── README.md
```

# Appendix D — Recommended architecture decision records (ADRs)

- ADR-001: Why local-first Tauri desktop over always-on web service.
- ADR-002: Why narration master track over fixed-duration clip assembly.
- ADR-003: Why deterministic cinematic motion before generative video.
- ADR-004: Why provider-neutral video generation and explicit cost approval.
- ADR-005: Why FFmpeg segment cache and dependency graph.
- ADR-006: Why SQLite for local jobs and budget ledger.
- ADR-007: Why full automated character rigging is deferred.

**End of PRD.**

# Appendix E — Outcome evidence ledger (required pilot template)

For each baseline/Studio episode, record: `episode_id`, `workflow` (`manual` / `storymotion`), `script_complexity`, `shot_count`, `source_asset_count`, `narration_duration_s`, `planned_due_at`, `approved_at`, `approved_export_sha256`, `active_creator_minutes_by_stage`, `wall_clock_minutes`, `provider_queue_minutes`, `cloud_jobs`, `first_attempt_usable_count`, `first_attempt_total_count`, `accepted_generated_seconds`, `paid_attempts`, `confirmed_cash_spend_usd_by_category`, `calendar_month`, `reviewer_ids`, `six_creative_scores`, `critical_defects`, `rework_minutes`, `quality_gate_result`, `notes_on_confounders`.

A **single JSON/CSV export and evidence folder** must allow another reviewer to independently recompute the outcome metrics. Avoid storing secrets, complete payment details or unnecessary personal data in the ledger.

## Change log

- **v1.1 (2026-11-14):** Added O-01–O-07, outcome hierarchy, explicit manual baseline/50% time study, first-pass 70% clip quality target, ≥4/5 creative score, four-week/eight-video validation, ≥20-release reliability extension, traceability from features to outcomes and distinct technical vs outcome validation states. Existing P0 functional obligations retained.
