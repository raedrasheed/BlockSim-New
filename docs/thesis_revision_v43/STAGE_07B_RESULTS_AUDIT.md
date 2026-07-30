# Stage 7B — Results Audit (Chapter 7 / Chapter 8) (§5, §8, §9)

Verifies that the results and conclusion narrative in `Raed-Rasheed-draft-44-00.docx`
presents the corrected Stage-6A findings in place, with corrected figures and tables embedded
and no surviving conflicting black-text claim.

## Chapter 7 — corrected results content (A–I coverage)

The corrected findings are integrated into the existing Chapter 7 structure by in-place red
replacement plus embedded corrected figures/tables. Coverage of the Stage-6A finding set:

| Finding | Where in draft-44 | Status |
|---------|-------------------|--------|
| (A) A1 energy invariant (8.420833333 kWh; no miner-count scaling) | §7.4.1 prose (red) + Table 7.1 row + Figure 7.4 | ✅ |
| (B) H1 duplicate elimination (B1>B2>B3/C1; 150 pairs; 30 clusters; B3/C1=0) | Table 7.1 row + **Table 7.2** + Figure 7.5 + §8.3 | ✅ |
| (C) H3 idle-saving identity (570/570; residual 7.1e-15 kWh) | §7.4.3 idle prose (red) + Table 7.1 row | ✅ |
| (D) H4/H5 completion-balance vs idle-energy trade-off (no fairness) | §7.4.3 (red) + Figures 7.6–7.7 + Table 7.1 row | ✅ |
| (E) H6 inactive-miner effects (interval↑, blocks↓; epab inconclusive) | Figure 7.8 + Table 7.1 row | ✅ |
| (F) H8 finite-domain μ (exhaustion/refresh; interval inconclusive) | Figure 7.9 + Table 7.1 row | ✅ |
| (G) H7 secondary single-height stale diagnostic (N separate; count-rate) | §7.3.3 + §7.4.3 (red) + Figure 7.10 + Table 7.1 row | ✅ |
| (H) Conditional metrics / zero-block NA (total/defined/undefined/reason) | **Table 7.3** + §7.4.1 per-block prose (red) | ✅ |
| (I) Scope: B0/B1 abstractions; B3/C1 one dataset; no generalization | Table 7.2 note + §8.3 (red) | ✅ |

Obsolete conflicting prose in §7.2, §7.3.3, §7.4.1, §7.4.2, §7.4.3, §7.6.1, §7.7 was
**replaced in place** (red), not annotated; see `STAGE_07B_OBSOLETE_TEXT_AUDIT.md` (PASS).

## §8 — required tables (all present)

- **Table 7.1** (replaced): corrected 7-row Stage-6A summary.
- **Table 7.2** (H1): duplicate-evaluation rate by scenario; **150 physical seed-matched runs
  per scenario**; uncertainty from **30 independent master-seed clusters**; B1>B2>B3/C1;
  **B3/C1 = 0** duplicate identities; explicit note **B3 and C1 are one dataset, never
  double-counted**.
- **Table 7.3** (conditional epab): columns **total / defined / undefined (NA) / reason**;
  zero-block retained, NA not imputed; B3/C1 one dataset (870 runs) never counted twice.

## §9 — discussion / RQ / contributions / conclusion (rewritten in place)

- §7.6.1 RQ interpretation, §7.6.1 closing, §7.7 summary/limitation rewritten (red) to the
  bounded finding set.
- §8.1 outcomes, §8.2 RQ2, §8.3 empirical + conceptual contributions, §8.4 practitioner
  caution rewritten (red).

Six stated conclusion points now supported by the corrected narrative:
1. Total fixed-horizon energy is an accounting invariant (A1); partitioning alone does not
   reduce total energy or carbon.
2. The confirmed effect of disjoint assignment is elimination of duplicate serialized
   candidate-header evaluations among honest miners (H1), under modeled assumptions.
3. Energy reductions arise only under the explicit idle policy (H3 identity; H5 trade-off) or
   from reduced participation (H6) — a completion-balance vs idle-energy trade-off, not
   fairness or a PoW-vs-PoCol advantage.
4. The propagation-delay stale behaviour is a **secondary single-height diagnostic** (H7),
   not a chain-wide fork or security rate.
5. B0/B1 are abstractions and B3/C1 are one physical dataset; the zero-duplicate result does
   not generalize to real miners that independently vary header fields.
6. PoCol is a proof-of-concept for the coordinated candidate-header abstraction; the full
   distributed common-template agreement protocol is specified but not yet executable, and
   chain-quality/fork control remain open engineering requirements.

## Verdict

**RESULTS AUDIT: PASS** — corrected Stage-6A findings integrated in place; required figures
and tables embedded; discussion/RQ/contributions/conclusion rewritten; no conflicting
black-text result claim survives.
