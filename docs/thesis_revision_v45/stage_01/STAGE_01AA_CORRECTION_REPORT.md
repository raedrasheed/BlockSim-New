# Stage 1AA — Correction Report (retry-terminalisation & transition-policy identity lock)

Stage 1AA is a narrow, documentation-only revision of the Stage-1 formal specification of **PoCol** and the idle policy
within PoCol. It closes six defects (AA1–AA6) in the `RoundAbort` result contract, the terminalisation of seated
setup-retry records at round closure, the handling of a stale `RoundID` through the record lifecycle, the identity of a
miner-state transition with respect to its assignment-effect policy, the legality of the `STATE_ONLY_ROLLBACK` tuple, and
the explicitness of rollback-item storage. It changes only the six normative `STAGE_01_*` documents and adds twelve
`STAGE_01AA_*` deliverables. No executable source, configuration, DOCX, or PDF is touched; no experiment is run; the A1
baseline (`8.420833333 kWh`) is unchanged; and no Stage-1A–1Z historical artifact is modified.

- **Branch:** `thesis-v45-pocol-stage1aa-retry-terminalization-transition-policy-lock`
- **Parent commit:** `f224a05396ee6971de885f4401a5a69d8da300b5` (Stage 1Z)

## Corrections

### AA1 — Standardise the RoundAbort result contract

`RoundAbort` RETURNS the single canonical `round_aborted(abort_record)` (`abort_record =
abort_record(RoundID, TemplateID, reason)`), replacing the bare `abort_record`; `RoundAbort` is the sole abort producer and
no bare `abort_record` or prose alias appears anywhere. Every procedure that PROPAGATES the result to its own caller —
`SetupRetryEvent`, `PrepareParticipantsForNewRound`, `ContinueTemplateRefreshAssignmentSetup`, `TemplateRefresh`,
`FullRangeExhaustNoSolution` — lists `round_aborted` in its RETURNS union and classifies the exact
`round_aborted(abort_record)` result via `RETURN CALL RoundAbort` (no alias-by-prose). The recovery paths
(`CompleteSecurityRecovery` branch D, `ApplyRecoveryWorkAfterEpilogue`, `ApplyRecoveryAssignmentContinuationAfterEpilogue`)
instead invoke the same canonical `RoundAbort` for effect (`recovery_finalising = true`) and return their own
recovery-specific disposition after classifying the `ROUND_ABORTED` effect. RULE: a target's `round_aborted` result maps
`setup_retry_record.status = ABORTED` (NEVER `CANCELLED`). *(Audit: `STAGE_01AA_ROUND_ABORT_RESULT_AUDIT.md`; vector
TV227.)*

### AA2 — Terminalise every SEATED retry record at round closure

New procedure `CancelSetupRetriesForRound(RoundContext, closing_RoundID, cancellation_reason,
dispatch_or_run_hook_context)` is the ONE named terminaliser: for each `setup_retry_record` of `closing_RoundID`, a
`SEATED` record has its still-queued `event_ref` cancelled and becomes `status = CANCELLED`
(`target_disposition = cancellation_reason`); an `APPLYING` record is NOT overwritten — a `terminal_closure_pending` flag
is set and the executing handler's captured target result finishes it as `ABORTED` / `CANCELLED` (never `APPLIED`).
`CloseRoundAssignments` INVOKES it, and the round-closure event-cancellation list EXPLICITLY includes `SetupRetryEvent`.
No terminal or superseded round leaves a `SEATED` retry record. *(Audit:
`STAGE_01AA_RETRY_TERMINALIZATION_AUDIT.md`; vectors TV228, TV229.)*

### AA3 — Handle a stale RoundID through the record lifecycle

`SetupRetryEvent`'s guard order RESOLVES `setup_retry_records[SetupRetryID]` and verifies the payload against the
immutable record BEFORE the stale-`RoundID` check. A stale dispatch of a KNOWN `SEATED` record TERMINALISES it —
`status = SUPERSEDED` (round advanced) or `CANCELLED` (closed round), `target_disposition = setup_retry_stale_noop` —
rather than leaving it `SEATED`. Status-based idempotence still precedes the stale/terminal/target guards, so a
post-success replay is duplicate-suppressed. A malformed payload matching no record may stale-noop, but a known `SEATED`
record never remains `SEATED` after a stale dispatch. *(Audit: `STAGE_01AA_RETRY_TERMINALIZATION_AUDIT.md`; vectors
TV230, TV231.)*

### AA4 — Make assignment_effect_policy part of transition semantics (design A)

`assignment_effect_policy ∈ { EDGE_DEFAULT, STATE_ONLY_ROLLBACK }` is a FIELD of the immutable `TransitionEventID`. Two
otherwise-identical transitions with different assignment side effects are therefore DISTINCT ids, so the applied/replay
registry never aliases a state-only rollback with an edge-default transition that would have applied the edge's
assignment status change. (The alternative — deriving the policy deterministically outside the id, "design B" — is not
adopted; the policy is carried in the id so the replay guard composes with the AA5 tuple check.) *(Audit:
`STAGE_01AA_TRANSITION_POLICY_IDENTITY_AUDIT.md`; vector TV232.)*

### AA5 — Enforce the legal STATE_ONLY_ROLLBACK tuple

`ApplyMinerStateTransition` gains an executable guard: `STATE_ONLY_ROLLBACK` is legal IFF `old_state = WAKING` AND
`new_state = OFFLINE` AND `reason = validation_abort` AND `assignment_ref` is exact and non-null AND
`waking_origin_assignment_ref[MinerID] = assignment_ref`; any other use records
`transition_rejection_log(..., illegal_state_only_rollback_tuple)` and returns `illegal_transition(TransitionEventID)`
with NO state/residency/energy/census/assignment mutation. Every non-rollback caller uses the signature default
`EDGE_DEFAULT`, so no caller can use `STATE_ONLY_ROLLBACK` on `T5` / `T21` / any other edge to bypass assignment effects.
*(Audit: `STAGE_01AA_STATE_ONLY_POLICY_GUARD_AUDIT.md`; vectors TV233, TV234.)*

### AA6 — Make rollback-item updates explicit and keyed

`setup_rollback_item` gains a `RollbackItemID`; `setup_transaction = { rollback_envelope, rollback_items :
map RollbackItemID -> setup_rollback_item }`. Each item is CREATED with `WakeEventRef = null` and
`wake_result = NOT_ATTEMPTED` and ADDED under its key BEFORE `StartWake`; after `StartWake` the STORED record is UPDATED
EXPLICITLY by key (`rollback_items[RollbackItemID].wake_result <- wr` and `.WakeEventRef <- actual | returned | null`).
Rollback CONSUMES the stored keyed record (iterating deterministically by `RollbackItemID`), never an unproven alias to a
local variable. Applies to participant setup (`PrepareParticipantsForNewRound`) and template-refresh setup
(`ContinueTemplateRefreshAssignmentSetup`). *(Audit: `STAGE_01AA_ROLLBACK_ITEM_STORAGE_AUDIT.md`; vector TV235.)*

## Deliverables (12 new `STAGE_01AA_*` files)

1. `STAGE_01AA_CORRECTION_REPORT.md` (this file)
2. `STAGE_01AA_ROUND_ABORT_RESULT_AUDIT.md` (AA1)
3. `STAGE_01AA_RETRY_TERMINALIZATION_AUDIT.md` (AA2/AA3)
4. `STAGE_01AA_TRANSITION_POLICY_IDENTITY_AUDIT.md` (AA4)
5. `STAGE_01AA_STATE_ONLY_POLICY_GUARD_AUDIT.md` (AA5)
6. `STAGE_01AA_ROLLBACK_ITEM_STORAGE_AUDIT.md` (AA6)
7. `STAGE_01AA_PROCEDURE_SIGNATURE_CALL_AUDIT.md`
8. `STAGE_01AA_PROCEDURE_CALL_GRAPH.md`
9. `STAGE_01AA_SEMANTIC_TEST_VECTORS.md` (TV227–TV235)
10. `STAGE_01AA_SUPERSESSION_REGISTER.md`
11. `STAGE_01AA_CROSS_DOCUMENT_AUDIT.md`
12. `STAGE_01AA_CHECKSUM_MANIFEST.sha256`

## Modified normative documents (6)

`STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_MINER_STATE_MACHINE.md` (adds §3.5), `STAGE_01_ROUND_STATE_MACHINE.md`
(adds §3.10e), `STAGE_01_INVARIANT_CATALOGUE.md` (I16 Stage-1AA clause), `STAGE_01_TERMINOLOGY.md` (Stage-1AA addendum),
`STAGE_01_TRACEABILITY_MATRIX.csv` (rows R191–R197).

## Discipline

Documentation-only; the algorithm remains **PoCol** and the mechanism remains the idle policy within PoCol; the A1
baseline `8.420833333 kWh` is unchanged; the call graph resolves with 86 callables (85 procedures + 1 function) and 0
dangling references (Stage 1AA adds the one new procedure `CancelSetupRetriesForRound`, defined once and called once from
`CloseRoundAssignments`); and Stage 2 is not begun.
