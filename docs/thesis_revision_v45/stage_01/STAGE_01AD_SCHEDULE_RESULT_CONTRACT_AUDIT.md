# Stage 1AD — ScheduleEvent Result-Union Contract Audit (correction AD3)

This is a documentation-only audit of correction **AD3** — the complete `ScheduleEvent` result union, audited across
every caller — in the Stage-1 formal specification of **PoCol** and the idle policy within PoCol. It was generated AFTER
the normative documents (`STAGE_01_PROTOCOL_PSEUDOCODE.md` PROCEDURE `ScheduleEvent` RETURNS and every caller of it;
`STAGE_01_ROUND_STATE_MACHINE.md` §3.10h AD3; `STAGE_01_TERMINOLOGY.md` Stage-1AD addendum "ScheduleEvent result union")
and the Stage-1AD semantic test vectors (`STAGE_01AD_SEMANTIC_TEST_VECTORS.md`, TV254) were final; it modifies no
specification document and quotes the current lines of the frozen source of truth. The A1 baseline `8.420833333 kWh` is
unchanged and the binding PoCol naming rule (the algorithm is **PoCol**; the mechanism under audit is the idle policy
within PoCol — never "PoCol-E"/"Energy-Aware PoCol"/"Enhanced PoCol") is preserved. Every claim below is grounded in an
actual quote from `STAGE_01_PROTOCOL_PSEUDOCODE.md` (the primary source) with an approximate line anchor, and is
corroborated by TV254.

---

## AD3 checks

| Check | Result |
|---|---|
| **1. `ScheduleEvent` RETURNS declares EXACTLY the five-variant union (one success + four rejections)** | **PASS** — `RETURNS: scheduled(event_ref, record) \| rejected_finalised_time \| post_horizon_event_rejected \| rejected_post_epilogue_not_strictly_later \| rejected_backward_time` (~L586–L587), annotated `AD3: the COMPLETE result union — every success and rejection variant ScheduleEvent can return. scheduled carries the canonical EventRef AND the central queued_event_record (was scheduled(event_ref, envelope))` (~L588–L589). Restated verbatim in the AD3 addendum `ScheduleEvent RETURNS scheduled(EventRef, queued_event_record) \| rejected_finalised_time \| post_horizon_event_rejected \| rejected_post_epilogue_not_strictly_later \| rejected_backward_time` (~L1134). Matches RSM §3.10h AD3 (~L978–L980) and the terminology addendum (~L1102–L1105). Corroborated by TV254 (the exact rejection variants named). |
| **2. Every rejection actually returned in the body appears in the declared union — no procedure returns a variant absent from its declared set** | **PASS** — the four `RETURN` statements in the body are `RETURN rejected_finalised_time` (~L537, finalised-time guard, I-02), `RETURN post_horizon_event_rejected` (~L544, O2 horizon `target_event_time > EQ.run_horizon_T`), `RETURN rejected_post_epilogue_not_strictly_later` (~L550, S7 post-epilogue guard), and `RETURN rejected_backward_time` (~L560, K8 `target_event_time < current_event_time`); the sole success `RETURNS: scheduled(event_ref, record)` is at ~L586. All four rejections and the success are members of the declared union (Check 1). AD3 addendum: `Every caller inspects the union; no procedure returns a rejection variant absent from this declared set` (~L1135–L1136). AD10 records the corrected gap: `ScheduleEvent's declared RETURNS omitted rejection variants` (~L1171). Corroborated by TV254 ("returns the exact rejection variant from its declared union"). |
| **3. Every result-inspecting caller pattern-matches `scheduled(event_ref, record)` — the second slot is named `record`, NEVER `envelope` — and takes an explicit rejection branch** | **PASS** — nine result-inspecting callers all bind the return and match `scheduled(event_ref, record)` (or the negative form `scheduled(...)`), with the second slot named `record` at every live site: StartWake `IF seat is NOT scheduled(event_ref, record)` (~L1559); PrepareParticipantsForNewRound retry `IF r = scheduled(event_ref, record)` (~L2090); SecurityFloorEvaluate deadline seat `IF r != scheduled(...)` (~L3214); SeatRecoveryCompletion `IF result = scheduled(event_ref, record)` (~L3462); SeatRecoveryWork `IF result = scheduled(event_ref, record)` (~L3617); CompleteSecurityRecovery branch-C `IF r = scheduled(event_ref, record)` (~L4076); ContinueTemplateRefreshAssignmentSetup retry `IF r = scheduled(event_ref, record)` (~L5527); ScheduleSolutionPropagation CertificateArrival seat `IF r_sched = scheduled(event_ref, record)` (~L4944); ScheduleSolutionPropagation BlockAcceptancePoint seat `IF b_sched = scheduled(event_ref, record)` (~L4957). NO live caller binds `scheduled(event_ref, envelope)` (independent search of the pseudocode finds `envelope` only in the "(was …)" history comment). Corroborated by TV254 ("the caller's `IF … = scheduled(event_ref, record)` binding does NOT match, so the caller takes its rejection branch"). |
| **4. There is NO bare one-field `scheduled(event_ref)` success result anywhere** | **PASS** — a whole-document regex search for `scheduled(event_ref)` / `scheduled(EventRef)` (single slot) returns zero matches; every `scheduled(` occurrence is the two-slot `scheduled(event_ref, record)` / `scheduled(EventRef, queued_event_record)` (or the ellipsis negative `scheduled(...)` at ~L3212, and the ~L589/~L1081 history comments). The Stage-1AC two-slot `scheduled(EventRef, envelope)` is superseded by AD3's `scheduled(EventRef, queued_event_record)` and no residual bare form remains. Corroborated by TV254 ("No caller treats a rejection as a successful seat because a variant is missing from the declared union"). |
| **5. Caller-inspection contract — every result-binding caller inspects the union; a for-effect caller relies only on the deterministic O2 post-horizon rejection** | **PASS** — the refined AD3 addendum states exactly this contract: `Every result-BINDING caller pattern-matches scheduled(event_ref, record) and takes an EXPLICIT branch on each rejection it can receive (so a stored/cancellable reference is NEVER a rejection token); a FOR-EFFECT caller's only reachable rejection is the deterministic O2 post-horizon rejection (the event is never enqueued), which needs no further handling` (~L1137–L1142), matched in RSM §3.10h AD3 and I16 AD3. The two `ScheduleSolutionPropagation` seats now BIND and INSPECT: the `CertificateArrival` seat `SET r_sched <- CALL ScheduleEvent(…)` then `IF r_sched = scheduled(event_ref, record): ADD event_ref TO certificate_arrival_events(cpc) ELSE: RECORD certificate_arrival_not_scheduled(…)` (~L4938–L4948), and the `BlockAcceptancePoint` seat `SET b_sched <- CALL ScheduleEvent(…)` then `IF b_sched = scheduled(event_ref, record): SET block_arrival_event(cpc) <- event_ref ELSE: SET block_arrival_event(cpc) <- null; RECORD block_arrival_not_scheduled(…)` (~L4951–L4962), so `certificate_arrival_events(cpc)` holds only real EventRefs and `block_arrival_event(cpc)` is null-guarded at every `CANCEL` (~L5053, ~L5194, ~L5405, ~L5588; field declared "or null" at ~L720). The two for-effect seats draw only the deterministic O2 rejection: `ScheduleNextHashWork`'s `HashWorkEvent` (~L2683, dropping the post-horizon rejection matches O2) and `HandlePropagationFailure`'s `ResumeFromPause` (~L5063, targets the current non-finalised in-horizon `event_time`, so no rejection is reachable). Consistent with TV254. |

---

## Caller-by-caller audit

Eleven live `CALL ScheduleEvent` sites exist (grep `CALL ScheduleEvent`; the two additional hits at ~L404/~L408 are the
`SCHEDULE`-shorthand definition and an L6 prose reference, not calls). Every `scheduled(` binding was inspected.

| Caller (procedure, anchor) | Event seated | Binds result? | Pattern-matches `scheduled(event_ref, record)`? | Handles rejection? |
|---|---|---|---|---|
| `StartWake` (~L1553) | `WakeCompleteEvent` | Yes (`seat`) | Yes — `IF seat is NOT scheduled(event_ref, record)` (~L1557) | **Yes** — `RETURN wake_schedule_failed_before_transition(reason = seat)` (~L1560) |
| `PrepareParticipantsForNewRound` — participant retry seat 1 (~L2082) | `SetupRetryEvent` | Yes (`r`) | Yes — `IF r = scheduled(event_ref, record)` (~L2088) | **Yes** — else falls through to `RETURN CALL RoundAbort(… participant_setup_failed …)` (~L2098) |
| `ContinueTemplateRefreshAssignmentSetup` — template-refresh retry seat 2 (~L5517) | `SetupRetryEvent` | Yes (`r`) | Yes — `IF r = scheduled(event_ref, record)` (~L5523) | **Yes** — else `RETURN CALL RoundAbort(… template_refresh_failed …)` (~L5533) |
| `SecurityFloorEvaluate` — recovery-entry seat (~L3207) | `RecoveryDeadlineEvent` | Yes (`r`) | Yes (negative) — `IF r != scheduled(...)` (~L3212) | **Yes** — `RECORD recovery_deadline_not_seated(episode, r)` (~L3213) |
| `SeatRecoveryCompletion` (~L3454) | `RecoveryCompletionDueEvent` | Yes (`result`) | Yes — `IF result = scheduled(event_ref, record)` (~L3460) | **Yes** — else `SetRecoveryDecisionStatus(… SCHEDULE_FAILED)` + `RETURN recovery_completion_not_seated(result)` (~L3469–L3471) |
| `SeatRecoveryWork` (~L3609) | `RecoveryWorkDueEvent` | Yes (`result`) | Yes — `IF result = scheduled(event_ref, record)` (~L3615) | **Yes** — else `RECORD recovery_work_schedule_rejected` + `RETURN recovery_work_not_seated(result)` (~L3625–L3626) |
| `CompleteSecurityRecovery` — branch-C continuation seat (~L4067) | `RecoveryAssignmentContinuationDueEvent` | Yes (`r`) | Yes — `IF r = scheduled(event_ref, record)` (~L4074) | **Yes** — else `RECORD recovery_continuation_not_seated` + `RETURN recovery_branch_result(kind = FAILED …)` (~L4081–L4082) |
| `ScheduleNextHashWork` (~L2683) | `HashWorkEvent` | No (fire-and-forget) | No | No — `RETURNS: scheduled` unconditionally (~L2687); only `post_horizon_event_rejected` is reachable and dropping it matches O2 (queue never holds events beyond `T`), so **safe-by-design** |
| `ScheduleSolutionPropagation` — per-recipient (~L4938) | `CertificateArrival` | Yes (`r_sched`) | **Yes** — `IF r_sched = scheduled(event_ref, record)` (~L4944), storing the canonical `event_ref` (~L4945) | **Yes** — `ELSE: RECORD certificate_arrival_not_scheduled(…, r_sched)` (~L4948); a rejected (post-horizon) arrival is never enqueued and never stored |
| `ScheduleSolutionPropagation` — acceptance point (~L4951) | `BlockAcceptancePoint` | Yes (`b_sched`) | **Yes** — `IF b_sched = scheduled(event_ref, record)` (~L4957), binding `block_arrival_event(cpc) <- event_ref` (~L4958) | **Yes** — `ELSE: SET block_arrival_event(cpc) <- null; RECORD block_arrival_not_scheduled(…, b_sched)` (~L4961–L4962); every `CANCEL block_arrival_event` is null-guarded |
| `HandlePropagationFailure` — candidate-scoped resume (~L5063) | `ResumeFromPause` | No (fire-and-forget) | No | No — `target_event_time = dispatch_envelope.event_time` (current, non-finalised, in-horizon) so NO rejection variant is reachable; **vacuously safe** (for-effect) |

---

## Result

**PASS on all five AD3 checks.** `ScheduleEvent`'s RETURNS declares exactly `scheduled(event_ref, record) |
rejected_finalised_time | post_horizon_event_rejected | rejected_post_epilogue_not_strictly_later | rejected_backward_time`
(~L586–L587, ~L1134); each of the four rejections is actually returned in the body (~L537, ~L544, ~L550, ~L560) and every
one is a member of the declared union, so no procedure returns a variant absent from its declared set (Checks 1–2). All
nine result-inspecting callers pattern-match `scheduled(event_ref, record)` with the second slot named `record` (never
`envelope`) and each takes an explicit rejection branch (Check 3, caller table), and there is no residual bare one-field
`scheduled(event_ref)` anywhere (Check 4). The pseudocode, RSM §3.10h AD3, the terminology Stage-1AD addendum, and TV254
agree on the union.

The caller-inspection contract (Check 5) now holds at all eleven call sites. The two `ScheduleSolutionPropagation` seats —
the `CertificateArrival` seat (~L4938) and the `BlockAcceptancePoint` seat (~L4951) — bind the `ScheduleEvent` result
(`r_sched` / `b_sched`), pattern-match `scheduled(event_ref, record)`, store only the canonical `event_ref` on a real seat,
and take an explicit rejection branch (`RECORD certificate_arrival_not_scheduled` / `RECORD block_arrival_not_scheduled`);
`block_arrival_event(cpc)` is declared "or null" (~L720) and every `CANCEL` of it is null-guarded (~L5053, ~L5194, ~L5405,
~L5588), so a stored/cancellable reference is never a rejection token. The AD3 addendum wording is the precise contract:
result-binding callers inspect and branch on each reachable rejection, and the two for-effect seats
(`ScheduleNextHashWork`'s `HashWorkEvent`, ~L2683; `HandlePropagationFailure`'s `ResumeFromPause`, ~L5063) rely only on the
deterministic O2 post-horizon rejection (never enqueued; nothing bound). The terminology AC1 EventRef paragraph now reads
`returns scheduled(EventRef, …)` with an explicit AD3 forward-reference (TERM ~L1050), so no residual `scheduled(EventRef,
envelope)` claim remains. The A1 baseline `8.420833333 kWh` and the binding PoCol naming rule are preserved.
