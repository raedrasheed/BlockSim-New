# Stage 0 — Change Map (permitted vs. forbidden scope per stage)

Defines, for each stage, exactly which artifact classes may be created/modified and which are
forbidden. A change outside a stage's permitted column is a governance violation.

## Artifact classes

- **GOV** — governance/verification docs (`docs/thesis_revision_v45/STAGE_0x_*`).
- **SPEC** — protocol specification, state machine, pseudocode, invariants, threat model
  (docs only; no executable code).
- **ENGINE** — the scientific simulator/engine, schemas, and their source tests.
- **EXP** — experiment matrix, seed tables, analysis plan, pilot/preregistration configs.
- **DATA** — executed run outputs, archives, manifests.
- **ANALYSIS** — statistical analysis code + result tables/figures for this line.
- **THESIS** — any `.docx` (draft-45 and its audits).
- **PROTECTED** — everything in `STAGE_00_PROTECTED_ARTIFACTS.md` (always read-only).

## Per-stage permissions

| Stage | May create/modify | Forbidden |
|------:|-------------------|-----------|
| 0 | GOV | ENGINE, SPEC, EXP, DATA, ANALYSIS, THESIS, PROTECTED |
| 1 | GOV, SPEC | ENGINE (code), THESIS, PROTECTED |
| 2 | GOV, ENGINE (idle states + multi-state energy) | security-floor controller (Stage 3), THESIS, PROTECTED |
| 3 | GOV, ENGINE (security floor + reserve) | **difficulty changes**, THESIS, PROTECTED |
| 4 | GOV, ENGINE (leases, reassignment, progress model) | cryptographic-proof claims, THESIS, PROTECTED |
| 5 | GOV, ENGINE (adversarial + incentive model) | incentive-compatibility claims, THESIS, PROTECTED |
| 6 | GOV, EXP (pilot + preregistration) | using pilot data for confirmatory claims, THESIS, PROTECTED |
| 7 | GOV, DATA (frozen execution + archive) | **any ENGINE change after viewing results**, THESIS, PROTECTED |
| 8 | GOV, ANALYSIS | ENGINE re-execution, THESIS, PROTECTED |
| 9 | GOV, THESIS (`draft-45-00.docx` + audits) | modifying draft-44, PROTECTED |
| 10 | GOV, THESIS (render, layout fixes, clean copy) | PROTECTED |

## Stage-0 permitted files (this stage, exhaustively)

Only these are created; nothing else is touched:

- `docs/thesis_revision_v45/STAGE_00_GOVERNANCE.md`
- `docs/thesis_revision_v45/STAGE_00_PROTECTED_ARTIFACTS.md`
- `docs/thesis_revision_v45/STAGE_00_CHANGE_MAP.md`
- `docs/thesis_revision_v45/STAGE_00_RISK_REGISTER.md`
- `docs/thesis_revision_v45/STAGE_00_CHECKSUM_MANIFEST.sha256`

## Frozen-after-view rule (Stage 7 → 8)

Once frozen-matrix results are viewed (Stage 7 onward), the scientific engine, schema,
dependencies, matrix, seeds, analysis plan, and retention policy are **frozen**. No engine
edit may occur after results are seen; a needed change forces a new preregistered freeze
cycle, not an in-place edit.

## Difficulty rule (Stages 3, 6, 7, 8)

Difficulty is **held constant** in the core confirmatory experiment. Any difficulty-control
experiment is a **separate exploratory** artifact set, labelled EXPLORATORY, and never merged
into the confirmatory contrasts.

## Branch/commit discipline

- All work lands on `thesis-v45-*` branches created from the approved predecessor commit.
- One controlled commit set per stage; push with `-u origin <branch>`.
- Protected branches are never checked out for modification, force-pushed, or deleted.
