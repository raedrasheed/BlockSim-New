# Stage 9 — Evidence Inventory

Document-only thesis-integration stage. No simulation, engine, seed, dataset, analysis,
figure or statistical-decision file is modified. This inventory records the complete
frozen evidence base that Stage 9 integrates into the PhD thesis, and its provenance.

## 1. Baseline

* **Branch:** `thesis-v45-pocol-stage8u-single-handoff-pow-comparison`
* **HEAD SHA:** `8c56773871e11c59323f9d705fcca29960cdcf1c`
* **Verified at Stage-9 start:** clean worktree; Stage-8U manifest 137/137 files verify;
  Stage-8S manifest verifies; draft-44 SHA-256 `a31400bce212585df8197ee3d63e4eb887b5f5d0f2f8a65b916b2489dbc12340`
  (matches the Stage-0 protected register); 257 accepted tests pass.
* **Authoritative source thesis:** `docs/Raed-Rasheed-draft-44-00.docx` (Stage-7B
  corrected thesis; preserved byte-identically — Stage 9 never edits it in place).

## 2. Evidence hierarchy (highest authority first)

### Tier 1 — Stage 8U: matched same-template PoW versus PoCol (final)
* Frozen 60-run dataset: `docs/thesis_revision_v45/stage_08u/STAGE_08U_RUN_DATASET.csv`
  (SHA in the Stage-8U manifest). 5 scenarios × 12 fresh paired confirmatory seeds.
* Analysis: `experiments/thesis_revision_v45/stage_08u/stage8u_results.json`;
  decisions `STAGE_08U_HYPOTHESIS_DECISIONS.csv`; comparison
  `POW_POCOL_COMPARISON_TABLE.csv`; effects `POW_POCOL_EFFECT_ESTIMATES.csv`.
* Figures FIG01–FIG18 (`figures/`), each SVG + 300-dpi PNG + CSV + caption + checksum.
* Reports: `STAGE_08U_ANALYSIS_REPORT.md`, `STAGE_08U_LIMITATIONS.md`,
  `STAGE_08U_THESIS_INSERTION_PACKAGE.md`, `STAGE_08U_COMPLETION_REPORT.md`.
* Scale: 20 miners (16 active primaries, 4 reserves), 300 s horizon, 1600-nonce domain,
  difficulty 1000, batch 25, base rate 100 nonces/s, reserve fraction 0.20.
* **Verdict: NOT LICENSED** (H-U1 pass, H-U2 fail, H-U3 pass, H-U5 fail; integrity 60/60).

### Tier 2 — Stage 8S: best throughput-oriented PoCol operating policy
* Frozen 48-run dataset: `docs/thesis_revision_v45/stage_08s/STAGE_08S_RUN_DATASET.csv`.
* Analysis: `experiments/thesis_revision_v45/stage_08s/stage8s_results.json`;
  decisions `STAGE_08S_HYPOTHESIS_DECISIONS.csv`; energy decomposition
  `STAGE_08S_ENERGY_DECOMPOSITION.csv`; floors
  `STAGE_08S_STATIC_AND_USEFUL_FLOOR_RESULTS.csv`.
* Scale: identical frozen core to Stage 8U.
* **Verdict: NOT LICENSED** (H-S1 supported; H-S2 fail; H-S3 fail; H-S4 pass).
* Best within-PoCol result: 90.39% block retention vs the no-floor PoCol control with a
  55.05% calculated low-power-state energy reduction relative to the within-run
  power-null.

### Tier 3 — Stage 8R / Stage 8M: historical policy evolution (diagnostic only)
* Stage 8R (`docs/thesis_revision_v45/stage_08r/`): revised predictive controller;
  NOT LICENSED. Trigger counts are decision-observation counts, **not** completed
  reassignments — must never be reported as completed reassignments.
* Stage 8M (`docs/thesis_revision_v45/stage_08m/`, `experiments/.../stage_07m/`): minimal
  baseline; energy claim not licensed. Frozen M03 record is the reproduced-record anchor.

### Tier 4 — Stage 1 normative protocol documents
* `docs/thesis_revision_v45/stage_01/`: protocol definition, state machines, invariants,
  terminology, traceability vectors. Source for the PoCol design chapter's normative
  statements.

### Tier 5 — Earlier thesis evaluation (Stage-6A, macro scale) — retain only when supported
* The draft-44 Chapter 7 currently reports the **Stage-6A frozen 1,890-run** evaluation
  (63 scientific-semantics groups × 30 seeds; 141 TH/s aggregate; 21.5 J/TH; 10,000 s
  horizon; aggregate power 3031.5 W). Its two surviving supported findings:
  * **A1 energy invariant:** total fixed-horizon energy = 8.420833333 kWh for every
    continuous full-participation configuration and every miner count (max rel. dev.
    3.6e-16); **partitioning alone does not reduce energy**. STILL SUPPORTED — consistent
    with the Stage-8U observation that P02's zero-duplicate coordination does not by
    itself lower fixed-horizon hashing energy.
  * **H1 duplicate elimination:** disjoint assignment eliminates exact-input duplicate
    candidate identities among honest miners under the common-template assumption. STILL
    SUPPORTED — reinforced by Stage-8U (P02 duplicate physical evaluations = 0).
* The draft-44 §7.3 throughput narrative ("PoCol performs equally as well as PoW … and
  better at higher miner counts") is from the **legacy BlockSim PoW abstraction**
  (exponential mining-time model, no matched templates). It is **SUPERSEDED** by the
  Stage-8U matched same-template PoW control, which shows PoCol produces fewer blocks
  (67.70% of W01) and longer rounds. It must be bounded/rewritten, not retained as stated.

## 3. Naming and comparator discipline (binding on every integrated statement)

* Algorithm name: **PoCol** / **Proof-of-Collaboration**. No new algorithm name.
* Stage-8U treatment: **the single-handoff useful-work policy within PoCol**.
* Stage-8U controls: **matched same-template PoW control** — W00 population-matched, W01
  active-capacity-matched (artificial). **Never** Bitcoin, the Bitcoin network,
  real-world PoW, or representative Bitcoin mining.
* Stage-8S block retention is relative to the **no-floor PoCol control (S00)**, not PoW.
* Stage-8S / Stage-8U energy reductions are **calculated** low-power-state residency
  reductions relative to the **within-run power-null reference** (8S) or the actual
  executed energy of the **matched PoW control** (8U) — never hardware measurements.

## 4. What Stage 9 does NOT touch

Engine (`Models/PoCol/stage2/*`, `matched_pow.py`, `search.py`, simulator), seeds,
datasets, analysis scripts, figures, statistical decisions, and all historical
Stage-8M/8R/8S/8U evidence remain byte-identical. Stage 9 adds only
`docs/thesis_revision_v45/stage_09/` documents and the new Stage-9 thesis DOCX/PDF
working copies; the authoritative `draft-44-00.docx` is preserved unchanged.
