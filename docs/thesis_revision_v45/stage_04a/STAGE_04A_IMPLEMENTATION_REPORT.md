# Stage 4A — Implementation Report

Final focused Stage-4 correction: **executable lease expiry, executable progress timeout,
`MINER_CANCELLED`, an authoritative `EvaluateRangeLease`, stale-safe range exhaustion, a
Path-B refactor with no overlapping slice, full Path-B transactionality, natural reassignment
replay, and lifecycle-interval reassignment energy attribution.**

Baseline: `10fb5e19aebc618ab1aedcc1e5584c9652fea57d` (the rejected Stage-4).
Branch: `thesis-v45-pocol-stage4a-expiry-progress-pathb-transaction-energy-attribution-lock`.

The accepted Stage-2B search core (`search.py`) is **byte-identical** to the baseline. The
whole lease layer stays **disabled by default** (`RangeLeasePolicy.enabled = False`), so every
accepted Stage-2B / Stage-3 / Stage-3A / Stage-4 test passes unchanged (89 retained + 14 new =
**103 tests**). Reassignment is a liveness / coverage mechanism that may **increase** energy and
latency and **never** saves energy; the energy-saving mechanism remains the idle policy within
PoCol; the fixed target and difficulty are never changed.

## S4A-1 — Lease expiry is executable

* `RangeLease.lease_expiry_time` is now backed by a real seated **`RangeLeaseExpiryEvent`**
  (`_seat_lease_expiry`), armed for **every** ACTIVE lease at creation, at Path-A rebind, and at
  Path-B rebind, and stored in `RangeLease.expiry_event_ref`.
* A new microphase `RANGE_LEASE_EXPIRY (23)` lands **after** `HASH_WORK (12)` at a shared
  event_time, so work completing exactly *at* the deadline commits first (COMPLETED), and work
  strictly *after* the deadline never commits.
* On dispatch (`_handle_range_lease_expiry`) a superseded lease (terminal / stale generation /
  no longer the slice's current lease) is a **stale no-op** (`stale_expiry_events`); otherwise it
  invokes `EvaluateRangeLease(LEASE_TIME_EXPIRED)`, which marks the lease **EXPIRED**, cancels
  that LeaseID's queued hash / range-exhaust events and its own deadline events, and reassigns
  the unfinished suffix.
* The default `lease_duration` is effectively unbounded (post-horizon), so confirmatory runs arm
  no expiry event; only a finite configured duration arms one.

## S4A-2 — Progress timeout is executable

* `RangeProgress` now carries `last_progress_time`, `timeout_event_ref`, `timeout_generation`.
* `_refresh_progress_timeout` (re)arms a **`RangeProgressTimeoutEvent`** at
  `last_progress_time + progress_timeout`. It is refreshed on **every causal frontier advance**
  in `_handle_hash_work` (guarded by `advanced = commit_end > old_frontier`) — **never** on
  planning a batch (`_seat_hash_work` touches nothing). Each refresh bumps `timeout_generation`
  and cancels the prior event, so a superseded deadline fires as a **stale no-op**
  (`stale_timeout_events`).
* On a live dispatch it invokes `EvaluateRangeLease(PROGRESS_TIMEOUT)` (disposition EXPIRED,
  counted in `progress_timeouts`).

## S4A-3 — `MINER_CANCELLED` is a distinct disposition

* New `MinerCancelledEvent` + `_handle_miner_cancelled`: a **voluntary** withdrawal moves the
  miner to `LOW_POWER_LISTEN` (it is **not** OFFLINE) and terminalises the lease **CANCELLED**
  (`miner_cancellations`, `leases_cancelled`) — distinct from a **failure** (`MinerFailureEvent`
  → OFFLINE → **REVOKED**, `leases_revoked`). Injected via `injected_lease_cancellations`
  (test-only; empty in confirmatory runs).
* `_TRIGGER_TERMINALISATION` maps each `LEASE_TRIGGERS` value to its terminal status + counter.

## S4A-4 — `EvaluateRangeLease` is authoritative

* It now **validates the trigger condition** (`_trigger_condition_satisfied`) before doing
  anything: a failure / cancellation is an explicit fact (miner already transitioned), a
  time-expiry / progress-timeout is checked against the recorded deadline. An unsatisfied
  condition leaves the lease **ACTIVE** (decision `LEASE_REMAINS_ACTIVE`) — it never revokes
  merely because it was called.
* It records **exactly one** authoritative, auditable `RangeLeaseObservation` per observation
  (`_append_lease_observation`), with `observation_key`, `lease_status_before`,
  `committed_frontier`, `progress_generation`, `condition_satisfied`, `decision_result`, and the
  linked `reassignment_decision_id`. The immutable observation key is
  `(RoundID, TemplateID, LeaseID, triggering_event_ref)` so re-invoking for the **same** event is
  idempotent even after the observation has mutated the slice progress.

## S4A-5 — `RangeExhaust` is stale-safe under leases

* `_handle_range_exhaust` now runs `_verify_exhaust_lease` first: a RangeExhaustEvent from a
  superseded lease (revoked / reassigned / stale generation / no longer current) performs **no
  effect** (`stale_exhaust_events`) — it never idles the successor miner nor mis-completes the
  slice.

## S4A-6 — the overlapping Path-B RangeSlice is removed

* Path B no longer creates a second nonce-domain slice (`RRS-…`) that overlaps the parent. It
  reuses the accepted Stage-3 activation in a new **`REASSIGNMENT_WAKE_ONLY`** scope
  (`ReserveActivationRequest.activation_scope` + `range_reassignment_request_id`). The wake uses a
  **continuation wake-handle** (`WH-…`) that is exactly the ORIGINAL slice's unfinished suffix
  `[committed_frontier, range_end)`; it is registered **only** as a wake handle
  (`reassignment_wake_slice_by_id`), **never** in `reserve_slices[round]` (the domain partition).
  The successor lease binds to the **ORIGINAL** `RangeProgress`.
* `_audit_slice_disjointness` proves, at every round close, that the domain-partition slices are
  pairwise disjoint and each wake handle is a strict subset of its parent — any overlap increments
  `overlapping_slice_count` (observed **0** in every scenario).

## S4A-7 — Path B is fully transactional

* `_seat_reserve_reassignment_wake` snapshots the observation / decision lists and, on any
  failure of the Stage-3 wake seat, **rolls back completely** (`_rollback_wake`): it truncates the
  synthetic observation and decision, deletes the wake-handle slice from both registries, and
  removes the `reassign_by_suffix_slice` link — leaving **no orphan** slice, observation, decision
  or link (`pathb_rollback_count`). A FAILED reassignment request is registered for audit only.

## S4A-8 — reassignment replay is natural

* A `reassignment_by_predecessor` registry keys each committed reassignment on its **terminal
  predecessor lease**. Re-observing the same terminal lease returns
  `range_reassignment_already_exists(...)` with **no** second request and **no manual generation
  rewind** (`reassignment_replay_count`). The generation counter no longer participates in replay
  detection.

## S4A-9 — reassignment energy is attributed by lifecycle interval

* The adapter attributes reassignment wake / active energy over the **reassignment lifecycle
  interval** per COMPLETED request — the wake window `[started_at, completed_at]` and the active
  window `[reassigned_search_start_time, reassigned_search_end_time]` — **never** the reassignee's
  full residency (which may include its own earlier primary work).
* Residency snapshots captured at both ends of each interval reconcile the interval attribution
  against the residency ledger **exactly**: `reassignment_energy_residual_j == 0` in every
  scenario, and per-miner total residency still reconciles.

## Files touched (scope-disciplined)

`leases.py`, `security.py`, `events.py`, `context.py`, `config.py`, `simulator.py`, `adapter.py`,
`__init__.py` — plus the new test file and this evidence. `search.py`, `driver.py`,
`energy_experiment.py` are unchanged. No Stage-5 content (no rewards / Sybil / selfish-mining /
dynamic difficulty / thesis integration).
