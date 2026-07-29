# Stage 5B1A — Scientific Code-Freeze Manifest

Builder: `experiments/thesis_revision_v43/code_freeze_5b1a.py`
Machine-readable: `results/thesis_revision_v43/stage_05b1a/manifests/code_freeze_manifest.json`

Stage 5B2 **must run only from the exact commit that carries this manifest**. Any
later code change invalidates the affected runs and requires a new freeze.

## 1. Frozen inputs

| Field | Value |
|-------|-------|
| Stage | 5B1A |
| Timestamp | 2026-07-29 |
| Matrix SHA-256 | `e436609dad106166ef4071c1a6cac6ed3cc2b22adda77b4bf87f7d6a61d404fc` |
| Seed-schedule SHA-256 | `6122dbd0f455a1c4c9676ec6575f064c3a682b3c978705d6588af11489b13e10` |
| Retention-list checksum | `2283f2ff69bcabf423267b2984ef4acfce852b217b39e1efe8061e583bc1702e` |
| Dependency-lock SHA-256 | `6e211ea7c031a3fab560843690e27e5a3c2aa2a8c363ab483369a2babc8157be` |
| Output-schema version | `5b1a.1` |
| Scenario-engine version | `5b1a.1` |
| Final Stage-5B2 run count | 1 890 |
| Test-suite result | **235 passed** |
| Thesis DOCX SHA-256 | `2c3afdc5739109d0ea12ada96c3115d626a2188c1acbaeaa4b6020974884cbda` |
| Thesis PDF SHA-256 | `131412bb2ce17ed97b98dfbefc136c7b5b226b9fd7372e79a25e4b0dc057e9c4` |

## 2. Freeze commit

The authoritative freeze reference is the **Stage-5B1A commit that adds this
manifest** — a commit's SHA cannot be embedded in its own content, so the manifest
records the base commit it descends from (`freeze_commit_ref`) and the freeze SHA is
reported in the Stage-5B1A Completion Report and in `git log`. Reproducing any run
requires: this commit + `STAGE_05B1A_FINAL_MATRIX.csv` (matrix SHA above) + the
frozen seed schedule + `requirements-thesis-v43-lock.txt` (dependency-lock SHA).

## 3. Verification performed at freeze

- Full test suite green (235 passed).
- Thesis DOCX/PDF SHA-256 byte-identical to draft-42.
- Matrix, seed, retention, and dependency checksums recorded.
- Repository state checked (`code_freeze_5b1a.repo_is_clean`); the freeze is the
  single Stage-5B1A commit.

## 4. Post-freeze rule

Stage 5B2 executes the 1 890-run matrix from this commit only. The retention list is
preserved unchanged except that failed/anomalous runs are added automatically. Any
edit to the scenario engine, hashing, matrix, seeds, or dependency lock **voids the
freeze** and requires regenerating this manifest under a new commit.
