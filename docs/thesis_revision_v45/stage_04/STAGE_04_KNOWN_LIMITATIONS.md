# Stage 4 — Known Limitations

Honest scope statement for the Stage-4 range-lease / reassignment implementation.  None of
these affect the acceptance gates.

## Scope (deliberate, per the Stage-4 brief)

1. **Reassignment transfers only the unfinished suffix.** It moves `[committed_frontier,
   range_end)` of an already-claimed primary or reserve slice AFTER that slice's lease becomes
   terminal.  It never re-partitions the domain and never re-searches committed nonces.

2. **Liveness / coverage only.** Reassignment is a liveness/coverage mechanism that may
   INCREASE energy and latency; it never saves energy.  The energy-saving mechanism remains the
   idle policy within PoCol; nonce partitioning alone is never an energy-saving mechanism.

3. **No Stage-5 content.** No reward redistribution, Sybil defence, selfish-mining analysis,
   template withholding/grinding, adversarial experiment matrices, chain-quality/common-prefix
   proofs, dynamic difficulty, thesis DOCX/PDF integration, or large confirmatory execution.

## Modeling notes

4. **Range-lease layer disabled by default.** `RangeLeasePolicy.enabled = False`, so every
   accepted Stage-2B / Stage-3 / Stage-3A behaviour and test is unchanged; Stage-4 behaviour is
   opt-in per run.

5. **One active lease per miner; one current lease per slice.** A miner is an eligible
   reassignee only when its own lease is terminal (it finished its range) or it is an AVAILABLE
   reserve.  Concurrent multiple leases per miner are out of scope for Stage 4.

6. **Failure is an explicit fact, never inferred.** A lease is revoked only on an explicit
   trigger (`MINER_FAILED` / `MINER_CANCELLED` / `LEASE_TIME_EXPIRED` / `PROGRESS_TIMEOUT` /
   `ROUND_CLOSING`).  Failure is never inferred from low hash rate.  The `injected_lease_faults`
   hook is a test-only injection and is empty in confirmatory runs.

7. **Reserve reassignment reuses the accepted Stage-3 wake.** A reserve reassignee (Path B) is
   woken through the accepted `SeatReserveActivationTransaction` on a reassignment-suffix slice;
   the reassignment request references the resulting activation request (S4-10).  To let the
   accepted Stage-3 handlers accept a reassignment-driven activation, a
   synthetic-provenance floor observation + decision is registered for it — this is bookkeeping
   only (it seats no capacity and, because the floor is disabled in the reassignment scenarios,
   does not affect floor metrics).

8. **`WAIT_FOR_ELIGIBLE_MINER` uses a small bounded retry.** It seats at most three
   idempotent `RangeReassignmentRetryEvent`s at strictly-later times (never spinning at the same
   timestamp); after that it falls back to preserving the uncovered suffix.  The confirmatory
   default is `CONTINUE_WITH_UNASSIGNED_RANGE`.

9. **Lease/progress timeouts default to effectively unbounded.** `lease_duration` and
   `progress_timeout` default to a very large value; expiry/timeout triggers are available and
   validated but are not the default driver of reassignment in the shipped scenarios (which use
   explicit failure injection).

## Energy / determinism

10. **Reassignment increases energy.** Revocation leaves the predecessor idle/offline; the
    successor adds `P_wake` + `P_hash` residency.  The adapter reports reassignment wake/active
    energy separately and never claims reassignment saves energy.

11. **All identities are exact.** Across every scenario the committed-frontier residual is 0,
    the reassignment-latency residual is 0.0, and the per-miner energy-identity residual is
    `0.0 J`; residency reconciles.

12. **Deterministic.** Fixed SHA-256 targets, deterministic reassignee ordering
    `(category_rank, projected_completion_time, activation_priority, MinerID)`, no wall-clock /
    RNG / network — runs are reproducible.

## Explicit non-claims

13. **Target and difficulty are never changed** by any lease or reassignment trigger (S4-20).

14. **Full-domain no-block exhaustion is never claimed while any suffix is unfinished.** A round
    with an unassigned suffix closes with an explicit
    `round_closed_with_unassigned_range` (or the Stage-3 unused-reserve-domain) disposition, and
    the uncovered nonce interval is reported — never hidden.
