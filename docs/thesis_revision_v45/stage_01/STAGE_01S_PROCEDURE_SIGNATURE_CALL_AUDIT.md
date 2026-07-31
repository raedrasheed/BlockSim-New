# Stage 1S — Procedure Signature & Call-Site Conformance Audit

Scope: a **signature-and-call-site conformance check** for the Stage-1S procedures of
**PoCol** (with **the idle policy within PoCol** enabled) whose signatures changed. It verifies
that every caller passes the new arguments correctly and that no call site is stale. Source of
truth (read-only, not modified): `STAGE_01_PROTOCOL_PSEUDOCODE.md`. Line numbers below are that
file's. This is **documentation only** — no behaviour, feature, or model is added; these are
signature/threading corrections. The A1 baseline **8.420833333 kWh is UNCHANGED** by this audit.

---

## 1. `ApplyMinerStateTransition(MinerID, old_state, new_state, transition_envelope, reason, assignment_ref, candidate_id, propagation_id)` — S1

Definition: §0.9, line 845. S1 collapses R3's decomposed identity inputs into ONE
`transition_envelope` object carrying `{envelope_namespace, event_time, delta_cycle, event_seq,
hook_id}`. Acceptance rule (lines 857–861): **every** call site passes exactly
`transition_envelope = dispatch_envelope` — no decomposed identity args, no omitted
namespace/hook, no positional `now`. `Grep "CALL ApplyMinerStateTransition"` returns **exactly 14
direct call sites**:

| # | Line | Caller (procedure) | Edge | transition_envelope arg | OK? |
|---|------|--------------------|------|-------------------------|-----|
| 1 | 981  | StartWake | from_state → WAKING | `= dispatch_envelope` | ✅ |
| 2 | 1027 | WakeCompleteEvent | WAKING → ACTIVE_HASHING | `= dispatch_envelope` | ✅ |
| 3 | 1037 | WakeCompleteEvent | WAKING → OFFLINE | `= dispatch_envelope` | ✅ |
| 4 | 1504 | MinerRegister | NONE → REGISTERED | `= dispatch_envelope` | ✅ |
| 5 | 1507 | MinerRegister (OPTIONALLY) | REGISTERED → RESERVE | `= dispatch_envelope` | ✅ |
| 6 | 1696 | ExhaustionAdjudicate | ACTIVE_HASHING → EXHAUSTED_PENDING | `= dispatch_envelope` | ✅ |
| 7 | 1781 | EnterLowPowerListen | from_state → LOW_POWER_LISTEN | `= dispatch_envelope` | ✅ |
| 8 | 1865 | AdversarialParticipationChangeEvent | ACTIVE_HASHING → OFFLINE | `= dispatch_envelope` | ✅ |
| 9 | 1884 | AdversarialParticipationChangeEvent | OFFLINE → REGISTERED | `= dispatch_envelope` | ✅ |
| 10 | 2838 | LeaseExpiry | WAKING → OFFLINE | `= dispatch_envelope` | ✅ |
| 11 | 3450 | CloseRoundAssignments | EXHAUSTED_PENDING → LOW_POWER_LISTEN | `= dispatch_envelope` | ✅ |
| 12 | 3466 | CloseRoundAssignments | WAKING → OFFLINE | `= dispatch_envelope` | ✅ |
| 13 | 3580 | CloseTemplateAssignments | EXHAUSTED_PENDING → LOW_POWER_LISTEN | `= dispatch_envelope` | ✅ |
| 14 | 3590 | CloseTemplateAssignments | WAKING → OFFLINE | `= dispatch_envelope` | ✅ |

All 14 additionally pass `reason`, `assignment_ref`, and BOTH `candidate_id`/`propagation_id`
(non-null only for the candidate-triggered pause at line 1781, null elsewhere per J3). No site
decomposes identity, omits the namespace/hook (both travel inside `dispatch_envelope`), or reads
an ambient `now`/`event_seq`. **Conformant.**

---

## 2. `CompleteSecurityRecovery(RoundContext, dispatch_envelope, episode, decision_id, RecoveryOutcome, bound_census_version)` — S3

Definition: line 2546 (INTERNAL branch dispatch, called ONLY by
ApplyRecoveryCompletionAfterEpilogue).

| Signature (6 args) | Sole caller | Args passed | OK? |
|--------------------|-------------|-------------|-----|
| RoundContext, dispatch_envelope, episode, decision_id, RecoveryOutcome, bound_census_version | ApplyRecoveryCompletionAfterEpilogue (line 2504) | `(RoundContext, D.due_dispatch_envelope, episode, decision_id, D.outcome, D.bound_census_version)` | ✅ all 6 |

The caller then branches on `disposition.kind`: **SUCCESS** (line 2506 → mark APPLIED, finalise,
clear episode), **DEFERRED** (line 2514 → decision stays APPLYING, episode active), **FAILED**
(line 2521 → APPLY_FAILED/HORIZON_DEFERRED, episode preserved). All three `disposition.kind`
values are handled. **Conformant.**

---

## 3. `RoundAbort(RoundContext, reason, dispatch_envelope, recovery_finalising = false)` — S4

Definition: line 3671 (`recovery_finalising` defaults to `false`, line 3672).

| Caller | Line | recovery_finalising passed | OK? |
|--------|------|----------------------------|-----|
| CompleteSecurityRecovery branch D (floor_unrecoverable) | 2562 | `recovery_finalising = true` | ✅ |
| RecoveryAssignmentContinuationEvent install-fail abort | 2669 | `recovery_finalising = true` | ✅ |
| FullRangeExhaustNoSolution (false_exhaustion_claim) | 3542 | omitted → default `false` | ✅ |
| FullRangeExhaustNoSolution (exhausted_no_solution) | 3549 | omitted → default `false` | ✅ |

The two recovery-finalising aborts pass `true` (so their closure SKIPS the S4 terminal cleanup and
the caller finalises the episode); every other abort uses the default `false`. **Conformant.**

---

## 4. `CloseRoundAssignments(..., recovery_finalising = false)` — S4

Definition: line 3414 (`recovery_finalising = false`, line 3416); the S4 terminal cleanup
`CancelActiveRecoveryEpisode` fires only when `NOT recovery_finalising` (line 3491).

| Caller | Line | recovery_finalising passed | S4 cleanup fires? | OK? |
|--------|------|----------------------------|-------------------|-----|
| RoundAbort | 3700 | `= recovery_finalising` (threaded through) | iff caller's flag false | ✅ |
| ValidBlockAccept (ROUND_ACCEPTED) | 3401 | omitted → default `false` | yes | ✅ |
| CloseRoundAtHorizon (ROUND_ABORTED) | 3802 | omitted → default `false` | yes | ✅ |

RoundAbort forwards its own `recovery_finalising` unchanged; ValidBlockAccept and
CloseRoundAtHorizon use the default, so the S4 cleanup fires for those closures. **Conformant.**

---

## 5. `ScheduleEvent(..., post_epilogue_context = null)` — S7

Definition: line 406 (`post_epilogue_context = null`, line 409). `Grep "CALL ScheduleEvent"`
returns 11 call sites.

| Caller | Line | post_epilogue_context passed | OK? |
|--------|------|------------------------------|-----|
| CompleteSecurityRecovery branch-C continuation seat | 2597–2603 | `= pctx` (a PostEpilogueSchedulingContext, §0.7e) | ✅ |
| All 10 other ScheduleEvent calls | — | omitted → default `null` | ✅ |

Exactly one call — the branch-C `RecoveryAssignmentContinuationEvent` seat — carries a
`PostEpilogueSchedulingContext`; the guard at lines 431–433 enforces a strictly-later
`target_event_time` and derives `delta_cycle = 0`. All other calls omit it (default null), which
the precondition at line 416 requires ("no other call may"). **Conformant.**

---

## 6. `SettleSecurityCensusDirty(RoundContext, event_time, settlement_kind)` — S5

Definition: line 825 (the SOLE clearer of `security_census_dirty[event_time]`;
`settlement_kind ∈ {PRIMARY_EPILOGUE, POST_RECOVERY_APPLICATION}`).

| Caller | Line | settlement_kind passed | OK? |
|--------|------|------------------------|-----|
| FinalizeEventTimeSecurityCensus | 2009 | `PRIMARY_EPILOGUE` | ✅ |
| FinalizePostRecoveryApplicationState | 2716 | `POST_RECOVERY_APPLICATION` | ✅ |

Exactly the two declared callers, each with the matching `settlement_kind` (lines 827–829). No
other procedure clears the flag. **Conformant.**

---

## Call-graph delta note

The two procedures **new** to Stage-1S are both defined and reachably called — no dangling call:

- **`SettleSecurityCensusDirty`** — defined line 825; called at lines 2009 and 2716 (the two
  settlement paths above).
- **`CancelActiveRecoveryEpisode`** — defined line 2161; called at line 3492 (CloseRoundAssignments
  S4 terminal cleanup, guarded by `NOT recovery_finalising`).

A mechanical `Grep` for `CALL <Name>` against every changed signature resolves each call site to a
live `PROCEDURE` definition. The only apparent "extra" mentions of these names are **prose false
positives** — narrative NOTE/comment references (e.g. lines 696, 823, 2405, 2418, 2541, 2560) that
are not `CALL` edges. There are **no stale call sites and no dangling calls**.

## Result

Every Stage-1S signature change is matched by conformant call sites: all 14
`ApplyMinerStateTransition` callers thread `transition_envelope = dispatch_envelope` with no
decomposed identity and no omitted namespace/hook; `CompleteSecurityRecovery`'s sole caller passes
all six arguments and branches on `disposition.kind ∈ {SUCCESS, DEFERRED, FAILED}`; `recovery_finalising`
is passed `true` at exactly the two recovery-finalising aborts and defaults `false` elsewhere, and
`RoundAbort` threads it into `CloseRoundAssignments` while `ValidBlockAccept`/`CloseRoundAtHorizon`
take the default so the S4 cleanup fires; the single `post_epilogue_context` seat is the branch-C
continuation and every other `ScheduleEvent` call omits it; and `SettleSecurityCensusDirty` has
exactly its two declared callers with the correct `settlement_kind`. The two new procedures are
defined and called with no dangling edges. These are signature/threading corrections to **PoCol**
with **the idle policy within PoCol** only — documentation-level, adding no feature — and the A1
baseline **8.420833333 kWh remains UNCHANGED**.

The prohibited rebranded-algorithm-name variants are not used anywhere in this document.
