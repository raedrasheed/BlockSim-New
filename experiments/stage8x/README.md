# Stage 8X — PoCol disjoint allocation + post-range low power vs traditional PoW

Fixed per-miner ASIC capacity (Bitmain Antminer S21 Pro: 234 TH/s, 3510 W, 15 J/TH).
Aggregate hash rate and aggregate active power both scale with the miner population;
difficulty is coupled to that growth so the matched PoW baseline keeps a 600 s nominal
block interval at every N.

Stage 8X is **self-contained**. It writes only under `experiments/stage8x/` and imports
only the pure `Models.Energy` constants; it never imports `InputsConfig`, `Main`,
`Scheduler`, `Event` or `Statistics`, so no earlier experiment is affected.

## Reproduction

Run from the repository root. Every command below is tested.

```bash
python -m experiments.stage8x.run      --phase pilot      # 45 pilot runs (excluded from inference)
python -m experiments.stage8x.validate                    # validation suite + non-interference check
python -m experiments.stage8x.freeze                      # manifest, checksums, commit, environment
python -m experiments.stage8x.run      --phase primary    # 300 physical runs + 600 alpha energy rows
python -m experiments.stage8x.run      --phase secondary  # 420 declared secondary diagnostic runs
python -m experiments.stage8x.analyze                     # tables A-I, 17 figures, final reports
```

Add `--force` to a `run` invocation to discard that phase's output and re-execute the
whole matrix. Without it, runs are resumable by `run_id`: completed runs are skipped and
never duplicated.

Tests alone: `python -m pytest experiments/stage8x/tests -q`

Requires `numpy pandas scipy matplotlib pytest`.

Approximate cost on 4 cores: pilot ~3 s, primary ~18 s, secondary ~6 min, analysis ~15 s.

## Layout

```
config/      ASIC profile, difficulty/target derivation, seed registry, frozen config
simulator/   candidate hashing semantics, power-state ledger, energy accounting, engine
analysis/    paired statistics, summary tables, figures
tests/       validation suite (74 tests)
outputs/     raw CSVs, seed registry, tables, progress logs
figures/     PNG + PDF + SVG
reports/     plan, pilot, freeze, execution, validation, results, methods, limitations
```

## Key outputs

| File | Contents |
|---|---|
| `outputs/stage8x_physical_runs.csv` | one row per primary physical run (300) |
| `outputs/stage8x_energy_sensitivity.csv` | one row per PoCol run x alpha (600) |
| `outputs/stage8x_secondary_runs.csv` | declared secondary diagnostics (420) |
| `outputs/stage8x_tableA..I_*.csv` | publication-rounded summary tables |
| `outputs/stage8x_seeds.json` | frozen seed registry (checksummed in the manifest) |
| `reports/STAGE_8X_RESULTS_REPORT.md` | the full result |
| `reports/STAGE_8X_LIMITATIONS.md` | read this before quoting any number |

## Protocols

| ID | Role | Description |
|---|---|---|
| `X-PW` | primary | Traditional competitive PoW. Distinct per-miner templates, independent search, local instant extranonce roll, always ACTIVE. |
| `X-PC` | primary | PoCol. Common immutable template per epoch, static disjoint miner-owned ranges, ACTIVE→LOW_POWER on range completion, wake on next legitimate event. No reserve miners, useful-work floor, reassignment or borrowing. |
| `X-PW-MT` | **secondary diagnostic** | Common-template PoW with random start offsets. The only configuration in which exact-input duplication is non-degenerate. Not part of the primary energy comparison, and not a model of Bitcoin mainnet. |
