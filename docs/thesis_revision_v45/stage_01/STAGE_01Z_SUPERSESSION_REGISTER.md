# Stage 1Z — Supersession Register

Stage 1Z supersedes specific Stage-1Y statements about the setup-retry idempotence registry, the rollback ledger
snapshot, the wake reference, the T12 assignment-effect exception, the ValidationAbort departure, and the setup
transaction shape. Each row records the SUPERSEDED statement, the SUPERSEDING Stage-1Z statement, and the authoritative
location in the current `STAGE_01_PROTOCOL_PSEUDOCODE.md` / `STAGE_01_MINER_STATE_MACHINE.md` (line anchors approximate).
No Stage-1A–1Y lettered artifact (`STAGE_01[A-Y]_*`) is modified; the historical layers remain frozen, and this register
is the sole record of what Stage 1Z overrides.

## 1. Superseded → superseding statements

| # | Superseded (Stage 1Y) | Superseding (Stage 1Z) | Authoritative location |
|--:|------------------------|-------------------------|------------------------|
| Z1 | `SetupRetryEvent` marked APPLYING and added the id to `applied_setup_retry_ids` BEFORE the target result was known, and the duplicate guard tested PRESENCE in `applied_setup_retry_ids` / `setup_retry_status_by_id` — which, once a SEATED record was published, would suppress the first legitimate dispatch; only `APPLYING` was ever written | One `setup_retry_record` per `SetupRetryID` in `setup_retry_records`; the seat publishes `SEATED`, the first dispatch flips `SEATED -> APPLYING` and EXECUTES, the captured target result sets `APPLIED` / `SUPERSEDED` / `ABORTED` / `CANCELLED`; the duplicate guard tests `status != SEATED`; the redundant mirror is removed; "applied" = `status = APPLIED` set only after the result | `SetupRetryEvent` (~L1901); seating publishes (~L1772, ~L5035); `setup_retry_record` §0.8 |
| Z2 | The setup before-image was captured AFTER `CreatePendingAssignment` (post-mutation) | The before-image is captured BEFORE `CreatePendingAssignment` (pre-constructor); invariant I20 requires rollback to restore the exact pre-constructor I8a/I8b values | `PrepareParticipantsForNewRound` (~L1709); `ContinueTemplateRefreshAssignmentSetup` (~L4977); invariant I20 |
| Z3 | The wake reference was a per-miner map entry (`wake_by_miner[m]`) that could be absent for a miner whose wake never seated, and the rollback indexed it directly | The `setup_rollback_item` carries `WakeEventRef : WakeEventRef | null` + `wake_result`; `AbortPendingWakeForRollback` cancels only a non-null pending ref — no undefined lookup | seating loops (~L1719, ~L4988); `AbortPendingWakeForRollback` (~L1789) |
| Z4 | The rollback "changes miner state only" was prose; `ApplyMinerStateTransition` step (5c) unconditionally applied the edge's assignment-status change | `ApplyMinerStateTransition` takes `assignment_effect_policy ∈ { EDGE_DEFAULT, STATE_ONLY_ROLLBACK }`; step (5c) is gated on `EDGE_DEFAULT`; `AbortPendingWakeForRollback` passes `STATE_ONLY_ROLLBACK` and owns the single close | `ApplyMinerStateTransition` (~L1073, step 5c); `AbortPendingWakeForRollback` (~L1821); miner-SM §3.4 |
| Z5 | `AbortPendingWakeForRollback` departed any `WAKING` miner unconditionally, without verifying the departure was bound to the exact wake that initiated the current WAKING residency | `waking_origin_assignment_ref[MinerID]` is set on WAKING entry / cleared on WAKING exit in the hook; the rollback verifies it equals the item's `assignment_version_ref` before the T12 — a mismatch returns `wake_abort_failed` and departs no miner | `ApplyMinerStateTransition` (5c-Z5); `AbortPendingWakeForRollback` (~L1797); miner-SM §3.4 |
| Z6 | `setup_transaction` carried parallel maps (`assignment_by_miner` / `wake_by_miner` / `before_image_by_miner` / `prior_states`), permitting a partial-map state | `setup_transaction = { rollback_envelope, rollback_items : [setup_rollback_item] }` — one complete record per created assignment, appended before `StartWake`; the setup rollbacks iterate `rollback_items` | `setup_rollback_item` §0.8; seating loops; `RollbackParticipantSetup` (~L1834), `RollbackTemplateRefreshSetup` (~L1871) |

## 2. Companion normative-document supersessions

| Document | Superseding Stage-1Z addendum |
|----------|-------------------------------|
| `STAGE_01_MINER_STATE_MACHINE.md` | §3.4 Stage-1Z addendum — the `STATE_ONLY_ROLLBACK` assignment-effect policy (Z4) and the wake-origin binding (Z5) |
| `STAGE_01_ROUND_STATE_MACHINE.md` | §3.10d Stage-1Z addendum (Z1–Z6); §3.10a/b/c retained as the frozen W/X/Y layers |
| `STAGE_01_INVARIANT_CATALOGUE.md` | I16 Stage-1Z clause (Z1–Z6) and the NEW invariant I20 (pre-mutation snapshot restore, Z2) |
| `STAGE_01_TERMINOLOGY.md` | Stage-1Z terminology addendum (`setup_retry_record`/`setup_retry_records`, pre-mutation snapshot, nullable `WakeEventRef`, `assignment_effect_policy`, `waking_origin_assignment_ref`, `setup_rollback_item`/`rollback_items`) |
| `STAGE_01_TRACEABILITY_MATRIX.csv` | Rows R184–R190 (Z1–Z6 + the TV219–TV226 block) |

## 3. Freeze statement

Stage-1A through Stage-1Y lettered artifacts (`STAGE_01[A-Y]_*`) are byte-identical to the Stage-1Y parent commit
(`479640add8b000323770255e05478958505eabac`). Stage 1Z modifies only the six normative `STAGE_01_*` documents and adds the
twelve `STAGE_01Z_*` deliverables; every override of a prior-letter statement is recorded in this register.
