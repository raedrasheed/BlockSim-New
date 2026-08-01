# Stage 1Y — Semantic Test Vectors (TV210–TV218)

These blocking paper test vectors exercise corrections Y1–Y5 of the retry-identity and rollback-closure lock. Each
vector names the EXACT procedures and preconditions it drives, states the required outcome, and asserts NO behaviour
that is not written in `STAGE_01_PROTOCOL_PSEUDOCODE.md` / `STAGE_01_MINER_STATE_MACHINE.md` (no assumed guard,
transition, edge, or result name). Every vector preserves the A1 baseline (`8.420833333 kWh`): none alters energy
inputs, the census computation, or any experiment. The algorithm is **PoCol** and the mechanism under test is the idle
policy within PoCol.

Terminology: `T12` is the authoritative `WAKING -> OFFLINE` miner edge with declared triggers
**Departure / WakeDeadlineExpiry / ValidationAbort** (`STAGE_01_MINER_STATE_MACHINE.md` §3, row T12);
`AbortPendingWakeForRollback` is the one named rollback wake-abort operation (Y5);
`TemplateRefreshSetupID = (RoundID, committed_new_TemplateID)` (Y2); `retry_generation` is the scalar generation and
`setup_retry_generation_by_scope` the per-scope map (Y3).

---

## TV210 — Replay after a successful HASHING transition is duplicate-suppressed, never aborted (Y1)

- **Procedures:** `SetupRetryEvent`, `PrepareParticipantsForNewRound` (or `ContinueTemplateRefreshAssignmentSetup`).
- **Setup:** a seated `SetupRetryEvent` fires, is marked `APPLYING` (added to `applied_setup_retry_ids` /
  `setup_retry_status_by_id`), runs its target, and the target succeeds — the round transitions to `HASHING`. The EXACT
  same `SetupRetryID` is then re-dispatched (a duplicate delivery) while `round_state = HASHING`.
- **Expected:** the canonical guard order runs (1) event shape + `RoundID` identity (RoundID still current), then (2)
  EXACT-replay idempotence — the `SetupRetryID` is already recorded, so it returns `setup_retry_duplicate_suppressed`.
  The wrong-round-state guard (step 5, which would `RoundAbort` because `round_state != ASSIGNMENT`) is NEVER reached. No
  `RoundAbort` occurs for the forward round.

## TV211 — Template-refresh retry carries and resolves the exact identity before the continuation runs (Y2)

- **Procedures:** `SetupRetryEvent` (`TEMPLATE_REFRESH_SETUP`), `ContinueTemplateRefreshAssignmentSetup`.
- **Setup:** `TemplateRefresh` committed a new `TemplateID` and set
  `template_refresh_setup_committed[new_TemplateID].TemplateRefreshSetupID`; a bounded `SetupRetryEvent` is seated with
  the payload `TemplateID_at_seat = new_TemplateID` and `TemplateRefreshSetupID = (RoundID, new_TemplateID)`.
- **Expected:** the retry verifies `TemplateID_at_seat = TemplateID_committed` AND
  `TemplateRefreshSetupID = template_refresh_setup_committed[TemplateID_at_seat].TemplateRefreshSetupID` BEFORE marking
  APPLYING and calling `ContinueTemplateRefreshAssignmentSetup`; the continuation re-verifies the exact
  `TemplateRefreshSetupID` on entry. Both resolve to the committed marker before any assignment work runs.

## TV212 — A stale template-refresh retry from an older TemplateID cannot operate on the newer template (Y2)

- **Procedures:** `SetupRetryEvent` (`TEMPLATE_REFRESH_SETUP`), `ContinueTemplateRefreshAssignmentSetup`.
- **Setup:** a `TEMPLATE_REFRESH_SETUP` retry seated for an EARLIER `TemplateID_old` arrives after a further refresh
  committed `TemplateID_new` (so `TemplateID_committed = TemplateID_new != TemplateID_old`).
- **Expected:** the kind-specific identity guard finds `TemplateID_at_seat (= TemplateID_old) != TemplateID_committed`
  (or the `TemplateRefreshSetupID` no longer matches the committed marker) and returns `setup_retry_stale_noop` — it
  NEVER operates on `TemplateID_new`. If the continuation were entered directly, its defensive Y2 check returns
  `template_refresh_retry_stale_noop`. No assignment is created against the current template.

## TV213 — retry_generation scalar and setup_retry_generation_by_scope map are distinct (Y3)

- **Procedures:** `SetupRetryEvent`, `ContinueTemplateRefreshAssignmentSetup`, `PrepareParticipantsForNewRound`,
  `RoundInitialise`.
- **Setup:** inspect the retry-generation identifiers across the seating sites and the retry handler.
- **Expected:** `retry_generation` appears ONLY as a scalar (input parameter / `SetupRetryID` component / budget
  comparison against `maximum_setup_retries`); `setup_retry_generation_by_scope` appears ONLY as a map indexed by
  `(RoundID, setup_kind, TemplateRefreshSetupID_or_null)`. No identifier is read as both a scalar and a map; there is no
  ambiguous indexing. `SetupRetryID` carries the full scope for both kinds.

## TV214 — Two committed WAKING items and a third failure: both affected miners resolved (Y4/Y5)

- **Procedures:** `CommitRecoveryAssignmentPlan`, `RollbackRecoveryAssignmentPlan`, `AbortPendingWakeForRollback`,
  `ApplyMinerStateTransition`.
- **Setup:** a plan whose first two items commit and enter `WAKING` (each with a captured `WakeEventRef`,
  `assignment_version`, and `coverage_custody_before_image`), and whose third item fails
  (`install_failed_after_mutation`), so the caller rolls back the `rollback_record`.
- **Expected:** the rollback cancels BOTH captured wakes, then calls `AbortPendingWakeForRollback` for BOTH affected
  miners — each departs `WAKING -> OFFLINE` via `T12` (`reason = validation_abort`) with its EXACT version, closes its
  exact head canonically, and restores its before-image — and returns `rollback_completed(rolled_to_offline,
  rolled_back_items)` with both items resolved. No affected miner remains `WAKING`.

## TV215 — A rollback item whose head is already CLOSED/unbound but whose miner is WAKING (Y4)

- **Procedures:** `RollbackRecoveryAssignmentPlan` / a setup rollback, `AbortPendingWakeForRollback`.
- **Setup:** a `rollback_item` whose `AssignmentID` is already `CLOSED` (or detached from the miner) while
  `miner_state(item.MinerID) = WAKING`.
- **Expected:** because the affected-miner resolution is UNCONDITIONAL (it does NOT require a live bound head),
  `AbortPendingWakeForRollback` still departs the `WAKING` miner via `T12` (the canonical close step is a no-op for an
  already-closed head). If the miner cannot be departed, it returns `wake_abort_failed` and the rollback returns
  `rollback_failed`. In no case does the rollback return `rollback_completed` while the miner is still `WAKING`.

## TV216 — Rollback T12 uses the authoritative ValidationAbort trigger; one closure owner (Y5)

- **Procedures:** `AbortPendingWakeForRollback`, `ApplyMinerStateTransition`.
- **Setup:** any rollback that departs a `WAKING` miner.
- **Expected:** the departure calls `ApplyMinerStateTransition(m, WAKING, OFFLINE, reason = validation_abort,
  assignment_ref = assignment_version_ref(AssignmentID, assignment_version), ...)` — `validation_abort` is a declared
  `T12` trigger in `STAGE_01_MINER_STATE_MACHINE.md` §3, and the version is exact. The transition hook changes miner
  state only (residency close + one-shot energy + no census change); the canonical assignment close
  (`termination_reason = cancellation`, `revocation_reason = assignment_revoked`, `closure_detail`) is performed by
  `AbortPendingWakeForRollback` ONLY. The hook and the operation never both close the same assignment.

## TV217 — An unresolvable affected miner aborts the install (Y4)

- **Procedures:** `RollbackRecoveryAssignmentPlan`, `AbortPendingWakeForRollback`,
  `ApplyRecoveryAssignmentContinuationAfterEpilogue` (caller), `RoundAbort`.
- **Setup:** one affected miner cannot complete the legal `T12` rollback (e.g. `ApplyMinerStateTransition` returns
  `illegal_stale_source` / `illegal_transition` for that miner).
- **Expected:** `AbortPendingWakeForRollback` returns `wake_abort_failed`; `RollbackRecoveryAssignmentPlan` returns
  `rollback_failed(residual_partial_assignment)`; and the caller records `RECOVERY_INSTALL_FAILED_ABORTED` and takes the
  declared `RoundAbort` path — it NEVER fabricates a genuine `UNRECOVERABLE`, and NEVER returns `rollback_completed`.

## TV218 — TemplateRefreshSetupID replay after a completed assignment setup is suppressed (Y1/Y2)

- **Procedures:** `SetupRetryEvent` (`TEMPLATE_REFRESH_SETUP`), `ContinueTemplateRefreshAssignmentSetup`,
  `CloseTemplateAssignments`, `TemplateCommit`.
- **Setup:** a `TEMPLATE_REFRESH_SETUP` retry whose `SetupRetryID` already ran to a successful assignment setup (its
  `SetupRetryID` is recorded and the round advanced) is re-dispatched.
- **Expected:** the EXACT-replay idempotence guard (Y1) returns `setup_retry_duplicate_suppressed`; no target runs
  again. Even if a fresh-generation retry is considered, `ContinueTemplateRefreshAssignmentSetup` (the only resume target)
  never calls `CloseTemplateAssignments`, constructs a candidate template, or calls `TemplateCommit` — the idempotent
  `template_refresh_setup_committed[TemplateID]` marker records those ran exactly once. No assignment creation /
  old-template closure / `TemplateCommit` is repeated.

---

## Coverage summary

| Vector | Correction | Primary procedures |
|--------|-----------|--------------------|
| TV210 | Y1 | `SetupRetryEvent` |
| TV211 | Y2 | `SetupRetryEvent`, `ContinueTemplateRefreshAssignmentSetup` |
| TV212 | Y2 | `SetupRetryEvent`, `ContinueTemplateRefreshAssignmentSetup` |
| TV213 | Y3 | `SetupRetryEvent`, `RoundInitialise`, seating sites |
| TV214 | Y4/Y5 | `RollbackRecoveryAssignmentPlan`, `AbortPendingWakeForRollback` |
| TV215 | Y4 | `AbortPendingWakeForRollback` |
| TV216 | Y5 | `AbortPendingWakeForRollback`, `ApplyMinerStateTransition` |
| TV217 | Y4 | `RollbackRecoveryAssignmentPlan`, `RoundAbort` |
| TV218 | Y1/Y2 | `SetupRetryEvent`, `ContinueTemplateRefreshAssignmentSetup` |

All nine vectors are specified against exact procedures and preconditions in the current
`STAGE_01_PROTOCOL_PSEUDOCODE.md` and `STAGE_01_MINER_STATE_MACHINE.md`; none assumes an unwritten guard, transition,
edge, or result name; and all preserve the A1 baseline `8.420833333 kWh`.
