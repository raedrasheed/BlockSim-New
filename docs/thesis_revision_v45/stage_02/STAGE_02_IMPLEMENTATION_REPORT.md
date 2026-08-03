# Stage 2B — PoCol Target-Coupled / Causal-Search / Genesis-Rollback Correction

Final Stage-2 scientific-core correction of the existing PoCol package after independent
final review of Stage 2A. This is a focused correction of the existing package (not a
rewrite).

- **Branch:** `thesis-v45-pocol-stage2b-target-causal-search-genesis-rollback-lock`
- **Parent commit (branch base):** `64bca1d18554016a8c6aa9688255ff1fb3eb844f`
- **Frozen Stage-1 normative baseline:** `8c9902e57c0d6557329bc742e39a50ed31b86170` (untouched)
- **Package:** `Models/PoCol/stage2/` (`config`, `events`, `context`, `driver`, `search`,
  `simulator`, `energy_experiment`, `adapter`, `demo`)
- **Tests:** `tests/thesis_revision_v45/stage2/` — **37 passing** (TV325–TV338, E2E-1…E2E-5,
  SCI-1…SCI-10, S2B-1 target tests, adapter). Machine evidence:
  `evidence/pytest_stage2b.log` + `pytest_stage2b.junit.xml` + `stage2b_metrics.json`.
- **Demo:** `python -m Models.PoCol.stage2.demo`

Algorithm: **PoCol**. Mechanism: **the idle policy within PoCol** (post-range low-power
residency; never nonce partitioning). **No dynamic difficulty** in the confirmatory core.

---

## S2B-1 — Success coupled to the actual fixed target (`search.py`)

A nonce succeeds iff `sha256_int(header, nonce) <= template.target`, with
`target = target_for_difficulty(difficulty) = floor((2^256 − 1) / difficulty)`. The
without-replacement winner sampler and `solution_after_units` are **removed** — no
stored-but-unused success field remains. `SUCCESS_MODEL =
"TARGET_COUPLED_SHA256_DIGEST_LEQ_TARGET"`. The finite domain genuinely admits **zero,
one, or many** solutions and **full-domain exhaustion with no block**; the winning block
is the first valid solution reached in simulation time under the event-ordering contract.
Tests: `test_s2b1_easier_target_is_superset`, `…_difficulty_changes_success_distribution`,
`…_target_is_used_not_stored_and_ignored`, `…_zero_and_multi_solution_outcomes_exist`,
SCI-6, SCI-7.

## S2B-2 — Causal hash-work accounting (`simulator.py`, design B)

`_seat_hash_work` plans a batch-completion event but **mutates nothing**; its read-only
scan determines only the event's completion time (the winning nonce's exact completion
time if a solution lies in the planned batch, else the full-batch completion time).
`_handle_hash_work` commits the interval `[cursor_start, commit_end)` **only at dispatch**
(the completion time), advances the cursor / `searched_count`, appends the ledger record,
and asserts the causal bound

    searched_count <= floor(hash_rate * (min(round_terminal_time, completion_time)
                                         − active_start)) + 1   (declared tolerance)

so no work is counted before its completion time and **no nonce is counted after round
end** (a batch whose round already closed commits zero). Measured maximum searched-count
vs elapsed-time residual: **5.0e-12** (confirmatory run). Tests: SCI-4, SCI-5.

## S2B-3 — Complete immutable hash-event identity (`events.py`, `simulator.py`)

`HashWorkEvent` and `RangeExhaustEvent` payloads carry `RoundID_at_seat`,
`TemplateID_at_seat`, `AssignmentID`, `assignment_version`, `MinerID`, `cursor_start`,
`cursor_end`/planned, and `expected_search_generation`. `_verify_hash_identity` checks all
of them (round, template, assignment exists + exact version, owner, `cursor_start ==
current cursor`, generation current) before any mutation; `search_generation` bumps on
every commit so a replayed or superseded event returns a no-effect disposition.

## S2B-4 — Executable nonce-evaluation ledger (`context.py`, `simulator.py`)

`EvaluationRecord` records every committed contiguous interval with `RoundID`,
`TemplateID`, `MinerID`, `AssignmentID`, `assignment_version`, `[interval_start,
interval_end)`, `completion_time`, solution outcome, and `EventRef`. The executable ledger
is the authority for the ledger tests: zero duplicate `(TemplateID, nonce)` entries, no
out-of-range or post-round evaluation, and `searched_count == ledger count` per miner
(all measured exactly 0 discrepancies over 52,795 evaluations in the confirmatory run).

## S2B-5 — Genesis failure through the ONE round-closure owner (`simulator.py`)

`_abort_round_initialise` routes every genesis admission failure, genesis seat failure,
duplicate-genesis configuration, and template-commit seat failure through `RoundAbort` →
`_close_and_publish`: previously-seated `MinerRegisterEvent`s are cancelled, all
PENDING/SEATED EXACT_ROUND requests terminalise, the terminal round is published, and the
next round is seated when legal. TV325 executes first-seat-ok / second-seat-ok /
third-seat-fails → round aborts, both seated events CANCELLED, all three requests
terminal, nothing leaks. TV335 leaves zero PENDING requests and zero QUEUED genesis
registrations.

## S2B-6 — Correct energy result labels (`adapter.py`, `energy_experiment.py`)

The adapter reports the run's continuous full-participation reference as
`continuous_all_active_control_kwh` (an accounting reference, NOT a matched CONTROL
simulation) — it is never presented as a general PoCol idle-policy saving. The constructed
matched CONTROL-vs-POCOL_IDLE identity experiment is exposed **separately** under
`matched_identity_experiment` and labelled "not a general PoCol saving". The experiment is
target-coupled (real `digest <= target`), deterministically selects a slow-winner /
fast-idler scenario, and validates `E_i = P_active·t_active + P_idle·t_idle` and
`ΔE_i = t_idle·(P_active − P_idle)` (max residual **7.1e-15 J**; zero saving when
`P_idle == P_active`). `RESULT_SCHEMA_VERSION = "stage2b.1"`.

## S2B-7 — Executable-ledger scientific tests + TV/E2E fixes

SCI-1…SCI-10 are driven by the ACTUAL simulator ledger/provenance (ranges, ledger,
completion times, searched counts, target validation, zero-solution exhaustion, matched
identity, A1). TV325–TV338 retained (TV325 + duplicate-genesis corrected per S2B-5);
E2E-1…E2E-5 retained against the target-coupled core. See
`STAGE_02_REQUIREMENT_TRACEABILITY.md` and `STAGE_02_TEST_REPORT.md`.

## Mandatory multi-round execution path (real target-coupled search)

    RunInitialise -> first-round bootstrap -> genesis admission (rollback via closure owner)
    -> TemplateCommit (immutable Template, fixed target) -> participant preparation
    (disjoint ranges; reserve held at P_listen) -> StartWake -> WakeCompleteEvent
    -> ACTIVE_HASHING -> planned batch-completion HashWorkEvent for EVERY active miner
    (real SHA-256; digest<=target) -> acceptance (first valid solution) OR range exhaustion
    -> idle OR no-block round abort -> closure -> next-round bootstrap -> ...
    -> horizon OR partial termination.

A confirmatory 8-miner / 150 s run executes **79 rounds** (56 accepted, 22 no-block),
reconciles residency, records **52,795** ledger evaluations with **0** duplicates and
**0** post-round evaluations, and yields run energy `0.00345 kWh` vs the continuous
all-active reference `0.00717 kWh`.

## Scope

No Stage-1 normative document is modified; the Stage-1 baseline stays frozen at `8c9902e`.
Stage 2B modifies the Stage-2 package, updates its tests, and refreshes this evidence set
only.
