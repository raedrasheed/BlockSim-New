# Corrected Simulation Methodology (PoW vs PoCol)

**Branch:** `claude/fix-energy-round-semantics`
**Scope:** energy accounting, round/stale semantics, shared configuration, block-interval
calibration, and the PoW/PoCol success model.
**Priority:** scientific validity over favourable results for PoCol.

This document specifies the corrected methodology introduced in Phases B1–B6. It
replaces the previous, physically invalid energy model that produced the
98–99 % "energy saving" figure. Every rule below is implemented deterministically
and covered by a test in `tests/`.

---

## 1. Physical model of a miner

A miner is modelled as continuously operating mining hardware. This is the
correct physical picture for both Nakamoto PoW and PoCol: hardware draws power
for as long as it is powered on and searching, **independently of how many
blocks it produces**. Charging energy per produced block (the old model) is the
root methodological error — it makes energy a function of block count and of the
number of competing/stale blocks, neither of which drives real electricity use.

### 1.1 Constants (shared, `Models/scenario.py`)

| Symbol | Meaning | Value |
|---|---|---|
| `H_net` | network hash rate | `141e12` H/s (141 TH/s) |
| `eff` | miner efficiency | `21.5` J/TH |
| `EF` | grid emission factor | `0.445` kg CO₂e/kWh |
| `T` | target block interval | `600` s |
| `simTime` | simulated wall-clock | `10000` s |

### 1.2 Power and the physical energy bound

Network power is a direct consequence of the constants and is **independent of
miner count N**:

```
P_network = H_net * eff = 141e12 H/s * 21.5 J/TH
          = 141 TH/s * 21.5 J/TH = 3031.5 W
```

For continuous mining over `simTime`, total energy is therefore fixed:

```
E_continuous = P_network * simTime
             = 3031.5 W * 10000 s
             = 3.0315e7 J = 8.420833… kWh
```

`8.4208 kWh` is a **hard upper bound and, for continuous mining, the exact
expected value** for *either* protocol. Any result above it is unphysical; any
"saving" that pushes one protocol far below it must come from that protocol
actually powering hardware down, which neither protocol does here.

---

## 2. Phase B1 — wall-clock energy integration

**File:** `Models/Node.py` (meter), `Models/PoCol/Consensus.py` (checkpoint hook),
`Main.py` / `experiments/run_scenario.py` (finalisation).
**Tests:** `tests/test_wallclock_energy.py`, `tests/test_energy_invariants.py`.

Each node carries an energy meter that **integrates power over simulation time**:

```
E_i(t) = P_i * active_time_i(t)          (monotonic, no re-charging)
P_i    = h_i * eff        where h_i is miner i's hash rate in H/s
```

Key rules:

1. **Monotonic integration.** `update_energy(t)` advances the meter from
   `last_energy_update_time` to `t` and adds `P_i * (t − last)`. It can never
   re-charge an interval, so overlapping fork/stale block events cannot
   double-count wall-clock.
2. **Created blocks are checkpoints, not charges.**
   `apply_energy_for_created_block` only advances meters to the block time; it
   adds no per-block energy.
3. **Fractional hash-rate normalisation.** Miner i's share is
   `h_i = H_net * (hp_i / Σ hp_j)`. The previous code used `H_net * (hp_i / 100)`,
   which was correct only at exactly N = 100 and made total energy scale with N.
4. **Finalisation.** `Node.finalize_all(simTime)` integrates every active miner
   to `simTime`, so continuous miners each contribute `P_i * simTime` and the
   network sums to `P_network * simTime` exactly.

**Invariant enforced by tests:** for continuous mining,
`Σ E_i = P_network * simTime = 8.4208 kWh`, independent of N and of block count,
for both PoW and PoCol.

---

## 3. Phase B2 — round termination and stale-event semantics

**File:** `Models/PoCol/Consensus.py`, `Models/PoCol/BlockCommit.py`,
`Scheduler.py`. **Tests:** `tests/test_round_semantics.py`.

A PoCol *round* is the competition to extend one parent block. It is identified
by `(parent_id, round_id)` with a monotonic `round_id`.

- `_open_round(parent_id)` bumps `round_id`, sets status `ACTIVE`.
- The **first** valid block on a parent calls `close_round(...)`; the round is
  recorded in `_closed_rounds`.
- Any later create-block event whose `(parent_id, round_id)` is already closed is
  **lazily rejected**: it is not counted, not charged, not committed, and
  schedules no propagation events. Rejection is scoped to the *exact*
  `(parent_id, round_id)`, so genuine competing blocks on other branches/rounds
  are still countable (verified by
  `test_invalidation_is_scoped_to_parent_and_round`).

This removes the earlier 62–76 % artefactual stale rate that arose from stale
events being fully processed (and previously charged energy). Under the corrected
model the realised stale rate is ~0 for both protocols at these parameters.

---

## 4. Phase B3 — single shared configuration

**File:** `Models/scenario.py`. **Tests:** `tests/test_config_equality.py`.

A frozen `ScenarioConfig` holds every protocol-**independent** parameter
(workload, network, energy constants, `simTime`, target interval). Both protocols
are configured from the *same* object via `apply_to`, so they cannot silently
diverge (the previous code ran PoW at `Tn = 3` but PoCol at `Tn = 10`, an
uncontrolled workload difference).

Only parameters listed in `PROTOCOL_SPECIFIC` may differ, and only PoCol has any
— the nonce-partitioning knobs (`PoCol_AutoNonceSpace`, `PoCol_TargetInterval`
set equal to `Binterval`, `PoCol_AssignStrategy`). PoW adds nothing.
`non_protocol_difference()` is asserted empty in the test suite.
A `config_hash` over the shared parameters is recorded with every run.

---

## 5. Phase B4 — block-interval calibration

**File:** `experiments/run_scenario.py`. **Tests:**
`tests/test_block_interval_calibration.py`.

Both protocols are calibrated to the **same** expected accepted-main-chain
interval, `T = Binterval = 600 s`, so neither is advantaged by running faster.

**PoW.** Each miner draws its next-block delay from
`Exp(rate = (h_i/H_total)/T)`. The network's next block is the minimum of N
independent exponentials, itself `Exp(rate = (Σ h_i/H_total)/T) = Exp(1/T)`, so
`E[interval] = T`.

**PoCol.** The shared nonce domain is auto-sized to `S = 2·H_total·T`, giving a
per-hash success probability `p = 1/(H_total·T)`. The network first-success time
is `Exp(1/T)` (mean `T`), truncated at the domain horizon `h = S/H_total = 2T`; a
round may **exhaust** (zero successes) and redraw a fresh template. The
truncation identity holds exactly:

```
E[block_time] = E[N]·h + E[X | X ≤ h]
             = [q/(1−q)]·h + (T − h·q/(1−q))
             = T,          with q = P(X > h) = e^{−h/T} = e^{−2}
```

so `E[interval] = T` for PoCol too. Both protocols therefore target `600 s` by
construction.

**Realised (30 seeds × N = 100).** PoW mean = 548 s, PoCol mean = 533 s — within
3 % of each other. Both sit slightly below `T` because the estimator
`(t_last − t_first)/(n − 1)` omits the censored gap past `simTime`; this bias is
**identical for both protocols**, which is exactly what a controlled comparison
requires. `test_both_protocols_run_at_equivalent_intervals` asserts the two
realised means agree within 15 %.

Both the created-block interval and the accepted-main-chain interval are reported
separately for every run.

---

## 6. Phase B5 — target-based stochastic success model

**File:** `Models/PoCol/Consensus.py` (`_sample_round_outcome`). **Tests:**
`tests/test_pow_success_model.py`.

The previous PoCol model pre-sampled exactly one solution nonce
(`random.randrange(0, space)`) and declared the miner owning that nonce the
winner — **guaranteeing exactly one success every round** and making forks and
exhaustion impossible. This is not how proof-of-work search behaves.

The corrected model:

- draws the network first-success time from `Exp(1/T)` (memoryless);
- allows **zero-success (exhausted) domains**: if the draw exceeds the horizon
  `2T`, the attempt exhausts (`P = e^{−2} ≈ 0.135`), a fresh template is drawn
  and counted, and the search retries — so zero / one / many successes are all
  possible;
- picks the winner **in proportion to hash share** (`rng.choices(weights=rates)`).

Tests verify: mean block time ≈ T with CV ≈ 1 (exponential signature);
exhaustion frequency matches `e^{−2}/(1−e^{−2}) ≈ 0.156` per successful round; a
double-hash miner wins ~2× as often; and the guaranteed-nonce field is gone.

---

## 7. Phase B6 — multi-seed experiment matrix

**File:** `experiments/run_matrix.py`. **Outputs:** `results/corrected/`.

- **Design:** 2 protocols × 5 miner counts {100, 200, 300, 400, 500} × 30 seeds
  = **300 runs**.
- **Isolation:** each run executes in a **fresh Python interpreter**
  (`experiments/run_scenario.py` via `subprocess`), so no global state leaks
  between runs.
- **Pairing:** PoW and PoCol share the same seed at each `(n, seed)`, enabling a
  paired comparison and paired effect sizes.
- **Statistics:** mean, median, std, 95 % CI (normal approximation, no scipy
  dependency), min, max per `(protocol, n)`; paired PoCol−PoW mean difference,
  percentage, and Cohen's d for energy, CO₂, and energy-per-block.
- **Reproducibility:** `configuration.json` (shared config + `config_hash`) and
  `reproducibility_manifest.json` (git commit, Python/package versions, platform,
  seeds, exact per-run commands) are written with every matrix run.

**Reproduce:**

```bash
python experiments/run_matrix.py 30 8      # 30 seeds, 8 parallel workers
python -m pytest tests/ -v                 # or run each tests/*.py directly
```

---

## 8. What this methodology deliberately does **not** do

- It does not power hardware down during idle/loser waits (neither protocol
  claims to), so it does not manufacture an energy gap.
- It does not tune any parameter to favour PoCol; all shared parameters are
  identical and the only PoCol-specific knobs set the nonce domain to the *same*
  target interval as PoW.
- It does not remove or hide unfavourable results — the exhausted-round overhead
  unique to PoCol is measured and reported.
