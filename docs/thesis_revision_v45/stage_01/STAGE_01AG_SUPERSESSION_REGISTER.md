# Stage 1AG — Supersession Register (AG9)

This register records, per correction AG9, the SPECIFIC inaccurate claims of the (now frozen) Stage-1AF audits that
Stage 1AG supersedes. Stage-1A through Stage-1AF lettered artifacts are UNCHANGED on disk; this register is the
authoritative statement of which prior audit conclusions were reached on an inaccurate reading of the same contract and how
the Stage-1AG normative tree corrects them. The algorithm remains **PoCol**; the mechanism is the idle policy within PoCol;
the A1 baseline (`8.420833333 kWh`) is unchanged. Every Stage-1AG audit inspects the FINAL normative tree only AFTER every
normative edit (AG1–AG8) and every semantic vector (TV288–TV298) was complete.

---

## 1. `STAGE_01AF_DISPATCH_ADAPTER_AUDIT` — assumed same-name payload fields were automatically bound

- **Inaccurate claim.** The AF dispatch-adapter audit certified that `BuildHandlerInvocation` binds the exact declared
  arguments for every wrapper.
- **Why it was wrong.** `BuildHandlerInvocation` iterates ONLY `d.payload_to_param_map`, but the AF binding table left that
  map EMPTY ("(none)") for `RoundInitialiseEvent`/`PrepareParticipantsEvent`/`FullRangeExhaustEvent` and partial for
  `TemplateCommitEvent`/`ReserveActivateEvent` — treating `round_setup_seq`, `RoundID_at_seat`, `TemplateID_at_seat`, and
  `activation_seq` as "staleness/tie-key context" that the adapter would somehow supply. With no map entry, those wrapper
  INPUTS would NOT be bound; the audit assumed an unwritten same-name fallback that does not exist.
- **AG correction.** AG1 gives every wrapper payload field an EXPLICIT `payload_to_param_map` entry and adds
  `d.handler_inputs`; `BuildHandlerInvocation` VERIFIES `keys(args) = d.handler_inputs` and returns
  `handler_invocation_built` / `handler_invocation_binding_failed` (no raw assert); `ProcessEventTime` never calls a handler
  on a binding failure. Verified by `STAGE_01AG_WRAPPER_ARGUMENT_BINDING_AUDIT.md` (TV288, TV298).

## 2. `STAGE_01AF_EVENT_DESCRIPTOR_AUDIT` — checked descriptor rows but not every ScheduleEvent seating payload

- **Inaccurate claim.** The AF event-descriptor audit certified that every descriptor's payload set matches its handler and
  is enforced.
- **Why it was wrong.** It validated the SCHEMA rows in isolation; it did not cross-check that every executable
  `ScheduleEvent(..., event_type, ..., {payload})` seat supplies exactly the descriptor's closed key set. In particular it
  did not catch that `StartWake` seated `WakeCompleteEvent` with `{MinerID, AssignmentID}` — missing `assignment_version` —
  which the descriptor requires.
- **AG correction.** AG2 fixes the `StartWake` seat to `{MinerID, AssignmentID, assignment_version}`; the AG descriptor and
  seating audits cross-check every seat payload against its descriptor (`STAGE_01AG_WAKE_VERSION_PAYLOAD_AUDIT.md`,
  `STAGE_01AG_DRIVER_EVENT_SEATING_AUDIT.md`).

## 3. `STAGE_01AF_SCHEDULER_SCHEMA_ENFORCEMENT_AUDIT` — missed that StartWake omits assignment_version

- **Inaccurate claim.** The AF scheduler-schema audit certified that ScheduleEvent's exact-closed-key-set enforcement is
  consistent with all in-tree seats.
- **Why it was wrong.** It verified the ENFORCEMENT logic but did not enumerate the actual seat call sites; the
  `WakeCompleteEvent` seat in `StartWake` would have been REJECTED (`rejected_payload_schema_mismatch`, missing
  `assignment_version`) under the very rule it certified — a latent contradiction it did not surface.
- **AG correction.** AG2 makes the `StartWake` seat carry `assignment_version`; verified by
  `STAGE_01AG_WAKE_VERSION_PAYLOAD_AUDIT.md` (TV289).

## 4. `STAGE_01AF_RUNCONTEXT_OWNERSHIP_AUDIT` — checked field presence but not the bootstrap circular dependency

- **Inaccurate claim.** The AF RunContext-ownership audit certified that RunContext owns every per-run field and the flow is
  coherent.
- **Why it was wrong.** It checked that fields (including `current_round_context`/`prior_round_terminal_state`) were PRESENT
  in `RunContext`, but not that they were USABLE: (a) `ProcessEventTime` took a `RoundContext` argument, so the first
  `RoundInitialiseEvent` (whose purpose is to CREATE the first RoundContext) had a circular dependency; (b) nothing consumed
  `current_round_context` dynamically per dispatch; (c) NOTHING ever wrote `prior_round_terminal_state`, so it was
  permanently null and the cross-round `SettleResidencyBoundary(REBASE_TO_NEXT_ROUND)` never received a real prior context.
- **AG correction.** AG3/AG5 make `ProcessEventTime`/`RunEventLoopToHorizon` take `RunContext` and resolve
  `current_round_context` per dispatch (the first `RoundInitialiseEvent` needs no RoundContext); AG6 publishes
  `prior_round_terminal_state` at the terminal closure owner. Verified by `STAGE_01AG_RUN_BOOTSTRAP_AUDIT.md` and
  `STAGE_01AG_ROUND_CONTEXT_ROTATION_AUDIT.md` (TV291, TV292, TV294).

## 5. Test vectors and the AF cross-document audit rested on the above gaps

- **TV273** assumed `RoundInitialiseEvent` was already dispatchable — but with `ProcessEventTime` requiring a `RoundContext`
  (item 4) it was not, until AG3.
- **TV276** assumed `assignment_version` existed at the actual `StartWake` seat — but the seat omitted it (items 2/3), until
  AG2.
- **TV286** did not detect the invalid/unused `source_context` (`ORDINARY_DISPATCH(EQ.current_event_ref)` is type-incorrect —
  an EventRef is not a dispatch_envelope) nor that `BlockAcceptancePoint` ignored the seat result — until AG7.
- **The Stage-1AF cross-document audit** therefore incorrectly marked the affected gates PASS. `STAGE_01AG_CROSS_DOCUMENT_AUDIT.md`
  re-evaluates every gate against the final Stage-1AG tree.

---

## 6. Frozen-artifact statement

- Stage-1A … Stage-1AF lettered artifacts (`STAGE_01A*`…`STAGE_01AF_*`) are UNCHANGED on disk; this register is the sole
  record of their superseded conclusions.
- No executable source, configuration, DOCX, or PDF was modified; no experiment was run; the A1 baseline `8.420833333 kWh`
  is unchanged; Stage 2 is not begun.
- The Stage-1AG corrections live only in the five modified `STAGE_01_*` normative documents and the new `STAGE_01AG_*`
  deliverables (`STAGE_01AG_CHECKSUM_MANIFEST.sha256`).
