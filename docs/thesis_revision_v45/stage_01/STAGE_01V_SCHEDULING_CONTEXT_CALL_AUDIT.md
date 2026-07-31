# Stage 1V — Scheduling-Context Call Audit (V2)

## 1. Scope and method

This document audits correction **V2 — one explicit `SchedulingSourceContext` at every
scheduling call site** — as it stands in the current, now-final Stage-1 formal
specification. V2 withdraws the former implicit-default alias under which a *bare*
`dispatch_envelope` argument was read as `ORDINARY_DISPATCH`, and requires that every
scheduling-bearing procedure and every scheduling-bearing call site name its scheduling
source explicitly, as exactly one variant of a closed two-variant type.

The audit is grounded in the actual current text of three artifacts in this directory:

- `STAGE_01_PROTOCOL_PSEUDOCODE.md` — the normative pseudocode (the object of the audit);
- `STAGE_01_ROUND_STATE_MACHINE.md` — §3.10 Stage-1V addendum, block **V2**;
- `STAGE_01_TERMINOLOGY.md` — the `SchedulingSourceContext` (U2) glossary entry and the
  Stage-1V terminology addendum, entry **V2**.

Method. The pseudocode was enumerated by matching every `scheduling_context` occurrence,
every `CALL StartWake(` site, every `CALL RangeAssign(` / `CALL RangeReassign(` /
`CALL ReserveActivate(` / `CALL ReserveActivateFromPlan(` /
`CALL CommitRecoveryAssignmentPlan(` site, every `post_epilogue_context` occurrence, and
every literal `dispatch_envelope = dispatch_envelope` argument. Each scheduling-bearing
site is recorded below with its enclosing procedure, its callee, the `scheduling_context`
variant it supplies, and whether that variant is passed **explicitly**. This document is
descriptive: it reads the specification and does not modify it.

Note on snapshot. The line numbers cited below reference the current committed snapshot of
the pseudocode; the procedure names, argument text, and structural findings are the
load-bearing content and are stable under incidental re-pagination.

## 2. The defect V2 corrects

Prior to V2 the specification carried an implicit coercion inherited from Stage-1U: a
scheduling-bearing procedure could be invoked with a *bare* dispatch envelope, and that
bare envelope was **read as** `ORDINARY_DISPATCH` by default. The scheduling *source* of a
wake was therefore not a syntactic property of the call site; it was recovered by a default
rule. This is unsound for two reasons that matter to the discrete-event semantics.

1. **Source ambiguity at the call site.** A single procedure — `StartWake`,
   `ReserveActivate`, `RangeAssign`, `RangeReassign`, `CommitRecoveryAssignmentPlan` — is
   reachable both from an ordinary dispatched handler (whose envelope names the event
   currently being processed) and from a **post-epilogue** installer
   (`ApplyRecoveryWorkAfterEpilogue`, `ApplyRecoveryAssignmentContinuationAfterEpilogue`,
   and the `CompleteSecurityRecovery` branch dispatch), which runs *after* the event time
   is drained and the epilogue has run. Under the implicit alias a reader could not decide,
   from the call text alone, which of these two sources a given invocation represented.

2. **Divergent target-time computation for a zero-latency wake.** The two sources compute
   the target event time of a seated `WakeCompleteEvent` differently. An
   `ORDINARY_DISPATCH` wake targets `now + wake_latency` and lets `ScheduleEvent` derive
   the delta-cycle (future time → `0`; same-time zero-latency → the forward cycle,
   never backward — H5/L6). A `POST_EPILOGUE` wake must target a time **strictly later**
   than the drained `source_event_time`: for positive latency, `source + wake_latency`; for
   **zero latency**, `next_representable_simulation_time(source_event_time)` — never the
   drained source instant itself (R1 structural). If a post-epilogue caller were allowed to
   construct a `PostEpilogueSchedulingContext` and then, via the implicit alias, seat its
   wake as though it were an ordinary dispatch, a zero-latency wake could be targeted at the
   already-finalised source time, violating the strictly-later requirement and the
   `finalised_event_times` guard. The ambiguity is thus not cosmetic: it changes the target
   instant a zero-latency wake resolves to, precisely at the ORDINARY-vs-POST_EPILOGUE
   boundary.

V2 eliminates the default rule so that the scheduling source is a declared, checkable
property of every call site.

## 3. The corrected contract

`SchedulingSourceContext` is a **closed sum type of exactly two variants** (pseudocode
registry §0.7, "U2 explicit scheduling-source context threaded through every post-epilogue
wake path", lines 761–767):

```
SchedulingSourceContext in { ORDINARY_DISPATCH(dispatch_envelope),
                             POST_EPILOGUE(PostEpilogueSchedulingContext) }
```

The contract has the following clauses, each with textual support in the current
pseudocode.

- **Closed, two-variant, no third case.** There is no `DEFAULT`, no null, and no bare
  envelope admitted where a `SchedulingSourceContext` is required. The registry entry
  (761–767), the `StartWake` input contract (line 1085: a `scheduling_context` typed
  `SchedulingSourceContext in {ORDINARY_DISPATCH(dispatch_envelope), POST_EPILOGUE(pctx)} —
  EXPLICIT`), and the procedure notes all state the two variants exhaustively.

- **Every scheduling-bearing procedure takes it as a named input.** Six procedure
  signatures declare `scheduling_context : SchedulingSourceContext`: `StartWake` (1083/1085),
  `RangeAssign` (1779/1781), `ReserveActivate` (2907/2909), `ReserveActivateFromPlan`
  (2938/2940), `CommitRecoveryAssignmentPlan` (3439/3440), and `RangeReassign` (3717/3719).
  None of these six retains a bare `dispatch_envelope` scheduling parameter in its
  signature.

- **The variant is the sole source of the underlying envelope.** Inside `StartWake` the
  dispatch envelope used for the WAKING transition is *projected from* the context, not
  received separately: `ORDINARY_DISPATCH(e) -> e`; `POST_EPILOGUE(pctx) ->
  pctx.source_envelope` (line 1094: `SET dispatch_envelope <- (scheduling_context is
  ORDINARY_DISPATCH(e) ? e : scheduling_context.pctx.source_envelope)`). There is no path by
  which an envelope enters the wake independently of the declared variant.

- **Lowering to the scheduler is explicit.** `ScheduleEvent` (420–459) consumes the
  *lowered* form of the context through its `post_epilogue_context` parameter (default
  `null`, line 423): a `POST_EPILOGUE` wake passes a live `PostEpilogueSchedulingContext`;
  an `ORDINARY_DISPATCH` wake passes `null`. `ScheduleEvent` enforces
  `target_event_time > source_event_time` when `post_epilogue_context != null` (lines
  445–448). Thus "present ⟺ POST_EPILOGUE, absent ⟺ ORDINARY" is the one-to-one lowering,
  and the strictly-later property is discharged at the single scheduler interface.

- **Threading, not re-derivation.** A procedure that receives a `scheduling_context` and
  itself calls a lower scheduling procedure **forwards the same context object**
  (`scheduling_context = scheduling_context`); it never re-labels a post-epilogue context as
  ordinary. The post-epilogue context is created once (a `PostEpilogueSchedulingContext`
  with `source_event_time`, `source_envelope`, `EventQueueContext`, `RunContext`; STRUCTURE
  at 407–418) and threaded intact to every nested `ScheduleEvent`.

## 4. Full call-site table

Legend for the **scheduling_context** column: `ORD` = `ORDINARY_DISPATCH(dispatch_envelope)`
passed literally; `POST` = `POST_EPILOGUE(pctx)` passed literally; `THREAD` = the callee's
own `scheduling_context` parameter forwarded unchanged (`scheduling_context =
scheduling_context`). "Explicit?" is **yes** when the call names a `SchedulingSourceContext`
variant (ORD/POST) or forwards the typed parameter (THREAD). No site passes the pre-V2
`dispatch_envelope = dispatch_envelope` scheduling argument; the `BARE` case does not occur
(§5).

### 4.1 Procedure signatures that declare `scheduling_context : SchedulingSourceContext`

| # | Procedure | Signature line | Input line | Signature carries `scheduling_context` |
|---|-----------|---------------|-----------|----------------------------------------|
| S1 | `StartWake` | 1083 | 1085 | yes — `SchedulingSourceContext … EXPLICIT` |
| S2 | `RangeAssign` | 1779 | 1781 | yes |
| S3 | `ReserveActivate` | 2907 | 2909 | yes |
| S4 | `ReserveActivateFromPlan` | 2938 | 2940 | yes |
| S5 | `CommitRecoveryAssignmentPlan` | 3439 | 3440 | yes |
| S6 | `RangeReassign` | 3717 | 3719 | yes |

All six declare the input; none declares a bare `dispatch_envelope` scheduling parameter.

### 4.2 `StartWake` call sites (the wake-seating layer)

| # | Enclosing procedure (case / context) | Call line | Ctx line | scheduling_context | Explicit? |
|---|--------------------------------------|-----------|----------|--------------------|-----------|
| W1 | `PrepareParticipantsForNewRound` — CASE REGISTERED (T3) | 1505 | 1506 | ORD | yes |
| W2 | `PrepareParticipantsForNewRound` — CASE RESERVE (T4) | 1522 | 1523 | ORD | yes |
| W3 | `PrepareParticipantsForNewRound` — CASE LOW_POWER_LISTEN (VALID_SOLUTION_VERIFIED / ROUND_ACCEPTED / ROUND_ABORTED, T10) | 1544 | 1545 | ORD | yes |
| W4 | `PrepareParticipantsForNewRound` — CASE LOW_POWER_LISTEN (RANGE_EXHAUSTED / ASSIGNMENT_REVOKED, T10) | 1559 | 1560 | ORD | yes |
| W5 | `RangeAssign` — activation (T3/T4) | 1797 | 1799 | THREAD | yes |
| W6 | `AdversarialParticipationChangeEvent` — LOW_POWER_LISTEN re-entry (RANGE_EXHAUSTED / ASSIGNMENT_REVOKED, T10) | 2203 | 2205 | ORD | yes |
| W7 | `ReserveActivateFromPlan` — reserve wake (T4) | 2956 | 2957 | THREAD | yes |
| W8 | `CommitRecoveryAssignmentPlan` — redistribution `required_wake_operations` loop | 3487 | 3488 | THREAD | yes |
| W9 | `RangeReassign` — reassigned-suffix activation (T3/T4) | 3751 | 3753 | THREAD | yes |
| W10 | `ResumeFromPause` — PATH-B resume (T30) | 3935 | 3937 | ORD | yes |
| W11 | `TemplateRefresh` — activation loop (T3/T4/T10) | 4509 | 4510 | ORD | yes |

All eleven `StartWake` sites pass an explicit `SchedulingSourceContext`: the four
`PrepareParticipantsForNewRound` cases, the `AdversarialParticipationChangeEvent` re-entry,
the `ResumeFromPause` resume, and the `TemplateRefresh` activation loop pass
`ORDINARY_DISPATCH(dispatch_envelope)` directly; the four sites inside procedures that
themselves receive a context (`RangeAssign`, `ReserveActivateFromPlan`,
`CommitRecoveryAssignmentPlan`, `RangeReassign`) forward it (THREAD).

### 4.3 Reserve-activation, commit, redistribution, and range-(re)assign caller sites

| # | Enclosing procedure (case) | Callee | Call line | Ctx line | scheduling_context | Explicit? |
|---|----------------------------|--------|-----------|----------|--------------------|-----------|
| C1 | `ReserveActivate` | `ReserveActivateFromPlan` | 2927 | 2928 | THREAD | yes |
| C2 | `CommitRecoveryAssignmentPlan` — RESERVE_ACTIVATION spec | `ReserveActivateFromPlan` | 3457 | 3459 | THREAD | yes |
| C3 | `CommitRecoveryAssignmentPlan` — REDISTRIBUTION spec | `RangeReassign` / `RangeAssign` (spec constructor) | 3477 | 3478 | THREAD | yes |
| C4 | `ApplyRecoveryWorkAfterEpilogue` | `CommitRecoveryAssignmentPlan` | 2865 | 2865 | POST | yes |
| C5 | `ApplyRecoveryAssignmentContinuationAfterEpilogue` | `CommitRecoveryAssignmentPlan` | 3334 | 3334 | POST | yes |
| A1 | `AdversarialParticipationChangeEvent` — ENTER, CASE REGISTERED / RESERVE (H6/T3/T4) | `RangeAssign` | 2155 | 2157 | ORD | yes |
| A2 | `AdversarialParticipationChangeEvent` — ENTER, CASE OFFLINE → REGISTERED (H6/T17→T3) | `RangeAssign` | 2165 | 2167 | ORD | yes |
| A3 | `LeaseExpiry` — common reassign tail (L4) | `RangeReassign` | 3697 | 3699 | ORD | yes |

C4 and C5 are the two entry points that *originate* a `POST_EPILOGUE` context: each
constructs a `PostEpilogueSchedulingContext pctx` (with `source_event_time`,
`source_envelope`, `EventQueueContext`, `RunContext`; at lines 2855–2856 and 3317–3318
respectively) and passes `scheduling_context = POST_EPILOGUE(pctx)`. C1–C3 thread whatever
context they received; because the sole originators of `POST_EPILOGUE` are C4/C5 and the
sole callers of C1–C3 in the post-epilogue lineage are the RESERVE_ACTIVATION /
REDISTRIBUTION specs inside `CommitRecoveryAssignmentPlan`, the post-epilogue context
reaches every nested wake unchanged and never degrades to ordinary.

A1, A2, and A3 are the two `RangeAssign` callers in `AdversarialParticipationChangeEvent`
and the single `RangeReassign` caller in `LeaseExpiry`. All three are ordinary dispatched
handlers and pass `scheduling_context = ORDINARY_DISPATCH(dispatch_envelope)` explicitly,
projecting the enclosing handler's own L1 dispatch envelope (comments at 2157/2167 read
"V2: explicit context (L1 envelope)"; at 3699, "V2: explicit context (L1 envelope); L4:
source is CLOSED"). No caller of `RangeAssign` or `RangeReassign` supplies a bare
`dispatch_envelope` scheduling argument.

### 4.4 Direct `ScheduleEvent` post-epilogue seats (the lowered layer)

`ScheduleEvent` never receives a `SchedulingSourceContext`; it receives the lowered
`post_epilogue_context` (default `null`, line 423). Exactly two sites pass it non-null:

| # | Enclosing procedure | Seat line | `post_epilogue_context` | Meaning |
|---|---------------------|-----------|-------------------------|---------|
| E1 | `StartWake` — seat of `WakeCompleteEvent` | 1111–1114 | `post_ctx` (= `pctx` for POST_EPILOGUE, `null` for ORDINARY_DISPATCH) | lowering of the wake's own context |
| E2 | `CompleteSecurityRecovery` — seat of `RecoveryAssignmentContinuationDueEvent` | 3216–3222 | `pctx` | strictly-later seat of the branch-C continuation DUE event |

Every other `CALL ScheduleEvent(` in the document (e.g. `SetupRetryEvent`, `HashWorkEvent`,
`CertificateArrival`, `BlockAcceptancePoint`, the `ResumeFromPause` event,
`RecoveryDeadlineEvent`, `RecoveryCompletionDueEvent`, `RecoveryWorkDueEvent`) leaves
`post_epilogue_context` at its default `null` — i.e. it is an ordinary dispatched-handler
schedule, the lowered form of `ORDINARY_DISPATCH`. This is consistent with the closed type:
absence of a post-epilogue context is exactly the ordinary-dispatch case.

### 4.5 Tally

- Procedure signatures carrying `scheduling_context`: **6** (§4.1).
- Scheduling-bearing call sites that carry a `SchedulingSourceContext`: **19** —
  11 `StartWake` (§4.2) + 8 reserve/commit/redistribution/range-(re)assign caller sites
  (§4.3: C1–C5, A1–A3).
- Of the 19: **all 19 discharge V2 explicitly** — `ORDINARY_DISPATCH` ×10 (W1–W4, W6,
  W10–W11, A1–A3), `THREAD` ×7 (W5, W7–W9, C1–C3), `POST_EPILOGUE` ×2 (C4–C5). **Zero**
  remain in the pre-V2 bare form.
- Direct `ScheduleEvent` post-epilogue seats (lowered layer): **2** (§4.4), both explicit.
- Total scheduling-bearing sites catalogued: **21** (19 context-bearing + 2 lowered seats).

## 5. Confirmation that the implicit alias is removed and every call site is explicit

### 5.1 The alias survives only as a withdrawal notice

A search of the pseudocode for the alias language ("read as ORDINARY_DISPATCH", "bare
dispatch_envelope", "bare-envelope", "implicit conversion") returns exactly one hit, and
that hit is the **withdrawal notice itself**, inside the `StartWake` precondition (lines
1088–1092):

> "There is NO bare-envelope alias / implicit conversion (the Stage-1U 'a bare
> dispatch_envelope is read as ORDINARY_DISPATCH' prose is WITHDRAWN)."

There is no surviving clause that *defines* or *applies* the alias. The only place the old
rule appears is where it is explicitly retired. The registry entry adds the reinforcing
prohibition (line 767): "No procedure creates a `pctx` and then schedules using only the old
ordinary dispatch envelope."

Consistent with the withdrawal, no procedure *signature* retains a bare `dispatch_envelope`
scheduling parameter among the six scheduling-bearing procedures (§4.1); each instead
declares `scheduling_context`.

### 5.2 No scheduling call passes a bare `dispatch_envelope`

A search for the literal `dispatch_envelope = dispatch_envelope` returns matches only in
calls into procedures that genuinely declare a `dispatch_envelope` (M1/L1) parameter for a
*state-transition or driver* purpose — e.g. `ApplyMinerStateTransition`, `RoundAbort`,
`TemplateRefresh`, `EnterLowPowerListen` (line 3642), `ScheduleSolutionPropagation` (1890),
`ExhaustionAdjudicate` (1898), `ResumeFromPause` (2183), `HandlePropagationFailure`,
`CloseRoundAssignments`, and `SetupRetryEvent`'s `TemplateRefresh` re-run. **None** of these
occurrences is a call into a `SchedulingSourceContext`-typed parameter. In particular, every
call to `StartWake`, `RangeAssign`, `RangeReassign`, `ReserveActivate`,
`ReserveActivateFromPlan`, and `CommitRecoveryAssignmentPlan` supplies `scheduling_context`
explicitly (§4.2, §4.3); the count of bare-`dispatch_envelope` scheduling arguments to those
six procedures is **zero**. There is therefore **no residual pre-V2 call site**: the three
sites flagged by the prior version of this audit — the two `RangeAssign` invocations in
`AdversarialParticipationChangeEvent` and the `RangeReassign` invocation in `LeaseExpiry` —
now pass `scheduling_context = ORDINARY_DISPATCH(dispatch_envelope)` (A1 at 2155/2157, A2 at
2165/2167, A3 at 3697/3699) and are fully V2-conformant.

### 5.3 `RangeAssign` / `RangeReassign` are create-then-wake transactions

Beyond declaring `scheduling_context`, both `RangeAssign` (1779–1819) and `RangeReassign`
(3717–3784) are now explicit create-then-wake **transactions**: each builds the PENDING head
via `CreatePendingAssignment`, runs the `StartWake` transaction threading its
`scheduling_context` (W5 at 1797/1799; W9 at 3751/3753), and **inspects the structured
`StartWake` disposition explicitly** — `wake_seated` versus `wake_schedule_failed_before_
transition` / `wake_transition_failed_after_seat` — rather than returning a bare
`assignment` (`RangeAssign`) or discarding the wake result (`RangeReassign`). On a wake
failure each closes the un-activated head legally, restores the coverage/custody ledgers,
asserts the miner stayed in its captured `from_state` (gate 4), and returns a structured
failure (`range_assign_wake_failed` at 1810 / `released_reassign_wake_failed` at 3701). The
scheduling-source context is thus both declared at the signature and consumed structurally
by the transaction.

## 6. Traceability to invariants, terminology, and the round state machine

The V2 contract is cross-referenced coherently across the three artifacts, and the
pseudocode now **matches** the companion documents' "every call site" assertion with no
exception.

- **`STAGE_01_PROTOCOL_PSEUDOCODE.md`.**
  - Registry (§0.7, lines 761–767, "U2 explicit scheduling-source context"): defines
    `SchedulingSourceContext in {ORDINARY_DISPATCH(dispatch_envelope),
    POST_EPILOGUE(PostEpilogueSchedulingContext)}` and lists the five carriers
    (`ReserveActivate` / `RangeReassign` / `RangeAssign` / `StartWake` /
    `CommitRecoveryAssignmentPlan`); asserts every wake is strictly later than the source.
  - `STRUCTURE PostEpilogueSchedulingContext` (S7, 407–418): the declared post-epilogue
    source with `source_event_time`, `source_envelope`, `EventQueueContext`, `RunContext`;
    the `ScheduleEvent(..., post_epilogue_context = this)` clause requires
    `target_event_time > source_event_time` and derives `delta_cycle = 0`.
  - `ScheduleEvent` (420–459): three declared scheduling sources; a post-epilogue call MUST
    carry `post_epilogue_context` and no other call may (426–430) — the lowering discipline
    of §3, enforced at 445–448.
  - `StartWake` (1083–1144): the canonical order — sample latency, compute the target via
    the `SchedulingSourceContext` (1102–1109), validate + `ScheduleEvent` (1111–1114), then
    transition — and the projection `ORDINARY_DISPATCH(e) -> e` / `POST_EPILOGUE(pctx) ->
    pctx.source_envelope` (1094).

- **`STAGE_01_ROUND_STATE_MACHINE.md` — §3.10 Stage-1V addendum, block V2** (lines 586–589,
  "one explicit SchedulingSourceContext at every call site"): "The Stage-1U
  bare-`dispatch_envelope` ORDINARY_DISPATCH alias is WITHDRAWN. Every `StartWake` /
  `ReserveActivate` / `RangeAssign` / `RangeReassign` / `CommitRecoveryAssignmentPlan` call
  passes an EXPLICIT `scheduling_context` — `ORDINARY_DISPATCH(dispatch_envelope)` or
  `POST_EPILOGUE(pctx)`; no signature depends on an implicit conversion." The companion
  clause U2 (541–546) states the strictly-later / zero-latency
  `next_representable_simulation_time(source)` target rule. The pseudocode discharges this at
  **all 19** call sites; the word "Every" now holds without exception.

- **`STAGE_01_TERMINOLOGY.md`.**
  - `SchedulingSourceContext` (U2) glossary entry (lines 758–761):
    `{ORDINARY_DISPATCH(dispatch_envelope), POST_EPILOGUE(PostEpilogueSchedulingContext)}`;
    "a `POST_EPILOGUE` caller threads the `pctx` all the way to `ScheduleEvent`, so a
    zero-latency post-epilogue wake targets `next_representable_simulation_time(source)` and
    is STRICTLY LATER than the source time."
  - Stage-1V terminology addendum, entry V2 (796–799): "The Stage-1U bare-`dispatch_envelope`
    ORDINARY_DISPATCH alias is WITHDRAWN. Every `StartWake` / `ReserveActivate` /
    `RangeAssign` / `RangeReassign` / `CommitRecoveryAssignmentPlan` call passes
    `scheduling_context = ORDINARY_DISPATCH(dispatch_envelope)` or `POST_EPILOGUE(pctx)`
    explicitly."

Invariant anchors exercised by V2: **L1** (dispatch-envelope identity now projected from the
context, never ambient), **L6 / H5** (`ScheduleEvent` is the sole delta-cycle authority; the
zero-latency wake takes the forward cycle, never backward), **S7 / R1** (post-epilogue source
declared; no enqueue at the drained `source_event_time`), **gate 4** (no failure leaves a
miner WAKING without a live `WakeCompleteEvent`, the transaction guarantee V3 layers on top
of V2), and the U2 strictly-later scheduling property.

## 7. Conclusion

The closed two-variant `SchedulingSourceContext` type is defined once, declared on all six
scheduling-bearing procedure signatures, projected (never re-derived) inside `StartWake`,
and lowered one-to-one onto `ScheduleEvent.post_epilogue_context`. The Stage-1U
bare-envelope ORDINARY_DISPATCH alias is withdrawn, and its only textual trace is the
withdrawal notice; no clause defines or applies it. All nineteen scheduling-bearing call
sites discharge the V2 contract explicitly (ten `ORDINARY_DISPATCH`, seven threaded, two
`POST_EPILOGUE`), and the two post-epilogue `ScheduleEvent` seats carry an explicit
`post_epilogue_context`. No call to any of the six scheduling procedures passes the pre-V2
`dispatch_envelope = dispatch_envelope` argument: there is **no residual pre-V2 call site**.
The pseudocode now matches, without exception, the "explicit at every call site" assertion
of the round-state-machine §3.10 V2 block and the terminology V2 addendum. V2 is fully
discharged across the specification.
