# Stage 5B1 — Storage Projection (from actual full-loop output)

Script: `experiments/thesis_revision_v43/storage_projection_5b1.py`
Data: `results/thesis_revision_v43/stage_05b1/storage_projection.json`

Every byte figure below is the size of a file the engine **actually produced** —
no size was assumed or fabricated. Full logs come from the real
`run_scenario(..., emit_log=True)` per-block records.

## 1. Measured per-run sizes

| Probe | Blocks | Summary bytes | Full-log bytes |
|-------|-------:|--------------:|---------------:|
| B3/C1, N=100 | 15 | 1 585 | 7 617 |
| B3/C1, N=500 | 17 | 1 583 | 8 407 |
| C2, N=500 (het-equal, idle 0.1) | 13 | 1 699 | 7 004 |
| B1, N=500 | 1 | 1 564 | 2 063 |

Summary size is ~constant (~1.6 kB) because the summary schema is fixed. Full-log
size scales with accepted-block count (one record per block); block counts are
small (1–17 over 10 000 s), so full logs are single-digit kB.

Cross-check: the 42-run validation set gives summary **median 1 584 B, 95th
percentile 1 699 B** (`validation_report.json`), consistent with the probes.

## 2. Retention policy

- **Every** run keeps its summary JSON (1 890 summaries).
- Full logs retained for one run per (scenario × miner-count) plus a ~1%
  deterministic sample → **41** full logs
  (`retention_sample_sha256 = b894c5e7…801cec`).

## 3. Projected footprint of the frozen 1 890-run matrix

```
expected = 1890 · median_summary + 41 · median_fulllog
         = 1890 · 1585 B + 41 · 7617 B ≈ 3.308 MB
p95      = 1890 · 1699 B + 41 · 8407 B ≈ 3.556 MB
```

| Component | Expected | p95 |
|-----------|---------:|----:|
| 1 890 summaries | 3.00 MB | 3.21 MB |
| 41 full logs | 0.31 MB | 0.34 MB |
| **Total** | **≈ 3.31 MB** | **≈ 3.56 MB** |

## 4. Interpretation

The full Stage-5B2 raw output is **≈ 3–4 MB** — four orders of magnitude below
any storage concern. The Stage-4 fear of an unbounded log explosion is fully
resolved: the finder model produces a small, bounded number of block events per
run, so total storage is trivial even if *all* 1 890 full logs were retained
(≈ 1890 · 8.4 kB ≈ 16 MB worst case).
