# Stage 1U — Post-Epilogue Context-Threading Audit (U2)

**Consensus mechanism.** This audit concerns the consensus specification named **PoCol**. Within PoCol,
**the idle policy within PoCol** is referenced solely as a mechanism; no property of the consensus
mechanism is claimed here. This is documentation only, describing the frozen behaviour of
`STAGE_01_PROTOCOL_PSEUDOCODE.md`; it neither adds a consensus feature nor amends any procedure beyond the
already-frozen U2 text it audits. The A1 accepted baseline of **8.420833333 kWh** is UNCHANGED and is
restated only for provenance: **U2 is a scheduling-provenance / causality correction** — it makes the
SOURCE of every post-epilogue wake explicit and threads it, unbroken, to the sole enqueue interface. It
counts time no differently and prices energy no differently: it moves no residency boundary, re-times no
`WAKING`/`ACTIVE_HASHING` interval, and re-prices nothing. Any energy difference remains attributable
**only to reduced active power-time** (fewer / shorter `ACTIVE_HASHING` residency intervals), exactly as
`ApplyMinerStateTransition`'s `residency_ledger` measured before.

**Scope — Stage-1U correction U2 (thread `PostEpilogueSchedulingContext` through the full wake path).**
Stage 1S (S7) made a post-epilogue `ScheduleEvent` call carry an explicit `PostEpilogueSchedulingContext`
and enforced a strictly-later target at the enqueue interface. U2 closes the remaining gap: it makes the
scheduling source an EXPLICIT tagged input, `SchedulingSourceContext`, on every procedure on the wake path —
`ReserveActivate`, `RangeReassign`, `RangeAssign`, `StartWake`, and `CommitRecoveryAssignmentPlan` — so a
post-epilogue caller threads its `pctx` all the way from the `ProcessEventTime` tail down to `ScheduleEvent`
without ever falling back to the drained dispatch envelope. Grounded in **§0.8** (`SchedulingSourceContext`),
the five procedure signatures (`PROCEDURE StartWake`, `PROCEDURE ReserveActivate`, `PROCEDURE RangeAssign`,
`PROCEDURE RangeReassign`, `PROCEDURE CommitRecoveryAssignmentPlan`), and the `ProcessEventTime` tail
(`ApplyRecoveryWorkAfterEpilogue`, `ApplyRecoveryAssignmentContinuationAfterEpilogue`).

## 1. `SchedulingSourceContext` — the explicit tagged input (§0.8)

§0.8 declares the tagged union that names WHERE a wake is being scheduled from:

```
  # SchedulingSourceContext in { ORDINARY_DISPATCH(dispatch_envelope), POST_EPILOGUE(PostEpilogueSchedulingContext) }
  #   ReserveActivate / RangeReassign / RangeAssign / StartWake / CommitRecoveryAssignmentPlan take an explicit
  #   scheduling_context of this type; a POST_EPILOGUE caller threads its PostEpilogueSchedulingContext all the way to
  #   ScheduleEvent ...
```

Two arms, exactly. `ORDINARY_DISPATCH(dispatch_envelope)` is the live-dispatch source (a handler dispatched
by `ProcessEventTime`, or a sim-driver entry with its `DriverEventEnvelope`); `POST_EPILOGUE(PostEpilogueSchedulingContext)`
is the post-drain source, carrying the `pctx` whose fields (`source_event_time`, `source_envelope`,
`EventQueueContext`, `RunContext`) were fixed by S7 (§0.7e). The `scheduling_context` is not an ambient or
inferred value: it is a declared INPUT parameter of each of the five procedures, so the source travels as
data, not as an assumption. A dispatched handler that threads a bare `dispatch_envelope = e` is read as
`scheduling_context = ORDINARY_DISPATCH(e)` (StartWake's own note), so the two spellings are equivalent for
ordinary callers; a post-epilogue caller MUST pass `POST_EPILOGUE(pctx)` explicitly.

## 2. The five procedures now take `scheduling_context` — PASS-check table

Every procedure on the wake path declares `scheduling_context` as an explicit `SchedulingSourceContext`
INPUT and threads it toward `ScheduleEvent`. Exact names, verbatim:

| # | Requirement (U2) | Procedure / structure — exact name | Evidence (verbatim) | Status |
|---|---|---|---|---|
| 1 | Tagged source type exists | `SchedulingSourceContext` (§0.8) | `SchedulingSourceContext in { ORDINARY_DISPATCH(dispatch_envelope), POST_EPILOGUE(PostEpilogueSchedulingContext) }` | PASS |
| 2 | Explicit input on the wake primitive | `PROCEDURE StartWake` | `INPUTS: ... scheduling_context   # U2: SchedulingSourceContext in {ORDINARY_DISPATCH(dispatch_envelope), POST_EPILOGUE(pctx)}` | PASS |
| 3 | Explicit input on reserve activation | `PROCEDURE ReserveActivate` | `INPUTS: RoundContext, deficit ..., scheduling_context   # U2: SchedulingSourceContext — ORDINARY_DISPATCH(...) ... or POST_EPILOGUE(pctx)` | PASS |
| 4 | Explicit input on fresh assignment | `PROCEDURE RangeAssign` | `INPUTS: RoundContext, MinerID, requested_size, lease_duration, scheduling_context   # U2: SchedulingSourceContext` | PASS |
| 5 | Explicit input on suffix reassignment | `PROCEDURE RangeReassign` | `INPUTS: RoundContext, unsearched_suffix, reason, from_miner, scheduling_context   # U2: SchedulingSourceContext` | PASS |
| 6 | Explicit input on plan commit | `PROCEDURE CommitRecoveryAssignmentPlan` | `INPUTS: RoundContext, plan, scheduling_context   # scheduling_context in SchedulingSourceContext (U2): POST_EPILOGUE(pctx) here` | PASS |
| 7 | Commit threads it to the constructors | `CommitRecoveryAssignmentPlan` → `ReserveActivate` / `RangeReassign` / `RangeAssign` | `CALL ReserveActivate(..., scheduling_context = scheduling_context)`; `CALL <the spec's constructor: RangeReassign / RangeAssign>(..., scheduling_context = scheduling_context)` | PASS |
| 8 | Commit threads it to every wake | `CommitRecoveryAssignmentPlan` → `StartWake` | `CALL StartWake(..., scheduling_context = scheduling_context)   # U2: StartWake threads it to ScheduleEvent` | PASS |
| 9 | Constructors thread it to the wake | `RangeAssign` / `RangeReassign` / `ReserveActivate` → `StartWake` | `RETURN CALL StartWake(..., scheduling_context = scheduling_context)` (RangeAssign, ReserveActivate); `CALL StartWake(..., scheduling_context = scheduling_context)` (RangeReassign) | PASS |
| 10 | Wake reaches the enqueue interface with pctx | `StartWake` → `ScheduleEvent` | `RETURN ScheduleEvent(..., post_epilogue_context = pctx) AND wake_started   # U2/S7: pctx reaches ScheduleEvent; strictly later` | PASS |

## 3. `StartWake`'s `POST_EPILOGUE` branch — target derivation and the seat through `ScheduleEvent`

`StartWake` recovers the underlying dispatch envelope from the tagged context without losing the tag:
`SET dispatch_envelope <- (scheduling_context is ORDINARY_DISPATCH(e) ? e : scheduling_context.pctx.source_envelope)`
(U2/L1) — an `ORDINARY_DISPATCH(e)` yields `e`; a `POST_EPILOGUE(pctx)` yields `pctx.source_envelope`, never
a manually stamped seq. It draws `wake_latency` once, then branches on the tag:

```
    IF scheduling_context is POST_EPILOGUE(pctx):
      SET src <- pctx.source_event_time
      SET target <- (wake_latency > 0 ? src + wake_latency : next_representable_simulation_time(src))
      RETURN ScheduleEvent(EQ, RoundContext, WakeCompleteEvent,
                           target_event_time = target, target_microphase = WAKE_COMPLETE,
                           {MinerID, AssignmentID(target_assignment)},
                           post_epilogue_context = pctx) AND wake_started
```

So a POSITIVE-latency post-epilogue wake targets `source_event_time + wake_latency`; a ZERO-latency
post-epilogue wake targets `next_representable_simulation_time(source_event_time)`. In both arms the target
is STRICTLY GREATER than `source_event_time`: `wake_latency > 0` gives `src + wake_latency > src`, and
`next_representable_simulation_time(src) > src` by definition. The `pctx` reaches `ScheduleEvent` as
`post_epilogue_context = pctx`, where the S7 rule re-checks the same strictness at the sole enqueue
interface: `IF NOT (target_event_time > post_epilogue_context.source_event_time): RETURN
rejected_post_epilogue_not_strictly_later` and otherwise `SET dc <- 0`. Strictness is therefore enforced
TWICE — once where the target is derived (StartWake) and once structurally where it is enqueued
(ScheduleEvent) — and `delta_cycle` is written by neither caller: `ScheduleEvent` alone derives it.

## 4. The full post-epilogue chain — traced end to end

The two post-epilogue hooks in the `ProcessEventTime` tail (§0.7d step (3)/(3b)) each build a `pctx` and pass
`POST_EPILOGUE(pctx)` into the plan commit; the commit threads that same context, unchanged, to every
constructor and every wake, and each wake threads it to `ScheduleEvent`:

```
ProcessEventTime tail
  ├─ ApplyRecoveryWorkAfterEpilogue(t)                              # U1 hook — recovery WORK
  │    SET pctx <- PostEpilogueSchedulingContext(source_event_time = t, source_envelope = W.due_dispatch_envelope, ...)
  │    CALL CommitRecoveryAssignmentPlan(RoundContext, plan, scheduling_context = POST_EPILOGUE(pctx))
  │
  └─ ApplyRecoveryAssignmentContinuationAfterEpilogue(t)            # T1 hook — branch-C RESTORED (redistribution-only)
       SET pctx <- PostEpilogueSchedulingContext(source_event_time = t, source_envelope = D.continuation_due_dispatch_envelope, ...)
       CALL CommitRecoveryAssignmentPlan(RoundContext, plan, scheduling_context = POST_EPILOGUE(pctx))

CommitRecoveryAssignmentPlan(..., scheduling_context = POST_EPILOGUE(pctx))
  ├─ RESERVE_ACTIVATION spec  → CALL ReserveActivate(..., scheduling_context = scheduling_context)
  ├─ REDISTRIBUTION spec      → CALL RangeReassign / RangeAssign(..., scheduling_context = scheduling_context)
  └─ per-spec required wake    → CALL StartWake(..., scheduling_context = scheduling_context)

ReserveActivate / RangeAssign / RangeReassign(..., scheduling_context)
  └─ CALL StartWake(..., scheduling_context = scheduling_context)

StartWake(..., scheduling_context = POST_EPILOGUE(pctx))
  └─ RETURN ScheduleEvent(..., post_epilogue_context = pctx)        # strictly-later seat; dc = 0
```

At no link is the tag dropped or rebuilt: `ApplyRecoveryWorkAfterEpilogue` and
`ApplyRecoveryAssignmentContinuationAfterEpilogue` construct `pctx` from `source_event_time = t` and the
DUE fact's own dispatch envelope, then pass `scheduling_context = POST_EPILOGUE(pctx)` to
`CommitRecoveryAssignmentPlan`; the commit forwards the SAME `scheduling_context` variable into
`ReserveActivate`, into the `RangeReassign` / `RangeAssign` constructor, and into every `StartWake`; each of
those forwards it verbatim to `StartWake`, which passes `pctx` to `ScheduleEvent`. The §0.8 contract states
the closure explicitly: *"No procedure creates a pctx and then schedules using only the old ordinary
dispatch envelope."* This audit confirms it — the only two procedures that construct a `pctx`
(`ApplyRecoveryWorkAfterEpilogue`, `ApplyRecoveryAssignmentContinuationAfterEpilogue`) both immediately pass
`POST_EPILOGUE(pctx)` into `CommitRecoveryAssignmentPlan`, and every downstream call site threads
`scheduling_context` rather than reconstructing an `ORDINARY_DISPATCH` from the drained envelope. (The
branch-C DUE event of §10a is a distinct S7-governed seat already covered by Stage 1S: `CompleteSecurityRecovery`
builds its own `pctx` and calls `ScheduleEvent(..., post_epilogue_context = pctx)` directly.)

## 5. Ordinary dispatched callers keep their existing delta-cycle derivation

The correction does not disturb ordinary wakes. A dispatched caller passes
`ORDINARY_DISPATCH(dispatch_envelope)` — equivalently a bare threaded `dispatch_envelope`, the default
reading in §0.8 and StartWake's INPUTS note. For that arm, `StartWake` falls through the `POST_EPILOGUE`
branch to the ordinary schedule: a positive-latency ordinary wake calls `ScheduleEvent` at
`target_event_time = now + wake_latency` (a future event_time, so `ScheduleEvent` derives `dc = 0`), and a
zero-latency ordinary wake calls `ScheduleEvent` at `target_event_time = now` (a same-time wake, so
`ScheduleEvent` derives the forward next delta-cycle, H5). In every case `ScheduleEvent` — not the caller —
derives `delta_cycle`, exactly as before U2. So ordinary wakes retain their delta-cycle derivation
unchanged; U2 only adds the tagged parameter and the post-epilogue arm.

## 6. Failure-mode contrast

U2 is meaningful because two concrete regressions are made unreachable by threading the tag:

- **A post-epilogue wake seated at the drained source time.** Suppose the tail built `pctx` with
  `source_event_time = t` but a downstream `StartWake` drew `wake_latency = 0` and scheduled at
  `target_event_time = t` (the drained epilogue time). This would enqueue an ordinary `WakeCompleteEvent` at
  a finalised event_time, violating R1 and the `ProcessEventTime` finalisation ASSERT
  (`ASSERT no ordinary event remains with event_time = t`). Under U2 this cannot happen: the `POST_EPILOGUE`
  arm targets `next_representable_simulation_time(t) > t` for a zero-latency wake, and even if a target of
  `t` were computed, `ScheduleEvent`'s S7 guard `RETURN rejected_post_epilogue_not_strictly_later` refuses
  the seat. The wake lands STRICTLY LATER, at `t + wake_latency` or `next_representable_simulation_time(t)`.

- **A `pctx` dropped at a nested `ScheduleEvent`.** Suppose `CommitRecoveryAssignmentPlan` had reconstructed
  an `ORDINARY_DISPATCH(dispatch_envelope)` from the drained envelope for one of its nested wakes (e.g. a
  single `StartWake` inside the per-spec required-wake loop) while carrying `pctx` for the others. That one
  wake would derive its `delta_cycle` from the LIVE `EQ.current_*` dispatch context — the drained event_time
  `t` — rather than from the strictly-later post-epilogue rule, re-seating a recovery wake at the drained
  time and re-introducing exactly the causality break S7 removed. Under U2 the tag is a threaded parameter,
  not a per-call reconstruction: `CommitRecoveryAssignmentPlan` passes the SAME `scheduling_context` into
  `ReserveActivate`, `RangeReassign` / `RangeAssign`, and every `StartWake`, so no nested seat can silently
  revert to the ordinary envelope. The §0.8 invariant names this failure and forbids it.

## 7. Result

U2 is realised exactly as specified: `SchedulingSourceContext` (§0.8) is an explicit tagged INPUT on
`ReserveActivate`, `RangeReassign`, `RangeAssign`, `StartWake`, and `CommitRecoveryAssignmentPlan`; a
`POST_EPILOGUE` caller threads its `PostEpilogueSchedulingContext` unbroken from the `ProcessEventTime` tail
(`ApplyRecoveryWorkAfterEpilogue` / `ApplyRecoveryAssignmentContinuationAfterEpilogue`) through
`CommitRecoveryAssignmentPlan` and the constructors to `StartWake`, which passes `post_epilogue_context = pctx`
to `ScheduleEvent`. A positive-latency post-epilogue wake targets `source_event_time + wake_latency`; a
zero-latency post-epilogue wake targets `next_representable_simulation_time(source_event_time)`; the
`target_event_time` is STRICTLY GREATER than `source_event_time`, enforced both where StartWake derives the
target and structurally at the S7 enqueue guard (`rejected_post_epilogue_not_strictly_later`), with
`delta_cycle` derived by `ScheduleEvent` alone. No procedure constructs a `pctx` and then schedules with only
the old ordinary dispatch envelope, and ordinary dispatched callers pass `ORDINARY_DISPATCH(dispatch_envelope)`
so their existing delta-cycle derivation is untouched. This is a scheduling-provenance / causality correction
only: it seats no new residency boundary, re-times no interval, and changes no cost model, so the A1 accepted
baseline of **8.420833333 kWh** is unchanged and any energy difference remains attributable solely to reduced
active power-time.

## Footer

This document is documentation only; it makes no property claim about the consensus mechanism. The consensus
mechanism is named **PoCol**, and **the idle policy within PoCol** is referenced solely as a mechanism. U2
changes how the SCHEDULING SOURCE is threaded, never how time or energy is counted; the A1 baseline of
**8.420833333 kWh** is unchanged. The prohibited rebranded-algorithm-name variants are not used anywhere in
this document.
