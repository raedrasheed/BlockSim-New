# MASTER REVISION PLAN — Thesis Scientific Revision v43

Approval-gated, staged revision of the PoCol PhD thesis
(`docs/Raed-Rasheed-draft-42-00.docx/.pdf`, never modified). One commit per
approved stage; work stops after each stage for explicit approval.

**Central corrective thesis:** the reported ~98–99% energy reduction is produced
by two accounting artifacts — PoW `/100` hash-rate mis-normalization (C-1) and
PoCol `÷N` energy division (C-2) — atop a single-run, unseeded, uncommitted
evidence base (C-3) with a scheduler-induced stale artifact (M-1). See
`INITIAL_SCIENTIFIC_AUDIT.md`. The revision replaces the energy accounting with
a physically correct wall-clock model, fixes the scheduler, runs seeded
ablations (B0–C2), and rewrites every claim to the strength the corrected
evidence supports. Approved framing = **Path A** (idealized common-template
abstraction; distributed agreement is specification + future work).

## Stage ledger

| Stage | Title | Key output | Gate (summary) |
|---|---|---|---|
| 0 | Inspection & master plan | this file + audit + traceability draft + decisions | no files changed; issues classified; plan approved |
| **1** | **Baseline freeze, branch, traceability** | `BASELINE_FREEZE.md`, `THESIS_TO_CODE_TRACEABILITY.csv`, `BASELINE_NUMERICAL_AUDIT.md`, read-only snapshot, lock file | draft-42 byte-identical; branch from recorded base; tests run as-is; headline values traced or UNTRACEABLE; invariant documented; `/100` & `÷N` documented **unmodified** |
| 2 | Energy accounting correction | wall-clock state model + unit types + tests | energy tests pass; 8.4208 kWh invariant within tolerance; energy independent of miner count at fixed aggregate hash rate; no thesis numbers regenerated |
| 3 | Difficulty, round state, scheduler | event `round_id/parent_id/template_id/miner_id/generation_id` + validation + tests | obsolete-event stales eliminated; expected interval validated; residual stales attributable to explicit propagation/protocol |
| 4 | Scientific baselines & ablation design | B0,B1,B2,B3,C1,C2 scenario defs + matrix | baselines isolate distinct effects; accurate terminology; shared params identical except tested variable; matrix approved before execution |
| 5 | Repeated experiments & sensitivity | ≥30 seeds/config; idle {0,5,10,20,30}%; full provenance | all runs complete; raw data immutable; provenance on every run; no thesis values updated |
| 6 | Statistical analysis & claim determination | CI/effect sizes; ablation table; `CLAIM_STATUS_MATRIX.csv` | every claim classified; percentages reproducible with CIs; unsupported claims flagged |
| 7 | Protocol/security/Sybil/reward revision | boundary + security-status tables; red-line Ch4/5 text | implementation boundary explicit; unsupported security inheritance removed; Sybil/reward limits explicit |
| 8 | Thesis scientific rewrite | `Raed-Rasheed-draft-43-stage-08-Redline.docx/pdf` + changelog + justification table | modified text red / unchanged black; numbers traceable; abstracts ↔ Ch7 ↔ RQs consistent; renders correctly |
| 9 | Citation/equation/table/figure audit | audit reports; updated red-line | no orphan citations; equations dimensionally coherent; tables reproduce data; figures legible |
| 10 | Strict examiner audit | `STRICT_EXAMINER_REPORT.md`, `FINAL_ISSUE_REGISTER.csv` | 0 unresolved critical; 0 unresolved major numeric inconsistencies; defensible contribution remains |
| 11 | Final corrections & submission package | `…ScientificRevision-{Redline,Clean}.{docx,pdf}` + reproducibility/provenance | all 18 final gates pass; draft-42 untouched; examiner verdict ≥ "acceptable subject to minor corrections" |

## Files expected to be touched (later stages)
- **Code (modify):** `Models/Node.py`, `Models/PoCol/{Consensus,Node,BlockCommit}.py`, `Models/Bitcoin/Consensus.py`, `Scheduler.py`, `Event.py`, `Statistics.py`, `InputsConfig.py`.
- **Code (new):** `Models/Energy/wallclock_energy.py`, `experiments/thesis_revision_v43/*`, `analysis/thesis_revision_v43/*`, `tests/thesis_revision_v43/*`.
- **Docs/results (new, versioned):** `docs/thesis_revision_v43/*`, `results/thesis_revision_v43/*`, `docs/Raed-Rasheed-draft-43-*`.
- **Never touched:** `docs/Raed-Rasheed-draft-42-00.{docx,pdf}`; the "Extending BlockSim" manuscript and its `experiments/`, `results/data`, `results/figures`, `tests/test_energy_models.py`; the committed Bitcoin/Ethereum workbooks.

## Estimated computational cost
Stage 5 core: 6 scenarios × 5 miner counts × ≥30 seeds ≈ 900 runs, + idle and
other sensitivity dimensions → ~1,500–2,500 runs. **Caveat:** the *current*
PoCol implementation is O(N²–N³) per run (Stage 1 measured Nn=200 ≈ 127 s;
Nn≥300 exceeds minutes) due to per-reception `_init_round` (O(N)) and
propagate-to-all (O(N)) amplified by the stale explosion. Stage 3 must reduce
this cost (event invalidation instead of re-scan) before Stage 5 is feasible at
scale. Post-fix, runs are expected to drop by orders of magnitude and the matrix
becomes a few CPU-hours, embarrassingly parallel.
