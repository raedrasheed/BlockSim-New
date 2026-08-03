# Stage 4B — Known Limitations & Scope

Stage 4B is a **single focused executable correction** on the range-lease / reassignment layer.
It does **not** return to Stage 1 / 2 / 3, does **not** modify the accepted Stage-2B search core
(`search.py` is byte-identical to baseline `0ab8e07`), and does **not** begin Stage 5.

## Scientific invariants (unchanged, and enforced)

* **Reassignment never saves energy.** It is a liveness / coverage mechanism that may *increase*
  energy and latency. The per-request energy report and the aggregate never present it as a
  saving; the only energy-saving mechanism is the idle policy within PoCol.
* **The target / difficulty are fixed.** No lease expiry, progress timeout, cancellation, failure
  or reassignment ever changes the SHA-256 target or difficulty. Nonce partitioning is never an
  energy-saving mechanism.
* **The lease layer is disabled by default** (`RangeLeasePolicy.enabled = False`), so the
  confirmatory Stage-2B / Stage-3 / Stage-3A energy and security results are untouched.

## Interpretation decisions

* **"Replay increments no counter" (S4B-6) = no *lifecycle* counter.** The diagnostic
  `reassignment_replay_count` / `lease_observation_replay_count` counters are still incremented on
  replay (they exist to *observe* replay and are asserted by the retained S4A-11 test). No
  lifecycle counter (`reassignment_requests_seated`, `leases_reassigned`, decision / request /
  event / lease creation) changes on replay, and the returned result is the exact stored one.
* **Failed-wake energy of a synchronous complete-seat failure is 0.0 J — and that is correct.**
  The `force_activation_complete_seat_failure` injection fails the `ReserveActivationCompleteEvent`
  *seat* synchronously at the activation-start instant (this is the accepted S3A-06 semantics), so
  the reserve accrues zero WAKING residency and the true wake energy over `[started_at,
  terminal_time]` is 0.0 J. The field is **present** (not omitted) and equals the exact residency
  delta; charging a non-zero value would fabricate energy never spent. `test_s4b_12` additionally
  demonstrates positively that a FAILED request whose wake window spans real WAKING residency is
  attributed `P_wake × interval > 0`.

## Deliberately out of scope (future stages)

* Multi-round reassignment *chaining* policy tuning (a slice reassigned more than
  `maximum_reassignments_per_slice` closes with the declared no-eligible / unassigned disposition;
  deeper chains are a Stage-5 policy question, not a correctness gap).
* Reassignment across **round boundaries** (a reassignment is scoped to its round; a suffix left
  unfinished at round close is reported `UNASSIGNED_AT_ROUND_CLOSE`, never silently dropped).
* A real (non-injected) FAILED wake that spans genuine WAKING residency does not arise in the
  confirmatory configs (leases disabled); its attribution is covered by the positive demonstration
  in `test_s4b_12` rather than an end-to-end run.

## Verification surface

* 115 tests (103 retained + 12 new) pass; `evidence/pytest_stage4b.{log,junit.xml}`.
* `RANGE_LEASE_METRICS.json`: six scenarios, all structural invariants hold, energy residual
  ≤ 1.9 × 10⁻¹⁴ J, residency reconciles.
* `search.py` byte-identical to `0ab8e07`; changed files limited to
  `simulator.py`, `adapter.py`, `context.py`, `leases.py`, `__init__.py` (+ the two test files).
