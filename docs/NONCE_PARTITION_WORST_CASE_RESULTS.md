# Nonce-Partitioning Worst-Case Experiment — Results

**Branch:** `claude/pocol-disjoint-nonce-worst-case`
**Data:** `results/nonce_partition_worst_case/`
**Reproduce:** `python experiments/nonce_partition/run_matrix.py 30` then
`python -m pytest tests/test_nonce_partition.py -v`

> This experiment is **separate** from the corrected continuous-mining comparison
> (`results/corrected/`, unchanged). It answers a different question — see
> `docs/NONCE_PARTITION_SCOPE_AND_LIMITATIONS.md`. All savings below emerge from
> **actual attempt counts and active-time accounting**; energy is never divided
> by `N`.

---

## 1. Core example (M = 100, N = 10, valid nonce = 99)

| Mode | attempts/miner | total attempts | total energy |
|---|---:|---:|---:|
| A — Common-Template Duplicate-Search Baseline | 100 | **1000** | 1000 |
| B — PoCol Disjoint-Nonce Allocation | ≤ 10 | **100** | 100 |

Ratios: attempts `100/1000 = 0.1`, energy `0.1`, **reduction 90 %**, worst-case
wall-clock completion time `1/10`. Duplicate evaluations avoided: **900**.
(Automated: `tests/test_nonce_partition.py::test_core_example_M100_N10`.)

---

## 2. Deterministic worst-case matrix (valid nonce at final position)

Energy reduction `= 1 − 1/N`, **identical across all domain sizes**
(`M ∈ {100, 1 000, 1 000 000, 2³²}`), confirming the result is analytical and
independent of `M`:

| N | reduction | attempts A → B (M = 1 000) | wall-clock ratio |
|---:|---:|---|---:|
| 1 | 0.0 % | 1 000 → 1 000 | 1.0 |
| 2 | 50.0 % | 2 000 → 1 000 | 0.5 |
| 5 | 80.0 % | 5 000 → 1 000 | 0.2 |
| 10 | 90.0 % | 10 000 → 1 000 | 0.1 |
| 20 | 95.0 % | 20 000 → 1 000 | 0.05 |
| 50 | 98.0 % | 50 000 → 1 000 | 0.02 |
| 100 | 99.0 % | 100 000 → 1 000 | 0.01 |
| 200 | 99.5 % | 200 000 → 1 000 | 0.005 |
| 500 | 99.8 % | 500 000 → 1 000 | 0.002 |

- For every `(M, N)` with `M` divisible by `N`, the code **asserts** `A = N·M`,
  `B = M`, and reduction `= 1 − 1/N` (run_matrix.py + tests).
- The `2³²` domain (~4.29 × 10⁹ nonces) is evaluated **analytically** — no
  enumeration — using O(N) big-integer arithmetic.
- Non-divisible cases (e.g. `M = 2³²`, `N = 5`) report the **honest actual**
  count (`B = M − rem`), which rounds to the same reduction at display precision
  but is stored exactly in `deterministic_results.csv`.

Full 36-row table: `results/nonce_partition_worst_case/deterministic_results.csv`.

---

## 3. Stochastic experiment (M = 2³², p = 2⁻³¹, 30 paired seeds)

`p = 2⁻³¹` gives `E[successes] = M·p = 2` per shared template, so domain
exhaustion is possible (`≈ e⁻² ≈ 13.5 %`). Zero/one/many successes all occur.

### 3.1 Mean total attempts (30 seeds; 95 % CI, normal approx)

| N | A duplicate (mean) | B disjoint (mean) | C independent (mean) |
|---:|---:|---:|---:|
| 100 | 1.796 × 10¹¹ | 2.521 × 10⁹ | 1.134 × 10⁹ |
| 200 | 3.592 × 10¹¹ | 2.322 × 10⁹ | 1.261 × 10⁹ |
| 300 | 5.389 × 10¹¹ | 2.552 × 10⁹ | 1.434 × 10⁹ |
| 400 | 7.185 × 10¹¹ | 2.353 × 10⁹ | 1.675 × 10⁹ |
| 500 | 8.981 × 10¹¹ | 2.726 × 10⁹ | 2.077 × 10⁹ |

Per-N 95 % CIs, medians, std, energy, completion time and exhaustion probability:
`results/nonce_partition_worst_case/stochastic_summary.csv`.

### 3.2 What the stochastic numbers show

1. **A (duplicate) scales with `N`** — total attempts ≈ `N × (shared first-success
   position)`. This is the pure-redundancy cost: at `N = 500` the baseline does
   ~9 × 10¹¹ evaluations.
2. **B (disjoint) is roughly flat in `N`** (~2.3–2.7 × 10⁹) — the domain is
   covered once, so adding miners does not multiply the work.
3. **C (independent) is also roughly flat** (~1.1–2.1 × 10⁹) and is the **same
   order of magnitude as B** — in fact **slightly lower**.
4. **Duplicate complete-header evaluations:** A carries ~1.78 × 10¹¹ (at N=100)
   up to ~8.96 × 10¹¹ (at N=500); **B and C carry exactly 0.**
5. **Exhaustion probability:** ~0.10 for the shared-template modes A and B
   (matching the per-template `e⁻²`), but **~0 for C** — with `N` independent
   searches the network almost always finds a solution.
6. **Paired effect size vs the baseline (Cohen's d on attempts):** B ≈ −1.28 and
   C ≈ −1.28 — a large reduction relative to A, and **statistically
   indistinguishable between B and C.**

### 3.3 The decisive comparison

> Disjoint allocation (B) beats the **duplicate baseline** (A) by ~2 orders of
> magnitude, but does **not** beat **independent candidate headers** (C). B and C
> are the same order of magnitude, with B slightly *higher*.

This is the crux: the large saving of disjoint allocation exists **only relative
to the artificial exact-duplicate baseline**. Against a realistic model where
miners already differentiate their headers (mode C), disjoint nonce partitioning
provides **no energy advantage**. This is exactly consistent with **Finding 1**
(continuous mining with distinct work → PoCol is energy-neutral).

---

## 4. Two findings, side by side (do not combine)

| | Scenario | Result |
|---|---|---|
| **Finding 1** | Continuous full-network mining, equal aggregate hash rate, **distinct** candidate work | PoCol and PoW consume **equal** aggregate energy (`results/corrected/`, 8.4208 kWh). |
| **Finding 2** | **Common-template exact-duplicate-search worst case** | Disjoint nonce allocation reduces attempts/energy by **`1 − 1/N`** vs the duplicate baseline (deterministic), and by ~2 orders of magnitude stochastically — but **matches**, and does not beat, independent-header mining. |

Finding 2 is an upper bound on the *duplicate-search* saving. It is **not** a
statement about Bitcoin and **must not** be combined with Finding 1.

---

## 5. Test results

```
python -m pytest tests/ -v
```

- `tests/test_nonce_partition.py`: **23 passed** (core example + 12 invariants +
  partition edge cases).
- Full repository suite: **66 passed** (43 pre-existing + 23 new).

## 6. Files

```
results/nonce_partition_worst_case/
  deterministic_results.csv      36 rows (9 miner counts x 4 domain sizes)
  stochastic_raw_runs.csv        450 rows (3 modes x 5 miner counts x 30 seeds)
  stochastic_summary.csv         15 rows (per N x mode)
  configuration.json             axes, p, energy model, seed pairing
  reproducibility_manifest.json  git commit, versions, seeds, reproduce command
```
