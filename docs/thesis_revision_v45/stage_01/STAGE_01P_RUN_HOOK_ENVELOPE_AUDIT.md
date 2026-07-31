# Stage 1P — Run-Hook Envelope Audit (P2)

This audit records a **documentation-only** revision of the **PoCol** consensus
specification. It concerns the deterministic identity of the horizon-close run
hook in `docs/thesis_revision_v45/stage_01/STAGE_01_PROTOCOL_PSEUDOCODE.md`. The
mechanism under revision is **the idle policy within PoCol**, referenced here as
a mechanism only; no property of that mechanism is claimed by this document. The
**A1 baseline of 8.420833333 kWh is UNCHANGED** — no energy figure is altered,
because the revision changes only how a run-level hook names its event envelope,
not what state transitions it produces.

**Scope.** Stage 1P correction **P2 — deterministic run-hook envelope**. The
audit covers exactly: the new `STRUCTURE RunHookContext` and its reserved
constants (§0.7e area), the `CloseRoundAtHorizon` (§20b) envelope construction
and replay guard, the four required properties, and the initialisation/threading
path through `RoundInitialise` (§1) and `ProcessEventTime`.

## 1. RunHookContext, reserved constants, and HorizonHookID

The undefined `horizon_close_delta_cycle` and `horizon_close_event_seq` fields of
Stage 1O are **REMOVED**. Run-hook identity is now owned by a single per-run
structure, `STRUCTURE RunHookContext` (defined immediately after
`STRUCTURE EventQueueContext` in the §0.7e area):

- `run_hook_seq` — a monotonic per-run counter for run-hook envelopes,
  **separate** from `EventQueueContext.event_creation_seq` (which is the
  ordinary-event namespace, J4). Initialised 0 at run start; preserved across
  rounds.
- `applied_run_hook_ids` — the idempotence key set of `RunHookID`s already
  applied. A run-hook whose id is in this set is a deterministic no-op on replay.
  Initialised empty at run start; preserved across rounds.

Two reserved constants accompany the structure:

- `RUN_HOOK_CYCLE` — a **reserved** `delta_cycle` value used ONLY by run-hook
  envelopes. `ScheduleEvent`'s delta-cycle derivation (§0.7e) produces only
  ordinary cycles (0, current, current+1, …) and **NEVER** `RUN_HOOK_CYCLE`.
- `HORIZON_CLOSE` — the run-hook **kind** for the horizon close.

The horizon-close hook's deterministic identity is
`HorizonHookID = (RunID, run_horizon_T, HORIZON_CLOSE)` — a fixed function of the
run and its horizon, so exactly one such identity exists per run.

## 2. CloseRoundAtHorizon (§20b): envelope construction and replay guard

`CloseRoundAtHorizon` now takes `INPUTS: RoundContext, RunHookContext` — the
run-hook envelope owner, not a dispatched event envelope. Its ordered effects:

1. Compute `HorizonHookID <- (RunID, run_horizon_T, HORIZON_CLOSE)`.
2. **Replay guard.** `IF HorizonHookID in RunHookContext.applied_run_hook_ids`
   then `RETURN horizon_close_duplicate_noop(HorizonHookID)` — no second
   transition energy and no second residency boundary are produced.
3. Increment: `SET RunHookContext.run_hook_seq <- RunHookContext.run_hook_seq + 1`.
4. Mint the deterministic envelope
   `horizon_envelope <- { event_time = run_horizon_T, delta_cycle = RUN_HOOK_CYCLE,
   event_seq = RunHookContext.run_hook_seq, hook_id = HorizonHookID }`.
5. Thread it through the single closure path:
   `CALL CloseRoundAssignments(RoundContext, disposition = ROUND_ABORTED,
   stop_reason = ROUND_ABORTED, dispatch_envelope = horizon_envelope)`. Every
   miner transition below (each `EnterLowPowerListen` / `ApplyMinerStateTransition`,
   M1) threads **this** envelope.
6. `RECORD horizon_end_disposition(RoundID) <- closed_at_horizon`.
7. `TRANSITION round_state -> ROUND_ABORTED` (declared horizon-end, terminal at T).
8. `ADD HorizonHookID to RunHookContext.applied_run_hook_ids`.

It returns `round_closed_at_horizon(RoundID, run_horizon_T, HorizonHookID)`. No
ambient or undefined event identity is read or stamped anywhere in the procedure.

## 3. Required properties

**Exactly one horizon-close envelope per run.** `HorizonHookID` is a fixed
function of `(RunID, run_horizon_T, HORIZON_CLOSE)`; step 8 records it in
`applied_run_hook_ids`, and step 2 short-circuits any later call. Hence at most
one envelope with `event_seq = run_hook_seq` is minted per run for the horizon
close (§20b).

**Replay returns horizon_close_duplicate_noop.** A replayed/retried call finds
`HorizonHookID in applied_run_hook_ids` (step 2) and returns
`horizon_close_duplicate_noop(HorizonHookID)` before step 3. No `run_hook_seq`
increment, no envelope mint, no `CloseRoundAssignments` call — therefore no
second transition energy and no second residency boundary (§20b).

**No collision with an ordinary ScheduleEvent envelope.** The envelope carries
`delta_cycle = RUN_HOOK_CYCLE`, a reserved value. `ScheduleEvent`'s delta-cycle
derivation (§0.7e) produces only ordinary cycles and never `RUN_HOOK_CYCLE`, so
the run-hook envelope occupies a disjoint namespace from every enqueued ordinary
event envelope.

**Unique miner-transition identity.** Every miner transition produced by the
horizon close threads `horizon_envelope` (step 5 / `CloseRoundAssignments` M1),
so each transition is uniquely identifiable through
`(MinerID, assignment_version, run-hook envelope)`. The reserved `delta_cycle`
plus the deterministic `run_hook_seq` guarantee no two transitions share an
identity and none aliases an ordinary event.

**No ambient/undefined event identity remains.** The removed Stage 1O fields
`horizon_close_delta_cycle` and `horizon_close_event_seq` are gone; the hook now
derives its full envelope from the single `RunHookContext` owner. No handler
reads an ambient seq and none manually stamps `EventQueueContext.event_creation_seq`.

## 4. Initialisation and threading

`RunHookContext` is initialised at run start inside `RoundInitialise` (§1) with
`run_hook_seq = 0` and `applied_run_hook_ids = empty set`, and is **preserved
across rounds** (it is per-run, not per-round). `ProcessEventTime` carries a
`RunHookContext` input (null off the horizon) and threads it to
`CloseRoundAtHorizon(RoundContext, RunHookContext)` at the horizon step, supplied
by the run driver `RunEventLoopToHorizon` as `RunContext.RunHookContext`.

## 5. BEFORE vs AFTER

| Aspect | BEFORE (Stage 1O) | AFTER (Stage 1P / P2) |
| --- | --- | --- |
| Envelope delta_cycle | `horizon_close_delta_cycle` (undefined) | `RUN_HOOK_CYCLE` (reserved, §0.7e) |
| Envelope event_seq | `horizon_close_event_seq` (undefined) | `run_hook_seq` from `RunHookContext` |
| Identity owner | none (ambient) | `STRUCTURE RunHookContext` (per-run) |
| Hook identity | none | `HorizonHookID = (RunID, run_horizon_T, HORIZON_CLOSE)` |
| Replay behaviour | unspecified | `horizon_close_duplicate_noop` via `applied_run_hook_ids` |
| Ordinary-event collision | not excluded | excluded (reserved cycle, disjoint namespace) |

## 6. Acceptance checks

| # | Check | Status | §-evidence |
| --- | --- | --- | --- |
| 1 | `horizon_close_delta_cycle` / `horizon_close_event_seq` removed | PASS | §0.7e (RunHookContext replaces them) |
| 2 | `RunHookContext` defined after `EventQueueContext`; `run_hook_seq` separate from `event_creation_seq` | PASS | §0.7e |
| 3 | Reserved `RUN_HOOK_CYCLE` never produced by `ScheduleEvent` derivation | PASS | §0.7e |
| 4 | `CloseRoundAtHorizon` takes `(RoundContext, RunHookContext)`; builds deterministic envelope | PASS | §20b |
| 5 | Replay guard returns `horizon_close_duplicate_noop`; no second transition/boundary | PASS | §20b |
| 6 | Envelope threaded into every miner transition via `CloseRoundAssignments` | PASS | §20b / M1 |
| 7 | `RunHookContext` initialised in `RoundInitialise`, preserved across rounds | PASS | §1 |
| 8 | `ProcessEventTime` threads `RunHookContext` to the hook at the horizon | PASS | ProcessEventTime / §20b |

---

Documentation only. The consensus specification is named **PoCol**. **The idle
policy within PoCol** is referenced here as a mechanism only; no property is
claimed. The **A1 baseline of 8.420833333 kWh is unchanged**. The prohibited
rebranded-algorithm-name variants are not used anywhere in this document.
