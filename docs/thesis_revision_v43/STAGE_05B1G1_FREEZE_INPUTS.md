# Stage 5B1G.1 — Freeze Inputs (for freeze #6)

Builder: `experiments/thesis_revision_v43/freeze_inputs_5b1g1.py`
Internal manifest: `results/thesis_revision_v43/stage_05b1g1/manifests/freeze_input_manifest.json`
Intended freeze branch: **`thesis-v43-stage5b2-freeze-6`**
Supersedes (invalidated for execution, preserved): `thesis-v43-stage5b2-freeze-5`
(and `…-4`, `…-3`, `…-2`, `…-1`)

## 1. Non-self-referential design

The internal freeze-INPUT manifest is committed with `contains_own_commit_sha: false`
and an explicit `self_reference_note`; the corrective-commit SHA is recorded
externally in the new remote freeze branch and the Stage-5B1G.1 completion report.

## 2. Frozen inputs (64-hex)

| Input | SHA-256 |
|-------|---------|
| Matrix (`STAGE_05B1G1_FINAL_MATRIX.csv`) | `9cb7297e7418a96fbaeb7f06c162bc8bdea1c1e049002a40344cab16cf5f6fcb` |
| Seed schedule | `6122dbd0f455a1c4c9676ec6575f064c3a682b3c978705d6588af11489b13e10` |
| Retention list | `2283f2ff69bcabf423267b2984ef4acfce852b217b39e1efe8061e583bc1702e` |
| Dependency lock | `6e211ea7c031a3fab560843690e27e5a3c2aa2a8c363ab483369a2babc8157be` |
| Thesis DOCX | `2c3afdc5739109d0ea12ada96c3115d626a2188c1acbaeaa4b6020974884cbda` |
| Thesis PDF | `131412bb2ce17ed97b98dfbefc136c7b5b226b9fd7372e79a25e4b0dc057e9c4` |

Scenario-engine version `5b1g.2` · output-schema `5b1g.2` · 1 890 runs · full test
suite **444 passed**.

## 3. Matrix hash audit (freeze #6)

1 890 rows · 63 `scientific_semantics_hash` groups all of size 30 · 1 890 unique
`run_execution_hash` · 0 duplicate same-seed semantics · B3/C1 → 870 shared runs · 0
anomalous groups. `run_execution_hash` and `scientific_semantics_hash` differ from
freeze #5 (engine `5b1g.2`); scenario **semantics definitions are unchanged** — the
micro-corrections fix per-run behaviour (exact B2 coverage, B2 path provenance,
per-non-winner deliveries + post-winner work), not matrix membership (1 890 runs,
63 × 30). The matrix SHA differs from freeze #5 (`84db950f…` → `9cb7297e…`); the seed
schedule, retention list, and dependency lock are byte-identical to prior freezes.

## 4. Rule for freeze #6

After the corrective commit is pushed, create remote branch
`thesis-v43-stage5b2-freeze-6` pointing exactly to the full corrective-commit SHA
(reported in the completion report). Stage 5B2 checks out and runs **only** from
freeze branch 6. The corrective commit must not be amended; a further scientific
change would require freeze #7. Freeze branches 1–5 are preserved unchanged as
historical invalidated freezes; **freeze-5 is invalid for execution**.
