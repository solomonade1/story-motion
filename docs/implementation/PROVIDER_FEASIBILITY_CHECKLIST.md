# Live provider feasibility — quote/approval checklist and benchmark worksheet

**Status:** PREPARED, NOT EXECUTED. No live provider was contacted in Phase 0. No quote, price, duration limit or
model name below is verified; every blank must be filled from the provider's **currently published** documentation
and terms at test time. Source: Charter B3/B4, Phase 0 prompt, QG G1 ("provider test, if used"), COST-*.

## A. Owner authorisation (all required before ANY billable or uploading request)
| Item | Value (owner fills in) |
|---|---|
| Provider and exact model/endpoint (from current docs) | |
| Docs / pricing / terms URLs and the date they were read | |
| Quote (provider's own unit, rounding, minimum billable) | |
| Maximum committed spend for this test (USD) | |
| Exact assets to upload (file names + SHA-256) and prompt text | |
| Provider data-retention / training / deletion terms accepted? | |
| Cancellation supported? Does a cancelled job still bill? | |
| Provider-side spending alert/limit configured? | |
| Credential storage method (OS credential store; never in repo/UI) | |
| Owner approval (name, date, written in chat) | |

If any row is blank, **stop**. A local in-app cap is an authorisation cap, not a guarantee about the provider's invoice.

## B. Pre-flight (agent, no network)
- [ ] Capabilities from docs entered in a versioned local config (`pricing_config_version` set; `pricing_verified=true` only after checking the provider's published price).
- [ ] Request validated locally: formats, duration, resolution, image count, prompt length.
- [ ] Quote computed with provider rounding/minimums; shown to the owner with destination, assets and prompt.
- [ ] Approval created only after the owner's explicit yes; max = quote.
- [ ] Mock run of the same request passes (`storymotion_media.providers.fake`).

## C. Predeclared Bible-shot sample (PRD §8.4, QG FX-04)
| # | Shot | Must show | Eligible for O-04? |
|---|---|---|---|
| a | camera / simple movement | | |
| b | walking / gesture | | |
| c | multi-character physical interaction | | |
| d | Jonah thrown overboard by sailors | Jonah crosses railing, moves outward and downward; not a voluntary jump | |
| e | great fish emerges / swallows | | |

## D. Worksheet (one row per paid attempt — never pre-fill with estimates)
`shot, exact prompt, source asset + license, model/version, request settings, provider job id, queue time,
output metadata (duration/resolution), first-attempt accepted?, action accuracy 1–5, identity consistency 1–5,
artifacts, billed amount (from invoice/usage), effective cost per accepted second`.
Use `templates/ai_generation_attempts.csv`. Mark simulated rows `mock=true`.

## E. Stop conditions
Unknown/stale price · ambiguous billing · missing credentials or offline · quote above the owner's maximum ·
timeout after acceptance (reconcile by job id; **no blind resubmit**) · any request that was not explicitly approved.
