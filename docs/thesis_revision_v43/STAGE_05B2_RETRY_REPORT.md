# Stage 5B2 — Retry / Attempt Report

Append-only ledger: `results/thesis_revision_v43/stage_05b2/logs/execution_ledger.jsonl`
(CSV: `STAGE_05B2_EXECUTION_LEDGER.csv`). Frozen commit
`45361674e6278971d430a79531f7aaac5cae3281`.

## Attempt history (all preserved, append-only)

| Phase | Outcome |
|-------|---------|
| Streaming executor (attempt 1) | 445 runs `COMPLETED_VALID`, then container restart |
| Recovery reconciliation | 1 `INTERRUPTED` marker + 445 `INVALIDATED` (durable outputs not finalized before restart) |
| Durable executor, run 1 | ~129 runs written durably, then parent `BrokenPipeError` (large-result IPC overflow) |
| Durable executor, run 2 (memory-safe) | resumed 1760 + recovered 130 → all runs durable |

Every attempt retried used the SAME run ID, run-execution hash, master seed, named
stream seeds, frozen commit, dependency environment, output schema, and QC rules. No
seed was replaced; no worker-sensitive scientific behaviour was changed. Failed /
interrupted outputs were preserved (not deleted), not silently dropped.

## Ledger totals

| Metric | Value |
|--------|------:|
| Total ledger rows | 2781 |
| Per-run attempt rows | 2780 |
| `COMPLETED_VALID` attempt rows | 2335 |
| `INVALIDATED` attempt rows (recovery) | 445 |
| `INTERRUPTED` markers | 1 |
| `FAILED_TERMINAL` | 0 |
| Resume/retry attempt rows (attempt > 1) | 445 |
| Distinct run IDs | 1890 |

## Final per-run reconciliation (last status wins)

| State | Count |
|-------|------:|
| `COMPLETED_VALID` (final) | **1890** |
| `FAILED_TERMINAL` | 0 |
| `INVALIDATED` (current) | 0 |
| not started | 0 |

Historical `INTERRUPTED` (1) and `INVALIDATED` (445) attempts remain preserved in the
append-only ledger; they reflect the two infrastructure interruptions, not scientific
defects. No scientific assertion failed at any point (0 QC failures across execution
and the final aggregation revalidation).
