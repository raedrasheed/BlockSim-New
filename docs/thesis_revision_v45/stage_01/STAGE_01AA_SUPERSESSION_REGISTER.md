# Stage 1AA — Supersession Register

Stage 1AA supersedes specific Stage-1Z statements about the `RoundAbort` result contract, the terminalisation of seated
setup-retry records, the stale-`RoundID` handling, the transition-identity treatment of the assignment-effect policy, the
legality of `STATE_ONLY_ROLLBACK`, and the shape/update discipline of the setup rollback item. Each row records the
SUPERSEDED statement, the SUPERSEDING Stage-1AA statement, and the authoritative location in the current
`STAGE_01_PROTOCOL_PSEUDOCODE.md` / `STAGE_01_MINER_STATE_MACHINE.md` (line anchors approximate). No Stage-1A–1Z lettered
artifact (`STAGE_01[A-Z]_*`) is modified; the historical layers remain frozen, and this register is the sole record of
what Stage 1AA overrides.

## 1. Superseded → superseding statements

| # | Superseded (Stage 1Z) | Superseding (Stage 1AA) | Authoritative location |
|--:|------------------------|--------------------------|------------------------|
| AA1 | `RoundAbort` returned a bare `abort_record`; propagating procedures described the abort in prose or via a bare `abort_record` in their RETURNS union, and `SetupRetryEvent`'s abort classification was not pinned to one canonical result name | `RoundAbort` RETURNS the single canonical `round_aborted(abort_record)`; the direct propagators (`SetupRetryEvent`, `PrepareParticipantsForNewRound`, `ContinueTemplateRefreshAssignmentSetup`, `TemplateRefresh`, `FullRangeExhaustNoSolution`) list and classify the exact result via `RETURN CALL RoundAbort`, while the recovery paths CALL the same canonical `RoundAbort` for effect (`recovery_finalising`) and return their own recovery disposition; a target `round_aborted` maps `setup_retry_record.status = ABORTED` (never `CANCELLED`) | `RoundAbort` (~L5206–L5207); `SetupRetryEvent` (~L2050); `FullRangeExhaustNoSolution` RETURNS (~L4944) |
| AA2 | A terminal/superseded round could leave a `SEATED` `setup_retry_record`; there was no named terminaliser and the round-closure event-cancellation list did not include `SetupRetryEvent` | `CancelSetupRetriesForRound` (invoked by `CloseRoundAssignments`, whose cancellation list now includes `SetupRetryEvent`) sets a `SEATED` record `CANCELLED` (cancelling its `event_ref`) and flags an `APPLYING` record `terminal_closure_pending`; `setup_retry_record` gains `terminal_closure_pending`; no closed/superseded round leaves a `SEATED` record | `CancelSetupRetriesForRound` (~L2068); `CloseRoundAssignments` (~L4879, ~L4885); record def (§0.8, ~L836) |
| AA3 | `SetupRetryEvent`'s stale-`RoundID` check could return a stale no-op while leaving a known `SEATED` record `SEATED` (the record was not resolved/terminalised before the stale check) | `SetupRetryEvent` resolves the record and verifies the payload BEFORE the stale-`RoundID` check; a known `SEATED` record is terminalised `SUPERSEDED` (advanced round) or `CANCELLED` (closed round); a malformed payload matching no record may stale-noop | `SetupRetryEvent` guard order (~L1983–L2007) |
| AA4 | `assignment_effect_policy` was a caller-passed argument OUTSIDE `TransitionEventID`, so an `EDGE_DEFAULT` and a `STATE_ONLY_ROLLBACK` transition with identical numeric identity could alias in the applied/replay registry | `assignment_effect_policy` is a FIELD of `TransitionEventID`, so transitions with different assignment side effects are distinct replay ids | `ApplyMinerStateTransition` `TransitionEventID` (~L1168–L1172); miner-SM §3.5 |
| AA5 | The rollback's "state-only" behaviour depended on the caller passing `STATE_ONLY_ROLLBACK` correctly; there was no executable guard preventing its use on another edge to bypass assignment effects | `ApplyMinerStateTransition` step (4b) rejects `STATE_ONLY_ROLLBACK` unless the exact `WAKING → OFFLINE` / `validation_abort` / exact-non-null `assignment_ref` / matching `waking_origin_assignment_ref` tuple holds, with no mutation (`illegal_state_only_rollback_tuple`) | `ApplyMinerStateTransition` (~L1194–L1202); miner-SM §3.5 |
| AA6 | `setup_transaction.rollback_items` was a list; the item's wake fields were mutated through a local-variable alias (`SET item.wake_result` / `SET item.WakeEventRef`) after appending | `setup_rollback_item` gains `RollbackItemID`; `rollback_items` is a map keyed by it; each item is created `WakeEventRef = null` / `wake_result = NOT_ATTEMPTED` before `StartWake` and UPDATED EXPLICITLY by key afterward; rollback consumes the stored keyed record iterating by `RollbackItemID` | seating loops (~L1770, ~L5076); `RollbackParticipantSetup` (~L1913); `RollbackTemplateRefreshSetup` (~L1944); §0.8 (~L874) |

## 2. Companion normative-document supersessions

| Document | Superseding Stage-1AA addendum |
|----------|-------------------------------|
| `STAGE_01_MINER_STATE_MACHINE.md` | §3.5 Stage-1AA addendum — `assignment_effect_policy` in the transition identity (AA4) and the legal `STATE_ONLY_ROLLBACK` tuple (AA5); §3.4 retained as the frozen Z layer |
| `STAGE_01_ROUND_STATE_MACHINE.md` | §3.10e Stage-1AA addendum (AA1–AA6); §3.10a/b/c/d retained as the frozen W/X/Y/Z layers |
| `STAGE_01_INVARIANT_CATALOGUE.md` | I16 Stage-1AA clause (AA1–AA6); I20 unchanged (AA6 changes item storage, not the pre-constructor restore semantics) |
| `STAGE_01_TERMINOLOGY.md` | Stage-1AA terminology addendum (`round_aborted(abort_record)`, `CancelSetupRetriesForRound`, `terminal_closure_pending`, stale-`RoundID` terminalisation, `assignment_effect_policy` in `TransitionEventID`, legal `STATE_ONLY_ROLLBACK` tuple, `RollbackItemID` / keyed `rollback_items` / `NOT_ATTEMPTED`) |
| `STAGE_01_TRACEABILITY_MATRIX.csv` | Rows R191–R197 (AA1–AA6 + the TV227–TV235 block) |

## 3. Freeze statement

Stage-1A through Stage-1Z lettered artifacts (`STAGE_01[A-Z]_*`) are byte-identical to the Stage-1Z parent commit
(`f224a05396ee6971de885f4401a5a69d8da300b5`). Stage 1AA modifies only the six normative `STAGE_01_*` documents and adds the
twelve `STAGE_01AA_*` deliverables; every override of a prior-letter statement is recorded in this register.
