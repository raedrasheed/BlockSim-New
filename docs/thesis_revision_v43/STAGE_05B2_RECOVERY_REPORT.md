# Stage 5B2 — Execution Recovery Report

Recovery of the interrupted Stage-5B2 full-matrix execution. Scientific source, matrix,
seeds, freeze inputs, thesis files, and freeze branch 6 were **not** modified. Frozen
commit `45361674e6278971d430a79531f7aaac5cae3281`.

## 1. Why the prior execution stopped

Two interruptions occurred; both were infrastructure events, not scientific defects:

1. **Container restart** during the first (streaming) executor. It had completed 445
   runs (ledger `COMPLETED_VALID`, attempt 1). The streaming executor buffered every
   run's records in partitioned gzip writers that are only atomically closed at the
   very end, so on restart **40 unclosed `.tmp` writers** were left — the 445
   completed runs had **no durable final outputs** (only 20 retained `full_logs`
   per-run bundles, which are closed per run, survived).
2. **Parent-process memory overflow** (`BrokenPipeError`) during the first durable
   re-run: the durable executor returned each run's full result (per-miner-generation
   + delivery records, up to tens of thousands of dicts) through the multiprocessing
   pipe to a single parent writer; the parent's inbound queue overflowed on the N=500
   rows and the parent died (~129 durable bundles were already safely on disk).

No Stage-5B2 process remained alive after either interruption (verified with `ps`).

## 2. Corrective design (operational metadata only — not scientific code)

The executor was made **durable and resumable**, and then **memory-safe**:

- Each run is persisted as ONE atomically-written per-run bundle
  (`runs/<scenario>/<group>/<run_id>.run.json.gz`, written to a per-process temp then
  `os.replace`d) the moment it completes — a restart never loses completed work.
- Workers now write their **own** uniquely-named bundle and return only a small
  payload (identity + QC verdict + summary metrics), so no large per-run data crosses
  the pipe — eliminating the parent overflow. Each worker writes only its own run's
  path, preserving isolation.
- On (re)start the executor revalidates every existing bundle (identity match + QC
  re-pass) and executes only the exact resume set; a recovery checkpoint is written at
  least every 50 newly completed runs (`STAGE_05B2_RECOVERY_CHECKPOINT.json`).

The frozen engine, config mapping, QC rules, seeds, and schema are unchanged; only how
outputs are persisted changed. No worker-sensitive scientific behaviour was altered.

## 3. Original ledger state and reconciliation (append-only)

The append-only ledger was preserved. The interrupted streamed outputs were moved
(not deleted) to `failed_attempts/recovery/attempt-1/`. Recovery records were appended:

| Event | Count |
|-------|------:|
| attempt-1 `COMPLETED_VALID` (superseded — durable outputs lost) | 445 |
| `INTERRUPTED` recovery marker (streaming attempt) | 1 |
| `INVALIDATED` (durable output not finalized before restart) | 445 |

Recovered `COMPLETED_VALID` with durable outputs at resume time: **0**. Resume-set
size: **1890**. Reconcile: recovered (0) + resume (1890) + failed_terminal (0) = 1890.

## 4. Final reconciliation

| Metric | Value |
|--------|------:|
| Planned physical runs | 1890 |
| **Completed valid (final)** | **1890** |
| Failed terminal (current) | 0 |
| Invalidated (current) | 0 |
| Not started | 0 |
| Recovered from durable bundles at resume time | 130 |
| Resumed and executed | 1760 |
| Total append-only ledger rows | 2781 |
| Resume/retry attempt rows (attempt > 1) | 445 |
| Historical interrupted / invalidated (preserved) | 1 / 445 |
| QC failures (execution + final aggregation revalidation) | 0 |

`recovered (130) + resumed (1760) = 1890`; final per-run last-status = 1890
`COMPLETED_VALID`. All 1890 durable bundles revalidated (identity + QC) during the
final aggregation with zero failures. A single run (`S5B2-00129`) executed during an
in-process harness sanity check was reconciled by appending a `COMPLETED_VALID`
ledger row from its revalidated durable bundle.

## 5. Checksums, storage, results branch

- Committed to the results branch: **474 files, ≈ 47 MB** (462 result outputs + 12 stage
  docs), largest committed table 34.7 MB (`STAGE_05B2_STORAGE_REPORT.md`). The earlier
  "≈ 775 MB / 578 files" figure described a single full-aggregate push **attempt** the
  remote rejected with HTTP 413; it never became branch history and is not a committed
  set.
- `STAGE_05B2_CHECKSUM_MANIFEST.sha256`: SHA-256 of **all 580 output files (committed +
  bulk)** as of aggregation time (its `bundle_manifest.json` entry refreshed after the
  5B2A reconciliation to 1890 entries). Stage 5B2A also splits the checksums by
  availability class (`STAGE_05B2A_*_CHECKSUMS.sha256`).
- Bulk data (durable per-run bundles 763 MB, and the corrupt streaming debris 98 MB
  under `failed_attempts/recovery/attempt-1/`) is durably archived as 42 deterministic
  chunks on the remote branch `thesis-v43-stage5b2-data-1` (roundtrip-verified from a
  fresh clone) **and** retained on disk; each bundle is individually checksummed in
  `bundle_manifest.json`.
- Frozen inputs re-verified unchanged; scientific-tree diff vs freeze 6 = 0 tracked
  modifications.
- Results branches: `thesis-v43-stage5b2-results-1` and, for the 5B2A corrections,
  `thesis-v43-stage5b2-results-2` (full commit SHAs recorded on push).

## Conclusion

`STAGE_5B2_EXECUTION_COMPLETE` — set together with the Stage-5B2 execution report on a
green post-execution test gate and a successful results-branch push (freeze branch 6
untouched).
