# ADR-0002 — Narration is the master clock; integer ms; frame quantisation

- **Status:** Accepted. **Source:** PRD §3.3, §11.2; QG TIME-02/04/05, OPS-02.

## Decision
1. Manifest times are **integer milliseconds** (strict ints; `1000.5` is rejected).
2. Shots must be contiguous (no gaps/overlaps) from 0 and end within **250 ms** of the narration length
   (QG OPS-02 tolerance, a *[QA proposal]* pending owner approval).
3. At render time each boundary is quantised **once** to a frame index with integer maths
   `(ms*fps+500)//1000`; all later steps use whole frames. Max cut error is therefore at most half a frame
   (20.8 ms at 24 fps) and is reported as `max_cut_quantisation_error_ms`.
4. A shot's encoded segment is `body + tail` frames; `tail` is extra footage consumed by an *outgoing*
   transition so the transition **onset** equals the next shot's start frame.
5. The declared narration length is checked against the actual audio (ffprobe) with a 50 ms tolerance.

## Consequence
Cut positions never drift cumulatively (no per-shot float accumulation). A/V sync over a 15-minute export is
**not** proven here (Phase 3, TIME-05).

## Rejected
Fixed 5-second shots; float seconds in the contract; deriving timing from video length.
