# Stage 6M — Structural Pilot Report

Two PILOT seeds (indexes 0, 1; provably disjoint from every confirmatory seed) x
{M01, M02, M03} = 6 runs. Structure and runtime only; **no energy effect was computed,
recorded or inspected**, and `test_s6m_06` asserts the pilot output contains none.

| scenario | seed idx | status | wall (s) | rounds | gates |
|---|---:|---|---:|---:|---|
| M01_HET_IDLE | 0 | COMPLETED | 1.33 | 227 | PASS |
| M01_HET_IDLE | 1 | COMPLETED | 1.28 | 228 | PASS |
| M02_HOM_IDLE | 0 | COMPLETED | 1.03 | 204 | PASS |
| M02_HOM_IDLE | 1 | COMPLETED | 0.99 | 201 | PASS |
| M03_HET_IDLE_FLOOR | 0 | COMPLETED | 1.61 | 193 | PASS |
| M03_HET_IDLE_FLOOR | 1 | COMPLETED | 1.82 | 189 | PASS |

All eleven structural gates pass on every run: completion; >= 100 rounds (min observed 189);
non-empty evaluation ledger; `duplicate_nonce_count = 0`;
`post_round_evaluation_record_count = 0`; residency reconciliation; M03 records security-floor
observations; M03 seats reserve activations; zero nonterminal activation requests; wall time
<= 10 min (max observed 1.82 s); peak RSS <= 4 GB (max observed well under 1 GB).

Machine-readable record: `experiments/thesis_revision_v45/stage_06m/pilot/structural_pilot_results.json`.
The pilot validated structure and runtime only; the design was frozen without change.
