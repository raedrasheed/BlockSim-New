# Stage 3 — Known Limitations

Honest scope statement for the Stage-3 security-floor / reserve-activation implementation.
None of these affect the acceptance gates.

## Scope (deliberate, per the Stage-3 brief)

1. **Operational capacity floor only.** The security floor prevents the effective active
   hashing capacity from silently falling below a declared minimum while a round is open.
   It does NOT prove chain quality, common prefix, Bitcoin/PoW security equivalence, or
   resistance to any adversarial fraction, and it is not reported as such.

2. **No range leasing or reassignment.** A reserve searches only its own previously
   UNCLAIMED reserve-domain slice; it never reassigns another miner's partially-searched or
   abandoned primary range. Range leases/reassignment are Stage 4.

3. **No dynamic difficulty / rewards / Sybil / selfish-mining / security proofs /
   adversarial matrices / thesis integration.** Out of Stage-3 scope.

## Modeling notes

4. **Floor disabled by default.** `SecurityFloorPolicy.enabled = False`, so every accepted
   Stage-2B behaviour and test is unchanged; Stage-3 behaviour is opt-in per run.

5. **Reserve pool fixed per run.** The reserve set is the `reserve_fraction` pool computed
   once from the genesis population; each round mints fresh round-bound reserve records and
   slice identities. Dynamic reserve churn across rounds is not modeled.

6. **One reserve slice per reserve miner.** The domain is partitioned into
   `n_primary + n_reserve` contiguous slices; each reserve miner can claim at most one
   slice. Finer sub-slicing is not modeled.

7. **Capacity-change observation points.** `EvaluateSecurityFloor` runs at the points where
   `H_effective` can change (all-primary-active, range exhaustion, reserve-activation
   completion); a solution ends the round. A per-`HashWorkEvent`-commit observation is not
   taken because an ordinary commit does not change the active set (only completion, routed
   through exhaustion/solution, does).

8. **Tail activation under a positive floor.** When a round finds no block, `H_effective`
   falls to 0, which breaches any positive floor; the policy then pulls in every remaining
   reserve until the whole domain is searched or the pool is exhausted (FLOOR_UNATTAINABLE).
   This is the intended full-domain-exhaustion behaviour, so `floor_unattainable_count`
   accumulates once per genuine below-floor moment with no reserves left — it is a faithful
   count, not an error.

## Energy / determinism

9. **Reserve activation increases energy.** Waking and running reserves adds `P_wake` and
   `P_hash` residency; the adapter reports reserve standby/wake/active energy separately and
   never claims reserve activation saves energy.

10. **Energy identity is exact.** `E_i = P_reserve·t_reserve + P_wake·t_wake +
    P_active·t_active + P_idle·t_idle` holds to `0.0 J` because energy is the residency sum.

11. **Deterministic.** Fixed SHA-256 targets, deterministic reserve ordering
    `(activation_priority, MinerID)`, no wall-clock / RNG / network — runs are reproducible.

## Explicit non-claims

12. **The target and difficulty are never changed by the floor** (S3-17); the floor is a
    separate operational field.
