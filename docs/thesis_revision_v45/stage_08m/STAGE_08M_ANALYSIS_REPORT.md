# Stage 8M — Preregistered Minimal Analysis Report

**Branch:** `thesis-v45-pocol-stage8m-minimal-analysis`.
**Input:** ONLY the frozen 30-row confirmatory dataset
`docs/thesis_revision_v45/stage_07m/STAGE_07M_CONFIRMATORY_DATASET.csv`
(SHA-256 `be4bd0174730fa1f…`, recorded in full in `stage8m_results.json`).
**Plan:** `docs/thesis_revision_v45/stage_06m/STAGE_06M_ANALYSIS_PLAN.md`, executed verbatim
by `experiments/thesis_revision_v45/stage_08m/analyze_8m.py` with the frozen analysis seed
**13165134141831138817**, all 2¹⁰ = 1024 sign assignments, and 10 000 paired bootstrap
resamples.

## Prominent scope statement (read first)

* This is a **reduced-resource design**: the confirmatory scale is **20 miners**, horizon
  300 s, with **10 paired seeds** per contrast.
* Two **descriptive 141-miner sanity checks** exist (X01/X02); they are non-inferential and
  enter no estimator here.
* Range leases, reassignment, the adversarial model and the incentive model are **validated
  executably** by the accepted 195-test suite but are **not included in the minimal
  confirmatory matrix**.
* **No broad security or incentive claim is made.**
* **No unconditional PoCol energy-reduction claim is made.** Every claim below is
  conditional on this configuration and its frozen decision rules.

## 0. Deterministic integrity gates — ALL PASS

All 30 runs are `COMPLETED` and pass every preregistered deterministic gate (energy-identity
residual ≤ 1e-8 J; residency-partition residual ≤ 1e-9 s; all forbidden counts exactly 0;
|E_power_null − A1_core| ≤ 1e-9 kWh with zero offline residency). Per-run values:
`STAGE_08M_INTEGRITY_RESULTS.csv`. Inference is therefore not blocked.

## 1. H-M1 — heterogeneous idle-energy reduction (M01 vs within-run power null): **PASS**

d_i = E_power_null(i) − E_idle(i) over the 10 paired seeds.

| estimand | value |
|---|---|
| paired mean reduction | **0.019303 kWh** (median 0.019312) |
| bootstrap 95 % CI of the mean | **[0.019258, 0.019343] kWh** |
| mean per-seed relative reduction | **0.5387** (53.87 %; median 0.5390) |
| bootstrap 95 % CI (relative) | [0.5374, 0.5398] |
| per-seed relative reductions | 0.5346 … 0.5415 (all 10 the same direction) |
| exact one-sided sign-permutation p | **0.0009765625** (= 1/1024, the minimum attainable) |

| preregistered criterion | value | verdict |
|---|---|---|
| mean relative reduction ≥ 5 % | 53.87 % | PASS |
| bootstrap 95 % lower bound of mean(d) > 0 | 0.019258 kWh | PASS |
| exact permutation p < 0.05 | 0.0009765625 | PASS |

**H-M1 decision: PASS.** Under the frozen 20-miner core, the idle policy within PoCol
reduces energy by ≈ 54 % relative to the within-run power-null counterfactual, consistently
across all 10 seeds.

## 2. H-M2 — homogeneous sensitivity (M02): descriptive only

Mean paired reduction 0.015967 kWh (95 % CI [0.015879, 0.016054]); mean relative reduction
**0.4456** (95 % CI [0.4431, 0.4480]). The reduction persists under homogeneous hash rates
but is smaller than under heterogeneity (44.6 % vs 53.9 %): the mechanism is sensitive to
rate heterogeneity, as the design anticipated. **No pass/fail, no equivalence claim, no
generalisation** — exactly as preregistered.

## 3. H-M3 — operational floor and service limits (M03 vs M01, same seed): **LIMITS EXCEEDED**

| preregistered limit | observed | verdict |
|---|---|---|
| accepted_blocks ratio ≥ 0.90 | mean **0.8242** (95 % CI [0.8053, 0.8430]; per-seed 0.778–0.872) | **FAIL** (both mean and every-seed readings) |
| median_round_duration ratio ≤ 1.10 | mean 1.0008 (95 % CI [0.9876, 1.0136]) | PASS |
| total_duration_below_floor ≤ 15 s | mean **274.82 s**, max 275.74 s (of a 300 s horizon) | **FAIL** (every run; ~92 % of horizon) |
| nonterminal_activation_request_count = 0 | 0 in all 10 runs | PASS |
| floor_unattainable_count (honest report) | per-seed 951–1159; **total 10 362** | reported |

**H-M3 decision: LIMITS EXCEEDED.** This is precisely the structural risk **declared before
execution** in the preregistration (§7): the accepted engine excludes still-WAKING primaries
from `H_effective`, so wake ramps count as below-floor time; with a 0.80 × H0 floor, zero
tolerance, and only 4 reserves, the M03 system spent nearly the whole horizon below the
measured floor, the floor was frequently unattainable, and accepted throughput dropped
≈ 18 % against same-seed M01.

## 4. Preregistered overall decision

> **An energy claim is allowed only when H-M1 passes AND H-M3 remains within its limits.**

H-M1 **passes**; H-M3 is **outside its limits**. Therefore, under the frozen rule:

**The conditional energy claim is NOT LICENSED.** The preregistered conclusion for exactly
this outcome, frozen before execution, applies verbatim: **the idle policy within PoCol
yields a large, consistent energy reduction, accompanied by operational capacity
degradation when the accepted 0.80 × H0 operational floor is enforced under the accepted
engine's wake semantics — and it is reported as such.**

This is a finding, not a failure of the study: the design measured both halves of the
trade-off it was built to measure, and the decision rule did its job.

## 5. Files

| file | content |
|---|---|
| `STAGE_08M_EFFECT_ESTIMATES.csv` | all point estimates, CIs and the exact p |
| `STAGE_08M_HYPOTHESIS_DECISIONS.csv` | every criterion, its value and verdict |
| `STAGE_08M_INTEGRITY_RESULTS.csv` | per-run deterministic gate values |
| `STAGE_08M_SCALE_CHECK_REPORT.md` | the two descriptive 141-miner sanity checks |
| `STAGE_08M_LIMITATIONS.md` | scope limits (prominent) |
| `STAGE_08M_THESIS_INSERTION_PACKAGE.md` | insertion-ready text (no DOCX/PDF edited) |
| `experiments/thesis_revision_v45/stage_08m/stage8m_results.json` | full numeric record |
