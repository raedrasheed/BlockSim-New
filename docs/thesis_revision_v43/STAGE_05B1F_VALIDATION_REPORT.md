# Stage 5B1F — Validation Report

Runner: `experiments/thesis_revision_v43/validate_5b1f.py`
Data: `results/thesis_revision_v43/stage_05b1f/validation_report_5b1f.json`,
`STAGE_05B1F_VALIDATION_RESULTS.json`

**The 1 890-run matrix is NOT executed.** Bounded validation only.

## 1. Coverage (Section 13)

**30 runs** (hard cap 200): scenarios B0, B1, B2, B3/C1, C2; homogeneous and
heterogeneous rates; equal and weighted allocation; propagation delays 0, 0.42, 5,
30, 60 s; one- and multiple-solution templates (μ = 1, 3, 5) including multiple
solutions owned by one miner; B2 overlapping random starts and full-domain
exhaustion; inactive fractions 5/15/30 %; a small-domain regime that produces stales.

| Regime hit | |
|-----------|:--:|
| non-zero legitimate stale blocks | ✅ |
| partial generation at cutoff | ✅ |
| B2 domain exhaustion | ✅ |
| multiple solutions per template | ✅ |
| inactive ranges | ✅ |

## 2. Eight reconciliations — all pass on every run

| Reconciliation | Definition |
|----------------|-----------|
| **Energy** | `total == active + idle + coordination` |
| **Candidates** | `total == distinct + duplicate` (exact integer) |
| **Per-miner-generation** | `Σ per-generation candidates == network total` (disjoint) |
| **Template chronology** | `end ≥ start`; `Σ duration == 10 000 s` |
| **Parent chain** | first parent `genesis`; each block → previous; no self-parent |
| **Block proposals** | `#blocks == accepted_blocks`; every block has a proposer |
| **Stale blocks** | competitors are distinct miners; denominators well-defined |
| **Inactive ranges** | inactive-only generations never block |

`all_reconciliations_pass = true`.

## 3. Corrections confirmed

- Each miner proposes at most one block per generation (its earliest solution).
- Stale competitors are distinct miners with distinct identities within a per-miner
  delay window; B1 same-header ⇒ zero distinct stale.
- B2 exhaustion uses exact union coverage, not `S/Σrates`.
- One candidate-time convention `(d+1)/rate`; no zero-time block.
- Parent provenance correct; partial never labelled exhausted.
- Per-miner-generation records reconcile to network totals; cumulative and
  generation-level progress are separate.
- Integer hash rates sum exactly; candidate counts exact via rational arithmetic.
- Finder counts are miners, not solution positions.

## 4. Full test suite

`python3 -m pytest tests/ -q` → **373 passed** (43 new Stage-5B1F). Thesis DOCX/PDF
byte-identical.
