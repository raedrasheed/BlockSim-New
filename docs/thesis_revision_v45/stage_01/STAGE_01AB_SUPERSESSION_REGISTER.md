# Stage 1AB — Supersession Register

Stage 1AB supersedes specific Stage-1AA statements about the `RoundAbort` result contract, the ordering of the abort
capture, the persistence of setup-retry lifecycle mutations, the post-target visibility of the closure flag, dispatch
ownership, and round-closure terminalisation — and it records that two Stage-1AA AUDIT claims were inaccurate (AB7). Each
row records the SUPERSEDED statement, the SUPERSEDING Stage-1AB statement, and the authoritative location in the current
`STAGE_01_PROTOCOL_PSEUDOCODE.md` (line anchors approximate). No Stage-1A–1AA lettered artifact (`STAGE_01[A-Z]_*` /
`STAGE_01AA_*`) is modified; the historical layers remain frozen, and this register is the sole record of what Stage 1AB
overrides.

## 1. Superseded → superseding statements

| # | Superseded (Stage 1AA) | Superseding (Stage 1AB) | Authoritative location |
|--:|------------------------|--------------------------|------------------------|
| AB1 | `PrepareParticipantsForNewRound`, `ContinueTemplateRefreshAssignmentSetup`, and `TemplateRefresh` declared a BARE `round_aborted` in their RETURNS unions, and `SetupRetryEvent`'s RETURNS obscured the union with "(the re-run target procedure's disposition)" | Every direct value-propagator lists the EXACT `round_aborted(abort_record)`; `SetupRetryEvent`'s RETURNS names it once and ENUMERATES the target dispositions explicitly; no result contract uses a bare alias | `PrepareParticipantsForNewRound` RETURNS (~L1871); `ContinueTemplateRefreshAssignmentSetup` RETURNS (~L5240); `TemplateRefresh` RETURNS (~L5137); `SetupRetryEvent` RETURNS (~L2097) |
| AB2 | `SetupRetryEvent`'s guard branches wrote `SET rec.target_disposition <- round_aborted` (a bare token) BEFORE the abort result existed, then `RETURN CALL RoundAbort(...)` | Each guard abort captures `SET disp <- CALL RoundAbort(...)` FIRST, then keyed `UPDATE status <- ABORTED` / `target_disposition <- disp`, then `RETURN disp`; the stored disposition is the exact `round_aborted(abort_record)` | `SetupRetryEvent` guards (~L2049, ~L2060, ~L2066) |
| AB3 | Lifecycle mutations were written through the local snapshot (`SET rec <- setup_retry_records[...]; SET rec.status <- ...`), relying on undeclared record-reference persistence | `rec` is READ-ONLY; the seat is the only CREATE; every lifecycle change is a keyed `UPDATE setup_retry_records[SetupRetryID]`; `CancelSetupRetriesForRound` iterates `SetupRetryID`s and updates by key | `SetupRetryEvent` (throughout EFFECTS); `CancelSetupRetriesForRound` (~L2129) |
| AB4 | `SetupRetryEvent` classified on the pre-target snapshot `rec.terminal_closure_pending`, which could miss a flag the target persisted mid-flight | After the target returns, the handler RE-READS `post_target_rec <- setup_retry_records[SetupRetryID]` and classifies on the PERSISTED flag; a closed-round record can never finish `APPLIED` | `SetupRetryEvent` step 8 (~L2085) |
| AB5 | A known `SetupRetryID` with a payload mismatch stale-nooped and LEFT the record `SEATED` regardless of whether the dispatch was the record's own event | `dispatched_event_ref` binds ownership: foreign ref → stale-noop (record left SEATED); the GENUINE event with a mismatched payload → integrity abort (`setup_retry_payload_integrity_failure`) that terminalises the record and cancels any residual event | `SetupRetryEvent` INPUTS (~L1979) + steps (1c)/(2) (~L2003, ~L2010) |
| AB6 | `CancelSetupRetriesForRound` mutated detached record values (`SET rec.status <- ...`) and did not clear a cancelled record's `event_ref` or assert closure post-conditions | Keyed UPDATEs; a cancelled `SEATED` record's `event_ref` is CLEARED to null; post-conditions asserted (no SEATED record, no queued event, terminal dispositions, persisted `terminal_closure_pending`) | `CancelSetupRetriesForRound` (~L2129–L2150) |

## 2. Corrected Stage-1AA audit claims (AB7)

Stage-1AA deliverables are frozen historical artifacts and are NOT modified. Stage 1AB records that the following
Stage-1AA claims were inaccurate against the Stage-1AA pseudocode they described, and that the underlying defects are
fixed here:

| Stage-1AA artifact | Inaccurate claim | Stage-1AB correction |
|--------------------|------------------|----------------------|
| `STAGE_01AA_ROUND_ABORT_RESULT_AUDIT.md` | Treated bare `round_aborted` return declarations (e.g. in `PrepareParticipantsForNewRound` / `ContinueTemplateRefreshAssignmentSetup` / `TemplateRefresh`) as exact `round_aborted(abort_record)` contracts | AB1 shapes every propagator's RETURNS to the exact `round_aborted(abort_record)`; the whole-file occurrence audit in `STAGE_01AB_EXACT_ABORT_CONTRACT_AUDIT.md` confirms zero bare-alias result contracts |
| `STAGE_01AA_RETRY_TERMINALIZATION_AUDIT.md` | Assumed writes through local `rec` variables (`SET rec.status <- ...`) persist in `setup_retry_records` | AB3 makes every lifecycle mutation a keyed `UPDATE setup_retry_records[SetupRetryID]`; `STAGE_01AB_RETRY_RECORD_PERSISTENCE_AUDIT.md` confirms no `SET rec.<field>` remains |
| `STAGE_01AA_SEMANTIC_TEST_VECTORS.md` (TV227) | Did not detect the bare-alias contract or the local-alias persistence gap | AB1/AB2/AB3 close both; TV236–TV239 exercise the exact shaped contract and keyed persistence |

**Process correction.** All Stage-1AB audits inspect the FINAL normative tree, generated only after every normative edit
and the semantic vectors were complete (the cross-document audit and the checksum manifest are generated last).

## 3. Companion normative-document supersessions

| Document | Superseding Stage-1AB addendum |
|----------|-------------------------------|
| `STAGE_01_ROUND_STATE_MACHINE.md` | §3.10f Stage-1AB addendum (AB1–AB7); §3.10a–§3.10e retained as the frozen W/X/Y/Z/AA layers |
| `STAGE_01_INVARIANT_CATALOGUE.md` | I16 Stage-1AB clause (AB1–AB6) |
| `STAGE_01_TERMINOLOGY.md` | Stage-1AB terminology addendum (exact abort shape, capture-before-persist, keyed persistent update, post-target re-read, `dispatched_event_ref`, `setup_retry_payload_integrity_failure`, closure post-conditions) |
| `STAGE_01_TRACEABILITY_MATRIX.csv` | Rows R198–R205 (AB1–AB7 + the TV236–TV243 block) |

The miner state machine is not modified — AB1–AB7 concern the retry-record lifecycle and the abort result contract only.

## 4. Freeze statement

Stage-1A through Stage-1AA lettered artifacts (`STAGE_01[A-Z]_*` and `STAGE_01AA_*`) are byte-identical to the Stage-1AA
parent commit (`e5f8aecb5ffea1fa3b4127befe9a510c785a1166`). Stage 1AB modifies only the five normative `STAGE_01_*`
documents it touches and adds the eleven `STAGE_01AB_*` deliverables; every override of a prior-letter statement — and the
two corrected Stage-1AA audit claims — is recorded in this register.
