# Stage 1T — Continuation-Epilogue Two-Step Contract and Post-Epilogue Causality Audit (T1/T7)

This is a documentation-only paper audit of two Stage-1T corrections as edited in
`docs/thesis_revision_v45/stage_01/STAGE_01_PROTOCOL_PSEUDOCODE.md`: **T1 — the branch-C
recovery continuation is a TWO-STEP contract** (a queued
`RecoveryAssignmentContinuationDueEvent` that ONLY records the continuation-due fact and
refreshes the census, plus the POST-epilogue hook
`ApplyRecoveryAssignmentContinuationAfterEpilogue` that is the ONLY place branch-C
`RESTORED` is applied) and **T7 — post-epilogue causality** (the continuation application
runs strictly after the epilogue, seats every `StartWake`/re-arm at a STRICTLY LATER
`event_time`, and leaves nothing due at `t` before `ProcessEventTime` finalises `t`). The
consensus algorithm is named **PoCol**; **the idle policy within PoCol** is referenced here
as a mechanism only, and this audit claims no energy, security, or fairness property of the
idle policy within PoCol. T1 and T7 are control-flow, lifecycle, and provenance corrections
to the deferred branch-C recovery continuation; they never change how time or energy is
counted — the census refreshes involved re-stamp provenance over the same `H_*` values and
mint no accounting quantity. The **A1 accepted accounting baseline of 8.420833333 kWh is
UNCHANGED** — no census value, residency interval, transition-energy term, or accounting
quantity is edited. This is documentation only: no new consensus feature is introduced.
Every claim below is checked by procedure-call-graph and control-flow reasoning over the
EXACT named procedures in the pseudocode as edited; no behavior is inferred beyond the text.

## 1. The canonical event-time tail and the two-step continuation contract (§0.7d / §10a)

`ProcessEventTime` (§0.7d) drives every `event_time`: it drains `t` to quiescence, then runs
ONE canonical event-time tail (R2) in a fixed order (lines 261–264):

1. `FinalizeEventTimeSecurityCensus(t)` — the ONE (unconditional) security-floor epilogue for
   `t` (line 261).
2. `ApplyRecoveryCompletionAfterEpilogue(t)` — the post-epilogue COMPLETION application (line 262).
3. `ApplyRecoveryAssignmentContinuationAfterEpilogue(t)` — the post-epilogue branch-C
   CONTINUATION application, "mutually exclusive with the above" for one episode at one
   `event_time` (line 263).
4. `FinalizePostRecoveryApplicationState(t)` — the single post-application settlement, NOT a
   second floor decision (line 264).

Under T1 the branch-C continuation mirrors the completion two-step. Just as the completion
splits into a queued `RecoveryCompletionDueEvent` (records the due fact + refreshes the
census, NO transition, §10a `PROCEDURE` line 2504) and the post-epilogue hook
`ApplyRecoveryCompletionAfterEpilogue` (the ONLY place a completion outcome is applied,
`PROCEDURE` line 2534), the continuation splits into the queued
`RecoveryAssignmentContinuationDueEvent` (`PROCEDURE` line 2704) and the post-epilogue hook
`ApplyRecoveryAssignmentContinuationAfterEpilogue` (`PROCEDURE` line 2741). The §10a header
NOTE states this directly (lines 2448–2457): branch-C seating "RECORDS the continuation DUE
fact and refreshes the census (NO transition / NO assignment install / NO APPLIED)", and the
post-epilogue hook "is the ONLY place branch-C RESTORED is APPLIED", so "no branch-C RESTORED
is ever applied during the ordinary event drain".

The §0.7g microphase mapping row registers `RecoveryAssignmentContinuationDueEvent` at
microphase `RECOVERY_ASSIGNMENT_CONTINUATION_DUE` (13d) with the explicit qualifier "records
the continuation DUE fact + refreshes the census; NO transition / NO assignment install / NO
APPLIED" (line 506). The §0.7g-driver seating row seats it through `ScheduleEvent` with tie
key `(RoundID, RecoveryEpisodeID, RecoveryDecisionID, ContinuationGeneration)`, "may create
same-time delta-cycle events? no", carrying "the full recovery identity + `ContinuationGeneration`",
"seated via the S7 PostEpilogueSchedulingContext (strictly-later)" (line 551).

## 2. T1(a)/(b) — the Due event applies nothing; the sole application site is the post-epilogue hook

**Seat (branch C of `CompleteSecurityRecovery`, §10a `PROCEDURE` line 2617).** `CompleteSecurityRecovery`
is the INTERNAL branch dispatch called ONLY by `ApplyRecoveryCompletionAfterEpilogue` after the
decision is marked `APPLYING` (lines 2617–2622). Branch C — the `ELSE` arm, "range
redistribution or reserve assignment is required" (lines 2654–2693) — performs NO `round_state`
mutation and only seats the Due event, in canonical order:

1. `t_cont <- next_representable_simulation_time(dispatch_envelope.event_time)` (line 2662) — a
   STRICTLY LATER `event_time` than the drained application `t` (R1).
2. validate `t_cont <= run_horizon_T` (line 2663); if `t_cont > T`, record
   `recovery_continuation_horizon_deferred` and `RETURN recovery_branch_result(kind = FAILED,
   reason = horizon_deferred)` (lines 2664–2665) — round STAYS `SECURITY_RECOVERY`.
3. mint the T2 continuation identity (`continuation_generation <- 1`, `continuation_id`,
   `continuation_bound_census_version`, lines 2670–2672).
4. seat ONE `RecoveryAssignmentContinuationDueEvent` through the S7 `PostEpilogueSchedulingContext`
   at `target_event_time = t_cont`, carrying the full recovery identity + `ContinuationGeneration = 1`
   (lines 2676–2684); only on `r = scheduled(...)` store `continuation_event_ref` and
   `RETURN recovery_branch_result(kind = DEFERRED, ...)` (lines 2685–2690); a rejected seat returns
   `kind = FAILED, reason = continuation_not_seated` (lines 2691–2693).

The caller's `DEFERRED` arm (`ApplyRecoveryCompletionAfterEpilogue` lines 2584–2590) leaves the
decision `APPLYING`, does NOT set `recovery_outcome_finalised`, does NOT clear
`current_recovery_episode`, keeps the decision in `pending_recovery_decisions`, and keeps the
round `SECURITY_RECOVERY`. So seating records no branch-C `RESTORED` result.

**Due (`RecoveryAssignmentContinuationDueEvent`, §10a `PROCEDURE` line 2704).** When the queued
Due event is dispatched at `t_cont` during the ordinary drain, it applies nothing. After its T1/T2
stale + identity guard (`round_state != SECURITY_RECOVERY` OR wrong episode OR decision not in
`pending` OR `D.status != APPLYING` OR `ContinuationGeneration != D.continuation_generation` OR
`recovery_outcome_finalised` set OR round/template/state-version mismatch →
`recovery_continuation_due_stale_noop`, lines 2718–2726) it does EXACTLY two things:

- records the due fact — `continuation_due_at_event_time <- dispatch_envelope.event_time` and
  `continuation_due_dispatch_envelope <- dispatch_envelope` (lines 2728–2729); and
- refreshes the census — `CaptureSecurityCensusOnRecoveryDeadline(RoundContext,
  dispatch_envelope.event_time, census_source = RECOVERY_COMPLETION_DUE)` (lines 2732–2733).

Its own comment is explicit: it "performs NO round-state transition, creates NO assignment, and
does NOT mark the decision APPLIED (T1 — no branch-C RESTORED result during the ordinary-event
drain)" (lines 2713–2717), and its NOTE repeats that "It NEVER applies branch C" and the
application "is `ApplyRecoveryAssignmentContinuationAfterEpilogue`, run AFTER this event_time's
epilogue" (lines 2736–2739). This establishes **T1(a): the Due event applies nothing.**

**Apply (`ApplyRecoveryAssignmentContinuationAfterEpilogue`, §10a `PROCEDURE` line 2741).** This
post-epilogue hook is the SOLE site of branch-C `RESTORED`. It locates the decision whose
`continuation_due_at_event_time = t` (lines 2753–2757), re-checks the T2 freshness + version
binding (`D.continuation_bound_census_version` compared to `census.RecoveryCensusVersion`, lines
2762–2767), and only on the redistribution-only path transitions `SECURITY_RECOVERY -> ASSIGNMENT`
(line 2772), installs the disjoint set (lines 2776–2780), reaches `HASHING` via
`CompleteAssignmentPhase` (line 2792), and only THEN marks the decision `APPLIED`, sets
`recovery_outcome_finalised[episode] <- RESTORED`, and clears `current_recovery_episode` (lines
2793–2800) — "This is the moment branch-C RESTORED is actually applied" (line 2794). The §0.8
`recovery_outcome_finalised` register confirms it is set "ONLY when an outcome is ACTUALLY APPLIED:
by `ApplyRecoveryCompletionAfterEpilogue` (branches A/B/D), or by
`ApplyRecoveryAssignmentContinuationAfterEpilogue` when branch C reaches HASHING (RESTORED)"
(lines 662–665), and the hook's NOTE names it "the ONLY place branch-C RESTORED is APPLIED, run
POST-epilogue so NO RESTORED result is recorded during the ordinary-event drain (T1)" (lines
2835–2843). This establishes **T1(b): the sole application site is the post-epilogue hook.**

## 3. T1(c) — canonical tail ordering and mutual exclusion; no branch-C RESTORED during the ordinary drain

**Ordering.** `ProcessEventTime` runs `ApplyRecoveryCompletionAfterEpilogue(t)` (line 262) BEFORE
`ApplyRecoveryAssignmentContinuationAfterEpilogue(t)` (line 263), both AFTER the single epilogue
`FinalizeEventTimeSecurityCensus(t)` (line 261) and BEFORE the settlement
`FinalizePostRecoveryApplicationState(t)` (line 264). The continuation hook's PRECONDITIONS state
it is "invoked by ProcessEventTime AFTER FinalizeEventTimeSecurityCensus(t) AND
ApplyRecoveryCompletionAfterEpilogue(t) (the T1 canonical tail)" (lines 2743–2744).

**Mutual exclusion.** For one `RecoveryEpisodeID` at one `event_time` AT MOST ONE of the two hooks
applies (lines 2745–2747). If the completion hook applies a branch-A/B/D `SUCCESS`, it clears the
episode — `SET current_recovery_episode <- null` (`ApplyRecoveryCompletionAfterEpilogue` line
2582) — so the continuation hook's first guard `IF current_recovery_episode = null: RETURN
nothing_due` fires (lines 2749) and it applies nothing. If instead the completion hook takes the
branch-C `DEFERRED` arm, it does NOT apply `RESTORED` (§2 above) and the continuation hook at that
same `event_time` finds no decision with `continuation_due_at_event_time = t` (the Due event is
seated at the strictly-later `t_cont`, not yet dispatched), so it returns `nothing_applicable_due(t)`
(lines 2754–2756). Either way, a completion applied at `t` clears the episode and the continuation
hook then finds nothing due.

**No branch-C RESTORED during the ordinary drain.** The ordinary drain dispatches only queued
events; the two events on the branch-C timeline that it dispatches —
`RecoveryCompletionDueEvent` and `RecoveryAssignmentContinuationDueEvent` — each RECORD-and-refresh
only and apply nothing (lines 2504–2532 and 2704–2739; §0.7g lines 508–518). Both applications are
post-epilogue hooks run by `ProcessEventTime` only after `t` is quiescent and the epilogue has run
(§0.7g-driver run-level-hook list lines 554–562). It follows that **no branch-C RESTORED result is
ever applied during the ordinary-event drain.**

## 4. T7 — post-epilogue causality: strictly-later scheduling and the two ProcessEventTime assertions

The continuation application runs strictly after the epilogue, and every event it seats is placed at
a STRICTLY LATER `event_time` through the S7 `PostEpilogueSchedulingContext`:

- The branch-C seat targets `t_cont = next_representable_simulation_time(t)` and passes
  `post_epilogue_context = pctx` (`CompleteSecurityRecovery` lines 2662, 2676–2684).
- The redistribution-only install builds a `PostEpilogueSchedulingContext` so "any `StartWake` seats
  its `WakeCompleteEvent` STRICTLY LATER through the post-epilogue context (never at `t`)"
  (`ApplyRecoveryAssignmentContinuationAfterEpilogue` lines 2776–2780).
- The T6-B reserve-dependent path activates the reserve (whose `StartWake` seats its
  `WakeCompleteEvent` strictly later, line 2820) and re-arms a strictly-later
  `RecoveryAssignmentContinuationDueEvent` at `t_rearm = next_representable_simulation_time(t)` with a
  fresh continuation generation, again through `pctx` (lines 2818–2830).

`ScheduleEvent` makes strictly-later placement structural: a call carrying a
`post_epilogue_context` is rejected unless `target_event_time > post_epilogue_context.source_event_time`
(`rejected_post_epilogue_not_strictly_later`) and derives `delta_cycle = 0` at that future time
(`ScheduleEvent` lines 434–440; `STRUCTURE PostEpilogueSchedulingContext` lines 399–410). So a
post-epilogue caller can NEVER enqueue at the drained `source_event_time`.

`ProcessEventTime` then asserts, before finalising `t`, the two conditions T7 relies on:

- `ASSERT no ordinary event remains with event_time = t` — "the post-epilogue application enqueued
  NOTHING at t (T7: incl. StartWake/re-arm strictly later)" (line 267); and
- `ASSERT no recovery-continuation application remains due at t` —
  "`ApplyRecoveryAssignmentContinuationAfterEpilogue` applied or re-armed strictly later; none left
  due at t" (line 269).

(The intervening `ASSERT security_census_dirty[t] = false`, line 268, is the R2 settlement assertion;
it confirms `FinalizePostRecoveryApplicationState` settled `t` without a second floor decision.) This
establishes **T7: the continuation application runs strictly after the epilogue, seats every
re-arm/`StartWake` strictly later, and leaves nothing due at `t`.**

## 5. Checks

| # | Check | Result | Citation (exact procedure + lines) |
|---|-------|:------:|------------------------------------|
| 1 | The Due event performs NO round-state transition, creates NO assignment, and never marks APPLIED — it records only the due fact and refreshes the census | PASS | `RecoveryAssignmentContinuationDueEvent` (§10a line 2704): records `continuation_due_at_event_time`/`continuation_due_dispatch_envelope` (lines 2728–2729), `CaptureSecurityCensusOnRecoveryDeadline(..., census_source = RECOVERY_COMPLETION_DUE)` (lines 2732–2733); comment lines 2713–2717; NOTE lines 2736–2739 |
| 2 | Branch C seats the Due event and returns `DEFERRED` without mutating `round_state` (seating is not applying) | PASS | `CompleteSecurityRecovery` branch C (§10a lines 2654–2693): `t_cont` (2662) → validate `<= T` (2663) → mint T2 identity (2670–2672) → seat via `PostEpilogueSchedulingContext` (2676–2684) → `DEFERRED` (2690); caller `DEFERRED` arm `ApplyRecoveryCompletionAfterEpilogue` lines 2584–2590 |
| 3 | The SOLE site that applies branch-C RESTORED is the post-epilogue hook | PASS | `ApplyRecoveryAssignmentContinuationAfterEpilogue` (§10a line 2741): APPLIED + `recovery_outcome_finalised[episode] <- RESTORED` at HASHING (lines 2795–2799); §0.8 `recovery_outcome_finalised` lines 662–665; NOTE lines 2835–2843 |
| 4 | `ProcessEventTime` canonical tail runs the four steps in the fixed order | PASS | `ProcessEventTime` lines 261–264 |
| 5 | T1 mutual exclusion: at most one of the completion hook and the continuation hook applies per episode per event_time | PASS | completion SUCCESS clears the episode (`ApplyRecoveryCompletionAfterEpilogue` line 2582); continuation hook then returns `nothing_due` (`ApplyRecoveryAssignmentContinuationAfterEpilogue` PRECONDITIONS 2745–2747, guard line 2749) |
| 6 | No branch-C RESTORED result is recorded during the ordinary-event drain | PASS | both applications are POST-epilogue run-level hooks (§0.7g lines 508–518; §0.7g-driver lines 554–562); Due-event NOTE lines 2736–2739; hook NOTE lines 2835–2843 |
| 7 | Every `StartWake` / re-arm the continuation seats is placed at a STRICTLY LATER `event_time` through `PostEpilogueSchedulingContext` | PASS | seat lines 2676–2684; install `pctx` lines 2776–2780; T6-B re-arm lines 2818–2830; `ScheduleEvent` S7 rule lines 434–440; `STRUCTURE PostEpilogueSchedulingContext` lines 399–410 |
| 8 | `ProcessEventTime` asserts nothing remains at `t` before finalising it (the two T7 assertions) | PASS | `ProcessEventTime` line 267 (no ordinary event at `t`) and line 269 (no recovery-continuation application due at `t`) |

## 6. Result

Under T1, the branch-C recovery continuation is a two-step contract. Step 1 is the queued
`RecoveryAssignmentContinuationDueEvent` (§10a, `PROCEDURE` line 2704), which — seated by
`CompleteSecurityRecovery` branch C through the S7 `PostEpilogueSchedulingContext` at the
strictly-later `t_cont` (lines 2662, 2676–2684) — RECORDS only `continuation_due_at_event_time`
and `continuation_due_dispatch_envelope` and refreshes the census via
`CaptureSecurityCensusOnRecoveryDeadline(..., census_source = RECOVERY_COMPLETION_DUE)` (lines
2728–2733), performing no round-state transition, creating no assignment, and never marking the
decision APPLIED. Step 2 is the post-epilogue hook
`ApplyRecoveryAssignmentContinuationAfterEpilogue` (§10a, `PROCEDURE` line 2741), the ONLY place
branch-C `RESTORED` is applied — at `HASHING`, after the `SECURITY_RECOVERY -> ASSIGNMENT`
transition, the disjoint install, and `CompleteAssignmentPhase` (lines 2772–2800). `ProcessEventTime`
runs the completion hook (line 262) before the continuation hook (line 263), and the two are
mutually exclusive for one episode at one `event_time`: a completion applied at `t` clears the
episode, so the continuation hook then finds nothing due (lines 2582, 2745–2749). Consequently no
branch-C `RESTORED` result is ever applied during the ordinary-event drain. Under T7, the
continuation application runs strictly after the epilogue and places every `StartWake` and re-arm
at a strictly-later `event_time` through `PostEpilogueSchedulingContext` (lines 2676–2684,
2776–2780, 2818–2830; `ScheduleEvent` lines 434–440), and `ProcessEventTime` asserts both that no
ordinary event remains at `t` (line 267) and that no recovery-continuation application remains due
at `t` (line 269) before finalising `t`. All of T1 and T7 operate purely on the deferred branch-C
continuation's control flow, lifecycle, and provenance; no census value, residency interval, or
transition-energy term is edited, the census refreshes only re-stamp provenance over the same
`H_*` values, the A1 accepted baseline of 8.420833333 kWh is unchanged, and no new consensus
feature is introduced.

The prohibited rebranded-algorithm-name variants are not used anywhere in this document.
