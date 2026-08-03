# Stage 4B — Implementation Report

Final focused Stage-4 correction: **terminalise the miner state together with its lease, reject
unknown lease triggers and return the complete replay observation, STRICT `RangeExhaust` identity,
a NON-domain `ReassignmentWakeHandle` in place of the synthetic Path-B `RangeSlice`, complete
Path-B seat-failure cleanup at BOTH seat points, the complete natural reassignment replay result,
a COMPLETE per-request reassignment-energy attribution (including FAILED / CANCELLED), and
progress-generation deadline identity on every causal frontier advance.**

Baseline: `0ab8e075c8d75aeabd19918c51690752077ee312` (the rejected Stage-4A).
Branch: `thesis-v45-pocol-stage4b-terminal-state-pathb-cleanup-replay-energy-completion-lock`.

The accepted Stage-2B search core (`search.py`) is **byte-identical** to the baseline. The whole
lease layer stays **disabled by default** (`RangeLeasePolicy.enabled = False`), so every accepted
Stage-2B / Stage-3 / Stage-3A / Stage-4 / Stage-4A test passes unchanged (**103 retained + 12 new
= 115 tests**). Reassignment is a liveness / coverage mechanism that may **increase** energy and
latency and **never** saves energy; the energy-saving mechanism remains the idle policy within
PoCol; the fixed SHA-256 target and difficulty are never changed by any lease / reassignment
trigger.

## S4B-1 — The miner is terminalised together with its lease

* `RevokeRangeLeaseTransaction` (`simulator.py`) now takes the trigger's **three-tuple**
  disposition from `_TRIGGER_TERMINALISATION` — `(lease_status, counter, miner_state)`:
  `MINER_FAILED → REVOKED / OFFLINE`, `MINER_CANCELLED → CANCELLED / LOW_POWER_LISTEN`,
  `LEASE_TIME_EXPIRED` and `PROGRESS_TIMEOUT → EXPIRED / LOW_POWER_LISTEN`.
* On terminalisation it cancels the exact HashWork **and** RangeExhaust **and** WakeComplete
  events for that miner (`_cancel_queued_hash_events`, returning the count of cancelled wakes into
  `wakes_cancelled_with_lease`), cancels the lease's expiry / progress-timeout deadlines, marks
  the search state terminal, and — the S4B-1 fix — **transitions the miner out of any live state**
  (`_LIVE_MINER_STATES = ACTIVE_HASHING / WAKING / EXHAUSTED_PENDING`) to the trigger's idle state
  immediately, bumping `miners_terminalised_with_lease`. Energy therefore stops charging `P_hash`
  / `P_wake` at the terminalisation instant.
* A lease that **expires before its `WakeCompleteEvent`** cancels that queued wake and idles the
  miner, so it is **never activated** by the stale wake (`test_s4b_01`). The re-armed deadline
  events verify the round-state version so an initial-mint deadline can never fire against the
  wrong round state (S4B-8 re-arm in `_handle_prepare_participants` after the
  `SOLUTION_PROPAGATION` transition).
* A terminalised miner is also **never re-recruited**: `_eligible_reassignment_candidates` now
  admits an alive-miner reassignee only when its own range genuinely **`EXHAUSTED`** (a
  successfully-finished searcher), never a miner whose own lease was `EXPIRED` / `REVOKED` /
  `CANCELLED` (which `RevokeRangeLeaseTransaction` also marks `completed`) and never one that found
  a `SOLUTION`. This closes the cascade in which a just-idled miner was re-woken to `WAKING` for
  the next expiring slice.

## S4B-2 — Unknown triggers are rejected; replay returns the complete observation

* `EvaluateRangeLease` rejects a `trigger not in LEASE_TRIGGERS` **before any mutation, counter or
  state change** — it returns `range_lease_observation_rejected_unknown_trigger`, bumps only
  `unknown_trigger_rejections`, and there is **no default `REVOKED` fallback**.
* An exact replay (same round / template / LeaseID / trigger key) returns the **complete stored
  result** `range_lease_observation_already_exists(observation, decision, outcome)` — never `None`
  — and mutates nothing further. `_finish` stores the `(observation, reassignment_decision_id,
  outcome)` triple in `lease_observation_by_key` at first evaluation.

## S4B-3 — STRICT `RangeExhaust` identity

`_verify_exhaust_lease` (guard in `_handle_range_exhaust`) now, with leases enabled, **rejects a
payload missing its `LeaseID`** and verifies every declared field before any effect: the lease
exists and is `ACTIVE`, it is the slice's current lease, it owns exactly this miner and assignment
(+ `assignment_version`), the `lease_generation` matches, the `expected_search_generation` matches,
the search state is `completed` with `completion_kind == EXHAUSTED`, the cursor **and** committed
frontier equal `range_end`, and the round / template match the current round. Any missing /
premature / stale exhaust event is a **no-op** (`stale_exhaust_events`) with no state, floor or
termination effect (`test_s4b_05`, `test_s4b_06`).

## S4B-4 — A NON-domain `ReassignmentWakeHandle` replaces the synthetic Path-B slice

* `_seat_reserve_reassignment_wake` no longer instantiates a `RangeSlice`. It creates a
  `ReassignmentWakeHandle{WakeHandleID, RoundID, TemplateID, OriginalRangeSliceID,
  RangeReassignmentRequestID, MinerID, generation, status}` (`leases.py`) that carries **no nonce
  interval**, and registers it **only** in `RunContext.reassignment_wake_handles` — never in
  `reserve_slice_by_id`, `reserve_slices`, or any nonce-domain registry.
* The activation request references `OriginalRangeSliceID` / `RangeReassignmentRequestID` /
  `WakeHandleID` with `activation_scope = REASSIGNMENT_WAKE_ONLY`. The **original `RangeProgress`
  remains the sole interval authority**, and the successor lease binds to that original `PS-…`
  slice (`test_s4b_08`). `_obj_activation_id` returns the `WakeHandleID` for a wake handle and the
  `RangeSliceID` for a reserve-domain slice, so the shared Stage-3 activation lifecycle handles
  both; `_audit_slice_disjointness` treats a wake handle as interval-free and only checks that its
  `OriginalRangeSliceID` is a valid live slice.

## S4B-5 — Complete Path-B seat-failure cleanup at BOTH seat points

* A **Path-B `ReserveActivationStartEvent` seat failure** (`_seat_reserve_reassignment_wake`
  rollback) removes the wake handle, its synthetic observation / decision and every reverse link,
  and registers a `FAILED` reassignment request (`test_s4b_09`).
* A **Path-B `ReserveActivationCompleteEvent` seat failure** now calls `_fail_pathb_wake`, which
  terminalises the linked activation request and `RangeReassignmentRequest` **FAILED**, closes the
  wake-energy interval (`wake_residency_at_end`), removes the wake handle and reverse links,
  preserves the committed frontier (`current_lease_id` stays `None` from the revoke), and applies
  the configured no-eligible policy; `_maybe_terminate_no_block` then closes the round rather than
  hang to the horizon (`test_s4b_10`). Both points bump `pathb_rollback_count`; the complete-seat
  point also bumps `wake_complete_seat_failures`. After either injection there is **no WAKING
  miner, no `SEATED` / `STARTED` request, no live wake handle, no orphan link, and no horizon
  hang** (metrics `s4_pathb_start_seat_failure`, `s5_pathb_complete_seat_failure`).

## S4B-6 — The complete natural reassignment replay result

`SeatRangeReassignmentTransaction`'s natural replay (`reassignment_by_predecessor` guard) returns
`_reassignment_already_exists(...)` = `range_reassignment_already_exists` carrying the **exact
stored** `request`, `status`, `start_event_ref`, `complete_event_ref`, `successor_lease` and
`disposition`. Replay creates no event / request / decision / lease and increments **no lifecycle
counter** (`test_s4b_11`).

## S4B-7 — COMPLETE per-request reassignment-energy attribution

* `RangeReassignmentRequest` carries the full lifecycle-interval timestamps and residency
  snapshots (`predecessor_active_residency_at_revoke`, `predecessor_low/offline_…_at_revoke`,
  `reassignee_reserve/low_residency_at_wake_start`, `wake_residency_at_start/end`,
  `active_residency_at_search_start/end`, `seated_at` / `started_at` / `completed_at` /
  `reassigned_search_start/end_time` / `terminal_time`, `status`, `disposition`).
* `adapter.reassignment_energy_report` produces **one row per request — COMPLETED, FAILED and
  CANCELLED alike** — with the predecessor active-before / idle-after energy, the reassignee
  standby-before-wake energy, the (possibly failed) wake energy, the reassigned active-hashing
  energy, every timestamp, plus an `aggregate` and `max_energy_residual_j`. **A failed wake's
  energy is NOT omitted**: its wake window `[started_at, terminal_time]` is charged at `P_wake`
  and reconciled against the residency-ledger `WAKING` delta over exactly that window (0.0 J when
  the complete-seat failure is synchronous at the start instant — a fabricated non-zero charge
  would be wrong; `test_s4b_12` also positively demonstrates a real failed-wake interval being
  attributed). Every interval energy reconciles with the ledger **exactly** (residual ≤ 1.9 × 10⁻¹⁴
  J across all metrics scenarios).

## S4B-8 — Progress-generation deadline identity on every causal advance

* Every causal committed-frontier advance in `_handle_hash_work` increments
  `progress_generation`, updates `last_progress_time`, and calls `_rearm_lease_deadlines`, which
  bumps `timeout_generation`, supersedes the old progress-timeout, and seats exactly one fresh
  timeout — planning a batch (`_seat_hash_work`) refreshes nothing (`test_s4b_07`).
* `_verify_deadline_identity` verifies **every** declared payload field on an expiry / progress
  timeout — `LeaseID`, `MinerID`, `RangeSliceID`, `lease_generation`, the lease being `ACTIVE`,
  `expected_progress_generation`, `expected_committed_frontier`, `timeout_generation` (timeout
  only), `expected_round_state_version`, round and template — so a stale or tampered deadline event
  performs **no effect** (`stale_expiry_events` / `stale_timeout_events`). The primary leases are
  minted before the `SOLUTION_PROPAGATION` transition, so their deadlines are **re-armed** with the
  post-transition round-state version immediately after that transition.

## Retained coverage (103 tests, unchanged)

* Stage-2 core + adapter + scientific + E2E + semantic vectors (TV325–TV338, E2E-1..5, SCI-1..10).
* Stage-3 / Stage-3A security-floor + reserve activation (S3-01..S3-18, S3A-01..S3A-12).
* Stage-4 / Stage-4A range leases + reassignment (S4-01..S4-20, S4A-01..S4A-14).

Backward compatibility is structural: `RangeLeasePolicy.enabled = False` by default; the
terminalisation, deadline, wake-handle and observation machinery is engaged only when the lease
layer is enabled. The single white-box test edit renames `reassignment_wake_slice_by_id →
reassignment_wake_handles` in the retained S4A-10 assertion to follow the S4B-4 refactor; its
intent (no orphan Path-B token after a rollback) is preserved.

## Scope discipline

* `Models/PoCol/stage2/search.py` — **byte-identical** to `0ab8e07`.
* Changed module files: `simulator.py`, `adapter.py`, `context.py`, `leases.py`, `__init__.py`.
* No return to Stage 1 / 2 / 3; no modification of the accepted Stage-2B search core; no Stage-5
  work. This is a single executable blocker correction.
