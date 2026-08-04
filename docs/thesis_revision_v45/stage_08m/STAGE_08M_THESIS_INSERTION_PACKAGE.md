# Stage 8M — Thesis Insertion Package

**No thesis DOCX or PDF is edited by this stage.** This package contains insertion-ready
text, tables and figure data for a later, separately-authorized insertion stage. Every
number below is traceable to `stage8m_results.json` and the frozen Stage-7M dataset
(SHA-256 `be4bd0174730fa1f…`).

---

## I.1 Suggested experimental-design paragraph

> The confirmatory evaluation of the PoCol idle policy uses a preregistered,
> resource-minimal design (Stage 6M): three scenarios at the frozen 20-miner core
> (heterogeneous idle, homogeneous idle, and heterogeneous idle with the accepted
> 0.80 × H0 operational floor), each executed on the same ten preregistered seeds
> (30 physical runs), with a within-run power-null counterfactual computed from the same
> residency ledger under an executably-proven price-substitution invariance. The design,
> seeds, outcomes, decision rules and analysis code were frozen and committed before any
> confirmatory seed executed; two descriptive 141-miner scale checks are reported
> separately and enter no inference. An earlier, larger preregistration (660 logical rows)
> was superseded before data collection solely for measured computational infeasibility.

## I.2 Suggested results paragraph (H-M1 / H-M2)

> Across the ten paired seeds, the idle policy reduced energy by a mean of 0.0193 kWh per
> 300 s run against the within-run power-null counterfactual — a mean relative reduction
> of 53.9 % (bootstrap 95 % CI [53.7 %, 54.0 %]; exact paired sign-permutation
> p = 0.00098, the minimum attainable at n = 10; every seed showed a reduction of at least
> 53.5 %). Under homogeneous hash rates the reduction remains large but smaller
> (44.6 %, 95 % CI [44.3 %, 44.8 %], descriptive), showing the mechanism's sensitivity to
> rate heterogeneity. The preregistered H-M1 criteria are all met.

## I.3 Suggested results paragraph (H-M3 and the overall verdict) — REQUIRED wording

> Under the accepted operational floor (0.80 × H0, minimum-cardinality reserve selection,
> zero tolerance, CONTINUE_DEGRADED), the preregistered service limits were exceeded:
> accepted-block throughput fell to a mean ratio of 0.824 against same-seed control
> (95 % CI [0.805, 0.843]; limit ≥ 0.90), and the system spent a mean of 274.8 s of the
> 300 s horizon below the measured floor (limit ≤ 15 s), with 10 362 floor-unattainable
> observations across the ten runs; round durations were unaffected (ratio 1.001) and no
> activation request was left non-terminal. This outcome realises a structural risk
> declared in the preregistration before execution: the accepted engine excludes
> still-WAKING primaries from effective capacity, so wake ramps count as below-floor time.
> Under the frozen joint decision rule (energy claim only if H-M1 passes AND H-M3 stays
> within limits), **no unconditional energy claim is made**. The preregistered conclusion
> is: the idle policy within PoCol yields a large, consistent energy reduction,
> accompanied by operational capacity degradation when the accepted 0.80 × H0 floor is
> enforced under the accepted engine's wake semantics.

## I.4 Main table (insertion-ready)

| contrast | n | mean | 95 % CI | exact p | verdict |
|---|---|---|---|---|---|
| H-M1 energy reduction (abs, kWh) | 10 | 0.019303 | [0.019258, 0.019343] | 0.00098 | PASS |
| H-M1 energy reduction (relative) | 10 | 0.5387 | [0.5374, 0.5398] | — | PASS (≥ 0.05) |
| H-M2 relative reduction (descriptive) | 10 | 0.4456 | [0.4431, 0.4480] | — | descriptive |
| H-M3 accepted-blocks ratio (M03/M01) | 10 | 0.8242 | [0.8053, 0.8430] | — | **FAIL** (≥ 0.90) |
| H-M3 median-round-duration ratio | 10 | 1.0008 | [0.9876, 1.0136] | — | PASS (≤ 1.10) |
| H-M3 below-floor duration (s, mean/max) | 10 | 274.82 / 275.74 | — | — | **FAIL** (≤ 15) |
| H-M3 floor-unattainable count (total) | 10 | 10 362 | — | — | reported |
| Overall energy claim (frozen rule) | — | — | — | — | **NOT LICENSED** |

## I.5 Per-seed data for figures

Per-seed vectors (relative reductions, block ratios, duration ratios, below-floor times)
are in `stage8m_results.json`; per-run raw values are in the frozen
`STAGE_07M_CONFIRMATORY_DATASET.csv`. Suggested figures: (a) paired dot plot of
E_idle vs E_power_null per seed (M01); (b) per-seed accepted-blocks ratio against the 0.90
limit line; (c) below-floor duration per seed against the 15 s limit line.

## I.6 Mandatory caveats to accompany any insertion

The seven prominent statements of `STAGE_08M_LIMITATIONS.md` (reduced-resource design;
20-miner primary confirmatory scale; 10 paired seeds; two descriptive 141-miner sanity
checks; leases/adversarial/incentive mechanisms executably validated but not in the
confirmatory matrix; no broad security or incentive claim; no unconditional PoCol
energy-reduction claim) must appear with any thesis text derived from this package.
