# Stage 1Z — Correction Report (retry-lifecycle & rollback-snapshot lock)

Stage 1Z is a narrow, documentation-only revision of the Stage-1 formal specification of **PoCol** and the idle policy
within PoCol. It closes six defects (Z1–Z6) in the setup-retry status lifecycle, the pre-mutation ledger snapshot, the
nullable wake reference, the T12 assignment-effect policy, the ValidationAbort wake-origin binding, and the centralisation
of rollback item data. It changes only the six normative `STAGE_01_*` documents and adds twelve `STAGE_01Z_*`
deliverables. No executable source, configuration, DOCX, or PDF is touched; no experiment is run; the A1 baseline
(`8.420833333 kWh`) is unchanged; and no Stage-1A–1Y historical artifact is modified.

- **Branch:** `thesis-v45-pocol-stage1z-retry-lifecycle-rollback-snapshot-lock`
- **Parent commit:** `479640add8b000323770255e05478958505eabac` (Stage 1Y)

## Corrections

### Z1 — Complete the setup-retry status lifecycle

`setup_retry_record` (`{ SetupRetryID, setup_kind, RoundID, TemplateID_at_seat, TemplateRefreshSetupID, retry_generation,
event_ref, status, target_disposition }`) is published in the single `setup_retry_records` registry. After a successful
`ScheduleEvent`, the seating procedure publishes `status = SEATED` atomically. `SetupRetryEvent`'s FIRST valid dispatch
flips `SEATED -> APPLYING` and EXECUTES the target (a SEATED record is NEVER duplicate-suppressed); it CAPTURES the target
result (no direct `RETURN CALL`) and sets the terminal status — `APPLIED` (succeeded), `SUPERSEDED` (a later generation
seated), `ABORTED` (RoundAbort), or `CANCELLED` (terminal/stale). A replay is duplicate-suppressed IFF the status is
already non-SEATED. The redundant Y-era `applied_setup_retry_ids` / `setup_retry_status_by_id` are removed; "applied" ≡
`status = APPLIED`, set only after the target result is known. *(Audit: `STAGE_01Z_SETUP_RETRY_LIFECYCLE_AUDIT.md`;
vectors TV219, TV220.)*

### Z2 — Capture ledger before-images before assignment creation

In `PrepareParticipantsForNewRound` and `ContinueTemplateRefreshAssignmentSetup`, `coverage_custody_before_image(range)`
is captured BEFORE `CreatePendingAssignment` mutates `custody_status` / `assignment_ledger`; on a creation failure the
before-image is discarded and no item is created. New invariant **I20** requires that rollback restores the exact
pre-constructor I8a/I8b values. *(Audit: `STAGE_01Z_PREMUTATION_SNAPSHOT_AUDIT.md`; vector TV221.)*

### Z3 — Make wake event references explicitly optional

A `setup_rollback_item` carries `WakeEventRef : WakeEventRef | null` and `wake_result`. On `StartWake`: `wake_seated`
stores the actual ref; `wake_schedule_failed_before_transition` stores null; `wake_transition_failed_after_seat` stores the
returned (already-cancelled) ref. `AbortPendingWakeForRollback` cancels only a non-null, still-pending ref — no undefined
map lookup. *(Audit: `STAGE_01Z_NULLABLE_WAKE_REFERENCE_AUDIT.md`; vector TV222.)*

### Z4 — Make the T12 assignment-effect policy executable

`ApplyMinerStateTransition` takes `assignment_effect_policy ∈ { EDGE_DEFAULT, STATE_ONLY_ROLLBACK }` (default
`EDGE_DEFAULT`). `EDGE_DEFAULT` applies the edge's declared assignment-status change; `STATE_ONLY_ROLLBACK` (passed only by
`AbortPendingWakeForRollback`) changes miner state / residency / one-shot energy / census ONLY and performs no assignment
mutation, and `AbortPendingWakeForRollback` then performs the single canonical close. `STAGE_01_MINER_STATE_MACHINE.md`
§3.4 documents the policy. *(Audit: `STAGE_01Z_T12_ASSIGNMENT_EFFECT_AUDIT.md`; vector TV223.)*

### Z5 — Define ValidationAbort for a detached or closed head

`waking_origin_assignment_ref[MinerID]` is set on entry to `WAKING` (to the exact `assignment_version_ref` woken) and
cleared on any `WAKING` departure, inside `ApplyMinerStateTransition`. The `T12` `ValidationAbort` rollback is legal only
when `miner_state = WAKING` AND `waking_origin_assignment_ref[MinerID]` equals the rollback item's `assignment_version_ref`
— even if the head is `CLOSED` / detached; on a mismatch `AbortPendingWakeForRollback` returns `wake_abort_failed` and
departs no miner; the association is cleared exactly once by the successful departure. *(Audit:
`STAGE_01Z_WAKING_ORIGIN_BINDING_AUDIT.md`; vectors TV224, TV225.)*

### Z6 — Centralise rollback item data

`setup_transaction = { rollback_envelope, rollback_items : [setup_rollback_item] }` replaces the Y-era parallel maps
(`assignment_by_miner` / `wake_by_miner` / `before_image_by_miner` / `prior_states`). Each `setup_rollback_item`
(`{ MinerID, AssignmentID, assignment_version, pre_wake_state, before_image, WakeEventRef | null, wake_result,
rollback_envelope }`) is appended complete BEFORE `StartWake`, so no partial-map state can exist. The two setup rollbacks
iterate `rollback_items`. *(Covered by the correction report, signature/call-graph audits, and the cross-document audit;
exercised by TV226.)*

## Deliverables (12 new `STAGE_01Z_*` files)

1. `STAGE_01Z_CORRECTION_REPORT.md` (this file)
2. `STAGE_01Z_SETUP_RETRY_LIFECYCLE_AUDIT.md` (Z1)
3. `STAGE_01Z_PREMUTATION_SNAPSHOT_AUDIT.md` (Z2)
4. `STAGE_01Z_NULLABLE_WAKE_REFERENCE_AUDIT.md` (Z3)
5. `STAGE_01Z_T12_ASSIGNMENT_EFFECT_AUDIT.md` (Z4)
6. `STAGE_01Z_WAKING_ORIGIN_BINDING_AUDIT.md` (Z5)
7. `STAGE_01Z_PROCEDURE_SIGNATURE_CALL_AUDIT.md`
8. `STAGE_01Z_PROCEDURE_CALL_GRAPH.md`
9. `STAGE_01Z_SEMANTIC_TEST_VECTORS.md` (TV219–TV226)
10. `STAGE_01Z_SUPERSESSION_REGISTER.md`
11. `STAGE_01Z_CROSS_DOCUMENT_AUDIT.md`
12. `STAGE_01Z_CHECKSUM_MANIFEST.sha256`

## Modified normative documents (6)

`STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_MINER_STATE_MACHINE.md`, `STAGE_01_ROUND_STATE_MACHINE.md`,
`STAGE_01_INVARIANT_CATALOGUE.md` (adds invariant I20), `STAGE_01_TERMINOLOGY.md`, `STAGE_01_TRACEABILITY_MATRIX.csv`.

## Discipline

Documentation-only; the algorithm remains **PoCol** and the mechanism remains the idle policy within PoCol; the A1
baseline `8.420833333 kWh` is unchanged; the call graph resolves with 85 procedures and 0 dangling references (Stage 1Z
adds no new procedure); and Stage 2 is not begun.
