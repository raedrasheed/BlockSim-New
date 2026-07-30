# Stage 5B2A — Manifest and Count Reconciliation

Exact, git-derived counts that supersede the approximate/contradictory figures in the
initial Stage-5B2 reports. Source results commit
`d2ef6012afc8275c108ef56737a54a156abe5ceb`; freeze-6
`45361674e6278971d430a79531f7aaac5cae3281`.

## 1. Execution ledger (exact)

| Quantity | Exact value |
|----------|------------:|
| Ledger data rows (non-empty JSONL lines) | **2781** |
| — of which per-run attempt rows | 2780 |
| — of which `RECOVERY` markers | 1 |
| Execution-ledger CSV lines (incl. header) | **2782** |
| `COMPLETED_VALID` attempt rows (all attempts) | 2335 |
| `INVALIDATED` attempt rows | 445 |
| `INTERRUPTED` markers | 1 |
| `FAILED_TERMINAL` | 0 |
| Final distinct run states | 1890 `COMPLETED_VALID` |

The earlier prose figure "2780 total attempt rows" was imprecise: 2780 is the per-run
attempt-row count; the ledger has **2781** data rows (2780 + 1 recovery marker) and the
CSV has **2782** lines including the header.

## 2. File-location reconciliation (exact, git-derived)

The earlier reports conflated the *attempted* full-aggregate commit (discarded,
never on any branch) with the *actual* compact commit. The exact facts:

| Category | Files | Size | Availability |
|----------|------:|-----:|--------------|
| Committed to Git — results-1/results-2 (`results/…/stage_05b2/` outputs) | 462 | 43.8 MB | `REMOTE_GIT` |
| Committed to Git — Stage-5B2/5B2A docs (`docs/…/STAGE_05B2*`) | 12 (+7 new in 5B2A) | ~3 MB | `REMOTE_GIT` |
| **Total committed to results-1** | **474** | **≈ 47 MB** | `REMOTE_GIT` |
| Bulk aggregates archived to bulk-data branch (`per_miner_generation` 63 + `delivery_delays` 63 files → 20 chunks) | 126 files → 20 chunks | 730 MB | `REMOTE_GIT` (bulk-data branch) |
| Run bundles archived (`runs/` 1890 files → 19 chunks) | 1890 → 19 chunks | 763 MB | `REMOTE_GIT` (bulk-data branch); originals `LOCAL_REDUNDANT` |
| Recovery debris archived (`recovery/attempt-1` 180 files → 3 chunks) | 180 → 3 chunks | 98 MB | `HISTORICAL_RECOVERY` |
| Full output checksum manifest entries | 580 | — | covers committed + locally-retained |
| Original bulk files (all four collections) | 2196 | 1.59 GB | see archive manifest |

The discarded full-aggregate commit attempt (≈ 775 MB, 578 output files) was rejected
by the remote with HTTP 413 and **never** became any branch's history; do not cite it
as "committed". The authoritative committed result set is the 474-file, ≈ 47 MB
results-1 commit, now carried forward to results-2 with the corrected docs.

## 3. Availability classification

Every path carries exactly one availability class, and each class has its own dedicated
checksum manifest (with the per-chunk asset index tying the remote archive together):

| Class | Count | Meaning | Manifest |
|-------|------:|---------|----------|
| `REMOTE_GIT` (results files) | see manifest | Committed on the pushed results branch `thesis-v43-stage5b2-results-2` | `STAGE_05B2A_REMOTE_GIT_CHECKSUMS.sha256` |
| `REMOTE_GIT` (archive chunks) | 42 | Archive chunks on the pushed bulk-data branch `thesis-v43-stage5b2-data-1` | `STAGE_05B2A_ARCHIVE_ASSET_CHECKSUMS.sha256` (+ `STAGE_05B2A_REMOTE_ASSET_INDEX.csv`) |
| `REMOTE_RELEASE_ASSET` | 0 | GitHub Release asset | **none** — release creation/asset upload is not available through the session's GitHub tooling; the bulk archive is stored on a dedicated remote git branch instead (§5 fallback) |
| `LOCAL_REDUNDANT` | 2016 | Retained on disk; byte-reconstructable from a remote archive chunk-set (`per_miner_generation` 63 + `delivery_delays` 63 + `runs` 1890) | `STAGE_05B2A_LOCAL_REDUNDANT_CHECKSUMS.sha256` |
| `HISTORICAL_RECOVERY` | 180 | Superseded interrupted/corrupt debris preserved per the recovery protocol (`failed_attempts/recovery/attempt-1`) | `STAGE_05B2A_HISTORICAL_RECOVERY_CHECKSUMS.sha256` |

`LOCAL_REDUNDANT` (2016) + `HISTORICAL_RECOVERY` (180) = the 2196 original bulk files in
`STAGE_05B2A_ORIGINAL_BULK_FILE_CHECKSUMS.sha256` (the reconstruction-verification
reference). The split manifests are disjoint in purpose: committed results-branch files,
remote archive chunks, locally-redundant bulk originals, and historical recovery debris.

## 4. Corrections applied

- `STAGE_05B2_EXECUTION_REPORT.md`, `STAGE_05B2_STORAGE_REPORT.md`,
  `STAGE_05B2_RECOVERY_REPORT.md`, `STAGE_05B2_RESULTS_MANIFEST.json` are updated so no
  report states that locally-only files are committed to Git, and so every count is the
  exact value above (474 committed / 2781 ledger rows / 2782 CSV lines / 1890 valid).
- Remote Git files and remote archive chunks are counted separately.
- The bulk scientific data now resides on a durable remote git branch, surviving
  deletion of the ephemeral container.
