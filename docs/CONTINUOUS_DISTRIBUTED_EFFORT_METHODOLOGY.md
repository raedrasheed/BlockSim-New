# Continuous Distributed-Effort Experiment — Methodology

**Branch:** `claude/pocol-continuous-distributed-effort`
**Status:** a new, explicitly bounded experiment. It does **not** modify or
overwrite `results/corrected/` or `results/nonce_partition_worst_case/`, and it
does not alter their conclusions.

---

## 0. Three findings — keep them separate

| | Scenario | Result | Where |
|---|---|---|---|
| **Finding 1** | Continuous full-power mining, equal aggregate hardware, distinct work | PoW = PoCol (8.4208 kWh) | `results/corrected/` |
| **Finding 2** | Common-template exact-duplicate search, one-shot worst case | disjoint saves `1 − 1/N` attempts vs the duplicate baseline; ties independent headers | `results/nonce_partition_worst_case/` |
| **Finding 3 (this experiment)** | Common-template duplicate baseline, **fixed-slot scheduling**, miners drop to **IDLE/SLEEP** after finishing assigned work | disjoint saves `(1 − q)(1 − 1/N)` energy, where `q = P_idle/P_active` — and **only** when miners actually power down | `results/continuous_distributed_effort/` |

These are **never** combined into one headline. Finding 3 makes explicit the
*mechanism* Finding 2 lacked: partitioning alone saves nothing; the saving comes
from **reduced ACTIVE time plus lower-power IDLE/SLEEP states**.

---

## 1. Research question

Under a single immutable shared block template, if `N` miners would otherwise
repeat the same complete nonce-domain search, how much energy is saved by (a)
assigning mutually disjoint nonce subdomains **and** (b) placing miners into IDLE
or SLEEP after their assigned work is complete? The experiment separates:

1. duplicate complete-header work (Mode A),
2. disjoint shared-template work (Mode B),
3. independent non-duplicate candidate work (Modes C1, C2).

Results are **not** generalized to Bitcoin.

---

## 2. Central modeling principle

**Nonce allocation by itself does not reduce energy** if miners stay fully
powered and immediately start another round. Energy reduction requires a change
in **actual operating time** or **power state**. Two scheduling policies isolate
this:

- **IMMEDIATE_RESTART (control):** finishing a range/round starts the next
  template immediately; miners are ACTIVE for the whole horizon. Expected result:
  PoW ≈ PoCol, energy-neutral (this reproduces Finding 1's mechanism).
- **FIXED_SLOT_IDLE:** mining runs in fixed slots (default 600 s), one immutable
  template per slot. A miner that finishes its range enters IDLE/SLEEP for the
  rest of the slot; when any miner finds a valid nonce the whole round closes and
  all miners drop to IDLE/SLEEP until the next slot boundary. The next template
  cannot start early. Here disjoint allocation can reduce ACTIVE time and energy.

Results from the two policies are never mixed.

---

## 3. Modes

- **A — COMMON_TEMPLATE_DUPLICATE_BASELINE:** identical template + complete domain
  to every miner, same start, same order → identical repeated complete-header
  evaluations. Intentionally constructed maximum-duplication baseline; **not**
  labelled simply "Bitcoin PoW".
- **B — POCOL_DISJOINT_NONCE:** same template, domain split into mutually disjoint
  subranges; each miner evaluates only its range; no complete header evaluated
  twice; finishing → IDLE/SLEEP; any success closes the round globally.
- **C1 — INDEPENDENT_HEADERS_EQUAL_TOTAL_BUDGET:** distinct headers per miner;
  **total** network budget = `M`, split into `M/N` per miner; no duplicate
  complete-header work. The most important realistic control for B.
- **C2 — INDEPENDENT_HEADERS_FULL_PER_MINER_BUDGET:** distinct headers; each miner
  gets up to `M` evaluations; total budget `N × M`. An **expanded-work-budget**
  reference — not directly equivalent to B.

---

## 4. Miner power states

Every miner is ACTIVE, IDLE, or SLEEP. State-based wall-clock integration:

```
elapsed  = current_time − last_state_change_time
energy_j += state_power_w × elapsed
if state == ACTIVE:  hashes += hashrate_hps × elapsed
last_state_change_time = current_time
```

Tracked per miner: `miner_id, assigned_range_start/end, assigned_candidate_count,
evaluated_candidate_count, hashrate_hps, active/idle/sleep_power_w, current_state,
last_state_change_time, active/idle/sleep_time_s, cumulative_energy_j/_kwh,
cumulative_hashes, exhausted_range, found_solution`. Every miner is finalized to
`simTime`. Energy is **never** tied to a block event, applied once per block, or
divided by `N`.

---

## 5. Power configuration

`active_power_ratio = 1.0`. Idle ratios tested:
`{0.00, 0.05, 0.10, 0.20, 0.50, 1.00}`; sleep ratios `{0.00, 0.01, 0.05}`.
`idle_power_i = active_power_i × idle_ratio`,
`sleep_power_i = active_power_i × sleep_ratio`. At `idle_ratio = 1.0` finishing a
range yields no saving; at `idle_ratio = 0.0` the idealized maximum saving emerges.

---

## 6. Hardware normalization policies

- **H1 — FIXED_AGGREGATE_NETWORK_HASHRATE:** aggregate `141 × 10¹² H/s`, aggregate
  active power `141 TH/s × 21.5 J/TH = 3031.5 W`; each miner gets
  `hashrate = 141e12/N`, `active_power = 3031.5/N`. (Under IMMEDIATE_RESTART over
  10 000 s this reproduces the Finding-1 total, `3031.5 W × 10000 s = 8.4208 kWh`.)
- **H2 — FIXED_PER_MINER_HARDWARE:** each miner has fixed hashrate and power;
  aggregate scales with `N`. Mirrors the "ten equally powered miners" example
  (default `100 W`/miner used in the section-8 tests).

H1 and H2 are never combined in one table without labelling the policy.

---

## 7. Nonce domain and slot calibration

Half-open domain `[0, M)`; `M ∈ {100, 1 000, 1 000 000, 2³²}`. Large domains are
**never enumerated** — analytical counts, per-range geometric first-success
sampling, and Python big integers only.

For the primary deterministic fixed-slot experiment the hash rate is calibrated so
a full-domain scan takes exactly one slot: `r = M / T` ⇒ full scan `= T`. The only
valid nonce is at `M − 1`, so every duplicate-baseline miner stays ACTIVE the full
`T`; each PoCol miner scans `≈ M/N` candidates and is ACTIVE for `≈ T/N`, then
IDLE/SLEEP until the slot ends.

---

## 8. Deterministic energy model

For `N` equal miners, slot `T`, active power `P`, idle ratio `q = P_idle/P_active`,
final-nonce worst case:

```
E_A = N · P · T
E_B = N · [ P·(T/N) + q·P·(T − T/N) ]
E_B / E_A = 1/N + q·(1 − 1/N)
Reduction = (1 − q)·(1 − 1/N)
```

Verified exactly (tests) for `N = 10, T = 600 s, P = 100 W`:

| q | E_A (J) | E_B (J) | E_B/E_A | reduction |
|---:|---:|---:|---:|---:|
| 0.00 | 600 000 | 60 000 | 0.10 | 90 % |
| 0.10 | 600 000 | 114 000 | 0.19 | 81 % |
| 1.00 | 600 000 | 600 000 | 1.00 | 0 % |

C1 (equal total budget) yields `E_C1 = E_B` in this worst case — B has **no**
advantage over C1. C2 (per-miner budget `M`) yields `E_C2 = E_A` (all miners
ACTIVE the full slot) but with **unique**, not duplicate, work.

---

## 9. Corrected stochastic shared-template model

The earlier nonce-partition stochastic model took the smallest *global* successful
nonce and mapped it to a range. That is wrong for parallel disjoint search: the
earliest solution **in wall-clock time** may sit in a numerically later range.

Corrected model: for each disjoint subrange `i`, draw a first local success
`G_i ~ Geometric(p)` using a **deterministic range-specific seed** derived from the
shared template seed. `G_i` is valid iff `G_i ≤ range_size_i`. Then:

```
t_star        = min_i G_i           over valid ranges   (LOCAL discovery time)
winner        = argmin_i G_i
winning_nonce = range_start_i + G_i − 1
A_PoCol       = Σ_i min(range_size_i, t_star)
```

For the duplicate baseline A the same per-range success set is reconstructed and
the first success in the **common numeric scan order** is
`min_i (range_start_i + G_i − 1)` — its discovery step is that nonce `+ 1`, and all
`N` miners are ACTIVE until then. A and B share the **same** shared-template
success positions (paired), and no domain is enumerated.

---

## 10. Global stopping

On the first valid nonce: close the round; record `winner_id`, `winning_nonce`,
`discovery_time`; transition all ACTIVE miners to IDLE/SLEEP; invalidate future
mining events of the closed round; prevent post-solution evaluations and
post-solution ACTIVE energy; under FIXED_SLOT_IDLE wait for the next slot
boundary; under IMMEDIATE_RESTART start the next round at once. A cancelled future
event is **not** a stale block.

---

## 11. Continuous multi-round operation

Horizon `10 000 s`, default slot `600 s`. Each slot boundary: new immutable
template + `template_id`, paired template seed, re-partition the domain, reset
round-local counters, preserve cumulative miner energy. Reported per run: slots
scheduled, successful/exhausted rounds, empty-slot time, active/idle/sleep miner
seconds, unique vs duplicate complete-header evaluations, total energy, energy per
round / per accepted block / per confirmed tx, average discovery time, slot
utilization, and % time ACTIVE.

---

## 12. Comparisons (reported separately)

`A vs B`, `B vs C1`, `B vs C2`, `IMMEDIATE_RESTART vs FIXED_SLOT_IDLE`,
`H1 vs H2`. The reduction of B vs A is **never** used as evidence that B beats C1;
`B vs C1` is computed as a direct paired difference with a pre-registered
equivalence margin (TOST).

---

## 13. Files & reproduction

```
experiments/continuous_distributed_effort/
  __init__.py configuration.py power_states.py round_model.py
  stochastic_template.py run_scenario.py run_matrix.py statistics.py
results/continuous_distributed_effort/
  deterministic_raw.csv stochastic_raw.csv summary_statistics.csv
  paired_comparisons.csv per_miner_energy.csv configuration.json
  reproducibility_manifest.json
```

```bash
python experiments/continuous_distributed_effort/run_matrix.py
python -m pytest tests/ -v
```
