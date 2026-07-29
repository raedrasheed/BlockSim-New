# Stage 5B1E — Range Lifecycle and Exhaustion Timing

Tests: `test_stage5b1e_lifecycle.py` (8–13)

## 1. Fixed disjoint-range exhaustion time (Section 2)

The old `D_ex = S / H_active` is only valid when work transfers perfectly between
miners. For **fixed** disjoint ranges it does not. With `τ_i = S_i / H_i`, a
non-reallocated generation's active domain is exhausted only when the **slowest**
active range completes:

```
D_ex = max_i τ_i   over active miners
```

- **Equal ranges + heterogeneous rates:** exhaustion is set by the slowest range.
  Validated (het-equal, μ=0.5, N=20): exhausted-generation duration = `max τ_i ≈
  950 s`, **not** `S / H_active ≈ 300 s` (tests 8, 9).
- **Weighted ranges:** reduce `τ_i` dispersion (test 10) — `std(τ_weighted) <
  std(τ_equal)`.
- Inactive ranges are **not** waited for and remain explicitly unsearched.
- Partial final generations record actual per-miner progress at the cutoff.
- No silent perfect work-transfer is assumed; any reallocation policy would be
  documented separately (none is implemented — see B3/C1 below).

## 2. B3/C1 continuous vs C2 idle — one explicit lifecycle difference (Section 3)

When a miner completes its disjoint range before the generation ends, the two
scenarios differ **only** in its power state, never in accounting:

| | Productive search after range done | Power state during the wait | Extra candidates |
|--|--|--|--|
| **B3/C1 (continuous)** | none | **active power** (continuous draw) | none |
| **C2 (idle)** | none | **idle power** | none |

- **B3/C1** keeps miners at active power for the full generation
  (`active_time = generation duration`), so total energy = `P_active · T` (invariant
  A1). The non-productive portion is reported explicitly as
  `non_productive_active_time_s` — the engine does **not** count it as continuing
  distinct search (no extra evaluations; disjoint duplicate = 0). Test 11.
- **C2** drops finished miners to idle power (`active_time = productive time`,
  `idle_time = remainder`); an idle miner performs **no** further candidate
  evaluations (test 12). Homogeneous equal-range C2 idles zero (all `τ_i` equal);
  heterogeneous equal-range C2 saves energy.

Thus B3/C1 and C2 differ through a clearly implemented state/lifecycle policy, not
through inconsistent accounting.

## 3. Partial generation at cutoff

A generation whose end time exceeds the remaining horizon is `PARTIAL_AT_CUTOFF`:
per-miner progress is recorded up to the cutoff, no block is accepted, and
`partial_cutoff_time_s` is set (test 13).
