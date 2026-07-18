# Hash-Rate-Aware Difficulty — Methodology

**Branch:** `claude/pocol-hashrate-aware-difficulty` · **Package:**
`experiments/hashrate_aware_difficulty/` · **Data:** `results/hashrate_aware_difficulty/`
**Protected (byte-identical):** all five existing result directories, including
`results/fixed_600s_pocol/` (the fixed-slot experiment is kept unchanged as a
separate experiment).

## 1. The critical scientific rule

Difficulty must depend on **aggregate effective hash rate**, never on the miner
count by itself:

```
H_network  = Σ H_i (ACTIVE miners)
W_expected = H_network × T_target          T_target = 600 s
p_success  = 1 / W_expected  =  (target + 1) / 2^256
target     = floor(2^256 / W_expected) − 1     (integer-safe, clamped to [0, 2^256−1])
E[attempts] = W_expected      E[T_block] = W_expected / H_network ≈ 600 s
```

**Never multiply difficulty by N unconditionally.** The phrase "difficulty
increases with the number of miners" is correct **only** under H2, where adding
miners adds hash rate.

## 2. Hash-rate policies (never mixed)

- **H1 — fixed aggregate:** `H_network = 141×10¹² H/s` for every N; `H_i = H/N`.
  Expected work, difficulty, and target are **constant in N** (`D_N/D_ref = 1`).
- **H2 — fixed per-miner:** `H_i = H_miner` ⇒ `H_network(N) = N·H_miner`. To keep
  600 s expected interval: `W(N) = N·H_miner·600`, so `D_N = N·D_1` and
  `target_N ≈ target_1 / N` (integer rounding).

## 3. Difficulty ≠ nonce-domain size

Difficulty is defined by `hash(candidate) ≤ target` — never by resizing the
domain. The finite domain `[0, M_total)` is a search-bookkeeping construct with
`M_total = H_network × domain_time_budget` (default budget `2T`); a domain may
contain zero/one/many valid candidates, `P(no success) = (1−p)^M`, and exhaustion
triggers a **new template at the same difficulty** (§7). Making the domain
bigger/smaller is not allowed to stand in for difficulty changes (tested).

## 4. The double-scaling defect (removed)

The fixed-600s experiment calibrated `M = (H_network/N)·600` under H1 and then
partitioned that M among N miners: per-miner work `H·600/N²` and PoCol discovery
`600/N` seconds **despite fixed aggregate hash rate** — an artificial N² scaling.
Correct H1 rule implemented here:

```
M_total = H_network × domain_time_budget          (NOT (H_network/N) × budget)
M_i     = M_total / N,  H_i = H_network / N  ⇒  T_exhaust,i = M_i/H_i = budget
```

Splitting a fixed-hash-rate network across a domain changes **ownership** of
candidate evaluations, not network speed (mandatory test). Under the corrected
model, discovery time is governed by `p·H_network` alone — no residual `600/N`.

## 5. Difficulty modes

- **D1 CONSTANT:** one fixed target (from the reference hash rate) for all N.
  Under H2, `E[T_N] = E[T_1]/N` — demonstrates un-retargeted dilution.
- **D2 HASHRATE_SCALED (primary):** target recomputed from current `H_network`;
  `E[T] ≈ 600 s` at every N; under H2 `D_N = N·D_1`.
- **D3 DYNAMIC_RETARGET:** starts from a reference target;
  `new_D = old_D × target_timespan / observed_timespan` on a configurable
  accepted-block window (10 test / 100 experiment / 2016 Bitcoin-like), with the
  per-retarget adjustment factor clamped to `[0.25, 4.0]`:
  `adj = clamp(target_timespan/observed_timespan, 0.25, 4.0)`. Retargeting uses
  accepted-block timestamps only, and never fires per-block in primary results.

## 6. Round semantics (average-interval design)

One immutable template per search phase: one target/difficulty for the whole
round, one finite domain, disjoint partition (PoCol), per-miner independent
stopping (idle on own exhaustion), global stop at first valid candidate, **block
committed immediately at discovery**, next template starts immediately. The
600 s is an *expected* interval produced by target and hash rate — never a
buffered wait (that is the separate fixed-slot experiment).

## 7. Template exhaustion

All subranges exhausted ⇒ `template_exhausted += 1`, new immutable template
(new abstract identifier ≙ new extranonce/Merkle/timestamp), **same difficulty**
unless a D3 window boundary was reached, repartition, continue immediately.
Success is never fabricated; difficulty is never lowered "because a domain ran
out".

## 8. Energy and security-work metrics

Wall-clock state integration (ACTIVE/IDLE/SLEEP) identical to the audited model;
`E_i = ΣP_state·t_state`; never `/N`, never per-block. Additional §15 metrics:
`accumulated_work_per_block = difficulty` (expected hashes implied by the
target — from the target, not from waiting time) and
`actual_hashes_per_accepted_block = total_hashes / accepted_blocks`. Idle waiting
is never counted as Proof-of-Work, and equal commit timestamps are never quoted
as equal security.

## 9. Matrix

Analytic difficulty table: N ∈ {1…500} × {H1,H2} × {D1,D2}. Stochastic (fresh
subprocess per run, paired seeds): primary D2 × {H1,H2} × 3 protocols ×
N ∈ {100…500} × 100 seeds; D1 under H2 (N ∈ {1,2,5,10}) × 3 protocols × 100
seeds; D3 (H2, PoCol, N ∈ {10,100}, window 10) × 100 seeds. Controls share
aggregate hash rate, target, expected work, difficulty, duration, efficiency,
and transaction workload. PoCol superiority may only be claimed against
independent-header PoW under equal difficulty and equal accepted-block output.
