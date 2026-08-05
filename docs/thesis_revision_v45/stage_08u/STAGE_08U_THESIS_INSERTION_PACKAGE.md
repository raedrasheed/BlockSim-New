# Stage 8U — Thesis Insertion Package

Ready-to-insert material for the thesis revision.  **No thesis DOCX or PDF was edited in
this stage.**  Every number below traces to `STAGE_08U_RUN_DATASET.csv` (60 frozen runs)
and `stage8u_results.json`, both covered by `STAGE_08U_CHECKSUM_MANIFEST.sha256`.

## 1. Terminology to use verbatim

| use this | never write |
|---|---|
| PoCol | (any new algorithm name) |
| the single-handoff useful-work policy within PoCol | "PoCol v2", "improved PoCol", "the new algorithm" |
| matched same-template PoW control | Bitcoin, the Bitcoin network, real-world PoW, a universal PoW model |
| population-matched control (W00) | "the PoW baseline" |
| active-capacity-matched control (W01) — artificial | "the PoW baseline" |

## 2. Headline finding (one paragraph, insertable)

Under a controlled simulator comparison in which a matched same-template PoW control and
PoCol share the same immutable block templates, the same SHA-256 primitive, the same
fixed target and difficulty, the same nonce domain, horizon, seeds, actual hash rates and
power values, the single-handoff useful-work policy within PoCol reduced total energy by
44.95% against the active-capacity-matched control (95% CI [44.87%, 45.02%], exact
p = 0.000488, Holm-corrected) and by 54.86% against the population-matched control, while
committing 139 712 physical SHA-256 evaluations per run with **zero** duplicates against
the control's 1 158 562 evaluations of which 942 371 were duplicates — a work-efficiency
of 1 173 versus 209 accepted blocks per million evaluations.  The policy eliminated
reserve-activation churn entirely (0.00 versus 646.67 activation requests per run under
the Stage-8S baseline) and held reassignment churn at 0.45 per closed round.  It did not,
however, meet its two preregistered operational limits: accepted blocks reached only
67.70% of the capacity-matched control (gate: ≥ 90%) with a 5.22× median round duration
(gate: ≤ 1.10×), and the mean time below the useful-work floor was 23.13 s (gate: ≤ 15 s).
Under the preregistered joint acceptance rule the policy claim is therefore **not
licensed**.

## 3. Results table (insertable as-is)

| scenario | energy (kWh) | blocks | median round (s) | total evals | duplicate evals | blocks per M evals |
|---|---|---|---|---|---|---|
| W00 matched same-template PoW, population-matched | 0.035833 | 249.42 | 0.185 | 1 447 489 | 1 228 115 | 172.4 |
| W01 matched same-template PoW, active-capacity-matched (artificial) | 0.029383 | 241.75 | 0.225 | 1 158 562 | 942 371 | 208.7 |
| P00 PoCol, operational floor disabled | 0.016548 | 178.00 | 1.180 | 152 980 | 0 | 1166.1 |
| P01 PoCol, Stage-8S coarse-reassignment policy | 0.016129 | 164.50 | 1.173 | 140 645 | 0 | 1172.2 |
| P02 PoCol, single-handoff useful-work policy | 0.016175 | 163.67 | 1.174 | 139 712 | 0 | 1173.2 |

Means over 12 fresh paired confirmatory seeds; 300 s horizon; 20 miners; 1600-nonce
domain; difficulty 1000.

## 4. Preregistered decision table (insertable)

| hypothesis | criterion | observed | required | outcome |
|---|---|---|---|---|
| H-U1 churn | reassignments per closed round | 0.4535 | ≤ 1.0 | PASS |
| H-U1 churn | activation requests vs P01 | 0.00 vs 646.67 | fewer | PASS |
| H-U1 churn | incomplete activations vs P01 | 0.00 vs 425.00 | fewer | PASS |
| H-U2 service | accepted-block ratio vs W01 | 0.6770 | ≥ 0.90 | **FAIL** |
| H-U2 service | median-duration ratio vs W01 | 5.2190 | ≤ 1.10 | **FAIL** |
| H-U3 energy | relative energy reduction vs W01 | 0.4495 | ≥ 0.20 | PASS |
| H-U3 energy | bootstrap CI lower bound | 0.4487 | > 0 | PASS |
| H-U5 operation | mean duration below useful floor | 23.13 s | ≤ 15 s | **FAIL** |
| H-U5 operation | all nonterminal/duplicate/post-round/rewind counts | 0 | 0 | PASS |
| — | all deterministic integrity gates, 60/60 runs | pass | pass | PASS |
| **joint rule** | H-U1 ∧ H-U2 ∧ H-U3 ∧ H-U5 ∧ integrity | — | — | **NOT LICENSED** |

## 5. Figures available for insertion

FIG01–FIG18 under `figures/`, each as SVG (vector, for print), 300-dpi PNG, source CSV,
caption markdown, metadata JSON and SHA-256 checksum.  `POW_POCOL_FIGURE_INDEX.md` lists
them; `POW_POCOL_CAPTION_PACKAGE.md` holds the caption text ready to paste.  Suggested
minimum set for the chapter: FIG01 (energy), FIG03 (blocks), FIG06 (evaluations with the
duplicate contrast), FIG12 (energy–service plane), FIG18 (decision dashboard), and FIG17
for the descriptive policy-evolution narrative.

## 6. Mandatory framing sentences

Include all of these near the results:

1. "This is a controlled simulator comparison under matched templates, target,
   difficulty, horizon, seeds, hash rates and power values; it is not a measurement of
   any deployed network."
2. "W00 and W01 answer different matching questions — physical population versus initial
   active mining capacity — and are reported separately, never merged."
3. "W01 is an artificial capacity-matched construction with no deployed counterpart."
4. "Comparisons with the Stage-8M, Stage-8R and Stage-8S results are descriptive only:
   each stage used its own disjoint fresh seed registry, and no cross-stage inferential
   statistic is computed."
5. "The within-run power-null counterfactual is an accounting construct, not an
   executable PoW control."
6. "Reserve and wake savings are reported separately from range-idle savings."
7. "No claim of broad PoW superiority, security superiority or incentive advantage is
   made."

## 7. Relationship to the historical stages (descriptive only)

Stage 8M established the minimal baseline; Stage 8R the predictive static-floor
controller (not licensed); Stage 8S the useful-floor coarse-reassignment policy (not
licensed: block ratio 0.9039 passed, below-useful 28.71 s and churn failed).  Stage 8U's
single-handoff policy removes the churn failure completely and improves the useful-floor
duration to 23.13 s, but does not reach the 15 s limit and does not meet the service gate
against the matched PoW control.  All four stages are honest, preregistered, not-licensed
outcomes of a single research line; the Stage-8M/8R/8S records are unmodified and remain
valid historical evidence.

## 8. Suggested honest framing for the contribution

The defensible contribution is **not** "PoCol beats PoW".  It is: under exactly matched
work semantics, partitioned cooperative search attains substantially lower energy and an
order-of-magnitude higher work-efficiency per accepted block than uncoordinated
full-domain search, at the cost of longer per-round latency and fewer blocks within a
fixed horizon; and a preregistered operating policy that removes activation churn
entirely is achievable, while the operational useful-work floor and the service parity
targets set for this cycle were not met.  The negative results are part of the
contribution and are reported without softening.
