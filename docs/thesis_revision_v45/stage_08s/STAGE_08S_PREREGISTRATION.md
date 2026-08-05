# Stage 8S — Preregistration (FINAL controller/operating-policy refinement)

Frozen and committed BEFORE any Stage-8S confirmatory seed executes. The algorithm remains
**PoCol**; the treatment is **the useful-work-aware idle and reserve-control policy within
PoCol**. This is the FINAL refinement cycle: if the gates below fail, the result is
preserved as-is — no further tuning, no Stage 8T, no seed/margin/target/difficulty change —
and remaining structural limitations become future work. The accepted Stage-8M and
Stage-8R findings are historical evidence and stand unchanged.

## 1. Core (identical to the frozen Stage-6M/8R core)

20 miners, horizon 300 s, nonce domain 1600, difficulty 1000 (fixed), batch 25, base rate
100.0, reserve fraction 0.20, frozen powers, heterogeneous rates,
leases/adversarial/incentive disabled. H0 = 4 000.

## 2. The two floors (S8S-1/S8S-2)

* **Static floor (historical, SECONDARY):** `H_static_floor = 0.80 × H0 = 3 200`, computed
  and reported in every run exactly as in Stages 8M/8R; never redefined; it does not
  determine H-S2.
* **Useful-work-aware target (PRIMARY):**
  `H_useful_target(t) = min(0.80 × H0, H_useful_available(t))`, where
  `H_useful_available(t)` counts only (1) ACTIVE_HASHING miners on a non-empty accepted
  range and (2) already-awake eligible receivers bounded by the spare whole batches active
  donors can cede (donor keeps ≥ 1 batch). WAKING miners, reserves, stale assignments,
  overlapping suffixes and any future-solution information are excluded; live wake
  requests appear only in H_pipeline. Declared clarifications: the DECISION reference
  counts receivers only in the coarse mode (the only mechanism that can deliver work to
  them); the REPORTED useful-floor metrics count receivers in every mode (mode-independent
  counterfactual, so scenarios are comparable). Both floors' duration/deficit-area/
  unattainable metrics are reported in every run and computed independently.

## 3. Scenarios (4; every non-treatment field identical)

| id | role | mode |
|---|---|---|
| `S00_NO_FLOOR` | control (denominator for H-S2/H-S4) | floor disabled |
| `S01_STAGE8R_STATIC_FLOOR` | baseline | `STAGE8R_PREDICTIVE_STATIC_FLOOR` (reproduces frozen R02 exactly; S8S-TEST-02) |
| `S02_USEFUL_FLOOR` | component comparison (descriptive) | `USEFUL_FLOOR_ONLY` |
| `S03_USEFUL_FLOOR_COARSE_REASSIGNMENT` | **PRIMARY** | useful target + receiver-first atomic coarse repartition + reserve admission control |

## 4. Frozen policy constants (not tunable after the pilot)

0.78 / 0.80 / 0.82 hysteresis; lookahead = cooldown = activation wake latency = 1.0 s;
coarse partition `part_count = min(1 + receivers, ceil(remaining/batch))` with
deterministic reduction so no non-final chunk is below one batch (accepted integer
apportionment; donor keeps the first chunk; one chunk per receiver; one repartition per
donor lineage per breach episode; one live chunk per receiver); the deterministic benefit
gate (post-split makespan must strictly beat the donor alone); receivers start
immediately (already awake — no wake transient); reserve wakes require an atomically bound
non-empty unclaimed slice, otherwise `activation_rejected_no_useful_work`.

## 5. Fresh seeds (provably disjoint)

`SHA256("PoCol-v45-stage8s-pilot-"+i)` (2 pilot),
`SHA256("PoCol-v45-stage8s-confirmatory-"+i)` (12 confirmatory, same seeds in every
scenario, none replaced after execution); analysis root
`SHA256("PoCol-v45-stage8s-analysis-0")` = **16767666002914861861**. Executable proof:
disjoint from all 54 previous registry seeds (Stage-6 registry + all Stage-8R seeds).
Registry: `STAGE_08S_SEED_REGISTRY.csv`; matrix: `STAGE_08S_EXPERIMENT_MATRIX.csv`.

## 6. Structural pilot (completed BEFORE this freeze; structure only)

4 scenarios × 2 fresh pilot seeds = 8 runs, all COMPLETED with every integrity gate
passing; useful-floor metrics exist in every run; coarse reassignment occurred in every
S03 pilot run with the chunk union/disjointness gates passing; reserve admission enforced
(every wake bound to useful work); worst wall 3.23 s. No parameter was tuned on pilot
output (`experiments/thesis_revision_v45/stage_08s/pilot/structural_pilot_8s.json`).

## 7. Hypotheses and decision rules

* **H-S1 throughput recovery** — S03 vs S01, primary outcome `accepted_blocks`, expected
  S03 > S01; exact paired sign permutation over all 2¹² = 4096 assignments (one-sided) and
  10 000-resample paired bootstrap with percentile 95 % CI.
* **H-S2 operational usefulness (deterministic acceptance)** — S03 vs S00:
  mean(accepted_blocks ratio) ≥ 0.90; mean(median-round-duration ratio) ≤ 1.10;
  mean `duration_below_useful_floor` ≤ 0.05 × horizon = 15 s; and for EVERY run:
  nonterminal activation/reassignment/lease counts = 0, duplicate_nonce_count = 0,
  post_round_evaluation_record_count = 0, physical_frontier_rewind_count = 0.
  The static-floor metric stays reported but does not determine H-S2.
* **H-S3 churn reduction** — S03 vs S01: mean `reassignments_per_closed_round` ≤ 1.0;
  mean `activation_requests_seated` < S01 with the Holm-corrected paired contrast
  rejecting; mean `incomplete_activation_request_count` < S01 with the Holm-corrected
  contrast rejecting; `reserve_wakes_rejected_no_useful_work` reported. A lower decision
  counter alone is never treated as churn reduction.
* **H-S4 retained energy benefit** — S03 within-run power-null accounting (identical to
  Stage 8M/8R): mean relative total low-power-state difference ≥ 0.20 AND the 95 %
  bootstrap lower bound of the mean absolute difference > 0; the four named components
  (range-idle, reserve-standby, wake, activated-reserve energy) reported separately.

**The overall structural-policy claim is licensed only when H-S2 AND H-S3 AND H-S4 pass
AND every deterministic integrity gate passes.** Failures are reported honestly; this is
the final cycle either way.

## 8. Analysis (frozen)

Unit: one physical run under one fresh master seed; n = 12 paired. 4096 exact sign
assignments; 10 000 paired bootstrap resamples; percentile 95 % CI (250th/9 750th order
statistics); bootstrap root 16767666002914861861 with labeled substreams. **Holm at
α = 0.05 over exactly three p-values:** H-S1 (accepted_blocks), H-S3 (activation-request
contrast), H-S3 (incomplete-request contrast). H-S2 and the integrity gates are
deterministic acceptance rules with no p-values. Miners, rounds, chunks and requests are
never independent observations; zero-block runs stay.

## 9. Execution plan (after this freeze commit)

4 × 12 = 48 runs; ≤ 2 concurrent workers; atomic checkpoint after every run; compact
run-level outputs for all 48; full diagnostic timelines ONLY for S01 seed 0, S02 seed 0,
S03 seed 0. Dataset: `STAGE_08S_RUN_DATASET.csv`. No CI.
