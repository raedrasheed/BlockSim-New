# Stage 8U — Implementation Report (COMMIT 1)

**Branch:** `thesis-v45-pocol-stage8u-single-handoff-pow-comparison`, from the exact
remote HEAD `bb588e881b667ed021d6cdbbda9971a14a0ae259` of
`thesis-v45-pocol-stage8s-useful-floor-coarse-reassignment` (recorded before any edit;
clean worktree; 235 accepted tests green; Stage-8S checksum manifest verified;
difficulty 1000 with its fixed target verified frozen; matplotlib 3.11.1 present).

This commit contains: the Phase-0 PoW baseline audit (read-only, written before any
engine change), the ADDITIVE matched same-template PoW control, the new
`USEFUL_FLOOR_SINGLE_HANDOFF` controller mode (U1–U5), the frozen deterministic
figure/table core, and tests U-TEST-01..22.  No preregistration content, no seeds beyond
the Stage-8U PILOT seed used in tests, no confirmatory execution.

## 1. Matched same-template PoW control (`Models/PoCol/stage2/matched_pow.py`)

New additive module; no legacy PoW file was modified (audit §7).  Matching guarantees:

* identical per-round template stream: `make_template(f"round-{k}", difficulty, D,
  template_seed + k)`, k = 1, 2, ... — the engine's own rule verbatim (same
  `TemplateID`s, same header bytes, same fixed target);
* identical SHA-256 primitive (imports the accepted `search.py` objects — U-TEST-02
  asserts module identity), fixed difficulty/target, domain 1600, horizon 300 s, batch
  25, actual per-miner rates, power values;
* identical block-acceptance point: first valid target-coupled solution by simulation
  time, at the winning nonce's exact per-nonce completion time (the engine's S2B-2
  rule), deterministic tie-break (time, MinerID, nonce);
* identical stale-cancellation discipline at acceptance: work not committed strictly
  before the acceptance time performs no effect; `post_round_evaluation_count == 0` by
  construction and recorded.

The treatment difference is exactly the PoW search discipline: every mining node
searches the FULL domain independently from a deterministic seed-derived offset
(`SHA256("pow-offset|{master_seed}|{round}|{miner}")[:8] mod D`) with wraparound;
overlap is allowed and measured (`total/unique/duplicate_physical_evaluations`, exact
circular-arc union).  All round timing uses exact rational arithmetic
(`fractions.Fraction`) — byte-deterministic across replays and platforms.

Declared closure rules (recorded in the module docstring; will be restated in the
preregistration): BLOCK at the exact first-solution time; EXHAUSTED (no solution in the
domain) at the FIRST miner's full-domain coverage — its coverage proves the domain
empty, the protocol-level analogue of the engine's exhaustion closure and the
PoW-favourable minimal rule; HORIZON truncation at 300 s.  Oracle scans determine
timing/closure only and are never counted as physical work (the engine's own planning
scan precedent).

Energy/residency: mining nodes hold ACTIVE_HASHING for the whole horizon (PoW never
idles); W01 standby nodes hold RESERVE_STANDBY at `P_reserve`.  Both identities are
computed and their residuals recorded (`energy_identity_residual_j` ≤ 1e-8 observed
1.5e-11; `residency_partition_residual_s` exactly 0).

Two never-merged scenario kinds: `POW_POPULATION_MATCHED` (all 20 nodes mine) and
`POW_ACTIVE_CAPACITY_MATCHED` (16 initial-active-capacity nodes mine, 4 standby nodes
at `P_reserve` — an explicitly labelled artificial capacity-matched control).

## 2. `USEFUL_FLOOR_SINGLE_HANDOFF` mode (U1–U5)

Additive mode in `refinement.py` / `context.py` / `simulator.py` / `adapter.py`; every
existing mode is untouched (`LEGACY_REACTIVE` default; U-TEST-01 reproduces the frozen
Stage-8M M03 record, the Stage-8R R02 row and the Stage-8S S03 row bit-exactly).

* **U1 — RoundHandoffEpoch** (`refinement.RoundHandoffEpoch`): all directed fields
  (identity, generation, donor/receiver, source/receiver assignment ids, original
  suffix, both chunks, both predicted makespans, status, terminal time, disposition);
  statuses OPEN/COMMITTED/COMPLETED/CANCELLED/FAILED/ROUND_CLOSED.  At most ONE epoch
  per round (`handoff_by_round` registry); a second attempt is an exact replay no-op
  that returns the existing epoch (`duplicate_handoff_prevented_count`); closure
  terminalises the epoch; an epoch never crosses rounds.  All six directed metrics are
  reported in every mode (zeros elsewhere).
* **U2 — deterministic selection** (`_handoff_eligible_receiver` /
  `_handoff_eligible_donor`): receiver = FASTEST already-awake primary
  (LOW_POWER_LISTEN, own accepted range completed, no live reassignment, same
  round/template, identity-checked assignment); donor = ACTIVE miner with the LARGEST
  accepted unsearched suffix ≥ 2 whole batches, identity-checked, no live
  reassignment.  Ties break on MinerID; no future-solution information (observables
  only — the same inputs the coarse mechanism was allowed).
* **U3 — one proportional split** (`_maybe_single_handoff`): R = donor_range_end −
  donor_accepted_frontier; receiver size by the accepted integer apportionment
  (floor + largest remainder on the actual rates, donor first on ties), clamped so both
  chunks hold ≥ 1 whole batch (R ≥ 2·batch makes this always feasible); exactly TWO
  contiguous disjoint chunks whose union is the original suffix; the deterministic
  benefit gate requires predicted post-split makespan STRICTLY below donor-alone (else
  the epoch is CANCELLED and nothing is reassigned); donor keeps the first chunk;
  ATOMIC apply — receiver seats first, donor shrinks last under a version bump, any
  failure restores the exact before-image (epoch FAILED).  One nonce, one live
  assignment; no rewinds; no duplicates; no post-round evaluations.  This single split
  is the ONLY reassignment allowed in the round.
* **U4 — single reserve-wake fallback** (`_single_reserve_admission` + a
  `max_batch_reserves=1` bound on the accepted batch-seating path): the handoff is
  tried FIRST on both the reactive and predictive decision paths; at most ONE reserve
  wake request per round (`handoff_reserve_by_round` guard, enforced again inside the
  seating routine); before seating the accepted all-or-none transaction atomically
  claims the exact UNCLAIMED reserve slice; the wake is REJECTED when no bound work
  exists (`reserve_wake_rejected_no_bound_work`), when an awake primary could take
  ceded work through a handoff (`reserve_wake_rejected_awake_receiver_available`), or
  when the observable productive window (max remaining/rate over active primaries) does
  not exceed wake latency plus one batch-completion time
  (`reserve_wake_rejected_short_useful_window`).  Given a bound non-empty slice and a
  sufficient window the wake strictly reduces the predicted useful makespan (the slice
  is otherwise unowned at every observable horizon) — recorded with the checks.  Never
  a multi-reserve batch.  Lifecycle metrics: `single_reserve_requests_seated /
  completed / incomplete` (settled at round closure).
* **U5 — no metric relabelling:** WAKING still contributes zero to `H_effective`; the
  static floor is never lowered or redefined; `duration_below_static_floor`,
  `duration_below_useful_floor`, `static_floor_deficit_area` (dataset field) and
  `useful_floor_deficit_area` remain independently computed and reported.  The
  REPORTED useful availability still counts all eligible awake receivers
  (counterfactual, comparable across modes); only the DECISION reference caps
  receivers at the one the single-handoff mechanism can actually serve (zero once the
  round's epoch is consumed) — via the additive `max_receivers` parameter of
  `h_useful_available`.

## 3. Frozen figure/table core (`experiments/thesis_revision_v45/stage_08u/figures_8u.py`)

Deterministic primitives the COMMIT-3 chart generator must use: canonical byte-stable
table serialisation, order-independent figure metadata with no timestamps or
environment state, the frozen FIG01..FIG18 specification list, and the Okabe-Ito
colour-blind-safe palette with fixed scenario colours.  U-TEST-22 gates byte identity.

## 4. Behavioural evidence (pilot seed 0, not confirmatory)

One PILOT-seed P02 run: 230 rounds, 171 accepted, 96 handoff epochs (96 committed, 71
completed, 0 failed, 0 cancelled), 1 564 replay no-ops, ZERO reserve wakes seated
(fallback rejected by the U4 admission checks), zero duplicates, zero nonterminal
records, `duration_below_useful_floor` 20.5 s.  Matched controls on the same seed:
W00 298 rounds / 233 blocks, 1 451 895 total / 202 308 unique / 1 249 587 duplicate
evaluations, 0.035833 kWh; W01 285 rounds / 222 blocks, 0.029383 kWh.  These pilot
numbers freeze nothing and license nothing; the honest early signal that the H-U2
service gates may fail against W01 is noted and will be evaluated only on the
preregistered confirmatory seeds.

## 5. Scope discipline

SHA-256 evaluation semantics, the accepted target, fixed difficulty, nonce-domain
semantics, physical hash rates, the immutable evaluation ledger and the
accepted/actual/physical frontier authorities are unmodified (U-TEST-19 and the 235
retained accepted tests).  Historical Stage-8M/8R/8S artifacts are byte-identical.  No
CI was created or waited for.  Thesis DOCX/PDF untouched.
