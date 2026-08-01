# Stage 1Z — Semantic Test Vectors (TV219–TV226)

These blocking paper test vectors exercise corrections Z1–Z6 of the retry-lifecycle and rollback-snapshot lock. Each
vector names the EXACT procedures and preconditions it drives, states the required outcome, and asserts NO behaviour that
is not written in `STAGE_01_PROTOCOL_PSEUDOCODE.md` / `STAGE_01_MINER_STATE_MACHINE.md` (no assumed guard, transition,
edge, or result name). Every vector preserves the A1 baseline (`8.420833333 kWh`). The algorithm is **PoCol** and the
mechanism under test is the idle policy within PoCol.

Terminology: `setup_retry_records[SetupRetryID]` is the single retry registry (Z1); `SetupRetryStatus ∈ { SEATED,
APPLYING, APPLIED, SUPERSEDED, CANCELLED, ABORTED }`; `setup_rollback_item` is the centralised per-assignment rollback
record (Z6); `assignment_effect_policy ∈ { EDGE_DEFAULT, STATE_ONLY_ROLLBACK }` (Z4);
`waking_origin_assignment_ref[MinerID]` is the wake-origin binding (Z5); `T12` is the authoritative `WAKING -> OFFLINE`
edge with the `ValidationAbort` trigger.

---

## TV219 — A SEATED retry's first dispatch executes and is not a duplicate (Z1)

- **Procedures:** the seating procedure (`PrepareParticipantsForNewRound` / `ContinueTemplateRefreshAssignmentSetup`),
  `SetupRetryEvent`.
- **Setup:** a rolled-back setup seats a `SetupRetryEvent`; the seat publishes `setup_retry_records[srid]` with
  `status = SEATED`. The event then fires for the FIRST time in a valid state (`round_state = ASSIGNMENT`, exact template
  identity, within budget, participants re-enlistable).
- **Expected:** the status-based duplicate guard reads `rec.status = SEATED` and does NOT suppress; the first dispatch
  ATOMICALLY flips `SEATED -> APPLYING` and EXECUTES the kind-specific target. The retry is never mistaken for a duplicate
  on its first dispatch (a presence-only guard would have wrongly suppressed it).

## TV220 — Target results drive the record deterministically; a replay is suppressed (Z1)

- **Procedures:** `SetupRetryEvent`, `PrepareParticipantsForNewRound` / `ContinueTemplateRefreshAssignmentSetup`.
- **Setup A (success):** the first dispatch's target returns `participant_set_prepared` (or a committed `TemplateID`).
- **Expected A:** the captured result sets `rec.status = APPLIED`; a later replay of the same `SetupRetryID` finds
  `rec.status = APPLIED` (non-SEATED) and returns `setup_retry_duplicate_suppressed` — no target re-run, no RoundAbort.
- **Setup B (later generation):** the target returns `participant_set_setup_retry_seated` / `template_refresh_retry_seated`.
- **Expected B:** `rec.status = SUPERSEDED` (a later generation was seated, with its own SEATED record).
- **Setup C (abort):** the target returns `round_aborted`.
- **Expected C:** `rec.status = ABORTED`. In all cases `rec.target_disposition` records the captured disposition.

## TV221 — The before-image is captured before creation; rollback restores it (Z2/I20)

- **Procedures:** `PrepareParticipantsForNewRound` / `ContinueTemplateRefreshAssignmentSetup`, `CreatePendingAssignment`,
  `AbortPendingWakeForRollback`.
- **Setup:** a setup item captures `before_image = coverage_custody_before_image(range)` BEFORE `CreatePendingAssignment`;
  the constructor then sets `custody_status(range)` and appends to `assignment_ledger`; the setup later fails and rolls back.
- **Expected:** the item's `before_image` is the pre-constructor I8a/I8b state; on rollback the coverage/custody ledgers
  for the item's range are restored to exactly those pre-constructor values (invariant I20) — never the post-mutation state.

## TV222 — A pre-transition wake-schedule failure yields WakeEventRef = null and a clean rollback (Z3)

- **Procedures:** `StartWake`, `PrepareParticipantsForNewRound` / `ContinueTemplateRefreshAssignmentSetup`,
  `AbortPendingWakeForRollback`.
- **Setup:** `CreatePendingAssignment` succeeds and a complete `setup_rollback_item` is appended; then `StartWake` returns
  `wake_schedule_failed_before_transition` (ScheduleEvent rejected the wake before any transition).
- **Expected:** the item records `WakeEventRef = null` and `wake_result = wake_schedule_failed_before_transition`. On
  rollback, `AbortPendingWakeForRollback` sees `WakeEventRef = null` and cancels nothing (no undefined map lookup), the
  miner was never `WAKING` so no T12 departs, and the assignment is closed and the before-image restored.

## TV223 — Rollback ValidationAbort uses STATE_ONLY_ROLLBACK; one close owner (Z4)

- **Procedures:** `AbortPendingWakeForRollback`, `ApplyMinerStateTransition`.
- **Setup:** a rollback departs a still-`WAKING` miner.
- **Expected:** `AbortPendingWakeForRollback` calls `ApplyMinerStateTransition(..., reason = validation_abort,
  assignment_effect_policy = STATE_ONLY_ROLLBACK)`. Under `STATE_ONLY_ROLLBACK` the hook changes miner state / residency /
  one-shot energy / census ONLY and mutates NO assignment status/custody/coverage; `AbortPendingWakeForRollback` then
  performs the canonical assignment close EXACTLY ONCE. The hook and the operation never both close the assignment.

## TV224 — ValidationAbort legally departs a WAKING miner whose head is CLOSED/detached (Z5)

- **Procedures:** `AbortPendingWakeForRollback`, `ApplyMinerStateTransition`.
- **Setup:** a miner remains `WAKING` after its assignment head became `CLOSED` / detached (e.g. an earlier self-rollback
  closed the head); the rollback item's `assignment_version_ref` equals the immutable
  `waking_origin_assignment_ref[MinerID]` set when the miner entered `WAKING`.
- **Expected:** because the wake-origin binding matches, the `T12` `ValidationAbort` legally departs the miner to `OFFLINE`
  (the head need not be live, Y4/Z5); the departure clears `waking_origin_assignment_ref[MinerID]` exactly once; the
  rollback resolves the miner.

## TV225 — A wake-origin mismatch rejects the departure (Z5)

- **Procedures:** `AbortPendingWakeForRollback`.
- **Setup:** a `WAKING` miner whose current `waking_origin_assignment_ref[MinerID]` names a DIFFERENT assignment version
  than the rollback item's `assignment_version_ref` (e.g. the miner was re-woken for another assignment).
- **Expected:** `AbortPendingWakeForRollback` returns `wake_abort_failed(reason = waking_origin_mismatch)` and departs NO
  miner; the caller returns `rollback_failed` and takes the declared `RECOVERY_INSTALL_FAILED_ABORTED` / `RoundAbort` path.
  No unrelated `WAKING` miner is silently departed.

## TV226 — Every setup-created assignment has one complete rollback item (Z6)

- **Procedures:** `PrepareParticipantsForNewRound` / `ContinueTemplateRefreshAssignmentSetup`, `RollbackParticipantSetup`
  / `RollbackTemplateRefreshSetup`.
- **Setup:** a setup creates several assignments; some wakes seat, one fails.
- **Expected:** each created assignment has exactly one complete `setup_rollback_item` in
  `setup_txn.rollback_items` — carrying `MinerID`, `AssignmentID`, `assignment_version`, `pre_wake_state`, `before_image`,
  an explicit (possibly null) `WakeEventRef`, `wake_result`, and `rollback_envelope` — appended BEFORE `StartWake`. No
  parallel-map field is absent; the rollback iterates `rollback_items` with no partial-map state.

---

## Coverage summary

| Vector | Correction | Primary procedures |
|--------|-----------|--------------------|
| TV219 | Z1 | seating procedure, `SetupRetryEvent` |
| TV220 | Z1 | `SetupRetryEvent`, targets |
| TV221 | Z2/I20 | seating procedures, `CreatePendingAssignment`, `AbortPendingWakeForRollback` |
| TV222 | Z3 | `StartWake`, `AbortPendingWakeForRollback` |
| TV223 | Z4 | `AbortPendingWakeForRollback`, `ApplyMinerStateTransition` |
| TV224 | Z5 | `AbortPendingWakeForRollback`, `ApplyMinerStateTransition` |
| TV225 | Z5 | `AbortPendingWakeForRollback` |
| TV226 | Z6 | seating procedures, setup rollbacks |

All eight vectors are specified against exact procedures and preconditions in the current
`STAGE_01_PROTOCOL_PSEUDOCODE.md` and `STAGE_01_MINER_STATE_MACHINE.md`; none assumes an unwritten guard, transition,
edge, or result name; and all preserve the A1 baseline `8.420833333 kWh`.
