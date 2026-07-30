# Stage 6 — Claim Classification

Per §17. Categories: SUPPORTED, NOT_SUPPORTED, INCONCLUSIVE, NOT_TESTABLE_AS_PREREGISTERED,
SECONDARY_DIAGNOSTIC_ONLY. Derived deterministically in
`models/claim_classification.json`. "Not statistically significant" is never read as proof
of no effect; an exploratory observation is never called a confirmation.

## Summary

| Id | Status | Disposition |
|----|--------|-------------|
| **A1** | accounting invariant | **SUPPORTED** by deterministic identity (max rel. deviation 3.6e-16 < 1e-6) |
| **H1** | confirmatory | **SUPPORTED** — B1 > B2 > B3/C1 duplicate rate (Holm p 3e-4; B1>B3/C1 by design) |
| **H3** | confirmatory | **SUPPORTED** — active+idle+coord=total identity; saving idle-driven, 0 under homogeneous-equal |
| **H4** | confirmatory | **SUPPORTED** — homogeneous equal ⇒ dispersion 0, idle 0 exactly |
| **H5** | confirmatory | **SUPPORTED** (weighted reduces dispersion & idle) **+ documented TRADE-OFF** (weighted removes the C2 idle energy saving) |
| **H6** | confirmatory | **SUPPORTED** for ↑interval, ↓accepted blocks, ↑unsearched, ↓raw energy; **INCONCLUSIVE** for "↑ energy per accepted block" |
| **H8** | confirmatory | **SUPPORTED** for ↑exhaustion & ↑template refreshes; **INCONCLUSIVE** for the effective-block-interval sub-claim |
| **H7** | secondary | **SECONDARY_DIAGNOSTIC_ONLY** — single-height stale rate ↑ with delay; primary metrics invariant |
| **H5x** | exploratory | **EXPLORATORY — NOT PREREGISTERED FOR CONFIRMATORY INFERENCE** |

## Justification (SUPPORTED criteria: direction met + effect supports + CI compatible + adjusted test meets rule + no fatal limitation)

- **A1 / H3 / H4** rest on deterministic accounting/geometry identities that reproduce
  exactly; SUPPORTED by identity, explicitly not as superiority claims.
- **H1** — direction met for all three contrasts; the two stochastic contrasts survive
  Holm with CIs excluding 0; the third is a design identity. SUPPORTED under the stated
  idealizing assumptions.
- **H5** — the fairness directions (dispersion, idle) are Holm-significant with CIs
  excluding 0. The energy outcome has no preregistered direction and is reported as a
  trade-off: weighting removes idle and therefore removes the idle-driven saving.
- **H6** — the interval-increase and accepted-block-decrease sub-claims are
  Holm-significant; the unsearched-domain and raw-energy reductions are design identities.
  The "may ↑ energy per accepted block" sub-claim is INCONCLUSIVE (small effect, CI spans
  0) — reported honestly, not as a confirmation.
- **H8** — exhaustion and template-refresh increases are Holm-significant; the realized
  block-interval increase is directionally consistent but not decisive → INCONCLUSIVE.
- **H7** — secondary diagnostic; not eligible for a confirmatory disposition.

## Nothing was over-claimed

No exploratory result (H5x, post-winner diagnostics, interactions) is used to confirm a
hypothesis. No INCONCLUSIVE sub-claim is upgraded. No accounting identity is presented as
an empirical protocol advantage.
