# Stage 1M — Scheduler Microphase Audit (M5)

A structural audit of the Stage-1M correction **M5** (every enqueue conforms to `ScheduleEvent` with
an EXPLICIT microphase; deterministic event-producing loops) in the **PoCol** protocol pseudocode
(`STAGE_01_PROTOCOL_PSEUDOCODE.md`). M5 adds a canonical event-type → microphase mapping (§0.7g) and
requires that EVERY operational enqueue — being a `ScheduleEvent` call, or the `SCHEDULE event E(...)
AT event_time = τ, microphase = m` shorthand for one (§0.7e) — supply an explicit `target_microphase`;
no enqueue omits it. Every loop that CREATES or CANCELS events is stably sorted over intrinsic keys
BEFORE `ScheduleEvent` assigns the monotonic `event_creation_seq` (J4/G7). This document is
documentation only; it audits wording and control structure, describes only the idle policy within
PoCol, introduces no new consensus feature, and claims **no** security, fairness, energy, or incentive
property. The A1 baseline (`8.420833333 kWh`) is unchanged; any energy change is attributable ONLY to
reduced active power-time.

---

## 1. The corrected-away problem

- **Before M5.** The target microphase of an event was fixed by the same-timestamp contract (§0.7,
  §21), but the enqueue call sites did not all state it. Three sites were written as bare `SCHEDULE
  event E(...) AT …` expressions that named an `event_time` but no microphase: the `HashWorkEvent`
  unit (`ScheduleNextHashWork`), the `CertificateArrival` / `BlockAcceptancePoint` events
  (`ScheduleSolutionPropagation`), and the candidate-scoped `ResumeFromPause` events
  (`HandlePropagationFailure`). The target microphase was therefore implicit at those sites, and two
  event-producing loops (`TemplateRefresh`'s eligible set and the two closure loops) did not state a
  deterministic iteration order, so the `event_creation_seq` those loops assigned could depend on
  data-structure iteration order.
- **After M5.** §0.7g states the canonical event-type → microphase mapping and the norm that *"EVERY
  operational enqueue is a `ScheduleEvent` call (or the `SCHEDULE event E(...) AT event_time = τ,
  microphase = m` shorthand for one, §0.7e), and it MUST supply an EXPLICIT `target_microphase` — no
  enqueue omits it."* The three bare `SCHEDULE` expressions are converted to explicit `CALL
  ScheduleEvent(...)` calls, each supplying `target_microphase` from the mapping. `TemplateRefresh`'s
  eligible loop and both closure loops now sort in a stable order over intrinsic keys before
  `ScheduleEvent` assigns `event_creation_seq`. §0.7g closes: *"Every loop that CREATES or CANCELS
  events iterates in a STABLE order (by `MinerID`, then `CandidateID`) BEFORE `ScheduleEvent` assigns
  the monotonic `event_creation_seq` (J4/G7), so the seq order is reproducible."*

## 2. Mechanism

### 2.1 The canonical event-type → microphase mapping (§0.7g)

M5 adds the fixed mapping. The ordinals are the same-timestamp inter-type priorities of §21 (a lower
ordinal fires first at a shared `event_time`); a lower ordinal is not a claim, only the queue order.

| Event type | Target microphase | §21 priority |
|-----------|-------------------|:-:|
| `BlockAcceptancePoint` (full-block arrival, register-only) | `FULL_BLOCK_ARRIVAL` | 5 |
| `CertificateArrival` | `CERTIFICATE_ARRIVAL` | 6 |
| `HashWorkEvent` (hash unit; may emit discovery/range-completion) | `HASH_WORK` | 7–9 |
| `LeaseExpiry` | `LEASE_EXPIRY` | 10 |
| `WakeCompleteEvent` | `WAKE_COMPLETE` | 11 |
| `ResumeFromPause` | `RESUME` | 12 |
| `AdversarialParticipationChangeEvent` | `PARTICIPATION_CHANGE` | 13a |
| `ActiveHashRateUpdate` / periodic monitoring | `MONITORING` | 13 |

The mapping covers `HashWorkEvent`, `CertificateArrival`, `BlockAcceptancePoint`, `ResumeFromPause`,
`WakeCompleteEvent`, adversarial participation (`AdversarialParticipationChangeEvent`), lease expiry
(`LeaseExpiry`), and monitoring (`ActiveHashRateUpdate` / periodic monitoring). The event-time
security decision is NOT a queued microphase — it is the epilogue
`FinalizeEventTimeSecurityCensus → SecurityFloorEvaluate` (I-01/I-02), so it has no mapping entry.
`AcceptanceBatchFinalize` (microphase 4) is enqueued once per (timestamp, acceptance point) by
`BlockAcceptancePoint`; round-closure/refresh transitions are the atomic RESULT of dispatched handlers
(§21 phases 1–4), not independently enqueued miner events. These ordinals match the §21 inter-type
priority order (`BlockAcceptancePoint` 5, `CertificateArrival` 6, solution/range/exhaustion via
`HashWorkEvent` 7–9, `LeaseExpiry` 10, `WakeCompleteEvent` 11, `ResumeFromPause` 12, monitoring 13).

### 2.2 The three converted enqueues

Each previously-bare `SCHEDULE` is now an explicit `CALL ScheduleEvent(...)` supplying its mapped
`target_microphase`:

```
# ScheduleNextHashWork (§5): HashWorkEvent at HASH_WORK
CALL ScheduleEvent(EQ, RoundContext, HashWorkEvent,
                   target_event_time = now + modeled_hash_step_time, target_microphase = HASH_WORK,
                   {MinerID, AssignmentID(assignment), assignment_version(assignment),
                    RoundID, TemplateID, from_cursor})   # M5: explicit microphase

# ScheduleSolutionPropagation (§16b): CertificateArrival at CERTIFICATE_ARRIVAL, BlockAcceptancePoint at FULL_BLOCK_ARRIVAL
ev <- CALL ScheduleEvent(EQ, RoundContext, CertificateArrival,
                         target_event_time = now + cert_delay(r), target_microphase = CERTIFICATE_ARRIVAL,
                         {r, ... CandidateID, PropagationID})           # M5: explicit microphase
SET block_arrival_event(cpc) <- CALL ScheduleEvent(EQ, RoundContext, BlockAcceptancePoint,
                         target_event_time = now + block_delay, target_microphase = FULL_BLOCK_ARRIVAL,
                         {... CandidateID, PropagationID, outcome})     # M5: explicit microphase

# HandlePropagationFailure (§16d-bis): ResumeFromPause at RESUME
CALL ScheduleEvent(EQ, RoundContext, ResumeFromPause,
                   target_event_time = dispatch_envelope.event_time, target_microphase = RESUME,
                   {M, trigger = failure_reason, pause_cause_candidate_id, pause_cause_propagation_id})   # M5
```

`StartWake` (§0.10) already schedules `WakeCompleteEvent` through `ScheduleEvent` with
`target_microphase = WAKE_COMPLETE` on both the positive-latency branch (`target_event_time = now +
wake_latency`) and the zero-latency H5 branch (`target_event_time = now`). As in §0.7e, the caller
supplies only `target_event_time` + `target_microphase`; `ScheduleEvent` alone derives `delta_cycle`
and assigns `seq`.

## 3. Call-site table — every enqueue supplies a target microphase (property 1)

Enumerating every real enqueue (`CALL ScheduleEvent`) in the document. A repository-wide search for
`CALL ScheduleEvent` returns exactly the six sites below (plus the §0.7e/§0.7g normative prose), and a
search for `SCHEDULE event` returns only the two definitional references in §0.7e and §0.7g — no bare
`SCHEDULE` enqueue remains.

| # | Procedure (§) | Event type | `target_microphase` | `target_event_time` |
|---|---|---|---|---|
| E1 | `StartWake` §0.10 (positive latency) | `WakeCompleteEvent` | `WAKE_COMPLETE` | `now + wake_latency` |
| E2 | `StartWake` §0.10 (zero latency, H5) | `WakeCompleteEvent` | `WAKE_COMPLETE` | `now` |
| E3 | `ScheduleNextHashWork` §5 | `HashWorkEvent` | `HASH_WORK` | `now + modeled_hash_step_time` |
| E4 | `ScheduleSolutionPropagation` §16b | `CertificateArrival` | `CERTIFICATE_ARRIVAL` | `now + cert_delay(r)` |
| E5 | `ScheduleSolutionPropagation` §16b | `BlockAcceptancePoint` | `FULL_BLOCK_ARRIVAL` | `now + block_delay` |
| E6 | `HandlePropagationFailure` §16d-bis | `ResumeFromPause` | `RESUME` | `dispatch_envelope.event_time` |

Every row supplies an explicit `target_microphase`; NONE omits it, and each value equals the §0.7g
mapping for that event type. There is no seventh enqueue path: §0.7e establishes exactly ONE enqueue
interface (`ScheduleEvent`), and every `SCHEDULE event E(...) AT event_time = τ, microphase = m` is
shorthand for a call to it.

## 4. Loop table — every event-producing loop is deterministically sorted (property 2)

The event-creating / event-cancelling loops now iterate in a stable sorted order over intrinsic keys
BEFORE `ScheduleEvent` assigns `event_creation_seq`, so the resulting queue order is reproducible
(§0.7g closing rule; §0.7a/G7).

| # | Loop (procedure §) | Stable sort key | Events produced / cancelled |
|---|---|---|---|
| P1 | `TemplateRefresh` §19 (eligible loop) | `SORT(eligible BY MinerID ascending)` | `StartWake` → `WakeCompleteEvent` per eligible miner |
| P2 | `CloseRoundAssignments` §17a | `SORT BY (holder(X) MinerID ascending, AssignmentID(X) ascending)` | `EnterLowPowerListen` / `ApplyMinerStateTransition` / wake cancellation per open assignment |
| P3 | `CloseTemplateAssignments` §19 | `SORT BY (holder(X) MinerID ascending, AssignmentID(X) ascending)` | `EnterLowPowerListen` / `ApplyMinerStateTransition` / wake cancellation per old-template assignment |
| P4 | `ScheduleSolutionPropagation` §16b (recipient loop) | `SORT({ m in current miners : m != finder } BY MinerID ascending)` | `CertificateArrival` per recipient |
| P5 | `HandlePropagationFailure` §16d-bis (resume loop) | `SORT({ m : PAUSED, both ids match } BY MinerID ascending)` | `ResumeFromPause` per matching paused miner |

The same stable-ordering discipline holds at the other event-cancelling / candidate loops that M5's
closing rule reaches by `CandidateID`: `PrepareParticipantsForNewRound` §12
(`SORT(eligible miners BY MinerID ascending)`), `AcceptanceBatchFinalize` §16d (`SORT … BY
a.CandidateID ascending`), `ValidBlockAccept` §17 (`SORT(active_propagation_set BY CandidateID
ascending)`), `CloseTemplateAssignments`'s context loop §19 (`SORT(active_propagation_set BY
CandidateID ascending)`), and `RoundAbort` §20 (`SORT(active_propagation_set BY CandidateID
ascending)`). No ordering depends on hash-map / set iteration order (§0.7a).

## 5. Acceptance-style PASS checklist

| # | Check | Result | Ground |
|---|---|---|---|
| C1 | Property 1 — every enqueue operation supplies a target microphase | PASS | §0.7g norm; call-site table E1–E6 (§3) |
| C2 | The three previously-bare `SCHEDULE` enqueues are converted to explicit `ScheduleEvent` calls with a `target_microphase` | PASS | `ScheduleNextHashWork` §5 (E3); `ScheduleSolutionPropagation` §16b (E4/E5); `HandlePropagationFailure` §16d-bis (E6) |
| C3 | `StartWake`'s `WakeCompleteEvent` supplies `WAKE_COMPLETE` on both branches | PASS | §0.10 (E1/E2) |
| C4 | No bare `SCHEDULE event …` enqueue remains; exactly six `CALL ScheduleEvent` sites | PASS | `SCHEDULE event` only in §0.7e/§0.7g prose; `CALL ScheduleEvent` = E1–E6 (§3) |
| C5 | Property 2 — every event-producing loop is deterministically sorted | PASS | loop table P1–P5 (§4); §0.7g closing rule |
| C6 | `TemplateRefresh` eligible loop stably sorted by `MinerID` | PASS | §19 (P1) |
| C7 | `CloseRoundAssignments` / `CloseTemplateAssignments` closure loops stably sorted by (holder `MinerID`, `AssignmentID`) | PASS | §17a (P2); §19 (P3) |
| C8 | `ScheduleSolutionPropagation` recipient loop and `HandlePropagationFailure` resume loop stably sorted by `MinerID` | PASS | §16b (P4); §16d-bis (P5) |
| C9 | Loops sort BEFORE `ScheduleEvent` assigns `event_creation_seq` (J4/G7) | PASS | §0.7g closing rule; §0.7a |
| C10 | Property 3 — the mapping covers `HashWorkEvent`, `CertificateArrival`, `BlockAcceptancePoint`, `ResumeFromPause`, `WakeCompleteEvent`, adversarial participation, lease expiry, monitoring | PASS | §0.7g table (§2.1) |
| C11 | The security-floor decision has NO mapping entry (it is the I-01/I-02 epilogue, not a queued microphase) | PASS | §0.7g; §0.7d |
| C12 | The mapped ordinals match the §21 inter-type priority order | PASS | §0.7g; §21 |
| C13 | A1 baseline unchanged; no new consensus feature; no property claimed; only the idle policy within PoCol described | PASS | A1 = 8.420833333 kWh; §0 |

---

## Result

**SCHEDULER MICROPHASE AUDIT (Stage 1M): PASS** — M5 adds the canonical event-type → microphase
mapping (§0.7g) covering `BlockAcceptancePoint` (`FULL_BLOCK_ARRIVAL`), `CertificateArrival`
(`CERTIFICATE_ARRIVAL`), `HashWorkEvent` (`HASH_WORK`), `LeaseExpiry` (`LEASE_EXPIRY`),
`WakeCompleteEvent` (`WAKE_COMPLETE`), `ResumeFromPause` (`RESUME`),
`AdversarialParticipationChangeEvent` (`PARTICIPATION_CHANGE`), and `ActiveHashRateUpdate` / periodic
monitoring (`MONITORING`), with the security-floor decision left out as the I-01/I-02 epilogue. All
six real enqueues — `StartWake`'s `WakeCompleteEvent` on both the positive- and zero-latency branches
(§0.10), `ScheduleNextHashWork`'s `HashWorkEvent` (§5), `ScheduleSolutionPropagation`'s
`CertificateArrival` and `BlockAcceptancePoint` (§16b), and `HandlePropagationFailure`'s
`ResumeFromPause` (§16d-bis) — are `ScheduleEvent` calls supplying an explicit `target_microphase`, and
NONE omits it (property 1). The three previously-bare `SCHEDULE` expressions are converted, and every
event-producing loop — `TemplateRefresh`'s eligible loop (§19), the `CloseRoundAssignments` (§17a) and
`CloseTemplateAssignments` (§19) closure loops, and the `ScheduleSolutionPropagation` recipient (§16b)
and `HandlePropagationFailure` resume (§16d-bis) loops — is stably sorted over intrinsic keys before
`ScheduleEvent` assigns `event_creation_seq` (property 2; §0.7g/J4/G7) — leaving the A1 baseline
(8.420833333 kWh) unchanged, with no new consensus feature and no property claimed, describing only the
idle policy within PoCol.
