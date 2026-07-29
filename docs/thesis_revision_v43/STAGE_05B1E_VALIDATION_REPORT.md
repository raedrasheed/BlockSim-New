# Stage 5B1E — Validation Report

Runner: `experiments/thesis_revision_v43/validate_5b1e.py`
Data: `results/thesis_revision_v43/stage_05b1e/validation_report_5b1e.json`,
`STAGE_05B1E_VALIDATION_RESULTS.json`

**The 1 890-run matrix is NOT executed.** This is a bounded validation set.

## 1. Coverage (Section 10)

**54 runs** (hard cap 200) spanning: scenarios B0, B3/C1, C2; N = 10, 100, 500;
homogeneous and heterogeneous miners; equal and weighted allocation; inactive
fractions 0 %, 5 %, 15 %, 30 %; μ ∈ {0.5, 2.0}. Every required regime is exercised:

| Regime | Hit |
|--------|:---:|
| inactive-only generation (no active solution) | ✅ |
| partial final generation | ✅ |
| early winner (block produced) | ✅ |
| non-zero idle opportunity (C2 het-equal) | ✅ |
| zero idle opportunity (C2 homogeneous) | ✅ |

## 2. Six reconciliations — all pass on every run

| Reconciliation | Definition |
|----------------|-----------|
| **Energy** | `total == active + idle + coordination` |
| **Candidate** | `total == distinct + duplicate` (exact integer) |
| **Domain** | per template: `searched + unsearched + inactive == assigned` |
| **Time** | `Σ generation duration == 10 000 s` |
| **Block** | `#blocks == accepted_blocks`; every block has an active finder |
| **Inactive-range** | inactive-only generations never block; `Σ per-miner candidates == total` |

`all_reconciliations_pass = true`, `all_coverage_hit = true`.

## 3. Corrections confirmed

- Inactive-only solutions produce no block (inactive-range reconciliation).
- Heterogeneous equal-range exhaustion uses `max_i τ_i`, not `S/H_active`.
- B3/C1 continuous power (idle = 0, non-productive active reported); C2 idle saves.
- Per-miner cumulative progress reconciles to the network total exactly.
- Candidate counts are exact integers with `total == distinct + duplicate`.
- Template chronology is monotonic and sums to the horizon.
- **B0 independent-template audit** (`STAGE_05B1E_B0_EQUIVALENCE_AUDIT.json`): for
  homogeneous full participation B0 equals B3 in energy, block count, zero duplicates,
  and zero agreement operations; the partitioned abstraction diverges under inactive
  miners, so B0 is run only under homogeneous full participation in the frozen matrix.

## 4. Full test suite

`python3 -m pytest tests/ -q` → **330 passed** (38 new Stage-5B1E). Thesis DOCX/PDF
byte-identical.
