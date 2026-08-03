# Stage 3A — Test Report

Machine evidence in `docs/thesis_revision_v45/stage_03a/evidence/`: `pytest_stage3a.log`
(full `pytest -v --durations=0`), `pytest_stage3a.junit.xml` (JUnit XML), `stage3a_metrics.json`
(deterministic correction metrics).  The curated floor metrics are mirrored at
`STAGE_03A_SECURITY_FLOOR_METRICS.json`.

## 1. Exact pytest command

```
python3 -m pytest tests/thesis_revision_v45/stage2/ -v --durations=0 \
    -p no:cacheprovider \
    --junitxml=docs/thesis_revision_v45/stage_03a/evidence/pytest_stage3a.junit.xml
```

The single directory `tests/thesis_revision_v45/stage2/` holds the complete Stage-2B +
Stage-3 + Stage-3A suite, so this one command runs all three.

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
| Branch | `thesis-v45-pocol-stage3a-security-floor-observation-activation-transaction-exhaustion-lock` |
| Parent SHA | `675995d5b1ff3845638e2402a26ab32dc7cf80fe` (rejected Stage-3 head) |
| Accepted Stage-2B baseline | `1e495bda74144d86c08aa0549bd3d633033600c4` (search core unchanged) |
| Commit SHA | the resulting HEAD of this branch (a file cannot embed its own commit hash; retrievable via `git rev-parse HEAD` and recorded in the acceptance-review handoff) |

## 4. Collection / result summary

| Metric | Value |
|---|---|
| Collected | 68 |
| Passed | 68 |
| Failed | 0 |
| Skipped | 0 |
| Errors | 0 |
| Duration | ~7.2 s |

Breakdown: 37 retained Stage-2B tests + 19 retained Stage-3 tests + 12 new Stage-3A tests
(S3A-01 … S3A-12).

## 5. Stage-3A test-name list (`test_stage3_security_floor.py`)

`test_s3a_01_active_hashing_missing_assignment_excluded`,
`test_s3a_02_sequential_wakes_observe_and_measure_initial_interval`,
`test_s3a_03_observation_key_replay_idempotent`,
`test_s3a_04_minimum_cardinality_selects_single_high_rate`,
`test_s3a_05_start_seat_failure_rolls_back`,
`test_s3a_06_complete_seat_failure_no_stranded_waking`,
`test_s3a_07_tampered_identity_no_effect`,
`test_s3a_08_completed_request_has_both_event_refs`,
`test_s3a_09_closure_terminalises_all_records_and_requests`,
`test_s3a_10_floor_zero_unused_reserve_domain_not_full_domain`,
`test_s3a_11_true_full_domain_exhaustion_covers_all_once`,
`test_s3a_12_adapter_enables_floor_and_activates_from_config`.

## 6. Retained tests

All 37 accepted Stage-2B tests and all 19 Stage-3 tests rerun and pass.  The floor is
disabled by default, so Stage-2B behaviour is identical.  The only test edits are: S3-03's
manually-built assignment now carries `RoundID`/`TemplateID` (matching the S3A-1 assignment
invariant), and the adapter schema-version assertions move `stage3.1` → `stage3a.1`.

## 7. Correction metrics (`evidence/stage3a_metrics.json`)

Deterministic; recomputed directly from executable state.  Across all five scenarios:
**nonce duplicate count = 0**, **post-round evaluation count = 0**, **max energy-identity
residual = 0.0 J**, **residency reconciles = True**, **non-terminal reserve records after
closure = 0**, **non-terminal activation requests after closure = 0**, **observation replay
count = 0** (the deterministic runs raise no key collision; S3A-03 exercises replay directly).

| Scenario | rounds | seated / completed | partial_rest. | floor_unattainable | full_domain | unused_reserve | complete-seat-fail | early-wake dur |
|---|---|---|---|---|---|---|---|---|
| canonical (min 250) | 74 | 148 / 146 | 0 | 74 | 73 | 0 | 2 | 74.0 |
| floor = 0 (unused reserve domain) | 150 | 0 / 0 | 0 | 0 | 0 | 149 | 0 | 0.0 |
| unattainable CONTINUE_DEGRADED | 129 | 258 / 256 | 129 | 899 | 128 | 0 | 2 | ~300.0 |
| unattainable ABORT_ROUND | 300 | 0 / 0 | 0 | 299 | 0 | 0 | 0 | ~300.0 |
| miner-count floor (min_count 3) | 110 | 218 / 218 | 0 | 545 | 109 | 0 | 0 | ~300.0 |

Notes:
- **Complete-seat-failure rollback is exercised naturally** (canonical / CONTINUE_DEGRADED:
  2 each) by reserve activations near the horizon whose CompleteEvent falls past `T`; the
  miner is never stranded (non-terminal counts stay 0).
- **`floor = 0` closes every round with the explicit unused-reserve-domain disposition**
  (149) and NEVER as full-domain exhaustion (0) — the reserve domain is not searched.
- **PARTIAL_RESTORATION** is exercised (CONTINUE_DEGRADED: 129) and **ABORT_ROUND** closes
  every unattainable round through the closure owner (299) with no live activation.
- **Early-wake below-floor duration** is positive (the real round-start-to-active interval).

## 8. Reproduction

```
git checkout thesis-v45-pocol-stage3a-security-floor-observation-activation-transaction-exhaustion-lock
python3 -m pytest tests/thesis_revision_v45/stage2/ -v --durations=0
python3 -m Models.PoCol.stage2.demo
```

Deterministic (fixed SHA-256 targets, deterministic reserve ordering; no wall-clock / RNG /
network), so a re-run reproduces the metrics above.
