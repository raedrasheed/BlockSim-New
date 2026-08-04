# Stage 6M — Resource-Minimal Confirmatory Preregistration

The smallest scientifically coherent experiment that tests the central energy claim of **the
idle policy within PoCol** and its operational security/service limits. Frozen BEFORE any
confirmatory seed executes. See `STAGE_06M_SUPERSESSION_NOTICE.md` for provenance.

## 1. Minimal confirmatory core (frozen)

```
num_miners = 20        horizon_T = 300.0 s     nonce_domain_size = 1600
difficulty = 1000      batch_size = 25         base_hash_rate = 100.0
reserve_fraction = 0.20
P_hash = 21.5 W   P_listen = 2.15 W   P_reserve = 2.15 W   P_wake = 10.75 W   P_offline = 0 W
range leases = DISABLED      reassignment = DISABLED
adversarial model = DISABLED incentive model = DISABLED
dynamic difficulty = FORBIDDEN (fixed target, fixed difficulty)
```

Analytical continuous-power reference:
`A1_core_kwh = 20 x 21.5 x 300 / 3_600_000 = 0.035833333333333335 kWh`
(reproduced executably by `a1_continuous_control_kwh` to <= 1e-9 kWh; `test_s6m_01`).

Derived population facts: 16 primaries (M000–M015), 4 reserves (M016–M019); initial
active-primary hash rate H0 = 4 000 (heterogeneous) / 1 600 (homogeneous).

## 2. Confirmatory scenarios (exactly three)

| id | heterogeneous | floor | other differences |
|---|---|---|---|
| `M01_HET_IDLE` | true | disabled | — |
| `M02_HOM_IDLE` | false | disabled | none vs M01 except heterogeneity (`test_s6m_02`) |
| `M03_HET_IDLE_FLOOR` | true | **enabled** | none vs M01 except the floor fields (`test_s6m_02`) |

M03 floor: `minimum_active_hash_rate = 0.80 x H0 = 3 200`, `MINIMUM_CARDINALITY`,
`ON_CAPACITY_CHANGE`, `activation_wake_latency = 1.0`, `floor_tolerance = 0.0`,
`floor_unattainable_policy = CONTINUE_DEGRADED`.

## 3. Seeds

The **first 10 existing confirmatory seeds** (Stage-6 registry, seed_index 0–9), unchanged.
No replacement seeds; no seeds added after viewing results. All three scenarios use the same
10 seeds. **3 x 10 = 30 confirmatory physical runs.**

## 4. Within-run power-null counterfactual

No separate power-control simulations. For every run, from the SAME residency ledger:

```
E_idle       = sum over states of P_state x t_state
E_power_null = P_hash x (t_hash + t_listen + t_reserve + t_wake) + P_offline x t_offline
```

where the state groups follow the accepted `per_miner_power` mapping verbatim
(`t_hash` includes ACTIVE_HASHING and EXHAUSTED_PENDING; `t_listen` includes
LOW_POWER_LISTEN and REGISTERED; OFFLINE and DISQUALIFIED are the offline group).

This substitution is **exact**, not approximate: `test_s6m_04` proves executably that
changing only `P_listen`, `P_reserve`, `P_wake` changes no round identity, no accepted block
count, no winner sequence (full event-log digest), no nonce evaluation ledger, no coverage
and no terminal disposition — only the energy accounting — and that the within-run
`E_power_null` equals, to 1e-12 kWh, the actual energy of a re-run with substituted prices.

Given zero offline residency, `E_power_null = A1_core`; this is an integrity gate
(<= 1e-9 kWh), not an assumption.

## 5. Structural pilot (pre-freeze; completed)

Two PILOT seeds (indexes 0, 1; disjoint from all confirmatory seeds) x {M01, M02, M03}.
All eleven structural gates passed on all six runs; **no pilot energy effect was computed,
recorded or inspected** (`test_s6m_06` asserts the output contains none). See
`STAGE_06M_PILOT_REPORT.md`.

## 6. Exploratory full-scale sanity checks (non-inferential)

`X01_SCALE_HET_IDLE` and `X02_SCALE_HET_IDLE_FLOOR`: 141 miners, horizon 300 s, domain 4 000,
batch 50, difficulty 1000; X02 adds the accepted operational floor
(0.80 x H0(141, het) = 22 480). One existing PILOT seed each (indexes 2 and 3). These runs
never enter permutation tests, bootstrap intervals or confirmatory evidence; they provide
runtime, memory, integrity and direction sanity only.

## 7. Hypotheses

**H-M1 — heterogeneous idle-energy reduction.** Condition M01; comparator within-run
`E_power_null`; primary estimand the paired mean of `E_power_null − E_idle` over the 10
seeds. Success requires ALL of: mean relative reduction >= 5 %; 95 % paired-bootstrap lower
bound > 0; exact paired sign-permutation p < 0.05 (one-sided, direction = reduction,
declared here).

**H-M2 — homogeneous sensitivity.** Condition M02, same comparator. Report mean, median,
95 % CI and relative difference. Mechanism-sensitivity only: no equivalence claim and no
generalisation beyond this configuration.

**H-M3 — operational floor and service.** Treatment M03; control M01 under the same seed.
Required limits: `accepted_blocks_M03 / accepted_blocks_M01 >= 0.90`;
`median_round_duration_M03 / median_round_duration_M01 <= 1.10`;
`total_duration_below_floor <= 0.05 x horizon_T = 15 s`;
`nonterminal_activation_request_count = 0`; `floor_unattainable_count` reported honestly.

**An energy claim is allowed only when H-M1 passes AND H-M3 remains within its limits.**
Known structural risk, declared before execution: the accepted engine excludes still-WAKING
primaries from `H_effective` (Stage-6 evidence, D-record IP-H7), so the per-round wake ramp
counts as below-floor time and the 15 s limit is at risk. The limit is frozen anyway; if it
fails, the preregistered conclusion is energy reduction accompanied by operational capacity
degradation, reported as such.

## 8. Deterministic integrity gates (every confirmatory run)

`maximum_energy_identity_residual_j <= 1e-8`;
`maximum_residency_partition_residual_s <= 1e-9`; and all of
`duplicate_nonce_count`, `post_round_evaluation_record_count`,
`post_round_evaluation_nonce_count`, `evaluation_missing_terminal_time_count`,
`physical_frontier_rewind_count`, `work_reward_union_residual`, `nonterminal_lease_count`,
`nonterminal_reassignment_request_count`, `adversarial_action_total` (the directive's
`nonterminal_adversarial_action_count`, mapped onto the accepted schema as the sum of all
adversarial action counters, which must be zero because the adversarial model is disabled)
**= 0**; plus `|E_power_null − A1_core| <= 1e-9 kWh` given zero offline residency.
A failed gate blocks the analysis; the engine is never modified.

## 9. What is NOT confirmatory here

No confirmatory matrices for range leases, reassignment, progress withholding, false
exhaustion, solution withholding, delayed-wake attacks, assignment splitting, virtual
identities, or rewards/penalties. The accepted 195 executable tests and the prior
deterministic evidence stand as **mechanism-validation** evidence: Stage-4 and Stage-5
mechanisms are executably validated but are not subjected to a new multi-seed confirmatory
matrix in the resource-minimal design. No broad attack-resistance or incentive claim is made,
and no unconditional PoCol energy-reduction claim is made.

## 10. Analysis

Inferential unit: one physical run under one master seed; n = 10 paired seeds. Exact paired
sign-permutation over all 2^10 = 1024 sign assignments; 10 000 paired bootstrap resamples;
fixed analysis seed **13165134141831138817** (the Stage-6 analysis seed, unchanged); 95 %
confidence intervals. Report paired mean difference, paired median difference, paired
relative difference, CI and exact permutation p. Rounds, miners and blocks are never
independent observations. No seeds are added post hoc. A wide interval or one including zero
is reported as inconclusive.
