# ADR-0006 — SQLite budget ledger (design only; implemented in Phase 4)

- **Status:** Proposed. **Source:** FR-BUD-001..008; QG COST-03/04/08, F-05, F-15.

## Design
SQLite (WAL) tables: `quotes`, `approvals`, `reservations`, `spend_ledger`, `provider_profiles`. Money columns are
integer micro-USD. A reservation is one `BEGIN IMMEDIATE` transaction that checks
`spent + active_reservations + new_quote <= cap` (equality allowed) and inserts the hold, so concurrent
requests serialise at the database (COST-04: 100 deterministic race runs). On restart, open reservations are
reloaded and reconciled using stored provider job ids (F-15). The cap is an *application-enforced
authorisation cap*, not a guarantee about provider invoices (QG §4.4).

## Phase 0 status
Not implemented. Phase 0 only supplies integer-micro-USD quotes and the approval gate on the fake provider.
