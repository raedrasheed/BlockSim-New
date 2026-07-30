# Stage 5B2A — Durable Bulk-Data Archive Report

## 1. Stage name and purpose

**Stage 5B2A — Durable Bulk-Data Archive and Manifest Reconciliation.**

Purpose: place the complete Stage-5B2 bulk simulation output (per-miner-generation
detail, per-delivery propagation records, durable per-run bundles, and superseded
recovery debris) into **durable remote storage that survives deletion of the ephemeral
execution container**, reconcile every documented count to its exact value, split the
checksum records by availability class, and carry the corrected reports and manifests
forward on a results branch — **without** rerunning any simulation, rebuilding any
archive, or altering any scientific code, frozen input, or committed scientific result.

This documentation-closure sub-stage (5B2A.1) adds the single archive report that was
missing from the Stage-5B2A results commit; it changes nothing else.

## 2. Source identifiers

| Artifact | Commit / branch |
|----------|-----------------|
| Freeze-6 (frozen scientific source) | `45361674e6278971d430a79531f7aaac5cae3281` |
| Stage-5B2 results-1 commit | `d2ef6012afc8275c108ef56737a54a156abe5ceb` |
| Stage-5B2A results-2 commit | `9347ec969bd59a3337582571668ae2140c40485b` |
| Bulk-data branch commit (`thesis-v43-stage5b2-data-1`) | `b44975dd0803e3912f6151398a5a93c34eb95082` |

This report is committed on `thesis-v43-stage5b2-results-3`, branched from exactly the
results-2 commit `9347ec969bd59a3337582571668ae2140c40485b`.

## 3. Scientific execution status

| Metric | Value |
|--------|------:|
| Planned physical runs | 1,890 |
| Completed valid | 1,890 |
| Failed terminal | 0 |
| Invalidated (current) | 0 |
| Not started | 0 |

**No simulation was rerun during Stage 5B2A.** The scientific execution completed in
Stage 5B2; Stage 5B2A operated solely on the already-produced outputs (archiving,
checksum splitting, manifest reconciliation, and documentation correction).

## 4. Archive inventory

- Four deterministic archives (deterministic `tar`: `--sort=name`,
  `--mtime='UTC 2020-01-01'`, `--owner=0 --group=0 --numeric-owner`), each split into
  ≤ 40 MiB chunks.
- Total chunks: **42**.
- Maximum chunk size: **41,943,040 bytes** (40 MiB); the final chunk of each archive is
  smaller.
- Original files archived: **2,196**.
- Original total bytes: **1,664,030,720**.

| Archive | Original directory | Original files | Chunks |
|---------|--------------------|---------------:|-------:|
| A — per-miner-generation | `per_miner_generation/` | 63 | **15** |
| B — delivery-delays | `delivery_delays/` | 63 | **5** |
| C — run-bundles | `runs/` | 1,890 | **19** |
| D — recovery-records | `failed_attempts/recovery/attempt-1/` | 180 | **3** |
| **Total** | | **2,196** | **42** |

## 5. Remote storage

- Branch: **`thesis-v43-stage5b2-data-1`**.
- Commit: **`b44975dd0803e3912f6151398a5a93c34eb95082`**.
- Availability: **`AVAILABLE_REMOTE_GIT`**.
- The 42 chunks are committed under
  `results/thesis_revision_v43/stage_05b2/bulk_archives/` and pushed **one chunk per
  commit** so that no single push exceeds the remote's HTTP-413 request-size limit.
- **GitHub Release assets were unavailable through the session tooling**; the approved
  incremental-branch fallback (Section 10 of the Stage-5B2A plan) was used instead. The
  bulk data therefore resides on a dedicated durable remote git branch, which survives
  deletion of the ephemeral execution container.

## 6. Roundtrip verification

Performed from a **fresh, clean, single-branch clone** of the bulk-data branch into an
isolated directory (i.e. exercising the real remote, not the local working copy):

| Check | Result |
|-------|--------|
| Chunks matched (name, byte size, SHA-256) | **42 / 42** |
| Archives reconstructed (`cat …part-* \| tar -xf -`) | **4 / 4** |
| Original files verified against their SHA-256 | **2,196** |
| Missing files | **0** |
| SHA-256 mismatches | **0** |
| Extra files | **0** |
| Verdict | **`ROUNDTRIP_OK`** |

Every one of the 2,196 original bulk files was reconstructed byte-identical from the
remote chunks.

## 7. Manifest reconciliation

`results/thesis_revision_v43/stage_05b2/manifests/bundle_manifest.json` was regenerated
directly from all 1,890 on-disk durable bundles:

| Quantity | Value |
|----------|------:|
| Bundle-manifest entries (final) | **1,890** |
| Previous entries | 1,761 |
| Entries added | **129** |
| Prior entries changed | **0** |
| SHA-256 mismatches against `results_manifest.json` | **0** |

Every recomputed bundle SHA-256 equals the value already recorded in
`results_manifest.json`; the 1,761 pre-existing entries were preserved unchanged, and
only the 129 missing entries were added.

## 8. Exact ledger reconciliation

From `docs/thesis_revision_v43/STAGE_05B2_EXECUTION_LEDGER.csv`:

| Quantity | Value |
|----------|------:|
| Ledger data rows | **2,781** |
| — per-run attempt rows | 2,780 |
| — recovery markers | 1 |
| CSV lines including header | **2,782** |
| `COMPLETED_VALID` attempt rows | 2,335 |
| `INVALIDATED` historical rows | 445 |
| `INTERRUPTED` markers | 1 |
| Final distinct valid runs | **1,890** |

The single recovery marker is the `INTERRUPTED` row; the 2,780 per-run attempt rows plus
that 1 recovery marker give 2,781 ledger data rows (2,782 CSV lines including the
header). The final per-run last-status is 1,890 `COMPLETED_VALID`.

## 9. Remote Git / result-count reconciliation

| Quantity | Value |
|----------|------:|
| results-1 committed result-output files (`results/…/stage_05b2/`) | **462** |
| results-1 Stage-5B2 documentation files (`docs/…/STAGE_05B2*`) | **12** |
| Total results-1 committed files | **474** |
| Approximate results-1 committed size | **≈ 47 MB** |

The earlier "≈ 775 MB / 578 files" figure described a single full-aggregate push
**attempt** that the remote rejected with HTTP 413; **that attempt never became any
branch's history** and is not the committed result set. The authoritative committed set
is 474 files (≈ 47 MB).

## 10. Availability classes

| Class | Meaning | Count | Manifest |
|-------|---------|------:|----------|
| `REMOTE_GIT` (results files) | Committed on the pushed results branch | 1,836 | `STAGE_05B2A_REMOTE_GIT_CHECKSUMS.sha256` |
| `REMOTE_GIT` (archive chunks) | Chunks on the pushed bulk-data branch | 42 | `STAGE_05B2A_ARCHIVE_ASSET_CHECKSUMS.sha256` (+ `STAGE_05B2A_REMOTE_ASSET_INDEX.csv`) |
| `LOCAL_REDUNDANT` (originals) | On disk; byte-reconstructable from a remote archive | 2,016 | `STAGE_05B2A_LOCAL_REDUNDANT_CHECKSUMS.sha256` |
| `HISTORICAL_RECOVERY` | Superseded interrupted/corrupt debris, preserved | 180 | `STAGE_05B2A_HISTORICAL_RECOVERY_CHECKSUMS.sha256` |
| `REMOTE_RELEASE_ASSET` | GitHub Release asset | **0** | none (release/asset upload unavailable) |

`LOCAL_REDUNDANT` (2,016) + `HISTORICAL_RECOVERY` (180) = the 2,196 original bulk files
in `STAGE_05B2A_ORIGINAL_BULK_FILE_CHECKSUMS.sha256`.

## 11. Scientific immutability

- The 1,890 result **identities and key metrics** remain byte-identical to results-1
  (`manifests/results_manifest.json` is byte-identical to `d2ef6012`).
- `summary/`, `per_miner/`, `per_template/`, `block_log/`, `stale_race/`, and
  `full_logs/` remain **byte-identical to results-1** (git diff vs `d2ef6012` = empty
  for every scientific-data directory).
- The thesis documents remain byte-identical:
  - `docs/Raed-Rasheed-draft-42-00.docx` —
    `2c3afdc5739109d0ea12ada96c3115d626a2188c1acbaeaa4b6020974884cbda`
  - `docs/Raed-Rasheed-draft-42-00.pdf` —
    `131412bb2ce17ed97b98dfbefc136c7b5b226b9fd7372e79a25e4b0dc057e9c4`
- The scientific engine, frozen matrix, seed schedule, dependency lock, and
  preregistration remain unchanged (freeze-6 `45361674…` untouched).

## 12. Exact Git delta from results-1 to results-2

The delta from `d2ef6012` (results-1) to `9347ec9` (results-2) is exactly:

- **10 files added**
- **7 files modified**
- **0 files deleted**

The 10 additions are the eight `STAGE_05B2A_*` manifests/indexes/reports plus the two
provenance scripts (`reconcile_bundle_manifest.py`, `roundtrip_verify.py`); the 7
modifications are the four corrected reports/manifests
(`STAGE_05B2_EXECUTION_REPORT.md`, `STAGE_05B2_STORAGE_REPORT.md`,
`STAGE_05B2_RECOVERY_REPORT.md`, `STAGE_05B2_RESULTS_MANIFEST.json`), the two
monolithic-checksum-manifest copies, and the reconciled `bundle_manifest.json`.

---

STAGE_5B2_ARCHIVE_COMPLETE_AND_READY_FOR_STAGE_6
