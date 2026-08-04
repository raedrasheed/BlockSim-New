# DO NOT RUN IN STAGE 6

This directory holds **configurations and registries only**. It contains, and must contain, **no
run output**.

```
frozen_configs/                   21 frozen per-scenario configurations (JSON)
confirmatory_run_registry.csv     630 planned physical runs (21 scenarios x 30 master seeds)
README_DO_NOT_RUN_IN_STAGE6.md    this file
```

## Prohibitions in force

* Do not execute any confirmatory master seed.
* Do not perform confirmatory statistical analysis.
* Do not make confirmatory energy, security, service or incentive claims.
* Do not begin Stage 7.

The 30 confirmatory master seeds live in
`docs/thesis_revision_v45/stage_06/STAGE_06_SEED_REGISTRY.csv` under the source label
`PoCol-v45-stage7-confirmatory-`. They are provably disjoint from the 8 pilot seeds, and the
Stage-6 pilot executed **pilot seeds only** — asserted by
`validate_preregistration.py` check [12] and by the Stage-6 test suite.

## Enforcement

`validate_preregistration.py` check [9] fails the build if any file appears in this directory
other than this README, `confirmatory_run_registry.csv`, and `.json` files under
`frozen_configs/`. The GitHub Actions workflow runs that check on every push.

## When Stage 7 is authorised

Follow `docs/thesis_revision_v45/stage_06/STAGE_06_STAGE7_EXECUTION_PLAN.md`. Stage-7 output goes
to `experiments/thesis_revision_v45/stage_07/`, never here.
