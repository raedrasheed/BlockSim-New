# STAGE 05A — Failure, Retry, and Exclusion Policy (frozen before Stage 5B)

## 1. A run FAILS only for a predefined technical reason
- process error (non-zero exit / exception);
- failed reconciliation (any of A–F below does not hold within tolerance);
- timeout (exceeds the documented per-run cap of **240 s**);
- corrupt or missing output (unreadable workbook / diag / summary);
- failed invariant (e.g. energy not equal to active+idle+coordination).

A run is **never** excluded because its outcome is inconvenient, extreme, or
unexpected.

## 2. Retry
A failed run may be retried with the **same seed, same configuration, same code
commit**, and a documented `retry_number`. At most **2 retries**; a third
failure is recorded as `FAILED` (not dropped silently) and excluded from
statistics with the reason recorded.

## 3. Code changes mid-stage
If code must change during Stage 5A/5B:
1. **stop** the stage;
2. create a **new commit**;
3. **invalidate** all runs produced under the previous commit for the affected
   scenarios;
4. never silently mix outputs from different scientific code versions — every
   summary row records its `code_commit`, and Stage 6 partitions by commit.

## 4. Run ledger (maintained across 5B)
A single ledger tracks: `planned`, `completed`, `failed`, `retried`, `excluded`,
and `exclusion_reason`, keyed by `run_id`. Counts must reconcile:
`planned = completed + failed_unretried + excluded` (with retried runs counted at
their final status).

## 5. Reconciliations that gate acceptance (per run, where applicable)
| id | identity | applies to |
|---|---|---|
| A energy | `total = active + idle + coordination` | all |
| B candidate | `total_evals = distinct + duplicate` | coverage/direct model |
| C nonce domain | `assigned = searched + unsearched + inactive` (± documented partial progress at cutoff) | coverage/full-sim |
| D events | `scheduled = valid + legit_competitors + obsolete_rejected + cancelled + beyond_cutoff` | full event-loop |
| E blocks | `valid_proposals = accepted + legit_stale + other_valid_unresolved` | full event-loop |
| F time | per miner `active + idle + offline = eligible_time` (± join/leave) | all |

Any reconciliation failure → the run FAILS (§1) and is retried (§2).

## 6. Data integrity
- Raw and summary data are **never** manually edited.
- Immutable outputs are `chmod 0444` with a per-run checksum and full provenance
  (config, seed, commit, config hash, timestamps, stdout/stderr).
- Retention follows the approved sampling policy (all failed/pilot/anomalous
  runs + one validation run per scenario×count + a predeclared random 1% sample
  keep full event/energy logs; all others keep a summary row + per-miner
  state-duration + event-classification + template-generation summaries).
