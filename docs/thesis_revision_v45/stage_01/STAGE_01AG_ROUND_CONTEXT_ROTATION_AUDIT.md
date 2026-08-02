# Stage 1AG — Round-Context Rotation Audit (correction AG5)

## Introduction

This audit verifies correction **AG5** (dynamic per-dispatch round context) against the FINAL normative tree in
`STAGE_01_PROTOCOL_PSEUDOCODE.md`. The algorithm is **PoCol**; the mechanism under audit is the idle policy within PoCol.
The A1 baseline (`8.420833333 kWh`) is preserved — AG5 is a documentation-only control-flow lock (no executable source,
configuration, or experiment was touched), so no energy figure is recomputed or altered.

AG5 requires that neither the run-level driver (`RunEventLoopToHorizon`) nor the event-loop driver (`ProcessEventTime`)
ever retains a `RoundContext` argument across a round rotation. The single owned run state
`RunContext.current_round_context` is the authority; every consumer re-resolves `RoundContext <-
RunContext.current_round_context` at its point of use. A round rotation (a terminal round closing and the next
`RoundInitialiseEvent` publishing a fresh context) is therefore observed immediately by the next dispatch, and a
required-but-null `RoundContext` is a structured `dispatch_context_unavailable` rather than a handler call on a null
context.

All line anchors below are into `STAGE_01_PROTOCOL_PSEUDOCODE.md` unless stated otherwise.

## Per-item verdicts

### Item 1 — `ProcessEventTime` retains no stale `RoundContext`; it resolves per dispatch AND once for the horizon-closure/epilogue tail

- `PROCEDURE ProcessEventTime` declares `INPUTS: RunContext, event_time t, is_horizon = ..., allow_empty_horizon =
  false, RunHookContext = null` — there is **no** `RoundContext` input parameter (L252–L254).
- The signature comment states it "receives the RUN context (NOT a RoundContext)" and that "the CURRENT RoundContext is
  re-resolved per dispatch as `RoundContext <- RunContext.current_round_context`" (L255–L258); the EFFECTS preamble
  repeats that "there is NO retained RoundContext argument ... re-resolved from `RunContext.current_round_context` at each
  dispatch (below) and at the epilogue tail" (L272–L274).
- **Per dispatch:** inside the pop-before-dispatch loop, `SET dispatch_round_context <- RunContext.current_round_context`
  (L303), and that freshly resolved value — never a retained argument — is the one threaded into the invocation builder at
  `CALL BuildHandlerInvocation(d, record, dispatch_round_context, RunContext, ctx)` (L324).
- **Once for the tail:** after the drain loop, `SET RoundContext <- RunContext.current_round_context` (L343) resolves the
  current round exactly once for the horizon-closure block and the event-time epilogue tail.

**Verdict: PASS.**

### Item 2 — a required-but-null `RoundContext` records `dispatch_context_unavailable` and does NOT call the handler (CONSUMEs + clears)

- The guard is checked before `BuildHandlerInvocation` / the handler call: `IF (RoundContext in d.runtime_injected) AND
  dispatch_round_context = null:` (L316), with the intent comment at L313–L315 ("do NOT call the handler ... record the
  structured `dispatch_context_unavailable`, CONSUME, and re-POP").
- On the guarded branch it records the structured result `RECORD dispatch_context_unavailable(record.event_type, er)`
  ("AG5: structured; handler never called", L317), then ATOMICALLY sets `queue_status <- CONSUMED` and CLEARs every
  `EQ.current_*` field (L318–L320), then `CONTINUE` re-POPs the next queued event (L321) — the handler is never invoked.
- The guard is scoped to descriptors that actually require the context (`RoundContext in d.runtime_injected`), so
  `RoundInitialiseEvent`, whose runtime injection is `RunContext` (not `RoundContext`) per the handler-inputs ground truth
  `{ RunContext, round_setup_seq }` (L1066) and the injection switch "CASE RunContext ... RoundInitialiseEvent only"
  (L228), is never blocked here.

**Verdict: PASS.**

### Item 3 — after `RoundInitialiseEvent` publishes a new `current_round_context`, every subsequent event resolves and receives the NEW context

- The `RoundInitialiseEvent` handler publishes the new context: `SET RunContext.current_round_context <- rc` with the
  in-line note "publish the new RoundContext (step 2) — every subsequent event resolves it" (L1118).
- Because each dispatch re-resolves `dispatch_round_context <- RunContext.current_round_context` (L303) immediately before
  building the invocation (L324), the very next dispatched event reads the newly published `rc`; the signature comment
  confirms "a round rotation is picked up immediately (no retained/stale RoundContext)" (L256–L257).
- Rotation continuity: the single terminal-round closure owner sets `RunContext.prior_round_terminal_state <-
  RunContext.current_round_context` (L6096) and seats the next bootstrap `CALL SeatNextRoundBootstrap(RunContext)`
  (L6102); that next `RoundInitialiseEvent` again republishes a fresh `current_round_context` (L1118), so no event
  dispatched after a rotation can receive the prior round's context.
- Confirmed by the normative semantic vector TV292 ("AG5 current round context after rotation") in
  `STAGE_01AG_SEMANTIC_TEST_VECTORS.md` (L61–L66): a `TemplateCommitEvent` dispatched after publication resolves
  `dispatch_round_context = RunContext.current_round_context = rc` (the NEW round), "NOT a null/placeholder/previous
  context".

**Verdict: PASS.**

### Item 4 — `RunEventLoopToHorizon` resolves `RoundContext <- RunContext.current_round_context` before `FinalizeSimulationRun` (no retained arg)

- `PROCEDURE RunEventLoopToHorizon` declares `INPUTS: RunContext` only (L474–L475), with the comment "the run driver holds
  ONLY the RunContext. It never retains a RoundContext argument; every RoundContext is resolved from
  `RunContext.current_round_context` at the point of use" (L476–L477).
- Immediately before the run-level finaliser: `SET RoundContext <- RunContext.current_round_context` ("AG5: resolve the
  current (now terminal) round — never a retained arg", L504), followed by `CALL FinalizeSimulationRun(RunContext,
  RoundContext)` (L505). The value passed is the freshly resolved current round, not an argument carried from an earlier
  round.

**Verdict: PASS.**

### Item 5 — the horizon-closure block (`CloseRoundAtHorizon` + epilogue-tail calls) uses the resolved current `RoundContext`

- The single tail resolution `SET RoundContext <- RunContext.current_round_context` (L343) is the value consumed by the
  entire horizon-closure/epilogue block.
- Horizon close: `IF is_horizon AND round_state NOT in {ROUND_ACCEPTED, ROUND_ABORTED}: CALL
  CloseRoundAtHorizon(RoundContext, RunHookContext)` (L350–L351) — passes the resolved current `RoundContext`.
- Epilogue tail: every canonical tail call takes the same resolved `RoundContext` —
  `FinalizeEventTimeSecurityCensus(RoundContext, t)` (L382), `ApplyRecoveryCompletionAfterEpilogue(RoundContext, t)`
  (L383), `ApplyRecoveryAssignmentContinuationAfterEpilogue(RoundContext, t)` (L384),
  `ApplyRecoveryWorkAfterEpilogue(RoundContext, t)` (L385), and `FinalizePostRecoveryApplicationState(RoundContext, t)`
  (L386).
- `CloseRoundAtHorizon` itself takes `INPUTS: RoundContext, RunHookContext` (L6490) and drives the terminal transition
  through that context, consistent with the resolved-current-round contract.

**Verdict: PASS.**

## Summary

| # | AG5 requirement | Line anchors (`STAGE_01_PROTOCOL_PSEUDOCODE.md`) | Verdict |
|---|-----------------|--------------------------------------------------|---------|
| 1 | `ProcessEventTime` retains no stale `RoundContext`; resolves per dispatch AND once for the horizon-closure/epilogue tail | L252–L254 (no `RoundContext` input); L255–L258, L272–L274 (contract); L303, L324 (per dispatch); L343 (tail, once) | PASS |
| 2 | Required-but-null `RoundContext` -> structured `dispatch_context_unavailable`, handler not called, CONSUME + clear | L313–L315 (intent); L316 (guard); L317 (record); L318–L320 (CONSUME + clear `EQ.current_*`); L321 (CONTINUE) | PASS |
| 3 | After `RoundInitialiseEvent` publishes the new context, every subsequent event resolves/receives the NEW context (none gets the prior round's) | L1118 (publish); L303 (per-dispatch resolve); L256–L257 (immediate pickup); L228/L1066 (bootstrap injects `RunContext`); L6096, L6102 (rotation); TV292 in `STAGE_01AG_SEMANTIC_TEST_VECTORS.md` L61–L66 | PASS |
| 4 | `RunEventLoopToHorizon` resolves `RoundContext <- RunContext.current_round_context` before `FinalizeSimulationRun` (no retained arg) | L474–L477 (`RunContext`-only input); L504 (resolve); L505 (call) | PASS |
| 5 | Horizon-closure block (`CloseRoundAtHorizon` + epilogue tail) uses the resolved current `RoundContext` | L343 (resolve once); L350–L351 (`CloseRoundAtHorizon`); L382–L386 (epilogue tail); L6490 (`CloseRoundAtHorizon` INPUTS) | PASS |

## Overall verdict

**PASS.** All five AG5 obligations are satisfied by the FINAL normative tree. `ProcessEventTime` and
`RunEventLoopToHorizon` each hold only `RunContext` and re-resolve `RoundContext <- RunContext.current_round_context` at
every point of use — per dispatch, once for the horizon-closure/epilogue tail, and once before `FinalizeSimulationRun`.
A required-but-null `RoundContext` is a structured `dispatch_context_unavailable` that CONSUMEs the event and never calls
the handler, and a newly published `current_round_context` is observed by the next dispatch, so no post-rotation event
receives a stale round's context. No defect found. PoCol and the A1 baseline (`8.420833333 kWh`) are unaffected.
