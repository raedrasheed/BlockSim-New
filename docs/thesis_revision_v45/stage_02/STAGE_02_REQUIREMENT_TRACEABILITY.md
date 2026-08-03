# Stage 2B — Requirement Traceability

Maps every Stage-2B requirement (S2B-1 … S2B-8) and acceptance gate to the executable code
that realises it and the test(s) that prove it. Algorithm: PoCol. Mechanism: the idle
policy within PoCol. No dynamic difficulty in the confirmatory core.

## S2B-1 — Success coupled to the fixed target

| Sub-requirement | Code | Test |
|---|---|---|
| Success iff `sha256_int(header,nonce) <= target` | `search.Template.is_solution`, `search.sha256_int`; `simulator._first_solution_in` | SCI-6, `test_s2b1_target_is_used_not_stored_and_ignored` |
| Template + target fixed for the round; no dynamic difficulty | `search.make_template`, `target_for_difficulty`; `_handle_template_commit` | SCI-6 |
| Zero / one / many solutions + full-domain exhaustion | `search.target_for_difficulty` (incl. target 0); `_handle_range_exhaust` no-block abort | SCI-7, `test_s2b1_zero_and_multi_solution_outcomes_exist` |
| Winner = first valid solution in sim time | `_handle_hash_work` (acceptance at winner completion time) | E2E-1, SCI-8 |
| Easier target ⊇ harder; difficulty changes distribution | `target_for_difficulty`, `success_probability` | `test_s2b1_easier_target_is_superset`, `…_difficulty_changes_success_distribution` |
| No sampled/placed winner; no `solution_after_units` | removed from `search.py` / `config.py` | (absence) |

## S2B-2 — Causal hash-work accounting

| Sub-requirement | Code | Test |
|---|---|---|
| Do not count future work at batch start | `_seat_hash_work` mutates nothing (read-only timing scan) | SCI-4, SCI-5 |
| Planned batch-completion event (design B) | `_seat_hash_work` seats at completion time; `_handle_hash_work` commits at dispatch | SCI-5 |
| Commit only work whose completion has arrived; winner uses exact completion time | `_handle_hash_work` (commit through first solution) | SCI-4, SCI-8 |
| Round-closed-first commits zero | `_handle_hash_work` round-terminal guard | SCI-4 |
| No nonce counted after `round_terminal_time` + causal assertion | `_handle_hash_work` `assert searched_count <= floor(rate*(min(rtt,now)-active_start))+TOL` | SCI-4 |

## S2B-3 — Complete immutable hash-event identity

| Sub-requirement | Code | Test |
|---|---|---|
| Payload carries round/template/assignment/version/miner/cursor/generation | `events.DESCRIPTORS` (HashWorkEvent, RangeExhaustEvent); `_seat_hash_work`, `_seat_range_exhaust` | SCI-5 |
| Pre-mutation verification of all identity fields | `simulator._verify_hash_identity` | SCI-5 |
| Replay/superseded → no-effect | `search_generation` bump + `_verify_hash_identity` | SCI-5 |

## S2B-4 — Executable nonce-evaluation ledger

| Sub-requirement | Code | Test |
|---|---|---|
| Per-commit interval record with full provenance | `context.EvaluationRecord`; appended in `_handle_hash_work` | SCI-2, SCI-4, SCI-5 |
| Zero duplicate evaluations (from the ledger) | disjoint ranges + per-miner cursor | SCI-2 |
| No out-of-range / post-round evaluation | ledger `completion_time` ≤ `round_terminal_times` | SCI-4 |
| `searched_count == ledger count` per miner | `final_searched` vs ledger sums | SCI-5 |
| Every active miner's work matches elapsed hash time | causal assertion + `max_search_time_residual` | SCI-3, SCI-5 |

## S2B-5 — Genesis failure through the one closure owner

| Sub-requirement | Code | Test |
|---|---|---|
| Invoke the one abort/closure owner on genesis failure | `_abort_round_initialise` → `RoundAbort` → `_close_and_publish` | TV325, TV326, TV335 |
| Cancel previously-seated genesis events; terminalise EXACT_ROUND requests; publish + seat next | `_close_and_publish` | TV325, TV335 |
| Exact TV325 sequence (3rd seat fails → abort → all terminal, no leak) | `genesis_seat_fail_at` hook + closure | TV325 |
| Duplicate genesis leaves zero pending / zero queued registrations | admission-failure path via closure | TV335 |

## S2B-6 — Correct energy result labels

| Sub-requirement | Code | Test |
|---|---|---|
| `matched_control_kwh` → `continuous_all_active_control_kwh` (accounting reference) | `adapter.results_schema` | `test_adapter_returns_declared_schema` |
| Constructed matched experiment exposed separately | `adapter.matched_identity_experiment_schema`; `energy_experiment.run_energy_experiment` | `test_adapter_returns_declared_schema`, SCI-8, SCI-9 |
| Constructed saving not reported as general PoCol saving | schema note; separate key | `test_adapter_returns_declared_schema` |

## S2B-7 — Executable-ledger scientific tests + TV/E2E

| Test | Semantics | File |
|---|---|---|
| SCI-1 | simulator assignment ranges disjoint + cover active domain | `test_stage2_scientific.py` |
| SCI-2 | ledger zero duplicate `(TemplateID, nonce)` | ″ |
| SCI-3 | every active miner has committed work or justified zero-work | ″ |
| SCI-4 | no ledger completion after round end | ″ |
| SCI-5 | `searched_count == ledger count` per miner | ″ |
| SCI-6 | fixed-target validation accepts exactly `digest <= target` | ″ |
| SCI-7 | deterministic no-solution template → full-domain exhaustion | ″ |
| SCI-8 | matched CONTROL & POCOL_IDLE same template/target/evals/winner/end | ″ |
| SCI-9 | `P_idle = P_active` → zero saving | ″ |
| SCI-10 | canonical A1 = 8.420833333 kWh | ″ |
| TV325–TV338 | semantic vectors (TV325 + dup-genesis corrected per S2B-5) | `test_stage2_semantic_vectors.py` |
| E2E-1…E2E-5 | full multi-round path, abort→second round, no leakage, horizon reconcile, partial finalization | `test_stage2_e2e.py` |

## S2B-8 — Evidence and final gate

| Artifact | Path |
|---|---|
| Implementation report | `STAGE_02_IMPLEMENTATION_REPORT.md` |
| Requirement traceability | `STAGE_02_REQUIREMENT_TRACEABILITY.md` (this file) |
| Test report | `STAGE_02_TEST_REPORT.md` |
| Known limitations | `STAGE_02_KNOWN_LIMITATIONS.md` |
| Checksum manifest | `STAGE_02_CHECKSUM_MANIFEST.sha256` |
| Machine pytest log / JUnit XML / metrics | `evidence/pytest_stage2b.log`, `pytest_stage2b.junit.xml`, `stage2b_metrics.json` |
| CI workflow | `.github/workflows/stage2b-pocol-tests.yml` |

## Acceptance gates → evidence

| Gate | Evidence |
|---|---|
| 1 success by fixed target/difficulty | SCI-6, S2B-1 tests |
| 2 zero-solution full-domain exhaustion executable | SCI-7 |
| 3 difficulty not stored-but-unused | `test_s2b1_target_is_used_not_stored_and_ignored`, `difficulty` removed as unused (`solution_after_units` deleted) |
| 4 hash work committed causally at completion time | S2B-2 design B, SCI-4/5 |
| 5 no work counted after round end | causal assertion, SCI-4 (post-round count 0) |
| 6 every hash event carries full identity | S2B-3, `_verify_hash_identity` |
| 7 ledger proves zero duplicate evaluations | SCI-2 (dup count 0) |
| 8 searched counts equal ledger counts | SCI-5 (0 mismatches) |
| 9 genesis failure leaves no live seat/request | TV325 |
| 10 duplicate genesis leaves no pending state | TV335 |
| 11 energy controls labelled correctly | S2B-6, adapter test |
| 12 matched identity + A1 tests pass | SCI-8/9/10 |
| 13 all semantic, E2E, scientific tests pass | 37 passed |
| 14 GitHub Actions success | `.github/workflows/stage2b-pocol-tests.yml` |
| 15 Stage 1 untouched | no `docs/thesis_revision_v45/stage_01/` change |
| 16 Stage 3 not begun | out of scope |
