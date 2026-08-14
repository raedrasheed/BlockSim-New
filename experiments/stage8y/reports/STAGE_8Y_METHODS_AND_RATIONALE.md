# STAGE 8Y — METHODS AND RATIONALE

Why Stage 8Y is built the way it is. Every choice below was fixed before the
confirmatory matrix ran (see `STAGE_8Y_FREEZE_REPORT.md`), and each is justified on
validity grounds rather than by which protocol it favours.

---

## 1. What Stage 8Y adds to Stage 8X, and why

Stage 8X established that under **homogeneous** hardware, disjoint nonce allocation
plus post-range low power yields only ~0.23 % energy saving, because identical miners
holding identical slots complete them simultaneously and therefore have almost no
surplus idle time. Stage 8Y asks whether the missing ingredient was **heterogeneity**:
if miners differ in efficiency, an energy-aware coordinator could in principle park
electrically expensive capacity and keep cheap capacity running.

Stage 8Y therefore adds exactly four mechanisms and nothing else: heterogeneous ASIC
populations, energy-aware active-set selection, a four-state power model with an
explicit wake cost, and adaptive reserve activation. Everything that could otherwise
confound the comparison — SHA-256 semantics, candidate identity, propagation,
acceptance, stale-work cancellation, seed discipline — is inherited unchanged, and
the hashing primitives are **imported read-only from Stage 8X** so they are provably
identical rather than merely similar.

The homogeneous composition H0 is retained as a control precisely so that Stage 8X
is the limiting case of Stage 8Y: any Stage 8Y effect that also appears at H0 is not
attributable to heterogeneity.

## 2. Why the comparator is favourable to PoW

Four deliberate choices all cut against the hypothesis:

* **Difficulty is derived from full installed hardware** and handed unchanged to
  every policy. Parking miners never reduces the work the network must do.
* **The nonce domain is derived from installed capacity**, and is partitioned into
  one slot per *installed* miner. Parking a miner leaves its slot unscanned; it does
  not shrink the domain. The alternative (sizing the domain from *active* capacity)
  would covertly reduce the requirement in PoCol's favour and is therefore excluded
  from the primary design.
* **Waking draws full active power while performing no hashing.** No manufacturer
  wake-power curve exists, so the conservative option was taken.
* **Traditional PoW keeps distinct per-miner templates and rolls its extranonce
  locally and instantly**, so it never idles and never performs duplicate work. The
  common-template comparator, in which duplicates are real, is confined to a labelled
  secondary diagnostic and is never used as the baseline.

## 3. Why the block-rate/energy trade-off is structural, not an artefact

Under matched difficulty the network finds blocks at rate `H_active(t) · q`, so block
retention tracks the time-average active hash fraction almost exactly. Energy tracks
the time-average active *power* fraction. The only way to break the 1:1 trade is to
make the removed power fraction exceed the removed capacity fraction — which is what
`SelectivityGain = PowerRemoved / CapacityRemoved` measures, and which is bounded by
the efficiency spread in the registry (15.0 → 29.5 J/TH, a factor of 1.967).

This was stated in the implementation plan §5 **before** execution, and the results
confirm it: `SelectivityGain` is 1.000 at H0 and 1.30–1.34 at H2/H4. The mechanism is
real but bounded, and it cannot deliver a large saving at high retention.

## 4. Why the decomposition is mandatory and how it is made exact

Because every miner is in exactly one of four states and waking is charged at active
power, `P_N·T = pw_active + pw_waking + pw_low + pw_standby` holds **identically**, so
the saving is exactly `(1 − α)·(pw_low + pw_standby)`. That identity makes two
orthogonal decompositions exact rather than approximate:

* **by cause** — participation (what a capacity-neutral removal would have saved) vs
  selection (the extra saving from parking expensive capacity), reported both
  sequentially and as a Shapley split because a two-factor attribution is
  ordering-dependent;
* **by state origin** — post-range low power vs reserve standby.

Both sum to the total with residual 0.0 J, asserted in test. This is what prevents
the claim "PoCol saved 54 %" when the honest statement is "three-quarters of that is
simply doing less hashing".

`ΔE_stale = 0` by construction, and that is itself a finding: an ACTIVE miner draws
the same power whether its work is useful or stale, so eliminating stale work does
not reduce energy unless it also reduces active time. The stale-work *evaluation*
difference is reported in Table J as a physical-work diagnostic and deliberately not
folded into the energy identity.

## 5. Why α is accounting-only but wake delay is simulated

α changes no dynamics, so each trajectory is simulated once and re-priced five times:
1080 physical primary runs, 4050 derived energy observations, always reported apart.
`t_wake` **does** change dynamics (a waking miner is unavailable), so it is a
simulated parameter with its own sweep. Conflating the two would misstate how much
evidence exists.

`LOW_POWER` and `STANDBY` share α because no vendor data distinguishes them; their
residence is nevertheless tracked separately so the assumption can be revisited
without re-running anything.

## 6. Why S4 is solved exactly

`min Σ P_i s.t. Σ h_i ≥ H_required` is a covering knapsack. A greedy efficiency-first
solution is *not* guaranteed optimal, and an "optimisation" policy that is silently
suboptimal would understate the mechanism under test. With few device classes the
problem is solved exactly by enumerating the counts of every class except the most
efficient and solving that one in closed form, with a documented stable tie-break.
The Pilot found and fixed a shared-buffer bug in this solver, and the fix is now
guarded by a test that checks the optimiser against **exhaustive enumeration**.

## 7. Why confirmatory and exploratory runs are separated

The brief's central risk is choosing a favourable configuration after seeing results.
Stage 8Y therefore declares one confirmatory parameterisation per policy **before
execution** (S4 selection; r_H = 0.60 as the midpoint of the pre-declared range; the
0.60→0.75→0.90→1.00 schedule; 300 s trigger; 10 s wake) and treats every sweep around
those values as secondary. Confirmatory and exploratory results are stored in
separate files, tagged separately, and never pooled in a statistical statement.

## 8. Statistical approach

All primary comparisons are seed-paired. Normality of the paired differences is
checked before choosing between the paired t-test and Wilcoxon signed-rank; magnitude,
a t-based CI, a **paired bootstrap** CI, Cohen's d_z and the rank-biserial correlation
accompany every p-value; Holm-Bonferroni is applied within each metric family. For the
central questions the analysis puts a bootstrap CI around the quantity itself and asks
whether the bound clears 0.50 / 0.90 / 0.95, rather than testing a difference from
zero. Undefined ratios are dropped as NA and counted; they are never replaced by zero,
and no run was discarded.

## 9. What would have falsified the design

The plan recorded in advance that retention ≈ r_H and saving ≈ (1−α)(1−r_P), that
selectivity is bounded by a factor of 1.967, and that Outcome C or D was therefore a
live possibility. That expectation was written down so a negative result could not
later be presented as a surprise, and so a positive result could not be presented as
if the design had been neutral about it. The observed outcome (C) is the one the
pre-registered reasoning identified as most likely, and it is reported as such.
