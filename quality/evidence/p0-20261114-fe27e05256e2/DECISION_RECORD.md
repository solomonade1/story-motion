# Decision record — Phase 0 (G0 + G1) — build `p0-20261114-fe27e05256e2`

Date: 2026-11-14 · Evidence location: `quality/evidence/p0-20261114-fe27e05256e2/` · Approver: **project owner** (decisions below were made through
the owner's written instructions in this session; the agent recorded them and cannot approve gates itself).

## Basis: the owner's own words (verbatim, this session)
1. On the Phase 0 (Jonah) clip: "The video play fine, the transition also works good but need adjustment. The animation still need refinement. The images use are not real but generated 2D images, I will be providing 3D images that need properly animation…"
2. "I have updated the quality gate." (Quality Gates v1.2) · "the evidence owner is the editor." · "I will look for cloud base when we will need it."
3. On the Hezekiah cut: "The story does make sense with piper joe smooth dissolve with the best flow for me."
4. "Review our output and pass the stage we need to pass."

## DR-001 — Scope extension beyond Phase 0 (owner-requested)
The mini-gate (QG §7.1) says "no unapproved work from later phases". At the owner's request the following later-phase items were built:
`RENDERED` shots (creator/Blender clips), clip `speed`/`trimStartMs`, `scan` and plan-to-manifest `build`, Piper/SAPI narration builder,
audio bed mixing with ducking and a clipping check (FR-AUDIO-002/-003/-004 slices), a synthesised ambience bed. **Status: owner-authorised; recorded here.**
They are tested but only partially trace to P0 rows (see REQUIREMENTS_TRACEABILITY.md) and are not part of the G1 claim.

## DR-002 — G0 baseline decisions
| Item | Decision |
|---|---|
| [QA proposal] thresholds and [Outcome proposal] targets | **Approved as written in Quality Gates v1.2**, unchanged. Later changes need a dated change record (QG §6.2 rule 6); relaxed criteria are never applied retroactively to failed runs |
| Release / gate approval authority | **Project owner** |
| Evidence owner (all P0 rows) | **The editor** (owner's statement) |
| Severity definitions | QG §2.3 (S0–S3) |
| Incident response (agent-executable) | S0/S1: stop the affected work, record the defect in IMPLEMENTATION_STATUS, fix the smallest cause, add a regression test, re-run the affected gate and dependants, record the result. S0/S1 = NO-GO until closed |
| Versioned artifacts | scene schema 1.1.0 (1.0.x readable) · `docs/BUDGET_POLICY.md` 0.1.0 · `docs/PROJECT_LAYOUT.md` 1.0.0-phase0 · `PROCESSOR_VERSION` phase0-1 |
> The agent drafted the incident-response and role wording from the Quality Gates; the owner can amend it by change record.

## DR-003 — What counts as G1 evidence
- **Technical feasibility artifact:** the 85.6 s, 13-shot Jonah slice (placeholder art, synthetic voice) — it meets the G1 technical criteria.
- **Creator narrative approval:** the real-asset Hezekiah cut (34.2 s, owner-supplied clips, Piper voice, ambient bed) — approved by the owner for story and flow (quote 3).
- G1 is therefore passed with **limited scope**. Passing G1 does **not** authorise an assertion about the full 15-minute workflow (QG §2.2).

## DR-004 — Exceptions accepted with this pass
| # | Exception | Consequence |
|---|---|---|
| E-1 | The Hezekiah clips' generating tool and licence are **unverified**; the Windows SAPI voice licence is unverified | These media are **for private review only** until the owner records the tool and terms. Piper `en_US-joe-medium` is CC0 (verified from its MODEL_CARD) |
| E-2 | PRD M0 asks to confirm provider duration/billing/input compatibility; **no live provider was tested** (owner deferred; QG G1 says "if used") | All provider behaviour is MOCK and tagged unverified; the confirmation is carried to Phase 4 as a dependency; the measured direct cash cost is **$0** |
| E-3 | No git repository: evidence is stamped with a source-tree hash instead of a commit | `git init` + commit recommended before Phase 1 |
| E-4 | Owner feedback "transitions need adjustment / animation needs refinement / real 3D assets pending" | Recorded as follow-up work for Phase 2; not a G1 blocker per owner's later approval of the Hezekiah flow |
