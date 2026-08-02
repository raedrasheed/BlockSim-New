# Stage 1AH Audit — Correction AH1: Make Every Scheduling Source Explicit

**Audit target.** Correction **AH1** — every `ScheduleEvent` call must name its scheduling
source through an EXPLICIT `scheduling_origin`, the AG `post_epilogue_context` flag must be
gone, and no scheduling path may derive its delta-cycle from ambient `EQ.current_*` outside an
active ordinary dispatch.

**Files inspected (final normative tree only).**
- `STAGE_01_PROTOCOL_PSEUDOCODE.md` (primary)
- `STAGE_01_TERMINOLOGY.md` (cross-check)

Every claim below cites `file:line` anchors that were read directly. Line references without a
file prefix are in `STAGE_01_PROTOCOL_PSEUDOCODE.md`.

**Context preserved (unchanged by this audit).** The algorithm is **PoCol**; the mechanism is
**"the idle policy within PoCol"** (`STAGE_01_PROTOCOL_PSEUDOCODE.md:1`, `:6-7`;
`STAGE_01_TERMINOLOGY.md:9`). The A1 baseline continuous-full-participation control energy is
**8.420833333 kWh**, unchanged (`STAGE_01_TERMINOLOGY.md:115`, `:168`).

---

## Check 1 — §0.7e defines the SchedulingOrigin union, DriverSchedulingContext, and the ordinary_dispatch_origin(EQ) notation

| # | Item verified | Evidence | Verdict |
|---|---------------|----------|---------|
| 1a | `SchedulingOrigin` union `ORDINARY_DISPATCH(OrdinaryDispatchContext) \| DRIVER(DriverSchedulingContext) \| POST_EPILOGUE(PostEpilogueSchedulingContext)` declared in §0.7e | `685-697` (union block); restated `576-578` | PASS |
| 1b | `DriverSchedulingContext` structure carries `driver_source_kind`, `driver_request_id`, `source_event_time`, `target_event_time`, `RunContext`, `EventQueueContext` | `663-683` (struct: `driver_source_kind` `669`, `driver_request_id` `670`, `source_event_time` `672`, `target_event_time` `675`, `RunContext` `678`, `EventQueueContext` `679`) | PASS |
| 1c | `driver_source_kind` enum `{ RUN_BOOTSTRAP, ROUND_ROTATION_BOOTSTRAP, MINER_JOIN, ORDINARY_RESERVE_DEFICIT }` | `669` | PASS |
| 1d | `ordinary_dispatch_origin(EQ)` notation defined as `ORDINARY_DISPATCH(OrdinaryDispatchContext(...))` built from the current dispatch frame, valid ONLY inside an active ordinary dispatch | `698-703` | PASS |
| 1e | `PostEpilogueSchedulingContext` (S7) defined with `source_event_time` = drained epilogue t (NOT `EQ.current_*`) | `641-661` (`source_event_time` `650`) | PASS |
| 1f | Terminology addendum matches the pseudocode definitions | `STAGE_01_TERMINOLOGY.md:1222-1234` | PASS |

**Check 1 verdict: PASS.**

---

## Check 2 — ScheduleEvent takes scheduling_origin as REQUIRED input and derives delta_cycle by branching on the origin variant

| # | Item verified | Evidence | Verdict |
|---|---------------|----------|---------|
| 2a | `scheduling_origin` is a REQUIRED, EXPLICIT input of `ScheduleEvent` | `768-772` (INPUTS list) | PASS |
| 2b | The AG `post_epilogue_context` flag is explicitly REPLACED (removed from the signature) | `770-771` ("This REPLACES the AG post_epilogue_context flag") | PASS |
| 2c | `delta_cycle` derived by `SWITCH scheduling_origin`, reading ONLY the origin's own carried source frame, NEVER ambient `EQ.current_*` | `800-830` (SWITCH); ORDINARY_DISPATCH reads `octx.dispatch_envelope`/`octx.dispatched_event_ref` `815-820`, NOT ambient EQ | PASS |
| 2d | DRIVER seat derives `dc = 0` and requires `target >= source`, else `rejected_driver_target_before_source` | `809-814` | PASS |
| 2e | POST_EPILOGUE seat derives `dc = 0` and requires `target > source_event_time`, else `rejected_post_epilogue_not_strictly_later` | `803-808` | PASS |
| 2f | Absent / unrecognised origin returns `rejected_invalid_scheduling_origin` (DEFAULT case) | `829-830`; in RETURNS union `886` | PASS |
| 2g | PRECONDITIONS enumerate the three declared sources; origin is "never inferred from ambient EQ.current_*" | `778-788` | PASS |

**Check 2 verdict: PASS.**

---

## Check 3 — Every `CALL ScheduleEvent(...)` call site passes an explicit scheduling_origin

All 18 live `CALL ScheduleEvent(...)` sites (grepped exhaustively) carry an explicit
`scheduling_origin`. The shorthand `SCHEDULE …` is defined as sugar for a call carrying
`scheduling_origin = ordinary_dispatch_origin(EQ)` and is used ONLY inside an active ordinary
dispatch (`572-574`).

| Seat / handler | Event seated | Call line | `scheduling_origin` line | Origin | Verdict |
|----------------|--------------|-----------|--------------------------|--------|---------|
| SeatNextRoundBootstrap (driver) | RoundInitialiseEvent | `1378` | `1381` | `DRIVER(dctx)` | PASS |
| SeatTemplateCommit (in-dispatch) | TemplateCommitEvent | `1399` | `1402` | `ordinary_dispatch_origin(EQ)` | PASS |
| SeatPrepareParticipants (in-dispatch) | PrepareParticipantsEvent | `1417` | `1420` | `ordinary_dispatch_origin(EQ)` | PASS |
| SeatMinerRegister (driver) | MinerRegisterEvent | `1460` | `1463` | `DRIVER(dctx)` | PASS |
| SeatReserveActivate (driver) | ReserveActivateEvent | `1488` | `1491` | `DRIVER(dctx)` | PASS |
| SeatFullRangeExhaust (in-dispatch) | FullRangeExhaustEvent | `1508` | `1511` | `ordinary_dispatch_origin(EQ)` | PASS |
| StartWake | WakeCompleteEvent | `2443` | `2446` | `wake_origin` = `ORDINARY_DISPATCH` or `POST_EPILOGUE(pctx)` (set at `2435`/`2438`) | PASS |
| SetupRetry (participant setup, in-dispatch) | SetupRetryEvent | `3108` | `3114` | `ordinary_dispatch_origin(EQ)` | PASS |
| HashWorkEvent seat (in-dispatch) | HashWorkEvent | `3741` | `3745` | `ordinary_dispatch_origin(EQ)` | PASS |
| RecoveryDeadline seat (epilogue) | RecoveryDeadlineEvent | `4300` | `4305` | `POST_EPILOGUE(pctx)` | PASS |
| RecoveryCompletion seat (epilogue) | RecoveryCompletionDueEvent | `4553` | `4559` | `POST_EPILOGUE(pctx)` | PASS |
| RecoveryWork seat (epilogue) | RecoveryWorkDueEvent | `4714` | `4720` | `POST_EPILOGUE(pctx)` | PASS |
| RecoveryAssignmentContinuation seat (post-epilogue) | RecoveryAssignmentContinuationDueEvent | `5173` | `5179` | `POST_EPILOGUE(pctx)` | PASS |
| CertificateArrival seat (in-dispatch) | CertificateArrival | `6053` | `6057` | `ordinary_dispatch_origin(EQ)` | PASS |
| BlockAcceptancePoint seat (in-dispatch) | BlockAcceptancePoint | `6067` | `6071` | `ordinary_dispatch_origin(EQ)` | PASS |
| SeatAcceptanceBatchFinalize (in-dispatch) | AcceptanceBatchFinalize | `6196` | `6200` | `ordinary_dispatch_origin(EQ)` | PASS |
| ResumeFromPause seat (in-dispatch) | ResumeFromPause | `6252` | `6256` | `ordinary_dispatch_origin(EQ)` | PASS |
| SetupRetry (template refresh, in-dispatch) | SetupRetryEvent | `6806` | `6812` | `ordinary_dispatch_origin(EQ)` | PASS |

Coverage against the AH1 requirement:
- Driver seats (SeatNextRoundBootstrap, SeatMinerRegister, SeatReserveActivate) use `DRIVER(...)` — PASS.
- In-dispatch seats (SeatTemplateCommit, SeatPrepareParticipants, SeatFullRangeExhaust, SeatAcceptanceBatchFinalize, HashWorkEvent, CertificateArrival, BlockAcceptancePoint, ResumeFromPause, SetupRetry ×2) use `ordinary_dispatch_origin(EQ)` — PASS.
- StartWake uses `ORDINARY_DISPATCH` or `POST_EPILOGUE` — PASS.
- Recovery epilogue seats (RecoveryDeadlineEvent, RecoveryCompletionDueEvent, RecoveryWorkDueEvent, RecoveryAssignmentContinuationDueEvent) use `POST_EPILOGUE(pctx)` — PASS.

**No call site passes `post_epilogue_context =`** (exhaustive grep of `post_epilogue_context`
returns only `770` and `2479`, neither of which is a `CALL ScheduleEvent(...)` argument) — PASS.

**Check 3 verdict: PASS** (all call sites carry an explicit origin; no call site passes the
removed flag). See the Defect below for a stale PROSE reference to the removed flag name.

---

## Check 4 — No scheduling path reads ambient EQ.current_* outside an active ordinary dispatch

| # | Item verified | Evidence | Verdict |
|---|---------------|----------|---------|
| 4a | The ONLY sanctioned reader of `EQ.current_*` for scheduling is `ordinary_dispatch_origin(EQ)`, valid ONLY inside an active ordinary dispatch | `698-703`, `913-914` | PASS |
| 4b | DRIVER seats build `DriverSchedulingContext.source_event_time` from the request (`config.run_start_time` / `predecessor_terminal_time` / `requested_event_time`), NEVER `EQ.current_*` | SeatNextRoundBootstrap `1371-1376` (+ note `1368`); SeatMinerRegister `1457-1459` (+ note `1456`); SeatReserveActivate `1485-1487` (+ note `1484`) | PASS |
| 4c | POST_EPILOGUE seats build `pctx.source_event_time` from the drained epilogue `t` (or `dispatch_envelope.event_time`), NEVER `EQ.current_*` | `4298`, `4551`, `4712`, `5171` (+ notes `4295-4296`, `4548-4549`, `4709`) | PASS |
| 4d | Remaining `EQ.current_*` reads are confined to ProcessEventTime's own dispatch lifecycle (`305-349`), §0.7e prose, or in-dispatch seats whose PRECONDITIONS assert `EQ.current_*` is the live dispatched frame (e.g. `1393`, `1411`, `1503`; targets at `1400`, `1418`, `1509`; BlockAcceptancePoint source frame `6175-6179`) | grep of `EQ.current_` reviewed in full | PASS |

**Check 4 verdict: PASS.**

---

## Defect found — CORRECTED (folded back into the final tree)

| # | File:line | Defect | Severity | Status |
|---|-----------|--------|----------|--------|
| D1 | `STAGE_01_PROTOCOL_PSEUDOCODE.md` (StartWake `NOTE`) | The StartWake `NOTE` still stated "…and ScheduleEvent receives **post_epilogue_context** explicitly." This was a stale reference to the AG flag that AH1 REMOVED, contradicting StartWake's own code (`scheduling_origin = wake_origin`) and the `ScheduleEvent` signature ("This REPLACES the AG post_epilogue_context flag"). | Documentation defect (normative prose asserted a false interface fact) | **FIXED** — the NOTE now reads "ScheduleEvent receives scheduling_origin = POST_EPILOGUE(pctx) explicitly (AH1)". |

After the fold-back, the ONLY surviving occurrence of `post_epilogue_context` in the pseudocode is the ScheduleEvent
signature line that documents its REPLACEMENT (a negative/historical reference), which is correct.

---

## Overall verdict

**PASS (after fold-back correction of D1).**

Correction AH1 is structurally complete and correct in the `SchedulingOrigin` union
(§0.7e), the `DriverSchedulingContext` structure, the `ScheduleEvent`
contract, all 18 `CALL ScheduleEvent(...)` call sites (each carries an explicit
`scheduling_origin`), and the delta-cycle derivation (no scheduling path reads ambient
`EQ.current_*` outside an active ordinary dispatch). The one genuine defect found — a stale
`post_epilogue_context` reference in the StartWake `NOTE` — was FIXED in the final normative tree
(the NOTE now names `scheduling_origin = POST_EPILOGUE(pctx)`), so AH1 is complete with no surviving
positive residue of the removed AG flag. PoCol, "the idle policy within PoCol", and the A1 baseline
**8.420833333 kWh** are unchanged.
