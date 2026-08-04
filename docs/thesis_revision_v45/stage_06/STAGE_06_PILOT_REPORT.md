# Stage 6 — Pilot Report (FEASIBILITY ONLY)

Generated from `experiments/thesis_revision_v45/stage_06/pilot/pilot_results.json` by
`generate_pilot_report.py`. Every number below is read from the executed pilot.

> This report contains **no** condition-specific energy saving, **no** inferential
> effect estimate, **no** p-value, **no** confidence interval, **no** ranking of
> conditions by energy effect, and **no** claim about which hypothesis passed. The only
> energy quantities reported are deterministic accounting residuals with fixed numeric
> tolerances (IP-H1, IP-H2, IP-H5), which are integrity gates rather than effects.

**Pilot seeds only.** Every executed seed is drawn from the PILOT registry, which is
provably disjoint from the confirmatory registry. **No confirmatory seed was executed.**

---

## 1. Execution summary

| tier | planned | executed | completed | failed |
|---|---:|---:|---:|---:|
| Tier 1 (12 miners, 200 s, domain 400, batch 25) | 44 | 44 | 44 | 0 |
| Tier 2 (141 miners, 10 000 s, domain 4000, batch 50) | 3 | 3 | 3 | 0 |

## 2. Tier 1 — reduced-scale semantic pilot

All **22** frozen confirmatory scenario types executed, **2** pilot seeds each, **44** runs, **0** exceptions.

| measurement | value |
|---|---|
| wall clock per run | 0.036 s – 1.527 s (total 32.6 s) |
| peak RSS | 54 MB |
| results JSON bytes per run | 8,113 – 1,253,558 |
| event-log entries per run | 58 – 6,657 |
| rounds per run | 1 – 160 |
| adapter schema keys | 179 (stable across all runs) |
| zero-block runs | 3 |
| runs reporting `maximum_q_adv = NA` | 32 of 44 |
| exceptions | 0 |

### 2.1 Residency composition (the measurement behind decision D-03)

| state | seconds | share |
|---|---:|---:|
| `WAKING` | 63475.8 | 60.1 % |
| `LOW_POWER_LISTEN` | 13878.6 | 13.1 % |
| `RESERVE` | 11944.3 | 11.3 % |
| `ACTIVE_HASHING` | 11098.0 | 10.5 % |
| `OFFLINE` | 5203.3 | 4.9 % |
| `DISQUALIFIED` | 0.0 | 0.0 % |
| `EXHAUSTED_PENDING` | 0.0 | 0.0 % |
| `REGISTERED` | 0.0 | 0.0 % |

WAKING dominates because the 1.0 s wake latency is a large fraction of a ≈1.4 s round. This is why the idle-policy-off level must also raise `P_wake` to `P_hash`: otherwise the IP-H5 negative control would show a large spurious saving.

## 2b. Tier 2 — full-scale runtime pilot, per-run record

Four representative full-scale configurations — heterogeneous control (A03), heterogeneous idle policy (A05), security floor (B02) and genuine Path-B reassignment (C04) — each on **one fixed pilot seed**, each executed as an independent process with its own log and its own checkpoint file.

Only feasibility quantities are recorded. **No condition-specific energy saving, ranking, confidence interval, p-value or hypothesis verdict is reported from Tier 2.**

### A03

| field | value |
|---|---|
| scenario id | `A03` |
| pilot seed | `7592847024147398299` (pilot index 4) |
| completion status | **COMPLETED** |
| wall-clock seconds | 9813.6 |
| peak memory (MB RSS) | 3010 |
| output bytes (results JSON) | 12,010 |
| event count | 1,236,549 |
| round count | 9,580 |
| zero-block count | 0 |
| NA count by field | 2 (`maximum_q_adv`, `time_weighted_q_adv`) |
| exception count | 0 |
| integrity-gate failures | 0 (none) |
| log path | `experiments/thesis_revision_v45/stage_06/pilot/tier2/A03.log` |
| checkpoint path | `experiments/thesis_revision_v45/stage_06/pilot/tier2/A03.json` |

### A05

| field | value |
|---|---|
| scenario id | `A05` |
| pilot seed | `1103766790086696942` (pilot index 5) |
| completion status | **COMPLETED** |
| wall-clock seconds | 9914.3 |
| peak memory (MB RSS) | 3010 |
| output bytes (results JSON) | 12,039 |
| event count | 1,236,508 |
| round count | 9,579 |
| zero-block count | 0 |
| NA count by field | 3 (`equal_power_paired_residual_kwh`, `maximum_q_adv`, `time_weighted_q_adv`) |
| exception count | 0 |
| integrity-gate failures | 0 (none) |
| log path | `experiments/thesis_revision_v45/stage_06/pilot/tier2/A05.log` |
| checkpoint path | `experiments/thesis_revision_v45/stage_06/pilot/tier2/A05.json` |

### C04

| field | value |
|---|---|
| scenario id | `C04` |
| pilot seed | `16366577634683644678` (pilot index 7) |
| completion status | **COMPLETED** |
| wall-clock seconds | 15735.8 |
| peak memory (MB RSS) | 5266 |
| output bytes (results JSON) | 36,060,982 |
| event count | 1,232,233 |
| round count | 9,592 |
| zero-block count | 0 |
| NA count by field | 3 (`equal_power_paired_residual_kwh`, `maximum_q_adv`, `time_weighted_q_adv`) |
| exception count | 0 |
| integrity-gate failures | 0 (none) |
| log path | `experiments/thesis_revision_v45/stage_06/pilot/tier2/C04.log` |
| checkpoint path | `experiments/thesis_revision_v45/stage_06/pilot/tier2/C04.json` |

**Incomplete.** 3 of 4 required Tier-2 runs are recorded; missing: B02. Stage 6 is not ready for scientific freeze until all four are recorded.

## 3. Integrity gates

Every IP-H9 gate was **computable on every run** and evaluated over a **non-empty** evaluation ledger, so a zero is evidence rather than absence of activity.

| gate | maximum over all completed runs | runs non-zero |
|---|---:|---:|
| `duplicate_nonce_count` | 24 | 2 |
| `post_round_evaluation_record_count` | 0 | 0 |
| `post_round_evaluation_nonce_count` | 0 | 0 |
| `evaluation_missing_terminal_time_count` | 0 | 0 |
| `nonterminal_lease_count` | 0 | 0 |
| `nonterminal_reassignment_request_count` | 0 | 0 |
| `nonterminal_activation_request_count` | 0 | 0 |
| `physical_frontier_rewind_count` | 0 | 0 |
| `work_reward_union_residual` | 0.0 | 0 |

| accounting gate | maximum | tolerance | holds |
|---|---:|---:|---|
| `maximum_energy_identity_residual_j` (IP-H2) | 0.000e+00 | 1e-8 J | yes |
| `maximum_residency_partition_residual_s` (IP-H2) | 1.819e-12 | 1e-9 s | yes |
| `equal_power_paired_residual_kwh` (IP-H5) | 0.000e+00 | 1e-9 kWh | yes |

The IP-H5 precondition — zero OFFLINE and zero DISQUALIFIED residency — was verified rather than assumed on every run where the gate applies.

## 4. Scenario liveness

A zero integrity result is only evidence if the scenario really performed the behaviour it is named for.

| scenario | evidence that it is not vacuous |
|---|---|
| B02 / B03 | floor observations 2359 / 2385; breaches 191 / 194; activations completed 147 / 150 — the two rows are distinct |
| B04 | floor-unattainable count 2133 (vs 824 for B02); maximum deficit 4500.0 — DIAGNOSTIC row |
| C03 (Path A) | reassignments 32 with **0 wake handles** — a genuine Path A |
| C04 (Path B) | reassignments 307 with **305 wake handles** — a genuine Stage-3 reserve wake |
| C05 (no eligible miner) | 2 revocations, 0 reassignments — CONTINUE_WITH_UNASSIGNED_RANGE |
| C06 (full domain) | accepted blocks 0 — every round exhausts the domain with no block |
| D00 (honest control) | delayed wakes 0, withheld 0, false exhaustion accepted 0 — no attack occurs |
| D01 | delayed wakes 198 |
| D02 | solutions withheld 5, never released 5 |
| D03 | false exhaustion accepted 120 |
| D04 | progress withholding 1 — **see §5** |

## 5. IP-H10d matched feasibility pair (D04C / D04)

Progress withholding under-reports the **committed** frontier, so an intermediate committed frontier must exist when the lease is revoked. The frontier advances only at batch completion, so a batch boundary must fall strictly inside a primary's range:

```
nonce_domain_size / primary_count  >  batch_size
```

| configuration | nonces per primary | batch size | intermediate frontier possible |
|---|---:|---:|---|
| original D04 (reference batch size) | 35.4 | 50 | **no** |
| D04C / D04 pair | 35.4 | 25 | **yes** |

The IP-H10d feasibility runs are recorded in `experiments/thesis_revision_v45/stage_06/pilot/`.

### 5.1 The frozen pair on ALL EIGHT pilot seeds

The fault schedule is frozen and fully specified in [`STAGE_06_D04_FAULT_SCHEDULE_FREEZE.md`](STAGE_06_D04_FAULT_SCHEDULE_FREEZE.md). It is seed-independent, so this sweep can only show how often the modelled state is **reachable**; it is never used to re-tune the schedule.

| arm | seed index | status | wall (s) | withholding | accepted<actual | rewind | re-evaluated | duplicate prevented |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| D04 | 0 | COMPLETED | 0.90 | 1 | 1 | 0 | 12 | 12 |
| D04 | 1 | COMPLETED | 0.81 | 2 | 2 | 0 | 24 | 24 |
| D04 | 2 | COMPLETED | 0.84 | 1 | 1 | 0 | 12 | 12 |
| D04 | 3 | COMPLETED | 0.79 | 2 | 2 | 0 | 24 | 24 |
| D04 | 4 | COMPLETED | 0.81 | 2 | 2 | 0 | 24 | 24 |
| D04 | 5 | COMPLETED | 0.92 | 1 | 1 | 0 | 12 | 12 |
| D04 | 6 | COMPLETED | 0.84 | 2 | 2 | 0 | 24 | 24 |
| D04 | 7 | COMPLETED | 1.26 | 2 | 2 | 0 | 24 | 24 |
| D04C | 0 | COMPLETED | 1.08 | 0 | 0 | 0 | 0 | 0 |
| D04C | 1 | COMPLETED | 0.75 | 0 | 0 | 0 | 0 | 0 |
| D04C | 2 | COMPLETED | 0.81 | 0 | 0 | 0 | 0 | 0 |
| D04C | 3 | COMPLETED | 0.84 | 0 | 0 | 0 | 0 | 0 |
| D04C | 4 | COMPLETED | 0.73 | 0 | 0 | 0 | 0 | 0 |
| D04C | 5 | COMPLETED | 0.85 | 0 | 0 | 0 | 0 | 0 |
| D04C | 6 | COMPLETED | 0.91 | 0 | 0 | 0 | 0 | 0 |
| D04C | 7 | COMPLETED | 0.97 | 0 | 0 | 0 | 0 | 0 |

Runs: **16** (8 control, 8 treatment), all `COMPLETED`. Seeds producing no withholding action: **0 of 8**.

Every pilot seed is **retained**, including any that produces no withholding action; its zero-action result is recorded as shown. No seed is replaced and no seed is redrawn. These are feasibility measurements on seeds disjoint from the confirmatory registry — not a confirmatory result, and not an effect estimate.

## 6. Other feasibility observations

* **Adapter schema is stable** at 179 keys across every run; every preregistered outcome resolves against it.
* **Round terminal times are strictly increasing** in every run, so the derivation of `round_duration` from consecutive differences is verified, not assumed.
* **Residency reconciles** in every run.
* **C05 can degrade to a single unterminated round.** On one pilot seed C05 executed 1 round over the whole 200 s horizon with 596.6 s of OFFLINE residency. This is the declared CONTINUE_WITH_UNASSIGNED_RANGE behaviour — with no reassignment and no reserve pool, a failed miner's range stays unassigned and the round cannot close. It is a real property of the condition, not a defect, and it yields a legitimate zero-block run. The effect is amplified at Tier-1 scale, where the fault schedule removes 3 of 12 miners; at the confirmatory scale the same schedule touches at most 4 of 141.
* **IP-H7 risk.** With the floor enabled, the Tier-1 pilot measured `total_duration_below_floor` of 191.858 s against a 200 s horizon and `floor_unattainable_count` of 824. IP-H7's preregistered criteria are `floor_unattainable_count == 0` and `total_duration_below_floor <= 0.01 x horizon_T`, so the criterion is at risk. The cause is the accepted engine's deliberate semantics: `_pending_primary_capacity` excludes still-WAKING primaries from `H_effective`, so "the WAKING ramp is a real below-floor interval". **IP-H7 is frozen exactly as specified and the criterion is not weakened** — adjusting a success criterion because the pilot suggests it may not be met is precisely the forbidden use of pilot data. The risk is recorded here so the acceptance reviewer sees it before Stage 7.

