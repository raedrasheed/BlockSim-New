# Stage 5B1 — Semantic Duplication Audit

Builder: `experiments/thesis_revision_v43/build_matrix_5b1.py`
Hashing: `experiments/thesis_revision_v43/hashing.py`
Output: `STAGE_05B1_FINAL_MATRIX.csv`,
`results/thesis_revision_v43/stage_05b1/raw/matrix_5b1_summary.json`

## 1. Three-tier hashing

| Hash | Includes | Purpose |
|------|----------|---------|
| `configuration_hash` | every configuration + labelling field (incl. `interpretation_labels`, `hypothesis_id`) | distinguishes every *planned* row |
| `execution_semantics_hash` | only fields that change **executable behaviour or measured output**; drops interpretation-only labels and parameters proven inactive | one hash per *physical execution* |
| `analysis_group_hash` | execution model + hypothesis + matrix class + design factors | groups rows into planned analyses |

Two proven-inactive drops:
1. **Interpretation labels** (`B3` vs `C1`) never change execution ⇒ dropped from
   `execution_semantics_hash` ⇒ B3 and C1 collapse.
2. **`idle_power_ratio` when idle is semantically inactive**
   (`idle_semantically_active` = false: homogeneous equal-range with μ≥1) ⇒ dropped,
   so idle-ratio variants of a zero-idle baseline do not create phantom runs.

## 2. The naive plan and the audit's reductions

The **naive** plan enumerates every interpretive scenario the thesis discusses as
an independent intended run. Because a reader cannot know a priori that B3 and C1
are the same execution, the naive plan lists them separately over the whole grid.

| Step | Count |
|------|-------|
| Naive planned rows (B3 and C1 separate) | **2 760** |
| − exact duplicates (`configuration_hash`) | −0 |
| − **B3 ≡ C1 semantic merge** (`execution_semantics_hash`) | **−870** |
| − other semantic duplicates | −0 |
| **Final Stage-5B2 run count** | **1 890** |

After the audit:
- distinct `configuration_hash` = 1 890 (every surviving row is a distinct plan),
- distinct `execution_semantics_hash` = 1 890 (**every surviving run is a unique
  physical execution** — no hidden redundancy remains),
- distinct `analysis_group_hash` = 63 (planned analysis groups).

870 rows carry the merged label `B3;C1` and record `reused_by_hypotheses`; one
physical run serves both the energy (B3) and collaboration (C1) interpretations.
No physical simulation is counted twice as independent data (pseudoreplication
guard, consistent with the frozen preregistration §4).

## 3. Why "0 other semantic duplicates" is the correct result

The sensitivity classes are **orthogonal by construction** — each varies exactly
one active factor off a baseline the CORE class does not occupy (μ, propagation
delay, inactive fraction, heterogeneity, allocation, idle ratio). No two surviving
rows share an execution-semantics hash. The audit therefore *confirms* the matrix
is already minimal apart from the B3≡C1 identity; it does not manufacture a
reduction by first inflating and re-collapsing arbitrary rows.

## 4. Ceiling

Final 1 890 runs ≤ hard ceiling **3 500** (`under_ceiling = true`). Validation-only
rows in the executable matrix: 0 (validation runs are a separate bounded set, not
part of the 1 890).

## 5. Distribution of the final matrix

By scenario: B0 150, B1 150, B2 150, B3_C1 870, C2 570.
By class: CORE 600, CORE_C2 150, SENS_IDLE 300, SENS_HETERO 240, SENS_MU 120,
SENS_INACTIVE 180, SENS_DELAY 240, EXPLORATORY 60.

This reproduces the Stage-5A frozen scenario/class distribution exactly, now
derived through a transparent, re-runnable audit.
