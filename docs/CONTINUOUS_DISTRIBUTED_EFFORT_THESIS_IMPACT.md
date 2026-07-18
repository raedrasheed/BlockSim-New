# Continuous Distributed-Effort Experiment — Thesis Impact

**Branch:** `claude/pocol-continuous-distributed-effort`
**Status:** the thesis document is **not** edited. This note records exactly which
claims the new experiment (Finding 3) supports and which remain unsupported, for a
later, separately reviewed thesis revision.

---

## 1. The three findings the thesis must keep separate

1. **Finding 1** (`results/corrected/`): under continuous full-power mining with
   equal aggregate hardware and distinct work, **PoCol = PoW** (8.4208 kWh).
2. **Finding 2** (`results/nonce_partition_worst_case/`): in a one-shot
   common-template exact-duplicate search, disjoint allocation reduces attempts by
   `1 − 1/N` versus the duplicate baseline, and **ties** independent headers.
3. **Finding 3** (this experiment): with fixed-slot scheduling and miners actually
   powering down after finishing, disjoint allocation reduces **energy** by
   `(1 − q)(1 − 1/N)` versus the duplicate baseline — but is **statistically
   equivalent to independent equal-budget headers (C1)**, and the saving is **zero**
   under immediate restart or `q = 1`.

These are three different questions. No thesis sentence may merge them.

---

## 2. Claims the new experiment SUPPORTS

- "In a common-template duplicate-search worst case, if miners transition to a
  lower-power IDLE/SLEEP state after completing their assigned nonce subrange, the
  idealized energy reduction of disjoint allocation is `(1 − q)(1 − 1/N)`, verified
  by state-integrated wall-clock accounting." *(deterministic formula + tests)*
- "This reduction is driven entirely by reduced ACTIVE time and lower idle power;
  it vanishes when miners keep mining immediately (IMMEDIATE_RESTART) or when
  idle power equals active power (q = 1)." *(control policy + q-sweep)*
- "The saving over the duplicate baseline is large (Cohen's d ≈ −5), but disjoint
  allocation is **energy-equivalent** to independent headers of equal total
  candidate budget (TOST equivalence at a pre-registered 1 % margin)." *(B vs C1)*

## 3. Claims the new experiment does NOT support

- ❌ "PoCol reduces Bitcoin's energy by `(1 − q)(1 − 1/N)` (or `1 − 1/N`)." The
  bound is against a synthetic duplicate baseline; real miners use distinct headers.
- ❌ "Nonce partitioning saves energy." Partitioning alone saves nothing
  (IMMEDIATE_RESTART is neutral); the saving requires powering down.
- ❌ "PoCol is more energy-efficient than ordinary independent-header mining."
  B ≈ C1 (equivalent). PoCol's only benefit is de-duplication + power-down, both
  obtainable by giving miners distinct headers and a fixed-slot idle policy.
- ❌ Any single headline combining Findings 1–3.

---

## 4. Recommended thesis framing

> "We show that a collaborative, fixed-slot protocol in which miners power down
> after completing a disjoint nonce subrange can, in the worst case of otherwise
> fully-duplicated complete-header search, reduce energy by up to `(1 − q)(1 − 1/N)`.
> This saving is a property of **de-duplication plus power-state management**, not
> of nonce partitioning itself: it disappears under continuous operation, and it is
> statistically equivalent to simply assigning miners independent headers of equal
> total budget. Realising it on real hardware would require (a) miners that
> actually enter low-power states and (b) a baseline that genuinely performs
> duplicate complete-header work — which the Bitcoin network does not."

This is honest, still a genuine contribution (a power-state-aware energy model plus
a precise, tested upper bound and its exact preconditions), and fully supported by
the committed code, tests, and data.

---

## 5. Unresolved limitations to disclose (see LIMITATIONS.md)

Security under reduced per-miner work; idle/sleep transition costs; coordination
overhead of range assignment; and the fact that the realistic baseline is C1
(independent headers), not A (duplicate). Idle/sleep power ratios are physical
assumptions swept here (`q ∈ {0…1}`, sleep `∈ {0, 0.01, 0.05}`) precisely because
the result depends on them.

**No thesis file is modified on this branch.**
