# Stage 1AF — Supersession Register (AF10)

This register records, per correction AF10, the SPECIFIC inaccurate claims of the (now frozen) Stage-1AE audits that
Stage 1AF supersedes. Stage-1A through Stage-1AE lettered artifacts are UNCHANGED on disk; this register is the authoritative
statement of which prior audit conclusions were reached on an inaccurate reading of the same contract and how the Stage-1AF
normative tree corrects them. The algorithm remains **PoCol**; the mechanism is the idle policy within PoCol; the A1 baseline
(`8.420833333 kWh`) is unchanged.

Every Stage-1AF audit inspects the FINAL normative tree (`STAGE_01_PROTOCOL_PSEUDOCODE.md` and companions) only AFTER every
normative edit (AF1–AF9) and every semantic vector (TV273–TV287) was complete.

---

## 1. `STAGE_01AE_EVENT_HANDLER_SCHEMA_AUDIT` — treated derived / tie-key identities as handler payload

- **Inaccurate claim.** The AE handler-schema audit marked `RoundInitialise`, `TemplateCommit`, `MinerRegister`, and
  `WakeCompleteEvent` as "payload matches handler INPUTS" against the AE4 descriptive table, whose "required
  immutable_payload fields" column listed values that are NOT the handler's stored inputs.
- **Why it was wrong.** `RoundInitialise` MINTS `RoundID` (its INPUTS are `config, RunContext, prior_state`), yet the AE4
  row declared payload `= RoundID`; `TemplateCommit` MINTS `TemplateID` from `candidate_template`, yet AE4 declared
  `RoundID, TemplateID`; `MinerRegister` DERIVES `MinerID` from `join_request`, yet AE4 declared `MinerID`;
  `WakeCompleteEvent`'s INPUTS are `MinerID, target_assignment`, yet AE4 declared `MinerID, AssignmentID` (omitting
  `assignment_version`, which its own tie key used). The audit conflated a handler-DERIVED id and a stable-tie-key identity
  with STORED handler payload.
- **AF correction.** AF1 replaces the descriptive schema with an executable `event_descriptor` per type that keeps the five
  categories apart (handler inputs / runtime context / stored payload / handler-derived values / stable ordering keys) and
  corrects each row: `RoundInitialiseEvent` payload `= { round_setup_seq }` (RoundID derived); `TemplateCommitEvent` payload
  `= { RoundID_at_seat, candidate_template }` (TemplateID derived); `MinerRegisterEvent` payload `= { join_request }` (MinerID
  derived); `WakeCompleteEvent` payload `= { MinerID, AssignmentID, assignment_version }` with the dispatcher resolving
  `target_assignment`. AF4 supplies the wrappers; AF2 supplies the exact binding. Verified by
  `STAGE_01AF_EVENT_DESCRIPTOR_AUDIT.md` and `STAGE_01AF_DRIVER_EVENT_BINDING_AUDIT.md`.

## 2. `STAGE_01AE_DISPATCH_SIGNATURE_AUDIT` — claimed a scheduling_context wrapper while the line passed a bare envelope

- **Inaccurate claim.** The AE dispatch-signature audit stated that `ReserveActivate` "receives the envelope wrapped as
  `scheduling_context = ORDINARY_DISPATCH(dispatch_envelope)`."
- **Why it was wrong.** The AE5 executable dispatch line in `ProcessEventTime` passed `dispatch_envelope = ctx.dispatch_envelope`
  IFF `recv env = yes` — i.e. a BARE `dispatch_envelope`, not a `scheduling_context` wrapper. The audit described intended
  behaviour that the executable line did not implement; `ReserveActivate`'s declared parameter is `scheduling_context`, so the
  bare envelope was an undeclared/aliased argument.
- **AF correction.** AF2's `BuildHandlerInvocation` binds the exact declared arguments, and AF4's `ReserveActivateEvent`
  wrapper receives `dispatch_envelope` and BUILDS `scheduling_context = ORDINARY_DISPATCH(dispatch_envelope)` for its
  `ReserveActivate` call, so a bare envelope never reaches `ReserveActivate`. Verified by
  `STAGE_01AF_DISPATCH_ADAPTER_AUDIT.md` (TV277).

## 3. `STAGE_01AE_QUEUE_REGISTRY_COHERENCE_AUDIT` — relied on an ambiguous QUEUED-projection convention without an executable POP

- **Inaccurate claim.** The AE coherence audit certified invariants (a)–(f) of I21 "hold literally under this projection,"
  where `EQ.event_queue` was described as "the QUEUED PROJECTION of the registry."
- **Why it was wrong.** `ProcessEventTime` never executed an explicit POP; it changed `queue_status` and RELIED on a prose
  convention that a status change "REMOVES the EventRef from the pending frontier by construction." Coherence was asserted by
  a definitional convention rather than by an executable dequeue, and the dispatch context was set field-by-field, not atomically.
- **AF correction.** AF5 makes `ProcessEventTime` ATOMICALLY POP the front EventRef, assert `QUEUED`, set `DISPATCHING`, and
  set the complete `EQ.current_*` in one atomic step; the completion sets `CONSUMED` and clears the context atomically.
  `EQ.event_queue` is the ONE representation (pending QUEUED only); the "by projection" convention is removed. I21 is
  strengthened (AF5 clause). Verified by `STAGE_01AF_QUEUE_POP_AND_CONTEXT_AUDIT.md` (TV283, TV284).

## 4. `STAGE_01AE_FIRE_AND_FORGET_RESULT_AUDIT` — missed the absent StartHashing RETURN and the HashWorkEvent shape mismatch

- **Inaccurate claim.** The AE fire-and-forget audit certified that `ScheduleNextHashWork` / `StartHashing` / `HashWorkEvent`
  report results truthfully with agreeing shapes.
- **Why it was wrong.** `StartHashing`'s body had NO `RETURN` on the `hash_work_seated` success path — the declared
  `hashing_started` result was unreachable (a silent fall-through). `HashWorkEvent`'s continuation returned a BARE
  `hash_work_seated`/`hash_work_not_seated` (via `RETURN CALL ScheduleNextHashWork(...)`) while its declared RETURNS union
  wrapped these in `continued(...)` — a body/RETURNS shape mismatch the audit did not detect.
- **AF correction.** AF7 gives `StartHashing` an explicit `RETURN hashing_started(event_ref)` on success (and
  `hashing_not_started(reason)` at the horizon), and wraps `HashWorkEvent`'s continuation as
  `continued(CALL ScheduleNextHashWork(...))` so the body shape matches the RETURNS union exactly; the `WakeCompleteEvent`
  caller's RETURNS is reconciled. Verified by `STAGE_01AF_HASH_RESULT_CONTRACT_AUDIT.md` (TV285).

## 5. `STAGE_01AE_CROSS_DOCUMENT_AUDIT` — therefore incorrectly marked gates 3, 5, 6, 10, 12, 13 PASS

- **Inaccurate claim.** The AE cross-document audit marked its acceptance gates 3, 5, 6, 10, 12, and 13 PASS.
- **Why it was wrong.** Those gates depended on the four audits above: the dispatch-schema/handler-INPUTS gate (3) inherited
  the payload/derived-value conflation; the dispatch-signature gate (5) inherited the bare-envelope-vs-wrapper claim; the
  queue-coherence gate (6) inherited the projection-not-POP convention; the fire-and-forget gate (10) inherited the missing
  RETURN and shape mismatch; the schema-completeness gate (12) inherited an incomplete (required-fields-only) validation; and
  the cross-document consistency gate (13) aggregated the above. With the underlying audits inaccurate, the PASS marks were
  unsound.
- **AF correction.** AF1–AF9 correct the underlying contracts and AF3 additionally enforces the exact closed key set,
  microphase match, and tie-key derivability (superseding the AE7 required-fields-only validation). `STAGE_01AF_CROSS_DOCUMENT_AUDIT.md`
  re-evaluates every gate against the final Stage-1AF tree.

---

## 6. Frozen-artifact statement

- Stage-1A … Stage-1AE lettered artifacts (`STAGE_01A*`…`STAGE_01AE_*`) are UNCHANGED on disk; this register is the sole
  record of their superseded conclusions.
- No executable source, configuration, DOCX, or PDF was modified; no experiment was run; the A1 baseline `8.420833333 kWh`
  is unchanged; Stage 2 is not begun.
- The Stage-1AF corrections live only in the five modified `STAGE_01_*` normative documents and the new `STAGE_01AF_*`
  deliverables (`STAGE_01AF_CHECKSUM_MANIFEST.sha256`).
