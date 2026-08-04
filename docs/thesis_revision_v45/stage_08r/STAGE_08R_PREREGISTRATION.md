# Stage 8R — Preregistration (revised idle and reserve-control policy within PoCol)

Frozen and committed BEFORE any Stage-8R confirmatory seed executes. The algorithm remains
**PoCol**; the treatment is **the revised idle and reserve-control policy within PoCol**.
The accepted Stage-8M results stand unchanged and are never reinterpreted: the legacy
controller produced a large low-power-state energy difference but exceeded the operational
service/capacity limits, and its joint energy claim was NOT licensed.

## 1. Core (identical to the frozen Stage-6M core; every non-treatment field matches)

20 miners, horizon 300 s, nonce domain 1600, difficulty 1000 (fixed; dynamic difficulty
forbidden), batch 25, base rate 100.0, reserve fraction 0.20, powers 21.5 / 2.15 / 2.15 /
10.75 / 0.0 W, heterogeneous rates, adversarial/incentive disabled.
H0 = 4 000; floor minimum = 0.80 × H0 = 3 200 where enabled.

## 2. Scenarios (4)

| id | role | floor | controller mode | leases |
|---|---|---|---|---|
| `R00_NO_FLOOR` | confirmatory control | off | LEGACY_REACTIVE (vacuous) | off |
| `R01_LEGACY_FLOOR` | confirmatory baseline | 0.80 × H0, zero tolerance | LEGACY_REACTIVE (accepted M03 semantics) | off |
| `R02_REVISED_CONTROLLER` | confirmatory treatment | 0.80 × H0 | HYSTERESIS_PREDICTIVE | off |
| `R03_REVISED_PLUS_REASSIGNMENT` | **EXPLORATORY** | 0.80 × H0 | HYSTERESIS_PREDICTIVE_REASSIGNMENT | on (voluntary controller-triggered suffix reassignment only) |

R03 is exploratory and may never determine the main policy-success verdict.

## 3. Frozen controller constants (declared before the pilot; never tuned afterwards)

```
reactive_trigger_ratio = 0.78    central_target_ratio = 0.80    recovery_ratio = 0.82
lookahead  = activation_wake_latency = 1.0 s
cooldown   = activation_wake_latency = 1.0 s
reassignment_chunk = 25 nonces (or the smaller remaining suffix)
```

Rationale: a symmetric two-percentage-point engineering deadband around the previously
frozen 0.80 operational target. The central 0.80 target is NOT reinterpreted as a formal
security threshold. These values were frozen before the structural pilot ran and are not
tunable after seeing the pilot or the confirmatory results.

## 4. Fresh seeds (provably disjoint)

`SHA256("PoCol-v45-stage8r-pilot-"+i)` / `SHA256("PoCol-v45-stage8r-confirmatory-"+i)`,
first unsigned 64-bit big-endian value. 2 pilot seeds (structure only), 12 confirmatory
seeds used by ALL four scenarios; no seed replaced after execution. Executable proof
(`scenarios_8r.assert_seed_disjointness`): pilot ∩ confirmatory = ∅ and both are disjoint
from every seed of every previous registry (39 previous pilot/confirmatory/analysis
seeds). Analysis seed (bootstrap RNG root, never a simulation seed):
**5792508466225871155** = SHA256("PoCol-v45-stage8r-analysis-0") first u64.
Registry: `STAGE_08R_SEED_REGISTRY.csv`; matrix: `STAGE_08R_EXPERIMENT_MATRIX.csv`.

## 5. Structural pilot (completed BEFORE this freeze; structure only)

4 scenarios × 2 fresh pilot seeds = 8 runs, all COMPLETED with every integrity gate
passing; predictive activation fired and hysteresis prevented duplicate batches in every
predictive-mode run; every required dataset field exists; worst wall 4.39 s, worst RSS far
under limits (`experiments/thesis_revision_v45/stage_08r/pilot/structural_pilot_8r.json`).
No pilot effect magnitude changed any policy parameter.

## 6. Hypotheses (primary refinement family = H-R1, H-R2, H-R3, Holm-corrected)

* **H-R1 service recovery** — R02 vs R01, same seed. Primary outcome `accepted_blocks`;
  expected direction R02 > R01. Report paired mean and median difference, 95 % paired
  bootstrap CI, exact one-sided sign-permutation p over all 2¹² = 4096 assignments.
* **H-R2 floor recovery** — R02 vs R01. Primary outcomes `total_duration_below_floor`,
  `floor_deficit_area`, `floor_unattainable_count`; expected direction R02 < R01. The
  family-level H-R2 p-value is the Holm input from its FIRST-listed outcome
  (`total_duration_below_floor`); the other two are reported with their own intervals and
  p-values as supporting outcomes of the same hypothesis (declared here, before data).
* **H-R3 activation churn** — R02 vs R01. Primary outcomes `activation_batches_seated`
  (vs the legacy per-request seat count as R01's batch equivalent — in the legacy
  controller every seated request is its own decision batch), `activation_requests_seated`,
  `incomplete_activation_request_count`, `activations_per_closed_round`; expected
  direction R02 < R01. Holm input: `activation_requests_seated` (declared here).
* **H-R4 operational acceptance (deterministic limits, no p-values)** — R02 is
  operationally acceptable only if ALL of:
  mean(accepted_blocks_R02 / accepted_blocks_R00) ≥ 0.90;
  mean(median_round_duration_R02 / median_round_duration_R00) ≤ 1.10;
  mean(total_duration_below_floor_R02) ≤ 0.05 × horizon = 15 s;
  `nonterminal_activation_request_count` = 0,
  `duplicate_nonce_count` = 0 and `post_round_evaluation_record_count` = 0 for every run.
  These limits are frozen and not changed after execution.
* **H-R5 retained energy benefit** — for R02, the SAME within-run power-null accounting
  used in Stage 8M. Require mean relative low-power-state energy reduction ≥ 0.20 AND
  95 % bootstrap lower bound > 0. This is a low-power-state ACCOUNTING result, not an
  unconditional protocol comparison.

**The overall revised-policy claim is licensed only when H-R4 passes AND H-R5 passes AND
all integrity gates pass.** H-R1/H-R2/H-R3 characterise the mechanism; failures are
reported honestly; no successful policy conclusion is forced.

## 7. Analysis (frozen)

Inferential unit: one physical run under one fresh master seed; n = 12 paired seeds.
All 2¹² = 4096 exact sign assignments (one-sided in the preregistered direction);
10 000 paired bootstrap resamples; percentile 95 % CIs (lower = 250th, upper = 9 750th
order statistic); bootstrap RNG root 5792508466225871155 with per-estimator labeled
substreams `Random(f"{root}:{label}")`. **Holm correction within the primary family**
{H-R1, H-R2, H-R3} at α = 0.05 using the three declared family p-values. Miners, rounds,
blocks and activation events are never independent observations. Zero-block runs stay.
Wide or zero-including intervals are reported as inconclusive.

## 8. Deterministic integrity gates (every run)

energy-identity residual ≤ 1e-8 J; residency-partition residual ≤ 1e-9 s; and all of
duplicate_nonce_count, post_round_evaluation_record_count, post_round_evaluation_nonce_count,
evaluation_missing_terminal_time_count, physical_frontier_rewind_count,
work_reward_union_residual, nonterminal_lease_count, nonterminal_reassignment_request_count,
adversarial_action_total, nonterminal_activation_request_count, nonterminal_episode_count,
live_batch_after_close_count exactly 0; residency reconciles; round terminal times strictly
increasing. Any failure blocks inference.

## 9. Execution plan (after this freeze commit)

4 × 12 = 48 runs; at most 2 concurrent workers; atomic checkpoint after every run; compact
run-level outputs for every run; full diagnostic timelines ONLY for R01 seed 0, R02 seed 0
and R03 seed 0. Dataset: `STAGE_08R_RUN_DATASET.csv` (48 rows). No CI created or waited
for.

## 10. Energy and time decomposition (per run, frozen definitions)

Role-state components: PRIMARY_ACTIVE_HASHING (primary ACTIVE_HASHING + EXHAUSTED_PENDING),
PRIMARY_LOW_POWER_LISTEN, RESERVE_STANDBY (reserve RESERVE/LOW_POWER_LISTEN/REGISTERED),
RESERVE_WAKING, ACTIVATED_RESERVE_HASHING (reserve ACTIVE_HASHING + EXHAUSTED_PENDING),
OFFLINE (OFFLINE + DISQUALIFIED, any role), COORDINATION_AND_VERIFICATION (primary
REGISTERED + primary WAKING). For each component: residency, energy, and the component's
within-run power-null difference `(P_hash − P_state) × t` (non-offline states), whose sum
is exactly `E_power_null − E_idle`. Named outputs: range_idle_energy_difference,
reserve_standby_energy_difference, wake_energy_difference, activated_reserve_energy,
total_low_power_state_difference. Reserve/wake saving is never combined with range-idle
saving in one unlabeled component; the final interpretation must state which component
produced each saving.
