# Stage 1Y — Correction Report (retry-identity & rollback-closure lock)

Stage 1Y is a narrow, documentation-only revision of the Stage-1 formal specification of **PoCol** and the idle policy
within PoCol. It closes five defects (Y1–Y5) in the setup-retry idempotence ordering, the template-refresh retry
identity, the retry-generation ownership, the rollback resolution of affected `WAKING` miners, and the legal-`T12`
rollback trigger / assignment-closure ownership. It changes only the six normative `STAGE_01_*` documents and adds
twelve `STAGE_01Y_*` deliverables. No executable source, configuration, DOCX, or PDF is touched; no experiment is run;
the A1 baseline (`8.420833333 kWh`) is unchanged; and no Stage-1A–1X historical artifact is modified.

- **Branch:** `thesis-v45-pocol-stage1y-retry-identity-rollback-closure-lock`
- **Parent commit:** `1fd776fd79f469de920194dccdebebede4a35a9e` (Stage 1X)

## Corrections

### Y1 — Setup-retry idempotence precedes the mutating guards

`SetupRetryEvent` now follows the canonical guard order: (1) event shape + `RoundID` identity; (2) EXACT-replay
idempotence; (3) terminal; (4) kind-specific template identity; (5) target round state; (6) budget + participant
compatibility; (7) atomically mark `APPLYING` and invoke. Because idempotence (2) precedes the terminal check (3) and
the wrong-round-state abort (5), a replay of a retry that already succeeded and moved the round to `HASHING` returns
`setup_retry_duplicate_suppressed` and NEVER calls `RoundAbort` for a forward round. A `SetupRetryStatus` enum
(`SEATED`, `APPLYING`, `APPLIED`, `SUPERSEDED`, `CANCELLED`, `ABORTED`) is recorded per `SetupRetryID` in
`setup_retry_status_by_id`. *(Audit: `STAGE_01Y_SETUP_RETRY_REPLAY_AUDIT.md`; vectors TV210, TV218.)*

### Y2 — Exact template-refresh setup identity

The `SetupRetryEvent` payload carries `TemplateID_at_seat` and `TemplateRefreshSetupID = (RoundID,
committed_new_TemplateID)` for `TEMPLATE_REFRESH_SETUP`. Both `SetupRetryEvent` and
`ContinueTemplateRefreshAssignmentSetup` verify the exact `TemplateRefreshSetupID` against
`template_refresh_setup_committed[TemplateID_at_seat].TemplateRefreshSetupID` on the initial invocation AND every retry.
The ambient "the refresh setup's TemplateID" phrasing is removed; a stale retry for an earlier `TemplateID` takes a
declared stale disposition and never operates on the current committed template. *(Audit:
`STAGE_01Y_TEMPLATE_RETRY_IDENTITY_AUDIT.md`; vectors TV211, TV212.)*

### Y3 — Retry-generation ownership (no shadowing)

The scalar `retry_generation` (the retry-generation input) and the map `setup_retry_generation_by_scope` (the bounded
per-scope counter registry keyed by `(RoundID, setup_kind, TemplateRefreshSetupID_or_null)`) are distinct identifiers;
no identifier is both a scalar and a map. `SetupRetryID` carries the complete scope:
`(RoundID, TemplateID, PARTICIPANT_SETUP, retry_generation)` /
`(TemplateRefreshSetupID, TEMPLATE_REFRESH_SETUP, retry_generation)`. *(Audit:
`STAGE_01Y_RETRY_GENERATION_OWNERSHIP_AUDIT.md`; vector TV213.)*

### Y4 — Handle every affected `WAKING` miner unconditionally

`RollbackRecoveryAssignmentPlan`, `RollbackParticipantSetup`, and `RollbackTemplateRefreshSetup` resolve every affected
`WAKING` miner REGARDLESS of whether its assignment remains a live bound head — a `CLOSED` / revoked / detached head does
not make a `WAKING` miner safe. The final coherence gate is "no affected miner remains `WAKING`". A rollback with an
unresolved affected `WAKING` miner returns `rollback_failed` and the caller takes the declared
`RECOVERY_INSTALL_FAILED_ABORTED` / `RoundAbort` path. The setup transactions gain `wake_by_miner` and
`before_image_by_miner` so the exact per-miner wake and ledger snapshot are available. *(Audit:
`STAGE_01Y_ROLLBACK_WAKING_COMPLETENESS_AUDIT.md`; vectors TV214, TV215, TV217.)*

### Y5 — One legal-`T12` rollback trigger and one closure owner

The new named operation `AbortPendingWakeForRollback` (1) cancels the exact `WakeCompleteEvent`; (2) departs a
still-`WAKING` miner `WAKING -> OFFLINE` via the authoritative `T12` `ValidationAbort` trigger (`reason =
validation_abort`, a trigger declared in `STAGE_01_MINER_STATE_MACHINE.md` §3 — NOT the assignment
`termination_reason`); (3) binds the exact assignment version; (4) closes the `WAKING` residency + charges the
transition energy once via `ApplyMinerStateTransition` (which for this form changes miner state only); (5) performs the
SINGLE canonical assignment close (`termination_reason = cancellation`, `revocation_reason = assignment_revoked`,
`closure_detail`); (6) restores the ledgers from the before-image; (7) returns a structured result. The transition hook
and this operation never both close the same assignment. `STAGE_01_MINER_STATE_MACHINE.md` §3.3 documents the
`ValidationAbort` rollback form and the single closure owner. *(Audit: `STAGE_01Y_T12_CLOSURE_OWNERSHIP_AUDIT.md`;
vector TV216.)*

## Deliverables (12 new `STAGE_01Y_*` files)

1. `STAGE_01Y_CORRECTION_REPORT.md` (this file)
2. `STAGE_01Y_SETUP_RETRY_REPLAY_AUDIT.md` (Y1)
3. `STAGE_01Y_TEMPLATE_RETRY_IDENTITY_AUDIT.md` (Y2)
4. `STAGE_01Y_RETRY_GENERATION_OWNERSHIP_AUDIT.md` (Y3)
5. `STAGE_01Y_ROLLBACK_WAKING_COMPLETENESS_AUDIT.md` (Y4)
6. `STAGE_01Y_T12_CLOSURE_OWNERSHIP_AUDIT.md` (Y5)
7. `STAGE_01Y_PROCEDURE_SIGNATURE_CALL_AUDIT.md`
8. `STAGE_01Y_PROCEDURE_CALL_GRAPH.md`
9. `STAGE_01Y_SEMANTIC_TEST_VECTORS.md` (TV210–TV218)
10. `STAGE_01Y_SUPERSESSION_REGISTER.md`
11. `STAGE_01Y_CROSS_DOCUMENT_AUDIT.md`
12. `STAGE_01Y_CHECKSUM_MANIFEST.sha256`

## Modified normative documents (6)

`STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_MINER_STATE_MACHINE.md`, `STAGE_01_ROUND_STATE_MACHINE.md`,
`STAGE_01_INVARIANT_CATALOGUE.md`, `STAGE_01_TERMINOLOGY.md`, `STAGE_01_TRACEABILITY_MATRIX.csv`.

## Discipline

Documentation-only; the algorithm remains **PoCol** and the mechanism remains the idle policy within PoCol; the A1
baseline `8.420833333 kWh` is unchanged; the call graph resolves with 85 procedures and 0 dangling references (the new
`AbortPendingWakeForRollback`); and Stage 2 is not begun.
