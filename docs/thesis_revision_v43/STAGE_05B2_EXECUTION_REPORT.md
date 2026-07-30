# Stage 5B2 — Full Matrix Execution Report

Execution of the frozen 1 890-run matrix from freeze branch
`thesis-v43-stage5b2-freeze-6` at commit
`45361674e6278971d430a79531f7aaac5cae3281`. Scientific code, matrix, seeds, dependency
lock, preregistration, thesis DOCX/PDF, and freeze branch 6 were **not** modified. The
execution survived two container/infrastructure interruptions and was completed via a
durable, resumable executor (see `STAGE_05B2_RECOVERY_REPORT.md`).

## 1. Pre-execution gates (all PASS)

- **Checkout:** detached worktree pinned to `45361674…`, tree `52c79e00…`, parent
  `e7f046b…`, clean.
- **Checksums:** matrix `9cb7297e…`, seed schedule `6122dbd0…`, retention `2283f2ff…`,
  dependency lock `6e211ea7…`, thesis DOCX `2c3afdc5…`, thesis PDF `131412bb…` — all
  match. Engine `5b1g.2`, output schema `5b1g.2`.
- **Structure:** 1890 rows · 63 scientific-semantics groups × 30 seeds · 1890 unique
  run-execution hashes · 0 same-seed duplicates · 870 B3;C1 shared rows.
- **Pre-execution test suite:** **444 passed, 0 failed, 0 skipped** (24 m 16 s).
- **Preflight:** 14 frozen run IDs across all regimes → 14/14 `COMPLETED_VALID`, all
  QC families A–J pass; no scientific/matrix defect exposed.

Environment: Python 3.11.15, Linux 6.18.5, 4 cores, 15.7 GB RAM; numpy 2.4.6, scipy
1.17.1, mpmath 1.4.1 (`STAGE_05B2_ENVIRONMENT.json`).

## 2. Execution model

One physical run per unique run-execution hash (B3 and C1 share a single execution).
Each matrix row → frozen `EngineConfig` (allocation label `disjoint_equal`/
`disjoint_weighted` mapped to the engine's `equal`/`weighted`); the frozen engine
derives all named random streams from the master seed. Isolated worker processes
compute + QC each run and write their own atomically-renamed durable bundle; the
executor is resumable and checkpoints every 50 runs. No exploratory rows added; no
zero-block, failed, or extreme rows removed; no seed replaced.

## 3. Per-run QC (families A–J) — 0 failures

Every run passed all applicable checks (identity; energy sum + continuous anchor;
integer candidate reconciliation `total == distinct + duplicate` and `Σ
per-miner-generation == total`; B2 exact circular start / modulo last-position /
exhaustion proof; disjoint zero-duplicate + domain reconciliation; template chronology
and parent provenance; solution/finder taxonomy; single-height stale-race diagnostic
incl. one delivery per active non-winner; NA policy; numerical validity). The final
aggregation re-ran QC on all 1890 bundles: **0 QC failures**.

## 4. Group-level cross-checks (§12) — all PASS

63 groups × 30 seeds; 1890 unique run-execution hashes; no same-seed scientific
duplicate; B3/C1 share one physical dataset (870 dual-label runs); **delay-only groups
have identical primary outcomes** (energy, candidates, accepted blocks, block interval,
active/idle times) across delay levels — only the single-height stale diagnostic and
delivery records vary with delay; the continuous full-participation energy anchor
(`8.420833333 kWh`) holds for every non-C2, full-participation run; all 142 zero-block
runs retained; no run removed.

## 5. Completion audit (§14)

| Metric | Value |
|--------|------:|
| Planned physical runs | 1890 |
| **Completed valid** | **1890** |
| Failed terminal | 0 |
| Invalidated (current) | 0 |
| Not started | 0 |
| Total attempts (append-only ledger) | 2780 |
| Retry/resume attempts (attempt > 1) | 445 |
| Historical interrupted / invalidated | 1 / 445 |
| Scenario runs (B0/B1/B2/B3;C1/C2) | 150 / 150 / 150 / 870 / 570 |
| Zero-block runs | 142 |
| Partial-final-generation runs | 1890 |
| per-miner-generation rows | 12 069 400 |
| stale-race records | 26 200 |
| delivery-delay records | 7 722 695 |
| Durable execution wall-clock | ≈ 582 s (final memory-safe pass) + recovery |
| Committed output size / files | ≈ 775 MB / ≈ 578 |
| Locally-retained (bundles + recovery) | 763 MB + 98 MB |

## 6. Post-execution gates

- **Post-execution frozen test suite:** **444 passed, 0 failed, 0 skipped** (18 m 40 s,
  start 07:28:16Z → 07:46:57Z), run from the same scientific source checkout.
- **Stage-5B2 data-integrity tests:** 10 passed.
- **Scientific-tree comparison vs freeze 6:** 0 tracked modifications; every new path
  is a Stage-5B2 result / report / ledger / checksum / harness / integrity test. Frozen
  engine, prior tests, matrix, dependency lock, thesis DOCX/PDF unchanged.

## 7. Conclusion

All 1890 runs are `COMPLETED_VALID`; every per-run QC check, group-level cross-check,
data-integrity test, and pre-/post-execution frozen test gate passed; the scientific
source and thesis files are unchanged; freeze branch 6 is untouched. The complete
results manifest (all 1890 runs), per-run bundle manifest, append-only execution
ledger, and a checksum manifest covering **every** output file were committed to the
results-only branch `thesis-v43-stage5b2-results-1` (based on `45361674…`) and pushed.

Per Section 10, the two bulk diagnostic aggregates (`per_miner_generation`,
`delivery_delays`; ≈ 730 MB) exceeded the remote push limit (HTTP 413) and are
**retained locally with complete checksums and an index**, not discarded; their full
detail for the 61 retained-full-log runs IS committed under `full_logs/`, their totals
reconcile in every committed `summary`, and they are deterministically regenerable from
the frozen commit (`STAGE_05B2_STORAGE_REPORT.md`).

**STAGE_5B2_EXECUTION_COMPLETE.** Stage 6 is not begun.
