# Stage 1AI — Procedure Call Graph

This document records the procedure/function call graph of the FINAL Stage-1AI normative pseudocode
(`STAGE_01_PROTOCOL_PSEUDOCODE.md`) and certifies that it closes with **0 dangling references**. It is regenerated
against the tree only after every AI edit (AI1–AI9) is complete. The algorithm is **PoCol**; the mechanism is the idle
policy within PoCol; the A1 baseline (`8.420833333 kWh`) is unchanged.

## 1. Callable inventory

- **Total defined callables:** **110** = **108 `PROCEDURE` + 2 `FUNCTION`** (the two `FUNCTION`s are
  `outcome_consistent_with_census` and `ClassifyRecoveryWork`).
- **Change over Stage 1AH:** **+2** callables — Stage 1AH closed at **108 total callables** (106 `PROCEDURE` + 2 `FUNCTION`);
  Stage 1AI adds exactly two new `PROCEDURE`s:
  1. `SetDriverRequestStatus` — the single guarded mutator of `driver_request.status` (AI4).
  2. `CompleteDriverRequestOnDispatch` — the dispatcher-owned request-completion owner that resolves the exact
     `driver_request` from the immutable seat-`EventRef` reverse binding and drives `SEATED → CONSUMED` (AI4).
- **No callable was removed or renamed.** AI is additive at the callable level; the other AI corrections change EXISTING
  procedures' bodies, signatures, or RETURNS unions (see §3) without introducing or deleting callables beyond the two above.

## 2. Dangling-reference check

A mechanical extraction of every `^PROCEDURE <name>` / `^FUNCTION <name>` definition and every `CALL <Name>` target over
the final `STAGE_01_PROTOCOL_PSEUDOCODE.md` yields **0 genuine dangling `CALL` targets** — every CamelCase `CALL` target
resolves to a defined callable. The only tokens a naive `\bCALL\s+(\w+)` regex flags are documented false positives, NOT
dangling calls:

| Flagged token | Why it is not a dangling call |
|---------------|-------------------------------|
| `inv` (`CALL inv.procedure WITH inv.args`) | a member dispatch of the bound `handler_invocation` variable in `ProcessEventTime`, not a named procedure |
| `is` / `the` / `target` / `this` | ordinary English inside prose comments ("the CALL is not guarded", "NOT a CALL target", "CALL this writer", "CALL the same canonical RoundAbort") |
| `ClassifyRecoveryWork` | defined as `FUNCTION ClassifyRecoveryWork` (a `FUNCTION`, not a `PROCEDURE`); resolved when both kinds are counted |

After filtering these, the set of `CALL` targets is a subset of the defined-callable set — the graph closes.

## 3. Stage-1AI call-graph deltas

The two new callables and the re-wired driver-request completion path introduce the following edges (caller → callee):

- `AdmitDriverRequest` → (no new callee; derives the stable logical id and admits) — the AI3 idempotent producer.
- `SeatMinerRegister` → `ScheduleEvent`, `SetDriverRequestStatus` (publishes the reverse binding + `PENDING → SEATED`
  atomically with the seat, AI4); `admission_mode ∈ {IN_DISPATCH_GENESIS, DRIVER_INTAKE}` (AI1).
- `SeatReserveActivate` → `ScheduleEvent`, `SetDriverRequestStatus` (same reverse-binding + `PENDING → SEATED`, AI4).
- `SeatPendingDriverRequests` → `SeatMinerRegister` / `SeatReserveActivate`, `SetDriverRequestStatus` (scope-stale /
  seat-failure rejections, AI4/AI5).
- `RoundInitialiseEvent` → `SeatMinerRegister(admission_mode = IN_DISPATCH_GENESIS)`, `SetDriverRequestStatus`, `RoundAbort`
  (the AI1 in-dispatch genesis seat + declared abort on a failed genesis seat).
- `ProcessEventTime` → `CompleteDriverRequestOnDispatch` (after every ordinary dispatch — the success path and the three
  defensive CONSUME paths, AI4).
- `CompleteDriverRequestOnDispatch` → `SetDriverRequestStatus` (`SEATED → CONSUMED`, AI4).
- `CancelQueuedEvent` → `SetDriverRequestStatus` (`SEATED → CANCELLED` for a cancelled driver seat, AI4).
- `SeatNextRoundBootstrap` → `ScheduleEvent` with a `DRIVER(RUN_BOOTSTRAP)` origin at run start OR a
  `TERMINAL_ROTATION` origin for a rotation (AI8).
- `CloseRoundAssignments` → `PublishTerminalRoundAndSeatNext` with its result CAPTURED + stored (AI6).
- `MinerRegister` → `SeatParticipantSetupOrAbort` with its result INSPECTED (AI7); `MinerRegisterEvent` → `MinerRegister`
  (propagates the disposition).
- `RunEventLoopToHorizon` → `FinalizeSimulationRun` on the `NEXT_ROUND_BOOTSTRAP_FAILED` partial-run path (AI6).

Every callee above is a defined `PROCEDURE`/`FUNCTION`; every new caller→callee edge is closed.

## 4. Result-union closure (spot check)

Each result token a caller SWITCHes on is present in the callee's RETURNS union (full verification in
`STAGE_01AI_PROCEDURE_SIGNATURE_CALL_AUDIT.md`): the `miner_registered_*` dispositions (MinerRegister → MinerRegisterEvent →
`CompleteDriverRequestOnDispatch` disposition); the four AI2 `ScheduleEvent` rejections (`rejected_driver_context_mismatch`
/ `_kind_event_type_mismatch` / `_target_context_mismatch` / `_target_before_simulation_frontier`); the `SetDriverRequestStatus`
results (`driver_request_status_set` / `_unknown` / `_status_mismatch` / `_illegal_transition`); the `AdmitDriverRequest`
results (`driver_request_admitted` / `_already_admitted` / `_time_before_admission_rejected` / `_scope_invalid`); and the
`CloseRoundAssignments` `closure_record(publication_result)` consumed by `ValidBlockAccept` / `RoundAbort` /
`CloseRoundAtHorizon` and stored for `RunEventLoopToHorizon`.

## 5. Verdict

**PASS — the Stage-1AI call graph closes with 0 dangling references over 110 defined callables** (108 total carried forward
from Stage 1AH plus `SetDriverRequestStatus` and `CompleteDriverRequestOnDispatch`), every AI-changed procedure's callees and
result tokens resolve, and no executable source / configuration / DOCX / PDF file is affected.
