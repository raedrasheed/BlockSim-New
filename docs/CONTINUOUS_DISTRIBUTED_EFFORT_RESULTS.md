# Continuous Distributed-Effort Experiment — Results

**Branch:** `claude/pocol-continuous-distributed-effort`
**Data:** `results/continuous_distributed_effort/`
**Reproduce:** `python experiments/continuous_distributed_effort/run_matrix.py 100 12`
then `python -m pytest tests/ -v`

> All savings below emerge from **actual reduced ACTIVE time and lower-power
> IDLE/SLEEP states**, integrated over wall-clock time. Energy is never divided by
> `N`. `results/corrected/` and `results/nonce_partition_worst_case/` are
> unchanged.

---

## 1. Headline

Under a common-template duplicate baseline, **fixed-slot scheduling**, and miners
actually dropping to IDLE/SLEEP after finishing their assigned work, disjoint
allocation reduces energy by up to `(1 − q)(1 − 1/N)` (q = P_idle/P_active). But
**that saving is entirely reproduced by independent equal-budget headers (C1)** —
PoCol (B) and C1 are statistically **equivalent** (TOST, 1% margin). PoCol's
benefit here is *de-duplication + power-down*, not partitioning per se.

Under **IMMEDIATE_RESTART** (continuous full power) the saving is **zero**.

---

## 2. Exact deterministic energy model (verified)

```
E_B / E_A = 1/N + q·(1 − 1/N)      Reduction = (1 − q)·(1 − 1/N)
```

Single-slot exact test (N=10, T=600 s, P=100 W): q=0 → 90 % (E_A=600000 J,
E_B=60000 J); q=0.10 → 81 %; q=1.0 → 0 %. (tests/test_continuous_distributed_effort.py)

---

## 3. N = 10, every idle-power ratio (FIXED_SLOT, H2, 10 000 s)

| q = P_idle/P_active | E_A (kWh) | E_B (kWh) | reduction | ideal (1−q)(1−1/10) |
|---:|---:|---:|---:|---:|
| 0.00 | 2.7778 | 0.2833 | 89.80 % | 90.00 % |
| 0.05 | 2.7778 | 0.4081 | 85.31 % | 85.50 % |
| 0.10 | 2.7778 | 0.5328 | 80.82 % | 81.00 % |
| 0.20 | 2.7778 | 0.7822 | 71.84 % | 72.00 % |
| 0.50 | 2.7778 | 1.5306 | 44.90 % | 45.00 % |
| 1.00 | 2.7778 | 2.7778 | 0.00 % | 0.00 % |

The small gap below the ideal is a **partial-slot** effect: 10 000 s / 600 s = 16
full slots + one 400 s slot, in which B still runs a full round; over exact
slot-multiples the reduction equals the formula (verified at single-slot).

---

## 4. IMMEDIATE_RESTART vs FIXED_SLOT_IDLE (N = 10, H2, q = 0)

| schedule | E_A (kWh) | E_B (kWh) | B % time ACTIVE |
|---|---:|---:|---:|
| IMMEDIATE_RESTART | 2.7778 | 2.7778 | 100.0 % |
| FIXED_SLOT_IDLE | 2.7778 | 0.2833 | 10.2 % |

This is the central control: **partitioning saves nothing unless miners power
down.** Under immediate restart B is ACTIVE the whole horizon and consumes exactly
as much as A (energy-neutral, consistent with Finding 1).

---

## 5. H1 vs H2 (N = 100, FIXED_SLOT, q = 0.10)

| hardware | E_A (kWh) | E_B (kWh) | E_B/E_A |
|---|---:|---:|---:|
| H1 fixed aggregate (141 TH/s) | 8.4208 | 0.9194 | 0.1092 |
| H2 fixed per-miner (100 W) | 27.7778 | 3.0328 | 0.1092 |

The **ratio is hardware-independent** (identical 0.1092), so the H2 stochastic
ratios transfer to H1. Note H1's baseline `E_A = 8.4208 kWh` is exactly the
Finding-1 continuous-mining energy (`3031.5 W × 10 000 s`), i.e. this experiment
is anchored to the corrected model.

---

## 6. Stochastic (H2, M = 10⁶, p = 2×10⁻⁶, FIXED_SLOT, idle = 0.10, 100 paired seeds)

Mean total energy (kWh) per mode; each run in a fresh subprocess:

| N | A duplicate | B disjoint | C1 equal-budget | C2 per-miner budget |
|---:|---:|---:|---:|---:|
| 100 | 13.376 | 2.886 | 2.886 | 2.903 |
| 200 | 26.908 | 5.667 | 5.666 | 5.682 |
| 300 | 41.284 | 8.446 | 8.445 | 8.464 |
| 400 | 55.692 | 11.224 | 11.225 | 11.244 |
| 500 | 69.126 | 14.001 | 14.004 | 14.025 |

### 6.1 Paired comparisons (d = B − other, kWh; bootstrap 95 % CI)

| N | B vs A (Cohen's d) | B vs C1 (Cohen's d, TOST) | B vs C2 (Cohen's d) |
|---:|---|---|---|
| 100 | −10.489, d=−5.28 | −0.00007, d≈0, **equivalent** | −0.017, d=−0.43 |
| 200 | −21.241, d=−5.19 | +0.0011, d≈0, **equivalent** | −0.015, d=−0.44 |
| 300 | −32.837, d=−4.87 | +0.0012, d≈0, **equivalent** | −0.017, d=−0.44 |
| 400 | −44.467, d=−4.76 | −0.0004, d≈0, **equivalent** | −0.020, d=−0.53 |
| 500 | −55.125, d=−4.79 | −0.0032, d=−0.12, **equivalent** | −0.023, d=−0.64 |

- **B vs A:** large energy saving (the whole point of removing duplicate work +
  powering down); Cohen's d ≈ −5.
- **B vs C1:** the paired mean difference is at the 10⁻³ kWh level and the
  pre-registered 1 %-margin **TOST reports equivalence at every N.** PoCol
  disjoint allocation is **not** better than independent headers of equal total
  budget.
- **B vs C2:** B is marginally *lower* than C2 (small effect, d ≈ −0.4 to −0.6)
  because C2 grants each miner the full `M` budget (more unique work); this is an
  expanded-work reference, not an equivalent comparison.

### 6.2 Per-state accounting

- % time ACTIVE under FIXED_SLOT falls far below 100 % for B/C1/C2 (miners idle
  after finishing), while A stays near 100 %.
- Exhaustion probability (no success in a slot) is non-zero for the shared
  template at `p = 2×10⁻⁶`; per-miner energy split (ACTIVE/IDLE/SLEEP) is in
  `per_miner_energy.csv`.

---

## 7. Three findings, side by side (never combined)

| | Scenario | Result |
|---|---|---|
| **Finding 1** | Continuous full-power mining, distinct work | PoW = PoCol (8.4208 kWh) |
| **Finding 2** | Common-template duplicate search, one-shot | disjoint saves `1 − 1/N` attempts vs A; ties independent headers |
| **Finding 3 (here)** | Common-template duplicate + fixed slots + power-down | disjoint saves `(1 − q)(1 − 1/N)` energy vs A; **equivalent to C1**; zero under immediate restart / q=1 |

---

## 8. Test results

`python -m pytest tests/ -v` → **86 passed** (66 prior + 20 new). The 20 new tests
cover all required invariants incl. the exact formula, energy=∫power dt,
state-time conservation, no-active-after-finish, global stopping, immediate-restart
neutrality, q=0/q=1 bounds, C1/C2 budgets, corrected local-time winner, seed
reproducibility, and that the corrected 8.4208 kWh experiment is unchanged.

## 9. Files

```
results/continuous_distributed_effort/
  deterministic_raw.csv    1068 rows (grid + sleep sub-sweep)
  stochastic_raw.csv       2000 rows (4 modes x 5 N x 100 seeds, fresh subprocess)
  summary_statistics.csv   per (N, mode): mean/median/std/pct/bootstrap CI
  paired_comparisons.csv   B vs A / C1 / C2 (+ TOST for B vs C1)
  per_miner_energy.csv     per-miner ACTIVE/IDLE/SLEEP energy (representative)
  configuration.json  reproducibility_manifest.json
```
