# Stage 6 — Limitations and Scientific Wording

Bounds on interpretation (§18). Every Stage-6 claim is conditioned on the modelled
assumptions and the frozen matrix; none is a real-deployment or security claim.

## 1. Modelling scope

- All results are **within the fixed 10,000-second horizon**, the **frozen aggregate
  hash-rate setting** (141 TH/s, efficiency 21.5 J/TH → P_total = 3031.5 W), and the
  frozen seed schedule (30 seeds). They are simulation outcomes, not measured deployment
  performance.
- B0 and B1 are **abstractions**, not real Bitcoin mining. B0 is an independent-search
  baseline; B1 is a redundant common-template baseline. They are not claimed to reproduce
  real miners hashing distinct dynamic headers.
- The energy model is a wall-clock `P·T` accounting model (Stage 2). Total energy for
  continuous full participation is fixed by construction (A1); the model does not
  represent hardware transients, DVFS, or network-level effects.

## 2. What must NOT be concluded

- **Not** that PoCol reduces energy merely by partitioning the nonce domain. Under
  matched aggregate hash rate and power, partitioning alone leaves fixed-horizon total
  energy unchanged (A1; H3 under homogeneous-equal). Every observed energy reduction is
  attributable to an explicitly modelled reduction in **active power-time** (C2 idle under
  heterogeneity, H5) or in **participation** (inactive miners, H6) or **idle power**.
- **Not** that fixed-horizon energy scales with miner count: at fixed aggregate hash rate
  and active power, total energy is independent of N.
- **Not** that all real PoW miners hash identical headers; the zero-duplicate result for
  disjoint allocation (B3/C1) holds only under an **immutable common template** with
  **disjoint assigned candidate ranges**, and does not generalize to independently
  changing real-world headers.
- **Not** complete elimination of all real-world duplicate work, **not** full
  blockchain-security equivalence, **not** full stale-chain / fork behaviour from the
  single-height diagnostic (H7), and **not** real deployment performance from simulation.

## 3. Statistical limitations

- 30 seeds per configuration; effects near the tolerance of the design (e.g. H8 block
  interval, H6 energy-per-accepted-block) are INCONCLUSIVE and reported as such.
- Confirmatory families use Holm correction; this is conservative when a family pools many
  outcomes (e.g. H6), which can render a directionally-consistent small effect
  non-significant. Such cases are classified INCONCLUSIVE, not NOT_SUPPORTED.
- B3 and C1 share one physical execution; they are never treated as independent samples.
- No fairness, incentive, reward, or Sybil claims are made — those mechanisms are not
  implemented.

## 4. Approved bounded wording

Use: "under the modelled assumptions"; "within the fixed 10,000-second horizon"; "for the
frozen aggregate hash-rate setting"; "under an immutable common template"; "for disjoint
assigned candidate ranges"; "in the single-height stale-race diagnostic"; "conditional on
at least one accepted block". These qualifiers accompany the corresponding Stage-6 claims
throughout the results report.
