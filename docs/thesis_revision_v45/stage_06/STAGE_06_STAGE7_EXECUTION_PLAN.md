# Stage 6 — Stage-7 Execution Plan (PREPARED, NOT EXECUTED)

**Stage 7 has not begun.** No confirmatory seed has been executed. No Stage-7 data directory
contains any confirmatory output. This document is the frozen plan Stage 7 will follow.

---

## 1. Identity

| item | value |
|---|---|
| engine commit SHA | `fb8a34d63d9369336d5c1e7aeecdfcf8263920b2` |
| experiment commit SHA | the Stage-6 commit on `thesis-v45-pocol-stage6-pilot-preregistration` (recorded in `STAGE_06_COMPLETION_REPORT.md`) |
| result schema version | `stage5c.1` |
| confirmatory scenarios | **22** |
| confirmatory master seeds | **30** |
| **total expected physical runs** | **660** |
| exploratory scenarios (separate matrix, not confirmatory) | 4 |

The run registry enumerating all 660 runs — with `run_id`, `pair_id`, master seed, seed index,
control/treatment arm, both child seeds and the per-scenario `config_sha256` — is
`experiments/thesis_revision_v45/stage_06/confirmatory/confirmatory_run_registry.csv`.

---

## 2. Execution order and chunking

**Deterministic job ordering.** Sort by `(block_id, scenario_id, seed_index)`. This is the order
in which the run registry is written, so the registry row order *is* the execution order.

| item | value |
|---|---|
| execution chunk size | **30 runs** — one scenario × all 30 master seeds |
| number of chunks | **22** |
| worker-count recommendation | **8 concurrent workers** (see §3) |
| per-run timeout | **90 minutes** |
| retry policy | at most **1** retry, and only for `INFRASTRUCTURE_FAILURE` (rule R09); the retry uses the identical master seed and configuration, and both attempts are archived (R10, R11) |

Chunking by scenario keeps a paired contrast's two arms in different chunks but under identical
seeds, so pairing is by `pair_id`, never by execution adjacency.

---

## 3. Runtime and resources

Grounded in the Tier-2 measurements in `STAGE_06_RUNTIME_AND_ARCHIVE_PLAN.md`. Stage 7 must
re-check these against its own first chunk before committing to the full sweep.

Runs are independent processes sharing nothing, so parallelism is limited by memory and cores,
not by contention. The worker count is set from measured peak RSS per run against available RAM,
with a safety factor of 2.

---

## 4. Directories

| purpose | path |
|---|---|
| frozen configurations (Stage 6, committed) | `experiments/thesis_revision_v45/stage_06/confirmatory/frozen_configs/` |
| run registry (Stage 6, committed) | `experiments/thesis_revision_v45/stage_06/confirmatory/confirmatory_run_registry.csv` |
| raw output (Stage 7) | `experiments/thesis_revision_v45/stage_07/raw/<block>/<scenario>/<run_id>.json` |
| per-chunk manifests (Stage 7) | `experiments/thesis_revision_v45/stage_07/manifests/<scenario>.sha256` |
| durable archive (Stage 7) | `experiments/thesis_revision_v45/stage_07/archive/pocol-v45-stage07-<chunk>.tar.zst` |

**No Stage-7 data directory may contain confirmatory outputs in Stage 6.** A placeholder README
is permitted and present; validator check [9] fails the build if anything else appears under
`confirmatory/`.

---

## 5. Confirmatory output schema (one row per physical run)

**Identity columns:** `run_id`, `scenario_id`, `block_id`, `pair_id`, `master_seed`,
`seed_index`, `condition`, `control_or_treatment`, `engine_commit_sha`, `config_sha256`,
`start_timestamp`, `end_timestamp`, `wall_clock_seconds`, `run_status`.

**Outcome columns:** every outcome in `STAGE_06_OUTCOME_DICTIONARY.csv`, with NA recorded as NA
and never as zero.

**Integrity columns:** `duplicate_nonce_count`, `post_round_evaluation_record_count`,
`post_round_evaluation_nonce_count`, `evaluation_missing_terminal_time_count`,
`residency_reconciliation_status`, `nonterminal_action_count`, `nonterminal_lease_count`,
`nonterminal_request_count`, `checksum_status`.

`run_status ∈ {COMPLETED, CONFIG_ERROR, EXECUTION_ERROR, INFRASTRUCTURE_FAILURE}`.

Round-level and miner-level tables may be archived as **secondary data**. They are **not
inferentially independent** and never enter a confirmatory test as units.

---

## 6. Checksums and archives

1. **Per-run checksum** — SHA-256 of each run's output JSON, written beside it.
2. **Chunk checksum** — SHA-256 over the sorted per-run digests of the chunk.
3. **Final archive checksum** — SHA-256 of each archive file plus a top-level manifest over all
   chunk checksums.
4. Every archive is verified by round-trip extraction and digest comparison before the raw
   directory is considered redundant.

---

## 7. Gates

**Before execution:**

1. `git status --porcelain` is empty and `HEAD` is the recorded Stage-6 commit.
2. The eight accepted executable modules are byte-identical to the frozen Stage-5D digests.
3. `python -m pytest tests/thesis_revision_v45/stage2/ -q` → **195 passed**.
4. `python -m pytest tests/thesis_revision_v45/stage_06/ -q` → all Stage-6 validation tests pass.
5. `python experiments/thesis_revision_v45/stage_06/validate_preregistration.py` → exit 0.
6. Every generator `--check` passes byte-identically.
7. The freeze-candidate manifest verifies.

**After execution:**

8. Exactly 660 run records exist, one per registry row, with no duplicates and no omissions.
9. Every `config_sha256` in the output matches the registry.
10. Gates 2–7 are re-run and still pass.
11. Every archive verifies against its checksum.

**Failure-stop threshold.** Execution halts immediately if **more than 5 % of runs in any chunk**
(i.e. ≥ 2 of 30) end in `EXECUTION_ERROR` or `CONFIG_ERROR`, or if **any** run fails an IP-H9
integrity gate. Halting is a stop-and-report, not a silent skip; partial results are retained
under the retention policy.

---

## 8. Fresh-clone reproduction

```
git clone <repo> pocol-v45 && cd pocol-v45
git checkout <stage-6 commit sha>
python -m pip install --upgrade pip pytest
python -m pytest tests/thesis_revision_v45/stage2/ -q            # expect 195 passed
python -m pytest tests/thesis_revision_v45/stage_06/ -q          # Stage-6 validation
python experiments/thesis_revision_v45/stage_06/generate_seed_registry.py --check
python experiments/thesis_revision_v45/stage_06/generate_confirmatory_matrix.py --check
python experiments/thesis_revision_v45/stage_06/generate_outcome_dictionary.py --check
python experiments/thesis_revision_v45/stage_06/validate_preregistration.py
sha256sum -c docs/thesis_revision_v45/stage_06/STAGE_06_FREEZE_CANDIDATE_MANIFEST.sha256
```

Every one of these is deterministic and requires no network access and no confirmatory data.

---

## 9. What Stage 7 must not do

* It must not modify any accepted executable module.
* It must not change any margin, outcome priority or hypothesis direction (rule R16).
* It must not draw a replacement seed for any reason (rule R02).
* It must not exclude a run on the basis of any outcome value (rules R12, R13).
* It must not perform the Stage-8 statistical analysis; Stage 7 executes and archives only.
