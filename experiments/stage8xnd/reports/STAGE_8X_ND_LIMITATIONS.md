# Stage 8X-ND — Limitations

1. **The zero-start sequential traversal is a stated conceptual model, not
   firmware telemetry.** Real ASIC lanes stride the nonce field in parallel;
   the secondary ND-PW-OFFSET diagnostic shows the energy/service conclusions
   are traversal-invariant, but fine-grained overlap structure is model-bound.
2. **Instant template renewal.** Header/extranonce rolling is modeled as free
   and instantaneous for both protocols. Any real per-renewal latency would
   penalize ND-PC more (it renews N× as often: every 37–184 ns) — the
   energy-neutral result is therefore an upper bound on PoCol's standing.
3. **Instant propagation; no orphan races** (disjoint or distinct-header
   search makes ties measure-zero here).
4. **Low-power states are sensitivity assumptions** (P_low = α·P_active), not
   Bitmain-certified modes; transitions are priced as free although ND-PC's
   straggler gaps are femtosecond-scale — physically no ASIC can enter a
   low-power state for 4.27 fs. The measured F_low ≤ 7.1e-8 is thus itself an
   upper bound on an unrealizable saving.
5. **Homogeneous fleet.** Identical hashrates make all ranges complete
   simultaneously; heterogeneous fleets would create real straggler windows —
   but also proportional block-rate structure (the Stage 8Y/8Z territory).
6. **The Bernoulli-field abstraction** (validated against real double-SHA-256
   in Stage 8X and by toy-domain enumeration in 8X-NR/ND test 20) replaces
   literal hashing; no operational SHA-256 is executed.
7. **Fixed 10 000 s horizon**; conditional interval means are truncation-
   biased low (532 s vs 600 s) — ratios between arms are unaffected.
8. **No difficulty retargeting within runs.**
9. **Nonce-domain utilization metrics are organizational, not security
   metrics.** Zero cross-miner overlap says nothing about attack cost.
10. **Findings are specific to the true 2^32 geometry at 234 TH/s.** On a
    hypothetical larger header-nonce field, sweep times and residency scale
    accordingly (Stage 8X's 600-s candidate domain shows what a 5-orders-
    larger effective domain yields: F_low ≈ 0.002).
