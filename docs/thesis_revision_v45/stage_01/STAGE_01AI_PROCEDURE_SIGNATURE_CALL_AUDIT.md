# Stage 1AI — Procedure Signature & Call-Site Audit

This audit verifies, for every procedure that Stage 1AI added or changed in the FINAL
`STAGE_01_PROTOCOL_PSEUDOCODE.md`, that (a) each `CALL` target resolves to a defined callable, (b) each call
site of a changed procedure passes the new/required arguments, (c) every result token a caller inspects is
present in the callee's declared `RETURNS` union, and (d) the two new callables are both defined and called.
All anchors are `file:line` into `docs/thesis_revision_v45/stage_01/STAGE_01_PROTOCOL_PSEUDOCODE.md` (the
sole subject document; this audit modifies no other file). Stage 1AI is a documentation-only formal-spec
correction of the PoCol Stage-1 protocol — no experiment, source, config, DOCX/PDF, or prior Stage-1A..1AH
artifact was touched.

## 1. Total defined callables

**110 defined callables** in the FINAL pseudocode: **108 `PROCEDURE` + 2 `FUNCTION`**
(`^PROCEDURE\s+\w+` = 108; `^FUNCTION\s+\w+` = 2). The two functions are
`outcome_consistent_with_census` (`:4751`) and `ClassifyRecoveryWork` (`:5042`). Definition extraction ran
`^(PROCEDURE|FUNCTION)\s+(\w+)`; call extraction ran `\bCALL\s+([A-Za-z_][\w.]*)` over the same file.

## 2. Dangling-reference result — **NONE genuine**

Every `CALL <Name>` whose target is an upper-case-initial identifier resolves to a defined `PROCEDURE`/
`FUNCTION`. The mechanical `\bCALL\s+…` scan surfaces **6 non-resolving hits, all regex false positives**
(prose or a dynamic-dispatch adapter, never a static procedure target):

| Hit | Anchor | Why it is a false positive |
|-----|--------|----------------------------|
| `CALL inv.procedure WITH inv.args` | `:351` | Dynamic dispatch — the dispatcher invokes the resolved handler bound by `BuildHandlerInvocation`; `inv.procedure` is a bound value, not a named callable. |
| `… the CALL is not guarded …` | `:204` | Prose (`is`). |
| `… NOT a CALL target …` | `:765`, `:3035` | Prose disclaimer that a lower-case predicate notation is `target`, not a call. |
| `… instead CALL the same canonical RoundAbort …` | `:2171` | Prose (`the`); the real callable `RoundAbort` is defined at `:7245`. |
| `… After SET disp <- CALL target(...) …` | `:2222` | Prose placeholder (`target`). |
| `… CALL this writer …` / `… CALL this rather than writing …` | `:2484`, `:2512` | Prose (`this`). |

**Genuine dangling targets: 0.**

## 3. The two NEW callables — defined AND called

| Callable | Defined | Call sites | Count |
|----------|---------|-----------|-------|
| `SetDriverRequestStatus(RunContext, DriverRequestID, expected_status, new_status, disposition)` | `:1760` | `:1063` (CancelQueuedEvent, SEATED→CANCELLED), `:1385` (RoundInitialiseEvent, genesis PENDING→REJECTED), `:1646` (SeatMinerRegister, PENDING→SEATED), `:1685` (SeatReserveActivate, PENDING→SEATED), `:1795` (CompleteDriverRequestOnDispatch, SEATED→CONSUMED), `:1824` (SeatPendingDriverRequests, scope-stale PENDING→REJECTED), `:1840` (SeatPendingDriverRequests, replay-noop PENDING→SEATED), `:1845` (SeatPendingDriverRequests, seat-failed PENDING→REJECTED) | **8** |
| `CompleteDriverRequestOnDispatch(RunContext, seat_event_ref, disposition)` | `:1784` | `:325`, `:336`, `:347`, `:362` — all in `ProcessEventTime` (integrity-failure, context-unavailable, binding-failed, and the ordinary SEATED→CONSUMED completion) | **4** |

`SetDriverRequestStatus` is the SOLE guarded mutator of `driver_request.status` (a CAS-style
`expected_status` guard + a legal-transition table; `RETURNS` at `:1780–1782`).
`CompleteDriverRequestOnDispatch` resolves the request from the TRUSTED seat `EventRef` and delegates the
SEATED→CONSUMED edge to `SetDriverRequestStatus` (`RETURN CALL …`, `:1795`); its `RETURNS` is
`(SetDriverRequestStatus result) | driver_request_not_a_seat(seat_event_ref)` (`:1796`).

## 4. AI-changed procedures — signature / RETURNS / call-site agreement

| Procedure | Change (Stage 1AI) | Call sites checked | Verdict |
|-----------|--------------------|--------------------|---------|
| `AdmitDriverRequest` (`:1711`) | Signature gains `round_scope`; `RETURNS` = `driver_request_admitted \| driver_request_already_admitted \| driver_request_time_before_admission_rejected \| driver_request_scope_invalid` (`:1752–1754`). | `:3238` (RoundInitialise) — passes `round_scope = EXACT_ROUND(RoundID_current)` (`:3239`); result asserted `driver_request_admitted(_)` (`:3241`), a token in the union. **Sole call site; `round_scope` present.** | **PASS** |
| `SeatMinerRegister` (`:1607`) | Signature gains `admission_mode ∈ {IN_DISPATCH_GENESIS, DRIVER_INTAKE}` (`:1608–1609`). | `:1379` (RoundInitialiseEvent) — `admission_mode = IN_DISPATCH_GENESIS`; `:1832` (SeatPendingDriverRequests) — `admission_mode = DRIVER_INTAKE`. **Both call sites pass `admission_mode`.** | **PASS** |
| `MinerRegister` (`:3965`) / `MinerRegisterEvent` (`:1435`) | New disposition union: `miner_registered \| miner_registered_barrier_pending \| miner_registered_participant_setup_seated \| _already_seated \| _aborted(…, participant_setup_seat_failed_round_abort(reason))`. | `MinerRegisterEvent` calls `MinerRegister` at `:1443` and propagates verbatim via `RETURN mr` (`:1444`). Callee `RETURNS` (`:4012–4014`) is byte-for-byte the wrapper `RETURNS` (`:1445–1447`) — the propagated union matches. | **PASS** |
| `ScheduleEvent` (`:834`) | Four new AI2 rejection variants in `RETURNS`: `rejected_driver_target_before_simulation_frontier` (`:993`), `rejected_driver_context_mismatch` (`:994`), `rejected_driver_kind_event_type_mismatch` (`:995`), `rejected_driver_target_context_mismatch` (`:996`); each produced inside the DRIVER / TERMINAL_ROTATION switch cases (`:896`, `:898`, `:900`, `:903`, `:910`, `:912`, `:914`, `:918`). | All 12 callers test `IF r = scheduled(event_ref, record)` and treat every non-success token as an opaque `reason` (e.g. `SeatMinerRegister :1650`, `SeatReserveActivate :1689`). No caller `CASE`-matches any of the four rejection tokens directly, so no caller can match a token outside the union. | **PASS** |
| `CloseRoundAssignments` (`:6802`) | `RETURNS closure_record(publication_result)` (`:6919–6920`); captures the terminal-publication result rather than discarding it (`:6914–6915`). | `:6783` (ValidBlockAccept), `:7287` (RoundAbort), `:7419` (CloseRoundAtHorizon) — each `SET clo <- CALL …` then `ASSERT clo = closure_record(publication_result = RoundContext.RunContext.terminal_publication_result)` (`:6789`, `:7293`, `:7424`). Result inspected at every site. | **PASS** |
| `RunEventLoopToHorizon` (`:508`) | `RETURNS` adds `run_completed_partial(next_round_bootstrap_failed)` (`:562`); produced on the AI6 terminate-partial path (`:545`) under `next_round_bootstrap_status = NEXT_ROUND_BOOTSTRAP_FAILED`. | Run-level driver; the added disposition is produced from a token (`NEXT_ROUND_BOOTSTRAP_FAILED`) that `CloseRoundAssignments` sets (`:6917`) — producer/consumer agree. | **PASS** |
| `RoundInitialiseEvent` (`:1358`) | Adds the `genesis_registration_seat_failed_round_abort` disposition; `RETURNS` = `round_initialised(RoundID) \| round_initialise_aborted(RoundID, template_commit_seat_failed_round_abort(reason)) \| round_initialise_aborted(RoundID, genesis_registration_seat_failed_round_abort(reason))` (`:1405–1406`). | Produced at `:1388–1389` when `SeatMinerRegister(… IN_DISPATCH_GENESIS)` returns `miner_register_seat_failed(_, greason)` (`:1380`). The genesis-fail branch terminalises the request via `SetDriverRequestStatus` (`:1385`) and aborts via `RoundAbort` (`:1388`); the returned disposition is in the union. | **PASS** |

### Check 3 detail — `SeatPendingDriverRequests` consumes the seat-owner unions exactly

`SeatPendingDriverRequests` (`:1798`) routes each PENDING request (`:1831–1833`) and `SWITCH`es on the seat
result (`:1834–1848`):

- `miner_register_seated(_,_) | reserve_activate_seated(_,_)` (`:1835`) — in `SeatMinerRegister` `RETURNS` (`:1651`) and `SeatReserveActivate` `RETURNS` (`:1690`).
- `miner_register_already_seated(_, event_ref) | reserve_activate_already_seated(_, event_ref)` (`:1837`) — in both unions (`:1651`, `:1690`).
- `miner_register_seat_failed(_, reason) | reserve_activate_seat_failed(_, reason)` (`:1844`) — in both unions (`:1652`, `:1691`).

Every matched token is present in the callee `RETURNS`; the three switch arms exhaust both owners' non-empty
result sets. No unlisted token is matched.

## 5. Cross-checks performed

1. **Call resolution.** 94 distinct `CALL` targets; every upper-case-initial target resolves to one of the
   110 defined callables; the 6 non-resolving hits are the prose/dynamic-dispatch false positives of §2.
   Genuine dangling references: **0**.
2. **Required new arguments.** `AdmitDriverRequest`'s only call site passes `round_scope` (`:3239`);
   `SeatMinerRegister`'s two call sites pass `admission_mode` — `IN_DISPATCH_GENESIS` in
   `RoundInitialiseEvent` (`:1379`) and `DRIVER_INTAKE` in `SeatPendingDriverRequests` (`:1832`).
3. **RETURNS ↔ caller-switch agreement.** The AI dispositions verified in situ:
   `miner_registered_*` propagated verbatim by `MinerRegisterEvent` (`:1444`) match `MinerRegister`
   (`:4012–4014`); the four AI2 `ScheduleEvent` rejections are all in its `RETURNS` (`:993–996`) and no
   caller matches a token outside it; the `SeatMinerRegister`/`SeatReserveActivate` results consumed by
   `SeatPendingDriverRequests` all appear in the callee unions (§ check-3 detail).
4. **New callables.** `SetDriverRequestStatus` (defined `:1760`, 8 call sites) and
   `CompleteDriverRequestOnDispatch` (defined `:1784`, 4 call sites) are each defined and called.
5. **Single-mutator discipline.** Every `driver_request.status` write routes through `SetDriverRequestStatus`
   (the CAS-style guard); the SEATED→CONSUMED completion routes through `CompleteDriverRequestOnDispatch` off
   the immutable reverse binding `driver_request_by_seat_event_ref` — no procedure overwrites the status
   directly.
6. **Terminal-round idle handling.** `CloseRoundAssignments` moves an `ACTIVE_HASHING` holder into
   `LOW_POWER_LISTEN` at closure via `EnterLowPowerListen` (`:6831`), consistent with the idle policy within
   PoCol; this signature change (`closure_record(publication_result)`) does not alter that behaviour and its
   result is inspected at all three call sites.

## 6. Overall verdict — **PASS**

Across all Stage-1AI-added and Stage-1AI-changed procedures, the signatures, the declared `RETURNS`
disposition sets, and every call site AGREE. The call graph resolves with **0 genuine dangling references**
over **110 defined callables** (108 `PROCEDURE` + 2 `FUNCTION`). Both new callables
(`SetDriverRequestStatus`, `CompleteDriverRequestOnDispatch`) are defined and called (8 and 4 sites); every
changed-procedure call site passes the new/required arguments; every inspected result token is present in the
callee's union. **No mismatch found.**
