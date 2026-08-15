# Stage 8X-ND — Methods and Rationale

## 1. Fidelity to the researcher's concept

The primary control implements the stated model literally: every ND-PW miner
owns the full 32-bit nonce-value domain and traverses 0,1,…,2^32−1
sequentially from 0 on each header realization (zero-start is the PRIMARY
rule, per brief §9); after exhausting the domain it renews header-affecting
state (extranonce/template) and sweeps 0…2^32−1 again. Random-offset traversal
is only the secondary diagnostic ND-PW-OFFSET. PoCol replaces the N full-domain
copies with one partition: start_i = ⌊i·2^32/N⌋, end_i = ⌊(i+1)·2^32/N⌋−1
(inclusive; max value 2^32−1, never 2^32), verified for coverage, disjointness
and ≤1 spread. The domain is never enlarged; the internal template-epoch
coordinate is kept strictly separate from nonce32.

## 2. The §29 validity check as a modeling commitment

N evaluations of the same numerical nonce under N distinct headers are N
independent Bernoulli(q) trials — same-value ≠ same-opportunity. The engine
realises this exactly: distinct-input rate N·h for ND-PW. For ND-PC, one
common template caps an epoch at its searched set, but disjoint ranges make
every evaluation fresh and the epoch renews in S/(N·h) seconds, so the
distinct-trial rate is also N·h. Nothing in the engine assumes partitioning
preserves block probability (brief §17) — the trial rates emerge from the
traversal geometry, and block retention is measured per paired seed.

## 3. Engine reuse and why it is valid

The three physical arms are byte-identical semantics to three arms of the
frozen Stage 8X-NR engine (zero-start CONV, offset CONV, PC), which carries 61
tests including toy-domain enumeration checks of the interval arithmetic and
exact work/state identities. Stage 8X-ND imports that engine READ-ONLY (the
602-file protected baseline proves the module untouched) and runs it on fresh
ND seeds; the ND suite re-asserts all 21 §36 properties against the wrapper.
This is the same reuse pattern Stage 8Y used with Stage 8X.

ND-PC-NOLP is a derived observation, not a simulation: the ND-PC physical
trajectory with t_low priced at full power (E = P·N·T exactly; test 15
verifies physics are untouched). §33's instruction not to duplicate
trajectories is thereby honoured: 450 physical runs + 150 derived rows,
labelled `run_kind` in every CSV.

## 4. Difficulty

q_N = 1/(N·h·600), D_N = H_N·600/2^32, shared by all arms at each N; PoCol is
never retargeted. q·D·2^32 = 1 asserted.

## 5. Metrics and resets

Nonce-domain metrics (per-miner domain size, C/U/R/ρ_nonce, cross-miner
multiplicity, sweep and renewal counts) at run scope, with epoch-scope
disjointness verified structurally; exact-input duplication carried as a
clearly-labelled secondary column. Energy from state-time with the exact
identity E = 3510·(T_active + α·T_low); service metrics with NA propagation;
paired per-seed ratios against ND-PW.

## 6. Statistics

30 fresh paired seeds (registry disjoint from 8X/8X-NR/8X-E50/8Y/8Z, verified
in test). Common-random-number pairing makes ND-PW and ND-PC block sequences
nearly identical per seed — retention CIs are degenerate at 1.0000, which is
the honest reflection of the trial-rate identity rather than a statistical
artifact; deterministic quantities are reported as magnitudes; the horizon-
truncation bias of conditional mean intervals (532 s vs 600 s nominal) is
noted wherever intervals are pooled.
