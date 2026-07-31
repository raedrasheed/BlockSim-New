# Stage 1U — Procedure Signature / Call-Site Audit

This audit verifies, by signature-and-call-site analysis over `STAGE_01_PROTOCOL_PSEUDOCODE.md` (not string search
alone), that every Stage-1U signature change is matched at every call site, and that the post-epilogue scheduling
context reaches every nested `ScheduleEvent`. Name remains **PoCol**; the mechanism is **the idle policy within
PoCol**; the A1 baseline (`8.420833333 kWh`) is unchanged.

## Signature changes (U2/U5/U6)

| Procedure | New / changed input | Call sites checked |
|-----------|---------------------|--------------------|
| `StartWake` | `scheduling_context` (`SchedulingSourceContext`) replaces the bare `dispatch_envelope`; an ordinary dispatched caller threads `ORDINARY_DISPATCH(dispatch_envelope)` (read from a bare threaded `dispatch_envelope`), a post-epilogue caller passes `POST_EPILOGUE(pctx)` | All `CALL StartWake` sites: the ordinary participant/refresh/reassign/resume sites thread the dispatched handler's `dispatch_envelope` (read as `ORDINARY_DISPATCH`); `ReserveActivate`, `RangeAssign`, `RangeReassign` and `CommitRecoveryAssignmentPlan` thread `scheduling_context = scheduling_context`. **PASS** |
| `ReserveActivate` | `scheduling_context` replaces `dispatch_envelope`; threads it to `StartWake` | Called by `CommitRecoveryAssignmentPlan` (`scheduling_context = scheduling_context`) — a live caller again (its Stage-1T caller, the removed reserve-dependent continuation ELSE, is gone). **PASS** |
| `RangeAssign` | `scheduling_context` replaces `dispatch_envelope`; threads it to `StartWake` | Called by `CommitRecoveryAssignmentPlan` (post-epilogue) and by the ordinary assignment path (read as `ORDINARY_DISPATCH`). **PASS** |
| `RangeReassign` | `scheduling_context` replaces `dispatch_envelope`; threads it to `StartWake` | Called by `CommitRecoveryAssignmentPlan` (post-epilogue) and by the ordinary reassignment paths (read as `ORDINARY_DISPATCH`). **PASS** |
| `CommitRecoveryAssignmentPlan` | takes `scheduling_context`; threads it to `ReserveActivate` / `RangeReassign` / `RangeAssign` / `StartWake` | Called by `ApplyRecoveryWorkAfterEpilogue` and `ApplyRecoveryAssignmentContinuationAfterEpilogue`, both passing `scheduling_context = POST_EPILOGUE(pctx)`. **PASS** |
| `CompleteAssignmentPhase` | returns an explicit `assignment_phase_completed \| assignment_phase_failed(reason)` (T5, unchanged in U; U6 fixes the callers) | All three call sites capture and branch: `PrepareParticipantsForNewRound`, `TemplateRefresh`, `ApplyRecoveryAssignmentContinuationAfterEpilogue`. **PASS** |

## Post-epilogue context reaches every nested ScheduleEvent (U2, gate 3)

Trace, for the post-epilogue recovery-work / continuation-install path:

```
ApplyRecoveryWorkAfterEpilogue(t) / ApplyRecoveryAssignmentContinuationAfterEpilogue(t)
  builds pctx = PostEpilogueSchedulingContext(source_event_time = t, source_envelope = <due dispatch_envelope>, EQ, RunContext)
  → CommitRecoveryAssignmentPlan(plan, scheduling_context = POST_EPILOGUE(pctx))
      → ReserveActivate(deficit, scheduling_context = POST_EPILOGUE(pctx))         # RESERVE spec
          → StartWake(..., scheduling_context = POST_EPILOGUE(pctx))
              → ScheduleEvent(EQ, RoundContext, WakeCompleteEvent, target = next_representable_simulation_time(t) | t + latency,
                              post_epilogue_context = pctx)                        # STRICTLY LATER than t
      → RangeReassign(..., scheduling_context = POST_EPILOGUE(pctx)) / RangeAssign(..., scheduling_context = POST_EPILOGUE(pctx))   # REDISTRIBUTION spec
          → StartWake(..., scheduling_context = POST_EPILOGUE(pctx)) → ScheduleEvent(..., post_epilogue_context = pctx)
```

**PASS** — no procedure on the post-epilogue path creates a `pctx` and then schedules using only the ordinary
dispatch envelope; the `PostEpilogueSchedulingContext` reaches every nested `ScheduleEvent`, and a zero-latency
post-epilogue wake targets `next_representable_simulation_time(source)` (strictly later than the source time, gate 4).

## Result

**SIGNATURE / CALL AUDIT (Stage 1U): PASS** — every Stage-1U signature change is matched at every call site; the
post-epilogue scheduling context reaches every nested `ScheduleEvent`; `ReserveActivate` regains a live caller; and no
`CompleteAssignmentPhase` caller ignores the disposition. Documentation only; name remains PoCol; A1 baseline
`8.420833333 kWh` unchanged; the prohibited rebranded-algorithm-name variants are not used anywhere in this document.
