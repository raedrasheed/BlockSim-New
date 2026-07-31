# Stage 1S — Post-Epilogue Scheduler Audit (S7)

**Consensus mechanism.** This audit concerns the consensus specification named **PoCol**. Within PoCol,
**the idle policy within PoCol** is referenced solely as a mechanism; no property of the consensus
mechanism is claimed here. This is documentation only, describing the frozen behaviour of
`STAGE_01_PROTOCOL_PSEUDOCODE.md`; it neither adds a consensus feature nor amends any procedure beyond the
already-frozen S7 text it audits. The A1 accepted baseline of **8.420833333 kWh** is UNCHANGED and is
restated only for provenance: **S7 is a scheduling-provenance correction** — it makes the SOURCE of a
post-epilogue `ScheduleEvent` call explicit and enforces a strictly-later target. It moves no residency
boundary and re-prices nothing; any energy difference remains attributable **only to reduced active
power-time** (fewer / shorter `ACTIVE_HASHING` residency intervals), exactly as `ApplyMinerStateTransition`'s
`residency_ledger` measured before (§0.7b).

**Scope — Stage-1S correction S7 (Explicit post-epilogue scheduling context).** `ScheduleEvent` (§0.7e) is
extended with a declared post-epilogue scheduling source, `post_epilogue_context`. A new structure,
`PostEpilogueSchedulingContext`, names the drained source event_time, the source envelope, and the
run/queue state the scheduler updates. With it, `ScheduleEvent` may be entered from EXACTLY ONE of three
declared sources, and a post-epilogue call MUST target a STRICTLY LATER event_time than its source. This
makes the R1 prohibition ("no ordinary event at the drained event_time `t`") STRUCTURAL rather than a caller
obligation. Grounded in **§0.7e** (`STRUCTURE PostEpilogueSchedulingContext`, `PROCEDURE ScheduleEvent`) and
**§10a** (`CompleteSecurityRecovery` branch C, which builds the `pctx` and seats the continuation).

## 1. The `PostEpilogueSchedulingContext` structure (§0.7e)

The structure declares the source of a post-epilogue `ScheduleEvent` call — a caller that is NOT an ordinary
dispatched handler and NOT a sim-driver entry, but `ApplyRecoveryCompletionAfterEpilogue`'s branch dispatch
(`CompleteSecurityRecovery`), run by `ProcessEventTime` AFTER the event_time is drained and the epilogue ran.
Its fields:

- `source_event_time` — the drained epilogue event_time `t` (`= dispatch_envelope.event_time` of the applied
  decision). This is the value the strictly-later check compares against.
- `source_envelope` — the `dispatch_envelope` of the applied recovery decision (its `ORDINARY_EVENT`
  identity), carried so the seated event's provenance is explicit.
- `EventQueueContext` — the sole dispatch/scheduling state (the same `EQ` `ScheduleEvent` updates).
- `RunContext` — the per-run owner (§1.0), for symmetry with the other two declared scheduling sources.

The structure comment binds the contract: `ScheduleEvent(..., post_epilogue_context = this)` requires
`target_event_time > source_event_time` and derives `delta_cycle = 0`; the `event_creation_seq` is STILL
minted solely by `ScheduleEvent` (J4); no post-epilogue caller may enqueue at `source_event_time`
(R1 structural).

## 2. The three declared scheduling sources (§0.7e PRECONDITIONS)

`ScheduleEvent`'s PRECONDITIONS admit EXACTLY ONE of three sources. A post-epilogue call MUST carry
`post_epilogue_context`; no other call may:

1. **A dispatched ordinary handler** — a handler dispatched by `ProcessEventTime`, with `EQ.current_*` set to
   the dispatched envelope; `post_epilogue_context = null`.
2. **An explicitly seated sim-driver handler** — a sim-driver entry with an explicit `DriverEventEnvelope`
   (§0.7f/K4) supplying the `EQ.current_*` values; `post_epilogue_context = null`.
3. **`ApplyRecoveryCompletionAfterEpilogue`'s branch dispatch (`CompleteSecurityRecovery`)** — which supplies
   a valid `PostEpilogueSchedulingContext`; this is the ONLY source that carries `post_epilogue_context`.

Sources (1) and (2) derive `delta_cycle` from the live dispatch context (K8); source (3) derives it from the
post-epilogue rule below. In every case the seq is owned solely by `ScheduleEvent`.

## 3. The `ScheduleEvent` post-epilogue branch (§0.7e, verbatim)

The rule is applied BEFORE the ordinary K8 delta-cycle derivation, so it fully governs the post-epilogue
case and short-circuits the same-time / backward arms:

```
    # S7 (2-post): POST-EPILOGUE SCHEDULING RULE. A post-epilogue caller MUST target a STRICTLY LATER event_time than
    #     its source (the drained epilogue event_time), and the derived delta_cycle is DETERMINISTICALLY 0 at that
    #     future event_time. So a post-epilogue caller can NEVER enqueue at source_event_time (R1 becomes structural).
    IF post_epilogue_context != null:
      IF NOT (target_event_time > post_epilogue_context.source_event_time):
        RETURN rejected_post_epilogue_not_strictly_later   # S7: a post-epilogue event at/behind the source is REJECTED
      SET dc <- 0                            # S7: deterministically 0 at the strictly-later future event_time
    # K8 (2): DERIVE the target delta_cycle from the dispatch context; the caller never supplies it.
    ELSE IF target_event_time > EQ.current_event_time:
      SET dc <- 0
    ...
```

After the branch, `ScheduleEvent` proceeds to the shared tail: it mints the seq atomically
(`SET EQ.event_creation_seq <- EQ.event_creation_seq + 1; SET seq <- EQ.event_creation_seq`, J4), builds an
`ORDINARY_EVENT` envelope, and inserts by the deterministic total-order key. So a post-epilogue event is an
ordinary queued event in every respect except that its delta-cycle and strict-lateness are governed by S7
rather than by the live `EQ.current_*` dispatch context.

## 4. Proof — a post-epilogue caller can never enqueue at `source_event_time`

Let a post-epilogue call carry `post_epilogue_context = pctx` with `pctx.source_event_time = t`, and let
`target_event_time = τ`. Because `pctx != null`, control enters the S7 branch:

1. If `NOT (τ > t)` — i.e. `τ <= t`, which includes `τ = t` — `ScheduleEvent` `RETURN`s
   `rejected_post_epilogue_not_strictly_later` and NO envelope is created and NO insert occurs. In
   particular the case `τ = t` is rejected: the caller cannot enqueue at `source_event_time`.
2. Otherwise `τ > t` strictly, `SET dc <- 0`, and the envelope is seated at `event_time = τ > t` with
   `delta_cycle = 0`.

Both arms are exhaustive and mutually exclusive, so the ONLY event a post-epilogue caller can seat has
`event_time > source_event_time` strictly. The guard is evaluated inside the single enqueue interface,
before any seq is minted or any queue write occurs, so no post-epilogue path can bypass it. Hence R1 ("no
ordinary event enqueued at the drained `t`") holds for post-epilogue callers STRUCTURALLY — it is a property
of `ScheduleEvent` itself, not a discipline the caller must remember. The finalisation ASSERT of §0.7d
(`no ordinary event remains with event_time = t`) therefore cannot be violated by any post-epilogue seat.

## 5. The sole current post-epilogue scheduling caller (§10a branch C)

`CompleteSecurityRecovery` branch C (RESTORED requiring range redistribution / reserve assignment) is the
ONLY current caller that passes a `post_epilogue_context`. It computes
`t_cont <- next_representable_simulation_time(dispatch_envelope.event_time)` (strictly later than `t`,
step 1), validates `t_cont <= run_horizon_T` (step 2), builds

```
    SET pctx <- PostEpilogueSchedulingContext(source_event_time = dispatch_envelope.event_time,
                  source_envelope = dispatch_envelope, EventQueueContext = EQ, RunContext = RoundContext.RunContext)
```

and seats EXACTLY ONE `RecoveryAssignmentContinuationEvent` through `ScheduleEvent(..., post_epilogue_context = pctx)`
at `target_event_time = t_cont, target_microphase = RECOVERY_ASSIGNMENT_CONTINUATION`, carrying the full
recovery identity (S3). Because `pctx.source_event_time = dispatch_envelope.event_time = t` and
`t_cont = next_representable_simulation_time(t) > t`, the S7 branch derives `dc = 0` and accepts the seat; a
seat at `t` would be rejected. The ASSIGNMENT transition and any `WakeCompleteEvent`s happen INSIDE the
continuation, dispatched at `t_cont`, never at `t`. No other procedure in the specification passes
`post_epilogue_context`, so sources (1) and (2) cover every other `ScheduleEvent` call and source (3) is
uniquely branch C's continuation.

## 6. Result

S7 is realised exactly as specified: `PostEpilogueSchedulingContext` (`source_event_time`, `source_envelope`,
`EventQueueContext`, `RunContext`) makes the post-epilogue scheduling source explicit; `ScheduleEvent` admits
EXACTLY ONE of three declared sources — a dispatched ordinary handler, an explicitly seated sim-driver
handler, or `ApplyRecoveryCompletionAfterEpilogue`'s branch dispatch with a valid `post_epilogue_context`;
and the post-epilogue branch rejects any `target_event_time <= source_event_time`
(`rejected_post_epilogue_not_strictly_later`) while deterministically setting `dc <- 0` at the strictly-later
future time. The `event_creation_seq` remains minted solely by `ScheduleEvent` (J4). The proof of §4 shows a
post-epilogue caller can never enqueue at `source_event_time`, making R1 structural; branch C's
`RecoveryAssignmentContinuationEvent` (seated at `next_representable_simulation_time(t) > t`) is the sole
current post-epilogue scheduling caller. This is a scheduling-provenance correction only: it seats no new
residency boundary and changes no cost model, so the A1 accepted baseline of **8.420833333 kWh** is unchanged
and any energy difference remains attributable solely to reduced active power-time.

## Footer

This document is documentation only; it makes no property claim about the consensus mechanism. The consensus
mechanism is named **PoCol**, and **the idle policy within PoCol** is referenced solely as a mechanism. The
A1 baseline of **8.420833333 kWh** is unchanged. The prohibited rebranded-algorithm-name variants are not used anywhere in this document.
