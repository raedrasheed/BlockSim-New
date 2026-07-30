# Stage 6 — Secondary Diagnostics (H7 single-height stale-race)

`H7` is a **secondary diagnostic sensitivity**, not a confirmatory result (amended in
`STAGE_05B1G_PREREGISTRATION_AMENDMENT.md`). It measures, for one accepted height in
isolation, which non-winning miners would have published a competing block before
receiving the winner. It has **no** fork resolution, no cross-height / chain-reorg
semantics, and its energy and evaluations are deliberately **not** integrated into the
primary metrics. Machine-readable: `diagnostics/h7_secondary.json`,
`tables/table12_secondary_stale.csv`; figure `fig08_h7_delay_singleheight`.

## 1. Delay sensitivity of the single-height diagnostic

B3/C1 homogeneous equal, N∈{100,500}; 60 runs per delay level; 1,043 accepted blocks per
level (denominator = opportunities).

| delay (s) | runs | Σ single-height stales | stales / accepted block (mean) | interval estimate |
|-----------|-----:|------------------------:|-------------------------------:|-------------------|
| 0 | 60 | 0 | 0.0000 | rule-of-three UB 0.00288; exact one-sided binomial UB 0.00353 |
| 0.42 (baseline) | 60 | 1 | 0.0011 | Wilson 95% [0.00017, 0.00541] |
| 5 | 60 | 5 | 0.0050 | Wilson 95% [0.00205, 0.01117] |
| 30 | 60 | 47 | 0.0471 | Wilson 95% [0.03406, 0.05941] |
| 60 | 60 | 104 | 0.1005 | Wilson 95% [0.08297, 0.11939] |

The single-height stale rate rises **monotonically** with propagation delay, as amended
H7 anticipates: a larger `received_winner_time` widens the window in which a distinct
non-winning miner can find a competing solution. At delay 0 no stale is observed; the
zero-observation upper bound is reported (rule-of-three / exact binomial), not zero
certainty.

## 2. Primary-metric invariance under delay (`primary_invariance_across_delay`)

Seed-matched to the delay=0.42 baseline, delay-only variation leaves the primary outcomes
**exactly unchanged** (max absolute deviation 0 across all delays and N):

- `total_energy_kwh` — invariant
- `accepted_blocks` — invariant
- `total_candidate_evaluations` — invariant
- `total_active_time_s` — invariant

Only the single-height stale diagnostic and the per-delivery records vary with delay,
confirming the diagnostic is a bolt-on measurement that does not perturb the search or
energy accounting.

## 3. Scope guardrails (what this is NOT)

This diagnostic is **not** a full asynchronous blockchain-network simulation, **not** a
chain-wide fork-rate estimate, **not** a security proof, and **not** a multi-height
stale-chain model. It is a single-height stale-race sensitivity reported for
completeness. No confirmatory or security claim is drawn from it.
