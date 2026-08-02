# Stage 1AG — Procedure Signature & Call-Site Audit

This audit records, for every procedure TOUCHED or ADDED by Stage 1AG, the exact `INPUTS`, the exact `RETURNS`
disposition set, and — at every call site — that the caller passes arguments matching the signature and inspects or
propagates the returned disposition explicitly. All signatures are quoted from the current
`STAGE_01_PROTOCOL_PSEUDOCODE.md` (line anchors approximate). The algorithm remains **PoCol**; the mechanism audited here
is the **idle policy within PoCol** (the driver-event / dispatch machinery that runs a round to quiescence). No executable
source, configuration, or experiment was touched; the **A1 baseline `8.420833333 kWh` is preserved and unchanged**.

Verification targets: (a) INPUTS match every call site; (b) RETURNS match the procedure body; (c) callers
inspect/propagate the disposition. A grep-based call-graph closure (`^(PROCEDURE|FUNCTION)` definitions vs `CALL
<Uppercase>` references) closes the audit.

## 1. Signature table (AG-touched / AG-added procedures)

| Procedure | Change | INPUTS | RETURNS (declared result set) |
|-----------|--------|--------|-------------------------------|
| `BuildHandlerInvocation` | AG1 (RETURNS) | `event_descriptor d, queued_event_record record, RoundContext, RunContext, OrdinaryDispatchContext ctx` | `handler_invocation_built(procedure, args)` \| `handler_invocation_binding_failed(event_type, missing_args, extra_args)` |
| `ProcessEventTime` | AG3/AG5 (INPUTS) | `RunContext, event_time t, is_horizon = (t == run_horizon_T), allow_empty_horizon = false, RunHookContext = null` | `event_time_finalised(t)` |
| `RunEventLoopToHorizon` | AG3 (INPUTS) | `RunContext` | `run_completed(T)` |
| `StartWake` | AG2 (RETURNS) | `RoundContext, MinerID, target_assignment, from_state, scheduling_context` | `wake_seated(AssignmentID, assignment_version, WakeEventRef, wake_target_time, resulting_state = WAKING)` \| `wake_schedule_failed_before_transition(reason)` \| `wake_transition_failed_after_seat(reason, WakeEventRef)` |
| `SeatNextRoundBootstrap` | AG4 (NEW) | `RunContext` | `round_bootstrap_seated(EventRef, round_setup_seq)` \| `round_bootstrap_already_seated(round_setup_seq)` \| `round_bootstrap_seat_failed(reason)` |
| `SeatTemplateCommit` | AG4 (NEW) | `RunContext, RoundID_at_seat, candidate_template` | `template_commit_seated(EventRef)` \| `template_commit_already_seated(key)` \| `template_commit_seat_failed(reason)` |
| `SeatPrepareParticipants` | AG4 (NEW) | `RunContext, RoundID_at_seat, TemplateID_at_seat` | `prepare_participants_seated(EventRef)` \| `prepare_participants_already_seated(key)` \| `prepare_participants_seat_failed(reason)` |
| `SeatMinerRegister` | AG4 (NEW) | `RunContext, join_request` | `miner_register_seated(EventRef)` \| `miner_register_already_seated(key)` \| `miner_register_seat_failed(reason)` |
| `SeatReserveActivate` | AG4 (NEW) | `RunContext, RoundID_at_seat, deficit` | `reserve_activate_seated(EventRef)` \| `reserve_activate_already_seated(key)` \| `reserve_activate_seat_failed(reason)` |
| `SeatFullRangeExhaust` | AG4 (NEW) | `RunContext, RoundID_at_seat, TemplateID_at_seat` | `full_range_exhaust_seated(EventRef)` \| `full_range_exhaust_already_seated(key)` \| `full_range_exhaust_seat_failed(reason)` |
| `SeatPendingDriverRequests` | AG4 (NEW) | `RunContext` | `driver_intake_seated` \| `driver_intake_no_round` |
| `CloseRoundAssignments` | AG6 (EFFECTS) | `RoundContext, disposition, stop_reason, dispatch_envelope, recovery_finalising = false` | `closure_record` |
| `SeatAcceptanceBatchFinalize` | AG7 (INPUTS drop `source_context`) | `RoundContext, acceptance_timestamp, acceptance_point` | `acceptance_batch_finalize_seated(EventRef, generation)` \| `acceptance_batch_finalize_already_seated(EventRef, generation)` \| `acceptance_batch_finalize_seat_failed(reason)` |
| `AcceptanceBatchFinalize` | AG7 (INPUTS gain `batch_generation`) | `RoundContext, acceptance_timestamp, acceptance_point, batch_generation, dispatch_envelope` | `accepted_block` \| `no_valid_candidate` |
| `BlockAcceptancePoint` | AG7 (consumer of the seat result) | `RoundContext, certificate, snapshot, CandidateID, PropagationID, outcome` | `registered` \| `ignored_stale_candidate` \| `acceptance_registration_failed(CandidateID, reason)` |
| `RunInitialise` | AG4 (RETURNS gain 5 fields) | `config (horizon T, ...)` | `RunContext(… , driver_event_seat, next_round_setup_seq, round_bootstrap_time, pending_join_requests, pending_ordinary_reserve_deficits)` |
| `RoundInitialise` | AG4 (RETURNS gain 1 field) | `config, RunContext, prior_state` | `RoundContext(… , reserve_activation_seq, …)` |
| `FinalizeSimulationRun` | AG3 (INPUTS) | `RunContext, RoundContext` | `run_finalised(T)` \| `run_already_finalised` |

**Signature/contract changes introduced by Stage 1AG:**
- **AG1.** `BuildHandlerInvocation` now VERIFIES the produced arg set against `d.handler_inputs` and returns the structured
  `handler_invocation_built(procedure, args)` / `handler_invocation_binding_failed(event_type, missing_args, extra_args)`
  (never a raw assert). INPUTS gain `RunContext` alongside `RoundContext` (the RoundInitialiseEvent wrapper is
  RunContext-injected).
- **AG2.** `StartWake`'s `wake_seated` gains `assignment_version` (now a 5-field constructor); the seated version is the exact
  immutable wake-origin version `WakeCompleteEvent` re-verifies.
- **AG3/AG5.** `ProcessEventTime` and `RunEventLoopToHorizon` take `RunContext` (not a retained `RoundContext`); the current
  `RoundContext` is re-resolved from `RunContext.current_round_context` per dispatch. `FinalizeSimulationRun` takes
  `(RunContext, RoundContext)`.
- **AG4.** Seven NEW named seating owners (`SeatNextRoundBootstrap`, `SeatTemplateCommit`, `SeatPrepareParticipants`,
  `SeatMinerRegister`, `SeatReserveActivate`, `SeatFullRangeExhaust`, `SeatPendingDriverRequests`); `RunInitialise` returns
  `driver_event_seat, next_round_setup_seq, round_bootstrap_time, pending_join_requests, pending_ordinary_reserve_deficits`;
  `RoundInitialise` returns `reserve_activation_seq`.
- **AG6.** `CloseRoundAssignments` publishes `prior_round_terminal_state <- current_round_context` and conditionally calls
  `SeatNextRoundBootstrap`. Signature unchanged (Stage-1AA form preserved).
- **AG7.** `SeatAcceptanceBatchFinalize` INPUTS drop the type-incorrect `source_context`; `AcceptanceBatchFinalize` INPUTS
  gain `batch_generation`; both RETURNS carry the `generation`.

## 2. Call-site agreement matrix

### `BuildHandlerInvocation` (AG1) — INPUTS ↔ call site ↔ RETURNS

| Caller | Args match | Result handling |
|--------|-----------|-----------------|
| `ProcessEventTime` | ✓ `BuildHandlerInvocation(d, record, dispatch_round_context, RunContext, ctx)` — 5 args match INPUTS | ✓ `SET inv <- CALL …`; `IF inv = handler_invocation_binding_failed(event_type, missing_args, extra_args)` → `RECORD dispatch_binding_failed(…)`, CONSUME, re-POP (handler NEVER called); else `inv = handler_invocation_built(procedure, args)` → `CALL inv.procedure WITH inv.args`. BOTH dispositions consumed. |

### `ProcessEventTime` (AG3/AG5) — RunContext threading + dynamic round resolution

| Caller / aspect | Check |
|-----------------|-------|
| `RunEventLoopToHorizon` sub-horizon | ✓ `ProcessEventTime(RunContext, t, is_horizon = false)` — passes the RUN context |
| `RunEventLoopToHorizon` horizon sentinel | ✓ `ProcessEventTime(RunContext, T, is_horizon = true, allow_empty_horizon = true, RunHookContext = RunContext.RunHookContext)` |
| Round resolution | ✓ `SET dispatch_round_context <- RunContext.current_round_context` per dispatch; epilogue tail `SET RoundContext <- RunContext.current_round_context` (no retained/stale RoundContext) |
| `dispatch_context_unavailable` path | ✓ `IF (RoundContext in d.runtime_injected) AND dispatch_round_context = null` → `RECORD dispatch_context_unavailable(record.event_type, er)`, CONSUME, CONTINUE (handler never called; RoundInitialiseEvent, injected `RunContext`, is never blocked) |

### `RunEventLoopToHorizon` (AG3) — INPUTS `RunContext` only; the AG4 driver chain

| Callee | Args match | Result handling |
|--------|-----------|-----------------|
| `SeatNextRoundBootstrap(RunContext)` (run start) | ✓ 1 arg | ✓ called for effect (idempotent per `round_setup_seq`); seats the first `RoundInitialiseEvent` before the loop |
| `SeatPendingDriverRequests(RunContext)` (per selected t) | ✓ 1 arg | ✓ called for effect (idempotent intake) |
| `ProcessEventTime(RunContext, …)` (both sites) | ✓ RunContext at both call sites | ✓ drives the loop |
| `FinalizeSimulationRun(RunContext, RoundContext)` | ✓ `SET RoundContext <- RunContext.current_round_context` THEN `FinalizeSimulationRun(RunContext, RoundContext)` — resolved (terminal) round, never a retained arg | ✓ run-level hook; asserts round terminal |

### `StartWake` (AG2) — every `wake_seated` caller at the 5-field arity

| Caller | `wake_seated` binding | Arity OK |
|--------|-----------------------|----------|
| `PrepareParticipantsForNewRound` (participant setup txn) | `wake_seated(waid, wav, wref, wtt, ws)` | ✓ 5-field (`wav` = assignment_version, slot 2) |
| `RangeAssignFromPlan` | `wake_seated(waid, wav, wref, wtt, ws)` | ✓ 5-field |
| `ResumeFromPause` | `wake_seated(waid, wav, wref, wtt, ws)` | ✓ 5-field |
| `ContinueTemplateRefreshAssignmentSetup` (refresh setup txn) | `wake_seated(waid, wav, wref, wtt, ws)` | ✓ 5-field |
| `ReserveActivateFromPlan` | `wake_seated(...)` then reads `wr.WakeEventRef` | ✓ constructor-tag match + field read (arity-safe) |
| `RangeReassignFromPlan` | `wake_seated(...)` then reads `wr.WakeEventRef` | ✓ constructor-tag match + field read (arity-safe) |

No caller binds the old 4-field form; the two `wake_seated(...)` sites match on the constructor tag and read
`WakeEventRef` by field name, so both are correct under the 5-field arity.

### The six Seat* owners + `SeatPendingDriverRequests` (AG4) — INPUTS, structured RETURNS, idempotence, reachability

| Owner | Call site(s) (args match) | Idempotence identity | Reachable |
|-------|---------------------------|----------------------|-----------|
| `SeatNextRoundBootstrap` | `RunEventLoopToHorizon` (`RunContext`) + `CloseRoundAssignments` (`RunContext`) | `(ROUND_INITIALISE, round_setup_seq)` → `driver_event_seat` | ✓ 2 |
| `SeatTemplateCommit` | `RoundInitialiseEvent` (`RunContext, RoundID_at_seat = rc.RoundID, candidate_template = …`) | `(TEMPLATE_COMMIT, RoundID_at_seat, candidate_template_id)` | ✓ 1 |
| `SeatPrepareParticipants` | `TemplateCommitEvent` (`RoundContext.RunContext, RoundID_at_seat, TemplateID_at_seat`) | `(PREPARE_PARTICIPANTS, RoundID_at_seat, TemplateID_at_seat)` | ✓ 1 |
| `SeatMinerRegister` | `SeatPendingDriverRequests` (`RunContext, join_request = jr`) | `(MINER_REGISTER, join_request_id)` | ✓ 1 |
| `SeatReserveActivate` | `SeatPendingDriverRequests` (`RunContext, RoundID_at_seat, deficit`) | `(RESERVE_ACTIVATE, RoundID_at_seat, activation_seq)` | ✓ 1 |
| `SeatFullRangeExhaust` | `ExhaustionAdjudicate` (`RoundContext.RunContext, RoundID_at_seat, TemplateID_at_seat`) | `(RANGE_EXHAUST, RoundID_at_seat, TemplateID_at_seat)` | ✓ 1 |
| `SeatPendingDriverRequests` | `RunEventLoopToHorizon` (`RunContext`) | routes to idempotent owners; `driver_intake_no_round` when no round | ✓ 1 |

Each owner's args match its INPUTS exactly; each inspects `ScheduleEvent`'s structured result (`r = scheduled(event_ref,
record)` → store `driver_event_seat[key]` and return `*_seated`, else `*_seat_failed(r)`); each guards replay via
`driver_event_seat[key] EXISTS AND queued_event_registry[…].queue_status in {QUEUED, DISPATCHING, CONSUMED}` →
`*_already_seated`. Every driver wrapper therefore has ≥1 reachable named seating path.

### `CloseRoundAssignments` (AG6)

| Aspect | Check |
|--------|-------|
| Publishes prior terminal round | ✓ `SET RunContext <- RoundContext.RunContext`; `SET RunContext.prior_round_terminal_state <- RunContext.current_round_context` (RoundID, `round_terminal_time`, residency_ledger, terminal disposition) |
| Conditional next-round bootstrap | ✓ `IF dispatch_envelope.envelope_namespace != RUN_HOOK AND next_representable_simulation_time(round_terminal_time(RoundID)) <= run_horizon_T:` → `CALL SeatNextRoundBootstrap(RunContext)`; a `RUN_HOOK` (horizon) close seats no next round |
| Downstream consumer | ✓ next `RoundInitialise` reads `prior_state = RunContext.prior_round_terminal_state` and threads it to `SettleResidencyBoundary(REBASE_TO_NEXT_ROUND)` |

### `SeatAcceptanceBatchFinalize` (AG7) + `AcceptanceBatchFinalize` (AG7)

| Caller / aspect | Args match | Result handling |
|-----------------|-----------|-----------------|
| `BlockAcceptancePoint` → `SeatAcceptanceBatchFinalize` | ✓ `(RoundContext, acceptance_timestamp = now, acceptance_point = RoundContext.acceptance_point)` — no `source_context` | ✓ `SWITCH seat`: `…_seated(event_ref, generation)` / `…_already_seated(event_ref, generation)` → `SET gen`; `…_seat_failed(reason)` → fail THIS candidate scoped (`acceptance_registration_failed`), no stranded batch. All three dispositions consumed. |
| `SeatAcceptanceBatchFinalize` → `ScheduleEvent` | ✓ closed payload `{acceptance_timestamp, acceptance_point, batch_generation = generation}` | ✓ inspects `scheduled(event_ref, record)`; stores `{generation, EventRef}` in `acceptance_batch_finalize_seat`; idempotent while QUEUED, opens next generation after DISPATCHING/CONSUMED/CANCELLED |
| `AcceptanceBatchFinalize` (dispatched handler) | ✓ payload carries `batch_generation`; INPUTS `(…, batch_generation, dispatch_envelope)` | ✓ reads/clears ONLY `acceptance_batch_registry[(ts, point, batch_generation)]` (generation-keyed); registered arrival routed to `gen` in `BlockAcceptancePoint` |

### `RunInitialise` (AG4) / `RoundInitialise` (AG4)

| Procedure | New RETURNS fields | INITIALISE ↔ RETURNS agreement |
|-----------|--------------------|--------------------------------|
| `RunInitialise` | `driver_event_seat`, `next_round_setup_seq`, `round_bootstrap_time`, `pending_join_requests`, `pending_ordinary_reserve_deficits` | ✓ each is `INITIALISE`/`SET` in EFFECTS and present in the returned `RunContext(...)`; consumed by the Seat* owners |
| `RoundInitialise` | `reserve_activation_seq` | ✓ `SET reserve_activation_seq <- 0` in EFFECTS and present in the returned `RoundContext(...)`; consumed by `SeatReserveActivate` |

## 3. Cross-checks performed

1. **Dispatch adapter dual disposition.** `BuildHandlerInvocation` returns exactly the two AG1 constructors; `ProcessEventTime`
   inspects both — a binding failure records `dispatch_binding_failed` and CONSUMES without calling the handler; a built
   invocation dispatches `inv.procedure WITH inv.args`.
2. **No retained RoundContext.** `ProcessEventTime`/`RunEventLoopToHorizon` INPUTS carry only `RunContext`; every
   `RoundContext` is re-resolved from `RunContext.current_round_context`; the required-but-null case is the structured
   `dispatch_context_unavailable`.
3. **Wake payload arity.** `StartWake`'s `wake_seated` is 5-field (`assignment_version` in slot 2); every caller binds the
   5-field form or matches the constructor tag and reads `WakeEventRef` by field.
4. **Named seating closure.** All seven AG4 owners take the declared INPUTS, return the structured seated/already/failed
   set, are idempotent via `driver_event_seat` (or `driver_intake_no_round`), and each is reached by ≥1 literal `CALL`.
5. **Cross-round continuity.** `CloseRoundAssignments` publishes `prior_round_terminal_state` and conditionally seats the
   next bootstrap; `RoundInitialise` consumes it via `prior_state`.
6. **Acceptance-batch context/generation.** `SeatAcceptanceBatchFinalize` drops `source_context`; `AcceptanceBatchFinalize`
   gains `batch_generation`; `BlockAcceptancePoint` seats first, captures the generation, and registers into it.
7. **Per-run / per-round field ownership.** The five new `RunInitialise` fields and the one new `RoundInitialise` field are
   both initialised in EFFECTS and returned explicitly, and each is consumed by an AG4 owner.
8. **Signature ↔ RETURNS ↔ call-site agreement** holds for every AG-touched procedure.

## 4. Call-graph closure result

Method: extract `^(PROCEDURE|FUNCTION)\s+<Name>` as definitions and `\bCALL\s+<Uppercase-Name>` as references; the set
difference (references − definitions) must be empty.

- **Defined callables (`PROCEDURE`/`FUNCTION`):** 104 (each name defined exactly once; no duplicate definition).
- **Distinct literal `CALL <Uppercase>` targets:** 82.
- **Dangling references (called but not defined):** **0.**

Every one of the 82 distinct `CALL` targets resolves to a defined callable. The seven AG4 procedures are defined and each
is reachable (§2); the AF4 driver wrappers and `AcceptanceBatchFinalize` carry zero literal `CALL` sites by design (they
are dispatched dynamically via `CALL inv.procedure WITH inv.args`, AG1) yet are reachable through their descriptor
`handler_procedure` and their named seat owners. This matches `STAGE_01AG_PROCEDURE_CALL_GRAPH.md` (0 dangling; 104
defined callables).

## 5. Verdict

For every procedure TOUCHED or ADDED by Stage 1AG, the declared INPUTS, the declared RETURNS disposition set, and every
call site AGREE: (a) INPUTS match each call site; (b) RETURNS match each body; (c) callers inspect or propagate the
disposition. The call graph closes with **0 dangling references** across **104 defined callables**. **PoCol** and the idle
policy within it are unchanged, and the **A1 baseline `8.420833333 kWh` is preserved**. No defects were found.
