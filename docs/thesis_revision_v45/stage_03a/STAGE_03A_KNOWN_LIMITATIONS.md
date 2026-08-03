# Stage 3A — Known Limitations

Honest scope statement for the corrected Stage-3A security-floor / reserve-activation
implementation.  None of these affect the acceptance gates.

## Scope (deliberate, per the Stage-3 / Stage-3A brief)

1. **Operational capacity floor only.** The floor prevents the effective active hashing
   capacity from silently falling below a declared minimum while a round is open.  It does
   NOT prove chain quality, common prefix, Bitcoin/PoW security equivalence, or resistance to
   any adversarial fraction, and is not reported as such.

2. **No range leasing or reassignment.** A reserve searches only its own previously
   UNCLAIMED reserve-domain slice; it never reassigns another miner's partially-searched or
   abandoned primary range.  Range leases/reassignment are Stage 4.

3. **No dynamic difficulty / rewards / Sybil / selfish-mining / security proofs /
   adversarial matrices / thesis integration.** Out of Stage-3A scope.

## Modeling notes

4. **Floor disabled by default.** `SecurityFloorPolicy.enabled = False`, so every accepted
   Stage-2B behaviour and test is unchanged; Stage-3 behaviour is opt-in per run.

5. **Round-start observation is measure-only.** The `participants_prepared` observation
   records the real first breach and opens the below-floor interval, but seats no reserve and
   takes no abort (WAKING primaries are imminent).  Every actionable decision is deferred to a
   capacity-change point where simulation time has advanced, so a round is never terminated at
   its own start time (a genuine liveness requirement, not a coverage gap).

6. **WAKING-primary pending capacity is a seat-decision input only.** It is never counted in
   `H_effective` (S3A-1); it only prevents over-activation during the normal wake ramp.  The
   ramp is still recorded as a real below-floor interval and measured.

7. **No mid-round primary-failure event in this model.** The current model changes capacity
   only via wake, exhaustion, reserve activation, the complete-seat-failure cancellation, and
   round closure — each of which is observed.  A dedicated adversarial primary-failure event
   is Stage 4+; the observation hook (`EvaluateSecurityFloor` at every capacity change) is
   already in place for it.

8. **One reserve slice per reserve miner; fixed reserve pool per run.** The domain is
   partitioned into `n_primary + n_reserve` contiguous slices; each reserve claims at most one.
   Finer sub-slicing and cross-round reserve churn are not modeled.

9. **Minimum-cardinality selection is exact for the modeled pool sizes.** The selector
   establishes minimum cardinality by largest rate, then a feasibility greedy over the
   preference order chooses the lexicographically smallest priority tuple among covering
   subsets of that size.  This is exact; for pathologically large eligible pools it remains a
   deterministic, polynomial procedure (not a full subset-sum search), which is sufficient for
   the modeled reserve fractions.

## Energy / determinism

10. **Reserve activation increases energy.** Waking and running reserves adds `P_wake` and
    `P_hash` residency; the adapter reports reserve standby/wake/active energy separately and
    never claims reserve activation saves energy.

11. **Energy identity is exact.** Per-miner energy equals the residency sum to `0.0 J`
    (metrics `max_energy_identity_residual_j = 0.0` in every scenario).

12. **Deterministic.** Fixed SHA-256 targets, deterministic reserve ordering
    `(activation_priority, MinerID)`, no wall-clock / RNG / network — runs are reproducible.

## Explicit non-claims

13. **The target and difficulty are never changed by the floor** (retained S3-17); the floor
    is a separate operational field.

14. **The complete-seat-failure path is real, not only injected.** Reserve activations near
    the run horizon whose CompleteEvent would fall past `T` fail to seat and are rolled back
    without stranding the miner (metrics: `activation_complete_seat_failure_count > 0` with
    `nonterminal_reserve_records_after_closure == 0`).  The StartEvent-seat-failure rollback
    (S3A-05) has no natural trigger in these runs (the StartEvent is seated at the current,
    non-finalised time) and is covered by fault injection.
