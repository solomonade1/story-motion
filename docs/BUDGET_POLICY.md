# Budget policy — v0.1.0 (baseline for G0; enforced in code from Phase 4)

**Status:** policy baseline only. **Nothing here is implemented as a ledger yet** (ADR-0006, Phase 4). Phase 0 enforces only
the approval gate and fail-closed pricing on the *fake* provider. Source: PRD §7.7 (FR-BUD-001..008), §12; Quality Gates §4.4.

| Rule | Value / behaviour |
|---|---|
| Monthly hard cap | **US$50** incremental cash (PRD default; configurable). Excludes existing subscriptions, hardware, electricity, internet, labour |
| Other caps | per-project and per-provider caps are configurable; none are set yet |
| Currency / arithmetic | USD baseline; **integer micro-USD**, never binary floats |
| Submission test | allowed only if `spent + active reservations + new quote <= cap` (**equality allowed**, +US$0.01 blocked) |
| Unknown / stale / ambiguous price | **fail closed**: no upload, no submission |
| Approval | explicit user confirmation before **every** billable attempt, or a user-defined approved batch envelope. A retry after a failed or rejected result is a **new** attempt needing a new approval |
| Transport retry | only for errors that prove non-acceptance (429/outage), bounded (2), same approval, same job. Submit timeout ⇒ reconcile by job id, **never** blind resubmit |
| Quote TTL | **not set for any real provider** (none authorised). The fake provider uses 300 s as a MOCK value. A real TTL is set from the provider's published terms in Phase 4 |
| Warnings | at 50 %, 75 %, 90 %, 100 % of the cap |
| Live provider | **none authorised.** Owner (2026-11-14): "I will look for cloud base when we will need it." Any live request needs written authorisation, a current quote and a hard cap (see `implementation/PROVIDER_FEASIBILITY_CHECKLIST.md`) |
| Limitation | the cap is an *application-enforced authorisation cap*, not a guarantee about provider invoices; actual charges must be reconciled where the provider exposes them |

Changes to this policy require a dated decision record (see `quality/evidence/<build-id>/DECISION_RECORD.md`).
