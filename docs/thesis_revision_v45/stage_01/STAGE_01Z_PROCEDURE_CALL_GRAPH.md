# Stage 1Z — Procedure Call Graph

This document resolves the procedure call graph of `STAGE_01_PROTOCOL_PSEUDOCODE.md` after corrections Z1–Z6 and records
that it contains NO dangling call. Stage 1Z adds NO new procedure — it introduces records, registries, and a signature
parameter (`assignment_effect_policy`) — so the defined count remains **85** (unchanged from Stage 1Y).

## 1. Resolution method

- **Defined symbols:** every `^PROCEDURE <name>` / `^FUNCTION <name>` header (85 unique names).
- **Call targets:** every `CALL <name>` invocation target.
- **Dispatched handlers:** event handlers (e.g. `SetupRetryEvent`) are seated via `ScheduleEvent` and dispatched by
  `ProcessEventTime`, not via `CALL`; a defined handler with no `CALL` site is NOT dangling.
- **Dangling test:** `{ call targets } \ { defined symbols }`. The only tokens the raw scan surfaces are `is` and `this`,
  from prose fragments, not invocations. **Real dangling calls = 0.**

## 2. Z-touched edges (no new nodes)

Stage 1Z changes the DATA threaded across existing edges (setup transaction becomes `rollback_items`; the retry registry
becomes `setup_retry_records`; `ApplyMinerStateTransition` gains `assignment_effect_policy`; the wake-origin map is set/
cleared in the hook) — the call topology is unchanged from Stage 1Y.

### 2.1 `AbortPendingWakeForRollback` (Z3/Z4/Z5) — 3 callers

| Caller | Site |
|--------|------|
| `RollbackParticipantSetup` | per `setup_txn.rollback_items` (§2, ~L1863) |
| `RollbackTemplateRefreshSetup` | per `setup_txn.rollback_items` (§2, ~L1894) |
| `RollbackRecoveryAssignmentPlan` | per `rollback_record.items` (§10a, ~L3917) |

- **Out-edge:** `AbortPendingWakeForRollback` → `ApplyMinerStateTransition` with `reason = validation_abort` and
  `assignment_effect_policy = STATE_ONLY_ROLLBACK` (Z4, the sole `STATE_ONLY_ROLLBACK` call site, ~L1821). It reads the
  nullable `WakeEventRef` (Z3) and the `waking_origin_assignment_ref` binding (Z5); it is the SINGLE owner of the canonical
  assignment close.

### 2.2 `ApplyMinerStateTransition` (Z4/Z5)

- Gains the `assignment_effect_policy = EDGE_DEFAULT` parameter (default). Every caller except
  `AbortPendingWakeForRollback` uses the default (`EDGE_DEFAULT`); only `AbortPendingWakeForRollback` passes
  `STATE_ONLY_ROLLBACK`.
- Sets `waking_origin_assignment_ref[MinerID]` on entry to `WAKING` and clears it on any `WAKING` departure (Z5), inside
  the atomic apply — no new call edge.

### 2.3 `SetupRetryEvent` (Z1) — dispatched handler

- In-edges: `ScheduleEvent(SetupRetryEvent, ...)` from `PrepareParticipantsForNewRound` and
  `ContinueTemplateRefreshAssignmentSetup`. Each seating site now, on `scheduled(event_ref)`, ATOMICALLY publishes
  `setup_retry_records[srid]` with `status = SEATED` (Z1, ~L1772 / ~L5035).
- Out-edges (unchanged): → `PrepareParticipantsForNewRound` (PARTICIPANT_SETUP), →
  `ContinueTemplateRefreshAssignmentSetup` (TEMPLATE_REFRESH_SETUP), → `RoundAbort`. The disposition is CAPTURED (no direct
  `RETURN CALL`) so the record's terminal status can be set.

### 2.4 The three rollback owners (Z6)

`RollbackParticipantSetup`, `RollbackTemplateRefreshSetup`, and `RollbackRecoveryAssignmentPlan` iterate their centralised
record lists (`setup_txn.rollback_items` / `rollback_record.items`) and call `AbortPendingWakeForRollback` per item — the
former parallel-map iteration is withdrawn (Z6). No call edge changed.

## 3. Full defined-procedure inventory (85)

Identical to `STAGE_01Y_PROCEDURE_CALL_GRAPH.md`'s 85 procedures. No procedure was added, removed, or renamed in Stage 1Z;
`ApplyMinerStateTransition`, `AbortPendingWakeForRollback`, `SetupRetryEvent`, the three rollback owners, the two seating
procedures, `StartWake`, and `RunInitialise` had their bodies/signatures updated in place.

## 4. Result

The Stage-1Z call graph resolves with **85 defined procedures and 0 dangling calls**. `AbortPendingWakeForRollback` is
defined once and reached from exactly three call sites (the three rollback owners), calling only `ApplyMinerStateTransition`
(now with `assignment_effect_policy = STATE_ONLY_ROLLBACK`); every dispatched handler (including `SetupRetryEvent`) is
reachable through `ScheduleEvent` / `ProcessEventTime`.
