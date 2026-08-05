# Stage 8S — Thesis Insertion Package

**No thesis DOCX or PDF is edited by this stage.** Insertion-ready text for a later,
separately-authorized integration stage; every number traces to `stage8s_results.json`
and the frozen `STAGE_08S_RUN_DATASET.csv`. The caveats of `STAGE_08S_LIMITATIONS.md`
accompany any use.

## I.1 Design paragraph

> In the final refinement cycle, the useful-work-aware idle and reserve-control policy
> within PoCol replaced the unattainable static capacity comparison with a bounded target,
> H_useful_target(t) = min(0.80 × H0, H_useful_available(t)), and added a work-conserving
> coarse suffix repartition: when predicted useful capacity falls below the target,
> already-awake miners that finished their own ranges receive contiguous, near-equal,
> deterministically apportioned chunks of the largest unsearched suffix — receivers
> first, reserves only afterwards, and never a reserve wake without atomically bound
> useful work. The historical static floor remained reported unchanged as a secondary
> metric. The experiment was preregistered on twelve fresh seeds with frozen constants
> and a declared final-cycle rule: whatever the gates decide, no further tuning follows.

## I.2 Results paragraph (required honesty preserved)

> The work-conserving policy produced the largest throughput recovery of the program:
> +10.6 accepted blocks against the Stage-8R controller under the same seeds (95 % CI
> [+9.1, +12.1], exact paired p = 0.00024, Holm-corrected), reaching 90.4 % of the
> no-floor control — the first arm to satisfy the 0.90 throughput gate — by finishing
> tail-round work instead of dropping it (p95 round duration 2.86 s → 2.33 s at equal
> per-round success). It also retained the low-power-state accounting benefit (55.1 %,
> 95 % CI [55.0 %, 55.2 %]). Nevertheless, the preregistered joint rule does not license
> the structural-policy claim: time below the useful-work-aware floor fell by a third
> (42.3 s → 28.7 s) but remained above the frozen 15 s gate, and activation churn rose
> rather than fell (642 vs 597 seated requests; 1.75 reassignments per closed round
> against a 1.0 limit), since every recovered round brings its own activation cycle. As
> preregistered for this final cycle, the result is reported as-is: the useful-work-aware
> policy solves the throughput half of the operational problem and leaves the
> idle-capacity and churn half as an explicitly quantified open limitation.

## I.3 Main table

| contrast / gate | value | verdict |
|---|---|---|
| H-S1 accepted blocks, S03 − S01 | +10.58, CI [+9.08, +12.08], p = 0.00024 | supported (Holm) |
| H-S2 blocks ratio S03/S00 ≥ 0.90 | **0.9039** | PASS (first time in program) |
| H-S2 median-duration ratio ≤ 1.10 | 1.0005 | PASS |
| H-S2 below-useful-floor ≤ 15 s | 28.71 s | **FAIL** |
| H-S2 per-run integrity zeros | all 0 | PASS |
| H-S3 reassignments/round ≤ 1.0 | 1.748 | **FAIL** |
| H-S3 requests < S01 | 642.3 vs 596.7 | **FAIL** (p = 1.0) |
| H-S3 incomplete < S01 | 414.0 vs 386.7 | **FAIL** (p = 1.0) |
| H-S4 relative reduction ≥ 0.20 | 0.5505, CI [0.5495, 0.5515] | PASS |
| **Overall structural-policy claim** | — | **NOT LICENSED** |

## I.4 Component sentence

> The retained saving decomposes into reserve standby (0.00472 kWh per run), primary
> range-idle residency (0.00442 kWh) and the wake transient (0.00086 kWh), against an
> activated-reserve hashing cost of 0.00019 kWh; range-idle and reserve/wake components
> are reported separately throughout.

## I.5 Program-closing sentence

> Across Stages 8M, 8R and 8S the operational-floor problem was progressively decomposed:
> the static 0.80 × H0 floor is structurally unattainable at this population (a pool
> bound, not a controller defect); decision churn is removable (Stage 8R); throughput is
> recoverable to the 0.90 gate by conserving tail work (Stage 8S); and the remaining
> open items — idle-receiver seconds above the 15 s useful-floor gate and churn that
> scales with recovered rounds — are quantified and left, per the frozen final-cycle
> rule, as future work.
