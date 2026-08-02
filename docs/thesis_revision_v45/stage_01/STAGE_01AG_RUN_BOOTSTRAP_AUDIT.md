# STAGE 1AG — Run-Bootstrap Audit (Correction AG3)

**Scope.** Formal-spec verification that the run-level bootstrap of the discrete-event
protocol is free of a circular RoundContext dependency: the run driver holds only the
`RunContext`, the first `RoundInitialiseEvent` is seatable and dispatchable while
`current_round_context = null`, and the round-creating event publishes the first
`RoundContext` rather than requiring one to exist.

**Subject.** The FINAL normative tree in `STAGE_01_PROTOCOL_PSEUDOCODE.md` (this stage
directory). All line anchors below reference that file.

## Intro

This stage formalises the **idle policy within PoCol**. The algorithm name is **PoCol**
throughout; the idle mechanism is described only as *"the idle policy within PoCol"* — no
renamed or energy-branded variant is introduced. Correction AG3 is a *structural* revision
of the run/round bootstrap contract (RunContext-owned round resolution, null-tolerant
seating); it touches control-flow ownership only and introduces **no numeric parameter
change**. The **A1 baseline of 8.420833333 kWh** (141 TH/s, 21.5 J/TH, 3031.5 W, 10,000 s)
is therefore **preserved unchanged**; any energy reduction remains attributed solely to
reduced active power-time (idle policy / reserve / reduced participation), not to any
bootstrap edit audited here.

## Verification results

| # | Claim under audit | Primary anchors (`STAGE_01_PROTOCOL_PSEUDOCODE.md`) | Verdict |
|---|-------------------|-----------------------------------------------------|:------:|
| 1 | `RunEventLoopToHorizon` INPUTS is `RunContext` (no retained `RoundContext`); calls `SeatNextRoundBootstrap(RunContext)` before the loop; passes `RunContext` to `ProcessEventTime`. | L474–L477 (signature + "holds ONLY the RunContext … never retains a RoundContext argument"); L484 (seat before loop); L489 (loop); L492, L498 (RunContext → ProcessEventTime) | **PASS** |
| 2 | `ProcessEventTime` INPUTS is `RunContext` (not `RoundContext`); resolves `dispatch_round_context <- RunContext.current_round_context` per event. | L252–L253 (signature); L255–L258 ("receives the RUN context (NOT a RoundContext)"); L303 (per-dispatch resolve, inside the WHILE at L283) | **PASS** |
| 3 | `RoundInitialiseEvent`'s descriptor injects `RunContext` (not `RoundContext`), is dispatchable while `current_round_context = null`, and publishes `RunContext.current_round_context <- rc`. | L1008 (recv env=no, recv ref=no); L1039 & L1066 (`runtime_injected: RunContext -> RunContext`; inputs `{RunContext, round_setup_seq}`); L228 (`CASE RunContext … RoundInitialiseEvent only`); L302 & L313–L316 (not blocked by the null-RoundContext guard); L1118 (publish `<- rc`) | **PASS** |
| 4 | `RunInitialise` returns `RunContext` with `current_round_context = null`; the first `RoundInitialiseEvent` bootstraps with no pre-existing `RoundContext` (no circular dependency). | L2422, L2447 (`INITIALISE current_round_context <- null`), L2459 (RETURNS it); L478–L480 (run-driver precondition restates null); L1205–L1206 (seat needs no RoundContext); L1116–L1118 (round is created/published, not required) | **PASS** |
| 5 | `ScheduleEvent` tolerates `RoundContext = null` for the bootstrap seat — PRECONDITIONS note present AND body has no `RoundContext.<field>` dereference. | L681–L684 (note: "MAY be null … NEVER dereferences RoundContext on any path"); body L690–L769 has zero `RoundContext.<field>` reads (ordering derived from EQ only, L709–L716, L769); L1214 (seat passes possibly-null RoundContext) | **PASS** |

## Item detail

### 1 — RunEventLoopToHorizon: RunContext-only driver

`PROCEDURE RunEventLoopToHorizon` (L474) declares `INPUTS: RunContext` (L475). The
in-spec comment L476–L477 is explicit: *"the run driver holds ONLY the RunContext. It
never retains a RoundContext argument; every RoundContext is resolved from
`RunContext.current_round_context` at the point of use."* Before the event loop, the run
driver calls `SeatNextRoundBootstrap(RunContext)` (L484), so a `RoundInitialiseEvent`
exists on the queue prior to the `WHILE` at L489. Both dispatch calls pass the run context,
never a round context: `ProcessEventTime(RunContext, t, is_horizon = false)` (L492) and the
horizon-sentinel `ProcessEventTime(RunContext, T, is_horizon = true, …)` (L498). The
post-loop finaliser resolves the (now terminal) round from `RunContext.current_round_context`
(L504) rather than from a retained argument. **PASS.**

### 2 — ProcessEventTime: per-dispatch RoundContext resolution

`PROCEDURE ProcessEventTime` (L252) declares `INPUTS: RunContext, event_time t, …`
(L253); L255–L258 states it *"receives the RUN context (NOT a RoundContext)"* and that the
current RoundContext *"is re-resolved per dispatch."* Inside the per-event `WHILE` (L283),
after the atomic POP, the dispatcher executes
`SET dispatch_round_context <- RunContext.current_round_context` (L303) for each event, so a
round rotation is observed immediately and no stale RoundContext can be carried across
events. **PASS.**

### 3 — RoundInitialiseEvent: injects RunContext, dispatchable at null, publishes rc

The descriptor row (L1008) records `recv env = no, recv ref = no`, with `config`/`prior_state`
resolved from `RunContext`; the binding row (L1039) declares `runtime_injected:
RunContext -> RunContext`, and the handler-inputs row (L1066) is `{ RunContext,
round_setup_seq }` — i.e. `RunContext`, never `RoundContext`. `BuildHandlerInvocation`
confirms this with `CASE RunContext … # RoundInitialiseEvent only` (L228). The dispatch
guard at L316, `IF (RoundContext in d.runtime_injected) AND dispatch_round_context = null`,
therefore does **not** fire for this event, as its own comment states (L313–L315) and as
L302 confirms (*"RoundInitialiseEvent's descriptor injects RunContext (not RoundContext), so
it is legal here"*). The handler publishes the new round with
`SET RunContext.current_round_context <- rc` (L1118). **PASS.**

### 4 — RunInitialise: null current_round_context, no circular dependency

`PROCEDURE RunInitialise` (L2422) executes `INITIALISE current_round_context <- null`
(L2447) and returns it in the `RunContext` tuple (L2459); `prior_round_terminal_state` is
likewise `null` at run start (L2446). The run driver's precondition restates this
(*"RunInitialise has created RunContext with current_round_context = null"*, L478–L480).
`SeatNextRoundBootstrap`'s precondition (L1205–L1206) confirms *"current_round_context is
null (run start) … No RoundContext is required to seat the round-CREATING event."* The
first `RoundInitialiseEvent` then *creates* the round via `RoundInitialise` and publishes it
(L1116–L1118, with `prior_state` null per L1116). Creation precedes any consumer, so there
is no pre-existing-RoundContext requirement and no circular dependency. **PASS.**

### 5 — ScheduleEvent: null-tolerant bootstrap seat, no RoundContext dereference

The `ScheduleEvent` PRECONDITIONS note (L681–L684) states: *"RoundContext MAY be null for a
RoundInitialiseEvent bootstrap seat (SeatNextRoundBootstrap, before the first round exists).
… it NEVER dereferences RoundContext on any path, so a null RoundContext is safe for that
seat."* Body inspection confirms this: across the whole procedure (L675–L792) the only
occurrences of `RoundContext` are the INPUTS signature (L676) and that note (L681–L684) —
the executable body (L690–L769) contains **no** `RoundContext.<field>` read. Ordering and
`delta_cycle` are derived exclusively from `EQ.current_*` (L709–L716) and the descriptor-
derived tie key (L769); the seat is validated against the §0.7g descriptor + EQ only.
`SeatNextRoundBootstrap` correspondingly calls
`ScheduleEvent(EQ, RoundContext = RunContext.current_round_context, RoundInitialiseEvent, …)`
(L1214), passing the null value at run start with no ill effect. **PASS.**

## Overall verdict

**PASS (5 / 5).** The AG3 run-bootstrap contract is internally consistent and free of a
circular RoundContext dependency: the run driver and `ProcessEventTime` carry only the
`RunContext` and resolve the current round per dispatch; `RoundInitialiseEvent` injects
`RunContext`, is dispatchable while `current_round_context = null`, and publishes the first
`RoundContext`; `RunInitialise` seeds `current_round_context = null`; and `ScheduleEvent`
seats the bootstrap event without dereferencing `RoundContext`. No defect found. The PoCol
idle-policy specification and the A1 baseline of 8.420833333 kWh are unaffected.
