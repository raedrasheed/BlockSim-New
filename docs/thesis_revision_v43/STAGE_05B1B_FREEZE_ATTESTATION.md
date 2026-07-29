# Stage 5B1B — External Scientific Freeze Attestation

Builder: `experiments/thesis_revision_v43/freeze_inputs_5b1b.py`
Internal manifest: `results/thesis_revision_v43/stage_05b1b/manifests/freeze_input_manifest.json`
Annotated tag: **`thesis-v43-stage5b2-freeze-1`**

## 1. Why an external attestation

A file committed to Git cannot reliably contain the SHA of the commit that contains
it (self-reference). Stage 5B1A's manifest therefore recorded only the *base*
commit. Stage 5B1B fixes this with a two-part scheme:

1. an **internal freeze-INPUT manifest**, committed, that records the frozen inputs
   and the *intended* tag name but makes **no** claim to contain its own commit SHA
   (`contains_own_commit_sha: false`, plus an explicit `self_reference_note`);
2. an **external annotated Git tag**, created **after** the commit exists, whose
   message carries the full 40-char commit SHA and all 64-hex checksums.

Stage 5B2 checks out and runs from the **tag**, not from a mutable branch.

## 2. Internal freeze-input manifest (committed, non-self-referential)

Records: matrix / seed-schedule / retention-list / dependency-lock SHA-256, scenario-
engine version, output-schema version, full test-suite result, thesis DOCX/PDF
SHA-256, and `intended_freeze_tag`. It asserts `contains_own_commit_sha: false`
(test 21). Input checksums (64-hex):

| Input | SHA-256 |
|-------|---------|
| Matrix (`STAGE_05B1B_FINAL_MATRIX.csv`) | `306d82834395a6bb159dbacf713eaf2290a7ada52c1e9c451c031d09014edce5` |
| Seed schedule | `6122dbd0f455a1c4c9676ec6575f064c3a682b3c978705d6588af11489b13e10` |
| Retention list | `2283f2ff69bcabf423267b2984ef4acfce852b217b39e1efe8061e583bc1702e` |
| Dependency lock | `6e211ea7c031a3fab560843690e27e5a3c2aa2a8c363ab483369a2babc8157be` |
| Thesis DOCX | `2c3afdc5739109d0ea12ada96c3115d626a2188c1acbaeaa4b6020974884cbda` |
| Thesis PDF | `131412bb2ce17ed97b98dfbefc136c7b5b226b9fd7372e79a25e4b0dc057e9c4` |

Scenario-engine version `5b1b.1` · output-schema `5b1a.1` · 1 890 runs.

## 3. Annotated tag `thesis-v43-stage5b2-freeze-1`

Created after the single Stage-5B1B commit. Its message contains, in full: the
40-char commit SHA, the four input checksums above, the two thesis checksums, the
engine and schema versions, the test-suite result, and a UTC timestamp. The tag is
pushed alongside the commit. **The tagged commit is never amended.** The exact
commit SHA and the annotated-tag object SHA are reported in the Stage-5B1B
Completion Report (they cannot be embedded here without self-reference).

## 4. Rule for Stage 5B2 and beyond

- Stage 5B2 must `git checkout thesis-v43-stage5b2-freeze-1` and run only from it.
- Any later scientific code change requires a new commit and a **new** freeze tag
  with an incremented suffix (`…-freeze-2`).
