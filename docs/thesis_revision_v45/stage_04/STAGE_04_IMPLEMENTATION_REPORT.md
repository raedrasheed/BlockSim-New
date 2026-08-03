# Stage 4 — Implementation Report

Focused executable implementation of explicit **nonce-range leases** and **deterministic
reassignment** of unfinished nonce work inside PoCol.  Branch
`thesis-v45-pocol-stage4-range-leases-reassignment`, created from exactly
`b88b56abd288d285ebce774cbbb6186b3ee5bbd2` (the accepted Stage-3A baseline).

Algorithm: **PoCol**.  Energy-saving mechanism: **the idle policy within PoCol** — nonce
partitioning alone is never an energy-saving mechanism.  Reassignment is a
**liveness / coverage** mechanism that may **increase** energy and latency; it never saves
energy.  The security floor remains an operational active-capacity floor only.  Dynamic
difficulty stays excluded, and the fixed target/difficulty are never changed by any lease or
reassignment trigger.

The accepted Stage-2B search core (`search.py`, `energy_experiment.py`) is **byte-identical**
to the baseline (verified against both `1e495bd` and `b88b56a`); Stage 1 is **untouched**;
Stage-2B / Stage-3 / Stage-3A evidence is preserved.  The range-lease layer is **disabled by
default** (`RangeLeasePolicy.enabled = False`), so all 68 accepted tests pass unchanged and
the confirmatory run is behaviourally identical to Stage-3A.

## Executable answers (Stage-4 objective)

1. **Ownership at an instant** — a `RangeLease` controls exactly `[committed_cursor,
   lease_end_nonce)`; a miner may evaluate a nonce only while holding the current ACTIVE lease
   for that exact round / template / slice / lease-generation / assignment-version.
2. **Progress before revocation** — the one authoritative `RangeProgress.committed_frontier`
   per slice advances only on causally-completed hash work (monotonic, never > `range_end`);
   planning a batch advances nothing.
3. **Reassignment conditions** — a lease is revoked on an explicit trigger
   (`MINER_FAILED` / `MINER_CANCELLED` / `LEASE_TIME_EXPIRED` / `PROGRESS_TIMEOUT` /
   `ROUND_CLOSING`) and only the unfinished suffix is transferred.
4. **No duplicate evaluation** — the successor starts at the exact committed frontier and the
   ledger proves zero duplicate `(TemplateID, RangeSliceID, nonce)` (and `(TemplateID,
   nonce)`) evaluations across predecessor and successor.
5. **Identity / versioning / expiry / replay** — immutable `LeaseID` +
   `RangeReassignmentRequestID`; full identity verification before mutation; idempotent
   observation key; exact replay creates no second lease/event.
6. **Interaction with Stage-3** — reserve activation (claims an UNCLAIMED reserve-domain
   slice) and reassignment (transfers a terminal slice's suffix) are distinct; a reserve
   reassignee reuses the accepted Stage-3 activation/wake lifecycle.
7. **No eligible miner** — an explicit configurable policy
   (`CONTINUE_WITH_UNASSIGNED_RANGE` / `ABORT_ROUND` / `WAIT_FOR_ELIGIBLE_MINER`).
8. **Reporting** — reassignment latency, energy (standby/wake/active/idle residency),
   coverage and uncovered suffixes are all reported (adapter schema `stage4.1`).

## What each requirement changed

* **S4-1/S4-2 (`leases.py`)** — immutable `RangeLease` + `RangeProgress` records with explicit
  lifecycles; `committed_frontier` is monotonic, causal and bounded.
* **S4-3 (`simulator.py`, `events.py`)** — every primary and every activated-reserve
  assignment receives a lease; `HashWorkEvent` / `RangeExhaustEvent` carry the current
  `LeaseID` + generation (optional descriptor keys, backward-compatible); `_verify_hash_lease`
  checks the full lease identity + frontier before any search-state mutation, and the ledger
  gains `RangeSliceID` / `LeaseID` / `lease_generation` / `progress_generation` /
  `predecessor_lease_id`.
* **S4-4 (`config.py`, `leases.py`)** — the immutable, validated `RangeLeasePolicy`; explicit
  triggers; a test-only `injected_lease_faults` hook (empty in confirmatory runs).
* **S4-5 (`simulator.EvaluateRangeLease`)** — the one authoritative, idempotent lease
  observation keyed by `(RoundID, TemplateID, LeaseID, triggering_event_ref, lease_generation,
  progress_generation, round_state_version)`.
* **S4-6 (`leases.select_reassignment_candidate`)** — one deterministic reassignee by
  `(category_rank, projected_completion_time, activation_priority, MinerID)`; never more than
  one; never auto-activates all reserves.
* **S4-7/S4-8 (`simulator.py`, `events.py`)** — `RangeReassignmentDecision` +
  `RangeReassignmentRequest` with immutable identity; `RangeReassignmentStart/Complete`
  events carrying the full predecessor/successor identity chain, verified before mutation.
* **S4-9 (`simulator.py`)** — `RevokeRangeLeaseTransaction`,
  `SeatRangeReassignmentTransaction` and the start→complete handlers commit all-or-none;
  a failed seat rolls back to a coherent state (predecessor terminal, request FAILED, slice
  `UNASSIGNED_PENDING_RETRY`); a failed complete-seat never strands a WAKING miner.
* **S4-10 (`simulator.py`)** — reserve reassignees reuse the accepted Stage-3
  `SeatReserveActivationTransaction` (Path B) and the reassignment request references the
  activation request — no second reserve-wake implementation.
* **S4-11 (`simulator._apply_no_eligible_policy`)** — the explicit no-eligible / seat-failure
  policy; `WAIT_FOR_ELIGIBLE_MINER` uses one bounded, idempotent retry event.
* **S4-12 (`simulator._close_lease_state`, `_maybe_terminate_no_block`)** — round closure
  terminalises every lease + request; full-domain no-block exhaustion is valid only when every
  slice's `committed_frontier == range_end` (unfinished suffixes are never hidden).
* **S4-13 (`adapter.py`)** — reassignment energy/latency/coverage reporting by residency.

## Files changed
`Models/PoCol/stage2/leases.py` (new), `events.py`, `context.py`, `config.py`, `simulator.py`,
`adapter.py`, `__init__.py`; `tests/thesis_revision_v45/stage2/test_stage4_range_leases.py`
(new), `test_stage2_adapter.py`, `test_stage3_security_floor.py` (schema-version bump only);
new `.github/workflows/stage4-pocol-tests.yml`; this `docs/thesis_revision_v45/stage_04/`
deliverable set.  `search.py` / `energy_experiment.py` are unchanged.
