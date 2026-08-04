# Stage 8R — Analysis Report (revised idle and reserve-control policy within PoCol)

**Input:** the frozen 48-row `STAGE_08R_RUN_DATASET.csv` only (SHA-256 in
`stage8r_results.json`). **Plan:** `STAGE_08R_PREREGISTRATION.md`, executed verbatim by
`analyze_8r.py` (n = 12 fresh paired seeds; all 4096 sign assignments; 10 000 paired
bootstrap resamples; analysis-seed root 5792508466225871155; Holm within {H-R1, H-R2,
H-R3}; analysis re-run byte-identical). All 48 runs pass every deterministic integrity
gate. R03 is exploratory and enters no estimator and no verdict.

## Historical conclusion (preserved, not rewritten)

> The legacy Stage-8M controller produced a large low-power-state energy difference but
> exceeded the operational service/capacity limits; its joint energy claim was NOT
> licensed.

Nothing below reinterprets that result; R01 re-executes the same legacy controller on
fresh seeds solely as the paired baseline.

## 1. Primary refinement family (R02 vs R01, Holm at α = 0.05)

| hypothesis | outcome (family input in bold) | paired mean Δ (R02−R01) | 95 % CI | exact p (one-sided) | Holm verdict |
|---|---|---|---|---|---|
| H-R1 service recovery | **accepted_blocks** (expect >) | **+2.67** | [+1.75, +3.67] | 0.00049 | **SUPPORTED** |
| H-R2 floor recovery | **total_duration_below_floor** (expect <) | **−0.54 s** | [−0.60, −0.46] | 0.00024 | **SUPPORTED** |
| | floor_deficit_area (supporting) | −3 069 hash·s | [−3 417, −2 660] | 0.00024 | (supporting) |
| | floor_unattainable_count (supporting) | **−948.1** (999.8 → 51.8) | [−990, −905] | 0.00024 | (supporting) |
| H-R3 activation churn | **activation_requests_seated** (expect <) | **+280.9** (312.8 → 593.7) | — | 1.0000 | **REFUTED** (direction reversed) |
| | activation_batches_seated (vs legacy per-request batches) | −164.3 | — | 0.00024 | (supporting, opposite picture) |
| | incomplete_activation_request_count | +272.0 | — | 1.0000 | (worse) |
| | activations_per_closed_round | +1.44 | — | 1.0000 | (worse) |

**Honest reading of H-R3.** The refinement collapsed *decision* churn exactly as designed —
164 fewer batch decisions and a 19-fold drop in floor-unattainable decisions (999.8 →
51.8) — but each predictive batch seats the whole 4-reserve pool at once (the deficit
always exceeds the pool, so minimum-cardinality selection under CONTINUE_DEGRADED is the
full pool), and it does so earlier and more often per round than the legacy incremental
path. Request volume therefore ROSE, and with it the incomplete-request count. The
preregistered family outcome (requests) is refuted and reported as such; no conclusion is
forced.

## 2. H-R4 operational acceptance (deterministic limits, R02 vs same-seed R00): **FAIL**

| limit | observed | verdict |
|---|---|---|
| mean accepted-blocks ratio R02/R00 ≥ 0.90 | **0.8519** | **FAIL** |
| mean median-round-duration ratio ≤ 1.10 | 0.9954 | PASS |
| mean below-floor duration ≤ 15 s | **274.12 s** | **FAIL** |
| nonterminal activation requests = 0 (every run) | 0 | PASS |
| duplicate nonces = 0 (every run) | 0 | PASS |
| post-round evaluation records = 0 (every run) | 0 | PASS |

## 3. H-R5 retained energy benefit (R02, within-run power null): **PASS**

Mean relative low-power-state reduction **0.5735** (95 % CI [0.5717, 0.5752]; requirement
≥ 0.20); mean absolute reduction 0.0206 kWh with bootstrap lower bound 0.0205 > 0. This is
a low-power-state accounting result, not an unconditional protocol comparison.

## 4. Overall preregistered verdict

> The revised-policy claim is licensed only when H-R4 passes AND H-R5 passes AND all
> integrity gates pass.

H-R5 passes; integrity passes; **H-R4 fails** ⇒ **the revised-policy claim is NOT
LICENSED.** The revised controller measurably improves throughput (+2.7 blocks, ratio to
no-floor control 0.837 → 0.852), trims the tail (p95 round duration 3.00 → 2.86 s) and
eliminates nearly all unattainable-decision churn — but it cannot make a **structurally
unattainable** floor attainable: the 4-reserve pool totals 1 000 H against a 3 200 H
floor, so the system still spends ≈ 274 s of 300 s below the floor. The binding
constraint is the reserve-pool capacity (a frozen population parameter), not the
controller's decision logic.

## 5. Final comparison (means over the 12 fresh seeds; R03 descriptive only)

| metric | R00 | R01 | R02 | R03 (expl.) |
|---|---|---|---|---|
| accepted blocks | 175.8 | 147.3 | 149.9 | 145.8 |
| closed rounds | 223.0 | 187.0 | 190.8 | 189.2 |
| blocks per closed round | 0.788 | 0.786 | 0.785 | 0.770 |
| median / mean / p95 round duration (s) | 1.17 / 1.35 / 2.00 | 1.17 / 1.61 / 3.00 | 1.17 / 1.57 / 2.86 | 1.17 / 1.59 / 2.81 |
| unclosed-tail duration (s) | 0.0 | 0.0 | 0.0 | 0.0 |
| below-floor duration (s) | 0.0 | 274.66 | 274.12 | **222.95** |
| floor deficit area (hash·s) | 0 | 834 234 | 831 165 | **679 400** |
| floor-unattainable count | 0 | 999.8 | 51.8 | 54.6 |
| activation requests seated / completed / incomplete | 0/0/0 | 312.8 / 196.4 / 116.3 | 593.7 / 205.3 / 388.3 | 589.0 / 216.3 / 372.7 |
| activation completion ratio | — | 0.628 | 0.346 | 0.367 |
| activation batches (episodes) | — | — | 148.4 (339.1) | 147.3 (336.4) |
| batches per episode (mean / max allowed) | — | — | 0.44 / 1 live | 0.44 / 1 live |
| duplicate batches prevented | — | — | 1 335.9 | 1 356.3 |
| prediction decisions / mean abs error / false-positive wakes / late wakes | — | — | 148.8 / 100.0 H / 0 / 190.3 | 147.8 / 100.0 H / 0 / 188.7 |
| max / time-weighted H_pipeline (H) | — | — | 5 000 / 1 004.8 | 5 000 / 1 096.6 |
| pipeline-above-target while physical-below-target (s) | — | — | 5.09 | 8.51 |
| controller suffix reassignments | — | — | — | 1 290.2 |
| E_idle (kWh) / relative reduction | 0.0165 / 0.539 | 0.0149 / 0.583 | 0.0153 / 0.574 | 0.0151 / 0.578 |
| duplicate nonces / post-round evals / integrity residuals | 0 / 0 / ≤ tol | 0 / 0 / ≤ tol | 0 / 0 / ≤ tol | 0 / 0 / ≤ tol |

**Which component produced each saving** (per-run means, `STAGE_08R_ENERGY_DECOMPOSITION.csv`):
in the floor scenarios the saving is dominated by **primary range-idle residency**
(R02: 0.0060 kWh) plus **reserve standby** (0.0047 kWh), with a small **wake-transient
difference** (0.0008 kWh); **activated-reserve hashing** costs only 0.0004 kWh. In R00 the
split shifts (reserve standby 0.0065 dominates, range-idle 0.0022) because floorless
rounds close at primary exhaustion instead of extending through wake/reserve tails.
Reserve/wake savings are never merged with range-idle savings.

**R03 (exploratory, no verdict):** the bounded 25-nonce suffix reassignment produced the
single largest floor improvement of any arm (below-floor −51.7 s and deficit area −155 k
hash·s vs R01) at zero throughput gain (145.8 blocks) and 1 290 reassignments per run —
direction-finding only, never confirmatory.

## 6. Prediction quality (R4, descriptive)

Every resolved prediction erred by exactly 100 H (one slowest-class miner's rate): the
forecast counts a miner as expiring within the lookahead while the event grid keeps it
active to the batch boundary. Zero false-positive wakes; 190 late wakes per run reflect
reactive episodes opened after the pool was already spent (structural, not a forecast
defect). H_pipeline stayed a reporting quantity: physical H_effective was never
substituted (R-TEST-02/03), and pipeline-above-target-while-physical-below covers only
≈ 5 s per run.
