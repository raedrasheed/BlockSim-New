# Stage 1I — Event-Time Security Epilogue Spec (I-01 / I-02)

Normative specification for corrections **I-01** (event-time security epilogue) and **I-02** (explicit
quiescence + epilogue driver). This is the authoritative spec for the **relocation** of the single
security-floor decision from a per-`(event_time, delta_cycle)` microphase (the Stage-1H/H3
`FinalizeTimestampSecurityCensus` at microphase 5) to an **`event_time` epilogue**
`FinalizeEventTimeSecurityCensus(event_time) → SecurityFloorEvaluate`. It **EXTENDS** the frozen
Stage-1H delta-cycle contract `STAGE_01H_DELTA_CYCLE_CONTRACT.md` (which is NOT modified here): the H2
total order and the delta-cycle rule (§0.7-H2) are unchanged; I-01/I-02 only change *when and by what
key* the security decision is taken. It is documentation only; it describes **PoCol** with **the idle
policy within PoCol** enabled and claims **no property** beyond the execution-ordering structure defined
here. No new consensus feature is introduced.

The accepted A1 baseline is `8.420833333 kWh` and is UNCHANGED; any energy reduction is attributable
ONLY to reduced active power-time. No numeric result is asserted here.

## 1. The corrected-away problem (I-01)

Under the Stage-1H/H3 scheme the pending decision was flagged `security_evaluation_required[(event_time,
delta_cycle)]` and drained by a microphase-5 event `FinalizeTimestampSecurityCensus(RoundContext,
event_time, delta_cycle)` (STAGE_01H §3 phase 5, §4 row "Settled-census evaluation (H3)"). Keying the
pending decision by the *pair* `(event_time, delta_cycle)` admits two defects at one timestamp `t`:

| # | Failure mode | Cause under `(event_time, delta_cycle)` keying |
|---|--------------|------------------------------------------------|
| **A** | **Stranded dirty flag** | A census-changing boundary in a LATE microphase `m ≥ 5` of cycle `k` keys its decision to `(t, k+1)` (§0.7-H2 rule 2 — cycle `k`'s phase 5 is already complete). If no cycle-`k+1` event materialises, the microphase-5 event for `(t, k+1)` is never dispatched and the flag is STRANDED between delta-cycles — a later delta-cycle carries a *different key*, so the decision is silently missed. |
| **B** | **Intermediate-census trigger** | Distinct keys `(t, k)`, `(t, k+1)`, `(t, k+2)` each own a separate microphase-5 evaluation, so an EARLY (intermediate) delta-cycle census can independently drive `HASHING → SECURITY_RECOVERY` before the FINAL census at `t` is known. |

Both defects share a root cause: the decision is bound to a *generation* within `t` rather than to `t`.

## 2. The correction (I-01): event-time keying + newest-wins overwrite

`ApplyMinerStateTransition` (§0.9) step **(7)** — "I-01 EVENT-TIME SECURITY BOOKKEEPING" — on every
boundary that changed the `ACTIVE_HASHING` census: recomputes `H_honest`/`H_adversarial`/`H_active`
and re-checks **I17** (step 6), `RECORD intermediate_census_for_audit(event_time, current_delta_cycle,
…)` **for audit only**, then

- `SET security_census_dirty[event_time] <- true` — keyed by **`event_time` ALONE** (never by
  `delta_cycle`), superseding the per-`(event_time, delta_cycle)` H3 flag;
- `SET latest_security_census[event_time] <- (H_active, H_honest, H_adversarial, q_adv)` — **OVERWRITES**
  with the NEWEST post-transition census (**newest wins**).

It **schedules no floor decision** and **keys nothing by the source `delta_cycle`**. Exactly one
`FinalizeEventTimeSecurityCensus(event_time)` (§9) then runs per `event_time`: it checks
`security_census_dirty[event_time]`, reads `latest_security_census[event_time]`, CLEARS the dirty flag,
and calls `SecurityFloorEvaluate` **at most once**, carrying `(RoundID, TemplateID, state_version)`
(§0.7c terminal-first + stale guard, I-05/G10). No intermediate delta-cycle census drives a transition.

## 3. Explicit quiescence and the epilogue driver (I-02)

`ProcessEventTime(event_time t)` (§0.7d) is the sole driver that advances simulated wall-clock time one
`event_time` at a time. For `t` it:

1. **DRAINS** every ordinary and delta-cycle event at `t` — INCLUDING same-`t` events generated inside
   handlers — in deterministic `(delta_cycle, microphase, stable_tie_key, seq)` order (smallest pending
   `delta_cycle` first), re-evaluating after each pass because a handler may append a forward
   `(t, current_delta_cycle+1)` event (§0.7-H2 rule 2), until **no ordinary event remains at `t`** —
   *quiescence*;
2. THEN runs the security **EPILOGUE** `FinalizeEventTimeSecurityCensus(t)` **EXACTLY ONCE** if
   `security_census_dirty[t]`;
3. adds `t` to `finalised_event_times`;
4. advances to the next `event_time`.

Two guarantees follow (§0.7d): **(a)** the epilogue runs even when no later event exists — it is not
itself a queued event that could be absent; **(b)** no ordinary event may be scheduled into an
already-finalised `event_time`, and any participation-changing action produced by the security decision
is scheduled at a **strictly later** `event_time`, so a recovery action can never change `H_active`
after the final decision at `t`.

## 4. Mechanism — exact fields and procedures

| Field / procedure | §  | Role in I-01/I-02 |
|-------------------|----|-------------------|
| `security_census_dirty : map event_time → bool` | §0.8 | Set true by `ApplyMinerStateTransition` on a census-changing boundary at that `event_time`; cleared ONLY by the epilogue. Keyed by `event_time` alone (I-01). |
| `latest_security_census : map event_time → census` | §0.8 | Overwritten (newest wins) by `ApplyMinerStateTransition` with the NEWEST post-transition `(H_active, H_honest, H_adversarial, q_adv)`; the epilogue decides from THIS value. |
| `finalised_event_times : set` | §0.8 | `event_time`s whose epilogue has run; no ordinary event may be scheduled into one (I-02). |
| `current_delta_cycle` | §0.8 | The `delta_cycle` of the dispatched event (H2); recorded in `transition_audit`, never used to key the decision. |
| `ApplyMinerStateTransition` step (7) | §0.9 | Flags dirty + overwrites census; schedules no decision. |
| `ProcessEventTime(event_time)` | §0.7d | Drains to quiescence, then invokes the epilogue once. |
| `FinalizeEventTimeSecurityCensus(event_time)` | §9 | Reads `latest_security_census`, clears the flag, calls `SecurityFloorEvaluate` at most once. |
| `SecurityFloorEvaluate(RoundID, TemplateID, state_version, …)` | §9 | SOLE breach recorder/recovery trigger; terminal-first (I-05) + stale guard (G10). |

`ProcessEventTime` loop structure (§0.7d, abbreviated):

```
LOOP:
  IF no ordinary event remains at event_time = t: BREAK          # quiescent (all delta-cycles drained)
  SET current_delta_cycle <- smallest delta_cycle with a pending event at t
  FOR EACH event e at (t, current_delta_cycle) IN ASCENDING (microphase, stable_tie_key, seq):
    ASSERT t not in finalised_event_times                        # never dispatch into a finalised time
    DISPATCH e                                                   # handler may append (t, k+1) or a later event_time
# ---- EVENT-TIME SECURITY EPILOGUE (runs once, even if no later event exists) ----
IF security_census_dirty[t]: CALL FinalizeEventTimeSecurityCensus(RoundContext, t)
ADD t to finalised_event_times
```

## 5. Total order and where the epilogue sits (relate to §21)

The H2 total order over queued events is unchanged (STAGE_01H §1):

    (event_time, delta_cycle, microphase, stable_tie_key, seq)     stable_tie_key = (CandidateID, MinerID, AssignmentID)

The epilogue is **NOT a queued event** and carries no such key: it is invoked *structurally* by
`ProcessEventTime` AFTER the last event of the highest `delta_cycle` at `t` has been dispatched —
i.e. strictly after every same-`event_time` event across ALL delta-cycles. Global event-priority
contract §21 now lists it OUTSIDE the inter-type queue, as the trailing line

> `— Security-floor decision (FinalizeEventTimeSecurityCensus -> SecurityFloorEvaluate): event-time`
> `EPILOGUE, run once AFTER quiescence (I-01/I-02), never as a same-timestamp queued event`

so the decision sits definitionally last at `t`, after items 1–13 of the §21 sequence, for every
delta-cycle.

## 6. Worked examples

**(a) Late-microphase exit whose dirty flag survives to the epilogue** *(cf. TV61).* At `t`, in a LATE
microphase of `delta_cycle = k`, a miner leaves `ACTIVE_HASHING` (e.g. `EnterLowPowerListen` or
`AdversarialParticipationChangeEvent(exit)`, §8a) via `ApplyMinerStateTransition`; no later event exists
after it in cycle `k`. Step (7) sets `security_census_dirty[t] <- true` and overwrites
`latest_security_census[t]`, keyed by `t` ALONE — NOT tied to the completing microphase or to cycle `k`,
so failure mode A cannot occur. `ProcessEventTime(t)` reaches quiescence and, because
`security_census_dirty[t]`, runs `FinalizeEventTimeSecurityCensus(t)` once on the exit's census.

**(b) Census changes across delta-cycles `k`, `k+1`, `k+2` → one decision on the `k+2` census** *(cf.
TV62).* At `t`, census-changing transitions occur in cycles `k`, then `k+1`, then `k+2` (each a
handler-generated forward event per §0.7-H2), each via `ApplyMinerStateTransition`. Each OVERWRITES
`latest_security_census[t]` (newest wins) and re-asserts `security_census_dirty[t]`; none schedules a
decision. `ProcessEventTime(t)` completes all of cycles `k`, `k+1`, `k+2` (no backward travel, §0.7-H2)
until `t` is quiescent, THEN runs `FinalizeEventTimeSecurityCensus(t)` ONCE, deciding from the census
left by the `k+2` transition. No intermediate delta-cycle census (`k` or `k+1`) independently triggers
recovery — failure mode B cannot occur. Sequence at `t`: boundary(`k`) → `latest_security_census[t] =`
census(`k`); boundary(`k+1`) overwrites → census(`k+1`); boundary(`k+2`) overwrites → census(`k+2`);
quiescent → epilogue reads census(`k+2`) → one `SecurityFloorEvaluate`; flag cleared.

**(c) The census transition is the LAST ordinary event at `t` (no later event) → epilogue still runs**
*(cf. TV63).* At `t`, the census-changing transition is the LAST ordinary event; the queue holds NO
later event at `t` (no later microphase/delta-cycle) and none at a later `event_time`.
`ProcessEventTime(t)` drains `t`, finds the queue quiescent, and — because
`FinalizeEventTimeSecurityCensus` is a STRUCTURAL epilogue invoked by the driver, NOT a queued event —
STILL calls it once (`security_census_dirty[t]` is set), then marks `t` finalised. A queued microphase-5
event, by contrast, would never fire (nothing dispatches it): the epilogue eliminates that miss.

## 7. Why an epilogue, not a microphase

A microphase-5 census evaluation is a *queued event*: it executes only if it is dispatched from the
queue at `t`. But a census-changing boundary in a late microphase (`m ≥ 5`) keys its would-be
evaluation to `(t, k+1)` (§0.7-H2 rule 2), and if no cycle-`k+1` event is ever enqueued, that
microphase-5 event is never dispatched — the decision is **missed** (failure mode A). Relocating the
decision to an epilogue invoked *structurally* by `ProcessEventTime` after quiescence removes the
dependency on "some later event being dispatched": the driver ALWAYS runs the epilogue once per
`event_time` whose `security_census_dirty` flag is set (§0.7d NOTE; §9). The missed-decision failure
mode is eliminated by construction.

## 8. Properties

- **P1 — No stranded dirty flag.** Because `security_census_dirty` and `latest_security_census` are keyed
  by `event_time` ALONE (§0.8, §0.9 step 7), no `delta_cycle` can carry a *different key*; a boundary in
  ANY delta-cycle at `t` sets the SAME flag `security_census_dirty[t]`, and `ProcessEventTime(t)` drains
  ALL delta-cycles before the epilogue, so the flag is always observed and cleared exactly once by
  `FinalizeEventTimeSecurityCensus(t)` (§9). The flag can never be stranded between delta-cycles.

- **P2 — Recovery action scheduled strictly later.** Any participation-changing action produced by the
  security decision (e.g. a recovery-driven transition) is scheduled at a **strictly later**
  `event_time`, and no ordinary event may enter an already-finalised `event_time` (`finalised_event_times`,
  §0.8; `ProcessEventTime` `ASSERT t not in finalised_event_times`, §0.7d). Therefore a recovery action
  can never alter `H_active` at `t` after the epilogue has finalised the census there (§9 NOTE).

## 9. Acceptance-style PASS checklist

| # | Check | Ground |
|---|-------|--------|
| 1 | `security_census_dirty` / `latest_security_census` keyed by `event_time` ALONE, never by `delta_cycle` | §0.8, §0.9 step (7) |
| 2 | `ApplyMinerStateTransition` recomputes census, verifies I17, records intermediate census FOR AUDIT, and schedules NO floor decision | §0.9 steps (6)–(7) |
| 3 | `latest_security_census[event_time]` overwritten newest-wins on every census-changing boundary | §0.9 step (7) |
| 4 | Exactly one `FinalizeEventTimeSecurityCensus(event_time)` per `event_time`, calling `SecurityFloorEvaluate` at most once with `(RoundID, TemplateID, state_version)` | §9, §0.7c |
| 5 | `ProcessEventTime` drains all ordinary + delta-cycle events at `t` (incl. handler-generated) to quiescence BEFORE the epilogue | §0.7d |
| 6 | Epilogue is structural, not queued — runs even when no later event exists (case c) | §0.7d NOTE, §9 |
| 7 | No intermediate delta-cycle census triggers recovery (cases a, b) | §9, I-01 |
| 8 | No ordinary event scheduled into a finalised `event_time`; recovery action scheduled at a STRICTLY LATER `event_time` (P2) | §0.7d, §0.8 |
| 9 | §21 lists the security decision as an event-time EPILOGUE run once after quiescence, OUTSIDE the inter-type queue | §21 |
| 10 | Name EXACTLY **PoCol**; mechanism only **the idle policy within PoCol**; "PoCol-E"/"Energy-Aware PoCol"/"Enhanced PoCol" PROHIBITED; A1 baseline `8.420833333 kWh` unchanged; no property claimed | this spec |

## 10. Naming and property discipline

The algorithm name is EXACTLY **PoCol**; the energy mechanism is described ONLY as **the idle policy
within PoCol**. The strings "PoCol-E", "Energy-Aware PoCol", and "Enhanced PoCol" are PROHIBITED and are
not used to denote this algorithm anywhere in the specification. This spec claims no energy, security,
fairness, or incentive property; it fixes only WHEN and by WHAT KEY the single security decision is
taken.

---

**Result: EVENT-TIME EPILOGUE SPEC (Stage 1I): PASS** — the single security-floor decision is relocated
from a per-`(event_time, delta_cycle)` microphase to the `event_time` epilogue
`FinalizeEventTimeSecurityCensus(event_time) → SecurityFloorEvaluate` (§9), driven ONCE by
`ProcessEventTime` (§0.7d) after `event_time` quiescence; `ApplyMinerStateTransition` (§0.9 step 7) flags
`security_census_dirty[event_time]` and overwrites `latest_security_census[event_time]` keyed by
`event_time` alone (I-01), so no dirty flag is stranded between delta-cycles (P1) and no intermediate
delta-cycle census triggers recovery; the epilogue can never be missed (§7); any recovery action is
scheduled at a strictly later `event_time` (P2). Extends STAGE_01H_DELTA_CYCLE_CONTRACT.md; no property
is claimed; the A1 baseline `8.420833333 kWh` is unchanged.
