# Stage 1AD — Dispatch-Integrity Context Audit (AD5 + AD8)

This audit verifies corrections **AD5 — the dispatcher-owned `OrdinaryDispatchContext`** and **AD8 — completeness + integrity
of the dispatched record**. AD5 requires that `ProcessEventTime` construct and own a complete
`OrdinaryDispatchContext = (dispatch_envelope, dispatched_event_ref)` from the trusted central `queued_event_record` and its
`EventRef`, delivering `dispatch_envelope` to every ordinary handler while passing `dispatched_event_ref` ONLY to a handler
whose declared signature includes it (Design B). AD8 requires that `ScheduleEvent` reject constructing an incomplete record,
that `ProcessEventTime` dispatch from the trusted stored record with a defensive corruption path, and that
`HandleDispatchIntegrityFailure` terminalise a corrupt record from the trusted `EventRef` — never letting a malformed untrusted
envelope become the transition identity for round closure. The audit was generated AFTER the normative documents
(`STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_ROUND_STATE_MACHINE.md`, `STAGE_01_TERMINOLOGY.md`) and the Stage-1AD semantic
test vectors (`STAGE_01AD_SEMANTIC_TEST_VECTORS.md`, TV252–TV261) were final; it reads them read-only and modifies nothing. The
A1 baseline `8.420833333 kWh` is unchanged, and the binding PoCol naming rule is preserved: the algorithm is **PoCol** and the
mechanism under audit is the idle policy within PoCol.

Scope is documentation-only. Line anchors are approximate (`~L`). Quotes are reproduced verbatim from the current normative
documents. AD5 checks are corroborated by TV256 (`STAGE_01AD_SEMANTIC_TEST_VECTORS.md`, ~L62–70); AD8 checks by TV259
(~L94–107).

---

## Checks

| Check | Result |
|-------|--------|
| **C1 (AD5).** `OrdinaryDispatchContext` is the two-field structure `(dispatch_envelope, dispatched_event_ref)`, declared dispatcher-owned. | **PASS** — `STRUCTURE OrdinaryDispatchContext` (`STAGE_01_PROTOCOL_PSEUDOCODE.md`, ~L515–521): `the complete dispatcher-owned context for one ordinary dispatch`, with `dispatch_envelope : the immutable complete ordinary-event envelope from the queued_event_record` and `dispatched_event_ref : EventRef — the record's own event_ref (the ACTUAL event being dispatched)`. Cross-checked by §3.10h AD5 (`STAGE_01_ROUND_STATE_MACHINE.md`, ~L987–990) and terminology (`STAGE_01_TERMINOLOGY.md`, ~L1098–1101). |
| **C2 (AD5).** `ProcessEventTime` CONSTRUCTS the context from the queued record + its `EventRef` (trusted stored record), and owns it. | **PASS** — `PROCEDURE ProcessEventTime` (~L212, ~L222): `SET record <- queued_event_registry[er]` then `SET ctx <- OrdinaryDispatchContext(dispatch_envelope = record.dispatch_envelope, dispatched_event_ref = er)   # AD5`, prefaced (~L217) by `MATERIALISE the dispatch identity from the STORED record (er + record.dispatch_envelope), never from ambient state`. TV256 (~L65–66) drives exactly this construction. |
| **C3 (AD5).** Design B: every ordinary handler receives `dispatch_envelope`; `dispatched_event_ref` is passed CONDITIONALLY, IFF the handler's declared signature includes it. | **PASS** — `ProcessEventTime` (~L233–237): `DISPATCH record.event_type WITH immutable_payload = record.immutable_payload, dispatch_envelope = ctx.dispatch_envelope, (AND dispatched_event_ref = ctx.dispatched_event_ref IFF record.event_type's signature declares it)`. The `IFF … signature declares it` guard is explicit. TV256 Expected (~L68–70): `dispatched_event_ref = ctx.dispatched_event_ref is passed ONLY to SetupRetryEvent`. |
| **C4 (AD5).** NO undeclared named argument is injected into a handler that omits `dispatched_event_ref`. | **PASS** — `ProcessEventTime` (~L234–235): `pass dispatched_event_ref ONLY to a handler whose declared signature includes it (currently only SetupRetryEvent). No undeclared named argument is injected into a handler that omits it.` Restated in `STRUCTURE OrdinaryDispatchContext` (~L519). TV256 Expected (~L69–70): `No undeclared named argument is injected into the handler that omits it, and no handler derives its own dispatched_event_ref from ambient state.` No FAIL: no dispatch site injects the ref unconditionally. |
| **C5 (AD5).** The one handler declaring `dispatched_event_ref` (`SetupRetryEvent`) receives it as a MANDATORY input supplied by the dispatcher, never read from payload/ambient. | **PASS** — `PROCEDURE SetupRetryEvent` INPUTS (~L2240, ~L2249–2252): `INPUTS: RoundContext, dispatch_envelope, dispatched_event_ref, …`; `dispatched_event_ref is the canonical EventRef of THIS dispatched SetupRetryEvent, supplied by ProcessEventTime from the OrdinaryDispatchContext it built (EQ.current_event_ref). It is NEVER read from the payload and NEVER derived by prose; it is a MANDATORY input`. TV256 (~L66). |
| **C6 (AD8).** `ScheduleEvent` asserts `immutable_payload` contains EVERY required field of the declared payload schema and does NOT construct/insert an incomplete record. | **PASS** — `PROCEDURE ScheduleEvent` (~L567–574): `ScheduleEvent does NOT construct or insert an INCOMPLETE queued_event_record (AD8): a missing required field is a construction-invariant violation, not a silent drop and not a substitution with current global values` … `ASSERT immutable_payload contains EVERY required field of the declared payload schema for event_type   # AD8: reject incomplete construction`. TV259 Expected (a) (~L100–101). |
| **C7 (AD8).** `ProcessEventTime` builds a COMPLETE dispatcher-owned context from the TRUSTED stored record, never untrusted input. | **PASS** — `ProcessEventTime` (~L220–222): `the STORED dispatch_envelope is COMPLETE by construction (ScheduleEvent rejected an incomplete record); the dispatcher builds the COMPLETE OrdinaryDispatchContext from the trusted record — never from untrusted input.` Anchored to the `SET ctx <-` construction on ~L222. |
| **C8 (AD8).** A defensive corruption check, on a detected-corrupt registry entry, calls `HandleDispatchIntegrityFailure` and CONSUMES the event (`DISPATCHING → CONSUMED`, never re-`QUEUED`) rather than dispatching it. | **PASS** — `ProcessEventTime` (~L228–232): `IF record is detected corrupt (immutable_payload incomplete for record.event_type OR dispatch_envelope incomplete): CALL HandleDispatchIntegrityFailure(RoundContext, er, record)` … `SET queued_event_registry[er].queue_status <- CONSUMED  # AD4: DISPATCHING -> CONSUMED (the corrupt event is drained, never re-QUEUED)` then `CONTINUE`. The corrupt branch precedes the `DISPATCH` line (~L236), so a corrupt record never reaches a handler. TV259 Expected (b) (~L102, ~L106–107). |
| **C9 (AD8).** `HandleDispatchIntegrityFailure` records the declared terminal disposition `dispatch_integrity_failure` and builds a COMPLETE integrity envelope from the TRUSTED `EventRef` fields, never the corrupt payload. | **PASS** — `PROCEDURE HandleDispatchIntegrityFailure` (~L316–321): `RECORD dispatch_integrity_failure(er, record.event_type)   # AD8: declared integrity terminal disposition` then `SET integrity_envelope <- { envelope_namespace = er.envelope_namespace, event_time = er.event_time, delta_cycle = er.delta_cycle, event_seq = er.seq, hook_id = null }   # AD8: COMPLETE, dispatcher-owned`, built `from the TRUSTED EventRef fields (never from the corrupt payload)`. TV259 (~L102–103). |
| **C10 (AD8).** Branch behaviour — current nonterminal-round SEATED record terminalises `SEATED → APPLYING → ABORTED` via `RoundAbort(dispatch_envelope = integrity_envelope)`. | **PASS** — see the branch table below; `HandleDispatchIntegrityFailure` (~L328–333). TV259 Expected (b) (~L103–105). |
| **C11 (AD8).** Branch behaviour — an older/terminal-round record is set `SUPERSEDED` WITHOUT aborting the current round; a non-SEATED record is left unchanged. | **PASS** — see the branch table below; `HandleDispatchIntegrityFailure` (~L334–338). TV259 Expected (b) (~L104–105). |
| **C12 (AD8).** A malformed untrusted envelope NEVER becomes the transition identity for round closure. | **PASS** — `HandleDispatchIntegrityFailure` passes `dispatch_envelope = integrity_envelope` (~L331), and `RoundAbort` records `round_terminal_time(RoundID) <- dispatch_envelope.event_time` (`PROCEDURE RoundAbort`, ~L5574–5576) — so the closure identity is the trusted integrity envelope, not the corrupt payload/envelope. NOTE (~L341–343): `its untrusted payload/envelope NEVER becomes the transition identity for round closure; any abort uses the COMPLETE integrity_envelope built from the trusted EventRef`. TV259 (~L106–107). No FAIL: the corrupt payload is never threaded as `dispatch_envelope`. |
| **C13 (AD8).** `HandleDispatchIntegrityFailure` is defined exactly once and called exactly once (from `ProcessEventTime`). | **PASS** — exactly one `PROCEDURE HandleDispatchIntegrityFailure` (~L310) and exactly one `CALL HandleDispatchIntegrityFailure(RoundContext, er, record)` (~L229, inside `ProcessEventTime`); the remaining two textual occurrences (~L1157, ~L2311) are prose comments, not a definition or call site. TV259 lists it under `Procedures` (~L96). |

---

## `HandleDispatchIntegrityFailure` branch behaviour (~L326–338)

The corrupt-record branch fires ONLY when `record.event_type = SetupRetryEvent AND the payload's SetupRetryID resolves to
setup_retry_records[SetupRetryID]` (~L326). Given the resolved record `rec`, the disposition is scoped to `rec`'s OWN round:

| Resolved record `rec` | Condition (~anchor) | Action | Current round aborted? |
|-----------------------|---------------------|--------|------------------------|
| Current nonterminal-round SEATED | `rec.status = SEATED AND rec.RoundID = RoundID_current AND round_state NOT in {ROUND_ACCEPTED, ROUND_ABORTED}` (~L328) | `SetSetupRetryStatus(SetupRetryID, APPLYING)` (leave SEATED first); `RoundAbort(reason = setup_retry_payload_integrity_failure(SetupRetryEvent), dispatch_envelope = integrity_envelope, recovery_finalising = false)`; `SetSetupRetryStatus(SetupRetryID, ABORTED)` — i.e. `SEATED → APPLYING → ABORTED` (~L329–333) | **YES** — via the trusted `integrity_envelope` (never the corrupt payload) |
| Older / terminal-round SEATED | `ELSE IF rec.status = SEATED` (record belongs to an older / terminal round) (~L334–335) | `SetSetupRetryStatus(SetupRetryID, SUPERSEDED)`; `target_disposition <- setup_retry_stale_noop(SetupRetryID)` (~L336–337) | **NO** — terminalised WITHOUT aborting the current round |
| Non-SEATED (already terminal) | falls through (no matching branch) (~L338) | left unchanged — `a non-SEATED record is already terminal — left unchanged (AC7)` | **NO** |

After the procedure returns `dispatch_integrity_handled(er)` (~L339–340), `ProcessEventTime` marks the corrupt event
`CONSUMED` (never re-`QUEUED`) and continues the drain (~L230–232). The `SEATED → APPLYING → ABORTED` path routes every status
write through the sole guard `SetSetupRetryStatus` (`PROCEDURE SetSetupRetryStatus`, ~L2463–2472), whose table permits
`SEATED → APPLYING` and `APPLYING → ABORTED` but no terminal-to-terminal rewrite — so the abort path is legal and the
`SUPERSEDED`/unchanged paths cannot be re-driven.

---

## Result

All thirteen checks PASS with no inconsistency. AD5 holds structurally: `OrdinaryDispatchContext = (dispatch_envelope,
dispatched_event_ref)` is declared dispatcher-owned (~L515–521), `ProcessEventTime` constructs it from the trusted stored
record + `EventRef` (~L217–222), and the single dispatch site delivers `dispatch_envelope` to every ordinary handler while
gating `dispatched_event_ref` behind `IFF record.event_type's signature declares it` (~L236–237) — no undeclared named argument
is injected, and only `SetupRetryEvent` declares and receives the ref (~L2240–2252), matching TV256. AD8 holds end-to-end:
`ScheduleEvent` asserts full-payload completeness and refuses to construct an incomplete record (~L567–574); `ProcessEventTime`
builds a complete context from the trusted record and, on a defensively detected corrupt entry, calls the single
`HandleDispatchIntegrityFailure` and consumes the event `DISPATCHING → CONSUMED` (never re-`QUEUED`, never into a handler)
(~L228–232); and `HandleDispatchIntegrityFailure` (defined once ~L310, called once ~L229) records `dispatch_integrity_failure`,
builds the complete integrity envelope from the trusted `EventRef` (~L316–321), and dispositions the resolved record by its own
round — current nonterminal-round SEATED via `SEATED → APPLYING → ABORTED` with `RoundAbort(dispatch_envelope =
integrity_envelope)`, older/terminal-round SEATED via `SUPERSEDED` without aborting the current round, non-SEATED left
unchanged (~L326–338). Because `RoundAbort` derives `round_terminal_time` from `dispatch_envelope.event_time` (~L5574–5576) and
the caller supplies the trusted `integrity_envelope`, a malformed untrusted envelope never becomes the transition identity for
round closure, matching TV259. The A1 baseline `8.420833333 kWh` and the binding PoCol naming rule (algorithm PoCol; mechanism
the idle policy within PoCol) are preserved throughout.
