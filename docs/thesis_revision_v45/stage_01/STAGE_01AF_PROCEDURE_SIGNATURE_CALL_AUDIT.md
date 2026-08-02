# Stage 1AF — Procedure Signature & Call-Site Audit

This audit records, for every procedure TOUCHED or ADDED by Stage 1AF, the exact `INPUTS`, the exact `RETURNS`
disposition set, and — at each call site — that the caller passes arguments matching the signature and inspects or
propagates the returned disposition where it must. All signatures are quoted from the FINAL normative tree
(`STAGE_01_PROTOCOL_PSEUDOCODE.md`; line anchors approximate). The algorithm remains **PoCol**; the mechanism is the
**idle policy within PoCol**; the A1 baseline (`8.420833333 kWh`) is preserved and unchanged. No executable source,
configuration, DOCX, or PDF was modified and no experiment was run for this audit.

Stage 1AF makes the Stage-1AE event-dispatch schema EXECUTABLE and locks the queue-pop / dispatch-binding contract: a
named dispatcher adapter (`BuildHandlerInvocation`, AF2), six driver-event wrappers (AF4), full descriptor-schema
enforcement in `ScheduleEvent` (AF3), an atomic queue-pop in `ProcessEventTime` (AF5), complete per-run ownership in
`RunInitialise` (AF6), an explicit hashing-result contract (AF7), a named acceptance-batch seat owner
(`SeatAcceptanceBatchFinalize`, AF8), and a non-asserting reverse-binding integrity path
(`HandleDispatchIntegrityFailure`, AF9).

## 1. Signature table (AF-touched / added procedures)

| Procedure | AF | INPUTS (declared) | RETURNS (declared result set) |
|-----------|----|-------------------|-------------------------------|
| `BuildHandlerInvocation` (NEW) | AF2 | `event_descriptor d, queued_event_record record, RoundContext, RunContext, OrdinaryDispatchContext ctx` | `handler_invocation(procedure, args)` |
| `ProcessEventTime` | AF5 | `RoundContext, event_time t, is_horizon, allow_empty_horizon = false, RunHookContext = null` | `event_time_finalised(t)` |
| `HandleDispatchIntegrityFailure` | AF9 | `RoundContext, er, record` | `dispatch_integrity_handled(er)` \| `dispatch_integrity_owner_binding_corrupt(er)` |
| `ScheduleEvent` | AF3 | `EventQueueContext EQ, RoundContext, event_type, target_event_time, target_microphase, envelope_fields, post_epilogue_context = null` | `scheduled(event_ref, record)` \| `rejected_finalised_time` \| `post_horizon_event_rejected` \| `rejected_post_epilogue_not_strictly_later` \| `rejected_backward_time` \| `rejected_event_type_unknown(event_type)` \| `rejected_microphase_mismatch(event_type, target_microphase, expected_microphase)` \| `rejected_payload_schema_mismatch(event_type, missing_fields, extra_fields, type_invalid_fields)` \| `rejected_stable_tie_key_unavailable(event_type)` |
| `RoundInitialiseEvent` (NEW) | AF4 | `RunContext, round_setup_seq` | `round_initialised(RoundID)` |
| `TemplateCommitEvent` (NEW) | AF4 | `RoundContext, RoundID_at_seat, candidate_template` | `template_committed(RoundID, TemplateID)` \| `template_commit_stale_noop(RoundID_at_seat)` |
| `MinerRegisterEvent` (NEW) | AF4 | `RoundContext, join_request, dispatch_envelope` | `miner_registered(MinerID)` |
| `PrepareParticipantsEvent` (NEW) | AF4 | `RoundContext, RoundID_at_seat, TemplateID_at_seat, dispatch_envelope` | `participant_set_prepared` \| `participant_set_setup_retry_seated(SetupRetryID, reason)` \| `round_aborted(abort_record)` \| `participant_setup_stale_noop(RoundID_at_seat, TemplateID_at_seat)` (corrected) |
| `ReserveActivateEvent` (NEW) | AF4 | `RoundContext, RoundID_at_seat, deficit, activation_seq, dispatch_envelope` | `reserve_activation_committed(MinerID, AssignmentID, assignment_version, WakeEventRef)` \| `reserve_activation_failed_before_mutation(reason)` \| `reserve_activation_failed_after_assignment(reason, AssignmentID, rollback_record)` \| `reserve_activation_stale_noop(RoundID_at_seat)` |
| `FullRangeExhaustEvent` (NEW) | AF4 | `RoundContext, RoundID_at_seat, TemplateID_at_seat, dispatch_envelope` | `(FullRangeExhaustNoSolution disposition: new_TemplateID \| template_refresh_retry_seated(SetupRetryID, reason) \| template_refresh_retry_stale_noop(TemplateRefreshSetupID) \| round_aborted(abort_record))` \| `range_exhaust_stale_noop(RoundID_at_seat, TemplateID_at_seat)` |
| `RunInitialise` | AF6 | `config` | `RunContext(RunID, EventQueueContext, RunHookContext, rebased_boundaries, run_finalised, run_horizon_T, security_census_dirty, latest_security_census, security_census_write_seq_by_event_time, applied_transition_registry, transition_rejection_log, setup_retry_records, queued_event_registry, setup_retry_by_seat_event_ref, waking_origin_assignment_ref, maximum_setup_retries, config, prior_round_terminal_state, current_round_context)` |
| `StartHashing` | AF7 | `RoundContext, MinerID, assignment` | `hashing_started(event_ref)` \| `hashing_not_started(reason)` |
| `ScheduleNextHashWork` | AF7 | `RoundContext, MinerID, assignment, from_cursor` | `hash_work_seated(EventRef)` \| `hash_work_not_seated(reason)` |
| `HashWorkEvent` | AF7 | `RoundContext, MinerID, AssignmentID, assignment_version, RoundID, TemplateID, cursor, dispatch_envelope` | `hash_work_result (solution \| exhausted \| continued(hash_work_seated(EventRef) \| hash_work_not_seated(reason)) \| noop)` |
| `SeatAcceptanceBatchFinalize` (NEW) | AF8 | `RoundContext, acceptance_timestamp, acceptance_point, source_context` | `acceptance_batch_finalize_seated(EventRef)` \| `acceptance_batch_finalize_already_seated(EventRef)` \| `acceptance_batch_finalize_seat_terminal(EventRef, status)` \| `acceptance_batch_finalize_seat_failed(reason)` |

**Signature / contract facts introduced by Stage 1AF (verified against the body):**

- `BuildHandlerInvocation` (AF2) takes exactly the five declared inputs and returns `handler_invocation(procedure, args)`
  on its single `RETURN` (line ~223); it is the sole binder of ordinary-dispatch handler arguments.
- `ScheduleEvent` (AF3) RETURNS gains `rejected_event_type_unknown`, `rejected_microphase_mismatch`,
  `rejected_payload_schema_mismatch(event_type, missing_fields, extra_fields, type_invalid_fields)` (four args), and
  `rejected_stable_tie_key_unavailable`; each is returned BEFORE any state mutation (lines ~663–689). The removed AE7
  `rejected_payload_schema_mismatch(event_type, missing_or_invalid_fields)` two-argument form appears ONLY inside the
  procedure NOTE that documents the replacement (line ~719); it is never returned by the body and never bound by a caller.
- `ProcessEventTime` (AF5) binds `RunContext <- RoundContext.RunContext` (line ~249), then `CALL BuildHandlerInvocation(...)`
  (line ~288) and `CALL inv.procedure WITH inv.args` (line ~289); the atomic POP moves `QUEUED -> DISPATCHING` and the tail
  moves `DISPATCHING -> CONSUMED`.
- `RunInitialise` (AF6) both INITIALISEs and RETURNS every per-run field, including `config`,
  `prior_round_terminal_state`, `current_round_context`, `queued_event_registry`, and `setup_retry_by_seat_event_ref`
  (lines ~2201–2207); no per-run registry is an implicit global.
- `StartHashing` (AF7) RETURNs `hashing_started(event_ref)` and `hashing_not_started(reason)` explicitly on both paths
  (lines ~3102–3105) — no successful fall-through. `HashWorkEvent` wraps its continuation as
  `continued(CALL ScheduleNextHashWork(...))` (line ~3181), matching the `continued(...)` shape of its declared RETURNS.
- `SeatAcceptanceBatchFinalize` (AF8) returns the four `*_seat*` variants and stores the seated `EventRef` in the
  per-round `acceptance_batch_finalize_seat` map (idempotent, replay-safe).
- `HandleDispatchIntegrityFailure` (AF9) returns `dispatch_integrity_owner_binding_corrupt(er)` on a corrupt reverse
  binding (line ~391) and `dispatch_integrity_handled(er)` otherwise (line ~414) — it never raw-asserts.

## 2. Call-site agreement matrix

| Procedure | Caller(s) (site) | Args match signature | Disposition handling |
|-----------|------------------|:--------------------:|----------------------|
| `BuildHandlerInvocation` | `ProcessEventTime` (line ~288, 1 literal site) | ✓ `(descriptor(record.event_type), record, RoundContext, RunContext, ctx)` | ✓ result bound to `inv`; `CALL inv.procedure WITH inv.args` dispatches the handler |
| `ProcessEventTime` | `RunEventLoopToHorizon` (run driver) | ✓ `(RoundContext, event_time, is_horizon, allow_empty_horizon, RunHookContext)` | ✓ drives the event loop; `event_time_finalised(t)` closes the time |
| `HandleDispatchIntegrityFailure` | `ProcessEventTime` (line ~280, 1 literal site) | ✓ `(RoundContext, er, record)` | ✓ for-effect (declared audit disposition); both variants lead ProcessEventTime to CONSUME the corrupt event |
| `ScheduleEvent` | all seat sites (14 literal sites: retry seats, hash-work, recovery-due seats, propagation/certificate/block seats, acceptance-batch seat) | ✓ `(EQ, RoundContext, event_type, target_event_time, target_microphase, envelope_fields[, post_epilogue_context])` | ✓ success bound as `scheduled(event_ref, record)`; rejections handled generically or re-wrapped opaquely (`hash_work_not_seated(r)`, `acceptance_batch_finalize_seat_failed(r)`); no caller binds the removed two-arg schema-mismatch form |
| `RoundInitialiseEvent` | `ProcessEventTime` via `CALL inv.procedure` (dynamic; 0 literal sites) | ✓ adapter supplies `RunContext` (recv env=no, recv ref=no); wrapper `CALL RoundInitialise(config, RunContext, prior_state)` — exact | ✓ returns `round_initialised(rc.RoundID)` |
| `TemplateCommitEvent` | `ProcessEventTime` via `CALL inv.procedure` (dynamic) | ✓ adapter supplies `RoundContext` + `candidate_template`; wrapper `CALL TemplateCommit(RoundContext, candidate_template)` — exact | ✓ wraps `TemplateID` as `template_committed(...)`; own `template_commit_stale_noop` on stale seat |
| `MinerRegisterEvent` | `ProcessEventTime` via `CALL inv.procedure` (dynamic) | ✓ adapter supplies `RoundContext` + `dispatch_envelope` + `join_request`; wrapper `CALL MinerRegister(RoundContext, join_request, dispatch_envelope)` — exact | ✓ wraps `MinerID` as `miner_registered(MinerID)` |
| `PrepareParticipantsEvent` | `ProcessEventTime` via `CALL inv.procedure` (dynamic) | ✓ adapter supplies `RoundContext` + `dispatch_envelope`; wrapper `CALL PrepareParticipantsForNewRound(RoundContext, dispatch_envelope)` — exact | ✓ propagates domain result / own `participant_setup_stale_noop`. See §4 note on the declared RETURNS enumeration |
| `ReserveActivateEvent` | `ProcessEventTime` via `CALL inv.procedure` (dynamic) | ✓ adapter supplies `RoundContext` + `dispatch_envelope` + `deficit`; wrapper `CALL ReserveActivate(RoundContext, deficit, scheduling_context = ORDINARY_DISPATCH(dispatch_envelope))` — exact (WRAPPER, never a bare envelope) | ✓ propagates the three domain variants + own `reserve_activation_stale_noop` |
| `FullRangeExhaustEvent` | `ProcessEventTime` via `CALL inv.procedure` (dynamic) | ✓ adapter supplies `RoundContext` + `dispatch_envelope`; wrapper `CALL FullRangeExhaustNoSolution(RoundContext, dispatch_envelope)` — exact | ✓ propagates the full domain disposition + own `range_exhaust_stale_noop` |
| `RunInitialise` | run driver (once per run) | ✓ `(config)` | ✓ every returned field is read by name via the bound `RunContext` (AF6 access convention) |
| `StartHashing` | `WakeCompleteEvent` (line ~2016, 1 literal site) | ✓ `(RoundContext, MinerID, target_assignment)` | ✓ `RETURN CALL StartHashing(...)` — `WakeCompleteEvent`'s RETURNS now carries `hashing_started(event_ref) \| hashing_not_started(reason)` (reconciled) |
| `ScheduleNextHashWork` | `StartHashing` (line ~3100); `HashWorkEvent` continuation (line ~3181) — 2 literal sites | ✓ `(RoundContext, MinerID, assignment, from_cursor)` | ✓ `StartHashing` maps `hash_work_seated/not_seated` -> `hashing_started/not_started`; `HashWorkEvent` wraps it in `continued(...)` |
| `HashWorkEvent` | `ProcessEventTime` via `CALL inv.procedure` (dynamic) | ✓ adapter binds payload keys + `dispatch_envelope`; `assignment = version(AssignmentID, assignment_version)` resolved in-body | ✓ returns `solution` / `exhausted` / `continued(...)` / `noop` per path |
| `SeatAcceptanceBatchFinalize` | `BlockAcceptancePoint` (line ~5478, 1 literal site) | ✓ `(RoundContext, acceptance_timestamp = now, acceptance_point, source_context = ORDINARY_DISPATCH(EQ.current_event_ref))` | ✓ for-effect: idempotence is enforced by the stored seat map; the seat EventRef remains cancellable via `CancelQueuedEvent` |

**Dynamic dispatch.** The six AF4 wrappers and every direct queued handler have zero LITERAL `CALL <Name>` sites; they
are reached through the ONE `CALL inv.procedure WITH inv.args` site in `ProcessEventTime`, where
`inv = BuildHandlerInvocation(descriptor(record.event_type), record, RoundContext, RunContext, ctx)`. Each is reachable
because its `event_type` has a descriptor whose `handler_procedure` names it (§0.7g-schema, lines ~942–963), and each
wrapper makes a literal `CALL` to its domain procedure (so those domain procedures also remain reachable). The adapter's
defensive assertions confirm `dispatch_envelope`/`dispatched_event_ref` are injected IFF `recv_env`/`recv_ref` (lines
~221–222): `BlockAcceptancePoint` receives neither; `SetupRetryEvent` receives both; all others receive the envelope only.

## 3. Call-graph closure result

Method: extract `^(PROCEDURE|FUNCTION)\s+<Name>` as definitions and `\bCALL\s+<Uppercase-Name>` as literal references
from `STAGE_01_PROTOCOL_PSEUDOCODE.md`; the set difference (references − definitions) is the dangling set.

- **Defined callables (`PROCEDURE`/`FUNCTION`, all names distinct):** 97
- **Distinct literal `CALL <Uppercase>` targets:** 75
- **Dynamic-dispatch sites (`CALL inv.procedure`):** 1 (the AF2/AF4 executable-dispatch pattern in `ProcessEventTime`)
- **Dangling references (called but not defined):** 0

Stage-1AF adds 8 callables over the Stage-1AE baseline of 89: `BuildHandlerInvocation` (AF2), the six AF4 wrappers
(`RoundInitialiseEvent`, `TemplateCommitEvent`, `MinerRegisterEvent`, `PrepareParticipantsEvent`,
`ReserveActivateEvent`, `FullRangeExhaustEvent`), and `SeatAcceptanceBatchFinalize` (AF8) → 97. This matches
`STAGE_01AF_PROCEDURE_CALL_GRAPH.md` (97 defined callables, 75 distinct literal `CALL` targets, 0 dangling).

Per-procedure literal call-site counts confirmed: `BuildHandlerInvocation` 1, `SeatAcceptanceBatchFinalize` 1,
`HandleDispatchIntegrityFailure` 1, `StartHashing` 1, `ScheduleNextHashWork` 2, `ScheduleEvent` 14; each AF4 wrapper 0
(dynamic dispatch only).

## 4. Observation — `PrepareParticipantsEvent` declared RETURNS enumeration (CORRECTED)

> **Correction applied.** The enumeration gap described below was corrected in the final normative tree: the
> `PrepareParticipantsEvent` RETURNS union at line ~1063 now lists `participant_set_setup_retry_seated(SetupRetryID,
> reason)` alongside `participant_set_prepared`, `round_aborted(abort_record)`, and the wrapper's own
> `participant_setup_stale_noop(...)`. The wrapper therefore declares every disposition it can propagate, at parity with
> its sibling wrappers. The analysis below is retained as the record of the gap that was found and fixed.

`PrepareParticipantsEvent` (line ~1062) executes `RETURN CALL PrepareParticipantsForNewRound(RoundContext,
dispatch_envelope = dispatch_envelope)` with the comment "propagate the domain disposition". Its domain procedure
`PrepareParticipantsForNewRound` declares (line ~2522):

`participant_set_prepared | participant_set_setup_retry_seated(SetupRetryID, reason) | round_aborted(abort_record)`

and the `participant_set_setup_retry_seated(...)` path is reachable during a dispatched `ASSIGNMENT_SETUP` event (a
clean rollback with retry budget remaining seats a `SetupRetryEvent`, line ~2519). The wrapper therefore CAN return
`participant_set_setup_retry_seated(...)`, but its declared RETURNS union (line ~1063) lists only
`participant_set_prepared | round_aborted(abort_record) | participant_setup_stale_noop(...)` — it omits the propagated
`participant_set_setup_retry_seated(...)` variant. The two sibling propagating wrappers each enumerate their full
propagated domain set: `ReserveActivateEvent` lists all three `ReserveActivate` variants plus its stale-noop (lines
~1076–1079) and `FullRangeExhaustEvent` lists the full `FullRangeExhaustNoSolution` disposition plus its stale-noop
(lines ~1089–1091).

Scope of impact: BEHAVIORAL agreement holds — the wrapper faithfully propagates the domain result, and its sole
caller (`ProcessEventTime` via `CALL inv.procedure`) consumes the handler disposition for-effect at the event-loop
boundary and pattern-matches on none of these variants, so no call site is broken. The gap is confined to the
completeness of the wrapper's DECLARED RETURNS enumeration. For contract exactness (audit criterion (b)) and parity
with the sibling wrappers, `PrepareParticipantsEvent`'s RETURNS should also list
`participant_set_setup_retry_seated(SetupRetryID, reason)`.

## 5. Cross-checks performed

1. **Adapter binding (AF2).** `BuildHandlerInvocation` INPUTS `(event_descriptor, record, RoundContext, RunContext,
   ctx)` match its single `ProcessEventTime` call site; it returns `handler_invocation(procedure, args)` and is the SOLE
   ordinary-dispatch argument binder.
2. **Wrapper → domain args (AF4).** Every one of the six wrappers CALLs its domain procedure with EXACTLY the domain
   signature's named arguments (`RoundInitialise`, `TemplateCommit`, `MinerRegister`, `PrepareParticipantsForNewRound`,
   `ReserveActivate` via the `ORDINARY_DISPATCH(...)` wrapper, `FullRangeExhaustNoSolution`).
3. **Scheduler schema RETURNS (AF3).** The four new rejection variants are present and returned before any mutation; the
   `rejected_payload_schema_mismatch` form carries four arguments; the removed two-arg form is documented-only and bound
   by no caller.
4. **Queue-pop + RunContext (AF5).** `ProcessEventTime` binds `RunContext` from `RoundContext.RunContext`, then invokes
   the adapter and `CALL inv.procedure`; the atomic POP/consume lifecycle owns `queue_status`.
5. **Per-run ownership (AF6).** `RunInitialise` returns all per-run fields, including `config`,
   `prior_round_terminal_state`, `current_round_context`, `queued_event_registry`, `setup_retry_by_seat_event_ref`.
6. **Hashing contract (AF7).** `StartHashing` RETURNs both variants explicitly; `HashWorkEvent`'s continuation is
   `continued(...)`; the `WakeCompleteEvent` caller RETURNS is reconciled to carry the `StartHashing` disposition.
7. **Acceptance-batch seat (AF8).** `SeatAcceptanceBatchFinalize` INPUTS and its four `*_seat*` RETURNS variants match
   its `BlockAcceptancePoint` call site.
8. **Integrity path (AF9).** `HandleDispatchIntegrityFailure` returns both declared variants and never raw-asserts on a
   corrupt reverse binding.
9. **Call-graph closure.** 0 dangling references; 97 defined callables (§3).

## 6. Overall verdict

For every procedure TOUCHED or ADDED by Stage 1AF, the declared INPUTS, the declared RETURNS disposition set, and all
call sites AGREE, and the call graph closes with **0 dangling references** and **97 defined callables**. Argument
binding is exact at every literal and dynamic-dispatch site; `ScheduleEvent`'s new schema-enforcement rejection set is
caller-compatible and the removed two-argument schema-mismatch form is bound by no caller; the hashing and
acceptance-batch result contracts are shape-consistent with their callers; and the integrity path is non-asserting. The
one documentation-completeness item this audit found — `PrepareParticipantsEvent`'s declared RETURNS union omitting the
propagated `participant_set_setup_retry_seated(SetupRetryID, reason)` variant — was CORRECTED in the final normative tree
(§4): the union now enumerates that variant, matching the wrapper body and its two sibling propagating wrappers. With
that correction applied, every Stage-1AF signature/RETURNS/call-site agreement holds. The algorithm remains **PoCol**,
the mechanism is the **idle policy within PoCol**, and the A1 baseline (`8.420833333 kWh`) is preserved.
