# Stage 5D — Test Report

**Command:** `python -m pytest tests/thesis_revision_v45 -v`
**Result:** `195 passed`
**Environment:** Python 3.11, pytest 9.1.1
**Raw evidence:** `evidence/pytest_stage5d.log`, `evidence/pytest_stage5d.junit.xml`

## Totals

| File | Tests | Result |
|---|---:|---|
| `test_stage2_adapter.py` | 4 | pass |
| `test_stage2_e2e.py` | 5 | pass |
| `test_stage2_scientific.py` | 14 | pass |
| `test_stage2_semantic_vectors.py` | 14 | pass |
| `test_stage3_security_floor.py` | 31 | pass |
| `test_stage4_range_leases.py` | 21 | pass |
| `test_stage4a_lease_lifecycle.py` | 14 | pass |
| `test_stage4b_terminal_pathb_replay_energy.py` | 12 | pass |
| `test_stage4c_exact_energy_links_deadline.py` | 9 | pass |
| `test_stage5_adversarial_incentive.py` | 26 | pass |
| `test_stage5a_frontier_reward_behaviour.py` | 12 | pass |
| `test_stage5b_ownership_pathb_wake_coverage.py` | 14 | pass |
| `test_stage5c_record_derived_accounting.py` | 9 | pass |
| **`test_stage5d_post_round_evidence_integrity.py`** | **10** | **pass** |
| **Total** | **195** | **0 failed, 0 skipped, 0 xfailed** |

All 185 Stage-5C tests are retained **byte-identical** — Stage 5D adds a new file and changes no
existing test. No test is skipped, marked xfail or conditionally collected.

## New Stage-5D tests

| Test | Coverage |
|---|---|
| `test_s5d_01_...[disabled_honest_control]` | Stage-5-disabled honest control |
| `test_s5d_01_...[enabled_without_leases]` | Stage 5 enabled, leases off |
| `test_s5d_01_...[enabled_with_leases]` | Stage 5 enabled, leases on |
| `test_s5d_01_...[path_a_reassignment]` | Path-A reassignment |
| `test_s5d_01_...[path_b_reassignment]` | genuine Path-B reassignment |
| `test_s5d_01_...[abandonment_coverage_gap]` | abandonment coverage gap |
| `test_s5d_01_...[false_exhaustion_coverage_gap]` | false-exhaustion coverage gap |
| `test_s5d_01_...[solution_withholding]` | solution withholding |
| `test_s5d_02_the_corrected_metric_is_not_the_ledger_length` | the correction, plus two positive controls |
| `test_s5d_03_the_required_scenarios_really_exercise_their_named_behaviour` | scenario liveness across all eight |

Each `S5D-01` case asserts, computed **independently** from `run.evaluation_ledger` and
`run.round_terminal_times`:

```
post_round_evaluation_record_count      == 0
post_round_evaluation_nonce_count       == 0
evaluation_missing_terminal_time_count  == 0
```

plus that every ledger round is present in the terminal-time registry and every record completes
at or before its round's terminal time. The tests never read a reported field and compare it
with itself.

## Independence and sensitivity

`test_s5d_02` proves the corrected computation is not vacuously zero:

| probe | expected | observed |
|---|---|---|
| shrink one round's terminal time below its records' completion times | those records reported as post-round, with their exact nonce count | matches |
| remove a round's terminal time entirely | reported as `evaluation_missing_terminal_time_count`, **not** as post-round, **not** skipped | matches |
| restore original state | audit returns to its original values | matches |

It also pins the contrast with the superseded definition: `len(run.evaluation_ledger)` is
non-zero in a healthy run while the corrected record count is zero.

## Scenario liveness

`test_s5d_03` asserts the eight scenarios are not vacuous, so a zero result is evidence rather
than absent activity: the disabled control really searches; leases really engage where declared;
Path A seats a reassignment with **no** Stage-3 wake; Path B is a **genuine** Stage-3 wake
through a non-domain `ReassignmentWakeHandle` scoped `REASSIGNMENT_WAKE_ONLY`; the abandonment
and false-exhaustion scenarios really produce coverage gaps; the withholding scenario really
withholds a valid solution.

## Executed-evidence measurements

From `generate_stage5d_metrics.py` across the eight required scenarios:

| scenario | post-round records | post-round nonces | missing terminal time | superseded `len(ledger)` |
|---|---:|---:|---:|---:|
| A — disabled honest control | 0 | 0 | 0 | 239 |
| B — enabled, no leases | 0 | 0 | 0 | 159 |
| C — enabled, with leases | 0 | 0 | 0 | 159 |
| D — Path-A reassignment | 0 | 0 | 0 | 717 |
| E — Path-B reassignment | 0 | 0 | 0 | 641 |
| F — abandonment coverage gap | 0 | 0 | 0 | 191 |
| G — false-exhaustion coverage gap | 0 | 0 | 0 | 191 |
| H — solution withholding | 0 | 0 | 0 | 4 |

All twelve generator invariants hold, including
`S5D_no_offending_records`, `S5D_every_ledger_round_has_a_terminal_time`,
`S5D_corrected_metric_differs_from_superseded_definition` and the five scenario-liveness
invariants.

## CI gate

`.github/workflows/stage5d-pocol-tests.yml` fails the build if, in **any** evidence scenario,
any of the three metrics is non-zero, any offending record is listed, or the ledger is empty (a
zero result over an empty ledger would be vacuous). It also verifies that `search.py` and all
seven accepted Stage-5C executable modules are byte-identical by SHA-256.

## Scope

These are deterministic micro-scenarios for evidence only. They are **not** the confirmatory
experiment matrix and no statistical claim is derived from them. They establish no security,
fairness, incentive-compatibility or Sybil-resistance property.
