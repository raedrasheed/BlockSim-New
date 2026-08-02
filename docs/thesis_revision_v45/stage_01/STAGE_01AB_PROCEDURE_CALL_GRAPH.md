# Stage 1AB — Procedure Call Graph

This document resolves the procedure call graph of `STAGE_01_PROTOCOL_PSEUDOCODE.md` after corrections AB1–AB7 and records
that it contains NO dangling call. Stage 1AB adds NO new procedure — it refines `SetupRetryEvent` and
`CancelSetupRetriesForRound` in place, shapes the abort RETURNS unions, and adds the `dispatched_event_ref` input — so the
defined count remains **86** callables (85 `PROCEDURE` + 1 `FUNCTION`), unchanged from Stage 1AA.

## 1. Resolution method

- **Defined symbols:** every `^PROCEDURE <name>` / `^FUNCTION <name>` header (86 unique names).
- **Call targets:** every `CALL <name>` invocation target.
- **Dispatched handlers:** event handlers (e.g. `SetupRetryEvent`) are seated via `ScheduleEvent` and dispatched by
  `ProcessEventTime`, not via `CALL`; a defined handler with no `CALL` site is NOT dangling.
- **Dangling test:** `{ call targets } \ { defined symbols }`. The only lowercase tokens the raw scan surfaces are `is`
  and `this`, from prose fragments, not invocations. **Real dangling calls = 0.**

## 2. AB-touched edges (no new nodes)

Stage 1AB changes the DATA, RESULT SHAPES, and PERSISTENCE DISCIPLINE across existing edges; the call topology is unchanged
from Stage 1AA.

### 2.1 `RoundAbort` (AB1/AB2) — exact result on every abort edge

`RoundAbort` returns `round_aborted(abort_record)` and is the sole abort producer. The `RETURN CALL RoundAbort(...)`
propagators — `SetupRetryEvent`, `PrepareParticipantsForNewRound`, `ContinueTemplateRefreshAssignmentSetup`,
`TemplateRefresh`, `FullRangeExhaustNoSolution` — now carry the EXACT shaped `round_aborted(abort_record)` in their RETURNS
unions (AB1). Inside `SetupRetryEvent`, each guard-driven abort edge is `SET disp <- CALL RoundAbort(...)` (captured, AB2)
rather than `RETURN CALL`, so the result can be persisted by key before it is returned. The AB5 payload-integrity abort
adds one more `CALL RoundAbort` edge inside `SetupRetryEvent` with `reason = setup_retry_payload_integrity_failure`. No new
node; the callee is the existing `RoundAbort`.

### 2.2 `SetupRetryEvent` (AB1/AB2/AB3/AB4/AB5) — dispatched handler

- In-edges (unchanged): `ScheduleEvent(SetupRetryEvent, ...)` from `PrepareParticipantsForNewRound` and
  `ContinueTemplateRefreshAssignmentSetup`; each seat publishes `setup_retry_records[srid]` with `status = SEATED`,
  `event_ref = event_ref`, `terminal_closure_pending = false`. `dispatched_event_ref` is materialised by `ProcessEventTime`
  at dispatch and compared to `rec.event_ref` (AB5).
- Out-edges: → `PrepareParticipantsForNewRound` (PARTICIPANT_SETUP), → `ContinueTemplateRefreshAssignmentSetup`
  (TEMPLATE_REFRESH_SETUP), → `RoundAbort` (captured, AB2, including the AB5 integrity abort). After the target returns the
  handler RE-READS `setup_retry_records[SetupRetryID]` (AB4) — a registry read, not a call edge.

### 2.3 `CancelSetupRetriesForRound` (AB3/AB6)

- In-edge (unchanged): `CloseRoundAssignments` → `CALL CancelSetupRetriesForRound(...)` (defined once, called once).
- Body: iterates matching `SetupRetryID`s and performs keyed UPDATEs (`status`, `target_disposition`,
  `terminal_closure_pending`, `event_ref`) — no `CALL` out-edge; it CANCELs a queued `event_ref` on `EQ`.

### 2.4 The abort propagators (AB1)

`PrepareParticipantsForNewRound`, `ContinueTemplateRefreshAssignmentSetup`, `TemplateRefresh`, `FullRangeExhaustNoSolution`
retain their `RETURN CALL RoundAbort(...)` edges; only their RETURNS shapes were made exact. No call edge changed.

## 3. Full defined-procedure inventory (86)

Identical to `STAGE_01AA_PROCEDURE_CALL_GRAPH.md`'s 86 callables. No procedure was added, removed, or renamed in Stage
1AB; `SetupRetryEvent`, `CancelSetupRetriesForRound`, `RoundAbort`, `PrepareParticipantsForNewRound`,
`ContinueTemplateRefreshAssignmentSetup`, `TemplateRefresh`, and `FullRangeExhaustNoSolution` had their bodies / signatures
/ RETURNS updated in place.

## 4. Result

The Stage-1AB call graph resolves with **86 defined callables and 0 dangling calls**. `SetupRetryEvent` remains a
dispatched handler (reachable through `ScheduleEvent` / `ProcessEventTime`) with its abort captured (`SET disp <- CALL
RoundAbort`, AB2) and its lifecycle mutations persisted by key (AB3); `CancelSetupRetriesForRound` remains defined once and
called once from `CloseRoundAssignments`; `RoundAbort` remains the sole abort producer returning the exact
`round_aborted(abort_record)` (AB1).
