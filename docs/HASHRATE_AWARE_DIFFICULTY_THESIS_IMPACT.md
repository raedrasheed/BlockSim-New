# Hash-Rate-Aware Difficulty — Thesis Impact

**Branch:** `claude/pocol-hashrate-aware-difficulty` (thesis document NOT edited).
Finding 5 in the series; Findings 1–4 and all five protected result
directories are byte-identical (git-verified by an automated test).

## What this experiment adds

The difficulty question is now answered correctly and testably:

> **How should PoCol difficulty change with the number of miners?**
> It should not change with the *number* of miners at all — it should follow
> **aggregate effective hash rate** (`W = H_network × T`). With fixed total
> hardware (H1), difficulty is constant for every N and 600 s holds. With
> per-miner hardware (H2), difficulty rises as `D_N = N·D_1` — because hash
> rate rose, not because miners were counted. Without retargeting (D1),
> intervals collapse to `600/N`; dynamic retargeting (D3) recovers the correct
> difficulty from accepted-block timestamps.

## Claims the thesis MAY make (supported)

- "PoCol difficulty must be derived from aggregate hash rate
  (`target = ⌊2²⁵⁶/(H·T)⌋−1`); a miner-count multiplier is correct only when
  per-miner hardware is fixed so that `H = N·H_miner`."
- "Under the corrected model, PoCol and independent-header PoW hold the same
  600 s expected interval, commit statistically equal blocks, expend equal
  total energy, and disclose equal accumulated work per block."
- "Full duplicate search forfeits parallelism entirely: its effective network
  rate is a single miner's rate, so under equal targets its expected interval
  is N×600 s — de-duplication (by disjoint ranges *or* distinct headers) is
  what restores parallel block production."
- "The earlier 600/N discovery times were an artifact of double scaling
  (M = (H/N)·600 partitioned again by N) and are removed."

## Claims the thesis may NOT make (unsupported)

- ❌ "Difficulty should be multiplied by N" (unconditionally).
- ❌ "PoCol saves energy in continuous operation" — total energy here is
  identical for all protocols (energy savings require the power-down designs of
  Findings 3–4, with their own caveats).
- ❌ "PoCol outperforms ordinary independent-header PoW" — TOST-equivalent
  energy, indistinguishable blocks/intervals.
- ❌ Any security-equivalence claim from timestamps or throughput.

## Recommended wording

> "We derive PoCol's difficulty from aggregate effective hash rate, exactly as
> in Nakamoto PoW retargeting theory. This yields constant difficulty under
> fixed total hardware, N-fold difficulty under N-fold hardware, and a stable
> 600-second expected interval in both cases — while showing that disjoint
> nonce allocation is one of several equivalent de-duplication mechanisms
> rather than a source of additional energy efficiency."
