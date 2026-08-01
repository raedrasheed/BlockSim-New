# Stage 1W — Correction Report (Legal-Rollback & Plan-Transaction Lock)

**Scope.** A documentation-only revision of the Stage-1 formal specification of PoCol ("the idle policy within PoCol")
that closes the executable-contract gaps the Stage-1V rollback and plan-commit paths left open: placeholder rollback
envelopes, illegal miner-state rollback edges, a prose-reconstructed template-refresh transaction, a double-wake in
the recovery-plan commit, missing plan-bound range constructors, mismatched transition/creation result contracts, and
an unbounded/state-incompatible setup retry. It corrects eight defects (W1–W8). This stage changes only the normative
Stage-1 documents; it does NOT change how time or energy are counted, so the A1 baseline (`8.420833333 kWh`) is
preserved.

**Branch.** `thesis-v45-pocol-stage1w-legal-rollback-plan-transaction-lock` (parent `e8c9649`).

---

## W1 — Remove all free / placeholder rollback envelopes

**Defect.** `RollbackParticipantSetup` and `RollbackTemplateRefreshSetup` transitioned with
`transition_envelope = <the setup dispatch_envelope>` / `<the refresh dispatch_envelope>` — angle-bracket placeholders
the procedures never received.

**Correction.** The setup transaction carries an IMMUTABLE `rollback_envelope` field set at creation to the setup's own
`dispatch_envelope` — a COMPLETE transition envelope `{ envelope_namespace, event_time, delta_cycle, event_seq,
hook_id }`. Both rollback procedures transition with `transition_envelope = setup_txn.rollback_envelope`. No
placeholder, ambient envelope, or undeclared identity remains.

**Where.** `PrepareParticipantsForNewRound` / `TemplateRefresh` (txn init with `rollback_envelope`);
`RollbackParticipantSetup` / `RollbackTemplateRefreshSetup` (use `setup_txn.rollback_envelope`).

## W2 — Use only legal miner-state edges during rollback

**Defect.** The V8 rollback issued `WAKING -> REGISTERED` / `WAKING -> RESERVE` / `WAKING -> LOW_POWER_LISTEN` — edges
absent from the authoritative miner state machine.

**Correction (Option 1, abort-oriented).** A participant left `WAKING` is departed to `OFFLINE` via the LEGAL `T12`
edge only (the sole legal `WAKING` departure besides `T5`/`T21`); the rollback reports `rolled_to_offline`, and a
rollback that routed any participant to `OFFLINE` forces a `RoundAbort` (no retry from an incompatible state). No
illegal edge is ever passed to `ApplyMinerStateTransition`.

**Where.** `RollbackParticipantSetup` / `RollbackTemplateRefreshSetup` (T12 + `rolled_to_offline`);
`PrepareParticipantsForNewRound` / `TemplateRefresh` (abort on `rolled_to_offline`).

## W3 — Make template-refresh setup a real transaction

**Defect.** `TemplateRefresh` constructed `refresh_setup_txn` AFTER the miner loop from prose ("the ACTUAL
WakeEventRefs returned") and merely `RECORD`ed a wake failure while continuing.

**Correction.** `refresh_setup_txn` is initialised BEFORE the loop (with the W1 `rollback_envelope`) and populated by
EXPLICIT statements inside the loop (created `AssignmentID`, prior miner state, `StartWake` `WakeEventRef`); on any
`CreatePendingAssignment`/`StartWake` failure it sets `refresh_setup_error`, does NOT call `CompleteAssignmentPhase`,
invokes `RollbackTemplateRefreshSetup`, then takes the declared retry/abort path.

**Where.** `TemplateRefresh` (init-before-loop, in-loop capture, fail-fast rollback + liveness).

## W4 — Consume structured range results exactly

**Defect.** `CommitRecoveryAssignmentPlan`'s REDISTRIBUTION branch tested an undefined `creation_failed`, treated the
constructor return as an assignment, and then ran a `required_wake_operations` `StartWake` loop over the same
assignment — a double wake.

**Correction.** The branch calls the plan-bound range constructor once per spec, consumes the structured result — on
success appends the returned `AssignmentID` + `WakeEventRef` and does NOT wake again; on failure branches on the
DECLARED results (`range_*_creation_failed`, `range_*_wake_failed`). Exactly one `WakeCompleteEvent` per committed
activation.

**Where.** `CommitRecoveryAssignmentPlan` (REDISTRIBUTION branch); `PrepareRecoveryAssignmentPlan` (spec fields; no
separate wake loop).

## W5 — Add plan-bound range constructors

**Defect.** Redistribution went through an abstract `<the spec's constructor: RangeReassign / RangeAssign>` that could
re-`SELECT`.

**Correction.** New named procedures `RangeAssignFromPlan` and `RangeReassignFromPlan` take the EXACT validated spec
fields (`MinerID`, `range`, `assignment_origin`, `source_assignment`, `reassignment_reason`, `lease_duration`,
`scheduling_context`), perform NO `SELECT`, and assert the committed object equals the spec. The ordinary
`RangeAssign`/`RangeReassign` keep policy `SELECT` and delegate; the recovery-plan commit path calls ONLY the
plan-bound constructors.

**Where.** `RangeAssignFromPlan`, `RangeReassignFromPlan` (new); `RangeAssign`, `RangeReassign` (delegate);
`CommitRecoveryAssignmentPlan` (calls plan-bound).

## W6 — Align ApplyMinerStateTransition returns with StartWake

**Defect.** `ApplyMinerStateTransition` declared `RETURNS: transition_record`, but `StartWake` tested
`IF tr != transition_applied` — a name the hook never returned.

**Correction.** `ApplyMinerStateTransition` returns exactly one of `transition_applied(TransitionEventID)` |
`duplicate_suppressed(TransitionEventID)` | `illegal_stale_source(TransitionEventID)` |
`illegal_transition(TransitionEventID)`; the `transition_record` name is withdrawn. `StartWake` retains the seated
event and returns `wake_seated` ONLY on `transition_applied`, cancelling the event on any other result.

**Where.** `ApplyMinerStateTransition` (four-variant union); `StartWake` (`IF tr is NOT transition_applied(teid)`).

## W7 — Handle assignment-constructor failure before recording

**Defect.** `CreatePendingAssignment` returned a bare `A`, yet `ReserveActivateFromPlan` (and the commit path) already
tested an undefined `creation_failed`; some callers read `AssignmentID` assuming success.

**Correction.** `CreatePendingAssignment` returns `assignment_created(assignment)` | `assignment_creation_failed(reason)`
(an executable I1/custody/coverage/provenance guard rejects with the failure result; nothing partial is built). Every
caller branches on the result BEFORE reading `AssignmentID`, setting lease fields, or adding the object to a
transaction record.

**Where.** `CreatePendingAssignment` (result union + guard); callers `PrepareParticipantsForNewRound`,
`TemplateRefresh`, `RangeAssignFromPlan`, `RangeReassignFromPlan`, `ReserveActivateFromPlan`,
`AdversarialParticipationChangeEvent`.

## W8 — Make setup retry state-compatible and bounded

**Defect.** The V8 `SetupRetryEvent` was seated whenever "a retry is warranted (bounded by the retry policy)" with no
`SetupRetryID`, no idempotence, no explicit bound, and no state-compatibility check — it could retry from an
incompatible `OFFLINE` state.

**Correction.** Registries `SetupRetryID = (RoundID, setup_kind, setup_retry_generation)`, per-round
`setup_retry_generation`, config `maximum_setup_retries`, and per-run `applied_setup_retry_ids`. A retry is seated only
when rollback left every eligible participant re-enlistable (`rolled_to_offline = false`), the generation is within
`maximum_setup_retries`, and the strictly-later target is within horizon; otherwise `RoundAbort`. `SetupRetryEvent` is
idempotent (duplicate `SetupRetryID` suppressed) and bounded (generation `<= maximum_setup_retries`), and aborts if any
eligible participant is not re-enlistable.

**Where.** `RunInitialise`/`RunContext` (`applied_setup_retry_ids`, `maximum_setup_retries`); `RoundInitialise`
(`setup_retry_generation`); `PrepareParticipantsForNewRound` / `TemplateRefresh` (seat decision); `SetupRetryEvent`
(idempotent + bounded + state-compatible).

---

## Summary of pseudocode changes

| Procedure | Status | Corrections |
|-----------|--------|-------------|
| `RangeAssignFromPlan` | new | W5, W7 |
| `RangeReassignFromPlan` | new | W5, W7 |
| `ApplyMinerStateTransition` | revised | W6 |
| `CreatePendingAssignment` | revised | W7 |
| `StartWake` | revised | W6 |
| `RangeAssign` | revised | W5 |
| `RangeReassign` | revised | W5 |
| `CommitRecoveryAssignmentPlan` | revised | W4, W5, W7 |
| `PrepareRecoveryAssignmentPlan` | revised | W4, W5 |
| `ReserveActivateFromPlan` | revised | W7 |
| `PrepareParticipantsForNewRound` | revised | W1, W2, W7, W8 |
| `TemplateRefresh` | revised | W1, W2, W3, W7, W8 |
| `RollbackParticipantSetup` | revised | W1, W2, W8 |
| `RollbackTemplateRefreshSetup` | revised | W1, W2, W8 |
| `SetupRetryEvent` | revised | W8 |
| `AdversarialParticipationChangeEvent` | revised | W7 |
| `RunInitialise` / `RunContext` | revised | W8 |
| `RoundInitialise` | revised | W8 |

The procedure inventory grows from 81 (Stage 1V) to **83** defined procedures/functions (adds `RangeAssignFromPlan`,
`RangeReassignFromPlan`). The call graph resolves with **zero** dangling references (see
`STAGE_01W_PROCEDURE_CALL_GRAPH.md`).

## Normative documents updated

- `STAGE_01_PROTOCOL_PSEUDOCODE.md` — the W1–W8 procedure edits above.
- `STAGE_01_ROUND_STATE_MACHINE.md` — §3.10a Stage-1W addendum (eight W-blocks).
- `STAGE_01_INVARIANT_CATALOGUE.md` — I16 W1/W2/W6/W7/W8 clauses.
- `STAGE_01_TERMINOLOGY.md` — Stage-1W terminology addendum.
- `STAGE_01_TRACEABILITY_MATRIX.csv` — rows R160–R168 (W1–W8 + the TV186–TV197 block).

## Test vectors

`STAGE_01W_SEMANTIC_TEST_VECTORS.md` defines TV186–TV197, one or more per correction; each names the exact procedures
and expected dispositions and preserves the A1 baseline.
