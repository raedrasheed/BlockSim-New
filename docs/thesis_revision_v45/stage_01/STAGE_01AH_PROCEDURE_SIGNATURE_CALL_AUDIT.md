# Stage 1AH — Procedure Signature / RETURNS / Call-Site Consistency Audit

**Scope.** Documentation-only. This audit inspects ONLY the final normative tree
`docs/thesis_revision_v45/stage_01/`, primary file `STAGE_01_PROTOCOL_PSEUDOCODE.md`
(7158 lines). It verifies that for every procedure Stage 1AH changed or added, the
`INPUTS`, the `CALL` sites, and the `RETURNS` union are mutually consistent; that the
call-graph is closed (0 dangling calls); and that no procedure reads a removed field.

The algorithm is **PoCol**; the mechanism exercised is **the idle policy within PoCol**.
No consensus property is claimed. The A1 baseline `8.420833333 kWh` is **unchanged** —
nothing in the Stage-1AH edits touches the energy model; these are pseudocode
signature/call/RETURNS revisions only.

All citations are `file:line` into `STAGE_01_PROTOCOL_PSEUDOCODE.md` unless noted.

---

## 1. Per-procedure INPUTS / CALL / RETURNS consistency

### 1.1 `ScheduleEvent` (def. 765)

| Check | Evidence | Verdict |
|-------|----------|:------:|
| INPUTS include `scheduling_origin` | `:768` — `scheduling_origin  # AH1: SchedulingOrigin (§0.7e), REQUIRED and EXPLICIT` | **PASS** |
| `scheduling_origin` REPLACES `post_epilogue_context` (not both) | `:770` — "This REPLACES the AG post_epilogue_context flag"; no `post_epilogue_context` in the INPUTS block (`:766–777`) | **PASS** |
| RETURNS union includes `rejected_invalid_scheduling_origin` | `:886` (produced at `:830`) | **PASS** |
| RETURNS union includes `rejected_driver_target_before_source` | `:887` (produced at `:813`) | **PASS** |
| Every executable `CALL ScheduleEvent` passes `scheduling_origin` | 18 call sites, each with an explicit origin one line below the call: `:1378→1381`, `:1399→1402`, `:1417→1420`, `:1460→1463`, `:1488→1491`, `:1508→1511`, `:2443→2446`, `:3108→3114`, `:3741→3745`, `:4300→4305`, `:4553→4559`, `:4714→4720`, `:5173→5179`, `:6053→6057`, `:6067→6071`, `:6196→6200`, `:6252→6256`, `:6806→6812` | **PASS** |

The 3 other `CALL ScheduleEvent` grep hits (`:572`, `:576`, `:583`) are prose in §0.7e
(the `SCHEDULE` shorthand definition and the L6 sole-delta-cycle rule), not executable
call sites; the shorthand itself binds `scheduling_origin = ordinary_dispatch_origin(EQ)`
(`:573`).

**Observation (non-defect).** `:2479` (a NOTE inside `StartWake`) still uses the old
phrase "ScheduleEvent receives post_epilogue_context explicitly". This is stale narrative
prose only — the `StartWake` call itself passes `scheduling_origin = wake_origin`
(`:2446`, built from `POST_EPILOGUE(pctx)` at `:2435`), so the signature and the call are
correct. Not counted as a signature/call/RETURNS mismatch (out of remit to edit source).

### 1.2 `SeatNextRoundBootstrap` (def. 1351)

| Check | Evidence | Verdict |
|-------|----------|:------:|
| INPUTS = `RunContext` | `:1352` | **PASS** |
| RETURNS union = seated / already_seated / no_request / seat_failed | `:1387–1389` (`round_bootstrap_seated`, `round_bootstrap_already_seated`, `round_bootstrap_no_request`, `round_bootstrap_seat_failed`) | **PASS** |
| Caller `RunEventLoopToHorizon` consumes the result | `:499` `SET boot0 <- CALL SeatNextRoundBootstrap(RunContext)`; inspected `:500` | **PASS** |
| Caller `PublishTerminalRoundAndSeatNext` consumes the result | `:6560` `SET boot <- CALL SeatNextRoundBootstrap(RunContext)`; `SWITCH boot` `:6561–6566` | **PASS** |

### 1.3 `SeatMinerRegister` (def. 1447) / `SeatReserveActivate` (def. 1471)

| Check | Evidence | Verdict |
|-------|----------|:------:|
| `SeatMinerRegister` takes `driver_request` (not a bare join_request) | `:1448` — "the MINER_JOIN driver_request record (not a bare join_request)" | **PASS** |
| `SeatReserveActivate` takes `driver_request` (not RoundID+deficit) | `:1472` — "the ORDINARY_RESERVE_DEFICIT driver_request record" (RoundID/deficit read from `driver_request.payload`, `:1477`) | **PASS** |
| RETURNS carry the `DriverRequestID` | `SeatMinerRegister` `:1468–1469`; `SeatReserveActivate` `:1497–1498` (all variants carry `DriverRequestID`) | **PASS** |
| Callers in `SeatPendingDriverRequests` pass `driver_request` and consume | `:1552` `CALL SeatMinerRegister(RunContext, driver_request = dr)`; `:1553` `CALL SeatReserveActivate(RunContext, driver_request = dr)`; `SWITCH res` `:1554–1566` | **PASS** |

### 1.4 New-owner set: INPUTS/RETURNS defined + call sites matched

| Procedure | Def / INPUTS / RETURNS | CALL site(s) — args + result | Verdict |
|-----------|------------------------|------------------------------|:------:|
| `AdmitDriverRequest` | def `:1518`; INPUTS `RunContext, kind, requested_event_time, payload` `:1519`; RETURNS `driver_request_admitted(DriverRequestID)` `:1531` | `:2868` `CALL AdmitDriverRequest(RunContext, kind = MINER_JOIN, requested_event_time = EQ.current_event_time, payload = { join_request = g.join_request })` — args match; producer call (barrier built from `expected`, `:2870`) | **PASS** |
| `SeatPendingDriverRequests` | def `:1533`; INPUTS `RunContext` `:1534`; RETURNS `driver_intake_completed(seated_count, rejected_count) | driver_intake_no_round` `:1568` | `:515` `CALL SeatPendingDriverRequests(RunContext)` — args match; effectful intake (loop re-checks the queue `:516`, count-return intentionally not captured, same convention as other run-level effectful calls) | **PASS** |
| `SeatParticipantSetupOrAbort` | def `:1427`; INPUTS `RunContext, RoundContext, RoundID_at_seat, TemplateID_at_seat, abort_envelope` `:1428`; RETURNS `:1444–1445` | `:1275` (`SET ps <- CALL …`; `SWITCH ps` `:1277`, consumed) and `:3625` (barrier-completion path; args match `:3625–3626`) | **PASS** |
| `PublishTerminalRoundAndSeatNext` | def `:6527`; INPUTS `RoundContext, disposition, dispatch_envelope` `:6528`; RETURNS `:6567–6568` | `:6514` `CALL PublishTerminalRoundAndSeatNext(RoundContext, disposition = disposition, dispatch_envelope = dispatch_envelope)` — args match; seat-failure disposition self-recorded internally (`:6565`) | **PASS** |
| `FinalizeSimulationRunNoRound` | def `:6944`; INPUTS `RunContext, reason` `:6945`; RETURNS `run_finalised_no_round(reason)` `:6958` | `:504` `CALL FinalizeSimulationRunNoRound(RunContext, reason = bootstrap_seat_failed_run_abort)` — args match; effectful terminal finaliser | **PASS** |

Note: `FinalizeSimulationRunNoRound` also has a defensive idempotency early-return
`run_already_finalised` (`:6951`) not enumerated in its RETURNS union (`:6958`). This is
**not** a Stage-1AH regression — it mirrors the pre-existing house convention of
`FinalizeSimulationRun`, whose identical guard `RETURN run_already_finalised` (`:6923`) is
likewise omitted from its RETURNS union `run_finalised(T)` (`:6936`). Consistent by
precedent; no fix warranted.

### 1.5 `BlockAcceptancePoint` (def. 6121) — `dispatch_envelope` three-way agreement

| Check | Evidence | Verdict |
|-------|----------|:------:|
| INPUTS include `dispatch_envelope` | `:6122` — `INPUTS: RoundContext, certificate, snapshot, CandidateID, PropagationID, outcome, dispatch_envelope   # AH7 (recv env = yes)` | **PASS** |
| Descriptor row: recv env = **yes** | `:1138` — final columns `… | **yes** (AH7) | no |` | **PASS** |
| Binding row: `dispatch_envelope -> dispatch_envelope` injected, recv env = yes | `:1169` — runtime_injected `RoundContext -> RoundContext; dispatch_envelope -> dispatch_envelope (AH7: recv env = yes …)` | **PASS** |

Descriptor payload (`:1138`) + binding map (`:1169`) produce exactly the 7-key
`handler_inputs` set at `:6122` (AG1 verify). All three rows agree.

### 1.6 Wrapper RETURNS unions carry the new AH6/AH5 dispositions

| Disposition (task) | Wrapper | Evidence | Verdict |
|--------------------|---------|----------|:------:|
| `round_initialise_aborted` | `RoundInitialiseEvent` | RETURNS `:1257` (produced `:1256`) | **PASS** |
| `template_committed_participant_setup_deferred` | `TemplateCommitEvent` | RETURNS `:1283` (produced `:1273`) | **PASS** |
| `template_commit_participant_setup_aborted` | `TemplateCommitEvent` | RETURNS `:1284` (produced `:1281`) | **PASS** |
| `participant_setup_registration_barrier_pending` | `PrepareParticipantsEvent` (propagated) + `PrepareParticipantsForNewRound` (source) | wrapper RETURNS `:1302`; source RETURNS `:3130` (produced `:3005`) | **PASS** |

### 1.7 `RunInitialise` (def. 2727) / `RoundInitialise` (def. 2804) RETURNS include new AH fields

| Check | Evidence | Verdict |
|-------|----------|:------:|
| `RunInitialise` RETURNS the AH2/AH3 bootstrap fields | `:2775` `bootstrap_request_registry, current_bootstrap_request` (init `:2758–2762`) | **PASS** |
| `RunInitialise` RETURNS the AH4 driver-request fields | `:2776` `driver_request_registry, driver_request_seq, pending_driver_request_index` (init `:2763–2765`) | **PASS** |
| `RunInitialise` RETURNS the AH5 genesis field | `:2777` `genesis_miner_registry` (init `:2766`) | **PASS** |
| `RunInitialise` RETURNS AG4 seat fields | `:2774` `driver_event_seat, next_round_setup_seq` | **PASS** |
| `RoundInitialise` RETURNS the AH5 barrier field | `:2887` `initial_registration_barrier` (init `:2847`) | **PASS** |
| `RoundInitialise` RETURNS AG4 activation ordinal | `:2878` `reserve_activation_seq` | **PASS** |

---

## 2. Call-graph closure

Extracted every `^(PROCEDURE|FUNCTION) <Name>` definition and every `CALL <Uppercase>`
site from the final text.

| Metric | Value | Verdict |
|--------|-------|:------:|
| Defined callables (`PROCEDURE`/`FUNCTION`) | **108** | — |
| Distinct `CALL` targets | 86 | — |
| Dangling calls (`CALL` with no matching definition) | **0** | **PASS** |
| Duplicate definitions | 0 | **PASS** |

The defined-but-not-`CALL`ed set is fully accounted for and contains **no orphans**:
the 20 event handlers reached by dispatch (via `BuildHandlerInvocation` / the §0.7g
descriptor table `:1130–1149`, e.g. `RoundInitialiseEvent`, `TemplateCommitEvent`,
`PrepareParticipantsEvent`, `MinerRegisterEvent`, `ReserveActivateEvent`,
`FullRangeExhaustEvent`, `BlockAcceptancePoint`, `HashWorkEvent`, `WakeCompleteEvent`,
recovery/lease/resume/participation handlers); the top-level entry points `RunInitialise`
(def. `:2727`) and `RunEventLoopToHorizon` (def. `:487`); and the pure function
`outcome_consistent_with_census` (def. `:4360`), invoked as a boolean expression at
`:4452`, `:5054`, `:5268` (no `CALL` keyword).

**Four new Stage-1AH procedures — defined AND reachable:**

| New procedure | Defined | Reachable via | Verdict |
|---------------|:------:|---------------|:------:|
| `SeatParticipantSetupOrAbort` (AH5/AH6) | `:1427` | `CALL` at `:1275` (`TemplateCommitEvent`), `:3625` (`MinerRegister`) | **PASS** |
| `AdmitDriverRequest` (AH4) | `:1518` | `CALL` at `:2868` (`RoundInitialise` genesis import) | **PASS** |
| `PublishTerminalRoundAndSeatNext` (AH2) | `:6527` | `CALL` at `:6514` (`CloseRoundAssignments`) | **PASS** |
| `FinalizeSimulationRunNoRound` (AH6) | `:6944` | `CALL` at `:504` (`RunEventLoopToHorizon`) | **PASS** |

---

## 3. No live read of a removed field

Removed fields: `round_bootstrap_time`, `pending_join_requests`,
`pending_ordinary_reserve_deficits`. Every textual occurrence is a narrative
removal/replacement note — none is a live read (`SET … <- …field`, an `IF` field access,
or a `CALL` argument):

| Line | Nature | Verdict |
|------|--------|:------:|
| `:497`, `:538` | comment: "not a fixed `round_bootstrap_time`" | narrative — **PASS** |
| `:2694` | STRUCTURE RunContext note: "it REPLACES the AG4 bare pending sets (`pending_join_requests` / `pending_ordinary_reserve_deficits`)" | narrative — **PASS** |
| `:2703` | STRUCTURE RunContext note: "`round_bootstrap_time` … is REMOVED" | narrative — **PASS** |
| `:2755`, `:2797` | `RunInitialise` comments: "NO fixed `round_bootstrap_time`" | narrative — **PASS** |

The STRUCTURE RunContext (`:2686–2704`) now declares `bootstrap_request_registry`,
`current_bootstrap_request`, `driver_request_registry`, `driver_request_seq`,
`pending_driver_request_index`, `genesis_miner_registry` in their place. No live read of
any removed field exists. **PASS**

---

## 4. Overall verdict

**OVERALL: PASS.** Across all Stage-1AH signature/RETURNS/call-site edits, every changed
or added procedure's `INPUTS`, `CALL` sites, and `RETURNS` union are mutually consistent;
the call-graph is closed (108 defined callables, 0 dangling calls); the 4 new procedures
(`SeatParticipantSetupOrAbort`, `AdmitDriverRequest`, `PublishTerminalRoundAndSeatNext`,
`FinalizeSimulationRunNoRound`) are defined and reachable; and no procedure reads a
removed field (`round_bootstrap_time`, `pending_join_requests`,
`pending_ordinary_reserve_deficits`). Algorithm remains **PoCol**; mechanism is **the idle
policy within PoCol**; the A1 baseline `8.420833333 kWh` is unchanged. The single narrative
leftover (`:2479`, stale "post_epilogue_context" wording in a `StartWake` NOTE) is a prose
nit, not a signature/call/RETURNS defect — the corresponding call correctly passes
`scheduling_origin`.
