# Stage 5B1A — Stratified Full-Log Retention Policy

Module: `experiments/thesis_revision_v43/retention_5b1a.py`
List: `STAGE_05B1A_RETENTION_LIST.json` (reason codes) ·
`results/thesis_revision_v43/stage_05b1a/raw/retention_manifest.json`
Tests: `test_stage5b1a_storage_retention.py` (24–29)

Replaces the flat "one-per-group + 1%" sample (41 logs) with a **deterministic
stratified** design (**61** matrix full logs) that guarantees coverage of every
scientifically load-bearing stratum. Selection is a pure function of the frozen
matrix rows, so it is reproducible with a stable checksum.

## 1. Strata (each retained run carries reason codes)

1. **All Stage-5B1A validation runs** (recorded in the manifest's
   `validation_retained_run_ids`).
2. Failed / retried / anomalous / reconciliation-failing runs — added
   **automatically during Stage 5B2** (the only permitted post-freeze change).
3. **≥1 run per scenario × miner-count** — `scenario_count_cover`.
4. **≥1 run per sensitivity level**:
   - each propagation-delay level — `delay_level:*`
   - each μ level — `mu_level:*`
   - each inactive-miner level — `inactive_level:*`
   - each idle-power level — `idle_power_level:*`
   - homogeneous / heterogeneous-equal / heterogeneous-weighted / exploratory-high
     — `dist:*`
5. **≥1 run per interesting regime** (selected by *expected* behaviour from config,
   so the list is fixed before execution):
   - `expected_zero_block_b1` (B1 at max N)
   - `expected_high_exhaustion` (min μ)
   - `expected_legitimate_stale` (max propagation delay)
   - `expected_nonzero_idle_c2` (C2 heterogeneous-equal)
   - `expected_zero_idle_c2` (C2 homogeneous-equal)
6. **Deterministic 1% sample** of the remaining rows — `one_percent_sample`.

## 2. Integrity

- Generated **before** Stage 5B2; every retained run has ≥1 reason code.
- Duplicate run ids removed; retained ids unique (test 29).
- Reproducible: two builds give the same set and the same
  `retention_checksum_sha256 = 2283f2ff…1702e` (tests 28–29).
- Preserved **unchanged** during Stage 5B2 except that a failed/anomalous run is
  added automatically (stratum 2).

## 3. Result

| Quantity | Value |
|----------|------:|
| Matrix full logs retained | **61** |
| Retention checksum (SHA-256) | `2283f2ff…1702e` |
| Every scenario × count covered | ✅ (test 24) |
| Every sensitivity level covered | ✅ (test 25) |
| All five regimes covered | ✅ (tests 26–27) |

Full logs are a small subset; per-miner and per-template summaries are retained for
**every** run regardless of full-log retention.
