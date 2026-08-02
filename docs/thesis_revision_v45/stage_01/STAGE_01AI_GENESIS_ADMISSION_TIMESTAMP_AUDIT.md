# Stage 1AI — Genesis-Admission Timestamp Audit (AI1)

**Scope.** This is a documentation-only formal-spec audit of correction **AI1** (genesis-admission
timestamp deadlock fix) against the FINAL normative tree of the PoCol Stage-1 protocol. It verifies
the correction as written in
`docs/thesis_revision_v45/stage_01/STAGE_01_PROTOCOL_PSEUDOCODE.md`. No source, config, DOCX, PDF, or
any Stage-1A..1AH artifact was modified; no experiment was run. All anchors below are `file:line`
references obtained by reading the normative file directly (the file is
`STAGE_01_PROTOCOL_PSEUDOCODE.md` throughout; line numbers are from the FINAL tree at the 1AI
worktree HEAD).

---

## 1. The defect AI1 fixes (statement)

In the PoCol Stage-1 driver-scheduling model, `RoundInitialise` imports the declared genesis miner
set for the first round by ADMITTING one `MINER_JOIN` `driver_request` per genesis miner, each with
`requested_event_time = EQ.current_event_time` (the round-setup time `t0`) and
`round_scope = EXACT_ROUND(RoundID_current)`, leaving each request `PENDING` on
`pending_driver_request_index` (`STAGE_01_PROTOCOL_PSEUDOCODE.md:3235`–`3244`). Before AI1 the ONLY
seating path for a `PENDING` request was the run-level outer loop `SeatPendingDriverRequests`, which
`RunEventLoopToHorizon` invokes BEFORE it selects the next earliest queue `event_time`
(`STAGE_01_PROTOCOL_PSEUDOCODE.md:536`). But the genesis requests are admitted *inside*
`RoundInitialise`, which runs *inside* the `RoundInitialiseEvent` handler dispatched by
`ProcessEventTime(t0)`; by the time that dispatch returns, `ProcessEventTime` has already added `t0`
to `finalised_event_times` in its epilogue (`STAGE_01_PROTOCOL_PSEUDOCODE.md:422`). The subsequent
outer-loop intake would therefore route each genesis `MinerRegisterEvent` to `ScheduleEvent` with
`target_event_time = requested_event_time = t0`, which is now finalised, and `ScheduleEvent` returns
`rejected_finalised_time` (`STAGE_01_PROTOCOL_PSEUDOCODE.md:870`–`871`). Every genesis registration
would then fail to seat, the initial-registration barrier (AH5) could never be satisfied, participant
setup would never seat, and the first round would deadlock. AI1 removes the deadlock by seating each
genesis `MinerRegisterEvent` SYNCHRONOUSLY inside the same `RoundInitialiseEvent` dispatch at the
still-live (non-finalised) `t0`, via an ORDINARY_DISPATCH origin, so `ScheduleEvent`'s finalised-time
guard is never reached.

---

## 2. Verification table

| # | AI1 claim | Evidence (`file:line`) | Verdict |
|---|-----------|------------------------|---------|
| 1 | `RoundInitialise` admits one `MINER_JOIN` `driver_request` **per declared genesis miner** with `round_scope = EXACT_ROUND(RoundID_current)` and `requested_event_time = EQ.current_event_time` (`t0`). | Genesis-import block iterates `RunContext.genesis_miner_registry` and calls `AdmitDriverRequest(kind = MINER_JOIN, requested_event_time = EQ.current_event_time, round_scope = EXACT_ROUND(RoundID_current), payload = { join_request })` per entry: `STAGE_01_PROTOCOL_PSEUDOCODE.md:3235`–`3241`; barrier `expected` populated + registry consumed once: `:3242`–`3244`. Guarded first-round only (`prior_state = null`): `:3235`. | **PASS** |
| 2 | The `RoundInitialiseEvent` handler, **AFTER publishing the RoundContext**, SEATS each genesis `MinerRegisterEvent` SYNCHRONOUSLY via `SeatMinerRegister(..., admission_mode = IN_DISPATCH_GENESIS)` — an ORDINARY_DISPATCH origin, target `= EQ.current_event_time` (`t0`, not yet finalised). | RoundContext published at `STAGE_01_PROTOCOL_PSEUDOCODE.md:1368`; genesis-seat loop immediately after, iterating `pending_driver_request_index`, filtering to `PENDING`/`MINER_JOIN`/`EXACT_ROUND(rc.RoundID)`, calling `SeatMinerRegister(RunContext, driver_request = gdr, admission_mode = IN_DISPATCH_GENESIS)`: `:1376`–`1379`. Explicitly NOT left for the outer loop (design note): `:1369`–`1375`. Same-`t0` dispatch is guaranteed because `ProcessEventTime` re-pops the smallest queued event each iteration so a handler's same-cycle addition is observed immediately, all before the epilogue finalises `t0`: `:296`, `:422`. | **PASS** |
| 3 | `SeatMinerRegister` has an `admission_mode` param `{IN_DISPATCH_GENESIS, DRIVER_INTAKE}`; `IN_DISPATCH_GENESIS` builds `ordinary_dispatch_origin(EQ)` and targets `EQ.current_event_time`. | Signature + enumerated modes: `STAGE_01_PROTOCOL_PSEUDOCODE.md:1607`–`1609`. `SWITCH admission_mode` → `CASE IN_DISPATCH_GENESIS: target_time <- EQ.current_event_time; origin <- ordinary_dispatch_origin(EQ)`: `:1624`–`1627`. `DRIVER_INTAKE` builds an explicit `DRIVER(...)` origin on the authoritative admission time (the other branch): `:1628`–`1635`. Seat call uses the mode-derived `target_time`/`origin`: `:1636`–`1639`. On `scheduled`, transitions the request `PENDING → SEATED` and clears the pending index atomically: `:1640`–`1649`. | **PASS** |
| 4 | The initial-registration barrier (AH5) still defers `PrepareParticipantsForNewRound` until all genesis miners register, so all genesis registrations execute before participant preparation. | Barrier set `satisfied = false` with `expected =` declared genesis set at admission: `STAGE_01_PROTOCOL_PSEUDOCODE.md:3243`. `TemplateCommitEvent` defers participant-setup seating while the barrier is unsatisfied (`template_committed_participant_setup_deferred`): `:1421`–`1422`. `MinerRegister` marks each genesis miner registered, and only when the FULL declared set has registered seats participant setup exactly once (else returns `barrier_pending`): `:3990`–`4007`. `PrepareParticipantsForNewRound` carries a defensive barrier guard returning `participant_setup_registration_barrier_pending`: `:3376`–`3377` (precondition stated `:3366`–`3369`). | **PASS** |
| 5 | A genesis registration that cannot seat **aborts the round** with `genesis_registration_seat_failed_round_abort`. | On `miner_register_seat_failed(_, greason)`: terminalise the request `PENDING → REJECTED` + remove from pending index, then `RoundAbort(rc, reason = genesis_registration_seat_failed_round_abort(greason), ...)` and `RETURN round_initialise_aborted(rc.RoundID, genesis_registration_seat_failed_round_abort(greason))`: `STAGE_01_PROTOCOL_PSEUDOCODE.md:1380`–`1389`. Declared in the RETURNS set: `:1405`–`1406`. | **PASS** |
| 6 | Executable genesis invariant (see §3). | See §3. | **PASS** |

---

## 3. Executable genesis invariant

**Invariant (AI1).** *Every `PENDING` genesis registration has either a live `QUEUED`
`MinerRegisterEvent` at a non-finalised `event_time`, OR a terminal `REJECTED`/`CANCELLED`
disposition; no genesis request remains `PENDING` after its source timestamp is finalised.*

**Discharge by construction (with anchors):**

1. **Admission.** A genesis request is created `PENDING` with `requested_event_time = t0` and added to
   `pending_driver_request_index` (`STAGE_01_PROTOCOL_PSEUDOCODE.md:3238`–`3244`,
   `AdmitDriverRequest` sets `status = PENDING` + indexes it: `:1746`–`1750`).

2. **`t0` is provably non-finalised at seat time.** The seat loop runs while the
   `RoundInitialiseEvent` for `t0` is still being dispatched inside `ProcessEventTime(t0)`'s drain
   loop; `t0` is added to `finalised_event_times` only in the epilogue, which runs strictly AFTER the
   drain reaches quiescence (`STAGE_01_PROTOCOL_PSEUDOCODE.md:288`–`289` drain, `:422` finalise; the
   dispatcher asserts it never dispatches into a finalised time, `:297`). Therefore
   `t0 ∉ EQ.finalised_event_times` when `SeatMinerRegister` runs.

3. **Seat succeeds → SEATED, live QUEUED at non-finalised `t0`.** `IN_DISPATCH_GENESIS` targets
   `EQ.current_event_time = t0` via `ordinary_dispatch_origin(EQ)`
   (`STAGE_01_PROTOCOL_PSEUDOCODE.md:1626`–`1627`). `ScheduleEvent`'s finalised-time guard tests
   `target_event_time in EQ.finalised_event_times` (`:870`); with `t0` non-finalised (step 2) the
   guard is NOT taken, the ORDINARY_DISPATCH branch derives `dc` and the event is enqueued `QUEUED`
   (`:920`–`931`, `:972`–`988`), and the request transitions `PENDING → SEATED` with the pending
   index cleared atomically with the seat (`:1640`–`1649`). The request is thus no longer `PENDING`
   and its `MinerRegisterEvent` is a live `QUEUED` event at the non-finalised `t0` (indeed it is
   drained in the SAME `ProcessEventTime(t0)` by the re-pop rule, `:296`).

4. **Seat fails → terminal REJECTED + round abort.** On `miner_register_seat_failed`, the request is
   set `PENDING → REJECTED` (`SetDriverRequestStatus`, `STAGE_01_PROTOCOL_PSEUDOCODE.md:1385`–`1386`),
   removed from the pending index (`:1387`), and the round is aborted
   (`:1388`–`1389`). No `PENDING` genesis request survives the handler.

5. **No `PENDING` genesis request outlives `t0`'s finalisation.** Every genesis request has left
   `PENDING` (→ `SEATED` per step 3, or → `REJECTED`/round-abort per step 4) BEFORE
   `RoundInitialiseEvent` returns, and `RoundInitialiseEvent` returns before `ProcessEventTime(t0)`'s
   epilogue finalises `t0` (`:422`). The pre-AI1 finalised-time seat
   (`rejected_finalised_time`, `:870`–`871`) is therefore never reached for a genesis request.

The invariant holds. **PASS.**

---

## 4. Residual observations

- The genesis path is exercised only for the FIRST round (`prior_state = null AND
  genesis_miner_registry non-empty`, `STAGE_01_PROTOCOL_PSEUDOCODE.md:3235`); subsequent-round
  barriers default to `satisfied = true` (`:3214`), and later external joins use `AdmitDriverRequest`
  with `NEXT_AVAILABLE_ROUND` scope routed through `SeatPendingDriverRequests`
  (`:1832`) — consistent with AI1's scoping and not affected by the fix.
- `SeatPendingDriverRequests` explicitly documents that first-round genesis miners are seated
  IN-DISPATCH by `RoundInitialiseEvent` (AI1) and are NOT expected from the outer intake
  (`STAGE_01_PROTOCOL_PSEUDOCODE.md:1805`–`1807`), so no double-seat or silent loss arises across the
  two paths (idempotent replay key on `DriverRequestID`, `:1619`).
- No genesis request is routed only through the outer loop, and no genesis seat targets a finalised
  `event_time`. No defect found.

---

## Overall verdict

**PASS** — AI1 (genesis-admission timestamp deadlock fix) is correctly and completely reflected in
the FINAL normative tree: genesis `MINER_JOIN` requests are admitted at `t0` by `RoundInitialise`,
seated SYNCHRONOUSLY in-dispatch by `RoundInitialiseEvent` via
`SeatMinerRegister(admission_mode = IN_DISPATCH_GENESIS)` at the non-finalised `t0` through an
ORDINARY_DISPATCH origin (never reaching `rejected_finalised_time`), the AH5 barrier still gates
participant preparation, an unseatable genesis registration aborts the round with
`genesis_registration_seat_failed_round_abort`, and the executable genesis invariant is discharged by
construction. No defect found.
