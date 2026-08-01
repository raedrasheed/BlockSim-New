# Stage 1AA — Semantic Test Vectors (TV227–TV235)

These blocking paper test vectors exercise corrections AA1–AA6 of the retry-terminalisation and transition-policy
identity lock. Each vector names the EXACT procedures and preconditions it drives, states the required outcome, and
asserts NO behaviour that is not written in `STAGE_01_PROTOCOL_PSEUDOCODE.md` / `STAGE_01_MINER_STATE_MACHINE.md`
(no assumed guard, transition, edge, or result name). Every vector preserves the A1 baseline (`8.420833333 kWh`). The
algorithm is **PoCol** and the mechanism under test is the idle policy within PoCol.

Terminology: `RoundAbort` returns the single canonical `round_aborted(abort_record)` (AA1); `CancelSetupRetriesForRound`
is the named terminaliser invoked by `CloseRoundAssignments` (AA2); `terminal_closure_pending` is the `APPLYING`-record
closure flag (AA2); `SetupRetryStatus ∈ { SEATED, APPLYING, APPLIED, SUPERSEDED, CANCELLED, ABORTED }`;
`assignment_effect_policy ∈ { EDGE_DEFAULT, STATE_ONLY_ROLLBACK }` is a field of `TransitionEventID` (AA4);
`waking_origin_assignment_ref[MinerID]` is the wake-origin binding; `T12` is the authoritative `WAKING -> OFFLINE` edge
with the `ValidationAbort` trigger; `setup_transaction.rollback_items` is keyed by `RollbackItemID` (AA6).

---

## TV227 — RoundAbort returns the canonical result and a target abort maps a retry to ABORTED (AA1)

- **Procedures:** `RoundAbort`, `SetupRetryEvent`, `PrepareParticipantsForNewRound` /
  `ContinueTemplateRefreshAssignmentSetup`.
- **Setup:** a `SEATED` retry's first dispatch flips `SEATED -> APPLYING` and runs its kind-specific target; the target
  reaches a declared abort and `RETURN CALL RoundAbort(...)`.
- **Expected:** `RoundAbort` returns exactly `round_aborted(abort_record)` (`abort_record(RoundID, TemplateID, reason)`);
  `SetupRetryEvent` captures `disp = round_aborted(abort_record)` and classifies `rec.status = ABORTED` (never `CANCELLED`)
  with `rec.target_disposition = disp`. Every direct propagator in the chain (`SetupRetryEvent`,
  `PrepareParticipantsForNewRound`, `ContinueTemplateRefreshAssignmentSetup`, `TemplateRefresh`,
  `FullRangeExhaustNoSolution`) lists `round_aborted` in its RETURNS union and matches the exact result name — no bare
  `abort_record` and no prose alias. (The recovery paths call the same canonical `RoundAbort` for effect and return their
  own recovery-specific disposition.)

## TV228 — Round closure cancels a SEATED retry record's queued event and sets CANCELLED (AA2)

- **Procedures:** `CloseRoundAssignments`, `CancelSetupRetriesForRound`.
- **Setup:** a round has a `SEATED` `setup_retry_record` with a still-queued `SetupRetryEvent`; the round is then closed
  (`ROUND_ACCEPTED` or `ROUND_ABORTED`).
- **Expected:** `CloseRoundAssignments` lists `SetupRetryEvent` in its event-cancellation set (cancelling the queued
  dispatch) and invokes `CancelSetupRetriesForRound(RoundContext, closing_RoundID = RoundID, cancellation_reason =
  round_closed(disposition), ...)`. For the `SEATED` record, `CancelSetupRetriesForRound` cancels its `event_ref` if still
  pending and sets `status = CANCELLED`, `target_disposition = round_closed(disposition)`. After closure NO
  setup-retry record of that round remains `SEATED`.

## TV229 — An APPLYING retry at closure is flagged and finishes terminal, never APPLIED (AA2)

- **Procedures:** `CancelSetupRetriesForRound`, `SetupRetryEvent`, `CloseRoundAssignments`.
- **Setup:** a retry record is `APPLYING` (its `SetupRetryEvent` handler is mid-flight executing its target) when the
  round closes and `CancelSetupRetriesForRound` runs for that round.
- **Expected:** `CancelSetupRetriesForRound` does NOT overwrite the `APPLYING` record; it sets
  `terminal_closure_pending = true`. When the executing handler's captured target result returns, `SetupRetryEvent`'s
  classification honours the flag: `rec.status = ABORTED` if the target result is `round_aborted(abort_record)`, else
  `rec.status = CANCELLED`. The record is NEVER left `APPLYING` and NEVER classified `APPLIED` under a closed round.

## TV230 — A stale dispatch for an advanced round terminalises a known SEATED record as SUPERSEDED (AA3)

- **Procedures:** `SetupRetryEvent`.
- **Setup:** a `SEATED` record exists for RoundID `r1`; the current round has advanced (`RoundID_current != r1`); a valid
  `SetupRetryEvent` for that exact `SetupRetryID` and matching payload dispatches.
- **Expected:** `SetupRetryEvent` resolves the record and verifies the payload BEFORE the stale-`RoundID` check; because
  the status is still `SEATED` it is not duplicate-suppressed; the stale-`RoundID` check then sets `rec.status =
  SUPERSEDED` and `rec.target_disposition = setup_retry_stale_noop` and returns `setup_retry_stale_noop(SetupRetryID)`.
  The known record does NOT remain `SEATED`.

## TV231 — A stale dispatch for a closed round terminalises a known SEATED record as CANCELLED (AA3)

- **Procedures:** `SetupRetryEvent`.
- **Setup:** a `SEATED` record for the current `RoundID` whose `round_state ∈ { ROUND_ACCEPTED, ROUND_ABORTED }`
  (terminal); a valid `SetupRetryEvent` with matching payload dispatches.
- **Expected:** after record resolution + payload match + the non-SEATED idempotence check (status is `SEATED`, so it
  proceeds), the terminal-round branch sets `rec.status = CANCELLED`, `rec.target_disposition =
  setup_retry_terminal_stale_noop`, and returns `setup_retry_terminal_stale_noop(SetupRetryID)`. The record is
  terminalised, not left `SEATED`. (A malformed payload matching no record instead returns `setup_retry_stale_noop`
  without terminalising any record.)

## TV232 — Two transitions differing only in assignment_effect_policy are distinct replay ids (AA4)

- **Procedures:** `ApplyMinerStateTransition`.
- **Setup:** consider a `WAKING -> OFFLINE` transition for one miner with a fixed dispatch envelope, reason, and exact
  `assignment_ref`. One form carries `assignment_effect_policy = EDGE_DEFAULT`; the other carries `STATE_ONLY_ROLLBACK`.
- **Expected:** `TransitionEventID` includes `assignment_effect_policy` as a field, so the two forms are DISTINCT ids.
  Registering (or replaying) one does NOT duplicate-suppress the other via the applied-transition registry; the registry
  never aliases a state-only rollback with an edge-default transition that would have applied the edge's assignment
  side effect.

## TV233 — STATE_ONLY_ROLLBACK on a non-rollback edge is rejected with no mutation (AA5)

- **Procedures:** `ApplyMinerStateTransition`.
- **Setup:** a caller invokes `ApplyMinerStateTransition` with `assignment_effect_policy = STATE_ONLY_ROLLBACK` on an
  edge that is NOT the rollback tuple — e.g. a non-`WAKING` `old_state`, a `new_state` other than `OFFLINE`, a
  `reason` other than `validation_abort`, or a null/inexact `assignment_ref`.
- **Expected:** the AA5 legal-tuple guard fails; `ApplyMinerStateTransition` records
  `transition_rejection_log(..., illegal_state_only_rollback_tuple)` and returns `illegal_transition(TransitionEventID)`
  with NO state / residency / one-shot energy / census / assignment mutation and no registry entry. No caller can use
  `STATE_ONLY_ROLLBACK` on `T5` / `T21` / any other edge to bypass its assignment effects.

## TV234 — STATE_ONLY_ROLLBACK with a wake-origin mismatch is rejected with no mutation (AA5)

- **Procedures:** `ApplyMinerStateTransition`, `AbortPendingWakeForRollback`.
- **Setup:** a `WAKING -> OFFLINE` / `validation_abort` transition with an exact non-null `assignment_ref`, but
  `waking_origin_assignment_ref[MinerID]` does NOT equal that `assignment_ref` (the miner's current WAKING residency was
  initiated by a different assignment version).
- **Expected:** the AA5 tuple's `waking_origin_assignment_ref[MinerID] = assignment_ref` conjunct fails, so
  `ApplyMinerStateTransition` returns `illegal_transition` with no mutation. (`AbortPendingWakeForRollback` additionally
  returns `wake_abort_failed(reason = waking_origin_mismatch)` from its own pre-call check and departs no miner.) No
  unrelated `WAKING` miner is departed.

## TV235 — A keyed rollback item is created NOT_ATTEMPTED and updated by key; rollback consumes the stored record (AA6)

- **Procedures:** `PrepareParticipantsForNewRound` / `ContinueTemplateRefreshAssignmentSetup`, `StartWake`,
  `RollbackParticipantSetup` / `RollbackTemplateRefreshSetup`.
- **Setup:** a setup creates an assignment; it builds a `setup_rollback_item` with an explicit `RollbackItemID`,
  `WakeEventRef = null`, `wake_result = NOT_ATTEMPTED`, and adds it under its key BEFORE `StartWake`. `StartWake` then
  returns one of `wake_seated` / `wake_transition_failed_after_seat` / `wake_schedule_failed_before_transition`.
- **Expected:** after `StartWake`, the STORED record is updated EXPLICITLY by key —
  `rollback_items[RollbackItemID].wake_result <- wr` and `.WakeEventRef <- actual ref | returned already-cancelled ref |
  null` — never a local-variable alias. On rollback, `RollbackParticipantSetup` / `RollbackTemplateRefreshSetup` iterate
  `rollback_items` deterministically by `RollbackItemID` and consume the stored record (its persisted post-`StartWake`
  `wake_result` / `WakeEventRef`), so no rollback reads a stale unproven alias.

---

## Coverage summary

| Vector | Correction | Primary procedures |
|--------|-----------|--------------------|
| TV227 | AA1 | `RoundAbort`, `SetupRetryEvent`, targets |
| TV228 | AA2 | `CloseRoundAssignments`, `CancelSetupRetriesForRound` |
| TV229 | AA2 | `CancelSetupRetriesForRound`, `SetupRetryEvent` |
| TV230 | AA3 | `SetupRetryEvent` |
| TV231 | AA3 | `SetupRetryEvent` |
| TV232 | AA4 | `ApplyMinerStateTransition` |
| TV233 | AA5 | `ApplyMinerStateTransition` |
| TV234 | AA5 | `ApplyMinerStateTransition`, `AbortPendingWakeForRollback` |
| TV235 | AA6 | seating procedures, `StartWake`, setup rollbacks |

All nine vectors are specified against exact procedures and preconditions in the current
`STAGE_01_PROTOCOL_PSEUDOCODE.md` and `STAGE_01_MINER_STATE_MACHINE.md`; none assumes an unwritten guard, transition,
edge, or result name; and all preserve the A1 baseline `8.420833333 kWh`.
