# STAGE 8X — METHODS AND RATIONALE

Why Stage 8X is built the way it is. Every design choice below was fixed before the
primary matrix was executed (see `STAGE_8X_FREEZE_REPORT.md`), and each is justified
on validity grounds rather than by which protocol it favours.

---

## 1. Why a new experiment family, and why a new engine

Earlier macro experiments in this repository hold the **aggregate** network hash rate
fixed (`InputsConfig.NetworkHashRate_Hps = 141e12`) and treat `Node.hashPower` as a
*share*. Under that model, adding miners subdivides a fixed budget: per-miner capacity
falls as N grows, and neither aggregate hash rate nor aggregate power responds to the
population. Stage 8X asks the opposite question — what happens when every miner is one
real, whole ASIC — so it cannot inherit those constants, and it does not.

The audit (Phase 1) found three structural obstacles in the existing engine:

* `InputsConfig` binds `model`, `NODES`, `Nn` and `simTime` at *import* time, and
  `Scheduler` binds the `Block` class at import time. A 300-run matrix spanning five
  network sizes cannot be executed in one process against that design.
* All randomness flows through the process-global `random` module, so paired seeding
  across protocols is not expressible.
* The existing PoCol energy rule charges each miner `block_time / N_miners`, which is a
  modelling assertion that manufactures an O(1/N) "saving" rather than measuring one.

Stage 8X therefore uses an isolated engine with an injected immutable config and
per-purpose, per-miner RNG streams. It preserves the BlockSim *semantics* that matter
(heap event queue with `(time, seq)` ordering, `Exp(1/Bdelay)` gossip propagation to
all peers, longest-chain acceptance, stale-work abandonment) and reuses the pure,
already-unit-tested `Models.Energy` constants. It imports **nothing** that carries
global state, so no earlier experiment can be perturbed.

## 2. Why the difficulty must be network-size coupled

With `H_N = N x 234 TH/s` growing in N, a fixed difficulty would make blocks arrive
five times faster at N = 500 than at N = 100, confounding population with block rate.
Coupling `D_N = H_N x 600 / 2^32` holds the *matched PoW baseline* at a nominal 600 s
interval at every N, so N varies the population while the service target stays fixed.

Critically, **one** `D_N` is computed per N and handed to both protocols. PoCol is
never recalibrated to make its block interval match PoW's; any difference in block
production or latency is an outcome, not an input.

## 3. Why an abstraction over SHA-256, and why it is not a shortcut

The primary matrix corresponds to ~1e21 candidate evaluations. Executing those as
Python hashes is impossible, and pretending to is forbidden. Stage 8X instead uses a
**winner oracle** that is mathematically equivalent to enumeration:

* acceptance is `SHA256d(header ‖ extranonce ‖ nonce) <= target`, so with SHA256d
  uniform on `[0, 2^256)` the winning candidates form an i.i.d. Bernoulli(q) field with
  `q = target/2^256`;
* the set of winners inside a domain of size M is therefore `Poisson(qM)` points at
  i.i.d. uniform positions, which is sampled directly;
* each miner's cursor then advances deterministically at its *physical* rate
  `h = 2.34e14 candidates/s`.

Two properties make this a model rather than a fudge. First, the field is **consistent
across miners**: if two miners evaluate the same `(template, candidate_index)` they get
the same answer, so duplicated work is genuinely wasted instead of silently doubling
the block rate — this is what makes the matched-template comparator meaningful.
Second, the mapping is pinned to real hashing: `monte_carlo_success_rate` performs
genuine double SHA-256 over genuinely serialized candidates at an artificially easy
target and confirms the empirical rate equals `target/2^256`.

Independent confirmation that the abstraction is faithful: the observed accepted-block
interval distribution matches `Exp(mean 600 s)` (figure `figD1`), and the observed
epoch-exhaustion share matches the closed-form `e^-1 = 0.368` (figure `figD3`) — neither
was fitted.

## 4. Why candidate identity is `(template_id, candidate_index)`

The brief insists that nonce-value reuse and exact-input duplication not be conflated.
A candidate is the exact serialized input; two evaluations are duplicates only if both
the template and the index match. Scanned work is recorded as half-open intervals per
template, so `W_unique` is the measure of their union and `W_duplicate = W_total -
W_unique` — exact, and computed without materialising 1e17 indices.

The consequence, reported rather than hidden: **traditional PoW performs zero exact
duplicate work**, because each miner owns a distinct coinbase and therefore a distinct
template. Its nonce-*value* reuse ratio is ~1.0 at the same time. Those two facts are
not in tension; they are the distinction the brief demands.

## 5. Why the nonce domain is derived, not tuned

The domain is the one parameter that could most easily be used to manufacture a result,
because a smaller epoch allocation mechanically buys more low-power time. It is
therefore derived from the protocol's own parameters:

```
S_N = H_N * tau_epoch,   tau_epoch = I_target = 600 s
L   = S_N / N = h * tau_epoch = 1.404e17 candidates per miner
```

One epoch holds exactly one block's expected work, so `P(no solution in an epoch)`
= `e^-1` by construction — a *predicted* quantity that the Pilot then verified rather
than fitted. The reduced Stage 8S/8U domain of 1600 is not reused; it was a diagnostic
setting for a different hash-rate regime.

Because this choice is consequential, the epoch allocation is additionally swept in a
**declared secondary analysis** (`tau ∈ {300, 60, 6} s`), frozen before execution, and
reported apart from the primary. That sweep maps the energy/throughput frontier
without letting any of it leak into the primary conclusion.

## 6. Why a liveness rule was needed (audit finding A5)

Read literally, the specified mechanism deadlocks. Homogeneous miners with equal
disjoint ranges finish those ranges at the *same instant*, so if the epoch domain
happens to contain no solution, every honest miner sleeps and the round can never end.
Since reserve miners, useful-work floors, reassignment and borrowing are all excluded
by design, the minimal remaining option is a **domain-exhaustion template refresh**: a
new common template with a fresh disjoint allocation, which each miner learns on
receipt. That is a round/epoch boundary, i.e. exactly the "legitimate wake-up event"
the specification anticipates.

This has an important interpretive consequence that the results section states
plainly: PoCol's low-power residency in this design is bounded by the time to *agree
on and receive* the next common template, not by any surplus of idle capacity. A PoW
miner rolls its extranonce locally and instantly at zero cost; a PoCol miner cannot,
because the template must be common for disjointness to be verifiable. That asymmetry
is the mechanism under test, and it is also the experiment's principal limitation.

The three exhaustion categories the brief asks to be distinguished are counted
separately throughout: legitimate per-miner range completion, global domain exhaustion,
and simulator artifact (zero occurrences after the Pilot fix).

## 7. Why alpha is accounting-only

Nothing in the engine reads alpha — asserted by a test that scans the engine source.
The physical trajectory for a given `(N, seed)` is simulated once and re-priced four
times from the recorded residencies, so the primary matrix is 300 physical runs and 600
derived energy observations. Presenting the sensitivity cases as if they were 1200
simulations would misstate the evidence, so the two counts are reported separately
everywhere.

## 8. Why the pairing is per-miner

Master seeds are split by purpose *and* by miner: miner i's search stream, its
propagation-delay stream and its template stream are derived independently. The same
`(N, k)` therefore gives miner i the same k-th search outcome under both protocols.
This is much stronger than seeding a global RNG identically, and it is why the paired
differences are so tight (e.g. all 30 paired active-time differences share the same
sign at every N).

## 9. Why transactions are excluded

The workload model contributes nothing to hashing, energy or block timing in either
protocol, and including it would add matched noise without enabling a fair throughput
comparison (both protocols would inherit the same tx model by construction). Blocks per
hour is used as the service metric instead. This is recorded as a limitation, not
presented as a neutral choice.

## 10. Statistical approach

Every primary comparison is seed-paired. Normality of the paired differences is tested
before choosing between the paired t-test and Wilcoxon signed-rank; the selected test
is named per row. Magnitude, 95 % CI, and both a parametric (Cohen's d_z) and a
non-parametric (rank-biserial) effect size are always reported alongside the p-value,
and Holm-Bonferroni correction is applied within each metric family across the five
network sizes. Sensitivity and secondary analyses are labelled as such and are not
folded into the primary family. Undefined ratios (e.g. latency ratio when a run
produced no block) are dropped as NA and counted; they are never replaced by zero, and
no run was discarded for producing few or zero blocks.

## 11. What would have falsified the design

The design was built so that a null result was reachable and reportable. In particular,
before execution it was recorded in the Pilot report that (a) traditional PoW performs
no exact duplicate work, so no duplicate-work advantage is available to PoCol in the
primary comparison, and (b) simultaneous range completion bounds low-power residency to
a small value. Both expectations were borne out, and the results are reported as the
neutral/negative outcome they are rather than reframed.
