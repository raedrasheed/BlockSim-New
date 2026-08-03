# Stage 3 — Test Report

Machine evidence in `docs/thesis_revision_v45/stage_03/evidence/`: `pytest_stage3.log`
(full `pytest -v --durations=0`), `pytest_stage3.junit.xml` (JUnit XML),
`stage3_metrics.json` (deterministic security-floor / reserve / energy metrics). The
curated floor metrics are also mirrored at `STAGE_03_SECURITY_FLOOR_METRICS.json`.

## 1. Exact pytest command

```
python3 -m pytest tests/thesis_revision_v45/stage2/ -v \
    -p no:cacheprovider \
    --junitxml=docs/thesis_revision_v45/stage_03/evidence/pytest_stage3.junit.xml
```

The single directory `tests/thesis_revision_v45/stage2/` holds the complete Stage-2B +
Stage-3 suite, so this one command runs both.

## 2. Environment

| Field | Value |
|---|---|
| Python | 3.11.15 |
| pytest | 9.1.1 |
| pluggy | 1.6.0 |
| Platform | Linux-6.18.5-x86_64-with-glibc2.39 |
| Third-party deps | none (stdlib only) |

## 3. Commit provenance

| Field | Value |
|---|---|
| Branch | `thesis-v45-pocol-stage3-security-floor-reserve-activation` |
| Parent SHA | `1e495bda74144d86c08aa0549bd3d633033600c4` |
| Commit SHA | the resulting HEAD of this branch (a file cannot embed its own commit hash; retrievable via `git rev-parse HEAD` and recorded in the acceptance-review handoff) |

## 4. Collection / result summary

| Metric | Value |
|---|---|
| Collected | 56 |
| Passed | 56 |
| Failed | 0 |
| Skipped | 0 |
| Errors | 0 |
| Duration | 7.26 s |

Breakdown: 37 retained Stage-2B tests + 19 Stage-3 tests (S3-01…S3-18 plus one adapter
schema check, `test_s3_adapter_schema_stage3_fields`).

## 5. Complete Stage-3 test-name list (`test_stage3_security_floor.py`)

`test_s3_01_floor_satisfied_no_activation`,
`test_s3_02_breach_after_exhaust_seats_activation`,
`test_s3_03_waking_reserve_not_counted`,
`test_s3_04_completed_reserve_active_counts_and_hashes`,
`test_s3_05_minimal_sufficient_subset`,
`test_s3_06_two_runs_select_same_reserves_and_slices`,
`test_s3_07_primary_and_reserve_slices_disjoint_cover_domain`,
`test_s3_08_activated_reserve_searches_only_its_slice`,
`test_s3_09_ledger_zero_duplicate_across_primary_and_reserve`,
`test_s3_10_exact_replay_creates_no_second_activation`,
`test_s3_11_stale_cross_round_activation_no_effect`,
`test_s3_12_pool_insufficient_floor_unattainable_reports_residual`,
`test_s3_13_continue_degraded_accumulates_exact_duration_below_floor`,
`test_s3_14_abort_round_closes_through_owner_no_live_activation`,
`test_s3_15_closure_cancels_pending_waking_and_terminalises_slices`,
`test_s3_16_reserve_energy_equals_residency_terms`,
`test_s3_17_floor_does_not_change_target_or_difficulty`,
`test_s3_18_full_domain_no_block_includes_reserve_slices_once`.

## 6. Retained Stage-2B test results

All 37 accepted Stage-2B tests rerun and pass unchanged (the floor is disabled by default,
so Stage-2B behaviour is identical):

- Semantic vectors TV325–TV338 (14) — pass.
- E2E-1…E2E-5 (5) — pass.
- SCI-1…SCI-10 + S2B-1 target tests (14) — pass.
- Adapter (4) — pass. The only change is `schema_version == "stage3.1"` (declared Stage-3
  bump), not a regression.

## 7. Security-floor / reserve / energy metrics (`evidence/stage3_metrics.json`)

Canonical floor scenario (4 miners, 2 reserve, D=400, min_active_hash_rate=250, zero-solution target):

| Metric | Value |
|---|---|
| Rounds | 49 |
| Floor observations | 342 |
| Distinct breaches | 146 |
| Activation decisions | 195 |
| Reserve activations seated / completed / cancelled | 98 / 98 / 0 |
| Floor-unattainable events | 48 |
| Total duration below floor | 98.0 |
| Maximum hash-rate deficit | 250.0 |
| Activated-reserve evaluations | 9,750 |
| **Nonce duplicate count** | **0** |
| **Post-round evaluation count** | **0** |
| **Max searched-count / time residual** | **2.84e-12** |
| **Max reserve energy-identity residual (J)** | **0.0** |
| Residency reconciles | True |

Floor-unattainable scenarios (min far above total capacity):

| Scenario | Result |
|---|---|
| CONTINUE_DEGRADED | run completes; residual reported; duration below floor = 57.0 (independently recomputed, S3-13) |
| ABORT_ROUND | 99 rounds closed via the closure owner with reason `security_floor_unattainable`; no live activation |

Adapter: `schema_version = "stage3.1"`; all Stage-3 security fields present.

## 8. Reproduction

```
git checkout thesis-v45-pocol-stage3-security-floor-reserve-activation
python3 -m pytest tests/thesis_revision_v45/stage2/ -v --durations=0
python3 -m Models.PoCol.stage2.demo
```

Deterministic (fixed SHA-256 targets, deterministic reserve ordering; no wall-clock / RNG /
network), so a re-run reproduces the metrics above.
