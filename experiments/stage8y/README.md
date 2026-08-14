# Stage 8Y — Heterogeneous Energy-Aware PoCol

Tests whether PoCol can exploit heterogeneous ASIC capacity, energy-aware work
allocation, coordinated low-power participation and adaptive reserve activation to
cut total network energy by **more than 50 %** against a matched traditional-PoW
baseline while retaining **≥ 90 %** (preferably **≥ 95 %**) of accepted-block
production.

The 50 % threshold is a **preregistered acceptance criterion**, not a target. The
design admits a negative result and reports one where it occurs.

Stage 8Y is self-contained under `experiments/stage8y/`. Its only external import is
`experiments.stage8x.simulator.hashing`, read-only, so the SHA-256 primitive and the
candidate-identity definition are provably identical to Stage 8X. It never imports
`InputsConfig`, `Main`, `Scheduler`, `Statistics` or `Event`, and it modifies no
pre-existing file.

## Reproduction

Run from the repository root. Every command is tested.

```bash
# 1. environment check
python -c "import numpy, pandas, scipy, matplotlib, tabulate, pytest; print('ok')"

# 2. protected-artifact baseline (record once, then verify)
python -m experiments.stage8y.baseline --record
python -m experiments.stage8y.baseline --check

# 3. unit + integration tests (116 tests)
python -m pytest experiments/stage8y/tests -q

# 4. Pilot (378 runs, excluded from all inference)
python -m experiments.stage8y.run --phase pilot

# 5. freeze (manifest, checksums, git, environment)
python -m experiments.stage8y.freeze

# 6. primary confirmatory execution (1080 runs)
python -m experiments.stage8y.run --phase primary

# 7. secondary sensitivity execution (2880 runs)
python -m experiments.stage8y.run --phase secondary

# 8. long-horizon validation (360 runs at T = 100 000 s)
python -m experiments.stage8y.run --phase longhorizon

# 9-10. statistics, Pareto analysis, tables A-Q, 21 figures, all reports
python -m experiments.stage8y.analyze

# 11. final completeness audit + validation (also re-runs legacy and Stage 8X suites)
python -m experiments.stage8y.validate
```

Add `--force` to any `run` invocation to discard that phase's output and re-execute.
Without it, runs resume by `run_id`: completed runs are skipped, never duplicated.

Reproduction from an emptied `outputs/` and `figures/` directory has been tested.
**Do not delete `config/`, `src/`, `reports/` or `manifests/`** — the freeze manifest
and the frozen configuration live there.

Requires `numpy pandas scipy matplotlib tabulate pytest`.
Approximate cost on 4 cores: tests 4 s, pilot 28 s, primary 69 s, secondary 177 s,
long horizon 182 s, analysis ~60 s.

## Layout

```
config/   hardware_registry.json, hardware, difficulty, policies, seeds, frozen config
src/      powerstate, energy, engine, metrics, analysis_{stats,tables,figures}
tests/    116-test validation suite
outputs/  raw CSVs, energy tables, tables A-Q (.csv + .md), progress logs, summary JSON
figures/  21 figure stems x PNG + PDF + SVG
reports/  plan, hardware rationale, pilot, freeze, execution, validation, results,
          statistics, Pareto, methods, limitations, acceptance, file manifest
manifests/ protected-artifact baseline, freeze manifest, file manifest
```

## Protocols

| ID | Role | Description |
|---|---|---|
| `POW` | **principal comparator** | traditional competitive PoW; distinct per-miner templates, local instant extranonce roll, always ACTIVE |
| `P0_ALL` | primary | PoCol, all miners active — isolates heterogeneity alone |
| `P3_ENERGY` | primary | PoCol, energy-aware active set (exact `min ΣP s.t. Σh ≥ H_req`) |
| `P4_RESERVE` | primary | PoCol, staged reserve activation with an explicit wake transition |
| `P1_EQUAL` | secondary | PoCol, equal ranges — fast miners finish first and park |
| `P2_HASHPROP` | secondary | PoCol, hash-proportional ranges — the control for P1 |
| `POW_CT` | **secondary diagnostic only** | Common-Template Independent PoW; the only configuration where exact duplicates are non-degenerate. Never the baseline, never a model of mainnet. |

## Headline result

**Outcome C.** > 50 % energy saving is reachable — maximum **53.9 %**
(P3_ENERGY, H2, N = 300, α = 0), still > 50 % at α = 0.05 — but **never with ≥ 90 %
block retention**: the best retention among all > 50 % configurations is **68.8 %**,
median latency runs 1.79–1.85× PoW against a 1.10 criterion, and the decomposition
attributes **~75 % of the saving to reduced hash participation** rather than to
preferential selection of efficient ASICs.

Read `reports/STAGE_8Y_LIMITATIONS.md` before quoting any number.
