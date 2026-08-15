# Stage 8X-E50 — Implementation Plan

**Question:** under a common immutable template and fixed per-miner ASIC
capacity, how much active capacity and energy can PoCol's deterministic
disjoint allocation avoid while preserving the unique candidate coverage and
block production of an uncoordinated same-template PoW control?
**Comparator discipline:** the baseline is the *same-template competitive PoW
control* (E50-MT100), never "Bitcoin PoW"; E50-CONV100 is an external reference
only and never the >50 % denominator.

## Arms (10 scenarios per N × seed)

| arm | template | active miners | allocation |
|---|---|---|---|
| E50-CONV100 | per miner (extranonce renewal) | N | none (external reference) |
| E50-MT100 | common per epoch | N | none — independent offset traversal |
| E50-PC10…PC100 | common per epoch | k = ⌈A·N⌉, A ∈ {.1,.2,.3,.4,.5,.6,.8,1.0} | static disjoint partition of 2^32 over ALL N; only active owners search; no borrowing/reassignment/handoff |

Renewal rule (one rule, all arms): epoch ends when every active miner completes
its assigned traversal (MT: full domain; PC: own range) or a block ends the
round. Active-set rotation: fixed run-level permutation π, sliding window of k
consecutive slots advancing one slot per epoch — duty exactly k/N per miner,
minimal transitions; recorded per miner.

## Engine (exact integer ticks, same abstraction as Stage 8X-NR)

Bernoulli(q) field over distinct inputs; g ~ Geometric(q) distinct inputs to
winner; winner value uniform on the winning epoch's searched set. Round ticks:
CONV ⌈g/N⌉; MT F·S + first-hit(x*) + 1; PC: full rotation cycles (N epochs,
k·S distinct, N·⌈S/N⌉ ticks) + ≤N-epoch exact iteration of the final cycle +
offset in the winning owner's range. All work/energy/coverage counts exact
integers; identities t_active + t_low = N·T and W = Σ evaluations asserted per
run. Same D_N (q_N = 1/(N·h·600)) for every arm at a given N — no retargeting
for reduced active sets (§13/§14), asserted in test.

## Matrix

Pilot: N ∈ {100,300,500} × 10 arms × 2 dedicated seeds = 60 runs (excluded from
inference). Primary: 5 N × 10 arms × 30 fresh paired seeds = **1500 runs**,
runtime projected < 60 s (Stage 8X-NR engine ran 750 runs in 8.3 s). α-cases
are accounting-only (state-time recorded once; no per-α trajectories, test 20).
Staged execution by N in one frozen matrix; no early stopping on outcomes.

## Modules

```
config/e50_config.py   constants, fractions, difficulty audit, partition,
                       rotation, preregistered predictions, config_hash
config/seeds.py        30 fresh paired + 2 pilot seeds, disjoint from
                       8X/8X-NR/8Y/8Z registries
src/engine_e50.py      three arm families, exact accounting
src/run_matrix.py      pilot/primary execution, 9 raw CSVs
src/analysis_e50.py    tables E50-A..E50-M, feasibility filter, paired stats
src/figures_e50.py     15 figures (PNG+PDF+SVG)
tests/test_stage8xe50.py  the 20 required tests (§34)
```

## Preregistered feasibility filter (frozen before Pilot)

feasible(N, A) ⇔ UniqueCoverageRetention ≥ 0.95 AND pooled BlockRetention ≥
0.90 AND pooled MedianLatencyRatio ≤ 1.20; savings then reported per α;
MaxEnergySaving over feasible points; MaxBlockRetentionAt50 per α; per-seed
block ratios NA when the paired MT100 run has zero blocks (reported, not
imputed). Success is NOT defined as ">50 %"; outcomes A–D all reportable.

## Order

protect (done, 500-file baseline `69576696…`) → theory report (done) → this
plan → config/seeds → engine → 20 tests → pilot → pilot report → freeze →
1500 primary runs → analysis → figures → reports → protected-artifact
re-verification → commit/push → final 29-point answer with Q1–Q6.
