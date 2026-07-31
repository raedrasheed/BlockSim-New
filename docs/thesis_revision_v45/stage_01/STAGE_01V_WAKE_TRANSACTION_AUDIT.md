# Stage 1V — Wake Transaction Audit (V3, V9)

## 0. Scope

This document audits correction **V3** ("`StartWake` is a transaction with explicit
structured outputs") together with its **V9** aspect ("no ambiguous boolean/`AND` returns;
signature, RETURNS block, and call sites agree") as they appear in the *current* Stage-1
formal specification. It is a descriptive audit: it reads and quotes the committed artifacts
and asserts nothing beyond what those artifacts state. It describes the final committed state
of the corpus — there are no open V3/V9 findings against the wake transaction.

The object under audit is the procedure `StartWake` and the complete set of procedures that
invoke it. Every claim is grounded in the following primary sources, all under
`docs/thesis_revision_v45/stage_01/`:

- `STAGE_01_PROTOCOL_PSEUDOCODE.md`
  - `StartWake` — §0.10, lines **1083–1144** (header at 1083: *"V3/V9: a TRANSACTION with
    explicit structured outputs"*).
  - `WakeCompleteEvent` — §0.10, lines 1146–1217 (the scheduled completion consumer that
    retires `WAKING`).
  - `ScheduleEvent` — §0.7f, lines 420–473 (the sole enqueue interface; `RETURNS:
    scheduled(envelope)` at 470).
  - `ProcessEventTime` finalisation assertion — line 272 (the causality obligation the
    zero-latency POST_EPILOGUE rule protects).
  - Call sites: `PrepareParticipantsForNewRound` (four cases, 1505/1522/1544/1559),
    `RangeAssign` §4 (1797), `AdversarialParticipationChangeEvent` low-power T10 re-entry
    (2203), `ReserveActivateFromPlan` §10 (2956), `CommitRecoveryAssignmentPlan`
    redistribution branch §10a (3487), `RangeReassign` §13 (3751), `ResumeFromPause` §16a
    (3935), `TemplateRefresh` (4509).
- `STAGE_01_ROUND_STATE_MACHINE.md` — §3.10 Stage-1V addendum, **V2** block lines 586–589,
  **V3** block lines 591–596, **V8** block lines 623–627, **V9** block lines 629–631.
- `STAGE_01_TERMINOLOGY.md` — Stage-1V terminology addendum, **V2** entry lines 796–799, the
  **`StartWake` transaction (V3)** entry lines 800–803, and the **No boolean/AND returns
  (V9)** entry lines 822–823.
- `STAGE_01_INVARIANT_CATALOGUE.md` — audited for a no-orphan-`WAKING` entry (see §7).

Nomenclature note. The specification annotates the no-orphan-`WAKING` liveness obligation and
the strictly-later zero-latency rule with the tag **"(gate 4)"** (pseudocode lines 1099, 1105,
1140, and again at the caller assertions 1809, 2967, 2977, 3762). The audit uses that tag
where the source does.

---

## 1. The defect (pre-V3 behaviour)

Before V3, `StartWake` was specified to signal its outcome through a **boolean or an
`AND`-composite** value — the pattern the V9 block names explicitly and removes: *"Constructs
like `RETURN ScheduleEvent(...) AND wake_started` are removed"*
(`STAGE_01_ROUND_STATE_MACHINE.md`, line 629). Three distinct hazards followed from a
boolean/composite return.

**(a) Ambiguity of disposition (a conformance / recoverability hazard).** A single truth value
cannot tell a caller *which* of the two possible failures occurred — a schedule that never
seated an event, versus a state transition that failed after an event was already seated. The
two require opposite compensating actions (nothing to undo, versus a seated event that must be
cancelled). A boolean forces the caller either to re-derive the situation from side state or to
guess; neither is executable. The terminology addendum records the resolution: *"Every
procedure inspects the scheduler disposition explicitly and returns one declared structured
result"* (`STAGE_01_TERMINOLOGY.md`, lines 822–823).

**(b) Orphan-`WAKING` (a liveness/safety hazard).** If the `WAKING` state transition and the
scheduling of the completion event are performed in an *unordered* or *independently committed*
fashion, a partial success leaves the system in one of two illegal configurations:

- the transition applied but the schedule failed — the miner is `WAKING` with **no live
  `WakeCompleteEvent`**, so it can never leave `WAKING` (no event will ever fire to advance it
  to `ACTIVE_HASHING` or `OFFLINE`): a dead miner and a stuck round; or
- the event was scheduled but the transition failed — a completion event exists targeting a
  miner that is not `WAKING`, to be absorbed only by the stale-target guard.

The first configuration — a miner stranded in `WAKING` with no completion event to retire it —
is the **orphan-`WAKING`** condition. The V3 block states the property that forecloses it: *"a
transition failure after the seat CANCELS the seated event, so no failure leaves a miner
WAKING without a live `WakeCompleteEvent`"* (`STAGE_01_ROUND_STATE_MACHINE.md`, lines 594–595).
The pseudocode carries the same statement as the transaction's purpose clause: *"so NO failure
leaves miner_state = WAKING with no live WakeCompleteEvent (gate 4)"*
(`STAGE_01_PROTOCOL_PSEUDOCODE.md`, line 1099).

**(c) Callers that ignored or mis-typed the result.** Because the pre-V3 return carried no
structured disposition, some create-then-wake constructors did not consume it: a `RangeAssign`
whose RETURNS annotation described the *assignment* rather than the wake outcome, and a
`RangeReassign` that issued a bare `CALL StartWake` and discarded the value entirely. Such a
site could not detect a wake failure and therefore could not compensate for a partially-created
head. The current `RangeReassign` NOTE records the removal of exactly that construct: *"the
pre-V3 discarded `CALL StartWake` is removed"* (`STAGE_01_PROTOCOL_PSEUDOCODE.md`, line 3774).

V3 removes all three hazards by making `StartWake` a **transaction** with a fixed statement
order and three **named structured dispositions**; V9 forbids the boolean/`AND` return that
made hazard (a) unrecoverable and requires that every call site inspect the named disposition,
so that signature, RETURNS block, and call sites agree.

---

## 2. The transaction (numbered statement-order walkthrough)

`StartWake` is declared (`STAGE_01_PROTOCOL_PSEUDOCODE.md`, line 1083):

```
PROCEDURE StartWake                                             # V3/V9: a TRANSACTION with explicit structured outputs
  INPUTS: RoundContext, MinerID, target_assignment, from_state,
          scheduling_context   # V2: SchedulingSourceContext in {ORDINARY_DISPATCH(dispatch_envelope), POST_EPILOGUE(pctx)} — EXPLICIT
  PRECONDITIONS: from_state = miner_state(MinerID) in {REGISTERED, RESERVE, EXHAUSTED_PENDING, LOW_POWER_LISTEN};
                 target_assignment is a bound PENDING (or PAUSED-resumed) assignment for MinerID.
```

The canonical order is stated in the body header (lines 1096–1099):

```
    # V3 CANONICAL ORDER: (1) sample latency; (2) compute target via SchedulingSourceContext; (3) validate + ScheduleEvent;
    #   (4) ONLY after a successful seat, apply the WAKING transition; (5) if the transition fails after the seat, CANCEL
    #   the seated WakeCompleteEvent; (6) publish the WakeEventRef; (7) return the structured wake_seated result — so NO
    #   failure leaves miner_state = WAKING with no live WakeCompleteEvent (gate 4).
```

The executable statements realise that order exactly.

**(1) Sample the wake latency** (line 1101):

```
    wake_latency <- [SIMULATION SAMPLING] wake_latency_model(MinerID)    # the ONLY wake draw (sampling summary item 3)
```

This is the sole wake-latency draw in the specification (F5). It occurs *before* any queue
mutation, so a rejected seat consumes no queue state.

**(2) Compute `target_time` from the `SchedulingSourceContext`** (lines 1102–1109):

```
    IF scheduling_context is POST_EPILOGUE(pctx):
      SET src <- pctx.source_event_time
      SET target_time <- (wake_latency > 0 ? src + wake_latency : next_representable_simulation_time(src))   # V3/gate 4: STRICTLY LATER than src
      SET post_ctx <- pctx
    ELSE:  # ORDINARY_DISPATCH(e)
      SET target_time <- now + wake_latency                             # future (ScheduleEvent derives dc = 0) or same-time (forward dc, H5)
      SET post_ctx <- null
```

The zero-latency `POST_EPILOGUE` branch targets `next_representable_simulation_time(src)`, not
`src` (audited in §4).

**(3) Validate + `ScheduleEvent` to SEAT the `WakeCompleteEvent`** (lines 1110–1119), inspecting
the disposition **explicitly** (V9):

```
    SET seat <- CALL ScheduleEvent(EQ, RoundContext, WakeCompleteEvent,
                     target_event_time = target_time, target_microphase = WAKE_COMPLETE,
                     {MinerID, AssignmentID(target_assignment)},
                     post_epilogue_context = post_ctx)                   # V2/S7: post_ctx present ONLY for POST_EPILOGUE
    IF seat != scheduled(...):
      RECORD wake_schedule_rejected(MinerID, AssignmentID(target_assignment), seat)
      RETURN wake_schedule_failed_before_transition(reason = seat)
    SET wake_event_ref <- seat.event_ref
```

`ScheduleEvent` returns `scheduled(envelope)` on success (`STAGE_01_PROTOCOL_PSEUDOCODE.md`,
line 470). The guard `IF seat != scheduled(...)` is the V9 explicit inspection — no boolean
`AND`. A failure here occurs **before any transition**; the comment records *"The miner is
UNCHANGED (still from_state); nothing to cancel"* (line 1116), and the procedure returns the
first named failure disposition.

**(4) ONLY after a successful seat, apply the `WAKING` transition** (lines 1120–1124):

```
    SET tr <- CALL ApplyMinerStateTransition(MinerID, from_state, WAKING,
                     transition_envelope = dispatch_envelope,           # S1: ONE explicit transition-envelope object
                     reason = wake_start, assignment_ref = target_assignment,
                     candidate_id = null, propagation_id = null)         # F6
```

`ApplyMinerStateTransition` is *"the ONLY writer of miner_state"* (line 1075). The miner enters
`WAKING` here — after, and only after, the completion event is on the queue.

**(5) If the transition fails after the seat, CANCEL the seated event** (lines 1125–1130):

```
    IF tr != transition_applied:
      IF wake_event_ref is still pending on EQ: CANCEL wake_event_ref on EQ
      RECORD wake_transition_failed(MinerID, wake_event_ref, tr)
      RETURN wake_transition_failed_after_seat(reason = tr, WakeEventRef = wake_event_ref)
```

The compensating `CANCEL` retires the event the transaction seated in step (3), so a failed
transition leaves neither a `WAKING` miner (the transition did not apply) nor a dangling
completion event. The second named failure disposition carries the `WakeEventRef` so the caller
can perform an idempotent re-cancel.

**(6) Publish the `WakeEventRef` on the assignment's wake registry** (line 1132):

```
    SET wake_event_ref_of(target_assignment) <- wake_event_ref
```

This makes the reference discoverable by a later rollback/cancel path (V4/V8).

**(7) Return the structured `wake_seated` result** (lines 1133–1135):

```
    RETURN wake_seated(AssignmentID = AssignmentID(target_assignment), WakeEventRef = wake_event_ref,
                       wake_target_time = target_time, resulting_state = WAKING)
```

### The three dispositions (exact field lists)

The `RETURNS:` block (lines 1136–1137) enumerates exactly:

```
  RETURNS: wake_seated(AssignmentID, WakeEventRef, wake_target_time, resulting_state = WAKING) |
           wake_schedule_failed_before_transition(reason) | wake_transition_failed_after_seat(reason, WakeEventRef)
```

| # | Disposition | Fields | Emitted when |
|---|-------------|--------|--------------|
| 1 | `wake_seated` | `AssignmentID`, `WakeEventRef`, `wake_target_time`, `resulting_state = WAKING` | seat succeeded **and** transition applied (steps 3–7 complete) |
| 2 | `wake_schedule_failed_before_transition` | `reason` | `ScheduleEvent` rejected the seat (step 3); miner unchanged, nothing to cancel |
| 3 | `wake_transition_failed_after_seat` | `reason`, `WakeEventRef` | seat succeeded but the `WAKING` transition failed (step 5); seated event cancelled |

These field lists are reproduced identically in the state machine (lines 592–593) and the
terminology addendum (lines 800–802). The three names partition the outcome space: exactly one
is returned on every path, and each names precisely which side effects have occurred. The
signature (line 1083 header), the RETURNS block (1136–1137), and every call site (§5) agree —
this is the V9 property realised for `StartWake`.

---

## 3. Seat-before-transition ordering argument

The ordering *seat first, transition second* is not incidental; it is what makes the
no-orphan-`WAKING` obligation discharge under a purely local (single-procedure) argument. The
NOTE states it directly (lines 1138–1140): *"It seats the `WakeCompleteEvent` FIRST (inspecting
the scheduler disposition EXPLICITLY, never a boolean AND — V9), THEN applies the WAKING
transition; a transition failure after the seat CANCELS the seated event, so no failure leaves
miner_state = WAKING without a live WakeCompleteEvent (gate 4)."*

**Why seat must precede the transition.** Consider the two possible orderings of the
irreversible-under-partial-failure pair {seat `WakeCompleteEvent`, enter `WAKING`}.

- *Transition-then-seat (rejected ordering).* The miner enters `WAKING` in step A; the seat is
  attempted in step B. If B fails, the miner is already `WAKING` and there is no live event to
  retire it — the exact orphan-`WAKING` configuration of §1(b). Recovery would require *rolling
  back a state transition* (`WAKING → from_state`), but `ApplyMinerStateTransition` accrues wake
  residency on entry (F6) and is the sole state writer; an ad-hoc reverse edge is not a
  sanctioned transition. The hazard is therefore unrecoverable in-procedure.

- *Seat-then-transition (adopted ordering).* The event is seated in step (3); the miner enters
  `WAKING` in step (4). If (3) fails, `WAKING` is never entered (early return, disposition 2).
  If (4) fails, the seated event is **cancelled** by the compensating action in step (5)
  (disposition 3), and the miner is still `from_state`. In both failure cases the *event* is the
  object that is cheaply and legally reversible (a queue `CANCEL`), whereas the *state
  transition* is only ever performed forward. Ordering the reversible action last lets the
  transaction compensate with a queue cancel instead of an illegal reverse transition.

**The compensating CANCEL.** Step (5)'s cancel is written defensively —
`IF wake_event_ref is still pending on EQ: CANCEL wake_event_ref on EQ` — so it is idempotent
with respect to any caller-side re-cancel. The create-then-wake callers rely on exactly that
idempotence: on `wake_transition_failed_after_seat` each re-checks *"IF wref is still pending on
EQ: CANCEL wref on EQ  # idempotent; StartWake already cancelled"* (`RangeAssign` line 1806,
`ReserveActivateFromPlan` line 2964, `RangeReassign` line 3759). The event thus has a single
definite disposition regardless of how many participants attempt to cancel it.

---

## 4. Zero-latency `POST_EPILOGUE` target-time rule (causality)

The target-time computation (step 2) treats the two `SchedulingSourceContext` variants
differently, and the difference is a causality obligation, not a modelling convenience.

For a **`POST_EPILOGUE(pctx)`** wake (line 1105):

```
      SET target_time <- (wake_latency > 0 ? src + wake_latency : next_representable_simulation_time(src))   # V3/gate 4: STRICTLY LATER than src
```

where `src = pctx.source_event_time`. When the sampled latency is zero, the target is
`next_representable_simulation_time(src)` — the least representable simulation time strictly
greater than `src` — **never `src` itself**.

**Why same-time re-entry is forbidden for a post-epilogue wake.** A `POST_EPILOGUE` hook runs
*after* the event-time epilogue of `src` — that is, after `src` has been drained. The
`ProcessEventTime` finalisation assertion records the invariant a same-time seat would break
(`STAGE_01_PROTOCOL_PSEUDOCODE.md`, line 272): *"ASSERT no ordinary event remains with
event_time = t  # R1: the post-epilogue application enqueued NOTHING at t (T7: incl.
StartWake/re-arm strictly later)"*. Seating a `WakeCompleteEvent` at `event_time = src` from a
post-epilogue hook would (i) place an ordinary event at an already-drained/finalising time,
violating that assertion, and (ii) re-enter the same instant with no forward progress in
`event_time`, defeating the monotone-time causal order. Mapping zero latency to
`next_representable_simulation_time(src)` guarantees `target_time > src`, so the wake fires at a
strictly later, not-yet-finalised instant. The NOTE restates the rule (lines 1142–1143): *"a
POST_EPILOGUE zero-latency wake targets `next_representable_simulation_time(source)`, never the
drained source time."*

**Why the `ORDINARY_DISPATCH` branch may keep the same instant.** For an `ORDINARY_DISPATCH(e)`
wake, `target_time <- now + wake_latency`; a zero draw yields a same-`event_time` target, which
is legal because that instant is *not yet finalised* and `ScheduleEvent` forwards the
`delta_cycle` (H5) to preserve causal order *within* the instant (line 1108). The contrast is
precisely the point: a same-time seat is causally admissible only while the instant is still
open (ordinary dispatch), and inadmissible once it has been drained (post-epilogue). V3 encodes
that distinction structurally in `StartWake`, and the state-machine V3 block reproduces the
rule (lines 595–596).

---

## 5. Caller disposition-handling table

Every audited call site inspects the *named* disposition; none inspects a boolean, and none
discards the result. The table records, per call site, which dispositions are matched, the
caller's own structured return, and the compensating action on failure. Line numbers are
`STAGE_01_PROTOCOL_PSEUDOCODE.md`.

| Call site (proc / line) | Context passed | `wake_seated` handling | Failure handling | Caller's own return |
|---|---|---|---|---|
| `PrepareParticipantsForNewRound` — REGISTERED (1505) | `ORDINARY_DISPATCH` | `IF wr = wake_seated(...)`: `ADD wref to participant_setup_txn.wakes` (1507) | `ELSE: SET participant_setup_error <- wr` (1508) | `participant_set_prepared` \| retry-seated \| `round_aborted` (1598), via V8 rollback |
| — RESERVE (1522) | `ORDINARY_DISPATCH` | `ADD wref …` (1524) | `ELSE: SET participant_setup_error <- wr` (1525) | as above |
| — LOW_POWER_LISTEN / VALID_SOLUTION_VERIFIED · ROUND_ACCEPTED · ROUND_ABORTED (1544) | `ORDINARY_DISPATCH` | `ADD wref …` (1546) | `ELSE: SET participant_setup_error <- wr` (1547) | as above |
| — LOW_POWER_LISTEN / RANGE_EXHAUSTED · ASSIGNMENT_REVOKED (1559) | `ORDINARY_DISPATCH` | `ADD wref …` (1561) | `ELSE: SET participant_setup_error <- wr` (1562) | as above |
| `RangeAssign` (1797) | threaded `scheduling_context` | `IF wr = wake_seated(...)`: `RETURN range_assigned(AssignmentID, WakeEventRef = wref, resulting_state = WAKING)` (1800–1801) | re-cancel on `wake_transition_failed_after_seat` (1805–1806); `CLOSE assignment` (1807); `RESTORE` ledgers (1808); `ASSERT miner_state = fs` (1809, gate 4); `RETURN range_assign_wake_failed(reason = wr, AssignmentID)` (1810) | `range_assigned` \| `range_assign_wake_failed` (1811) |
| `AdversarialParticipationChangeEvent` — low-power T10 fresh re-entry (2203) | `ORDINARY_DISPATCH` | tail-`RETURN CALL StartWake(...)` — named disposition forwarded unchanged inside `participation_change_record` | (same; forwarded) | `participation_change_record` (2222) |
| `ReserveActivateFromPlan` (2956) | threaded `scheduling_context` | `IF wr = wake_seated(...)`: `RETURN reserve_activation_committed(MinerID, AssignmentID, assignment_version, WakeEventRef = wr.WakeEventRef)` (2958–2960) | re-cancel on `wake_transition_failed_after_seat` (2963–2964); `CLOSE assignment` (2965); `RESTORE` ledgers (2966); `ASSERT miner_state = RESERVE` (2967, gate 4); `RETURN reserve_activation_failed_after_assignment(reason = wr, AssignmentID, rollback_record)` (2969–2970) | committed \| failed_before_mutation \| failed_after_assignment (2971–2973) |
| `CommitRecoveryAssignmentPlan` — redistribution wakes (3487) | `POST_EPILOGUE` | `IF w = wake_seated(waid, wref, wtt, ws)`: `ADD wref to created_events` (3489–3490) | `ELSE:` build `plan.rollback_metadata`, `RETURN install_failed_after_mutation(reason = w, plan.rollback_metadata)` (3491–3494) | install_committed \| failed_before_mutation \| failed_after_mutation (3498) |
| `RangeReassign` (3751) | threaded `scheduling_context` | `IF wr != wake_seated(...)` is the failure guard; on success `SET wref <- wr.WakeEventRef` (3764), update the ledger (3766–3767), `RETURN range_reassigned(provenance, AssignmentID, WakeEventRef = wref)` (3770–3771) | re-cancel on `wake_transition_failed_after_seat` (3758–3759); `CLOSE assignment` (3760); `RESTORE` ledgers so suffix stays reassignable (3761); `ASSERT miner_state = fs` (3762, gate 4); `RETURN range_reassign_wake_failed(reason = wr, AssignmentID)` (3763) | `range_reassigned` \| `range_reassign_wake_failed` (3772) |
| `ResumeFromPause` (3935) | `ORDINARY_DISPATCH` | `IF wr = wake_seated(...)`: `RETURN resume_started(MinerID, resumed_from, WakeEventRef = wref)` (3938) | `RETURN resume_wake_failed(MinerID, reason = wr)` (3939); *"the miner is not left WAKING (StartWake guarantees it)"* | `resume_started` \| `resume_wake_failed` (3940) |
| `TemplateRefresh` (4509) | `ORDINARY_DISPATCH` | `IF wr = wake_seated(...)`: `RECORD refresh_wake(m, assignment_m, wref)` (4511), captured into `refresh_setup_txn` (4525–4528) | `ELSE: RECORD refresh_wake_failed(m, assignment_m, wr)` (4512); V8 rollback via `RollbackTemplateRefreshSetup` (4534) + liveness path | `new_TemplateID` \| retry \| `RoundAbort` (4531–4539) |

Observations.

- **Every site inspects the named disposition.** Ten of the eleven `StartWake` invocations bind
  the result (`SET wr <- CALL StartWake …` or `SET w <- CALL StartWake …`) and branch on it; the
  eleventh (`AdversarialParticipationChangeEvent`, line 2203) is a tail `RETURN CALL StartWake`
  that forwards the named structured disposition to its caller intact. There is **no** bare or
  discarded `CALL StartWake` anywhere in the corpus, and **no** `RETURN ScheduleEvent(...) AND …`
  boolean composite (both confirmed by exhaustive grep, §6 and §8). This is the V9 property:
  *"the caller inspects the named disposition"* (line 1144), never a truth value.

- **Create-then-wake transactions roll back their own head on wake failure.** `RangeAssign`,
  `ReserveActivateFromPlan`, and `RangeReassign` each first construct a PENDING head (via
  `CreatePendingAssignment`) and then run the `StartWake` transaction. On any wake failure each
  one (i) re-cancels a possibly-seated event idempotently on `wake_transition_failed_after_seat`,
  (ii) closes the just-created PENDING head legally (`status = CLOSED`, `custody_status =
  revoked`, J7/I18b), (iii) restores the coverage/custody ledgers for the range, (iv) asserts the
  miner remained in its captured `from_state` (`fs` / `RESERVE`) — the gate-4 assertion — and (v)
  returns a *structured* failure disposition (`range_assign_wake_failed` /
  `reserve_activation_failed_after_assignment` / `range_reassign_wake_failed`). No orphan PENDING
  assignment and no stranded `WAKING` miner survive.

- **`RangeAssign` and `RangeReassign` are now fully conformant (previously-recorded findings
  resolved).** Earlier revisions of this audit recorded two findings against these two sites: a
  `RangeAssign` whose RETURNS annotation lagged its body, and a `RangeReassign` that discarded the
  `StartWake` result. Both are resolved in the current corpus. `RangeAssign` captures
  `wr <- CALL StartWake(...)` (1797), returns `range_assigned(AssignmentID, WakeEventRef,
  resulting_state = WAKING)` on `wake_seated` (1801), and its RETURNS block (1811) now enumerates
  `range_assigned(AssignmentID, WakeEventRef, resulting_state = WAKING) |
  range_assign_wake_failed(reason, AssignmentID)` — agreeing with the body. `RangeReassign`
  likewise captures `wr <- CALL StartWake(...)` (3751), returns `range_reassigned(provenance,
  AssignmentID, WakeEventRef)` on success (3770–3771), and its RETURNS block (3772) enumerates
  `range_reassigned(provenance, AssignmentID, WakeEventRef) | range_reassign_wake_failed(reason,
  AssignmentID)`. The `RangeReassign` NOTE states the resolution in-line: *"INSPECTS the
  structured disposition EXPLICITLY (the pre-V3 discarded `CALL StartWake` is removed)"* (lines
  3773–3774). For both procedures signature, RETURNS block, and body agree (V9); there are no
  open findings.

- **Explicit scheduling contexts.** The `scheduling_context` supplied at each site is the V2
  explicit context. The post-epilogue install paths (`ReserveActivateFromPlan` and the
  redistribution constructors invoked by `CommitRecoveryAssignmentPlan`, §10a) thread
  `POST_EPILOGUE(pctx)`, so their wakes obey the strictly-later rule of §4; the dispatched setup
  and resume paths thread `ORDINARY_DISPATCH(dispatch_envelope)`.

---

## 6. The no-orphan-`WAKING` invariant and its proof sketch

**Invariant (no-orphan-`WAKING`).** In every reachable configuration, if `miner_state(m) =
WAKING` then there exists a live (pending, un-cancelled) `WakeCompleteEvent` on `EQ` targeting
`m`'s bound head. Equivalently: no miner is ever left `WAKING` without a live completion event.
The specification states it as the transaction's purpose clause and tags it *(gate 4)*
(pseudocode lines 1099, 1140; state machine lines 594–595).

**Proof sketch.**

1. *Sole entry into `WAKING`.* `ApplyMinerStateTransition` is the sole writer of `miner_state`
   (line 1075). The only edge whose target is `WAKING` with `reason = wake_start` is step (4) of
   `StartWake` (line 1121). Hence every entry into `WAKING` is a `StartWake` step (4).

2. *Step (4) runs only after a live seat.* Step (4) is reached only by falling through the guard
   at step (3): `IF seat != scheduled(...)` returns early (disposition 2, line 1118). Therefore,
   at the instant step (4) executes, `seat = scheduled(envelope)` and `wake_event_ref <-
   seat.event_ref` (line 1119) names a live event just enqueued through the sole `ScheduleEvent`
   interface. So the moment `m` becomes `WAKING`, a live `WakeCompleteEvent` for `m`'s head
   already exists on `EQ`.

3. *Failure of step (4) restores the pre-state and retires the event.* If the transition does not
   apply (`tr != transition_applied`), step (5) cancels `wake_event_ref` (line 1128) and returns
   disposition 3; `m` was never moved to `WAKING`. So a failed transition produces neither a
   `WAKING` miner nor a dangling event.

4. *No other producer of `WAKING`-with-no-event.* Because (1)–(3) cover every path that sets
   `WAKING`, the only reachable configurations with `miner_state(m) = WAKING` are those produced
   by a completed step (4), each of which (by 2) carries a live completion event, and that event's
   reference is published on the assignment (step 6, line 1132).

5. *Consumers preserve the invariant.* `WAKING` is left only by (a) the scheduled
   `WakeCompleteEvent` firing — `WAKING → ACTIVE_HASHING` on success (line 1169) or `WAKING →
   OFFLINE` on deadline expiry (line 1179) — which consumes the very event that witnessed the
   invariant, after the M3 stale-target guard (lines 1152–1158) has confirmed the target is still
   the miner's live head; or (b) a V8 rollback / cancel that *both* cancels the published
   `WakeEventRef` *and* closes the head, and which verifies *"no participant remains WAKING for a
   rolled-back head"* (`STAGE_01_ROUND_STATE_MACHINE.md`, lines 624–625). Neither consumer can
   leave a `WAKING` miner without its event.

Therefore the biconditional "(`m` is `WAKING`) ⟺ (a live `WakeCompleteEvent` for `m` exists)"
holds across the transaction and its consumers, which is the no-orphan-`WAKING` invariant. ∎

**No orphan PENDING head either.** A create-then-wake caller compounds the local guarantee with
a head-closure obligation. When `StartWake` returns either failure disposition to `RangeAssign`
(1802–1810), `ReserveActivateFromPlan` (2961–2970), or `RangeReassign` (3754–3763), the caller
closes the PENDING head it created (`status PENDING → CLOSED`, `custody_status = revoked`, no
`CURRENT` recorded, I18b), restores the range's coverage/custody ledgers, and asserts the miner
stayed in its captured `from_state`. Consequently a wake failure inside a create-then-wake
transaction leaves *neither* a stranded `WAKING` miner (by the proof above) *nor* an orphan
PENDING assignment (by the head-closure) *nor* an un-reassignable suffix (the ledger restore in
`RangeReassign` keeps the accepted unsearched suffix reassignable, line 3761).

**Corroborating assertions in the corpus.** `ReserveActivateFromPlan` states the miner-side
guarantee as an executable assertion on its failure path: `ASSERT miner_state(reserve_miner) =
RESERVE  # V4/gate 4: the reserve miner stays RESERVE, not WAKING` (line 2967), and its NOTE
adds *"never a stranded WAKING miner (gate 4)"* (line 2977). `RangeAssign` and `RangeReassign`
carry the parallel `ASSERT miner_state(...) = fs  # V3/gate 4: the miner is not left WAKING`
(lines 1809, 3762). The V8 rollbacks (`RollbackParticipantSetup`, `RollbackTemplateRefreshSetup`)
close the loop for the ordinary setup paths by verifying the same negative (state-machine lines
623–625).

---

## 7. Traceability to invariants, terminology, and the round state machine

**State machine (`STAGE_01_ROUND_STATE_MACHINE.md`, §3.10 Stage-1V addendum).**

- **V2 block (586–589)** withdraws the Stage-1U bare-`dispatch_envelope` alias and requires an
  explicit `scheduling_context` at every `StartWake` / `ReserveActivate` / `RangeAssign` /
  `RangeReassign` / `CommitRecoveryAssignmentPlan` call — the context threading audited in §5.
- **V3 block (591–596)** reproduces the three disposition signatures verbatim and states the
  seat-before-transition / cancel-on-post-seat-failure property and the zero-latency
  `POST_EPILOGUE → next_representable_simulation_time(source)` rule. The pseudocode of §2–§5 is
  a faithful realisation of this block.
- **V8 block (623–627)** supplies the executable rollbacks that discharge the consumer half of
  the §6 invariant for the ordinary assignment-setup paths, and states that
  `PrepareParticipantsForNewRound` and `TemplateRefresh` capture each structured `StartWake`
  result and roll back on failure.
- **V9 block (629–631)** removes `RETURN ScheduleEvent(...) AND wake_started`-style returns and
  requires that *"every procedure inspects the scheduler disposition explicitly and returns one
  declared structured result whose signature, RETURNS block, and call sites agree."* The audit
  confirms signature/RETURNS/call-site agreement for `StartWake` and for all eleven call sites
  (§5), with no open findings.

**Terminology (`STAGE_01_TERMINOLOGY.md`, Stage-1V addendum).**

- The **`StartWake` transaction (V3)** entry (800–803) defines `wake_seated` /
  `wake_schedule_failed_before_transition` / `wake_transition_failed_after_seat` with the same
  field lists used here, and states the no-orphan-`WAKING` property.
- The **No boolean/AND returns (V9)** entry (822–823) matches the V9 block: *"Every procedure
  inspects the scheduler disposition explicitly and returns one declared structured result;
  `RETURN ScheduleEvent(...) AND wake_started`-style constructs are removed."*
- These terminology definitions are the naming authority the audit's tables and dispositions
  cite.

**Invariant catalogue (`STAGE_01_INVARIANT_CATALOGUE.md`) — traceability note.** The catalogue
does **not** contain a separately numbered `I`-invariant for no-orphan-`WAKING`: a search for
`WakeComplete`, `remains WAKING`, and `left WAKING` over the catalogue returns no matching
entry, and its two `StartWake` mentions (lines 374, 446) concern recovery-census re-arming and
round-boundary residency accounting, not the wake transaction. The no-orphan-`WAKING`
obligation is instead carried (i) as the Stage-1V **"gate 4"** liveness tag inside the
`StartWake` procedure and its callers (pseudocode 1099, 1105, 1140, 1809, 2967, 2977, 3762),
(ii) in the state-machine **V3** block (594–595), and (iii) in the terminology **V3** entry
(802–803). This is reported as an accurate description of the current corpus, not as a
prescription: the property is specified and proved locally, but is not lifted into the numbered
`I`-invariant table. Lifting it into the `I`-series would be a documentation addition, not a
change to the pseudocode audited here.

---

## 8. Summary of dispositions

| Disposition | When | Miner end-state | Event end-state |
|---|---|---|---|
| `wake_seated(AssignmentID, WakeEventRef, wake_target_time, resulting_state=WAKING)` | seat ok + transition ok | `WAKING` | live `WakeCompleteEvent` at `wake_target_time` |
| `wake_schedule_failed_before_transition(reason)` | seat rejected | unchanged (`from_state`) | none created |
| `wake_transition_failed_after_seat(reason, WakeEventRef)` | seat ok, transition failed | unchanged (`from_state`) | seated event **cancelled** |

In all three, the biconditional of §6 holds: a `WAKING` miner exists **iff** a live
`WakeCompleteEvent` exists. V3 makes the outcome a named, inspectable transaction; V9 guarantees
every caller reads that name rather than an ambiguous boolean; and the seat-before-transition
ordering with a compensating cancel is what closes the orphan-`WAKING` liveness hazard under a
local, single-procedure argument. The create-then-wake callers (`RangeAssign`,
`ReserveActivateFromPlan`, `RangeReassign`) extend the same discipline to their own PENDING
heads, so a wake failure leaves no orphan assignment.

**Mechanical checks performed for this audit (against `STAGE_01_PROTOCOL_PSEUDOCODE.md`).**

- `CALL StartWake` invocations: **11**, across **8** procedures — `PrepareParticipantsForNewRound`
  (×4: 1505/1522/1544/1559), `RangeAssign` (1797), `AdversarialParticipationChangeEvent` (2203),
  `ReserveActivateFromPlan` (2956), `CommitRecoveryAssignmentPlan` (3487), `RangeReassign` (3751),
  `ResumeFromPause` (3935), `TemplateRefresh` (4509).
- Bare / discarded `CALL StartWake` (result neither bound nor returned): **0**.
- `RETURN ScheduleEvent(...) AND …` (or any `AND wake_started`) boolean composite: **0**.
