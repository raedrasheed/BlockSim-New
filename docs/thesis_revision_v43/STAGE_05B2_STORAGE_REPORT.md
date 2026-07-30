# Stage 5B2 — Storage and File-Count Report

Outputs under `results/thesis_revision_v43/stage_05b2/`. Formats: gzip-compressed
JSONL for tables (partitioned), JSON for manifests, CSV for ledgers/indexes. Parquet
is not used (pyarrow is absent from the frozen dependency environment; installing it
would alter the frozen environment). No file uses Excel. Every committed table file is
well under the 90 MB limit (largest **34.7 MB**).

## Push-size limit and §10 fallback

The complete aggregated dataset is ≈ 775 MB. A single `git push` of that size was
**rejected by the remote with HTTP 413 (Request Entity Too Large)**. Per Section 10,
the dataset is **not discarded**: the two bulk kinds are **retained locally with
complete checksums and an index**, and a compact, reliably-pushable results branch
(≈ 47 MB) carrying every manifest, checksum, the full ledger, all per-run
summary/per-miner/per-template/block-log/stale-race outputs, and the full detail for
the 61 retained-full-log runs, is committed and pushed.

## Committed aggregated outputs (results branch `thesis-v43-stage5b2-results-1`)

| Kind | Format | Size | Files | Partitioning |
|------|--------|-----:|------:|--------------|
| `summary/` | jsonl.gz | 328 KB | 1 | one line per run (1890) |
| `per_miner/` | jsonl.gz | 19 MB | 5 | by scenario |
| `per_template/` | jsonl.gz | 2.3 MB | 5 | by scenario |
| `block_log/` | jsonl.gz | 828 KB | 5 | by scenario |
| `stale_race/` | jsonl.gz | 560 KB | 5 | by scenario |
| `full_logs/` | per-run json + jsonl.gz | 18 MB | 427 | 61 retained runs incl. their per-miner-generation + delivery detail |
| `manifests/` | json + csv | 3.3 MB | 5 | results manifest (all 1890), bundle manifest, index, checksums |
| `logs/` | jsonl | 2.0 MB | 1 | append-only execution ledger |
| **Committed total** | | **≈ 47 MB** | **≈ 474** | largest file well under 90 MB |

## Locally-retained, NOT committed (preserved on disk, fully checksummed)

| Data | Size | Reason |
|------|-----:|--------|
| `per_miner_generation/` (aggregate, all 1890) | 566 MB | Bulk diagnostic detail (12 069 400 rows). Exceeds the remote push limit; retained locally, checksummed in `STAGE_05B2_CHECKSUM_MANIFEST.sha256`. Full detail for the 61 retained runs IS committed under `full_logs/`; totals reconcile in every committed `summary`. Deterministically regenerable from the frozen commit. |
| `delivery_delays/` (aggregate, all 1890) | 164 MB | Bulk per-delivery diagnostic (7 722 695 records). Summarised per accepted height in the committed `stale_race` records (`active_nonwinner_delivery_count`); full detail for the 61 retained runs IS committed under `full_logs/`. Retained locally, checksummed. |
| `runs/` durable per-run bundles (1890) | 763 MB | Durable working set — byte-for-byte redundant with the aggregates; each bundle's SHA-256 in `manifests/bundle_manifest.json`. |
| `failed_attempts/recovery/attempt-1/` | 98 MB | Superseded corrupt streaming debris (40 unclosed `.tmp`), preserved per the recovery protocol; no scientific value. |

All retained on disk under the execution worktree
`/home/user/blocksim-stage5b2-exec/results/thesis_revision_v43/stage_05b2/`. Free disk
at completion: ~27 GB.

## Integrity

`STAGE_05B2_CHECKSUM_MANIFEST.sha256` lists the SHA-256 of **every output file —
committed and locally-retained** (580 files), so the locally-retained bulk aggregates
are fully verifiable. `manifests/results_manifest.json` lists all 1890 runs with
identity, bundle SHA-256, and key metrics; `manifests/bundle_manifest.json` lists
every durable per-run bundle SHA-256. Every one of the 1890 runs is checksum-verifiable.
