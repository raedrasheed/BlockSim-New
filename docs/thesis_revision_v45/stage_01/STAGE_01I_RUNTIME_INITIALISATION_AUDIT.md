# Stage 1I — Runtime-Initialisation Audit (I-04)

This audit confirms correction **I-04** in the **PoCol** Stage-1 pseudocode: `RoundInitialise`
EXPLICITLY initialises and RETURNS every normative runtime registry, so none exists only as an
implicit global, and the per-round versus per-run scope of each registry is defined. It is a
structural audit of the specification text (`STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.7d, §0.8, §0.9, §1,
§9; `STAGE_01_ROUND_STATE_MACHINE.md` §3.12); no protocol property (energy, security, fairness) is
claimed or evaluated here. The mechanism under review is **the idle policy within PoCol**; no new
consensus feature is introduced. The A1 baseline (`8.420833333 kWh`) is unchanged — this correction
touches only initialisation and scoping of runtime bookkeeping, not any power-time term.

## 1. Corrected-away condition

Previously a runtime registry could be assumed to exist as an ambient global, readable by a handler
before any procedure had demonstrably created it, and with no stated reset scope — leaving it
undefined whether a field is reset each round or carried across rounds. I-04 removes that ambiguity:
`RoundInitialise` (§1) is the single creation site, it lists every registry, and each is tagged
PER-ROUND or PER-RUN with an explicit reset-or-preserve rule.

## 2. Registry table (§0.8 `STRUCTURE RoundContext registries`; §1 `RoundInitialise`)

| registry | scope | initialised-to | initialising step in `RoundInitialise` | consuming procedure(s) | correction |
|----------|-------|----------------|----------------------------------------|------------------------|------------|
| `active_propagation_set` | per-round | empty set | `INITIALISE active_propagation_set <- empty` | `ScheduleSolutionPropagation` (add), `propagation_quiescent` (§0.6), `AcceptanceBatchFinalize`, `HandlePropagationFailure` | F3/G6; I-04 |
| `acceptance_batch_registry` | per-round | empty map | `INITIALISE acceptance_batch_registry <- empty` | `BlockAcceptancePoint` (§0.7 PHASE 3 register), `AcceptanceBatchFinalize` (§0.7 PHASE 4), `propagation_quiescent` | §0.7; I-04 |
| `candidate_discovery_seq` | per-round | `0` | `SET candidate_discovery_seq <- 0` | `HashWorkEvent`/`CreatePropagationContext` via `CandidateID = (RoundID, candidate_discovery_seq)` (G7) | G7; I-04 |
| `block_accepted` | per-round | `false` | `SET block_accepted <- false` | `propagation_quiescent` (§0.6), `AcceptanceBatchFinalize` | §0.6; I-04 |
| `state_version` | per-round | `0` | `SET state_version <- 0` | `SecurityFloorEvaluate` (carries epoch, G10); bumped by every `TRANSITION round_state` | G10; I-04 |
| `residency_ledger` | per-round | empty | `INITIALISE residency_ledger <- empty` | `ApplyMinerStateTransition` (sole owner, H7/I19); `HashWorkEvent` records metadata only, never a `t_<state>` | H7/I19; I-04 |
| `security_census_dirty` | per-run | empty map (run start) | `INITIALISE security_census_dirty <- empty map` (in `IF prior_state = null`) | `ApplyMinerStateTransition` step (7) sets; `ProcessEventTime` reads (§0.7d); `FinalizeEventTimeSecurityCensus` reads+clears (§9) | I-01; I-04 |
| `latest_security_census` | per-run | empty map (run start) | `INITIALISE latest_security_census <- empty map` (in `IF prior_state = null`) | `ApplyMinerStateTransition` step (7) overwrites; `FinalizeEventTimeSecurityCensus` reads (§9) | I-01; I-04 |
| `transition_event_registry` | per-run | empty set (run start) | `INITIALISE transition_event_registry <- empty set` (in `IF prior_state = null`) | `ApplyMinerStateTransition` step (0) reads+adds `TransitionEventID` (I-03) | I-03; I-04 |
| `finalised_event_times` | per-run | empty set (run start) | `INITIALISE finalised_event_times <- empty set` (in `IF prior_state = null`) | `ProcessEventTime` asserts-not-in + adds `t` (§0.7d/§0.7); scheduling guard (no ordinary event into a finalised `event_time`) | I-02; I-04 |
| `current_delta_cycle` | per-run | `0` (run start) | `SET current_delta_cycle <- 0` (in `IF prior_state = null`) | `ProcessEventTime` sets the dispatch cursor (§0.7d); `ApplyMinerStateTransition` reads it into `TransitionEventID`; delta-cycle rule §0.7-H2 | H2; I-04 |

All eleven registries appear in the `RETURNS RoundContext(…)` list of `RoundInitialise` — the
per-round set `{active_propagation_set, acceptance_batch_registry, candidate_discovery_seq,
block_accepted, state_version, residency_ledger}` and the per-run set `{security_census_dirty,
latest_security_census, transition_event_registry, finalised_event_times, current_delta_cycle}`.

## 3. Scope definition (per-round vs per-run) and why the per-run set must persist

**Per-round** (`§0.8` comment "reset by `RoundInitialise` at each round; I4"): reset FRESH by every
`RoundInitialise`. These are keyed within one round (`RoundID`-scoped `CandidateID` counter, the
round's propagation set / acceptance batches / accepted flag / state epoch / residency ledger), so a
per-round reset is correct and required.

**Per-run event-loop bookkeeping** (`§0.8` comment "PER-RUN: initialised once at run start,
PRESERVED across rounds; I-04"): `security_census_dirty`, `latest_security_census`,
`transition_event_registry`, `finalised_event_times`, `current_delta_cycle`. These are keyed by
`event_time` / `TransitionEventID`, both of which embed the **run-monotonic** `seq`/`event_time`, so
they must persist across round boundaries. A per-round reset would be a defect:

- resetting `finalised_event_times` would **un-finalise** past `event_time`s, violating I-02 (an
  already-closed timestamp could then accept an ordinary event, or its epilogue could re-run);
- resetting `transition_event_registry` would **drop replay-suppression state** (I-03), so an exact
  `TransitionEventID` replay after a round boundary would no longer be suppressed and would charge a
  second residency boundary/energy;
- resetting `security_census_dirty` / `latest_security_census` would strand or lose a pending
  event-time census whose epilogue (I-01) has not yet run;
- `current_delta_cycle` is the live dispatch cursor within the current `event_time` (H2) and is not a
  round-scoped quantity.

`RoundInitialise` therefore initialises the per-run bookkeeping ONLY at run start and preserves it
thereafter:

- **Run start (genesis round):** `IF prior_state = null:` initialises the five per-run fields
  (`security_census_dirty`, `latest_security_census`, `transition_event_registry`,
  `finalised_event_times` to empty; `current_delta_cycle <- 0`).
- **Subsequent rounds:** the `ELSE` branch `PRESERVE security_census_dirty, latest_security_census,
  transition_event_registry, finalised_event_times, current_delta_cycle from prior_state (§3.12)` —
  matching `STAGE_01_ROUND_STATE_MACHINE.md` §3.12 ("What information is preserved between rounds":
  the security-accounting history and audit log carry over) and round transitions R20/R21 ("carry
  forward preserved info (§3.12)").

## 4. No-implicit-global argument (created before any consumer reads it)

Every consumer named below is reachable only inside a round whose `RoundContext` was produced by
`RoundInitialise`, so each registry is created before its first read:

- **`ApplyMinerStateTransition` (§0.9)** reads/writes `transition_event_registry` (step (0), I-03),
  and reads/writes `security_census_dirty[event_time]` and `latest_security_census[event_time]`
  (step (7), I-01); it reads `current_delta_cycle` when building the `TransitionEventID`. The hook is
  invoked first at `MinerRegister` (T1), which runs inside an already-initialised round, so all four
  fields exist before the first transition.
- **`ProcessEventTime` (§0.7d)** reads/writes `finalised_event_times`, `current_delta_cycle`, and
  `security_census_dirty[t]`; its precondition `t not in finalised_event_times` presupposes the set
  exists — guaranteed by the run-start initialisation.
- **`FinalizeEventTimeSecurityCensus` (§9)** reads `security_census_dirty[event_time]` and
  `latest_security_census[event_time]` and clears the dirty flag; it is driven by `ProcessEventTime`,
  which only runs after `RoundInitialise` created both maps.

Per-round consumers (`propagation_quiescent`, `AcceptanceBatchFinalize`, `BlockAcceptancePoint`,
`ScheduleSolutionPropagation`, `SecurityFloorEvaluate`'s epoch check, the `CandidateID` seq) likewise
read fields that the same-round `RoundInitialise` set to their empty/zero/`false` seeds. No consumer
references any of the eleven registries as an ambient global.

## 5. Read-before-init impossibility for the run-start ordering

At run start there is no `prior_state`, so the per-run fields have no earlier definition to fall back
on. The event loop cannot dispatch any event before `ProcessEventTime` runs, and `ProcessEventTime`,
`ApplyMinerStateTransition`, and `FinalizeEventTimeSecurityCensus` are only reachable once a
`RoundContext` exists. `RoundContext` is produced solely by `RoundInitialise`, whose
`IF prior_state = null` branch initialises `security_census_dirty`, `latest_security_census`,
`transition_event_registry`, `finalised_event_times`, and `current_delta_cycle` before it RETURNS.
Thus any execution order that could read one of these fields is strictly preceded by its
initialisation — a read-before-init at run start is unreachable by construction.

## 6. Acceptance checklist

- **PASS — every registry explicitly initialised.** All eleven appear as an `INITIALISE`/`SET` step
  in `RoundInitialise` (§1); none is assumed to pre-exist.
- **PASS — every registry returned.** All eleven appear in the `RETURNS RoundContext(…)` list,
  grouped as per-round and per-run (§1).
- **PASS — scope defined.** Per-round = `{active_propagation_set, acceptance_batch_registry,
  candidate_discovery_seq, block_accepted, state_version, residency_ledger}`; per-run =
  `{security_census_dirty, latest_security_census, transition_event_registry, finalised_event_times,
  current_delta_cycle}` (§0.8 comments; §1 NOTE I-04).
- **PASS — per-run preserved across rounds.** `IF prior_state = null` initialises them once; the
  `ELSE` branch preserves them via §3.12; keyed by run-monotonic `event_time`/`TransitionEventID`, a
  per-round reset would un-finalise past `event_time`s (I-02) or drop replay-suppression (I-03).
- **PASS — no implicit global.** Each consumer (`ApplyMinerStateTransition`, `ProcessEventTime`,
  `FinalizeEventTimeSecurityCensus`, and the per-round consumers) reads a field created by
  `RoundInitialise` of the same run/round (§4).
- **PASS — no field read before init.** The run-start ordering makes a read-before-init unreachable
  (§5); `ProcessEventTime`'s precondition and the hook's step (0)/(7) all follow the RETURN.
- **PASS — A1 unchanged.** The `8.420833333 kWh` baseline is untouched; `residency_ledger` ownership
  of `t_<state>` (H7/I19) is unaffected by this initialisation/scoping correction.

Exercised by **TV66** ("`RoundInitialise` creates every runtime registry; no field is read before
initialisation", Reqs I-04) in `STAGE_01I_SEMANTIC_TEST_VECTORS.md`; TV61–TV65 corroborate the
per-run epilogue/idempotence state whose persistence this audit requires.

## 7. Result

**Result: RUNTIME INITIALISATION AUDIT (Stage 1I): PASS** — `RoundInitialise` explicitly initialises
and returns all eleven normative runtime registries with none existing as an implicit global; the
per-round set `{active_propagation_set, acceptance_batch_registry, candidate_discovery_seq,
block_accepted, state_version, residency_ledger}` is reset each round while the per-run event-loop
bookkeeping `{security_census_dirty, latest_security_census, transition_event_registry,
finalised_event_times, current_delta_cycle}` is initialised once at run start (`prior_state = null`)
and preserved across rounds (§3.12) because it is keyed by run-monotonic `event_time`/
`TransitionEventID`; every consumer (`ApplyMinerStateTransition`, `ProcessEventTime`,
`FinalizeEventTimeSecurityCensus`) reads only fields already created by `RoundInitialise`, no field
is read before initialisation, and the A1 baseline (`8.420833333 kWh`) is unchanged.
