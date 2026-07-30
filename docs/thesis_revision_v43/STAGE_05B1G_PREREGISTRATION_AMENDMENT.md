# Stage 5B1G — Preregistration Amendment (H7 reclassification)

**Amends:** `STAGE_05A_PREREGISTRATION.md` (frozen before Stage 5B).
**Date:** recorded with the Stage 5B1G corrective commit.
**Nature:** reclassification of one hypothesis + one analysis rule. **No seeds,
scenario semantics, or other hypotheses are changed.** No thesis prose is edited.

## 1. Why

Stage 5B1G establishes that the stale model is a **single-height stale-race
diagnostic**: it measures, for one accepted height in isolation, which non-winning
miners would have published a competing block before receiving the winner. It has no
chain-reorganisation, fork-resolution, or cross-height semantics, and its energy and
evaluations are deliberately **not** integrated into the primary metrics. A quantity
of this scope cannot support a *confirmatory* claim about protocol behaviour.

## 2. Amendment

**H7 (propagation delay)** is reclassified from a **confirmatory** hypothesis to a
**secondary diagnostic sensitivity**:

> **H7 (propagation delay) — SECONDARY DIAGNOSTIC SENSITIVITY (amended 5B1G).**
> Within the single-height stale-race diagnostic, ↑ propagation delay ⇒ ↑ single-height
> stale rate, because a larger `received_winner_time` widens the window in which a
> distinct non-winning miner can discover a competing solution. Reported as a
> **descriptive sensitivity** of the diagnostic (secondary outcome), **not** as a
> confirmatory result about the protocol. The relevant statistic is
> `single_height_stales_per_accepted_block` (and its `single_height_stale_fraction_of_valid_proposals`),
> under the corrected model in which **each non-winning miner may produce at most one
> stale per height while multiple distinct miners may stale at the same height**
> (`stale_block_count ∈ 0 .. N_active-1`; no global one-stale-per-height cap).

Consequently the **outcomes list** moves "legitimate stale rate" from *Primary* to
*Secondary*, renamed `single_height_stales_per_accepted_block`. Analysis rule 4
(Stale rate) still applies (exact one-sided binomial / rule-of-three for zero
observations; Wilson otherwise) but now governs a **secondary diagnostic**, not a
confirmatory test.

## 3. Unchanged

- Confirmatory hypotheses **H1–H6, H8** are unchanged.
- Seed schedule (`6122dbd0…b13e10`), scenario semantics, matrix membership (63 × 30 =
  1 890) are unchanged.
- H2's continuous-energy equivalence and the A1 accounting invariant are unaffected
  (the stale-race diagnostic contributes no primary energy).

## 4. Integrity

This amendment is recorded **before** the full matrix executes and does not select or
alter seeds after examining outcomes. It reclassifies scope and evidential status
only; it does not change any measured quantity's definition beyond the corrections
documented in `STAGE_05B1G_STALE_DIAGNOSTIC_SCOPE.md`.
