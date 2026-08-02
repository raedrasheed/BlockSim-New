# Stage 1AE — Truthful Fire-and-Forget Scheduling Results Audit (correction AE9)

This is a documentation-only audit of correction **AE9** — truthful fire-and-forget scheduling results — in the Stage-1
formal specification of **PoCol** and the idle policy within PoCol. It was generated AFTER the normative documents were
final (`STAGE_01_PROTOCOL_PSEUDOCODE.md` PROCEDURE `ScheduleNextHashWork`, its callers `StartHashing` and the
`HashWorkEvent` handler continuation, PROCEDURE `ScheduleEvent` RETURNS, and every for-effect `CALL ScheduleEvent(...)`
site; `STAGE_01_ROUND_STATE_MACHINE.md` §3.10i AE9; `STAGE_01AE_SEMANTIC_TEST_VECTORS.md` TV270) and modifies no
specification document — it only quotes the current lines of the frozen source of truth. The A1 baseline
`8.420833333 kWh` is unchanged, and the binding PoCol naming rule (the algorithm is **PoCol**; the mechanism under audit
is the idle policy within PoCol — never "PoCol-E"/"Energy-Aware PoCol"/"Enhanced PoCol") is preserved. Every claim below
is grounded in an actual quote from `STAGE_01_PROTOCOL_PSEUDOCODE.md` (the primary source) with an approximate line
anchor and is corroborated by TV270. AE9 is precisely the correction of the one gap the Stage-1AD result-union audit had
flagged: `ScheduleNextHashWork` formerly returned a bare `scheduled` (fire-and-forget); it is now a result-binding caller.

---

## AE9 checks

| Check | Result |
|---|---|
| **1. `ScheduleNextHashWork` CAPTURES the `ScheduleEvent` result and RETURNS `hash_work_seated(EventRef)` / `hash_work_not_seated(reason)` — its RETURNS is no longer a bare `scheduled`** | **PASS** — the body binds the result `SET r <- CALL ScheduleEvent(EQ, RoundContext, HashWorkEvent, ...)` (~L2823), then `IF r = scheduled(event_ref, record): RETURN hash_work_seated(event_ref)` (~L2827–L2828) and otherwise `RETURN hash_work_not_seated(r)` (~L2829); the declared `RETURNS: hash_work_seated(EventRef) \| hash_work_not_seated(reason)` (~L2830) contains NO `scheduled` variant. The intent is stated inline: `AE9: CAPTURE the ScheduleEvent result and REPORT it TRUTHFULLY — never return scheduled when the seat was rejected` (~L2819). Corroborated by TV270 ("`ScheduleNextHashWork` returns `hash_work_not_seated(post_horizon_event_rejected)` — NEVER `scheduled`"). |
| **2. It NEVER returns `scheduled` after `ScheduleEvent` returned `post_horizon_event_rejected` — any non-scheduled result maps to `hash_work_not_seated(reason)`** | **PASS** — only the exact `scheduled(event_ref, record)` match returns the seated form (~L2827–L2828); ANY other result flows to `RETURN hash_work_not_seated(r)` where `r` is the exact rejection, annotated `AE9: r is the exact ScheduleEvent rejection (e.g. post_horizon_event_rejected)` (~L2829). The only reachable rejection here is O2 post-horizon, per `The only reachable rejection here is post_horizon_event_rejected (O2: now + modeled_hash_step_time > T ends hashing at the horizon) ... but ANY non-scheduled result maps to hash_work_not_seated(reason)` (~L2820–L2822), against `ScheduleEvent`'s `RETURN post_horizon_event_rejected` on `target_event_time > EQ.run_horizon_T` (~L575–L577). Corroborated by TV270 (setup targets `now + modeled_hash_step_time > T`, expected `hash_work_not_seated(post_horizon_event_rejected)`). |
| **3. `StartHashing` binds the result and on `hash_work_not_seated` returns `hashing_not_started(reason)`** | **PASS** — `SET hw <- CALL ScheduleNextHashWork(RoundContext, MinerID, assignment, from_cursor = ...)` (~L2808) then `IF hw = hash_work_not_seated(reason): RETURN hashing_not_started(reason)` (~L2810–L2811); the declared `RETURNS: hashing_started \| hashing_not_started(reason)` (~L2812) carries the truthful negative disposition, annotated `AE9/O2: at the horizon — deterministic terminal, not an error` (~L2811) and `AE9: CAPTURE the result and report it truthfully` (~L2806). Corroborated by TV270 ("The caller (`StartHashing` / `HashWorkEvent`) reports the truthful continuation disposition (hashing ends at the horizon)"). |
| **4. The `HashWorkEvent` handler's continuation RETURNS the `ScheduleNextHashWork` result (`hash_work_seated` / `hash_work_not_seated`), never a bare `scheduled`** | **PASS** — the continuation is `RETURN CALL ScheduleNextHashWork(RoundContext, MinerID, assignment, from_cursor = cursor)` (~L2885); the handler's declared `RETURNS: hash_work_result (solution \| exhausted \| continued(hash_work_seated(EventRef) \| hash_work_not_seated(reason)) \| noop)` (~L2886) contains NO bare `scheduled`. Inline: `AE9: the continuation disposition IS the ScheduleNextHashWork result — hash_work_seated(EventRef) for a scheduled next unit, or hash_work_not_seated(post_horizon_event_rejected) ... It is never reported as a bare scheduled` (~L2882–L2884). Corroborated by TV270. |
| **5. Every remaining for-effect `CALL ScheduleEvent` caller either handles the result OR only a deterministic, provably-safe rejection is reachable** | **PASS** — a whole-document grep of `CALL ScheduleEvent` finds eleven call sites (the ~L427/~L431 hits are the `SCHEDULE`-shorthand definition and an authority note, not calls); ten bind the result to a variable that is then inspected (AD3 result-binding callers, already audited in Stage 1AD), leaving exactly ONE genuine for-effect caller: `HandlePropagationFailure`'s `ResumeFromPause` seat `CALL ScheduleEvent(EQ, RoundContext, ResumeFromPause, target_event_time = dispatch_envelope.event_time, target_microphase = RESUME, {M, trigger = failure_reason, pause_cause_candidate_id = CandidateID, pause_cause_propagation_id = PropagationID})` (~L5222), for which NO rejection variant is reachable (see the caller table). The RSM §3.10i statement matches: `Every remaining for-effect ScheduleEvent caller handles every reachable result or relies only on the deterministic O2 post-horizon rejection` (RSM ~L1078–L1079). Corroborated by TV270. |

---

## For-effect `CALL ScheduleEvent` caller audit

A grep of `CALL ScheduleEvent` yields eleven call sites. Ten are AD3 **result-binding** callers — the result is bound to
a variable that is then inspected — and were audited in Stage 1AD (`STAGE_01AD_SCHEDULE_RESULT_CONTRACT_AUDIT.md`): the
`WakeCompleteEvent` seat in `StartWake` (~L1682, `seat`); the two `SetupRetryEvent` seats in
`PrepareParticipantsForNewRound` (~L2212, `r`) and `ContinueTemplateRefreshAssignmentSetup` (~L5713, `r`); the
`RecoveryDeadlineEvent` seat in `SecurityFloorEvaluate` (~L3357, `r`, target capped at `min(..., run_horizon_T)`); the
`RecoveryCompletionDueEvent` seat in `SeatRecoveryCompletion` (~L3604, `result`); the `RecoveryWorkDueEvent` seat in
`SeatRecoveryWork` (~L3759, `result`); the `RecoveryAssignmentContinuationDueEvent` seat in `CompleteSecurityRecovery`
(~L4217, `r`); and the `CertificateArrival` / `BlockAcceptancePoint` seats in `ScheduleSolutionPropagation` (~L5097,
`r_sched`; ~L5110, `b_sched`). `ScheduleNextHashWork` (~L2823) — the AD3-era for-effect caller — now BINDS and inspects
`r` (Checks 1–2), so it has left the for-effect set. Exactly one genuine for-effect caller remains:

| For-effect `ScheduleEvent` caller (procedure, event, ~L) | Reachable results | Handled or provably-unreachable rejection |
|---|---|---|
| `HandlePropagationFailure` — `ResumeFromPause` (~L5222) | `scheduled(event_ref, record)` ONLY. `target_event_time = dispatch_envelope.event_time` is the CURRENT dispatched event_time `t` (the seat runs inside `AcceptanceBatchFinalize`, a dispatched handler that threads its own envelope, ~L5287/~L5309/~L5314). None of the four rejections is reachable: **finalised-time** — `t` is added to `finalised_event_times` only at the ProcessEventTime epilogue tail (`ADD t to finalised_event_times`, ~L304), AFTER the drain in which this handler runs, so `t not in finalised_event_times` here (guard ~L569); **post-horizon** — `t <= T` because no event beyond `T` is ever enqueued or dispatched (O2, guard ~L575); **backward-time** — `target = current`, not `< current` (guard ~L592–L593); **post-epilogue** — `post_epilogue_context` defaults to `null` (guard ~L581); **schema-mismatch** — `ResumeFromPause` is declared in §0.7g-schema with payload `MinerID, trigger, pause_cause_candidate_id, pause_cause_propagation_id` (~L814), matched exactly by the passed `{M, trigger, pause_cause_candidate_id, pause_cause_propagation_id}` (guard ~L603–L605). | **Provably safe (vacuous).** Since only `scheduled` is reachable, there is no rejection to report; dropping the (never-produced) rejection cannot mislead. This is stronger than "only O2 post-horizon reachable" — here NO rejection is reachable at all. The seated `ResumeFromPause` refs are later cancellable through the queue owner at round/candidate closure (AE1/AE2). |

---

## Result

**PASS on all five AE9 checks; no FAIL.** `ScheduleNextHashWork` captures the `ScheduleEvent` result and returns
`hash_work_seated(EventRef)` / `hash_work_not_seated(reason)` (~L2823–L2830), mapping the O2 `post_horizon_event_rejected`
to `hash_work_not_seated(r)` and never returning a bare `scheduled` after a rejection (Checks 1–2). `StartHashing` binds
the result and returns `hashing_not_started(reason)` on `hash_work_not_seated` (~L2808–L2812, Check 3); the `HashWorkEvent`
continuation returns the `ScheduleNextHashWork` result, and its declared `RETURNS` union carries only
`continued(hash_work_seated(EventRef) | hash_work_not_seated(reason))` with no bare `scheduled` (~L2885–L2886, Check 4). Of
the eleven `CALL ScheduleEvent` sites, ten are AD3 result-binding callers (already audited in Stage 1AD) and exactly one is
genuinely for-effect — `HandlePropagationFailure`'s `ResumeFromPause` seat (~L5222) — for which no rejection variant is
reachable (current, non-finalised, in-horizon, same-time, in-schema seat), so its fire-and-forget disposition is vacuously
safe (Check 5). No caller reports `scheduled` after a rejection, and no unhandled reachable non-post-horizon rejection was
found. All findings agree with RSM §3.10i AE9 (~L1076–L1079) and TV270.
