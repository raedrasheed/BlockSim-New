# Stage 4C — Implementation Report

Final narrowly-bounded Stage-4 correction: **every reassignment-energy component is a true
request-interval residency-ledger delta, five independent per-component residuals + an
interval-overlap audit + an aggregate-vs-run-residency bound, complete Path-B reverse-link cleanup,
an explicit auditable Path-B identity, total + safe deadline-payload verification, and state-pure
replay / unknown-trigger rejection.**

Baseline: `8750c5ecc8571b962e0f9d69e63f4ca7fe5ffdf3` (the rejected Stage-4B).
Branch: `thesis-v45-pocol-stage4c-exact-energy-pathb-links-deadline-identity-lock`.

The accepted Stage-2B search core (`search.py`) is **byte-identical** to the baseline. The whole
lease layer stays **disabled by default** (`RangeLeasePolicy.enabled = False`), so every accepted
Stage-2B / Stage-3 / Stage-3A / Stage-4 / Stage-4A / Stage-4B test passes unchanged (**115 retained
+ 9 new = 124 tests**). Reassignment is a liveness / coverage mechanism that may **increase** energy
and never saves it; the fixed SHA-256 target and difficulty are never changed by any trigger; the
energy-saving mechanism remains the idle policy within PoCol.

## S4C-1 — Every energy field is a true request-interval delta

* **The residency ledger only accumulates CLOSED intervals**, so a snapshot taken mid-interval (an
  OFFLINE predecessor between revocation and round close, a RESERVE reassignee between seat and
  wake) understates the true residency. `_residency(m, state, t)` (`simulator.py`) now adds the
  still-open interval `[state_since, t]` when the miner is currently in `state`, giving the TRUE
  cumulative residency at time `t`. Every snapshot is taken at its exact interval time.
* Each predecessor `RangeLease` records its holder's cumulative per-state residency **at lease
  start** (`active/low/offline_residency_at_lease_start`, `_stamp_lease_start_residency`), so the
  predecessor's active energy is charged over EXACTLY that lease's interval, never the miner's
  whole-run cumulative residency.
* Each `RangeReassignmentRequest` records `revocation_time`, the predecessor's active/low/offline
  residency **at revocation** and **at request terminal** (`_stamp_request_terminal`), the
  reassignee's reserve/low/offline residency **at seat** and **at wake start** (or **at terminal**
  when the wake never starts), the wake residency at start/end, and the reassigned active residency
  at search start/end. `adapter.reassignment_energy_report` computes each component EXACTLY:
  * predecessor active `= P_hash·(active@revocation − active@lease_start)`;
  * predecessor idle/offline `= P_low·(low@terminal − low@revocation) + P_off·(off@terminal −
    off@revocation)`;
  * reassignee standby `= P_res·Δreserve + P_low·Δlow + P_off·Δoff` over `[seat, wake_start]` (or
    `[seat, terminal]` when the wake never ran);
  * wake `= P_wake·(wake@end − wake@start)`; reassigned active `= P_hash·(active@end − active@start)`.
  The FINAL run residency is never used when a request terminal time is earlier (`test_s4c_01`,
  `test_s4c_02`, `test_s4c_03`).

## S4C-2 — Five component residuals + overlap audit + aggregate bound

* The report exposes one residual per component (`residual_predecessor_active_j`,
  `residual_predecessor_idle_or_offline_j`, `residual_reassignee_standby_j`,
  `residual_reassignment_wake_j`, `residual_reassignment_active_hashing_j`) and their maximum
  `max_request_energy_residual_j`. The wake and reassigned-active residuals are the strong
  time-vs-ledger reconciliation (a continuous single-state interval's ledger delta must equal its
  wall duration); the predecessor / standby residuals verify every snapshot is a valid, ordered
  point within `[0, final ledger]`. Across all six metrics scenarios the maximum residual is
  ≤ 1.9 × 10⁻¹⁴ J (floating-point noise, far below 1 × 10⁻⁶).
* An **interval-overlap audit** (`overlapping_charged_interval_count`) sorts every charged
  cumulative-residency span per `(miner, state)` and proves no span overlaps another — no residency
  second is charged to two requests. This exposed and drove a fix: a reassignee between its
  reassignment SEAT and COMPLETE still looked EXHAUSTED and could be double-booked onto a second
  expiring slice; `_eligible_reassignment_candidates` now excludes any miner with an **in-flight**
  reassignment this round (a SEATED / STARTED request), so one reassignment is in flight per miner
  (`test_s4c_05`).
* A **chained predecessor's** active work is already owned by the request that provisioned it (its
  reassigned-active), so the report does NOT re-charge it as the downstream revocation's
  predecessor-active — component 1 is 0 for a reassigned-kind predecessor lease (`test_s4c_05`).
* The **aggregate bound** (`aggregate_exceeds_run_residency_count`) proves the total charged per
  `(miner, state)` never exceeds `P_state × that miner's total run residency`.

## S4C-3 — Complete Path-B reverse-link cleanup

Both Path-B seat-failure points clean every linked state. `_fail_pathb_wake` (complete-seat point)
now terminalises the linked `ReserveActivationRequest` **and** `RangeReassignmentRequest` FAILED,
closes the wake/standby timestamps (`_stamp_request_terminal`), removes the wake handle and its
`reassign_by_suffix_slice` entry, clears the reserve record's `assigned_reserve_slice_id` /
`activation_request_id` / `activation_event_ref` (`_clear_reserve_record_activation_fields`), gives
the synthetic activation decision a terminal failure disposition
(`_terminalise_synthetic_activation_decision`) so no `ACTIVATION_SEATED` decision is left without a
recorded failed outcome, preserves the committed frontier (`current_lease_id` stays `None`), and
applies the no-eligible policy. The start-seat point (`SeatReserveActivationTransaction` rollback +
`_rollback_wake`) restores the reserve record and deletes the synthetic decision entirely. After
either, no registry or reverse binding references the removed WakeHandleID (`test_s4c_06`).

## S4C-4 — Complete, auditable Path-B identity

`ReserveActivationRequest` carries explicit `WakeHandleID`, `OriginalRangeSliceID` and
`RangeReassignmentRequestID` (`security.py`), set at seat by `_seat_reserve_reassignment_wake` →
`SeatReserveActivationTransaction`. `ReserveSliceID` is no longer overloaded as the wake identity;
`WakeHandleID` names the non-domain lifecycle token, `OriginalRangeSliceID` the authoritative
`RangeProgress`, `RangeReassignmentRequestID` the linked reassignment request. The identity stays
auditable **after** the wake handle is removed by the failure cleanup (`test_s4c_07`).

## S4C-5 — Total, safe deadline-payload verification

Both `RangeLeaseExpiryEvent` and `RangeProgressTimeoutEvent` payloads now explicitly carry
`expected_lease_status` (added to `_PROGRESS_TIMEOUT_PAYLOAD_KEYS` in `events.py` and to the seated
payload). `_verify_deadline_identity` reads every declared field with SAFE extraction (`.get`), so a
MISSING declared field is treated as tampered identity (no default is substituted for
`expected_lease_status`); every field is verified, plus the current EventRef must equal the lease's
/ progress's currently-armed deadline ref. Any missing / tampered field — or a stale EventRef —
returns `range_deadline_no_effect(reason="missing_or_tampered_identity")` with **no KeyError and no
state mutation** (`test_s4c_08`).

## S4C-6 — State-pure replay and unknown-trigger rejection

The three replay / rejection diagnostic counters (`reassignment_replay_count`,
`lease_observation_replay_count`, `unknown_trigger_rejections`) moved OUT of the protocol-state
`lease_stats` ledger into a separate `RunContext.lease_diagnostics` namespace (`context.py`),
explicitly excluded from the deterministic result metrics and from the protocol-state snapshot. An
exact reassignment replay (`SeatRangeReassignmentTransaction`), an exact observation replay and an
unknown-trigger rejection (`EvaluateRangeLease`) now change **no** protocol state — `lease_stats`,
leases, progress, miner state, decisions, observations, queue and sequences are byte-identical
before and after; only the diagnostic namespace records that the replay / rejection was observed
(the sanctioned diagnostic entry). A full protocol-state snapshot is byte-equivalent across both
paths (`test_s4c_09`). The retained S4A observation-replay, S4A-11 and S4B-04 assertions were
relocated to read the counter from `lease_diagnostics` (identical assertion strength; a mechanical
relocation the new S4C-6 data model requires — not a weakening or rename).

## Retained coverage (115 tests, unchanged)

Stage-2 / Stage-3 / Stage-3A / Stage-4 / Stage-4A / Stage-4B (TV325–TV338, E2E-1..5, SCI-1..10,
S3-01..S3-18, S3A-01..S3A-12, S4-01..S4-20, S4A-01..S4A-14, S4B-01..S4B-12).

## Scope discipline

* `Models/PoCol/stage2/search.py` — **byte-identical** to `8750c5e`.
* Changed module files: `simulator.py`, `adapter.py`, `context.py`, `leases.py`, `security.py`,
  `events.py`.
* No return to Stage 1 / 2 / 3; no modification of the accepted Stage-2B search core; no Stage-5
  work. This is a single narrowly-bounded correction.
