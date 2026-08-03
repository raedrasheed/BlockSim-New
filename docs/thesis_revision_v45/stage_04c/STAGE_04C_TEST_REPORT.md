# Stage 4C — Test Report

Command: `python -m pytest tests/thesis_revision_v45/stage2/ -v --durations=0`.

Result: **124 passed, 0 failed, 0 errored, 0 skipped** in ≈14.3 s (Python 3.11, pytest).
Evidence: `evidence/pytest_stage4c.log`, `evidence/pytest_stage4c.junit.xml`.

* **115 retained** — Stage-2 / Stage-3 / Stage-3A / Stage-4 / Stage-4A / Stage-4B. All unchanged
  except three white-box counter-location relocations (S4A obs-replay, S4A-11, S4B-04).
* **9 new** — Stage-4C (`test_stage4c_exact_energy_links_deadline.py`).

## Stage-4C locking tests

| Test | Requirement | What it locks |
|------|-------------|---------------|
| `test_s4c_01_predecessor_active_energy_is_only_the_current_lease_delta` | S4C-1 | A predecessor with earlier-round ACTIVE residency is charged only the current lease's `[lease_start, revocation]` active delta, not the whole cumulative (a 3× over-charge avoided). |
| `test_s4c_02_no_later_round_idle_charged_to_the_earlier_request` | S4C-1 | Idle energy is charged only over `[revocation, request_terminal]`; a much larger FINAL low residency (later rounds) is not used. |
| `test_s4c_03_reassignee_standby_is_only_seat_to_wake_interval` | S4C-1 | A reserve reassignee with prior RESERVE history is charged standby only over `[seat, wake_start]`, not its whole prior RESERVE residency. |
| `test_s4c_04_all_statuses_carry_all_five_components_and_residuals` | S4C-2 | COMPLETED, FAILED and CANCELLED requests each carry all five energy components and all five per-component residuals; a failed wake with a real interval is attributed. |
| `test_s4c_05_same_miner_two_requests_no_double_charge` | S4C-2 | A reassignee's ACTIVE work is charged once (its provisioning request), not re-charged as a downstream revocation's predecessor-active; overlap = 0 and aggregate-exceeds = 0 on a synthetic chain and a real multi-fault run. |
| `test_s4c_06_pathb_complete_seat_failure_clears_every_reverse_link` | S4C-3 | A Path-B complete-seat failure clears the reserve record's three reverse links, removes the wake handle + suffix entry, and leaves no `ACTIVATION_SEATED` decision without a terminal outcome. |
| `test_s4c_07_pathb_identity_auditable_after_handle_removal` | S4C-4 | A FAILED Path-B activation request retains explicit `WakeHandleID` / `OriginalRangeSliceID` / `RangeReassignmentRequestID` after the wake handle has been removed. |
| `test_s4c_08_missing_or_tampered_deadline_field_is_structured_no_effect` | S4C-5 | Removing OR tampering ANY declared field of either deadline payload (and a stale EventRef) yields `range_deadline_no_effect("missing_or_tampered_identity")` with no exception and no state change; the untampered event is the control. |
| `test_s4c_09_replay_and_rejection_are_state_pure` | S4C-6 | A full protocol-state snapshot (lease_stats, registries, sequences, queue, miner states) is byte-equivalent across an exact reassignment replay and an unknown-trigger rejection; only `lease_diagnostics` moves. |

## Metrics cross-check (`STAGE_04C_RANGE_LEASE_METRICS.json`)

Six deterministic scenarios (time-expiry, progress-timeout, Path-B wake, Path-B complete-seat
failure, combined multi-fault, cancellation). Every one holds:

* `overlapping_charged_interval_count = 0` — no residency interval charged twice;
* `aggregate_exceeds_run_residency_count = 0` — no aggregate exceeds a miner's total run residency;
* `stale_reserve_reverse_link_count = 0`, `wake_handle_reference_residue_count = 0` — complete
  Path-B cleanup;
* `max_request_energy_residual_j ≤ 1.9 × 10⁻¹⁴` and every one of the five component residuals ≤ that
  (floating-point noise, far below 1 × 10⁻⁶);
* `replay_state_delta_count = 0` — replay / rejection are state-pure;
* `duplicate_nonce_count = 0`, `post_round_evaluation_count = 0`,
  `nonterminal_lease_count = 0`, `nonterminal_reassignment_request_count = 0`;
* `residency_reconciles = true`.

Request counts by status are recorded per scenario (e.g. the Path-B complete-seat-failure scenario
records exactly one FAILED request).
