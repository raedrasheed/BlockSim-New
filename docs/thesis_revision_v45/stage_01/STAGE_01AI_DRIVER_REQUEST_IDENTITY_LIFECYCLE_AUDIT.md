# Stage 1AI — Driver-Request Identity & Lifecycle Audit (AI3/AI4)

**Scope.** This is a documentation-only formal-spec audit of corrections **AI3** (stable driver-request
identity at admission) and **AI4** (executable driver-request lifecycle) for the PoCol Stage-1 protocol.
It verifies the FINAL normative tree with exact `file:line` anchors read from
`docs/thesis_revision_v45/stage_01/STAGE_01_PROTOCOL_PSEUDOCODE.md` (all line references below are into
that file). No source, config, DOCX/PDF, or Stage-1A..1AH artifact was modified; the only file created is
this audit. All naming follows PoCol conventions.

Procedures and structures read in full for this audit: `AdmitDriverRequest`, `SetDriverRequestStatus`,
`CompleteDriverRequestOnDispatch`, `SeatMinerRegister`, `SeatReserveActivate`, `SeatPendingDriverRequests`,
`CancelQueuedEvent`, the dispatch-completion block of `ProcessEventTime`, `STRUCTURE RunContext`
(`RunInitialise`), and `STRUCTURE driver_request`.

---

## 1. The two defects being corrected

The Stage-1AH driver-request model (`driver_request` record produced by `AdmitDriverRequest`, seated by the
named owners, terminalised by `SeatPendingDriverRequests`) shipped two normative gaps that AI3/AI4 close.
Both are confirmed against the AH baseline preserved in the working diff of the pseudocode file.

**Defect 1 — AH treated SEATED as terminal, with no CONSUMED / CANCELLED producer.**
Under AH the `DriverRequestStatus` enum already *declared* `CONSUMED` and `CANCELLED`, but no procedure ever
produced those edges. `SeatPendingDriverRequests` wrote the status field *directly* — the AH baseline had, in
its seat-result switch, `SET dr.status <- SEATED ; SET dr.seated_event_ref <- event_ref` on a successful seat
and `SET dr.status <- REJECTED ; ...` on a failed seat — and the `driver_request.disposition` field was
documented as "the terminal disposition recorded on SEATED / REJECTED / CANCELLED". SEATED was therefore an
effectively **terminal success state**: once a request seated, nothing transitioned it to CONSUMED when its
wrapper event actually dispatched, and nothing reconciled it to CANCELLED when its seat was cancelled. A
dispatched-or-cancelled seat left its `driver_request` dangling forever in SEATED, and the actual handler
result was never recorded on the request. Because the mutations were open-coded across the intake procedure,
there was also no single guard preventing an illegal edge or a SEATED-while-consumed overwrite.

**Defect 2 — AH admission was not replay-idempotent.**
Under AH, `AdmitDriverRequest` unconditionally advanced the per-run ordinal on every call
(`SET RunContext.driver_request_seq <- RunContext.driver_request_seq + 1`) and its `RETURNS` clause was only
`driver_request_admitted(DriverRequestID)` — there was no stable logical identity derived from the request's
own content, no registry keyed by that identity, and no `already_admitted` result. A re-admission of the SAME
logical request (the same external miner join, or the same ordinary reserve deficit) therefore minted a
**second** `DriverRequestID`, a second `driver_request` record, and a second downstream seat / EventRef /
protocol effect. Idempotence existed only at the seat layer (AH3 `driver_event_seat`), not at the admission
layer, so replay was not absorbed where it enters the system.

**The fixes.** AI3 introduces a stable `logical_request_id` (ExternalDriverRequestID) derived from the
request's own content *before* any sequence is minted, a `driver_request_by_logical_id` replay registry, and
an `already_admitted` return that yields the SAME `DriverRequestID`. AI4 makes the lifecycle executable: a
declared legal-transition table; a single guarded CAS-style mutator `SetDriverRequestStatus`; an immutable
`driver_request_by_seat_event_ref` reverse binding published atomically with the seat; a dispatcher-owned
completion point `CompleteDriverRequestOnDispatch` (SEATED → CONSUMED) called on the success path and every
defensive CONSUME path; `CancelQueuedEvent` reconciliation (SEATED → CANCELLED); and a `consumed_result`
field recording the actual handler result on CONSUMED.

---

## 2. AI3 — Stable driver-request identity at admission

| # | Claim | Evidence (`STAGE_01_PROTOCOL_PSEUDOCODE.md`) | Verdict |
|---|-------|----------------------------------------------|---------|
| AI3.1 | `AdmitDriverRequest` derives a STABLE logical identity from the request's own content **before** advancing `driver_request_seq`. | Derivation `SWITCH kind` at **1734–1736** precedes the sequence advance at **1742**; comment **1730–1733** states "derive the STABLE logical identity … BEFORE advancing the sequence". | PASS |
| AI3.2 | MINER_JOIN keyed by a deterministic JoinRequestID via `JOIN_REQUEST(join_request_id(payload.join_request))`. | **1735**: `CASE MINER_JOIN: SET logical_id <- JOIN_REQUEST(join_request_id(payload.join_request))`. | PASS |
| AI3.3 | ORDINARY_RESERVE_DEFICIT keyed by a deterministic ReserveActivationRequestID via `RESERVE_ACTIVATION(...)`. | **1736**: `CASE ORDINARY_RESERVE_DEFICIT: SET logical_id <- RESERVE_ACTIVATION(payload.RoundID_at_seat, deficit_identity(payload.deficit))`. | PASS |
| AI3.4 | It checks `driver_request_by_logical_id`; on a HIT returns `driver_request_already_admitted(existing DriverRequestID)` — the SAME id — and mints NO new sequence. | Replay check **1739**: `IF RunContext.driver_request_by_logical_id[logical_id] EXISTS:`; **1740** returns `driver_request_already_admitted(RunContext.driver_request_by_logical_id[logical_id])` (`# AI3: same DriverRequestID`). The `RETURN` occurs *before* the sequence advance at **1742**, so no id is minted. | PASS |
| AI3.5 | Only a genuinely NEW logical request advances the sequence and registers `driver_request_by_logical_id[logical_id] <- drid`. | Advance guarded to the miss path — **1742** `SET ...driver_request_seq <- ...+ 1`, **1743** `SET drid <- (RunContext.RunID, RunContext.driver_request_seq)`; registration **1749** `SET RunContext.driver_request_by_logical_id[logical_id] <- drid` (`# AI3: register the stable-identity replay key`). | PASS |
| AI3.6 | `driver_request` STRUCTURE has a `logical_request_id` field carrying the stable logical identity. | STRUCTURE `driver_request` field **3062–3066**: `logical_request_id : AI3 — the STABLE logical identity (ExternalDriverRequestID) …`. Constructed at **1744** `driver_request(DriverRequestID = drid, logical_request_id = logical_id, …)`. | PASS |
| AI3.7 | RunContext declares `driver_request_by_logical_id`, initialised empty, and it is in RETURNS. | Declared **3005–3010** (`driver_request_by_logical_id : AI3 — map DriverRequestLogicalID -> DriverRequestID …`); initialised empty **3127** `INITIALISE driver_request_by_logical_id <- empty map`; returned **3143** (`driver_request_by_logical_id, driver_request_by_seat_event_ref, # AI3/AI4`). | PASS |
| AI3.8 | The advanced-ordinal-only-on-new invariant is documented on the field. | `driver_request_seq` field note **3000–3001**: "AI3: advanced ONLY when a GENUINELY NEW logical request is admitted (never on a replay)". | PASS |

**AI3 note.** The derivation is total over the two admissible kinds and is content-addressed
(`join_request_id(...)` / `deficit_identity(...)`), so two genuinely distinct requests derive distinct logical
ids while a replay derives the same one. The replay check and the registry write bracket the sequence advance,
so admission-layer idempotence holds strictly before any per-run identity, EventRef, or protocol effect is
created. **AI3 verdict: PASS.**

---

## 3. AI4 — Executable driver-request lifecycle

| # | Claim | Evidence (`STAGE_01_PROTOCOL_PSEUDOCODE.md`) | Verdict |
|---|-------|----------------------------------------------|---------|
| AI4.1 | Legal-transition table declared: PENDING→{SEATED,REJECTED,CANCELLED}; SEATED→{CONSUMED,CANCELLED}; CONSUMED/REJECTED/CANCELLED terminal. | STRUCTURE RunContext note **3021–3026** (`AI4 — DriverRequestStatus LEGAL TRANSITION TABLE …`: `PENDING -> SEATED | REJECTED | CANCELLED`; `SEATED -> CONSUMED | CANCELLED`; "CONSUMED and REJECTED and CANCELLED are TERMINAL"). Enforced inline in the mutator at **1772–1774**. | PASS |
| AI4.2 | `SetDriverRequestStatus(RunContext, DriverRequestID, expected_status, new_status, disposition)` is the SINGLE guarded mutator with a CAS-style guard producing `status_mismatch`. | Procedure header **1760**; signature **1761**; CAS guard **1768** `IF dr.status != expected_status:` → **1769** `RETURN driver_request_status_mismatch(...)` (`# AI4: a CAS-style guard (no blind overwrite)`). | PASS |
| AI4.3 | It rejects illegal edges with `driver_request_illegal_transition` and can never take SEATED-while-CONSUMED/CANCELLED. | Illegal-edge guard **1772–1774** `RETURN driver_request_illegal_transition(...)` (`# AI4: never SEATED-while-CONSUMED/CANCELLED`). Because CONSUMED/CANCELLED are terminal and any `new_status = SEATED` requires `expected_status = PENDING` (the CAS guard at 1768 fails for a CONSUMED/CANCELLED record), no SEATED-after-terminal edge is reachable. Unknown-id path is a declared no-op **1765–1766**. | PASS |
| AI4.4 | No other procedure writes `dr.status` directly — the ONLY direct write to a driver_request status is inside `SetDriverRequestStatus`. | See §4 (single-guarded-mutator check). Sole write **1775** `SET dr.status <- new_status`. | PASS |
| AI4.5 | Immutable reverse binding `driver_request_by_seat_event_ref` is a RunContext field, initialised empty, in RETURNS. | Declared **3011–3016**; initialised empty **3128** `INITIALISE driver_request_by_seat_event_ref <- empty map`; returned **3143**. | PASS |
| AI4.6 | The reverse binding is published ATOMICALLY with the seat in `SeatMinerRegister`. | `SeatMinerRegister` `ATOMICALLY` block **1642–1648**; binding published at **1644** `SET RunContext.driver_request_by_seat_event_ref[event_ref] <- driver_request.DriverRequestID` inside the same atomic block that sets SEATED (**1646–1647**) and clears the pending index (**1648**). | PASS |
| AI4.7 | The reverse binding is published ATOMICALLY with the seat in `SeatReserveActivate`. | `SeatReserveActivate` `ATOMICALLY` block **1680–1687**; binding published at **1682**, SEATED set at **1685–1686**, pending index cleared at **1687**. | PASS |
| AI4.8 | `CompleteDriverRequestOnDispatch` resolves the exact request from the seat EventRef and transitions SEATED→CONSUMED. | Procedure **1784**; resolves via reverse binding **1790–1792** (`SET drid <- RunContext.driver_request_by_seat_event_ref[seat_event_ref]`); transition **1795** `RETURN CALL SetDriverRequestStatus(..., expected_status = SEATED, new_status = CONSUMED, disposition = disposition)`. Non-driver EventRef → declared no-op **1790–1791** (`driver_request_not_a_seat`). | PASS |
| AI4.9 | `ProcessEventTime` calls it after the handler dispatch on the SUCCESS path with `driver_request_consumed(handler_result)`. | Success path **362–363**: `CALL CompleteDriverRequestOnDispatch(RunContext, seat_event_ref = er, disposition = driver_request_consumed(handler_result))` immediately after the DISPATCHING→CONSUMED atomic block (**353–355**) that captured `handler_result` at **351**. | PASS |
| AI4.10 | It is also called on the 3 defensive CONSUME paths with `driver_request_consumed_dispatch_failure(...)`. | (a) corrupt-record integrity path **325–326** `...dispatch_failure(dispatch_integrity_failure)`; (b) missing-RoundContext path **336–337** `...dispatch_failure(dispatch_context_unavailable)`; (c) handler-binding-failure path **347–348** `...dispatch_failure(dispatch_binding_failed)`. Each follows its own DISPATCHING→CONSUMED atomic block. | PASS |
| AI4.11 | `CancelQueuedEvent` reconciles a cancelled seat's driver_request to CANCELLED via the reverse binding + `SetDriverRequestStatus`. | `CancelQueuedEvent` QUEUED-cancel branch **1061–1064**: `IF RunContext_bound.driver_request_by_seat_event_ref[EventRef] EXISTS:` → `SET drid <- ...` → `CALL SetDriverRequestStatus(..., expected_status = SEATED, new_status = CANCELLED, disposition = driver_request_seat_cancelled(...))` (`# AI4: SEATED -> CANCELLED (never resurrected)`). | PASS |
| AI4.12 | `driver_request` has a `consumed_result` field recording the actual handler result on CONSUMED. | STRUCTURE field **3082–3083** (`consumed_result : AI4 — the ACTUAL handler result … null until CONSUMED`); written in the mutator **1777–1778** `IF new_status = CONSUMED AND disposition = driver_request_consumed(handler_result): SET dr.consumed_result <- handler_result`. Initialised `null` at construction **1747**. | PASS |
| AI4.13 | `SeatPendingDriverRequests` routes seat failures to REJECTED via `SetDriverRequestStatus` and removes them from the pending index. | Seat-failed case **1844–1847**: `CALL SetDriverRequestStatus(..., expected_status = PENDING, new_status = REJECTED, disposition = driver_request_rejected(reason))` then `REMOVE drid FROM RunContext.pending_driver_request_index`. Stale-scope rejection likewise **1824–1826**. | PASS |
| AI4.14 | No SEATED request lingers in the pending index. | On a successful seat the owner removes the id inside the atomic seat block (**1648**, **1687**); `SeatPendingDriverRequests` counts it as already terminalised (**1835–1836**) and, for a replay `already_seated`, defensively removes it (**1843**). REJECTED requests are removed (**1826**, **1847**). Field note **3002–3004** confirms "a SEATED/CONSUMED/REJECTED/CANCELLED request never lingers in the index". | PASS |

**AI4 verdict: PASS.**

---

## 4. Single-guarded-mutator check (dr.status is written ONLY in SetDriverRequestStatus)

The AI4 invariant is that every mutation of a `driver_request`'s `status` routes through the single guarded
mutator `SetDriverRequestStatus`, so no procedure overwrites the status directly and no illegal edge is ever
taken (stated at **1762–1763** and **3027**). Verified by exhaustive search for direct status-field writes.

**Search 1 — all `.status <-` field writes in the pseudocode** (`grep -n '\.status\s*<-'`):

| Line | Write target | Record type | Inside `SetDriverRequestStatus`? |
|------|--------------|-------------|----------------------------------|
| **1775** | `dr.status <- new_status` | `driver_request` | **YES** — the sole guarded write |
| 3881 | `setup_retry_records[SetupRetryID].status <- new_status` | setup_retry_record (AC subsystem) | n/a — not a driver_request |
| 4763 | `recovery_decisions[decision_id].status <- new_status` | recovery_decision | n/a — not a driver_request |
| 4805, 4885, 4895, 5087, 5156, 5189, 5193, 5200, 5207, 5215, 5224, 5234 | `recovery_work[...].status <- ...` | recovery_work | n/a — not a driver_request |

Only line **1775** targets a `driver_request` record's `status`, and it lies inside `SetDriverRequestStatus`
(procedure header **1760**, body **1764–1779**). Every other `.status <-` write is on a distinct record type
(setup-retry, recovery-decision, recovery-work) governed by its own subsystem owner and is outside the scope
of the driver-request lifecycle.

**Search 2 — every SEATED/CONSUMED/REJECTED/CANCELLED transition on a driver_request goes through the
mutator.** The producers of driver-request status changes are: `SeatMinerRegister` **1646–1647**,
`SeatReserveActivate` **1685–1686** (PENDING→SEATED); `CompleteDriverRequestOnDispatch` **1795**
(SEATED→CONSUMED); `CancelQueuedEvent` **1063–1064** (SEATED→CANCELLED); `SeatPendingDriverRequests`
**1824–1825**, **1840–1841**, **1845–1846** (PENDING→REJECTED / defensive PENDING→SEATED); and the genesis
in-dispatch reject path **1385**. Each is a `CALL SetDriverRequestStatus(...)`; none writes `dr.status`
directly. This is exactly the AH regression closed: the AH baseline of `SeatPendingDriverRequests` performed
open-coded `SET dr.status <- SEATED` / `SET dr.status <- REJECTED` writes, which no longer exist in the final
tree.

**Result: PASS** — `dr.status` is written in exactly one place, `SetDriverRequestStatus` line **1775**, and
all lifecycle edges route through it under the CAS guard and legal-transition table.

---

## 5. Cross-cutting consistency notes

- **Atomicity of seat + binding + SEATED + de-index.** In both seat owners the reverse binding, the
  `seated_event_ref` write, the PENDING→SEATED transition, and the pending-index removal occur inside one
  `ATOMICALLY` block (`SeatMinerRegister` **1642–1648**; `SeatReserveActivate` **1680–1687**), so the reverse
  binding and the SEATED status can never be observed apart from each other — a precondition for the
  dispatcher's completion point to resolve the exact request.
- **No resurrection of terminal requests.** A request already CANCELLED via `CancelQueuedEvent` presents a
  `status_mismatch` when `CompleteDriverRequestOnDispatch` later attempts SEATED→CONSUMED (guard **1768–1769**,
  documented at **1793–1794**), so it is left terminal rather than driven back to CONSUMED. Symmetrically a
  CONSUMED request cannot be cancelled. This is the executable form of "SEATED is no longer terminal, and the
  terminal states genuinely are".
- **Dispatcher owns completion once.** `CompleteDriverRequestOnDispatch` is the single place a driver_request
  becomes CONSUMED (**356–363**), invoked after the DISPATCHING→CONSUMED atomic completion on the success path
  and each defensive path; a non-driver event carries no reverse binding and is a declared no-op
  (**1790–1791**), so ordinary in-round events and the bootstrap `RoundInitialiseEvent` are correctly skipped.
- **RETURNS closure.** Both AI3 and AI4 RunContext fields (`driver_request_by_logical_id`,
  `driver_request_by_seat_event_ref`) are initialised empty in `RunInitialise` (**3127–3128**) and appear in
  the `RETURNS` tuple (**3143**), so they are genuinely part of the per-run state, not dangling locals.

---

## 6. Overall verdict

**PASS.** Every AI3 and AI4 claim is substantiated by exact anchors in the final normative tree. AI3
establishes admission-layer replay idempotence: a stable content-derived `logical_request_id` is computed and
checked against `driver_request_by_logical_id` before any sequence is minted, and a replay returns the SAME
`DriverRequestID` with no new effect. AI4 makes the lifecycle executable and closed: a declared legal-transition
table, a single CAS-guarded mutator `SetDriverRequestStatus` that is the sole writer of `dr.status`
(verified line 1775 only), an immutable seat reverse binding published atomically with each seat, a
dispatcher-owned SEATED→CONSUMED completion on the success and all three defensive CONSUME paths, a
SEATED→CANCELLED reconciliation in the sole queue-owner cancellation, a `consumed_result` capturing the actual
handler result, and a pending index that never retains a SEATED request. Both AH defects — SEATED-as-terminal
with no CONSUMED/CANCELLED producer, and non-idempotent admission — are fully closed. **No FAIL was found.**
