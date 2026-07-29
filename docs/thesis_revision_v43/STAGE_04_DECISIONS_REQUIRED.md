# STAGE 04 — Decisions Required Before Stage 5

Twelve decisions (section 19) plus one storage decision. Each has a
recommendation; **none is applied without approval.**

| # | Decision | Options | Recommendation |
|---|---|---|---|
| 1 | Solution-count sampling | exact Binomial vs Poisson | **Exact Binomial** (already implemented + validated; Poisson kept as labelled diagnostic). |
| 2 | B0 template abstraction | byte-level serialized headers vs abstract per-miner template identity | **Abstract per-miner template identity**, labelled "independent-template PoW abstraction" (not "exact Bitcoin"). Byte-level serialization is future work. |
| 3 | B3 vs C1 distinction | manufacture a difference vs state equivalence | **State C1 ≡ B3 in the executed simulator** (Path A: TemplateID commitment / pre-committed reward not implemented). Report C1 as the PoCol continuous abstraction, numerically equal to B3. |
| 4 | Hash-rate distributions | which heterogeneous law | **Homogeneous (H/N) primary**; one documented **log-normal** heterogeneous law for sensitivity (report σ, Gini ≈ 0.4, max/min share). Not chosen to favour PoCol. |
| 5 | Range allocation | equal vs weighted | **Equal for homogeneous baseline**; heterogeneous sensitivity compares **equal vs configured-hash-rate-weighted**. Measured-hash-rate-weighted stays *future work* (no verifiable permissionless measurement). |
| 6 | Propagation-delay levels | — | **{0, 0.42, 1, 5, 30, 60} s** (0 by construction → 0 stale). |
| 7 | μ / nonce-domain levels | — | **{0.5, 1, 2}** (μ=2 base; μ<1 needed to observe C2 idle saving and exhaustion). |
| 8 | Inactive-miner fractions | — | **{0, 5, 15, 30} %**. |
| 9 | Idle-power ratios (C2) | — | **{0, 5, 10, 20, 30} %**; 0 % = explicit theoretical lower bound (not the headline). |
| 10 | Coordination energy | excluded vs configured | **Excluded (0) as idealized lower bound**, reported as a separate field; a *configured* sensitivity only if the candidate supplies a measured/justified value — **never invented**. |
| 11 | Confirmatory vs exploratory | which hypotheses pre-registered | **Confirmatory (pre-registered direction):** A1, A3, A4, A5, A8. **Exploratory:** A6, A7, A9, A10 + churn/topology. |
| 12 | Stage-5 run count & budget | scale | **≈ 3 240 runs (core+sensitivity), ≈ 2.5 CPU-hours**, ~10–15 min parallel. Approve, trim, or expand. |
| S | **Storage of raw outputs** | full workbooks vs summaries | **Summary row per run + small diag.json (~10–20 MB total)**; full EnergyLog only for a ~20-run validation subset. Full per-run workbooks (~3.2 GB) exceed the environment and are rejected. |

## Cross-cutting caveats the candidate should confirm
- The **duplicate-elimination ⇒ energy saving** claim is **not** supported for
  *total* energy (only energy-per-block / coverage); Stage 6 will word it that way.
- **C2 idle saving is null under symmetric homogeneous μ ≥ 1**; a genuine saving
  requires early range completion (μ < 1 or heterogeneous equal-range). The
  thesis energy claim must be scoped to those conditions.
- **C1 ≡ B3** numerically; PoCol's implemented novelty over B3 is protocol
  metadata/reward that is *specified, not executed*.
