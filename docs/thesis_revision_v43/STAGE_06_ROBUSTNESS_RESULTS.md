# Stage 6 — Robustness and Model Checking

Machine-readable: `results/thesis_revision_v43/stage_06/tables/table06_robustness.csv`.
For every confirmatory contrast we compare mean-based vs median-based effects and
parametric-adjacent vs non-parametric paired tests, and check assumptions.

## 1. Mean vs median (location)

Each contrast reports both the paired **mean difference** and the **Hodges-Lehmann**
median shift. For all confirmatory contrasts the two agree in sign; magnitudes are close
(e.g. H1 B1−B2 mean +0.395 vs HL +0.392; H6 interval means and HL shifts co-directional).
Conclusions do not depend on mean vs median.

## 2. Parametric-adjacent vs non-parametric test

The primary test is a distribution-free paired **permutation** test; **Wilcoxon**
signed-rank is reported as a sensitivity check (`wilcoxon_p` column). For every contrast
declared SUPPORTED the permutation and Wilcoxon tests agree on significance at α=0.05. The
`robustness` column flags any contrast where the two disagree or where mean/median
directions diverge — none of the SUPPORTED confirmatory conclusions is flagged.

## 3. Deterministic (design-identity) contrasts

Several contrasts have constant paired differences (B1−B3/C1 duplicate rate; H6
`inactive_domain` and `total_energy`; A1 energy). These are **not** dressed as empirical
tests: they are flagged `deterministic=True`, their permutation p is `None`, and they are
reported as exact design identities. This prevents zero-variance quantities from
manufacturing spurious significance.

## 4. Ties, zeros, skew, undefined outcomes

- **Ties / zeros:** duplicate-rate differences for B1 and B3/C1 are constant within a
  miner count; Wilcoxon uses only non-zero differences and the permutation test flags the
  degenerate all-equal case. Count outcomes with many zeros (single-height stales) are
  treated with Wilson / rule-of-three, not normal approximations.
- **Skew:** bounded/skewed outcomes are summarised with median/IQR and distribution-free
  intervals; inference is permutation/bootstrap based.
- **Undefined outcomes:** block-normalised metrics are NA for zero-block runs and are
  dropped pairwise (reported `n_dropped_na`), never imputed.

## 5. Inclusion sensitivity (all runs vs conditional subsets)

Unconditional claims (energy, accepted blocks, exhaustion, candidate counts, zero-block)
use all 30 seeds per config. Conditional block-normalised claims are computed only on
defined pairs and are explicitly labelled "conditional on ≥1 accepted block". The H6/H8
families have no zero-block runs, so their conditional and unconditional populations
coincide.

## 6. Multiplicity sensitivity

Every family reports raw and Holm-adjusted p. The conclusions that survive Holm (H1
ordering; H5 dispersion/idle; H6 interval and accepted-blocks; H8 exhaustion and
refreshes) are the ones classified SUPPORTED. Sub-claims that are directionally consistent
but do not survive Holm (H6 energy-per-accepted-block; H8 block interval; parts of H6
exhaustion) are classified INCONCLUSIVE — never as confirmations.

## 7. Influential observations

No observation is removed for being influential. Where a single seed produces an extreme
value (e.g. B2 duplicate rate tails), the distribution-free effect (HL) and bootstrap CI
absorb it; conclusions are unchanged with or without the extreme seed because inference
is rank/resample based, not moment based.
