# Nonce-Partitioning Worst-Case Experiment — Scope and Limitations

**Branch:** `claude/pocol-disjoint-nonce-worst-case`

This document states precisely what the disjoint-nonce worst-case experiment does
and does **not** show. Read it before quoting any number from
`results/nonce_partition_worst_case/` in the thesis.

---

## 1. What the experiment measures

It measures, for a **single immutable shared block template**, the difference in

- candidate-header evaluations (attempts),
- worst-case wall-clock completion time,
- energy (via attempt counts and active-miner time),

between two search strategies:

- **A — Common-Template Duplicate-Search Baseline:** `N` miners each scan the
  **whole** finite nonce domain in the **same** order over the **same** header,
  so they redundantly re-evaluate identical candidates.
- **B — PoCol Disjoint-Nonce Allocation:** the same domain is split into `N`
  mutually disjoint sub-ranges so each candidate is evaluated **once**.

In the final-nonce worst case this yields an attempt/energy reduction of
`1 − 1/N` (e.g. 90 % at `N = 10`, 99 % at `N = 100`).

---

## 2. Explicit limitations (must be stated with any result)

1. **The reduction applies to exact duplicate *complete-header* evaluation only.**
   It quantifies the removal of *identical* candidate-header work, nothing else.
2. **Same nonce does not imply the same hash input.** A header hash depends on the
   whole block header, not just the nonce field.
3. **Different Merkle roots, extranonces, timestamps, or transaction sets produce
   different headers.** Two miners testing "nonce 42" on different templates are
   doing *different* work, and partitioning the nonce field saves nothing there.
4. **The baseline is deliberately constructed as a worst case.** It is the
   maximum-redundancy scenario, chosen to make the upper bound `1 − 1/N`
   observable — not a model of how independent miners actually behave.
5. **Results must not be generalized automatically to Bitcoin.** Real miners
   already differentiate their headers (via extranonce/coinbase), so the Bitcoin
   network does not perform the exact-duplicate work this baseline assumes.
6. **PoCol reduces energy only to the extent the baseline actually contains
   measurable duplicate complete-header work.** With no duplicate complete-header
   work, the saving is zero — which is exactly what the reference mode
   `independent_candidate_headers` demonstrates and what Finding 1 (continuous
   mining, distinct work) reports.

---

## 3. Relationship to the corrected continuous-mining result (Finding 1)

The corrected experiment (`results/corrected/`, **unchanged** on this branch)
shows PoCol and PoW consume **equal** aggregate energy under continuous mining
with **distinct** candidate work. That result stands. This experiment does not
contradict it: it isolates a *different* quantity — the energy attributable to
**exact duplicate** complete-header search — which the continuous-mining scenario
does not contain.

- **Finding 1 (continuous mining, distinct work):** PoCol is energy-neutral.
- **Finding 2 (common-template exact-duplicate worst case):** disjoint allocation
  saves up to `1 − 1/N`.

Both are true because they answer different questions. Neither may be used to
support the other.

---

## 4. What may and may not be claimed in the thesis

**May be claimed (supported):**

- "In a bounded synthetic worst case where `N` miners would otherwise redundantly
  search an identical complete candidate header over the same finite nonce
  domain, disjoint nonce allocation reduces candidate evaluations, worst-case
  completion time, and energy by `1 − 1/N`."
- "This is an upper bound on the duplicate-search saving, verified by exact
  attempt counting and dual-method energy accounting."

**May *not* be claimed (unsupported):**

- "PoCol reduces Bitcoin's energy consumption by up to 99 %." (The Bitcoin
  network does not perform the assumed exact-duplicate work.)
- "PoCol saves `1 − 1/N` energy in general / under normal mining." (Only in the
  duplicate-search worst case; under distinct work the saving is zero — Finding 1.)
- Any combination of Finding 1 and Finding 2 into a single headline number.
