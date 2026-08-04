# Stage 8M — Limitations (prominent, binding on every downstream use)

Every statement derived from Stage 6M/7M/8M carries these limits. They restate and extend
`STAGE_06M_LIMITATIONS.md` after seeing the data; nothing here relaxes a frozen rule.

1. **Reduced-resource design.** The confirmatory experiment is the resource-minimal
   redesign adopted after the original 660-row design was measured computationally
   infeasible (superseded before any data collection). Findings are claims about the
   minimal core, not about the superseded design.
2. **20-miner primary confirmatory scale.** All confirmatory inference is at 20 miners,
   horizon 300 s, nonce domain 1600, difficulty 1000, fixed target. No claim extends to
   other scales, horizons or difficulty regimes.
3. **10 paired seeds.** n = 10 is the preregistered inferential unit count. The exact
   permutation floor is p = 1/1024; intervals are percentile bootstrap intervals over 10
   seeds. The estimates are tight here because the effect is large and consistent, not
   because n is large.
4. **Two descriptive 141-miner sanity checks only.** X01/X02 are single-seed, PILOT-seeded,
   non-inferential runs. They corroborate direction, integrity and feasibility at scale;
   they confirm nothing.
5. **Leases / adversarial / incentive mechanisms: executably validated, not confirmatorily
   tested here.** The accepted 195-test suite validates those mechanisms deterministically,
   but the minimal confirmatory matrix disables them. **No broad security claim and no
   incentive claim** is made anywhere in this stage.
6. **No unconditional PoCol energy-reduction claim.** H-M1 passed, but the frozen decision
   rule licenses an energy claim only jointly with H-M3, and H-M3 exceeded its service
   limits. The only permitted statement is the conditional one recorded in the analysis
   report: large, consistent idle-policy energy reduction **accompanied by operational
   capacity degradation under the accepted 0.80 × H0 floor and the accepted engine's wake
   semantics**, at this configuration.
7. **Within-run counterfactual, not a hardware measurement.** E_power_null is an exact
   price-substitution counterfactual on the same event path (proved executably by
   `test_s6m_04`), with declared wattages. It is not a physical power measurement and does
   not model hardware DVFS, thermal effects or real-network latency.
8. **Floor semantics are the accepted engine's semantics.** Still-WAKING primaries are
   excluded from `H_effective` (declared structural risk, D-record IP-H7). The H-M3
   failures quantify the cost of the floor **as implemented and accepted**; they do not
   evaluate alternative wake-crediting semantics, which would be a different (post-hoc)
   model and are out of scope.
9. **Determinism and environment.** Results are exactly reproducible from the frozen seeds,
   configs and engine (SHA-256-bound in every run record) on CPython 3.11; wall/RSS figures
   are environment-specific and non-normative.
