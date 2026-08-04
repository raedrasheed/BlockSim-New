# Stage 6M — Limitations (declared before execution)

1. **Reduced scale.** The primary confirmatory scale is 20 miners / 300 s, not the 141-miner
   / 10 000 s reference. The two 141-miner scale checks are descriptive sanity checks only.
2. **n = 10 seeds.** Power is limited by design; wide intervals are reported as inconclusive.
3. **Within-run counterfactual.** E_power_null is a price substitution on the same residency
   ledger. It is exact for the accepted engine (proven by the invariance test) but it is a
   counterfactual about POWER PRICES, not an independently simulated control arm.
4. **Mechanisms not re-confirmed.** Range leases, reassignment, all adversarial behaviours
   and the incentive model are executably validated by the accepted 195-test suite and prior
   deterministic evidence, but receive no new multi-seed confirmatory matrix here. No broad
   security or incentive claim is made.
5. **Known floor semantics risk.** The accepted engine counts the per-round WAKING ramp as
   below-floor capacity, so H-M3's 15 s below-floor limit is at structural risk; it is frozen
   anyway and will be reported honestly.
6. **No unconditional claim.** Any energy statement is conditional on H-M1 passing AND H-M3's
   operational limits, at this configuration, under the idle policy within PoCol.
