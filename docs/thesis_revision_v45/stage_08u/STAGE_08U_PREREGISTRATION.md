# Stage 8U — Preregistration (FROZEN at COMMIT 2, before any confirmatory seed)

This document freezes the Stage-8U experiment: the matched PoW-versus-PoCol comparison
of **the single-handoff useful-work policy within PoCol**.  It is committed BEFORE any
CONFIRMATORY seed is executed.  After this freeze nothing may be tuned: no seed, margin,
acceptance threshold, target, difficulty or scenario definition changes.  This is the
FINAL refinement cycle: if the joint acceptance rule fails, the result is preserved
honestly — there is no Stage 8V and Stage 9 is not begun.

Naming discipline (binding for every report and figure): the algorithm is **PoCol**; the
new treatment is only ever "the single-handoff useful-work policy within PoCol"; the two
W-scenarios are the **matched same-template PoW control** (population-matched and
active-capacity-matched).  No W-scenario is ever described as any real-world network.

## 1. Frozen core (identical to Stage 6M/8R/8S)

20 miners (16 primaries M000–M015, 4 reserves M016–M019), heterogeneous actual rates
`base 100.0 × (1 + index mod 4)` (H0 = 4000 H, reserve pool 1000 H), horizon 300 s,
nonce domain 1600, difficulty 1000 with fixed target `floor((2^256−1)/1000)`, batch 25,
reserve fraction 0.20, static floor 3200 H (0.80·H0), wake latency 1.0 s, frozen powers
P_hash 21.5 / P_listen 2.15 / P_reserve 2.15 / P_wake 10.75 / P_offline 0.0 W.
Controller constants frozen at 0.78 / 0.80 / 0.82, lookahead = cooldown = wake latency,
25-nonce chunk.  Leases, adversarial and incentive models disabled.  Dynamic difficulty
does not exist anywhere.

## 2. Scenarios (exactly five; frozen in `scenarios_8u.py`)

| scenario_id | engine | role | definition |
|---|---|---|---|
| W00_POW_POPULATION_MATCHED | matched PoW | CONFIRMATORY_POW_CONTROL | all 20 nodes mine continuously |
| W01_POW_ACTIVE_CAPACITY_MATCHED | matched PoW | CONFIRMATORY_POW_CONTROL | exactly the 16 initial active miners mine; 4 non-mining standby nodes at P_reserve (explicitly labelled ARTIFICIAL capacity-matched control) |
| P00_POCOL_NO_FLOOR | PoCol engine | CONFIRMATORY_CONTROL | accepted heterogeneous idle-policy control, floor disabled (LEGACY_REACTIVE) |
| P01_POCOL_STAGE8S_COARSE | PoCol engine | CONFIRMATORY_BASELINE | the accepted Stage-8S S03 controller, unchanged (USEFUL_FLOOR_COARSE_REASSIGNMENT) |
| P02_POCOL_SINGLE_HANDOFF | PoCol engine | CONFIRMATORY_PRIMARY | the single-handoff useful-work policy within PoCol (USEFUL_FLOOR_SINGLE_HANDOFF, U1–U5) |

W00 and W01 are never merged, never averaged together, and answer different questions
(same population versus artificially matched active capacity).

**Matched-PoW semantics (frozen; implemented in `Models/PoCol/stage2/matched_pow.py`):**
identical per-round template stream (`make_template(f"round-{k}", 1000, 1600,
template_seed + k)` with `template_seed = child_seed(master_seed, "template")` — the
engine's own rule), identical SHA-256 primitive, fixed target/difficulty, horizon,
batch, actual rates and powers, identical acceptance point (first valid target-coupled
solution by simulation time, at the winning nonce's exact per-nonce completion time,
ties broken by (time, MinerID, nonce)) and stale-work cancellation at acceptance.  PoW
nodes search the FULL domain independently from deterministic seed-derived offsets
(`SHA256("pow-offset|{master_seed}|{round}|{miner}")[:8] mod 1600`) with wraparound;
overlap allowed and measured.  Declared closure rules: BLOCK at the exact first-solution
time (work not strictly earlier is cancelled); EXHAUSTED at the FIRST miner's
full-domain coverage (coverage proves the domain empty — the PoW-favourable minimal
rule); HORIZON truncation at 300 s (whole batches completing at or before closure
commit).  Oracle scans determine timing only and are never counted as physical work.
Recorded per run: total/unique/duplicate physical evaluations, every first valid
solution, post-round evaluation count (zero by construction, still asserted), energy and
residency identity residuals.

## 3. Seeds (fresh; SHA-256-derived; frozen in `STAGE_08U_SEED_REGISTRY.csv`)

`seed(tag, i) = int.from_bytes(SHA256(tag + str(i))[:8], "big")`.

* PILOT (2): `PoCol-v45-stage8u-pilot-{0,1}` → 801072209236353412,
  2069121140149646086.
* CONFIRMATORY (12): `PoCol-v45-stage8u-confirmatory-{0..11}` →
  7109416645113272217 … 13947008554506819547.
* ANALYSIS root: `PoCol-v45-stage8u-analysis-0` → 17618529829928476883.

All 15 seeds are executably disjoint (`scenarios_8u.assert_seed_disjointness()`) from
every seed of every previous registry: the Stage-6 registry used by 6M/7M/8M, the
Stage-8R registry and the Stage-8S registry — 69 previous seeds in total.

Runs: pilot 5 × 2 = 10 (already executed, STRUCTURE ONLY — see §7); confirmatory
5 × 12 = 60, none executed before this freeze.  The unit of analysis is the RUN
(one scenario × one seed); rounds, miners, events, hashes and chunks are NEVER treated
as independent observations.

## 4. Frozen outcome definitions (columns of `STAGE_08U_RUN_DATASET.csv`)

* **Total energy** `E_idle_kwh`: the run's executed wall-clock residency energy (for
  PoW runs this is the actual always-on energy; the within-PoCol power-null pair is
  reported for P-runs only and is NOT an executable PoW control).
* **Blocks** `rounds_accepted`; **closed rounds** `rounds_executed` (PoCol: rounds with
  terminal times; PoW: BLOCK + EXHAUSTED closures — the single horizon-truncated
  residual round is excluded from duration statistics and counted separately).
* **Round durations**: per-run `median_round_duration` and `p95_round_duration` over
  closed-round durations.
* **Evaluations**: `total/unique/duplicate_physical_evaluations` (PoCol: the committed
  evaluation-ledger totals, duplicates = the accepted duplicate_nonce_count, zero for
  honest runs; PoW: the causal committed counts with circular-arc-union uniqueness).
* **Efficiency**: `blocks_per_million_physical_evaluations`;
  `energy_per_accepted_block_kwh` (None/NA when a run has zero blocks — never
  imputed).
* **Churn** (P-runs): `activation_requests_seated / completed / cancelled`,
  `incomplete_activation_request_count`, `activations_per_closed_round`,
  `reassignments_per_closed_round` (coarse reassignments + committed handoffs),
  `handoffs_per_closed_round`.
* **Floors** (P-runs): `duration_below_static_floor`,
  `static_floor_deficit_area_hash_s`, `duration_below_useful_floor`,
  `useful_floor_deficit_area` — always all four, never merged.
* Handoff lifecycle (P02): the six U1 epoch counters and the six U4 fallback counters.

## 5. Hypotheses (frozen gates; evaluated ONLY on the 12 confirmatory seeds)

Let `mean_X(f)` be the mean of field f over scenario X's 12 confirmatory runs; paired
differences pair runs by seed index.

* **H-U1 (churn, P02 vs P01)** — ALL of:
  (a) `mean_P02(reassignments_per_closed_round) ≤ 1.0`;
  (b) `mean_P02(activation_requests_seated) < mean_P01(activation_requests_seated)`;
  (c) `mean_P02(incomplete_activation_request_count) <
      mean_P01(incomplete_activation_request_count)`.
* **H-U2 (service vs W01)** — BOTH of:
  (a) `mean_P02(rounds_accepted) / mean_W01(rounds_accepted) ≥ 0.90`;
  (b) `mean_P02(median_round_duration) / mean_W01(median_round_duration) ≤ 1.10`.
* **H-U3 (energy vs W01)** — BOTH of:
  (a) mean over seeds of the paired relative reduction
      `(E_W01 − E_P02)/E_W01 ≥ 0.20`;
  (b) the paired-bootstrap 95% CI lower bound of that mean is > 0.
* **H-U4 (vs W00)** — DESCRIPTIVE + INFERENTIAL SENSITIVITY ONLY, never a licensing
  gate: report energy, blocks, durations, total/unique/duplicate evaluations and energy
  per accepted block for P02 vs W00 with the same estimators, labelled SENSITIVITY.
* **H-U5 (structural health of P02)** — ALL of:
  (a) `mean_P02(duration_below_useful_floor) ≤ 15.0 s`;
  (b) nonterminal handoff epochs, activation requests, leases and reassignment
      requests are ZERO in every P02 run;
  (c) duplicate evaluations zero, post-round evaluations zero, physical-frontier
      rewinds zero in every P02 run.

**Licensing rule (joint):** the single-handoff policy claim is licensed iff
H-U1 ∧ H-U2 ∧ H-U3 ∧ H-U5 all hold AND every integrity gate passes in all 60 runs.
A partial pass is reported as NOT LICENSED with the failing gate(s) named.  If the rule
fails: no re-tuning, no new seeds, no Stage 8V; the honest result enters the thesis.

## 6. Frozen analysis plan (`analyze_8u.py`, COMMIT 3, byte-identical re-runs)

* n = 12 paired fresh seeds per scenario; runs are the unit of analysis.
* **Exact paired sign permutation**: all 2^12 = 4096 sign assignments of the paired
  differences; two-sided p = (#{|T_perm| ≥ |T_obs|}) / 4096 with T = mean difference.
* **Paired bootstrap**: B = 10 000 resamples of the 12 seed indices with replacement;
  percentile 95% CIs (sorted[249], sorted[9749]).  Deterministic substreams
  `random.Random(f"{ANALYSIS_SEED_8U}:{label}")` with ANALYSIS_SEED_8U =
  17618529829928476883; labels are the metric identifiers.
* **Holm step-down (α = 0.05) over EXACTLY these four p-values** (frozen family):
  1. P02 vs P01 paired difference in `activation_requests_seated`;
  2. P02 vs P01 paired difference in `incomplete_activation_request_count`;
  3. P02 vs W01 paired difference in `rounds_accepted`;
  4. P02 vs W01 paired difference in `E_idle_kwh`.
* Every other contrast (including every P02-vs-W00 statistic) is SENSITIVITY /
  descriptive and carries no licensing weight.
* No cross-stage inferential statistic: comparisons with historical Stage-8M/8R/8S
  results are descriptive only (FIG17).

## 7. Structural pilot (already executed; pilot seeds only)

`run_stage8u.py pilot`: 10/10 COMPLETED, every structural gate PASS (integrity fields
computable and passing; wall ≤ 2.98 s/run, RSS far below limit; the handoff occurs in
every P02 pilot run and honours contiguity/union/benefit/atomicity gates; ≤ 1 epoch and
≤ 1 reserve wake per round; PoW overlap measurable; PoW post-round evaluations zero; W00
and W01 separate).  Pilot data were used for STRUCTURE ONLY; every gate and margin above
is the directive's, unchanged after the pilot.  One harness defect was fixed during the
pilot (the one-wake-per-round integrity gate was mis-scoped onto the P01 coarse
baseline, which may legitimately seat several wakes per round; the gate is now applied
only to P02).  No engine, scenario, seed or margin changed.

## 8. Figures (frozen plan; deterministic; FIG01–FIG18 of `figures_8u.FIGURE_SPECS`)

All 18 figures are generated programmatically (matplotlib), colour-blind-safe
(Okabe-Ito), no 3D, no truncated bars, paired per-seed points visible, means with 95%
CIs; each ships as SVG + 300-dpi PNG + source CSV + caption markdown + checksum, with
byte-identical tables and deterministic metadata on regeneration (U-TEST-22).  FIG05
shows NA for zero-block runs; FIG17 is descriptive only with NO cross-stage p-value;
FIG18 shows the frozen pass/fail criteria of §5.

## 9. Interpretation rules (binding)

This is a controlled simulator comparison under matched templates, rates, powers and
seeds — not a claim about any deployed network.  W00 and W01 answer different questions
and are reported separately.  The within-PoCol power-null counterfactual is not an
executable PoW control and is never presented as one.  Reserve/wake savings are reported
separately from range-idle savings.  No broad PoW-superiority, security or incentive
claim is made from this comparison; security and incentive analyses remain those of the
accepted earlier stages.

## 10. Stop rules

After COMMIT 3, exactly one stop token is issued:
`STAGE_8U_SINGLE_HANDOFF_POW_COMPARISON_COMPLETE_READY_FOR_REVIEW` on completion, or
`STAGE_8U_SINGLE_HANDOFF_POW_COMPARISON_BLOCKED` plus the blocker, the failed gate and
the minimum correction.  Whatever the outcome: no further tuning, no Stage 8V, no
Stage 9.
