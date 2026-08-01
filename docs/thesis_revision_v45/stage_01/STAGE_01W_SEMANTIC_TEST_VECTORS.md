# Stage 1W — Semantic Test Vectors (TV186–TV197)

Paper test vectors for the legal-rollback & plan-transaction lock (W1–W8). Each vector names the EXACT procedures,
preconditions, dispositions, and transitions in `STAGE_01_PROTOCOL_PSEUDOCODE.md`; no guard, transition, edge,
result, or rollback is assumed that is not in the pseudocode. The protocol name remains **PoCol**; the mechanism is
**the idle policy within PoCol**; the A1 baseline (`8.420833333 kWh`) is preserved by every vector (each is a
control-flow / rollback / transaction / result-contract check, never a change to how time or energy is counted).

Each vector lists **Setup**, **Steps** (the pseudocode path exercised), and **Expected** (the observable disposition
that must hold).

---

## TV186 — Rollback receives an explicit complete rollback envelope (W1)

**Setup.** `PrepareParticipantsForNewRound` runs; it initialised `participant_setup_txn` with
`rollback_envelope = dispatch_envelope`. A setup failure occurs.
**Steps.**
1. `RollbackParticipantSetup(RoundContext, participant_setup_txn)` runs; every `ApplyMinerStateTransition` it issues
   passes `transition_envelope = setup_txn.rollback_envelope`.
2. `setup_txn.rollback_envelope` carries all five identity fields `{ envelope_namespace, event_time, delta_cycle,
   event_seq, hook_id }`.
**Expected.** No angle-bracket placeholder (`<the setup dispatch_envelope>`), ambient envelope, or undeclared identity
is used; every rollback transition receives a COMPLETE `transition_envelope`. A1 preserved.

## TV187 — A REGISTERED→WAKING miner is rolled back with only legal edges (W2)

**Setup.** In participant setup, a REGISTERED miner `m` reached `WAKING` (its `StartWake` returned `wake_seated`), then
a later miner's setup fails.
**Steps.**
1. `RollbackParticipantSetup` cancels the captured wake, then departs `m` via
   `ApplyMinerStateTransition(m, WAKING, OFFLINE, ...)` — the LEGAL `T12` edge — and sets `rolled_to_offline <- true`.
2. No `ApplyMinerStateTransition(m, WAKING, REGISTERED, ...)` is ever issued (that edge is absent from the miner state
   machine).
**Expected.** `m` departs `WAKING` only via `T12` (`WAKING -> OFFLINE`); the prohibited `WAKING -> REGISTERED` edge is
never attempted; after rollback no participant is `WAKING`. A1 preserved.

## TV188 — A LOW_POWER_LISTEN→WAKING miner is rolled back without WAKING→LOW_POWER_LISTEN (W2)

**Setup.** In `TemplateRefresh`, a `LOW_POWER_LISTEN` miner `m` reached `WAKING` (T10 → `wake_seated`), then the refresh
setup fails.
**Steps.**
1. `RollbackTemplateRefreshSetup` cancels the captured wake and departs `m` via
   `ApplyMinerStateTransition(m, WAKING, OFFLINE, ...)` (`T12`), setting `rolled_to_offline <- true`.
2. No `ApplyMinerStateTransition(m, WAKING, LOW_POWER_LISTEN, ...)` is issued.
**Expected.** The prohibited `WAKING -> LOW_POWER_LISTEN` edge is never attempted; `m` is departed legally to `OFFLINE`.
A1 preserved.

## TV189 — A TemplateRefresh StartWake failure rolls back before CompleteAssignmentPhase (W3)

**Setup.** `TemplateRefresh` initialised `refresh_setup_txn` before its loop. One miner's `StartWake` returns a
non-`wake_seated` disposition.
**Steps.**
1. The loop sets `refresh_setup_error <- wr` and BREAKs (mints no further work).
2. Because `refresh_setup_error != null`, `TemplateRefresh` does NOT call `CompleteAssignmentPhase`; it calls
   `RollbackTemplateRefreshSetup(RoundContext, refresh_setup_txn)` and then takes the W8 liveness path (bounded
   `SetupRetryEvent` or `RoundAbort`).
**Expected.** `refresh_setup_error` is set, `CompleteAssignmentPhase` is not called, and the named rollback + declared
liveness path executes; `refresh_setup_txn` was populated by explicit in-loop statements, not reconstructed from prose.
A1 preserved.

## TV190 — RangeAssignFromPlan commits exactly the spec and returns one AssignmentID + one WakeEventRef (W5)

**Setup.** `CommitRecoveryAssignmentPlan` calls `RangeAssignFromPlan` for an ORIGINAL spec
`{ MinerID = m, range = r, origin = ORIGINAL, source_assignment = null, reassignment_reason = null }`.
**Steps.**
1. `RangeAssignFromPlan` performs NO `SELECT`; `CreatePendingAssignment(m, r, ORIGINAL, ...)` returns
   `assignment_created(a)`.
2. It asserts `MinerID(a) = m AND range(a) = r AND origin(a) = ORIGINAL AND source_assignment_ref(a) = null`, seats ONE
   `StartWake`, and returns `range_assigned(AssignmentID(a), WakeEventRef, resulting_state = WAKING)`.
**Expected.** Exactly `m`/`r` are committed (no SELECT), and exactly one `AssignmentID` and one `WakeEventRef` are
returned. A1 preserved.

## TV191 — RangeReassignFromPlan commits the validated suffix and provenance without SELECT (W5)

**Setup.** `CommitRecoveryAssignmentPlan` calls `RangeReassignFromPlan` for a REASSIGNED spec
`{ MinerID = m, range = accepted-unsearched-suffix S, origin = REASSIGNED, source_assignment = s,
reassignment_reason = security_recovery }`.
**Steps.**
1. `RangeReassignFromPlan` performs NO `SELECT`; `CreatePendingAssignment(m, S, REASSIGNED, source_assignment = s, ...)`
   returns `assignment_created(a)`.
2. It asserts the committed object equals the spec, seats ONE `StartWake`, updates the coverage ledger, and returns
   `range_reassigned(provenance(a), AssignmentID(a), WakeEventRef)`.
**Expected.** The validated source suffix and provenance are committed with no independent selection; the I9 provenance
is carried in the result. A1 preserved.

## TV192 — CommitRecoveryAssignmentPlan consumes a success range result with no second wake (W4)

**Setup.** A REDISTRIBUTION spec commits successfully: the plan-bound constructor returns
`range_reassigned(prov, aid, wref)`.
**Steps.**
1. `CommitRecoveryAssignmentPlan` adds `rr.AssignmentID` to `created_assignments` and `rr.WakeEventRef` to
   `created_events`, then `CONTINUE`s to the next spec.
2. It does NOT execute any `FOR EACH wake in spec.required_wake_operations: StartWake(...)` loop (removed).
**Expected.** The returned `AssignmentID`/`WakeEventRef` are recorded and NO second `StartWake` is issued — exactly one
`WakeCompleteEvent` per committed activation. A1 preserved.

## TV193 — A range wake failure follows the declared failure branch with coherent rollback metadata (W4)

**Setup.** A REDISTRIBUTION spec's plan-bound constructor returns `range_reassign_wake_failed(reason, aid)` after an
earlier spec already committed (so `created_assignments`/`created_events` are non-empty).
**Steps.**
1. `CommitRecoveryAssignmentPlan` matches the declared `range_reassign_wake_failed` branch (never an undefined
   `creation_failed`).
2. It sets `plan.rollback_metadata <- rollback_record(RecoveryInstallID, created_assignments, created_events)` and
   returns `install_failed_after_mutation(reason = rr.reason, plan.rollback_metadata)`.
**Expected.** The declared failure branch is taken and the rollback metadata contains the ACTUAL references of the
earlier committed specs; the failing spec already self-rolled-back its own head. A1 preserved.

## TV194 — ApplyMinerStateTransition result governs whether StartWake keeps the event (W6)

**Setup.** `StartWake` seated its `WakeCompleteEvent` and calls `ApplyMinerStateTransition(MinerID, from_state, WAKING, ...)`.
**Steps.**
1. If the call returns `transition_applied(TransitionEventID)`: `StartWake` publishes the `WakeEventRef` and returns
   `wake_seated(...)`.
2. If it returns any other declared result (`duplicate_suppressed` / `illegal_stale_source` / `illegal_transition`):
   `StartWake` cancels the seated `WakeCompleteEvent` (if still pending) and returns
   `wake_transition_failed_after_seat(reason = tr, WakeEventRef)`, leaving the miner in `from_state`.
**Expected.** The wake is retained iff the result is `transition_applied`; every other declared result cancels the
event; no miner is left `WAKING` without a live `WakeCompleteEvent`. A1 preserved.

## TV195 — A CreatePendingAssignment failure creates nothing (W7)

**Setup.** A caller (e.g. `PrepareParticipantsForNewRound`, `RangeAssignFromPlan`, or `ReserveActivateFromPlan`) calls
`CreatePendingAssignment`, whose executable I1/custody/coverage/provenance guard fails.
**Steps.**
1. `CreatePendingAssignment` returns `assignment_creation_failed(reason)` and creates NO assignment, ledger entry, or
   lineage.
2. The caller branches on the result BEFORE any `AssignmentID` access: it sets no lease fields, seats no `StartWake`,
   and adds no `AssignmentID` to any transaction record (it sets its `*_setup_error` / returns a `*_creation_failed`
   disposition).
**Expected.** No lease field, `AssignmentID`, wake, or transaction entry exists for the non-created object. A1 preserved.

## TV196 — Rollback that routes miners OFFLINE seats no retry and aborts (W8)

**Setup.** A participant setup fails after at least one miner reached `WAKING`; `RollbackParticipantSetup` returns
`rollback_completed(rolled_to_offline = true)`.
**Steps.**
1. `PrepareParticipantsForNewRound` observes `rb.rolled_to_offline = true` and does NOT seat a `SetupRetryEvent`.
2. It returns `RoundAbort(RoundContext, reason = participant_setup_failed(setup_reason), ...)`.
**Expected.** No `SetupRetryEvent` is seated from the state-incompatible (OFFLINE) rollback; `RoundAbort` executes.
A1 preserved.

## TV197 — A bounded legal retry is idempotent and generation-bounded (W8)

**Setup.** A setup failed BEFORE any miner reached `WAKING` (e.g. the first `CreatePendingAssignment` failed), so
`RollbackParticipantSetup` returned `rollback_completed(rolled_to_offline = false)`; the retry budget is not exhausted.
A `SetupRetryEvent` with `SetupRetryID = (RoundID, PARTICIPANT_SETUP, g)` is seated, then re-dispatched twice.
**Steps.**
1. First dispatch: `SetupRetryEvent` passes the stale guard, `SetupRetryID ∉ applied_setup_retry_ids`,
   `g <= maximum_setup_retries`, every eligible participant is re-enlistable → it adds `SetupRetryID` to
   `applied_setup_retry_ids` and re-invokes `PrepareParticipantsForNewRound`.
2. Second dispatch of the SAME `SetupRetryID`: `SetupRetryID ∈ applied_setup_retry_ids` → returns
   `setup_retry_duplicate_suppressed(SetupRetryID)` (the setup does not run twice).
3. A retry whose `setup_retry_generation > maximum_setup_retries` returns `setup_retry_exhausted` (and the seating side
   would have aborted rather than seat it).
**Expected.** The retry runs at most once per `SetupRetryID` (idempotent) and the generation can never exceed
`maximum_setup_retries` (bounded). A1 preserved.

---

## Coverage map

| Vector | Correction | Primary procedures exercised |
|--------|-----------|------------------------------|
| TV186  | W1        | `PrepareParticipantsForNewRound`, `RollbackParticipantSetup` |
| TV187  | W2        | `RollbackParticipantSetup`, `ApplyMinerStateTransition` (T12) |
| TV188  | W2        | `TemplateRefresh`, `RollbackTemplateRefreshSetup`, `ApplyMinerStateTransition` (T12) |
| TV189  | W3        | `TemplateRefresh`, `RollbackTemplateRefreshSetup` |
| TV190  | W5        | `RangeAssignFromPlan`, `CommitRecoveryAssignmentPlan` |
| TV191  | W5        | `RangeReassignFromPlan`, `CommitRecoveryAssignmentPlan` |
| TV192  | W4        | `CommitRecoveryAssignmentPlan`, `RangeReassignFromPlan` |
| TV193  | W4        | `CommitRecoveryAssignmentPlan`, `RollbackRecoveryAssignmentPlan` |
| TV194  | W6        | `StartWake`, `ApplyMinerStateTransition` |
| TV195  | W7        | `CreatePendingAssignment` (+ every caller) |
| TV196  | W8        | `RollbackParticipantSetup`, `PrepareParticipantsForNewRound`, `RoundAbort` |
| TV197  | W8        | `SetupRetryEvent`, `PrepareParticipantsForNewRound` |

All twelve vectors are control-flow / rollback / transaction / result-contract checks over named procedures in
`STAGE_01_PROTOCOL_PSEUDOCODE.md`; none alters the energy or time accounting, so the A1 baseline `8.420833333 kWh` is
preserved by every vector.
