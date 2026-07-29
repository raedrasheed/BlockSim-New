# BASELINE FREEZE — Thesis Scientific Revision v43 (Stage 1)

**Purpose:** Freeze the exact state of the code, data, and thesis *before* any
scientific or implementation correction, so that every later change is
measured against a fixed, reproducible reference point. **No defect is fixed in
Stage 1.**

---

## 1. Provenance of the revision environment

| Item | Value |
|---|---|
| Repository | `raedrasheed/BlockSim-New` |
| Default branch (`main`) commit | `7f3129eefa9aed10cb915c732d90fd52cef69b8c` |
| **Effective base commit of this stage** | `2d3c243b36e904ca04bf391b0a4adc73c8cbe273` |
| Base commit subject | `Add Raed-Rasheed-draft-42-00` |
| Working branch (created this stage) | `claude/thesis-scientific-revision-v43` |
| Python | 3.11.15 |
| Platform | Linux 6.18.5 (ephemeral container) |

### ⚠️ Branch-base discrepancy (must be acknowledged)

The Stage 1 instruction was to branch from `main`. **The authoritative thesis
files `docs/Raed-Rasheed-draft-42-00.docx/.pdf` do NOT exist on `main`
(`7f3129e`).** They were introduced by a single commit `2d3c243`
(`Add Raed-Rasheed-draft-42-00`) which sits one commit ahead of `main` on the
harness branch `claude/blocksim-thesis-audit-fgepvs`:

```
$ git log --oneline main..2d3c243
2d3c243 Add Raed-Rasheed-draft-42-00
$ git ls-tree -r --name-only main -- docs/ | grep draft-42
(none)
```

Branching literally from `main` would produce a working tree with **no thesis**,
making the revision impossible. Therefore this branch was based on `2d3c243`
(= `main` + the single thesis-adding commit). Both SHAs are recorded above.
**If the candidate requires a literal `main` base, please advise; the thesis
files would then have to be re-introduced.**

---

## 2. Original thesis files — SHA-256 (byte-for-byte integrity)

Recorded **before** any Stage 1 activity and to be re-verified **after**:

| File | SHA-256 (before) |
|---|---|
| `docs/Raed-Rasheed-draft-42-00.docx` | `2c3afdc5739109d0ea12ada96c3115d626a2188c1acbaeaa4b6020974884cbda` |
| `docs/Raed-Rasheed-draft-42-00.pdf`  | `131412bb2ce17ed97b98dfbefc136c7b5b226b9fd7372e79a25e4b0dc057e9c4` |

These files are **never** edited, moved, renamed, or overwritten in this project.
Post-stage verification appears in the Stage 1 Completion Report.

---

## 3. Dependency lock

Runtime + test dependencies were absent from the base image and were installed
and pinned. See `requirements-thesis-v43-lock.txt`:

```
pandas==3.0.5
numpy==2.4.6
xlsxwriter==3.2.9
scipy==1.17.1
pytest==9.1.1
```

**Note (potential threat to reproducibility):** the original thesis experiments
almost certainly ran on *older* pandas/numpy. The exact original versions are
**not recorded anywhere in the repository** (no `requirements.txt`, no lock
file, no environment capture in the thesis). This is logged as a reproducibility
gap, not fixed in Stage 1.

---

## 4. Seed / determinism audit (critical finding)

A repository-wide search found **no random-seed control of any kind**:

```
grep -rn --include=*.py -E "random\.seed|np\.random\.seed|seed\(" .
-> NONE FOUND
```

The simulator uses Python's global `random` (`random.expovariate`,
`random.randrange`) and `numpy` without ever calling `random.seed(...)` or
`np.random.seed(...)`. **Every run is therefore non-deterministic**, seeded from
OS entropy at process start.

**Consequence:** the single-run values reported in the thesis (Chapter 7,
Tables 7.1/7.2) **cannot be exactly reproduced** by re-running the code — only
their statistical pattern can. This is the primary reason Chapter 7 headline
values are classified **UNTRACEABLE** in `THESIS_TO_CODE_TRACEABILITY.csv`.
Stage 1 demonstrates this non-determinism empirically via repeated runs of two
configurations (see `BASELINE_NUMERICAL_AUDIT.md`).

---

## 5. Two distinct research artifacts in one repository (scope guard)

Per the approved scope, this project touches **only the thesis path**. The
repository also contains an unrelated journal manuscript; its assets are **out
of scope** and untouched.

| In scope (thesis) | Out of scope (journal manuscript) |
|---|---|
| `docs/Raed-Rasheed-draft-42-00.*` | `docs/Extending_BlockSim_*.{docx,pdf}` |
| `Models/PoCol/*`, `Models/Bitcoin/*` | `Models/Energy/energy_models.py`, `Models/Energy/scenarios.py` |
| `Models/Node.py`, `Scheduler.py`, `Event.py`, `Statistics.py`, `InputsConfig.py`, `Main.py` | `experiments/*`, `results/data/*`, `results/figures/*`, `tests/test_energy_models.py` |
| PoW = simulator **Model 1**; PoCol = simulator **Model 3** | PoW-economic / PoS-validator energy models (reviewer-response paper) |

The 30-seed experiments, figures, and `tests/test_energy_models.py` belong to
the **journal manuscript** and do **not** generate the thesis's Chapter 7
tables. They must not be presented as thesis evidence.

---

## 6. Large committed workbooks (left untouched, per instruction)

The following committed outputs are **left in place, unmodified** (Stage 1
constraint 8). They are single Bitcoin/Ethereum runs (Model 1 / Model 2), *not*
the thesis 100–500 miner sweep, but they independently corroborate the PoW
`/100` accounting mechanism (see numerical audit):

- `Bitcoin_20260122_143644_…xlsx` — 50 miners → 3.93 kWh
- `Bitcoin_20260122_153749_…xlsx` — 1000 miners → 83.84 kWh
- `Bitcoin_20260122_151441_…xlsx`, `Bitcoin_20260122_151630_…xlsx`
- `Ethereum_20260122_15*.xlsx` (4 files)

---

## 7. Read-only baseline snapshot layout

```
results/thesis_revision_v43/
├── baseline_snapshot/   # raw .xlsx outputs of the as-is runs (chmod 0444)
├── logs/                # per-run stdout/stderr
└── manifests/           # per-run provenance JSON + _ALL_RUNS.json
```

Each manifest records: tag, model, miner count, repeat index, git commit,
seed status, exact command + config, InputsConfig SHA-256, start/end UTC
timestamps, wall time, return code, output filename, output SHA-256, and the
raw InputConfig/SimOutput rows.

---

## 8. What Stage 1 deliberately did NOT do

- Did **not** modify `Models/Node.py` (`/100` normalization) — documented only.
- Did **not** modify `Models/PoCol/Consensus.py` (`÷N` energy share) — documented only.
- Did **not** add seeds, event IDs, idle power, or any correction.
- Did **not** edit any tracked source file to run the matrix (a *copy* of the
  source was edited in the scratchpad; the tracked `InputsConfig.py` is unchanged
  — verified by `git status`).
- Did **not** hand-edit any generated result file.
