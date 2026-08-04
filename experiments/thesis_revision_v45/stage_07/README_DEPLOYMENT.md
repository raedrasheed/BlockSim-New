# Stage 7 — Portable Frozen-Execution Bundle

Self-contained, resumable, CONCURRENT execution of the **660 frozen logical rows**,
realised as **630 unique physical executions** (A05 and B01 share a configuration —
see STAGE_07A_PREREGISTRATION_AMENDMENT.md) on a
persistent external host. Nothing here regenerates a run identity, a seed, a scenario or a
configuration: the bundle consumes the Stage-6 frozen artefacts and executes them.

**Baseline commit:** `026483496ffb434243f45e174c63b43b77b3b43a`
**Stage-7 preflight-failure commit:** `ca81c986ce63ab27ce45939a4f6a80bfd9998707`

> The bundle **refuses to execute the first confirmatory run** unless a filled host record
> evaluates to `verdict = PASS`. That is the point of it.

## 1. The memory equation

Concurrency is decided by memory, never by core count:

```
required_RAM = 1.25 * (
      n_lightweight    * peak_RAM_lightweight
    + n_security_floor * peak_RAM_security_floor
    + n_reassignment   * peak_RAM_reassignment
    + n_compressors    * peak_RAM_compressor )
```

| term | value | basis |
|---|---:|---|
| `peak_RAM_lightweight` | 3 010 MB (2.94 GiB) | **MEASURED** — A03, A05 |
| `peak_RAM_reassignment` | 5 266 MB (5.14 GiB) | **MEASURED** — C04 |
| `peak_RAM_security_floor` | 4 397 MB (4.29 GiB) | **ESTIMATED** — right-censored B02 |
| `peak_RAM_compressor` | 707 MB (0.69 GiB) | **MEASURED** — xz -9 fixed encoder dictionary |

Worked values, after the 1.25 margin and **before** OS and orchestration reserve:

| heavy workers | required RAM |
|---:|---:|
| 8 | **51.4 GiB** |
| 16 | **102.9 GiB** |
| 8 + 2 compressors | 53.2 GiB |

## 2. Recommended host classes

### PLAN A
* 16 vCPU
* 96 GB RAM
* 50 GB persistent NVMe
* **30-day guaranteed lifetime**
* maximum **8 heavy workers**, and only after the preflight passes

### PLAN B
* 32 vCPU
* 128 GB RAM
* 100 GB persistent NVMe
* minimum **14-day guaranteed lifetime**
* worker mix determined by **measured RAM**, not core count alone

Neither plan authorises execution on its own. The preflight decides.

## 3. Deployment

```bash
git clone <repo> && git checkout thesis-v45-pocol-stage7-frozen-execution
cd experiments/thesis_revision_v45/stage_07

python resource_preflight.py --template host.json     # 1. emit the blank record
# (a reference copy lives at docs/thesis_revision_v45/stage_07/
#  STAGE_07_RESOURCE_PREFLIGHT_RECORD.template.json — the bundle directory holds
#  code only, so that the Stage-6 no-confirmatory-output guard stays exact)
$EDITOR host.json                                     # 2. fill from DIRECT OBSERVATION
python resource_preflight.py --record host.json       # 3. evaluate -> PASS or FAIL

python run_stage7.py --preflight host.json --dry-run  # 4. inspect the schedule
python run_stage7.py --preflight host.json            # 5. execute (refuses unless PASS)
python resume_stage7.py --preflight host.json         # 6. after any interruption

python build_physical_registry.py                     # 7. 630 physical / 660 logical
python build_run_level_dataset.py                     # 8. one row per LOGICAL run
python verify_stage7_archive.py                       # 9. round-trip verify the archive
```

Every field in `host.json` must come from direct observation of the host. A field filled from a
quotation, a marketing figure or an intention to provision is a preflight failure, not a
formality.

## 4. Priority order

Slowest and longest first, so the binding path starts immediately:

1. `SECURITY_FLOOR` — B02, B03, B04 (~18.6 h each, **ESTIMATED**)
2. `REASSIGNMENT` — C02–C05, D00–D04, D04C (~4.4 h each, measured)
3. `C06` — full-domain no-block; **unbenchmarked**, scheduled at the slowest class's timeout
4. `LIGHTWEIGHT` — the remaining 8 scenarios (~2.8 h each, measured)

## 5. Run lifecycle

```
PENDING -> RUNNING -> COMPLETED
                   -> FAILED_INFRASTRUCTURE -> (same seed, same config) -> RERUN_COMPLETED
                   -> FAILED_MODEL           -> STOPS THE FROZEN EXECUTION
```

After every completed run, in order: validate schema → checksum → compress → **verify the
compressed copy by round-trip** → atomically update the registry → archive the log → reclaim
the temporary raw file. The raw file is deleted only after its compressed copy has been
decompressed and its digest compared.

`resume_stage7.py` re-executes only `PENDING`, interrupted `RUNNING` and
`FAILED_INFRASTRUCTURE`. A `COMPLETED` or `RERUN_COMPLETED` run is **never** re-executed. A
`FAILED_MODEL` run is **never** retried — it stops execution, and the engine is not modified.

**No replacement seed is ever drawn.** An infrastructure retry reuses the identical
`(scenario_id, master_seed)` pair and the identical frozen configuration; both attempts are
archived and the successful attempt is the inferential record.

## 6. What must not happen

* No outcome-based stopping. Partial effects are never inspected to decide whether to continue.
* Zero-block runs stay in the dataset.
* NA stays NA. It is never imputed as zero.
* Rounds, miners, blocks, transactions and evaluation intervals are **not** independent
  inferential observations; the unit is one physical run under one master seed.
* The engine, `search.py`, the scenarios, the seeds, the hypotheses, the outcomes, the margins
  and the analysis plan are frozen and are not modified by this bundle.

The algorithm is **PoCol**. The energy-saving mechanism is **the idle policy within PoCol**.
Nonce-domain partitioning alone is not an energy-saving mechanism.


## 7. Concurrency (S7A-1)

Workers run as genuinely concurrent non-blocking subprocesses. `Pool` keeps **separate active
counts per cost class**, a **total process cap** that charges compressors against the same
budget, and never exceeds the preflight-approved limits. Admission order is deterministic
(priority band, scenario, seed index); completion order is not, and a run's identity never
depends on when it finished. `C06` is unbenchmarked and is admitted against the **slowest
measured class's** budget, not the lightweight one.

A `FAILED_MODEL` result stops **new admissions** immediately; already-running workers are
allowed to close safely, and the engine is not modified.

## 8. Durable paths (S7A-2)

Nothing is hard-coded to the repository. `ExecutionPaths` derives the registry, raw, logs,
failed_attempts, chunks, archive, manifests and run_level locations from the host record's
`durable_output_path` and `archive_path`. The preflight verifies those paths **on the real
filesystem**: creatable, writable, measured free space *at the path*, `os.replace` atomicity on
the registry filesystem, and a compress/decompress/digest round-trip on the archive filesystem.
A record whose numbers look fine but whose paths do not work is **rejected**.

## 9. Result provenance after reclaim (S7A-5)

The raw file is deleted once its compressed copy verifies, so the registry never records a
dangling `result_file`. It records `raw_reclaimed=true`, the original `raw_sha256`, the
existing `compressed_file` and `compressed_sha256`, and `archive_verified`. The dataset builder
reads only the verified existing archive member.

## 10. `chunk_size`

Removed from the execution interface. It was never an executable checkpoint boundary — the
checkpoint is the atomic registry update after **every** completed run — so carrying a
parameter that did nothing would have been misleading. Chunking remains a *reporting* concept
in the archive plan only.
