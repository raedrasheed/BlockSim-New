# Stage 8S — Structural Feasibility Report (READ-ONLY, from frozen Stage-8R data)

**Baseline:** `thesis-v45-pocol-stage8r-controller-refinement` @
`12baeae0cbba54234723d6ec79e4216e4948c689` (fetched; clean worktree; 213 tests green;
Stage-8R manifest verified — the frozen dataset and analysis are unchanged).
**Inputs:** the frozen 48-row `STAGE_08R_RUN_DATASET.csv` and the three frozen Stage-8R
timelines only. Stage-8R was NOT rerun. Numeric record:
`STAGE_08S_STRUCTURAL_FEASIBILITY_METRICS.json`.

Labels: **[OBSERVED]** frozen record · **[DERIVED]** computed under stated assumptions ·
**[HYPOTHESIS]** interpretation · **[UNRESOLVED]** not derivable from frozen data.

## 1. The structural constants [OBSERVED/DERIVED]

| quantity | value |
|---|---|
| H0 (16 heterogeneous primaries) | 4 000 H |
| static floor 0.80 × H0 | 3 200 H |
| maximum reserve capacity (M016–M019: 100+200+300+400) | **1 000 H** |
| maximum physically useful capacity (H0 + reserves) | 5 000 H |
| per-round nonce domain / per-slot range | 1 600 / 80 nonces |

**[DERIVED]** The static floor is mathematically unattainable whenever active primary
capacity drops more than 1 800 H below H0 — i.e. as soon as the fastest 2–3 primaries
exhaust — regardless of any controller decision. Reconstructed at the timeline seeds:
**556 (R01), 523 (R02), 248 (R03)** observation periods per run in which
H_effective + the ENTIRE reserve pool < 3 200 H.

## 2. Below-floor time decomposed against remaining useful work [DERIVED]

Using the frozen evaluation ledgers (remaining unsearched nonces per round over time) at
the timeline seeds, with the criterion "a window is *usefully* deficient only if remaining
work exceeds what the active miners themselves will consume in it by ≥ 1 batch":

| timeline run | below static floor (s) | usefully deficient (s) | work-exhausted / useless (s) |
|---|---|---|---|
| R01 s00 | 275.0 | 263.7 | 11.3 |
| R02 s00 | 274.8 | 261.2 | 13.6 |
| R03 s00 | 227.0 | 200.0 | 27.0 |

**[HYPOTHESIS]** Most below-static-floor time still has assignable unsearched work — the
raw material for a work-conserving policy exists. But the assignable work is concentrated
in a FEW donor suffixes (each slot is only 80 nonces), so the *bounded* useful target
min(3 200, H_useful_available) will typically sit far below 3 200 in the round tail: the
useful-floor metric is expected to expose a much smaller — and actually actionable —
deficit than the static metric. **[UNRESOLVED]** per-seed decomposition (timelines exist
for 3 seeds only).

## 3. The decisive R03 finding: the 25-nonce arm never actually reassigned [OBSERVED]

From the frozen R03 timeline results schema:
`controller_suffix_reassignment_count = 1 198` trigger decisions, yet
`reassignment_requests_seated = 0`, `reassignment_requests_completed = 0`,
`leases_reassigned = 0`, and the frozen evaluation ledger contains **zero** reassigned-work
records (4 300 primary + 505 activated-reserve only).

**[DERIVED]** R03's floor improvement (below-floor 227.0 vs 275.0 s; deficit area −19 %)
therefore came from **tail truncation**: each trigger cancelled the slow donor's lease and
the ≤ 25-nonce suffix was closed *unassigned* (`no_eligible_miner_policy =
CONTINUE_WITH_UNASSIGNED_RANGE`), letting rounds close earlier — which also explains R03's
slightly LOWER accepted blocks (145.8 vs R01's 147.3): it dropped work instead of
conserving it. **[UNRESOLVED from frozen data]** exactly which eligibility filter emptied
the candidate list at trigger time; this is probed executably during Stage-8S
implementation and the answer is recorded in the implementation report.
**[HYPOTHESIS → design]** A useful policy must therefore (a) verify receivers BEFORE
disrupting the donor, (b) conserve the union of work exactly, and (c) prefer coarse
few-chunk splits over per-batch churn — precisely S8S-3/S8S-4.

## 4. Activation requests without useful outcome [OBSERVED]

Per-run means from the frozen dataset: R01 seats 312.8 requests, completes 196.4
(incomplete 116.3, workless-wake rate 0.372); R02 seats 593.7, completes 205.3
(incomplete 388.3, rate **0.654**). Every incomplete request burned wake energy and
restored nothing — the reserve-admission-control target of S8S-5.

## 5. Reassignment size statistics [OBSERVED]

Mean/median/max-simultaneous reassignment sizes are **not computable** for Stage-8R:
no reassignment was ever seated (§3). The counters exist in the frozen schema and are
zero. **[OBSERVED-absence]**

## 6. Blocks, rounds and energy (context) [OBSERVED]

R00 175.8 / R01 147.3 / R02 149.9 / R03 145.8 accepted blocks (223 / 187 / 191 / 189
closed rounds). Energy decomposition per run (means): range-idle difference 0.0060–0.0064
kWh and reserve standby 0.0046–0.0049 kWh dominate the saving in floor scenarios; wake
difference ≈ 0.0008; activated-reserve hashing cost ≈ 0.0004. Full per-seed table in the
metrics JSON.

## 7. Feasibility conclusion for the Stage-8S design [HYPOTHESIS, falsifiable]

The static 0.80 × H0 gate can never pass at this population (§1) — retaining it as a
PRIMARY gate would predetermine failure, which is why it becomes a SECONDARY historical
metric (S8S-1) while the bounded useful-work-aware target (S8S-2) becomes primary. The
throughput gap to R00 (~26 blocks) is concentrated in tail rounds whose remaining work
sits in few small suffixes; a work-conserving coarse repartition (S8S-4) plus reserve
admission control (S8S-5) attacks exactly that gap. Whether it is enough to reach the
0.90 throughput gate is the open question this FINAL experiment answers — in either
direction, honestly.
