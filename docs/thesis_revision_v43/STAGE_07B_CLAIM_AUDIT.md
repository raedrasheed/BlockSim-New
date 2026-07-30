# Stage 7B — Claim Audit

Every energy/collaboration claim in draft-44 is classified against the Stage-6A authoritative
findings. Obsolete claims were removed/replaced (see `STAGE_07B_OBSOLETE_TEXT_AUDIT.md`);
the surviving active claims are:

| # | Active claim (red) | Class | Authoritative basis |
|---|--------------------|-------|---------------------|
| 1 | Total fixed-horizon energy = 8.420833333 kWh for every continuous full-participation configuration and every miner count (max rel. dev. 3.6e-16). | ACCOUNTING INVARIANT (A1) | a1_invariant.json |
| 2 | Nonce-domain partitioning alone does not reduce total energy; no miner-count energy scaling. | INVARIANT consequence | STAGE_06_RESULTS_REPORT |
| 3 | Disjoint assignment eliminates duplicate serialized candidate-header evaluations among honest miners; ordering B1 > B2 > B3/C1; B3/C1 = 0 duplicate identities (150 pairs; 30 clusters; Holm p ≈ 2e-4). | CONFIRMATORY (H1) | table08_candidate_redundancy.csv |
| 4 | Idle-saving identity saving = Σ idle_time·(P_active−P_idle)/3.6e6 verified for 570/570 C2 runs (max abs residual 7.1e-15 kWh, 0 failures). | IDENTITY (H3) | STAGE_06A_H3_IDENTITY_AUDIT |
| 5 | Weighted ranges remove modeled dispersion/idle and return C2 energy to the anchor — a completion-balance vs idle-energy trade-off, **not** fairness. | CONFIRMATORY + TRADE-OFF (H4/H5) | STAGE_06A_CORRECTION_REPORT |
| 6 | Longer effective block interval and fewer accepted blocks as inactive fraction rises; epab inconclusive. | CONFIRMATORY / INCONCLUSIVE (H6) | table10_inactive_miners.csv |
| 7 | Range exhaustion and template refreshes increase as μ decreases; interval inconclusive. | CONFIRMATORY / INCONCLUSIVE (H8) | fig07_h8_mu.csv |
| 8 | single_height_stales_per_accepted_block rises with propagation delay; N=100/500 separate; count-rate; no binomial. | SECONDARY DIAGNOSTIC (H7) | STAGE_06A_H7_INTERVAL_AUDIT |
| 9 | B0/B1 are abstractions; B3 and C1 are two interpretations of one physical dataset (never double-counted); zero duplicates do not generalize to real headers. | SCOPE LIMITATION | STAGE_06A_DEPENDENCE_AUDIT |

No active claim asserts a PoCol-vs-PoW total-energy or carbon reduction, energy efficiency,
fairness, or a chain-wide fork/stale rate.

## Verdict

**CLAIM AUDIT: PASS** — all active energy/collaboration claims are red and map to an
authoritative Stage-6A finding with correct class (invariant / confirmatory / identity /
trade-off / inconclusive / secondary / scope).
