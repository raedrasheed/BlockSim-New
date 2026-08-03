# Stage 4C — Known Limitations & Scope

Stage 4C is a **single narrowly-bounded correction** on the range-lease / reassignment energy
attribution, Path-B cleanup, deadline identity and replay purity. It does **not** return to
Stage 1 / 2 / 3, does **not** modify the accepted Stage-2B search core (`search.py` is byte-identical
to baseline `8750c5e`), and does **not** begin Stage 5.

## Scientific invariants (unchanged, and enforced)

* **Reassignment never saves energy.** It is a liveness / coverage mechanism that may *increase*
  energy and latency. Every energy component is attributed by its exact request LIFECYCLE interval;
  the report never presents reassignment as a saving. The only energy-saving mechanism is the idle
  policy within PoCol.
* **The target / difficulty are fixed.** No lease expiry, progress timeout, cancellation, failure
  or reassignment changes the SHA-256 target or difficulty; nonce partitioning is never an
  energy-saving mechanism.
* **The lease layer is disabled by default** (`RangeLeasePolicy.enabled = False`), so the
  confirmatory Stage-2B / Stage-3 / Stage-3A energy and security results are untouched.

## Interpretation & design decisions

* **The residency ledger accumulates CLOSED intervals only.** `_residency(m, state, t)` adds the
  still-open interval `[state_since, t]` when the miner is currently in `state`, so every snapshot is
  the TRUE cumulative residency at that instant. Without this, a snapshot taken mid-interval (an
  OFFLINE predecessor between revocation and round close) understates the residency — this was the
  concrete defect S4C-1 corrects.
* **Chained predecessor active energy is attributed once.** When a reassignee's own reassigned lease
  is later revoked, its ACTIVE work is already owned by the request that provisioned it (component 5,
  reassigned-active); the downstream revocation's component 1 (predecessor-active) is therefore 0
  for a reassigned-kind predecessor lease. This is the deterministic rule that keeps the
  interval-overlap count at 0 for reassignment chains.
* **One reassignment in flight per miner.** A miner between its reassignment SEAT and COMPLETE is no
  longer selectable as a second reassignee. Before S4C this could double-book a miner's single
  search onto two slices and double-charge its ACTIVE residency; the interval-overlap audit exposed
  it and `_eligible_reassignment_candidates` now excludes in-flight reassignees. This also improves
  coverage (each slice goes to a distinct available miner).
* **The five per-component residuals are 0 in correct operation.** The wake and reassigned-active
  residuals are the strong time-vs-ledger reconciliation; the predecessor / standby residuals verify
  each snapshot is a valid, ordered point within `[0, final ledger]`. The overlap audit and the
  aggregate-vs-run-residency bound are the substantive cross-checks; `residency_reconciles` is the
  global one. A snapshot for a synthetic miner absent from the run (unit-test constructions) is not
  cross-checked against a ledger it has no entry in.
* **The three diagnostic counters are non-protocol.** `reassignment_replay_count`,
  `lease_observation_replay_count` and `unknown_trigger_rejections` live in
  `RunContext.lease_diagnostics`, excluded from the deterministic result metrics and the
  protocol-state snapshot — the sanctioned diagnostic record permitted by S4C-6. Three retained
  white-box assertions were relocated to read them there; no accepted test is weakened or renamed.

## Deliberately out of scope (future stages)

* Reassignment-chaining policy depth tuning (bounded by `maximum_reassignments_per_slice`; a
  slice reassigned past the limit closes with the declared no-eligible / unassigned disposition).
* Cross-round reassignment (a reassignment is scoped to its round; a suffix left unfinished at round
  close is reported `UNASSIGNED_AT_ROUND_CLOSE`, never silently dropped).

## Verification surface

* 124 tests (115 retained + 9 new) pass; `evidence/pytest_stage4c.{log,junit.xml}`.
* `STAGE_04C_RANGE_LEASE_METRICS.json`: six scenarios; overlap = 0, aggregate-exceeds = 0, stale
  reverse-link = 0, wake-handle residue = 0, replay-state-delta = 0, max residual ≤ 1.9 × 10⁻¹⁴ J,
  residency reconciles.
* `search.py` byte-identical to `8750c5e`; changed files limited to `simulator.py`, `adapter.py`,
  `context.py`, `leases.py`, `security.py`, `events.py` (+ the test files).
