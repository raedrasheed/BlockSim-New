# Stage 1AB — Correction Report (retry-record persistence & exact abort-contract lock)

Stage 1AB is a narrow, documentation-only revision of the Stage-1 formal specification of **PoCol** and the idle policy
within PoCol. It closes seven defects (AB1–AB7) in the exactness of the `RoundAbort` result contract, the ordering of the
abort capture, the persistence of every setup-retry lifecycle mutation, the post-target re-read of the record, the binding
of dispatch ownership to the retry event reference, the strength of round-closure terminalisation, and the accuracy of two
prior-stage audit claims. It changes only the five normative `STAGE_01_*` documents it touches and adds eleven
`STAGE_01AB_*` deliverables. No executable source, configuration, DOCX, or PDF is touched; no experiment is run; the A1
baseline (`8.420833333 kWh`) is unchanged; and no Stage-1A–1AA historical artifact is modified.

- **Branch:** `thesis-v45-pocol-stage1ab-retry-record-persistence-abort-contract-lock`
- **Parent commit:** `e5f8aecb5ffea1fa3b4127befe9a510c785a1166` (Stage 1AA)

## Corrections

### AB1 — Use the exact RoundAbort result shape in every contract

`RoundAbort` returns `round_aborted(abort_record)`. Every direct value-propagator now lists that EXACT shaped result in its
RETURNS union, never the bare constructor: `PrepareParticipantsForNewRound`, `ContinueTemplateRefreshAssignmentSetup`,
`TemplateRefresh`, and `FullRangeExhaustNoSolution` are shaped, and `SetupRetryEvent`'s RETURNS names
`round_aborted(abort_record)` ONCE and ENUMERATES the re-run target dispositions explicitly (no vague "target procedure's
disposition"). A whole-file audit classifies every `round_aborted` occurrence as an exact pattern match with payload, a
constructor invocation with payload, a type/RETURNS declaration with payload, or a prose comment — no result contract uses
a bare `round_aborted` alias. *(Audit: `STAGE_01AB_EXACT_ABORT_CONTRACT_AUDIT.md`; vectors TV236, TV237.)*

### AB2 — Capture RoundAbort before updating target_disposition

Each guard-driven abort in `SetupRetryEvent` (wrong round state, retry budget exhausted, incompatible participant state,
and the AB5 payload-integrity abort) now executes `SET disp <- CALL RoundAbort(...)` FIRST, then persists
`status <- ABORTED` and `target_disposition <- disp` by key, then returns `disp`. The stored `target_disposition` is the
exact `round_aborted(abort_record(RoundID, TemplateID, reason))` returned by `RoundAbort` — never a bare token written
before the abort result exists. *(Audit: `STAGE_01AB_EXACT_ABORT_CONTRACT_AUDIT.md`; vector TV238.)*

### AB3 — Make every setup-retry record update explicitly persistent

`SET rec <- setup_retry_records[SetupRetryID]` is treated as a READ-ONLY snapshot; record-reference write semantics are not
assumed anywhere in the specification. The seat is the only CREATE; every subsequent lifecycle change (`status`,
`target_disposition`, `terminal_closure_pending`, `event_ref`) is an explicit keyed UPDATE of
`setup_retry_records[SetupRetryID]`. `CancelSetupRetriesForRound` iterates `SetupRetryID`s (not detached record values) and
updates each record by key. *(Audit: `STAGE_01AB_RETRY_RECORD_PERSISTENCE_AUDIT.md`; vector TV239.)*

### AB4 — Re-read the record after the target returns

A `SetupRetryEvent` target may synchronously call `RoundAbort` → `CloseRoundAssignments` → `CancelSetupRetriesForRound`,
which PERSISTS `terminal_closure_pending` on this record by key. After `SET disp <- CALL target(...)`, the handler RE-READS
`post_target_rec <- setup_retry_records[SetupRetryID]` and classifies on `post_target_rec.terminal_closure_pending` (the
persisted flag), never the pre-target snapshot — so a record whose round closed finishes `ABORTED` / `CANCELLED` and NEVER
`APPLIED`. *(Audit: `STAGE_01AB_TERMINAL_CLOSURE_VISIBILITY_AUDIT.md`; vector TV240.)*

### AB5 — Bind dispatch ownership to the retry event reference

`SetupRetryEvent` carries `dispatched_event_ref` (the canonical identity of the dispatched event, derivable from
`dispatch_envelope`, equal to the seat-stored `rec.event_ref` for a genuine dispatch). Ownership is verified before the
handler operates on the record: an unknown `SetupRetryID` is a stale no-op (Case A); a known id whose
`dispatched_event_ref ≠ rec.event_ref` is a foreign/replayed event that stale-noops and LEAVES the record `SEATED` for its
genuine queued event (Case B); the genuine event whose payload mismatches the immutable record is integrity corruption of
the owning event that terminalises the record via the declared `setup_retry_payload_integrity_failure` abort (`ABORTED`,
exact stored disposition), cancelling any residual event ref (Case C). The only event a `SEATED` record owns is never
consumed while the record stays `SEATED`. *(Audit: `STAGE_01AB_RETRY_DISPATCH_OWNERSHIP_AUDIT.md`; vectors TV241, TV242.)*

### AB6 — Strengthen round-closure terminalisation

`CancelSetupRetriesForRound` uses keyed persistent UPDATEs and clears a cancelled `SEATED` record's `event_ref` to null,
and asserts, after it completes for `closing_RoundID`: no record has `status = SEATED`; no `SEATED` record has a queued
`event_ref`; every terminalised record has a terminal `target_disposition`; every `APPLYING` record has
`terminal_closure_pending` persisted in the registry. *(Audit: `STAGE_01AB_TERMINAL_CLOSURE_VISIBILITY_AUDIT.md`; vector
TV243.)*

### AB7 — Supersede the inaccurate Stage-1AA audit claims

`STAGE_01AA_ROUND_ABORT_RESULT_AUDIT.md` treated bare `round_aborted` return declarations as exact
`round_aborted(abort_record)` contracts; `STAGE_01AA_RETRY_TERMINALIZATION_AUDIT.md` assumed writes through local `rec`
variables persist in `setup_retry_records`; TV227 did not detect those two mismatches. Those Stage-1AA artifacts are
frozen; the corrections are recorded in `STAGE_01AB_SUPERSESSION_REGISTER.md`. All Stage-1AB audits inspect the final
normative tree only after every normative edit and semantic vector was complete.

## Deliverables (11 new `STAGE_01AB_*` files)

1. `STAGE_01AB_CORRECTION_REPORT.md` (this file)
2. `STAGE_01AB_EXACT_ABORT_CONTRACT_AUDIT.md` (AB1/AB2)
3. `STAGE_01AB_RETRY_RECORD_PERSISTENCE_AUDIT.md` (AB3)
4. `STAGE_01AB_RETRY_DISPATCH_OWNERSHIP_AUDIT.md` (AB5)
5. `STAGE_01AB_TERMINAL_CLOSURE_VISIBILITY_AUDIT.md` (AB4/AB6)
6. `STAGE_01AB_PROCEDURE_SIGNATURE_CALL_AUDIT.md`
7. `STAGE_01AB_PROCEDURE_CALL_GRAPH.md`
8. `STAGE_01AB_SEMANTIC_TEST_VECTORS.md` (TV236–TV243)
9. `STAGE_01AB_SUPERSESSION_REGISTER.md`
10. `STAGE_01AB_CROSS_DOCUMENT_AUDIT.md`
11. `STAGE_01AB_CHECKSUM_MANIFEST.sha256`

## Modified normative documents (5)

`STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_ROUND_STATE_MACHINE.md` (adds §3.10f), `STAGE_01_INVARIANT_CATALOGUE.md`
(I16 Stage-1AB clause), `STAGE_01_TERMINOLOGY.md` (Stage-1AB addendum), `STAGE_01_TRACEABILITY_MATRIX.csv` (rows
R198–R205). The miner state machine is not touched (AB1–AB7 concern the retry-record lifecycle and the abort result
contract only).

## Discipline

Documentation-only; the algorithm remains **PoCol** and the mechanism remains the idle policy within PoCol; the A1
baseline `8.420833333 kWh` is unchanged; the call graph resolves with 86 callables (85 procedures + 1 function) and 0
dangling references (Stage 1AB adds no new procedure — it refines `SetupRetryEvent` and `CancelSetupRetriesForRound` and
shapes the abort RETURNS unions); and Stage 2 is not begun.
