# Stage 5 — Reward and Penalty Ledger Report

All figures are measured, produced by
`python docs/thesis_revision_v45/stage_05/generate_stage5_metrics.py` and stored in
`STAGE_05_ADVERSARIAL_INCENTIVE_METRICS.json`.

**These are model parameters, not proposals.** No rate value here is claimed to be optimal,
equilibrium-producing, fair, or Sybil-resistant. Nothing in this report establishes incentive
compatibility. The ledger exists so that adversarial behaviour has a *measurable* accounting
consequence — not to demonstrate that any behaviour is deterred.

---

## 1. Components

### Rewards (`sign = +1`)

| Component | Basis | Eligibility reason |
|---|---|---|
| `WORK_REWARD` | per unique accepted committed evaluation, deduplicated by `(range lineage, interval)` | `unique_accepted_committed_evaluations` |
| `AVAILABILITY_REWARD` | per second of sanctioned availability residency, as a **per-round delta** | `sanctioned_availability_residency` |
| `WINNER_REWARD` | once per accepted block, to its solver only | `accepted_block_solver` |
| `RESERVE_ACTIVATION_REWARD` | once per COMPLETED reserve activation request | `completed_reserve_activation` |
| `REASSIGNMENT_REWARD` | once per COMPLETED reassignment request | `completed_reassignment_service` |

### Penalties (`sign = −1`)

| Component | Requires | Eligibility reason |
|---|---|---|
| `FALSE_CLAIM_PENALTY` | a claim the **modeled audit actually detected** | `detected_false_claim` |
| `INVALID_MESSAGE_PENALTY` | a rejected invalid / out-of-range action | `rejected_invalid_action` |
| `ABANDONMENT_PENALTY` | **intentional** abandonment (`IDLE_POLICY_DEFECTOR`) | `intentional_abandonment` |

A crash fault is not an intentional abandonment. `penalise_crash_faults` defaults to `False`,
and S5-22 measures a crash-faulted run accruing **zero** abandonment penalty.

## 2. Deduplication and replay idempotence

Every entry carries an immutable `deduplication_key` built from the reward event identity and
the range lineage. `_emit` refuses to write a key already present, so no reward or penalty can
be counted twice — under replay, under re-finalisation, or under any identity multiplication.

Measured across all twelve scenarios:

| Property | Result |
|---|---|
| `incentive_reconciliation_residual` (max over scenarios) | **0.0** |
| Duplicate deduplication keys | **0** (S5-20) |
| Re-running round finalisation adds entries | **no** (S5-20) |

## 3. Availability is a residency quantity

`AVAILABILITY_REWARD` pays for time spent in a sanctioned availability state. It is **not**
evidence of actual work, and is never presented as such. Two correctness properties:

- **Time-aware.** The residency ledger accumulates only closed intervals, so the still-open
  interval `[state_since, t]` is added explicitly. Without this a miner resident at round
  closure would be credited zero.
- **Per-round delta.** A round-start snapshot is taken in `_handle_prepare_participants`, and
  the reward is the delta against it — never the cumulative run total.

## 4. Measured ledger outcomes

Reward rates used: `r_work = 1.0`, `r_avail = 0.1`, `r_win = 100.0`; penalties `q_false = 7.0`,
`q_invalid = 5.0`, `q_abandon = 11.0`.

| Scenario | Entries | Net | Naive | Deduplicated | Naive ÷ dedup | Residual |
|---|---:|---:|---:|---:|---:|---:|
| B honest + incentives | 178 | 2,941.0 | 29.0 | 29.0 | 1.00× | 0.0 |
| C free rider (0.5) | 399 | 7,999.0 | 7,975.0 | 7,975.0 | 1.00× | 0.0 |
| D misreporter (3×) | 599 | 11,999.0 | 11,975.0 | 11,975.0 | 1.00× | 0.0 |
| E false exhaustion, detected | 629 | 11,789.0 | 11,975.0 | 11,975.0 | 1.00× | 0.0 |
| F false exhaustion, undetected | 679 | 12,999.0 | 12,975.0 | 12,975.0 | 1.00× | 0.0 |
| G withholding, never released (1 entity, 4 identities) | 8 | 16.0 | 16.0 | 4.0 | 4.00× | 0.0 |
| H withholding, delayed (1 entity, 4 identities) | 89 | 952.0 | 160.0 | 40.0 | 4.00× | 0.0 |
| I delayed wake | 176 | 3,524.0 | 3,500.0 | 3,500.0 | 1.00× | 0.0 |
| J out-of-range actor | 629 | 11,849.0 | 11,975.0 | 11,975.0 | 1.00× | 0.0 |
| **K split ×4 + 3 identities** | 599 | 11,999.0 | **44,700.0** | **11,975.0** | **3.73×** | 0.0 |
| **L one entity holding all 4 identities** | 599 | 11,999.0 | **47,900.0** | **11,975.0** | **4.00×** | 0.0 |

The naive figure is amplified **only for the entity that actually declares the identities or
the split**. Single-identity miners with no declared entity multiply nothing, so scenarios C, D,
E, F, I and J — which each declare one attacker controlling one miner with no splitting — show a
ratio of exactly 1.00×.

### 4.1 Penalties land exactly where they should

- **Scenario E vs D.** Identical except for the detected false claims. Net falls from 11,999.0
  to 11,789.0 — a difference of **210.0 = 30 detected claims × 7.0**. Exact.
- **Scenario J vs D.** Identical except for the rejected out-of-range attempts. Net falls to
  11,849.0 — a difference of **150.0 = 30 rejections × 5.0**. Exact.
- **Scenario F.** The audit detects nothing, so **no** false-claim penalty is charged, even
  though 3,000 nonces went unsearched. The attack is not punished by the ledger; it is
  punished only by the honest coverage-gap label on the round. This is the model behaving
  correctly, and it is worth stating plainly: **an undetected liar pays nothing.**

### 4.2 Withholding does not pay — but is not penalised either

Scenario G: four miners withhold every solution, no block is ever accepted, and the winner
reward total is **0.0**. The withholders forgo 100.0 per block they could have claimed.

That is a measurement of forgone reward under this parameterisation. It is **not** a claim that
withholding is irrational, unprofitable in general, or deterred. A withholder in a real
deployment may hold value this model does not represent. There is no
`SOLUTION_WITHHOLDING_PENALTY` component, because the model does not assume withholding is
detectable.

### 4.3 The accounting-amplification exposure (S5-8)

Two scenarios make the exposure visible.

**Scenario L — one entity holding all four identities.** The cleanest case: the entity really
controls 4 of the 4 mining identities, so naive per-identity accounting credits it exactly
**4.00×** (47,900.0) what its actual work earns under deduplication (11,975.0).

**Scenario K — assignment splitting on top of identity multiplication.** One declared entity
controls a single miner, splits its assignment 4 ways and declares 3 identities, giving that
entity a 12× per-entity factor. Because only that one entity is amplified and the other three
miners are not, the aggregate ratio is **3.73×** (44,700.0 vs 11,975.0).

In both cases deduplicating on range lineage removes the amplification entirely: the credited
total is identical to the honest case.

**Scope.** This measures what the deduplication rule removes from the reward ledger. It says
nothing about an adversary's ability to acquire identities, influence assignment, or affect
consensus. It is **not a Sybil-resistance result** and must not be cited as one. Both views are
reported precisely so the exposure is visible rather than assumed away.

## 5. What the ledger cannot tell you

- It does not model rational choice: no miner in this simulator responds to incentives. Every
  behaviour is *declared* in the configuration, not *chosen* in response to payoffs.
- Because behaviours are declared rather than chosen, **no equilibrium, best-response or
  incentive-compatibility conclusion can be drawn from any figure in this report.**
- The parameterisation is arbitrary. Different rates would produce different net figures and
  different apparent orderings between honest and adversarial entities.
- Penalties depend entirely on the assumed audit detection probability, which is a model
  parameter and not a property PoCol is shown to possess.
