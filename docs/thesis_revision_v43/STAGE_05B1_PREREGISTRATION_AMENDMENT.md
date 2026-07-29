# Stage 5B1 — Preregistration Amendment: H2 → Accounting Invariant A1

**Amendment date:** 2026-07-29 (Stage 5B1, before Stage-5B2 execution)
**Amends:** `STAGE_05A_PREREGISTRATION.md` (frozen; **not edited**)
**Status:** transparent, dated amendment — the frozen preregistration remains
byte-for-byte unchanged; this document records the reclassification and its
rationale.

## 1. Change

The Stage-5A confirmatory hypothesis **H2 (continuous-operation energy
equivalence)** is **reclassified** as **Accounting Invariant A1**. It is removed
from the set of confirmatory *hypotheses* (H1, H3–H8 remain confirmatory) and
recorded instead as a deterministic accounting identity that requires no
statistical test.

## 2. Rationale

H2 asserted that B0, B1, B2, B3/C1 have equal total energy under matched
aggregate hash rate, active power, and duration. Under the Stage-2 wall-clock
energy model this is **true by construction**, not empirically:

```
E = P_total · T,   P_total = H_net · efficiency = 141e12 · 21.5 / 1e12 = 3031.5 W
E = 3031.5 W · 10 000 s / 3.6e6 = 8.420833333… kWh
```

`P_total` and `T` do not depend on miner count or on the search discipline that
distinguishes B0/B1/B2/B3/C1. Total energy is therefore identical across those
scenarios as a matter of arithmetic. Testing an accounting identity with seeds,
tolerances, and confidence intervals would be a category error — it would dress a
deterministic equality as an empirical finding.

## 3. What A1 states (and does not)

**A1 (Accounting Invariant).** For all continuous scenarios (B0, B1, B2, B3/C1),
total energy equals `P_total · T` exactly (to floating-point precision), for every
miner count and search discipline. Confirmed for N ∈ {100…500} in validation
(checks B5-*, G-B0/B1/B2/B3, and the 62 Stage-5B1 tests).

A1 is an **equivalence by identity**, explicitly **not** a claim that any scenario
is *superior*. Search discipline changes coverage and energy-per-accepted-block,
never total energy. C2 is excluded from A1 because in-loop idle can remove active
time (energy ≤ A1), and that reduction is governed by H3/H4/H5.

## 4. Effect on the analysis plan

- The Stage-5A equivalence rule for H2 (relative tolerance 1e-6 on total kWh)
  becomes the **verification tolerance for A1** — used to *confirm the identity
  reproduces*, not to test a hypothesis.
- No seeds, outcomes, or rules for H1, H3–H8 change.
- The matrix labels the continuous CORE runs `hypothesis_id = "H1;A1"`: they serve
  the duplicate-coverage hypothesis (H1) and confirm the accounting invariant (A1).

## 5. Integrity

This amendment is additive and dated; it does not alter the frozen preregistration
or any outcome definition. It is made **before** the full matrix executes and is
motivated by the model's structure, not by any observed result.
