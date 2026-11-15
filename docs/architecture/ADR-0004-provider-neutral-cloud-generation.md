# ADR-0004 — Provider-neutral cloud generation behind an approval gate

- **Status:** Accepted (interface + fake provider only). **Source:** PRD §11.3, FR-AI-001..005, FR-BUD-*; QG COST-*.

## Decision
`providers/base.py` defines vendor-neutral types (`ProviderCapabilities`, `AnimationRequest`, `CostQuote`,
`Approval`, `RemoteJobRef`, `GenerationStatus`, `LocalArtifact`) and the `VideoGenerationProvider` protocol
(`get_capabilities / quote / submit(approval) / lookup_by_approval / get_status / download / cancel`).

- The manifest stores only `providerProfileId` and a *downloaded clip asset*. No provider fields or secrets can
  enter it (`extra="forbid"`; test `test_secrets_or_provider_fields_cannot_enter_manifest`).
- Rendering **never** calls a provider. A GENERATIVE shot renders its approved clip or its declared local
  fallback, and the fallback is reported (ANIM-03).
- Money is integer **micro-USD**. Unknown price ⇒ `PricingUnavailable` (fail closed).
- `create_approval` requires explicit confirmation. A submission needs a matching, unexpired quote and approval.
- Idempotency key = approval id: same approval ⇒ same job, one charge; a creative retry needs a **new** approval.
- Client policy (`providers/flow.py`): bounded transport retries only for errors proving non-acceptance
  (429/outage); a submit timeout triggers lookup-by-approval, else `AmbiguousSubmission` and **no** resubmit.
- Downloads are verified (provider checksum, ffprobe decode, resolution, duration) before use.

## What this does NOT prove
`FakeVideoProvider` prices and limits are invented MOCK values. Nothing here validates a real provider's pricing,
billing, quality or API. The real adapter, secrets storage and reservation ledger are Phase 4; the live
feasibility test is blocked pending owner authorisation (see `PROVIDER_FEASIBILITY_CHECKLIST.md`).
