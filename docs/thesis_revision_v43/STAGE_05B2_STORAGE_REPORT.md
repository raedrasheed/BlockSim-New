# Stage 5B2 — Storage and File-Count Report

Outputs under `results/thesis_revision_v43/stage_05b2/`. Formats: gzip-compressed
JSONL for tables (partitioned), JSON for manifests, CSV for ledgers/indexes. Parquet
is not used (pyarrow is absent from the frozen dependency environment; installing it
would alter the frozen environment). No file uses Excel. Every committed table file is
well under the 90 MB limit (largest **34.7 MB**).

## Push-size limit and §10 fallback

The complete aggregated dataset is ≈ 775 MB. A **single** `git push` of that size was
**rejected by the remote with HTTP 413 (Request Entity Too Large)**; that discarded
attempt never became any branch's history and is not cited as committed anywhere. Per
Section 10 the dataset is **not discarded**. Two complementary durable copies exist:

1. a compact, reliably-pushable **results branch** `thesis-v43-stage5b2-results-1`
   (carried forward to `…-results-2`; ≈ 47 MB, **474 files**) carrying every manifest,
   checksum, the full ledger, all per-run
   summary/per-miner/per-template/block-log/stale-race outputs, and the full detail for
   the 61 retained-full-log runs; and
2. the full bulk data (**per_miner_generation + delivery_delays + run bundles + recovery
   debris**, 2196 files, ≈ 1.59 GB) stored as **42 deterministic ≤40 MB archive chunks**
   on the dedicated remote branch **`thesis-v43-stage5b2-data-1`** — each chunk pushed
   individually to stay under the 413 limit, and the whole set **roundtrip-verified from
   a fresh clone** (all 2196 original files byte-identical; see
   `STAGE_05B2A_BULK_ARCHIVE_MANIFEST.json`).

Both branches survive deletion of the ephemeral execution container.

## Committed aggregated outputs (results branch `thesis-v43-stage5b2-results-1`)

| Kind | Format | Size | Files | Partitioning |
|------|--------|-----:|------:|--------------|
| `summary/` | jsonl.gz | 328 KB | 1 | one line per run (1890) |
| `per_miner/` | jsonl.gz | 19 MB | 5 | by scenario |
| `per_template/` | jsonl.gz | 2.3 MB | 5 | by scenario |
| `block_log/` | jsonl.gz | 828 KB | 5 | by scenario |
| `stale_race/` | jsonl.gz | 560 KB | 5 | by scenario |
| `full_logs/` | per-run json + jsonl.gz | 18 MB | 427 | 61 retained runs incl. their per-miner-generation + delivery detail |
| `manifests/` | json + csv | 3.3 MB | 5 | results manifest (all 1890), bundle manifest (reconciled to all 1890 entries in Stage 5B2A), index, checksums |
| `logs/` | jsonl | 2.0 MB | 1 | append-only execution ledger |
| **Committed total** | | **≈ 47 MB** | **≈ 474** | largest file well under 90 MB |

## Bulk data — archived to the remote bulk-data branch, and retained on disk

Not committed to the *results* branch (would exceed the push limit); instead durably
archived as 42 deterministic chunks on the remote branch `thesis-v43-stage5b2-data-1`
(availability class `AVAILABLE_REMOTE_GIT`) **and** retained on disk. Every file is
checksummed in `STAGE_05B2A_ORIGINAL_BULK_FILE_CHECKSUMS.sha256` (2196 files) and the
chunks in `STAGE_05B2A_ARCHIVE_ASSET_CHECKSUMS.sha256` (42 chunks).

| Data | Size | Availability class | Notes |
|------|-----:|--------------------|-------|
| `per_miner_generation/` (aggregate, all 1890) | 566 MB | `LOCAL_REDUNDANT` (+remote archive) | Bulk diagnostic detail (12 069 400 rows), archive A (63 files → 15 chunks). Full detail for the 61 retained runs IS committed under `full_logs/`; totals reconcile in every committed `summary`. Deterministically regenerable from the frozen commit. |
| `delivery_delays/` (aggregate, all 1890) | 164 MB | `LOCAL_REDUNDANT` (+remote archive) | Bulk per-delivery diagnostic (7 722 695 records), archive B (63 files → 5 chunks). Summarised per accepted height in the committed `stale_race` records (`active_nonwinner_delivery_count`); full detail for the 61 retained runs IS committed under `full_logs/`. |
| `runs/` durable per-run bundles (1890) | 763 MB | `LOCAL_REDUNDANT` (+remote archive) | Durable working set — byte-for-byte redundant with the aggregates, archive C (1890 files → 19 chunks); each bundle's SHA-256 in `manifests/bundle_manifest.json`. |
| `failed_attempts/recovery/attempt-1/` | 98 MB | `HISTORICAL_RECOVERY` (+remote archive) | Superseded corrupt streaming debris (40 unclosed `.tmp`), preserved per the recovery protocol, archive D (180 files → 3 chunks); no scientific value. |

Local copies remain on disk under the execution worktree
`/home/user/blocksim-stage5b2-exec/results/thesis_revision_v43/stage_05b2/`. Free disk
at completion: ~23 GB.

## Integrity

`STAGE_05B2_CHECKSUM_MANIFEST.sha256` lists the SHA-256 of **every output file —
committed and bulk** (580 files) as of aggregation time; its `bundle_manifest.json`
entry was updated when the manifest was reconciled to all 1890 entries in Stage 5B2A.
Stage 5B2A additionally splits the checksums by availability class:
`STAGE_05B2A_REMOTE_GIT_CHECKSUMS.sha256` (committed results-branch files),
`STAGE_05B2A_ARCHIVE_ASSET_CHECKSUMS.sha256` (42 remote archive chunks),
`STAGE_05B2A_LOCAL_REDUNDANT_CHECKSUMS.sha256` (per_miner_generation + delivery_delays +
run bundles), and `STAGE_05B2A_HISTORICAL_RECOVERY_CHECKSUMS.sha256` (recovery debris);
there are no GitHub Release assets (`REMOTE_RELEASE_ASSET` is empty — release/asset
upload is unavailable through the session tooling). `manifests/results_manifest.json`
lists all 1890 runs with identity, bundle SHA-256, and key metrics;
`manifests/bundle_manifest.json` lists every one of the 1890 durable per-run bundle
SHA-256. Every one of the 1890 runs is checksum-verifiable.
