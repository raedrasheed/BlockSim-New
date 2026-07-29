# STAGE 05A — Statistical Preregistration (frozen before Stage 5B)

Frozen before the full matrix executes. Seeds, hypotheses, outcomes, and
analysis rules below are fixed; they must not be changed after examining
outcomes. Seed schedule: `results/thesis_revision_v43/stage_05a/raw/seed_schedule.json`
(SHA-256 `6122dbd0…b13e10`, 30 seeds `20260201–20260230`). Matrix:
`STAGE_05A_FINAL_MATRIX.csv`.

---

## 1. Confirmatory hypotheses

- **H1 (duplicate coverage).** Under one common immutable template, B1 has a
  higher duplicate candidate-header evaluation rate than B2 and B3/C1.
  *Primary:* duplicate evaluation rate. *Secondary:* distinct coverage, energy
  per accepted block, exhaustion rate. **Direction:** B1 > B2 > B3/C1. *No claim
  of lower total energy.*
- **H2 (continuous-operation energy equivalence).** Under matched aggregate hash
  rate, active power, and duration, total energy of B0, B1, B2, B3/C1 is **equal
  within a predefined tolerance**, except for explicitly modelled coordination
  or state-duration differences. *Primary:* total energy. **Equivalence, not
  superiority.**
- **H3 (C2 idle mechanism).** C2 energy reduction, when observed, decomposes as
  active-time reduction + explicit idle-power consumption + explicit coordination.
  *Primary:* active energy, idle energy, total energy. *Does not assume a saving
  in the homogeneous equal-range baseline.*
- **H4 (homogeneous completion symmetry).** With homogeneous rates and equal
  ranges, range-completion times are ≈ equal → post-range idle opportunity ≈ 0.
  *Primary:* range-completion time distribution, idle duration.
- **H5 (heterogeneity & allocation).** With heterogeneous miners, equal ranges
  let fast miners complete early and idle; hash-rate-weighted ranges reduce
  completion imbalance and may reduce/eliminate that idle. *Primary:* idle
  duration, total energy, completion-time dispersion. **Trade-off, not guaranteed
  PoCol superiority.**
- **H6 (inactive miners).** ↑ inactive fraction → ↑ unsearched domain, ↑
  exhaustion/refresh, ↑ block latency; may ↓ raw active energy while ↑ energy per
  accepted block. *Primary:* unsearched range, exhausted generations, block
  interval, energy per accepted block.
- **H7 (propagation delay).** ↑ delay → ↑ legitimate stale rate, obsolete-event
  rejection classified separately. *Primary:* legitimate stale rate.
- **H8 (finite-domain μ).** ↓ μ → ↑ exhaustion probability and template-refresh
  frequency. *Primary:* exhausted generations, template refreshes, effective
  block interval.

## 2. Outcomes (frozen)

**Primary:** total energy; active energy; idle energy; energy per accepted
block; effective block interval; accepted block count; legitimate stale rate;
duplicate evaluation rate; exhaustion probability; unsearched nonce-domain
fraction.

**Secondary:** throughput; energy per transaction; confirmation-time proxy;
carbon conversion; template refresh count; coordination message/byte counts;
active-time distribution; idle-time distribution; range-completion dispersion;
event-queue peak and runtime.

**Exploratory / descriptive:** fairness indicators; per-miner coverage;
concentration diagnostics; reward proxies. **No inferential fairness/incentive
claims** (reward and Sybil mechanisms are not implemented).

## 3. Effect-size and equivalence rules

1. **Continuous-energy equivalence (H2):** tolerance derived from accounting
   precision, **not** an arbitrary percentage. Proposed: relative tolerance
   `1e-6` on total kWh (the observed simulator floating-point spread across seeds
   is ≤ ~1e-13; 1e-6 is a conservative accounting-precision band). B0/B1/B2/B3_C1
   declared equivalent iff all pairwise `|Δtotal|/mean < 1e-6`.
2. **Duplicate-rate (H1):** report absolute percentage-point difference, relative
   difference, and 95% CI (bootstrap over seeds).
3. **C2 energy reduction (H3):** absolute kWh difference, relative %, explicit
   active/idle decomposition, and 95% CI. Report the exact identity
   `saving = Σ idle_time·(P_active − P_idle)`.
4. **Stale rate (H7):** for zero observations, an exact one-sided binomial (or
   rule-of-three `3/n`) upper 95% bound with the denominator = number of accepted
   blocks (opportunities); otherwise a Wilson interval.
5. **Block interval:** mean, SD, 95% CI, and effect size relative to the
   configured target (600 s). **p-values are never used as sole evidence.**

## 4. Preregistration integrity
- Seeds are frozen (checksum above) and **not** selected after examining outcomes.
- B3 and C1 reference **one** underlying run (no pseudoreplication; see the
  `interpretation_labels="B3;C1"` field and `hypothesis_to_run.json`).
- Reused runs across hypotheses carry one `run_id`; Stage 6 will not count a
  physical simulation twice as independent data.
- Confirmatory hypotheses (H1–H8) and outcomes are frozen here **before** Stage 5B.
