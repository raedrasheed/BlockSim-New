# Fixed 600-Second Round Experiment — Thesis Impact

**Branch:** `claude/pocol-fixed-600s-distributed-nonce` (thesis document NOT edited).
This experiment is **Finding 4** in the repository's series; it does not alter
Findings 1–3 (`results/corrected/`, `results/nonce_partition_worst_case/`,
`results/continuous_distributed_effort/`, `results/mainsim_idle_after_range/` —
all byte-identical, git-verified by an automated test).

## The four findings (never combined into one headline)

| | Design | Result |
|---|---|---|
| 1 | Continuous mining, distinct work | PoCol = PoW, 8.4208 kWh — no saving |
| 2 | One-shot duplicate-search worst case | `1−1/N` fewer attempts vs duplicate; ties independent |
| 3 | Slots + power-down (continuous model) | energy `(1−q)(1−1/N)` vs duplicate; ≡ independent (TOST) |
| 4 | **Fixed 600 s rounds, buffered commit (this)** | equal blocks/interval/throughput **enforced**; energy `(1−q)(1−1/N)` vs duplicate; **independent control matches PoCol exactly** |

Finding 4's contribution over Finding 3: block production is held **exactly
equal by construction** (17/17 blocks, 600 s interval, equal throughput), so the
energy comparison can no longer be confounded by throughput differences — and
under that control, the answer is unchanged.

## Claims the thesis MAY make (supported)

- "In a controlled fixed-slot design where every protocol commits exactly one
  block per 600 s, distributing the nonce domain disjointly and idling finished
  miners reduces energy versus a common-template duplicate-search baseline by
  exactly `(1−q)(1−1/N)` (90 % at N=10, q=0 — verified attempt-by-attempt), with
  identical accepted blocks, interval, and throughput."
- "The reduction is a fixed-slot power-management saving enabled by
  de-duplication: an independent-header control with equal candidate budget
  achieves the identical reduction, deterministically and statistically."
- "PoCol discovers blocks far earlier within a round (≤ 600/N s vs up to 600 s),
  which buys idle time, not extra blocks, under the fixed schedule."

## Claims the thesis may NOT make (unsupported)

- ❌ "PoCol reduces Bitcoin's energy by 90–99.8 %." (Duplicate baseline ≠ Bitcoin;
  limitations §20.)
- ❌ "PoCol is more energy-efficient than ordinary (independent-header) PoW."
  The direct paired comparison shows no distinguishable difference.
- ❌ "Disjoint partitioning itself saves energy." At q=1 or without the slot
  wait, the saving is zero (invariants 20, and Finding 3's immediate-restart).
- ❌ Any security-neutrality claim: with miners ACTIVE ~0.1–0.5 % of the time,
  security/incentive analysis is untouched and required separately.

## Recommended thesis wording for the energy chapter

> "Under a fixed 600-second round schedule with buffered commits, disjoint nonce
> allocation plus power-state management attains the idealized bound
> `(1−q)(1−1/N)` against a maximally duplicative common-template baseline while
> holding block production and throughput exactly equal. The same bound is
> attained by independent candidate headers with an equal work budget; the
> mechanism of the saving is therefore duplicate-work elimination combined with
> fixed-slot idling, and the security consequences of the resulting low duty
> cycle remain an open question for future work."
