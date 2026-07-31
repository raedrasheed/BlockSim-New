# Stage 1G — State-Hook & Census Audit (G3)

This audit confirms correction **G3** in the PoCol Stage-1 pseudocode: `ActiveHashRateUpdate`
is **compute-only**, and every miner-participation change — including adversarial entry and
exit — routes through the central state hook `ApplyMinerStateTransition`. It is a structural
audit of the specification text; no protocol property is claimed or evaluated here.

## 1. Corrected `ActiveHashRateUpdate` — COMPUTE-ONLY

`ActiveHashRateUpdate(RoundContext, t)` is a read-only re-derivation of the census at time `t`.
It **READS** the current miner-state census and **RECORDS** the rates:

- `H_honest(t)` = SUM over honest miners currently in `ACTIVE_HASHING` of their modeled hash rate.
- `H_adversarial(t)` = SUM over adversarial miners currently in `ACTIVE_HASHING` of their modeled hash rate.
- `H_active(t)` = `H_honest(t) + H_adversarial(t)` — the exact census decomposition (**I17**).
- `q_adv(t)` = `H_adversarial(t) / H_active(t)`, or `NA` when `H_active(t) = 0` (I17: undefined at zero).

It records **values only**: no state change and no breach. It has **NO `[SIMULATION SAMPLING]`
step**. It MUST NOT (a) apply a sampled adversarial active set directly to miner states, (b) alter
the `ACTIVE_HASHING` census without a state transition, or (c) add or remove a miner from
`H_active` independently of `miner_state`. It is a periodic snapshot of the I17 identity, not a
writer of the census.

## 2. `AdversarialParticipationChangeEvent(MinerID, direction ∈ {enter, exit})`

This scheduled event is the **sole carrier** of each modeled adversarial participation change. Its
state change is deterministic and always goes through the hook:

- **exit** (while `miner_state = ACTIVE_HASHING`): calls
  `ApplyMinerStateTransition(ACTIVE_HASHING -> OFFLINE, now, reason = adversarial_withdrawal)`
  (edge **T11**), then RELEASES the miner's assignment for reclamation — only the accepted
  unsearched suffix is reassignable (C4).
- **enter** (from `OFFLINE`/`RESERVE`/`REGISTERED`/`LOW_POWER_LISTEN`): activates through the
  **normal path**. If `OFFLINE`, first `ApplyMinerStateTransition(OFFLINE -> REGISTERED, now,
  reason = adversarial_rejoin)` (edge **T17**) via the hook, then `RangeAssign`, which builds a
  `CreatePendingAssignment` and issues `StartWake`. The miner reaches `ACTIVE_HASHING` **only at
  its own `WakeCompleteEvent`** (F5) — never a direct census add.
- otherwise: `RETURN no_change` (already in the target participation state).

The `[SIMULATION SAMPLING]` adversarial-participation draw is now entirely in the **SCHEDULING** of
these events (the model draws each miner's enter/exit times and which miner changes); the resulting
**state change is deterministic and goes through the hook**.

## 3. Hook contract — `ApplyMinerStateTransition`

`ApplyMinerStateTransition(MinerID, old_state, new_state, event_time, reason, assignment_ref,
candidate_ref)` is the **sole writer of `miner_state`** (0.3). At each call it:

- CLOSES the old residency interval at `event_time` and OPENS the new one at `event_time`;
- CHARGES one-shot boundary (transition/coordination) energy for the crossing (never folded into
  `P*t`, never double-counted);
- SETS `miner_state <- new_state` atomically;
- RECOMPUTES `H_honest` / `H_adversarial` / `H_active` deterministically from the post-transition
  `ACTIVE_HASHING` set and re-checks **I17** at **every `ACTIVE_HASHING` boundary** (entry and exit);
- SETS `q_adv`, or `NA` when `H_active = 0`;
- **SCHEDULES** (never inlines) `SecurityFloorEvaluate` for the boundary;
- SUPPRESSES duplicate transitions (idempotent per `(MinerID, event_time, old_state -> new_state)`);
- requires a **legal** `old_state -> new_state` transition as a precondition (T1 registration entry
  excepted, `old_state = NONE`).

## 4. Properties

| # | Property | Result | Why |
|---|----------|--------|-----|
| P1 | `ActiveHashRateUpdate` cannot alter miner participation | PASS | Compute-only; reads the census and records values; performs no state writes. |
| P2 | Every adversarial entry/exit goes through the hook | PASS | Both directions of `AdversarialParticipationChangeEvent` call `ApplyMinerStateTransition` (T11 / T17 then normal path). |
| P3 | I17 is recomputed at the exact transition time | PASS | The hook recomputes `H_*` and re-checks I17 at every `ACTIVE_HASHING` boundary, at `event_time`. |
| P4 | `H_adversarial` is never sampled independently after `H_active` | PASS | `H_adversarial` is summed from the post-transition adversarial `ACTIVE_HASHING` set; no independent draw. |
| P5 | C7 preserved | PASS | Floor breaches are recorded only by `SecurityFloorEvaluate`, which the hook schedules at the boundary. |
| P6 | No census mutation outside a state transition | PASS | The census changes only via the hook; `ActiveHashRateUpdate` never mutates it. |

## 5. Result

**STATE-HOOK & CENSUS AUDIT (G3): PASS**, exercised by **TV41**.
