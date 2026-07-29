# Stage 5B1A — Storage Projection (expanded artifacts, measured)

Module: `experiments/thesis_revision_v43/storage_projection_5b1a.py`
Data: `results/thesis_revision_v43/stage_05b1a/storage_projection_5b1a.json`

Re-estimated from the **full** per-run artifact set — run summary, per-miner
summary, per-template summary, manifest, stdout log, and retained full block-log —
measured across the nine required configurations at N=100 and N=500 (18 probes,
part of the 88 validation runs). Every byte is the size of a file the engine
actually produced; both uncompressed and gzip sizes are recorded.

## 1. Measured artifact sizes (median over probes)

| Artifact | Median bytes | Note |
|----------|-------------:|------|
| run summary | 2 522 | fixed schema |
| **per-miner summary** | **323 392** | one row per miner (dominant at N=500) |
| per-template summary | 12 029 | one row per template generation |
| manifest | 129 | tiny |
| stdout log | 76 | tiny |
| full block-log | 5 175 | one record per accepted block |

Per-run total (summary + per-miner + per-template + manifest + stdout), median
**≈ 327 kB**, 95th percentile **≈ 403 kB**. The per-miner summary dominates because
it preserves every miner (Section 6 requires per-miner data for **every** run, not
just retained full logs).

## 2. Projected footprint of the frozen 1 890-run matrix

Retention policy: every run keeps summary + per-miner + per-template + manifest +
stdout; the **61** retained runs additionally keep the full block-log.

| Quantity | Uncompressed | gzip |
|----------|-------------:|-----:|
| Projected final (expected) | **≈ 617.8 MB** | **≈ 20.0 MB** |
| Projected final (95th pct) | ≈ 761.1 MB | — |
| Projected temporary (all full-logs co-resident) | ≈ 627.3 MB | — |

By artifact type the final footprint is ~98% per-miner summaries. **The prior
summary-only 3.3 MB projection is discarded** — it did not include per-miner /
per-template artifacts and understated storage by ~200×.

## 3. Recommendation

- **Store compressed.** gzip reduces the footprint from ~618 MB to ~20 MB (per-miner
  rows are highly repetitive). Compression should be the default at rest.
- Per-miner summaries are the cost driver; if storage is constrained, a columnar/
  parquet encoding of per-miner data would shrink it further, but even uncompressed
  ~618 MB is well within a normal workstation budget.
- No change to the scientific requirement: per-miner and per-template summaries are
  preserved for **all** 1 890 runs.
