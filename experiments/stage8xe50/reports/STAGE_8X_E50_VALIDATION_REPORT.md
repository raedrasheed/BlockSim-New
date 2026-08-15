# Stage 8X-E50 — Validation Report

## 1. Automated test suite — 39/39 pass (all 20 required tests of brief §34)

| §34 test | Result |
|---|---|
| 1 S21 Pro arithmetic (234·15 = 3510) | pass |
| 2 2^32 nonce domain, valid bounds | pass |
| 3/4 PoCol partition coverage + disjointness (tiling, spread ≤ 1) at all N | pass |
| 5 MT same-template identity (ρ_exact > 0.98) | pass |
| 6 exact-duplicate counting = (N−1)/N to 2e-4 | pass |
| 7 unique-coverage union arithmetic (incl. wrap-around) | pass |
| 8 active-set size k = ⌈A·N⌉ at every (N, fraction) | pass |
| 9 deterministic epoch rotation | pass |
| 10 fairness rotation: duty exactly k per N-epoch cycle, window sum = k·2^32 | pass |
| 11 low-power energy identity E(α) = P(T_act + αT_low) | pass |
| 12 state-time conservation (0.0 measured) | pass |
| 13 same target across all scenarios at same N; q·D·2^32 = 1 | pass |
| 14 matched renewal rule MT vs PoCol (epoch seconds = assignment/h) | pass |
| 15 zero exact duplication in PoCol (R_exact = 0, all fractions) | pass |
| 16 analytical union coverage vs explicit enumeration on toy domains | pass |
| 17 domain-saturation handling: U_MT = h·T, U_PC = k·h·T (rel 1e-6) | pass |
| 18 NA handling at zero blocks (no fabricated intervals; NA propagates) | pass |
| 19 paired-seed reproducibility (bitwise) | pass |
| 20 α accounting-only (identical trajectory, monotone energies) | pass |

Plus: seed disjointness from Stage 8X/8X-NR/8Y/8Z registries; theory-surface
checks (saving = (1−k/N)(1−α); PC out-produces MT pooled).

## 2. Theory-vs-measurement

Every deterministic prediction of `STAGE_8X_E50_THEORY_REPORT.md` (written
before execution) was reproduced: MT ρ_exact = (N−1)/N (≤2e-4), U_MT = h·T
(≤1e-6 rel), U_PC = k·h·T, coverage retention = k, F_low = 1−k/N, savings
surface (1−k/N)(1−α) (≤1e-8 abs), E_block(PC) = E_block(CONV), and the LP50
maximum of 45.0 % — including the *negative* prediction that no tested point
reaches 50 % at α = 0.5.

## 3. Full-repository regression — 301/301 pass

legacy 11, Stage 8X 74, Stage 8Y 116, Stage 8X-NR 61, Stage 8X-E50 39.

## 4. Protected artifacts

500-file baseline (now including all of Stage 8X-NR alongside 6A/8S/8U in
results/docs/Models, original 8X, 8Y, 8Z, thesis documents, shared simulator
modules):

```
baseline_sha256 = 69576696669f4cac4fd364ddcae34de2df7959936d4d39c67e86cdddc11f056d
current_sha256  = 69576696669f4cac4fd364ddcae34de2df7959936d4d39c67e86cdddc11f056d  (OK)
```

Stage 8X-E50 wrote only under `experiments/stage8xe50/`. The single shared-code
touchpoint is a read-only import of `experiments.stage8xnr.src.noncedomain`
(union arithmetic), verified unmodified by the baseline.

## 5. Run audit

1500/1500 primary runs; 50 cells × exactly 30 seeds; zero identity violations;
no runs discarded (MT100 zero-block runs are retained as data); staged
execution completed in a single 1.6 s pass — no batch was stopped or altered
on outcome.
