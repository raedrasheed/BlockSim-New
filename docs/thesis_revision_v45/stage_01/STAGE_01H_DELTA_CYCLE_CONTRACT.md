# Stage 1H — Delta-Cycle Contract (H2)

Normative specification for correction **H2** (same-`event_time` causal ordering). This is the full
contract that `STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.7-H2 points to ("The full contract, worked
examples, and the required-race table are in `STAGE_01H_DELTA_CYCLE_CONTRACT.md`"). It **EXTENDS** the
frozen Stage-1G microphase spec `STAGE_01G_EVENT_MICROPHASE_SPEC.md` (which is NOT modified here) with
one added ordering coordinate, `delta_cycle`, that resolves same-timestamp events created *inside*
handlers. It is documentation only; it describes **PoCol** with **the idle policy within PoCol**
enabled and claims **no property** (no energy, security, fairness, or incentive claim) beyond the
causal-consistency structure defined here. This is a Stage-1 specification-only causal-consistency
lock; no new consensus feature is introduced.

The accepted A1 baseline is `8.420833333 kWh` and is UNCHANGED; any energy reduction is attributable
ONLY to reduced active power-time. No numeric result is asserted here.

## 1. Event envelope and total order (H2)

Every scheduled event carries the immutable envelope (`STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.2, F1
extended in H2):

    { event_type, event_time, delta_cycle, microphase, RoundID, TemplateID,
      CandidateID?, PropagationID?, MinerID?, AssignmentID?, assignment_version?, seq }

Events are dispatched by the **total order key**

    (event_time, delta_cycle, microphase, stable_tie_key, seq)     stable_tie_key = (CandidateID, MinerID, AssignmentID)

| Field | Role |
|-------|------|
| `event_time` | Simulated wall-clock instant the event fires. Primary sort key; the loop advances monotonically over distinct `event_time`s. |
| `delta_cycle` | The causal **generation** within one `event_time` (H2). Counts how many completed passes over the microphase ladder precede this event *at the same timestamp*. New `event_time`s start numbering at `0`. |
| `microphase` | The target microphase (§0.7 / §2 of the G5 spec) into which this event is dispatched within its `delta_cycle`. |
| `stable_tie_key` | `(CandidateID, MinerID, AssignmentID)` — the deterministic intra-microphase order over intrinsic keys (G7, §0.7a). Never data-structure iteration order. |
| `seq` | Strictly monotonic per-run creation counter, assigned ONLY after the deterministic key order is established; the final tie-break (G7). |

**Why `delta_cycle` sits between `event_time` and `microphase`.** Two events with the same
`event_time` but created in different causal generations must not interleave by microphase. If the key
were `(event_time, microphase, …)`, a generation-`k+1` event whose target microphase is *earlier* than
a generation-`k` event would sort ahead of it and execute "before" its own cause — backward causal
travel inside one timestamp. Placing `delta_cycle` immediately after `event_time` makes generation the
dominant tie-break within a timestamp: every microphase of cycle `k` is fully drained before any event
of cycle `k+1`, so a later-generated event can never preempt an earlier generation's microphase. A
propagation context is never identified by `RoundID` alone (§0.2).

## 2. The delta-cycle rule (no backward travel within a timestamp)

A handler running in microphase `m` of `(event_time = t, delta_cycle = k)` may create same-`event_time`
events. To keep scheduling **causally forward** it obeys (§0.7-H2):

1. an event whose target `microphase > m` is scheduled in the CURRENT `delta_cycle = k`;
2. an event whose target `microphase <= m` (same or earlier microphase) is scheduled in
   `delta_cycle = k + 1` at that microphase — **never backward into a completed phase of cycle `k`**;
3. the loop completes ALL microphases of `delta_cycle k` before processing any event of
   `delta_cycle k + 1` at the same `event_time`;
4. no event may travel backward into a completed `delta_cycle`.

A new `event_time` (any event scheduled at a strictly future timestamp) starts `delta_cycle` numbering
at `0`. Within a microphase, ties break by `(CandidateID, MinerID, AssignmentID, seq)`, NEVER by
data-structure iteration order (G7, §0.7a). The rule is total and closed: for any `(m, m')` pair the
placement is uniquely determined, so there is no ambiguous and no backward outcome (§6).

## 3. The microphase ladder this contract extends

The per-`event_time` microphase order is defined by `STAGE_01G_EVENT_MICROPHASE_SPEC.md` §2 and
restated in `STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.7. H2 does not change the ladder; it adds
`delta_cycle` so the ladder is re-run, in full and forward, for each causal generation at one
`event_time`.

| Phase | Runs (per `(event_time, delta_cycle)`) |
|-------|----------------------------------------|
| **1** | Terminal abort / previously-committed closure: `RoundAbort` -> `CloseRoundAssignments(ROUND_ABORTED)`; an already-committed `ROUND_ACCEPTED` closure. |
| **2** | Template invalidation / refresh: `TemplateRefresh` / `CloseTemplateAssignments`. |
| **3** | Collect ALL full-block arrivals: each `BlockAcceptancePoint` (§16d) ONLY registers into `acceptance_batch_registry[(timestamp, acceptance_point)]` (sets `PENDING_ACCEPTANCE`, records `acceptance_timestamp`) and returns — it never accepts, arbitrates, or closes. |
| **4** | `AcceptanceBatchFinalize` (§16e) EXACTLY ONCE per `(timestamp, acceptance_point)`: validate all collected candidates, select the winner (smallest `candidate_hash`, then smallest `MinerID`), `ValidBlockAccept` commits acceptance and closes the round ATOMICALLY. |
| **5** | The SINGLE settled-census evaluation: `FinalizeTimestampSecurityCensus` -> `SecurityFloorEvaluate` (§9), terminal/source-guarded (G10/H4). |
| **6+** | Certificate arrivals; solution discovery (`HashWorkEvent` hit); range completion; reported exhaustion; lease expiry; wake completion (`WakeCompleteEvent`, microphase `WAKE_COMPLETE`); resume (`ResumeFromPause`); periodic monitoring. |

Round-acceptance closure is the atomic result of `AcceptanceBatchFinalize` (phase 4), not an
independent preceding event.

**Superseded artifact.** The frozen flat `STAGE_01F_EVENT_PRIORITY_TABLE.md` is **NO LONGER
authoritative**: it is a historical Stage-1F artifact, superseded by the microphase model
(G5 / `STAGE_01G_EVENT_MICROPHASE_SPEC.md`) and this H2 delta-cycle extension (H1). Where it differs
from the microphase + delta-cycle contract, this contract governs (§0.7, §21).

## 4. Governed cases

Every same-`event_time` event created inside another handler is governed by §2. The named cases:

| Case | Creating site | Target microphase | Lands in |
|------|---------------|-------------------|----------|
| **Settled-census evaluation (H3)** | `ApplyMinerStateTransition` (§0.9) sets `security_evaluation_required[(event_time, current_delta_cycle)]` when a boundary changed the `ACTIVE_HASHING` census; NO per-transition floor decision. `FinalizeTimestampSecurityCensus(RoundContext, event_time, delta_cycle)` (§9) is the microphase-5 event. | 5 | If the flagging boundary occurred in microphase `m < 5`: microphase 5 of the SAME cycle `k`. If it occurred in a microphase `m >= 5` (e.g. a 6+ wake/resume boundary): microphase 5 of cycle `k+1` (rule 2 — cycle `k`'s phase 5 is already complete). Exactly one evaluation per settled `(event_time, delta_cycle)`. |
| **Zero-latency wake (H5)** | `StartWake` (§0.10) schedules `WakeCompleteEvent`. With `wake_latency = 0` it schedules `AT event_time = now, delta_cycle = current_delta_cycle + 1, microphase = WAKE_COMPLETE`. | `WAKE_COMPLETE` (6+) | `(now, k+1, WAKE_COMPLETE)` — never backward into a completed phase of cycle `k`. A positive latency instead schedules a future `event_time` at `delta_cycle = 0` (fresh timestamp). |
| **Resume from pause** | `ResumeFromPause` (§16a), scheduled by `HandlePropagationFailure` (§16d-bis) or from an adversarial reactivation, then `StartWake` -> `WakeCompleteEvent`. | `Resume` (6+) | If the failure handler ran in microphase `m < Resume`: cycle `k`. If it ran at a 6+ microphase (certificate/timeout): cycle `k+1` (the resumes "re-activate miners in a later delta-cycle", §16d-bis). |
| **Candidate-failure cleanup** | `HandlePropagationFailure` (§16d-bis) cancels the candidate's events, schedules candidate-scoped `ResumeFromPause`s, and sets `security_evaluation_required[(now, current_delta_cycle)]`. | per created event | Each created resume follows the row above; the census flag is drained by the single microphase-5 `FinalizeTimestampSecurityCensus` for that settled cycle. |
| **Any same-`event_time` event created inside another handler** | any handler | any `m'` | `m' > m` -> cycle `k`; `m' <= m` -> cycle `k+1` (§2). |

## 5. Worked examples

**(a) Three same-timestamp `ACTIVE_HASHING` exits — one census evaluation.** Three miners leave
`ACTIVE_HASHING` at `(event_time = t, delta_cycle = k)` (e.g. `AdversarialParticipationChangeEvent(exit)`
or `EnterLowPowerListen`). Each routes through `ApplyMinerStateTransition` (§0.9): it recomputes the
census, `RECORD intermediate_census_for_audit(t, k, …)` (audit only), and — because each changed the
`ACTIVE_HASHING` census — sets `security_evaluation_required[(t, k)] <- true`. NO transition schedules
its own `SecurityFloorEvaluate`. In microphase 5 of `(t, k)`, `FinalizeTimestampSecurityCensus(RoundContext,
t, k)` runs EXACTLY ONCE: it reads the FINAL settled census (after all three transitions), clears the
flag, and calls `SecurityFloorEvaluate` at most once with `(RoundID, TemplateID, state_version)`. The
first of the three transitions never triggers recovery from an intermediate census (H3; cf. TV52).

**(b) Zero-latency wake initiated in a late microphase.** `StartWake` (§0.10) runs at
`(event_time = now, delta_cycle = k)` in a 6+ microphase, and `wake_latency = 0` (a permitted
experimental value). The handler applies `-> WAKING` via `ApplyMinerStateTransition`, then, because
latency is zero, schedules `WakeCompleteEvent AT event_time = now, delta_cycle = k + 1, microphase =
WAKE_COMPLETE`. Since `WAKE_COMPLETE` is at or before the creating microphase (rule 2), it lands in the
NEXT cycle at `(now, k+1, WAKE_COMPLETE)` — never backward into a completed phase of cycle `k` (H5;
cf. TV54).

**(c) A microphase-6 handler that schedules another microphase-6 event.** A handler in microphase 6 of
`(t, k)` creates an event whose target microphase is also 6 (`m' = 6 <= m = 6`). By rule 2 it is
scheduled in `delta_cycle k + 1` at microphase 6, i.e. `(t, k+1, 6)`. It fires strictly after every
event of `(t, k)` and before any event of `(t, k+2)`. Had its target been microphase 8 (`> 6`), it
would instead land in the current cycle at `(t, k, 8)` (rule 1).

## 6. Required-race table

Same-`event_time` races, by creating microphase `m` vs target microphase `m'`, with the deterministic
resulting `(delta_cycle, microphase)`. `k` is the creating handler's `delta_cycle`. There is never an
ambiguous or backward placement.

| Creating handler at `(t, k, m)` | Created event's target `m'` | Rule | Deterministic placement |
|---------------------------------|-----------------------------|------|-------------------------|
| Miner-state boundary in `m = 3` (phase-3 registration side effect) flags census | 5 (`FinalizeTimestampSecurityCensus`) | `m' > m` -> current cycle | `(t, k, 5)` |
| Miner-state boundary in `m = 4` (closure-driven transition) flags census | 5 | `m' > m` | `(t, k, 5)` |
| Miner-state boundary in `m = 6+` (wake/resume/adversarial) flags census | 5 | `m' <= m` -> next cycle | `(t, k+1, 5)` |
| `StartWake` in any `m`, `wake_latency = 0` | `WAKE_COMPLETE` (6+) | forced next cycle (H5) | `(t, k+1, WAKE_COMPLETE)` |
| `StartWake` in any `m`, `wake_latency > 0` | `WAKE_COMPLETE` (6+) | new `event_time` | `(t + wake_latency, 0, WAKE_COMPLETE)` |
| `HandlePropagationFailure` in `m = 4` (via `AcceptanceBatchFinalize`) schedules `ResumeFromPause` | `Resume` (6+) | `m' > m` | `(t, k, Resume)` |
| `HandlePropagationFailure` in `m = 6+` (via certificate/timeout) schedules `ResumeFromPause` | `Resume` (6+) | `m' <= m` | `(t, k+1, Resume)` |
| Any handler in `m` schedules an event with `m' > m` | `m' > m` | rule 1 | `(t, k, m')` |
| Any handler in `m` schedules an event with `m' <= m` | `m' <= m` | rule 2 | `(t, k+1, m')` |
| Any handler schedules at a strictly future `event_time` | any | new timestamp | `(t' > t, 0, m')` |

## 7. Zero-latency wake determinism (H5)

`wake_latency = 0` is a permitted future experimental value; it never collapses the wake into a
synchronous, inline, or blocking call. `StartWake` (§0.10) is NON-BLOCKING and returns to the event
loop immediately (§0.1/F5); the miner reaches `ACTIVE_HASHING` only at its scheduled `WakeCompleteEvent`.
With zero latency that event is placed at `(now, current_delta_cycle + 1, WAKE_COMPLETE)`, so a resume
initiated after the wake microphase never travels backward into a completed phase (§2, rule 2).

The `WAKING` residency and its `P_wake * t_wake + E_transition` accounting path **always exist** (with
`t_wake = 0` in the zero-latency case). That path is owned SOLELY by `ApplyMinerStateTransition`'s
`residency_ledger` (H7/I19, §0.9): the `WAKING` interval is opened at `StartWake`'s `-> WAKING`
transition and closed at the `WakeCompleteEvent`'s `WAKING -> ACTIVE_HASHING` boundary, accruing
`P_wake * t_wake` once (a zero-duration interval when `t_wake = 0`), plus the one-shot `E_transition`
for the crossing (RangeAssign NOTE / D2, §4). No other procedure increments any `t_<state>`. Any energy
change is attributable ONLY to reduced active power-time; the A1 baseline `8.420833333 kWh` is unchanged
and no numeric result is asserted.

## 8. Naming and property discipline

The algorithm name is EXACTLY **PoCol**; the energy mechanism is described ONLY as **the idle policy
within PoCol**. The strings "PoCol-E", "Energy-Aware PoCol", and "Enhanced PoCol" are PROHIBITED and
are not used to denote this algorithm anywhere in the specification. This contract claims no energy,
security, fairness, or incentive property; it fixes only same-timestamp causal ordering.

---

**Result: DELTA-CYCLE CONTRACT (Stage 1H): PASS** — every same-`event_time` event created inside a
handler is placed by the total order `(event_time, delta_cycle, microphase, stable_tie_key, seq)` and
the delta-cycle rule (§0.7-H2) at a uniquely determined, causally forward `(delta_cycle, microphase)`;
no event travels backward into a completed microphase or delta-cycle; the ordering is deterministic and
reproducible across reruns (G7). No property is claimed.
