# Stage 4A — Known Limitations

Honest scope statement for the Stage-4A correction. None of these affect the acceptance gates.

## Scope (deliberate)

1. **Correction-only.** Stage 4A corrects the rejected Stage-4 lease layer (executable expiry /
   progress timeout, `MINER_CANCELLED`, authoritative observation, stale-safe exhaustion, Path-B
   overlap removal + transactionality, natural replay, interval energy). It adds no new mechanism
   beyond those corrections.

2. **Liveness / coverage only.** Reassignment (including on a time-expiry, progress-timeout or
   voluntary cancellation) may **increase** energy and latency; it never saves energy. The
   energy-saving mechanism remains the idle policy within PoCol; nonce partitioning alone is never
   energy-saving.

3. **No Stage-5 content.** No reward redistribution, Sybil defence, selfish-mining analysis,
   template grinding, adversarial matrices, chain-quality / common-prefix proofs, dynamic
   difficulty, thesis DOCX/PDF integration, or large confirmatory execution.

## Modeling notes

4. **Disabled by default.** `RangeLeasePolicy.enabled = False`, and deadlines default to an
   effectively-unbounded value (post-horizon, so no event is armed). Every accepted Stage-2B /
   Stage-3 / Stage-3A / Stage-4 behaviour and test is unchanged. Expiry / progress-timeout /
   cancellation are opt-in per run.

5. **Faults and cancellations are explicit facts, never inferred.** A lease terminalises only on
   an explicit trigger (`LEASE_TIME_EXPIRED` / `PROGRESS_TIMEOUT` / `MINER_FAILED` /
   `MINER_CANCELLED` / `ROUND_CLOSING`). `injected_lease_faults` and
   `injected_lease_cancellations` are test-only and empty in confirmatory runs.

6. **Deadline ordering at a shared instant.** `RANGE_LEASE_EXPIRY (23)` and
   `RANGE_PROGRESS_TIMEOUT (24)` land after `HASH_WORK (12)` at a shared event_time, so work
   committing exactly at the deadline commits first (a range finished at the deadline is
   COMPLETED, not spuriously expired); work strictly after the deadline never commits.

7. **Path B reuses the accepted Stage-3 wake with no domain slice.** A reserve reassignee is woken
   through the accepted `SeatReserveActivationTransaction` in `REASSIGNMENT_WAKE_ONLY` scope on a
   **continuation wake-handle** (the original slice's unfinished suffix), and the successor lease
   binds to the ORIGINAL `RangeProgress`. The wake handle is never a nonce-domain partition member;
   `overlapping_slice_count` is 0. The synthetic floor observation / decision used to satisfy the
   Stage-3 handlers is bookkeeping only and is rolled back completely on a failed wake.

## Energy / determinism

8. **Reassignment energy is attributed by lifecycle interval.** Wake / active energy is charged
   over `[started_at, completed_at]` and `[reassigned_search_start_time,
   reassigned_search_end_time]` per COMPLETED request — never the reassignee's full residency (which
   may include its own earlier primary work). Residency snapshots at both interval ends reconcile
   the attribution against the ledger exactly: `reassignment_energy_residual_j == 0`.

9. **All identities exact.** Across every scenario: committed-frontier residual 0, duplicate-nonce
   count 0, post-round-evaluation count 0, non-terminal lease / request count 0, per-miner residency
   reconciles.

10. **Deterministic.** Fixed SHA-256 targets, deterministic reassignee ordering, deterministic
    deadline scheduling, no wall-clock / RNG / network.

## Explicit non-claims

11. **Target and difficulty are never changed** by any lease / reassignment / expiry / timeout /
    cancellation trigger.

12. **Full-domain no-block exhaustion is never claimed while any suffix is unfinished.** A round
    with an unassigned suffix closes with an explicit unassigned/unused-reserve disposition and the
    uncovered nonce interval is reported — never hidden.
