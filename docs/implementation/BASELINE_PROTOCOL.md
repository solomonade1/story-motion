# OG1 Baseline Protocol — manual ~15-minute episode

**Status:** protocol defined (Phase 0). **OG1 is NOT VALIDATED**: no manual baseline episode exists yet, and this
document does not claim one. Source: PRD §3.6, §14.2–14.3; Quality Gates §6.2 (OG1, measurement rules).

## Purpose
Establish how much *active creator time* and *incremental cash* one finished minute costs with the creator's
**current manual workflow**, so that O-03 (≥50% less hands-on time) can later be computed honestly. Until this is
done, O-03 is NOT VALIDATED regardless of how fast StoryMotion feels.

## Who / what
- **Creator** performs the episode with their usual tools (no StoryMotion automation). Existing ChatGPT/Claude
  subscriptions may be used, as in the Studio condition.
- **Evidence owner (named before starting):** ______ . **Second reviewer for scoring (recommended):** ______ .
- Use a **real** ~15-minute Bible-story episode (script, narration, illustrations the creator already intends to
  publish). Prefer ≥2 baseline episodes; one is the minimum.

## Steps
1. **Freeze the inputs** in `baseline_manifest.json` (template below): script word count, approximate shot count,
   narration length, number/type of supplied illustrations, how many are reused vs new, intended quality rubric,
   starting-state assumptions (what already existed before the clock started).
2. **Pre-declare** the due date/time for the episode (needed later for O-06 on-time logic).
3. **Time-log while working.** Use `time_logs.csv`. One row per work block. Record **active minutes** (hands on
   keyboard/mouse, thinking about the video, reviewing, fixing) separately from **elapsed wall-clock minutes**
   and **waiting/queue minutes** (e.g. renders, AI generation queues). Never substitute one for another.
   Stages: `storyboarding`, `media_prep`, `visual_motion`, `clip_generation_oversight`, `editing`, `review`,
   `correction`, `export_troubleshooting`, `other` (explain).
4. **Keep receipts** for every incremental cash cost (`cash_ledger.csv`), with invoice/receipt file references.
   Exclude only what the PRD excludes (existing subscriptions, hardware, electricity, internet, labour).
   Record any excluded task or cost explicitly with a reason.
5. **Record outcomes** in `episode_outcomes.csv`: final duration, revisions, accepted clips, failed exports.
6. **Score creative quality** in `creative_reviews.csv` using the six PRD §14.2 dimensions (1–5 each):
   action accuracy; character continuity; motion smoothness; framing; fit to narration; variety/emotional impact.
   Note any **critical story contradiction** (automatic fail). Prefer two reviewers; say if only one.
7. **Owner signs** the baseline (`baseline_manifest.json` → `signedBy`, `signedAt`) before any Studio comparison.

## Statistic (fixed in advance)
`rate = active creator minutes / approved final episode minutes`, per episode.
`Improvement = 1 − median(Studio rates) / median(Manual rates)`. Negative means regression. With a single
baseline episode, report the sample size and flag the uncertainty; do not call it statistically conclusive.

## Comparability rules (prevent incomparable samples)
- Similar script complexity and shot count (record both; explain material differences).
- Same asset availability at start; same quality rubric; same definition of "done" (creator-approved export).
- Log prompt-writing, asset sourcing and human intervention **equally** in both conditions.
- No rewriting the denominator afterwards: keep rejected attempts, rework and partial episodes in the log.
- A baseline without logs, receipts or owner signature is **NOT VALIDATED**, not "close enough".

## Templates
Empty CSVs with headers only: `docs/implementation/templates/`
`time_logs.csv`, `cash_ledger.csv`, `creative_reviews.csv`, `episode_outcomes.csv`, plus (used from the Studio
phases) `ai_generation_attempts.csv`, `release_schedule.csv`, and `baseline_manifest.template.json`.
These are **empty on purpose**; Phase 0 contains no human-measured data.
