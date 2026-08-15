# Stage 8X-E50 — Methods and Rationale

## 1. What is being isolated, and why the baseline is artificial on purpose

The experiment isolates one mechanism: **coordination of search over a shared
2^32 header-nonce domain under a common immutable template**. The baseline
E50-MT100 deliberately removes template diversity so that uncoordinated search
produces measurable exact-input duplication; PoCol removes that duplication by
deterministic disjoint allocation. E50-CONV100 (conventional independent-
template PoW) is carried as an external reference precisely so the result can
never be silently generalized: conventional PoW has zero exact duplication and
therefore none of the recoverable waste that E50 measures.

## 2. Matched template-renewal rule

One rule for every arm: *a template epoch ends when every ACTIVE miner has
completed its assigned traversal, or a block ends the round.* MT100's
uncoordinated assignment is the full domain per miner (epoch = 2^32 ticks);
PoCol's assignment is the miner's own range (epoch = ⌈2^32/N⌉ ticks). The
faster PoCol template cadence is not an artifact but the coordination effect
itself: fresh templates are what turn evaluations into distinct inputs. The
rule is machine-checked (test 14: epoch seconds = assignment ticks / h in both
arms).

## 3. Engine abstraction

Identical to Stage 8X-NR (revalidated here): Bernoulli(q) field over distinct
inputs, Geometric(q) distinct inputs to first winner, winner uniform on the
winning epoch's searched set, integer-tick accounting (1 tick = 1/h s). PoCol
epoch arithmetic is O(1) via the partition prefix P[i] = ⌊i·2^32/N⌋: distinct
inputs per sliding-window epoch = window sum; any N consecutive epochs cover
exactly k·2^32 distinct inputs; at most N epochs of the final rotation cycle
are walked per round. Work and energy identities hold exactly (0.0 relative
error in all 1500 runs).

## 4. Active-set selection and rotation (brief §11)

k = ⌈A·N⌉. A fixed run-level slot assignment with a sliding window of k
consecutive slots advancing one slot per template epoch. Consequences, all
closed-form and verified: duty = k/N per miner over any N consecutive epochs;
Jain index 1.0; one activation episode (k consecutive epochs) per N-epoch
cycle; active episodes of k·⌈S/N⌉ ticks. No range borrowing, reassignment,
handoff, or reserve reallocation anywhere in the primary experiment.

## 5. Difficulty fairness (brief §13–14)

q_N = 1/(N·h·600), D_N = H_N·600/2^32, re-derived and asserted
(q·D·2^32 = 1). The same target is used by all ten arms at a given N; PoCol
active fractions are never retargeted. Reduced-active PoCol therefore competes
at the full-network difficulty; its block production is an outcome, not a
calibration.

## 6. Metrics

* **Unique coverage** U_exact: distinct (template_id, nonce32) inputs — the
  central metric; never substituted by total hash count.
* Physical work C_total; R_exact = C − U; ρ_exact; nonce-value reuse retained
  as a separate concept (Stage 8X-NR's instrumentation; PoCol cross-miner
  nonce overlap within epochs is zero by the same partition arithmetic).
* Energy from state-time: E(α) = P·(T_active + α·T_low); α ∈ {0,.1,.25,.5} are
  labelled sensitivity assumptions computed from one recorded trajectory.
* Service: pooled blocks/retention, pooled median-interval ratios, with
  explicit run counts and the preregistered NA rule for per-seed ratios when
  the paired MT100 run has zero blocks.
* Fairness: duty min/max/SD, Jain, transitions, episode durations.

## 7. Statistical design

30 fresh paired seeds (registry disjoint from Stage 8X/8X-NR/8Y/8Z, verified in
test). Common random numbers: identical geometric round streams across arms.
Deterministic quantities (coverage retention, savings, F_low, fairness) are
reported as magnitudes with degenerate CIs; stochastic quantities (blocks,
intervals) are reported pooled with counts. The feasibility filter, thresholds,
fractions, horizon and grids were frozen before the Pilot (config hash
`d74001f4e4b7…`); nothing was tuned toward 50 %, and the theory report
(written before execution) predicted every deterministic value subsequently
measured, including the LP50 failure to reach 50 %.
