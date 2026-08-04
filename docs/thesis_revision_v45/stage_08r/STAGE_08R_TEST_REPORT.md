# Stage 8R — Test Report (implementation gate for COMMIT 1)

Executed locally (no CI created or waited for):

| suite | result |
|---|---|
| accepted engine suite `tests/thesis_revision_v45/stage2/` | **195 passed** |
| Stage-8R controller suite `tests/thesis_revision_v45/stage_08r/` | **18 passed** (R-TEST-01..18) |
| Stage-6M validation suite | 8 passed, **1 expected failure**: `test_s6m_08` byte-identity of the engine vs the Stage-5D digests — fails BY CONSTRUCTION on this branch because the Stage-8R directive authorizes engine modification; the Stage-6M evidence itself is untouched and its checksum manifests still verify |

## R-TEST map

| test | requirement | proof style |
|---|---|---|
| R-TEST-01 | LEGACY_REACTIVE reproduces the frozen Stage-8M M03 run (same seed) | exact equality on rounds, accepted, bit-equal energy and below-floor duration, activations, unattainable count, ledger entries; zero controller registries |
| R-TEST-02 | WAKING contributes zero to H_effective | fixture: identical state, ACTIVE_HASHING → 100 Hz, WAKING → 0 |
| R-TEST-03 | WAKING capacity appears only in H_pipeline | fixture: H_effective 0, H_pipeline 250 |
| R-TEST-04 | one episode never owns two simultaneous live batches | full-run invariant: for consecutive batches of any episode, every request of the earlier batch COMPLETED before the later batch seated |
| R-TEST-05 | repeated observations replay-idempotent | request↔batch bijection; duplicate-prevention counter > 0; observations ≫ batches |
| R-TEST-06 | hysteresis prevents 0.78/0.82 oscillation | reactive opens strictly below 0.78 × H0; every RECOVERED closure has a ≥ 0.82 × H0 observation; no reactive open inside the deadband |
| R-TEST-07 | cooldown blocks replacement batches | consecutive same-episode batches closer than the cooldown must show physical capacity below the frozen trigger at the second seat |
| R-TEST-08 | predictive activation precedes the reactive trigger | ≥ 1 predictive batch seated while physical capacity was still ≥ 0.78 × H0 |
| R-TEST-09 | prediction uses observables, not a future oracle | AST-stripped source scan (no winning_nonce / contained_solution / header_bytes / sha256 / random / round_terminal_time) + fixture: H_future depends only on cursor, range and rate vs lookahead |
| R-TEST-10 | a sufficient live batch prevents another | duplicate-prevention counter > 0; no live batch survives any round |
| R-TEST-11 | minimum-cardinality selection deterministic | repeated calls identical; [10,100] with need 90 selects only the 100 |
| R-TEST-12 | round closure leaves zero live episodes/requests | all episodes terminal with closed_at; all batches TERMINAL; all requests terminal |
| R-TEST-13 | target/difficulty unchanged in every mode | difficulty 1000 and identical `target_for_difficulty` across all 4 modes |
| R-TEST-14 | duplicate nonce count zero (honest scenarios) | R02 and R03 full runs |
| R-TEST-15 | post-round evaluation counts zero | accepted Stage-5D audit on R02 and R03 runs |
| R-TEST-16 | energy identity + residency partition exact | residuals ≤ 1e-8 J / 1e-9 s on R02 and R03 runs |
| R-TEST-17 | exploratory reassignment: no overlap, no rewind | R03 run: ≥ 1 controller suffix reassignment; frontier rewinds 0; overlapping slices 0; all lease/reassignment requests terminal; one trigger per suffix lineage |
| R-TEST-18 | stale predictive state has no next-round effect | every episode/batch/request/prediction bound to its round; closures ≤ round terminal time |

Every executed simulation in the suite uses a PILOT seed, except R-TEST-01 which — as the
directive requires — re-executes the frozen M03 confirmatory seed solely to prove exact
reproduction of the already-frozen record.
