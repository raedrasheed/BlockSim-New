# Stage 4 — Test Report

Machine evidence in `docs/thesis_revision_v45/stage_04/evidence/`: `pytest_stage4.log`
(full `pytest -v --durations=0`), `pytest_stage4.junit.xml` (JUnit XML), `stage4_metrics.json`
(deterministic range-lease / reassignment metrics).  The curated metrics are mirrored at
`STAGE_04_RANGE_LEASE_METRICS.json`.

## 1. Exact pytest command

```
python3 -m pytest tests/thesis_revision_v45/stage2/ -v --durations=0 \
    -p no:cacheprovider \
    --junitxml=docs/thesis_revision_v45/stage_04/evidence/pytest_stage4.junit.xml
```

The single directory `tests/thesis_revision_v45/stage2/` holds the complete Stage-2B +
Stage-3 + Stage-3A + Stage-4 suite, so this one command runs all four.

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
| Branch | `thesis-v45-pocol-stage4-range-leases-reassignment` |
| Parent SHA | `b88b56abd288d285ebce774cbbb6186b3ee5bbd2` (accepted Stage-3A baseline) |
| Accepted Stage-2B core | `1e495bda74144d86c08aa0549bd3d633033600c4` (search core unchanged) |
| Commit SHA | the resulting HEAD of this branch (a file cannot embed its own commit hash; retrievable via `git rev-parse HEAD` and recorded in the acceptance-review handoff) |

## 4. Collection / result summary

| Metric | Value |
|---|---|
| Collected | 89 |
| Passed | 89 |
| Failed | 0 |
| Skipped | 0 |
| Errors | 0 |
| Duration | ~8.6 s |

Breakdown: 37 Stage-2B + 19 Stage-3 + 12 Stage-3A (68 retained) + 20 Stage-4 (S4-01…S4-20)
+ 1 Stage-4 adapter-schema check = 89.

## 5. Stage-4 test-name list (`test_stage4_range_leases.py`)

`test_s4_01_every_primary_gets_one_active_lease`,
`test_s4_02_every_activated_reserve_gets_one_active_lease`,
`test_s4_03_committed_progress_is_exact`,
`test_s4_04_planning_does_not_advance_frontier`,
`test_s4_05_miner_failure_revokes_lease_and_cancels_hash_event`,
`test_s4_06_new_lease_begins_at_committed_frontier`,
`test_s4_07_reassignee_evaluates_no_nonce_below_frontier`,
`test_s4_08_zero_duplicate_nonce_across_predecessor_and_successor`,
`test_s4_09_stale_old_lease_hash_event_no_effect`,
`test_s4_10_exact_replay_creates_no_second_lease_or_event`,
`test_s4_11_two_runs_select_same_reassignment_miner`,
`test_s4_12_reserve_reassignee_uses_stage3_wake_lifecycle`,
`test_s4_13_no_eligible_continue_records_uncovered_suffix`,
`test_s4_14_no_eligible_abort_closes_through_owner`,
`test_s4_15_reassignment_seat_failure_leaves_coherent_state`,
`test_s4_16_closure_terminalises_all_leases_and_requests`,
`test_s4_17_full_domain_rejected_with_unassigned_suffix`,
`test_s4_18_true_full_domain_after_reassignment_covers_all_once`,
`test_s4_19_reassignment_energy_equals_residency_terms`,
`test_s4_20_lease_policy_does_not_change_target_or_difficulty`,
`test_s4_adapter_schema_and_execution_from_config`.

## 6. Retained tests

All 68 accepted Stage-2B / Stage-3 / Stage-3A tests rerun and pass.  The range-lease layer is
disabled by default, so their behaviour is identical.  The only edits are the adapter
schema-version assertions (`stage3a.1` → `stage4.1`).

## 7. Range-lease / reassignment metrics (`evidence/stage4_metrics.json`)

Deterministic; recomputed directly from executable state.  Across all six scenarios:
**duplicate nonce count = 0**, **post-round evaluation count = 0**, **max progress-frontier
residual = 0**, **max reassignment-latency residual = 0.0**, **max energy-identity residual =
0.0 J**, **non-terminal leases after closure = 0**, **non-terminal reassignment requests after
closure = 0**, **residency reconciles = True**.

| Scenario | rounds | revoked | reassigned | completed | failed | rollback | uncovered nonces |
|---|---|---|---|---|---|---|---|
| no_fault_full_domain | 30 | 0 | 0 | 0 | 0 | 0 | 25 (final round truncated at horizon) |
| path_a_primary_reassignment | 30 | 1 | 1 | 1 | 0 | 0 | 150 (post-fault tail rounds) |
| path_b_reserve_reassignment | 21 | 1 | 1 | 1 | 0 | 0 | 400 |
| no_eligible_continue_unassigned | 1 | 1 | 0 | 0 | 0 | 0 | 350 |
| no_eligible_abort | 7 | 1 | 0 | 0 | 0 | 0 | 525 |
| seat_failure_rollback | 1 | 1 | 0 | 0 | 1 | 1 | 0 |

Notes:
- **Path A** (primary reassignee) and **Path B** (reserve reassignee via the accepted Stage-3
  wake) both complete exactly one reassignment with full-domain coverage and zero duplicates.
- **`no_eligible_continue`** preserves the exact committed frontier and records the uncovered
  suffix (350 = the `[50, 400)` tail of the single failed miner) — NOT a full-domain claim.
- **`no_eligible_abort`** closes round-1 through the accepted closure owner
  (`range_reassignment_unavailable`); every lease/request is terminal.
- **`seat_failure_rollback`** exercises the transactional rollback: 1 FAILED request, coherent
  state, no stranded miner.

## 8. Reproduction

```
git checkout thesis-v45-pocol-stage4-range-leases-reassignment
python3 -m pytest tests/thesis_revision_v45/stage2/ -v --durations=0
python3 -m Models.PoCol.stage2.demo
```

Deterministic (fixed SHA-256 targets, deterministic reassignment ordering; no wall-clock / RNG
/ network), so a re-run reproduces the metrics above.
