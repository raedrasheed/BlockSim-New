# Stage 7 — Claim Audit

Every claim touched in draft-43 is classified consistently with Stage 6A
(`STAGE_06_CLAIM_CLASSIFICATION.md`). Categories: SUPPORTED, INCONCLUSIVE,
SECONDARY_DIAGNOSTIC_ONLY, deterministic accounting identity.

| Thesis claim (as corrected in red) | Stage-6A classification |
|------------------------------------|-------------------------|
| Total fixed-horizon energy is fixed at 8.420833333 kWh; partitioning alone does not reduce it | A1 — deterministic accounting identity |
| Disjoint assignment eliminates duplicate candidate identities (B1 > B2 > B3/C1) under the modeled immutable-template/disjoint-range assumptions | H1 — SUPPORTED (seed-cluster) |
| C2 idle energy saving = Σ idle_time·(P_active−P_idle)/3.6e6, verified exactly; idle-driven | H3 — SUPPORTED (identity) |
| Homogeneous+equal ⇒ zero completion dispersion, zero idle | H4 — SUPPORTED |
| Hash-rate-weighted ranges reduce completion dispersion/idle but remove the idle saving (completion-balance vs idle-energy trade-off) | H5 — SUPPORTED + documented trade-off |
| Inactive miners lower raw energy via reduced participation, degrade block production; energy-per-block inconclusive | H6 — SUPPORTED (primary) / INCONCLUSIVE (epab) |
| Smaller μ ⇒ more exhaustion & template refreshes; block interval inconclusive | H8 — SUPPORTED / INCONCLUSIVE (interval) |
| Propagation delay raises single-height stale count-rate | H7 — SECONDARY_DIAGNOSTIC_ONLY |

## Claims removed/superseded (no longer asserted)

- "PoCol reduces total energy by ~98–99%" / "much lower cost per block" / energy scaling
  with miner count → superseded in red by the A1 invariant.
- "collaborative mining makes PoW substantially more energy-efficient" (unqualified) →
  narrowed to duplicate-identity elimination + idle/participation-driven energy only.
- Protocol/economic **fairness** claims → replaced by modeled range-completion balance;
  no reward/incentive/participation/economic/Sybil-resistance/proof-of-effort fairness.
- H7 as a chain-wide fork/stale-chain/security result → narrowed to single-height
  diagnostic.
- B3 vs C1 as independent samples → one physical dataset.
- B0/B1 as direct models of real Bitcoin mining → abstractions.

## Contribution / research-question consistency (§14)

RQ2 and the empirical-contribution statements (§8.2, §8.3) are corrected in red so no
contribution exceeds the evidence: the confirmed contributions are (1) duplicate-identity
control under the modeled assumptions, (2) an idle-/participation-driven energy mechanism,
and (3) the fixed-horizon energy invariant as a governing accounting result — not a
partitioning-based total-energy reduction and not deployment/PoW-equivalence readiness.

**Claim audit: PASS** — no surviving claim exceeds the Stage-6A evidence.
