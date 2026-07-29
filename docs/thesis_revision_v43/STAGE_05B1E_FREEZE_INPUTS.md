# Stage 5B1E — Freeze Inputs (for freeze #3)

Builder: `experiments/thesis_revision_v43/freeze_inputs_5b1e.py`
Internal manifest: `results/thesis_revision_v43/stage_05b1e/manifests/freeze_input_manifest.json`
Intended freeze branch: **`thesis-v43-stage5b2-freeze-3`**
Supersedes (invalidated, preserved): `thesis-v43-stage5b2-freeze-2` (and `…-freeze-1`)

## 1. Non-self-referential design

The internal freeze-INPUT manifest is committed with `contains_own_commit_sha: false`
and an explicit `self_reference_note`; the corrective-commit SHA is recorded
externally in the new remote freeze branch and the Stage-5B1E completion report.

## 2. Frozen inputs (64-hex)

| Input | SHA-256 |
|-------|---------|
| Matrix (`STAGE_05B1E_FINAL_MATRIX.csv`) | `5fc3812763ffaeb317b95b77c7e8abef29a5333fe8562d92f6a92c0a797ccde1` |
| Seed schedule | `6122dbd0f455a1c4c9676ec6575f064c3a682b3c978705d6588af11489b13e10` |
| Retention list | `2283f2ff69bcabf423267b2984ef4acfce852b217b39e1efe8061e583bc1702e` |
| Dependency lock | `6e211ea7c031a3fab560843690e27e5a3c2aa2a8c363ab483369a2babc8157be` |
| Thesis DOCX | `2c3afdc5739109d0ea12ada96c3115d626a2188c1acbaeaa4b6020974884cbda` |
| Thesis PDF | `131412bb2ce17ed97b98dfbefc136c7b5b226b9fd7372e79a25e4b0dc057e9c4` |

Scenario-engine version `5b1e.1` · output-schema `5b1a.1` · 1 890 runs · test suite
**330 passed**.

## 3. Matrix hash audit (freeze #3)

1 890 rows · 63 `scientific_semantics_hash` groups all of size 30 · 1 890 unique
`run_execution_hash` · 0 duplicate same-seed semantics · B3/C1 → 870 shared runs · 0
anomalous groups. `run_execution_hash` and `scientific_semantics_hash` differ from
freeze #2 (engine `5b1e.1`); scenario **semantics definitions are unchanged** — the
corrections fix per-run behaviour, not the matrix membership (1 890 runs, 63 × 30).

## 4. Rule for freeze #3

After the corrective commit is pushed, create remote branch
`thesis-v43-stage5b2-freeze-3` pointing exactly to the full corrective-commit SHA
(reported in the completion report). Stage 5B2 checks out and runs **only** from
freeze branch 3. The corrective commit must not be amended; a further scientific
change would require freeze #4.
