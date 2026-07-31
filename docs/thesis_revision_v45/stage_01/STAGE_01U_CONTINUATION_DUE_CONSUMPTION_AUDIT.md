# Stage 1U — Explicit Continuation-Due-Fact Consumption Audit (U4)

This is a documentation-only paper audit of one Stage-1U correction as edited in
`docs/thesis_revision_v45/stage_01/STAGE_01_PROTOCOL_PSEUDOCODE.md`: **U4 — the branch-C
continuation-due fact (and every recovery-work due fact) is EXPLICITLY consumed.** Before U4 a
"still due at `t`" condition could be read off a timestamp field; under U4 the due fact is a
first-class lifecycle value `CONTINUATION_DUE_STATUS in { NOT_DUE, DUE, CONSUMED, SUPERSEDED,
CANCELLED }` carried on the continuation record and on every recovery-work record, the Due events
set it to `DUE`, the post-epilogue hooks ATOMICALLY consume it before returning, and
`ProcessEventTime`'s finalisation assertion checks the EXPLICIT status — never a timestamp field
that merely equals `t`. The consensus algorithm is named **PoCol**; **the idle policy within PoCol**
is referenced here as a mechanism only, and this audit claims no energy, security, or fairness
property of the idle policy within PoCol. U4 is a lifecycle and assertion-integrity correction to
the deferred branch-C continuation and to recovery work: it changes only how a "due" fact is
represented and retired, never how time or energy is counted — no census value, residency interval,
transition-energy term, or accounting quantity is edited, and the census refreshes involved re-stamp
provenance over the same `H_*` values and mint no accounting quantity. The **A1 accepted accounting
baseline of 8.420833333 kWh is UNCHANGED.** This is documentation only: no new consensus feature is
introduced. Every claim below is checked by control-flow and lifecycle reasoning over the EXACT named
procedures in the pseudocode as edited; no behaviour is inferred beyond the text.

## 1. The explicit `CONTINUATION_DUE_STATUS` lifecycle (§0.8)

§0.8 declares the due fact as an enumerated lifecycle, not a derived predicate. The register states
`CONTINUATION_DUE_STATUS in { NOT_DUE, DUE, CONSUMED, SUPERSEDED, CANCELLED }` (line 731), and its
U4 gloss is explicit (lines 732–736): "The branch-C continuation record
(`recovery_decisions[decision_id]`) and every recovery-work record carry a
`continuation_due_status` / `due_status`. `RecoveryAssignmentContinuationDueEvent` (and
`RecoveryWorkDueEvent`) set it to `DUE`; the post-epilogue hook ATOMICALLY consumes it (`CONSUMED`
on apply/re-arm, `SUPERSEDED` on a stale-noop, `CANCELLED` on terminal closure) BEFORE returning.
`ProcessEventTime`'s final assertion checks the EXPLICIT status, never a timestamp field that merely
equals `t`. (`decision_record` gains a `continuation_due_status` field.)"

The status is a genuine field on both records:

- **Continuation record.** The `recovery_decisions` map holds `decision_record { … ,
  continuation_due_at_event_time, continuation_due_dispatch_envelope, continuation_due_status
  (CONTINUATION_DUE_STATUS, U4), continuation_status (…, U3) }` (§0.8 lines 644–649). The status
  (`continuation_due_status`) is thus DISTINCT from the timestamp (`continuation_due_at_event_time`)
  and from the stashed envelope (`continuation_due_dispatch_envelope`): the "is it due?" question is
  answered by the explicit enum, and the timestamp only records WHEN the DUE status was written.
- **Recovery-work record.** The `recovery_work` map holds `work_record { … , status
  (RECOVERY_WORK_STATUS), work_due_event_ref, due_at_event_time, due_dispatch_envelope, due_status
  (CONTINUATION_DUE_STATUS) }` (§0.8 lines 721–724), so a work action "is an explicit identity with a
  lifecycle" (line 725). Its `due_status` reuses the same `CONTINUATION_DUE_STATUS` enum; its coarse
  `status` field ranges over `RECOVERY_WORK_STATUS in { CREATED, ARMED, DUE, CONSUMED, SUPERSEDED,
  CANCELLED, SCHEDULE_FAILED }` (line 728).

The initial value is the non-due sentinel: `SeatRecoveryWork` (§ `PROCEDURE` line 2537) publishes a
freshly seated work record with `due_status = NOT_DUE` (line 2571), so a work action is `NOT_DUE`
from the moment it is armed until its Due event fires.

## 2. The Due events set `DUE` (and apply nothing)

**Continuation Due event.** `RecoveryAssignmentContinuationDueEvent` (§ `PROCEDURE` line 2998, "T1
step 1: records the continuation DUE + refreshes census; NO application") is dispatched from the
queue at the strictly-later `t_cont`. After its T1/T2/U4 stale + identity guard (`round_state !=
SECURITY_RECOVERY` OR wrong episode OR decision not in `pending` OR `D.status != APPLYING` OR
`ContinuationGeneration != D.continuation_generation` OR `recovery_outcome_finalised` set OR
round/template/state-version mismatch → `recovery_continuation_due_stale_noop`, lines 3014–3022) it
does exactly three things and NO application: it sets the explicit status
`SET recovery_decisions[RecoveryDecisionID].continuation_due_status <- DUE` (line 3025, "# U4"),
records the timestamp `continuation_due_at_event_time <- dispatch_envelope.event_time` (line 3026),
stashes `continuation_due_dispatch_envelope` for the post-epilogue apply (line 3027), and refreshes
the census via `CaptureSecurityCensusOnRecoveryDeadline(…, census_source = RECOVERY_CONTINUATION_DUE)`
(lines 3031–3032). Its comment is explicit that it records only the due fact "(continuation_due_status
= DUE)" and "does NOT mark the decision APPLIED" (lines 3009–3013), and its NOTE names the application
as `ApplyRecoveryAssignmentContinuationAfterEpilogue`, "run AFTER this event_time's epilogue" (lines
3035–3038). The DUE fact stashes the envelope precisely so the later hook "will EXPLICITLY consume
this due status" (line 3024).

**Recovery-work Due event.** `RecoveryWorkDueEvent` (§ `PROCEDURE` line 2589, "U1/U4: records the
work DUE fact + refreshes census; NO work here") mirrors the pattern. After its U1/U3/U4 stale +
identity guard (`round_state != SECURITY_RECOVERY` OR wrong episode OR
`pending_recovery_work[episode] != RecoveryWorkID` OR `W.status != ARMED` OR wrong generation OR
outcome finalised OR round/template/state-version mismatch → `recovery_work_due_stale_noop`, lines
2599–2607) it sets both fields — `SET recovery_work[RecoveryWorkID].status <- DUE` (line 2609) and
`SET recovery_work[RecoveryWorkID].due_status <- DUE` (line 2610, "# U4") — records
`due_at_event_time <- dispatch_envelope.event_time` (line 2611), stashes `due_dispatch_envelope`
(line 2612), and refreshes the census via `CaptureSecurityCensusOnRecoveryDeadline(…, census_source =
RECOVERY_WORK_DUE)` (lines 2615–2616). Its NOTE states it "records the due fact (due_status = DUE) and
refreshes the census. The WORK is `ApplyRecoveryWorkAfterEpilogue`, run AFTER this event_time's
epilogue" (lines 2619–2621). So both Due events only WRITE `DUE`; neither consumes it and neither
applies anything.

## 3. The post-epilogue hooks atomically consume `DUE` before returning

Each post-epilogue hook locates the decision/work whose EXPLICIT status is `DUE` at `t`, and on
EVERY return path writes exactly one of `CONSUMED` / `SUPERSEDED` / `CANCELLED` to that status
before it returns. No path returns while leaving the status at `DUE`.

### 3.1 `ApplyRecoveryAssignmentContinuationAfterEpilogue` (§ `PROCEDURE` line 3040)

The hook locates the target by the EXPLICIT status, not by a bare timestamp: "IF NO decision_id in
`pending_recovery_decisions[episode]` WITH `recovery_decisions[decision_id].continuation_due_status
= DUE` AND `recovery_decisions[decision_id].continuation_due_at_event_time = t`: RETURN
`nothing_applicable_due(t)`" (lines 3055–3058). The status is the primary predicate; the timestamp is
an AND-conjunct that pins the DUE fact to this `event_time`. Every subsequent exit consumes the DUE
status:

| Transition (branch-C path) | Guard / trigger | Status written | Code path (exact lines) |
|---|---|:--:|---|
| Stale / superseded / census no longer warrants RESTORED | `round_state != SECURITY_RECOVERY` OR `D.status != APPLYING` OR `D.continuation_bound_census_version != census.RecoveryCensusVersion` OR `NOT outcome_consistent_with_census(RESTORED, census)` (3064–3067) | `SUPERSEDED` | line 3069 `SET … continuation_due_status <- SUPERSEDED`; RETURN `recovery_continuation_apply_stale` (3071) |
| Plan invalid (compute-only; NO mutation) | `plan = plan_invalid(reason)` (3077) | `CONSUMED` | line 3079 `SET … continuation_due_status <- CONSUMED`; `SetRecoveryDecisionStatus(…, APPLY_FAILED)` (3080); episode preserved (3083) |
| Install failed BEFORE mutation (reversible; roll back the state transition) | `commit = install_failed_before_mutation` (3091) | `CONSUMED` | line 3095 `CONSUMED` after `TRANSITION -> SECURITY_RECOVERY` (3093); `APPLY_FAILED` (3096) |
| Install failed AFTER mutation, rollback COMPLETE | `commit = install_failed_after_mutation` then `rb = rollback_completed` (3099–3101) | `CONSUMED` | line 3104 `CONSUMED` after `TRANSITION -> SECURITY_RECOVERY` (3102); `APPLY_FAILED` (3105) |
| Install failed AFTER mutation, rollback FAILED (irreversible abort) | `rb = rollback_failed` (3108) | `CANCELLED` | line 3109 `CANCELLED`; `APPLY_FAILED_TERMINAL` (3110); `recovery_episode_disposition <- RECOVERY_INSTALL_FAILED_ABORTED` (3112); `RoundAbort(recovery_install_failed_aborted)` (3115) |
| APPLIED — branch-C RESTORED reaches HASHING | `commit = install_committed` then `disp = assignment_phase_completed` (3118–3120) | `CONSUMED` | line 3122 `CONSUMED`; `SetRecoveryDecisionStatus(…, APPLIED)` (3123); `recovery_outcome_finalised[episode] <- RESTORED` (3124) |
| Assignment phase failed, rollback FAILED (irreversible abort) | `disp = assignment_phase_failed` then `rb = rollback_failed` (3129–3131) | `CANCELLED` | line 3133 `CANCELLED`; `APPLY_FAILED_TERMINAL` (3134); `RECOVERY_INSTALL_FAILED_ABORTED` (3136); `RoundAbort` (3139) |
| Assignment phase failed, rollback COMPLETE | `disp = assignment_phase_failed`, rollback ok (3142) | `CONSUMED` | line 3144 `CONSUMED` after `TRANSITION -> SECURITY_RECOVERY` (3142); `APPLY_FAILED` (3145) |

So the APPLIED path writes `CONSUMED` (line 3122); every plan-invalid / reversible-rollback path
writes `CONSUMED` (lines 3079, 3095, 3104, 3144) alongside a DECLARED failure disposition
(`APPLY_FAILED`); the stale / version-mismatch noop writes `SUPERSEDED` (line 3069); and each
irreversible-abort path writes `CANCELLED` (lines 3109, 3133) alongside `APPLY_FAILED_TERMINAL` and
`RECOVERY_INSTALL_FAILED_ABORTED`. The hook's NOTE confirms it "EXPLICITLY consumes the continuation
due fact (CONSUMED / SUPERSEDED / CANCELLED, U4) before returning" (lines 3155–3156). The consumption
is atomic with the outcome: on the APPLIED path the same straight-line block sets `CONSUMED` (3122),
`APPLIED` (3123), and `RESTORED` (3124) with no intervening event boundary, and on each failure path
the status write and the declared disposition sit in the same block before RETURN.

### 3.2 `ApplyRecoveryWorkAfterEpilogue` (§ `PROCEDURE` line 2623)

The recovery-work hook likewise locates its target by the EXPLICIT `due_status` and consumes it on
every path: "IF `W.due_status != DUE` OR `W.due_at_event_time != t`: RETURN
`nothing_applicable_due(t)`" (line 2633). Each subsequent exit writes a terminal status:

| Transition (recovery-work path) | Guard / trigger | Status written | Code path (exact lines) |
|---|---|:--:|---|
| Stale / freshness lost | `round_state != SECURITY_RECOVERY` OR outcome finalised OR `W.bound_census_version != census.RecoveryCensusVersion` OR NOT (breach ∧ before deadline) (2637–2640) | `SUPERSEDED` | line 2641 `due_status <- SUPERSEDED` (+ `status <- SUPERSEDED` 2642) |
| Plan invalid (compute-only; NO mutation) | `plan = plan_invalid(reason)` (2649) | `CONSUMED` | line 2651 `due_status <- CONSUMED` (+ `status` 2652) |
| Commit failed BEFORE mutation | `commit = install_failed_before_mutation` (2657) | `CONSUMED` | line 2658 `due_status <- CONSUMED` |
| Commit failed AFTER mutation, rollback FAILED (irreversible abort) | `rb = rollback_failed(rr)` (2664) | `CONSUMED` | line 2666 `due_status <- CONSUMED`; `RECOVERY_INSTALL_FAILED_ABORTED` (2668); `RoundAbort` (2670) |
| Commit failed AFTER mutation, rollback SUCCEEDED | rollback ok (2673) | `CONSUMED` | line 2674 `due_status <- CONSUMED` |
| APPLIED — reserve wake / redistribution seated (round STAYS SECURITY_RECOVERY) | `commit = install_committed` (2677) | `CONSUMED` | line 2680 `due_status <- CONSUMED` (+ `status` 2681) |

The work hook consumes as `CONSUMED` on apply / plan-invalid / commit-fail / rollback and as
`SUPERSEDED` on the stale-noop; its NOTE states it "EXPLICITLY consumes the due fact (CONSUMED /
SUPERSEDED) before returning (U4)" (lines 2689–2690). A recovery-work due fact never depends on this
hook to write `CANCELLED`; that value is reserved for terminal round closure (§4).

### 3.3 Terminal consumption — `CancelActiveRecoveryEpisode` (§ `PROCEDURE` line 2305)

The remaining lifecycle value `CANCELLED` is written on terminal closure of an unfinished episode.
`CancelActiveRecoveryEpisode` (S4 terminal cleanup, called only by `CloseRoundAssignments` when the
round is closing and no outcome is being applied) cancels each pending decision's queued
continuation event and then, for a decision still marked due, writes the explicit status:
`IF D.continuation_due_status = DUE: SET recovery_decisions[decision_id].continuation_due_status <-
CANCELLED` (line 2320, "# U4: explicit terminal consumption"). Symmetrically for an in-flight
recovery-work action it cancels the queued `RecoveryWorkDueEvent` and writes
`IF W.due_status = DUE: SET recovery_work[W.work_id].due_status <- CANCELLED` (line 2329, "# U4:
explicit terminal consumption"). So a terminal round leaves NO record with an unconsumed `DUE` status:
any DUE continuation or DUE work fact that survives to closure is explicitly retired to `CANCELLED`.

## 4. The finalisation assertion checks the EXPLICIT status, not a timestamp

`ProcessEventTime` runs the canonical event-time tail — `FinalizeEventTimeSecurityCensus(t)` (line
265), `ApplyRecoveryCompletionAfterEpilogue(t)` (line 266),
`ApplyRecoveryAssignmentContinuationAfterEpilogue(t)` (line 267), `ApplyRecoveryWorkAfterEpilogue(t)`
(line 268), `FinalizePostRecoveryApplicationState(t)` (line 269) — and only THEN asserts the U4
finalisation conditions. The header states `t` "may be finalised ONLY when it is quiescent, its
census is settled, and no recovery-continuation / recovery-work application remains due at t (checked
via the EXPLICIT due status, U4)" (lines 270–271). The two assertions are, verbatim:

- `ASSERT no recovery_decisions[*].continuation_due_status = DUE with continuation_due_at_event_time =
  t` (line 274) — commented "U4/T7: every DUE continuation at t was explicitly CONSUMED/SUPERSEDED/
  CANCELLED (not inferred from a timestamp)" (line 275); and
- `ASSERT no recovery_work[*].due_status = DUE with due_at_event_time = t` (line 276) — commented
  "U1/U4: every DUE recovery-work fact at t was explicitly consumed by
  `ApplyRecoveryWorkAfterEpilogue`" (line 277).

Both assertions predicate on the EXPLICIT status field (`continuation_due_status = DUE`,
`due_status = DUE`); the timestamp (`… _at_event_time = t`) is only an AND-conjunct that scopes the
check to THIS `event_time`. The check therefore passes IFF every record whose DUE fact was pinned to
`t` has been advanced OUT of `DUE` into `CONSUMED` / `SUPERSEDED` / `CANCELLED` by §3's hooks (or by
§3.3 on terminal closure). Because §3.1 and §3.2 write a terminal status on every return path and
§3.3 retires any survivor to `CANCELLED`, no `DUE` record with `… _at_event_time = t` can reach line
274 or line 276 — the assertions hold structurally rather than by coincidence of timestamps.

## 5. Checks

| # | Check | Result | Citation (exact procedure + lines) |
|---|-------|:------:|------------------------------------|
| 1 | `CONTINUATION_DUE_STATUS` is an explicit enumerated lifecycle carried on the continuation record AND on every recovery-work record | PASS | §0.8 enum line 731; U4 gloss lines 732–736; `decision_record.continuation_due_status` lines 644–649; `work_record.due_status` lines 721–724; initial `NOT_DUE` in `SeatRecoveryWork` line 2571 |
| 2 | The continuation Due event sets `continuation_due_status <- DUE` and applies nothing | PASS | `RecoveryAssignmentContinuationDueEvent` (line 2998): `<- DUE` line 3025; timestamp/envelope 3026–3027; census refresh 3031–3032; comment 3009–3013; NOTE 3035–3038 |
| 3 | The recovery-work Due event sets `due_status <- DUE` and applies nothing | PASS | `RecoveryWorkDueEvent` (line 2589): `<- DUE` line 2610; `status <- DUE` 2609; timestamp/envelope 2611–2612; census refresh 2615–2616; NOTE 2619–2621 |
| 4 | The continuation hook consumes the DUE fact on EVERY return path (APPLIED → CONSUMED; plan-invalid/rollback → CONSUMED; stale/version-mismatch → SUPERSEDED; irreversible abort → CANCELLED) before returning | PASS | `ApplyRecoveryAssignmentContinuationAfterEpilogue` (line 3040): SUPERSEDED 3069; CONSUMED 3079, 3095, 3104, 3122, 3144; CANCELLED 3109, 3133; NOTE 3155–3156 |
| 5 | The recovery-work hook consumes the DUE fact on EVERY return path (apply/plan-invalid/commit-fail/rollback → CONSUMED; stale → SUPERSEDED) before returning | PASS | `ApplyRecoveryWorkAfterEpilogue` (line 2623): locate by `due_status` 2633; SUPERSEDED 2641; CONSUMED 2651, 2658, 2666, 2674, 2680; NOTE 2689–2690 |
| 6 | A DUE fact surviving to terminal round closure is explicitly retired to CANCELLED | PASS | `CancelActiveRecoveryEpisode` (line 2305): continuation line 2320; recovery-work line 2329 |
| 7 | The consumption is ATOMIC with the outcome — the status write and the declared disposition sit in one straight-line block before RETURN (no intervening event boundary) | PASS | APPLIED block CONSUMED+APPLIED+RESTORED lines 3122–3124; each failure block writes status + `APPLY_FAILED`/`APPLY_FAILED_TERMINAL` before RETURN (3079–3083, 3109–3117, 3133–3141) |
| 8 | `ProcessEventTime`'s finalisation assertion checks the EXPLICIT status (`= DUE`), with the timestamp only scoping to `t` | PASS | `ProcessEventTime` line 274 (continuation) and line 276 (recovery-work); header note 270–271; per-assertion comments 275, 277 |

## 6. Failure-mode contrast

**Failure mode A — a due fact INFERRED from a timestamp rather than an explicit status.** Suppose the
records carried only `continuation_due_at_event_time` / `due_at_event_time` and no status field, and
"is it still due?" were read as "does the timestamp equal `t`?". Then a decision that had already been
applied, superseded, or rolled back would STILL satisfy `… _at_event_time = t` — the timestamp is
written once by the Due event (lines 3026, 2611) and is not cleared by the application. The
finalisation check would either spuriously fire on an already-handled record or, to avoid that, would
have to be weakened to a heuristic. U4 forecloses this: the assertion predicates on
`continuation_due_status = DUE` / `due_status = DUE` (lines 274, 276), a value that the Due event
WRITES (lines 3025, 2610) and that every hook return path REWRITES to `CONSUMED` / `SUPERSEDED` /
`CANCELLED` (§3). "Handled" is a state the record is IN, not a coincidence of two timestamps; the
timestamp survives only as an `event_time` scope for the check.

**Failure mode B — a DUE fact left UNCONSUMED at finalisation.** Suppose some hook return path
(a plan-invalid abort, a rollback branch, or a stale-noop) returned WITHOUT writing the status. That
record would still read `DUE` with `… _at_event_time = t` when `ProcessEventTime` reached line 274 /
276, and the assertion would fire — `t` could not be finalised. U4 makes this unreachable: §3.1
writes a terminal status on all eight continuation exits (lines 3069, 3079, 3095, 3104, 3109, 3122,
3133, 3144), §3.2 writes one on all six recovery-work exits (lines 2641, 2651, 2658, 2666, 2674,
2680), and §3.3 retires any survivor of a terminal closure to `CANCELLED` (lines 2320, 2329). There
is no return path on which a record pinned to `t` keeps `DUE`, so the finalisation assertion is
discharged by construction — it is an assertion-integrity guarantee, not an accounting change.

## 7. Result

Under U4 the branch-C continuation-due fact and every recovery-work due fact are an EXPLICIT
lifecycle value `CONTINUATION_DUE_STATUS in { NOT_DUE, DUE, CONSUMED, SUPERSEDED, CANCELLED }` carried
on the continuation record (`recovery_decisions[decision_id].continuation_due_status`, §0.8 lines
644–649, 731) and on every recovery-work record (`recovery_work[work_id].due_status`, §0.8 lines
721–724), seeded `NOT_DUE` at seating (`SeatRecoveryWork` line 2571). The Due events set it to `DUE`
and apply nothing: `RecoveryAssignmentContinuationDueEvent` (line 3025) and `RecoveryWorkDueEvent`
(line 2610). The post-epilogue hooks ATOMICALLY consume it before returning:
`ApplyRecoveryAssignmentContinuationAfterEpilogue` writes `CONSUMED` on the APPLIED path (line 3122)
and on every plan-invalid / reversible-rollback path (lines 3079, 3095, 3104, 3144), `SUPERSEDED` on
the stale / version-mismatch noop (line 3069), and `CANCELLED` on each irreversible-abort path (lines
3109, 3133), each alongside a DECLARED failure disposition (`APPLY_FAILED` / `APPLY_FAILED_TERMINAL` /
`RECOVERY_INSTALL_FAILED_ABORTED`); `ApplyRecoveryWorkAfterEpilogue` writes `CONSUMED` on apply /
plan-invalid / commit-fail / rollback (lines 2651, 2658, 2666, 2674, 2680) and `SUPERSEDED` on the
stale-noop (line 2641); and `CancelActiveRecoveryEpisode` retires any DUE survivor of a terminal
closure to `CANCELLED` (lines 2320, 2329). `ProcessEventTime` finalises `t` only after asserting the
EXPLICIT status — `ASSERT no recovery_decisions[*].continuation_due_status = DUE with
continuation_due_at_event_time = t` (line 274) and `ASSERT no recovery_work[*].due_status = DUE with
due_at_event_time = t` (line 276) — where the timestamp only scopes the check to this `event_time` and
the DUE status is the load-bearing predicate. U4 operates purely on how a due fact is represented and
retired: it changes no census value, residency interval, or transition-energy term, the census
refreshes only re-stamp provenance over the same `H_*` values, the A1 accepted baseline of
8.420833333 kWh is unchanged, and no new consensus feature is introduced — it is a lifecycle and
assertion-integrity correction, never a change to how time or energy is counted.

The prohibited rebranded-algorithm-name variants are not used anywhere in this document.
