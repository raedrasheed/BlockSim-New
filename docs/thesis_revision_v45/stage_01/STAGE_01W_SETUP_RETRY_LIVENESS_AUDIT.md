# Stage 1W — Setup Retry Liveness Audit (W8)

## 1. Scope

This audit documents correction **W8** of the Stage-1W revision to the PoCol formal
specification (the idle policy within PoCol): *make the setup retry state-compatible and
bounded*. The correction concerns the deterministic re-invocation of a rolled-back
assignment setup — the queued handler `SetupRetryEvent` and the two seating sites that mint
it, `PrepareParticipantsForNewRound` (for `PARTICIPANT_SETUP`) and `TemplateRefresh` (for
`TEMPLATE_REFRESH_SETUP`) — together with the three registries that make the retry
idempotent and bounded: the per-round counter `setup_retry_generation`, the per-run
idempotence set `applied_setup_retry_ids`, and the config bound `maximum_setup_retries`.

The audit is descriptive and documentation-only. It reads the current specification text and
records the state of the corrected contract; it modifies no protocol file. Every claim below
is grounded in the current text of

- `STAGE_01_PROTOCOL_PSEUDOCODE.md` (the normative pseudocode; line references were
  re-established by grep against the current file, not inherited from any earlier revision),

with traceability confirmed against `STAGE_01_ROUND_STATE_MACHINE.md` (§3.10a),
`STAGE_01_TERMINOLOGY.md` (Stage-1W addendum), `STAGE_01_INVARIANT_CATALOGUE.md` (I16, W8
amendment), and `STAGE_01_TRACEABILITY_MATRIX.csv` (R167, R168).

The A1 energy-accounting baseline (`8.420833333 kWh`,
`STAGE_01_ENERGY_MODEL_SPECIFICATION.md` line 29) is unaffected by this correction and is
preserved unchanged. W8 is a control-flow / event-identity / liveness correction with no
energy or time semantics: it changes *which* retries are seated and how they terminate, never
how any residency interval is charged.

## 2. The defect (pre-W8 / V8 state)

In the V8 formulation the setup rollbacks already existed as named executable procedures and
each caller already took an explicit liveness path — a `SetupRetryEvent` or a declared
`RoundAbort` — so the round was never left in `ASSIGNMENT` with no controller. What V8 lacked
was any discipline *on the retry itself*. The Stage-1V audit records the V8 gate verbatim
(`STAGE_01V_SETUP_ROLLBACK_LIVENESS_AUDIT.md`, lines 186–194):

```
IF a setup retry is warranted (bounded by the retry policy)
   AND next_representable_simulation_time(dispatch_envelope.event_time) <= run_horizon_T:
```

and describes the V8 `SetupRetryEvent` inputs as merely "`RoundContext, dispatch_envelope,
RoundID, setup_kind, reason`" (same audit, lines 158–160). Three distinct faults followed:

1. **No idempotence.** The V8 retry carried no retry identity. A re-dispatched or duplicated
   `SetupRetryEvent` would re-invoke `PrepareParticipantsForNewRound` / `TemplateRefresh`
   again, running the setup more than once; nothing recorded that a given retry had already
   been applied.

2. **No explicit, verifiable bound.** "Warranted (bounded by the retry policy)" was a prose
   predicate with no registry backing it. There was no per-round generation counter and no
   config field to compare against, so the bound could not be audited and — depending on how
   "the retry policy" was realised — a retry chain need not provably terminate.

3. **No state-compatibility check.** The V8 gate inspected only "warranted" and horizon. It
   did **not** consult whether the rollback had routed a participant to `OFFLINE`. A rollback
   that legally departs a `WAKING` participant to `OFFLINE` (the T12 edge) leaves that miner
   in a state the setup **cannot** re-enlist, yet V8 would still seat the retry — a retry
   attempted from an incompatible state, which cannot succeed and merely burns the
   (unbounded) budget before eventually failing.

W8 replaces the prose "warranted" predicate with three concrete registries, a state-
compatibility gate, and an idempotent, bounded retry identity.

## 3. The retry registries

W8 introduces exactly three normative registries. Each is explicitly owned, per the Q5
ownership discipline, and its reset owner is fixed.

| Registry | Declaration | Scope | Reset owner |
|----------|-------------|-------|-------------|
| `setup_retry_generation` | `RoundInitialise`, pseudocode line 1391: `INITIALISE setup_retry_generation <- empty map   # W8: per (RoundID, setup_kind) bounded retry counter (absent = 0 retries so far)` | Per-**round** map, keyed by `(RoundID, setup_kind)` | `RoundInitialise` — reset FRESH every round (returned explicitly at line 1416: `setup_retry_generation)   # W8: per-round bounded setup-retry counter`) |
| `applied_setup_retry_ids` | `RunContext` structure, line 1319: `applied_setup_retry_ids : W8 — set of already-applied SetupRetryIDs (RoundID, setup_kind, generation), guarding` idempotent replay; initialised in `RunInitialise` line 1340: `INITIALISE applied_setup_retry_ids <- empty set   # W8: idempotence registry for SetupRetryEvent` | Per-**run** set | `RunInitialise` — created ONCE per run; never re-created by `RoundInitialise` |
| `maximum_setup_retries` | `RunContext` structure, line 1321: `maximum_setup_retries : W8 — config bound on setup_retry_generation per (RoundID, setup_kind)`; set in `RunInitialise` line 1341: `SET maximum_setup_retries <- config.maximum_setup_retries   # W8: bounded retry budget per (RoundID, setup_kind)` | Per-**run** scalar (config bound in `RunContext`) | `RunInitialise` — set once from `config`; a fixed budget for the run |

The scope split is deliberate and matches the identity `SetupRetryID = (RoundID,
setup_kind, setup_retry_generation)`. The generation counter is per-round because a fresh
round starts its retry budget from zero (`absent = 0 retries so far`, line 1391); the
idempotence set and the bound are per-run because a `SetupRetryID` is globally unique across
the run (it embeds the `RoundID`) and the budget is a run-wide policy constant. Both per-run
fields are returned explicitly from `RunInitialise` (lines 1346: `applied_setup_retry_ids,
maximum_setup_retries)   # W8`) and `RoundInitialise` never re-creates them — it binds
`RunContext` by reference and only resets the per-round `setup_retry_generation`.

## 4. The state-compatibility gate

W8's central liveness rule is that a retry may be seated **only** when the rollback left every
eligible participant in a state the retried procedure can legally re-enlist. This is enforced
at two layers: at the **seat** (in each caller, before minting a `SetupRetryEvent`) and again
at **dispatch** (inside `SetupRetryEvent`, before re-invoking the setup).

**Seat-time gate (rollback routed miners OFFLINE → abort).**
`RollbackParticipantSetup` reports whether its legal T12 departures stranded any participant.
Its effect body sets `rolled_to_offline <- true` for each WAKING participant it departs (line
1656: `IF tr is transition_applied(teid): SET rolled_to_offline <- true    # W2/W8: a WAKING
participant was legally departed`) and returns that flag (line 1665: `RETURN
rollback_completed(rolled_to_offline)   # W2/W8: report whether a retry is state-
incompatible`). `PrepareParticipantsForNewRound` consumes it as the FIRST post-rollback
decision (lines 1606–1608):

```
IF rb.rolled_to_offline:
  RETURN CALL RoundAbort(RoundContext, reason = participant_setup_failed(setup_reason),
                         dispatch_envelope = dispatch_envelope, recovery_finalising = false)   # W8: retry state-incompatible
```

`TemplateRefresh` (consuming `RollbackTemplateRefreshSetup`, which reports the same flag at
line 1694) applies the identical gate (lines 4672–4674):

```
IF rb.rolled_to_offline:
  RETURN CALL RoundAbort(RoundContext, reason = template_refresh_failed(setup_reason),
                         dispatch_envelope = dispatch_envelope, recovery_finalising = false)   # W8: retry state-incompatible
```

Thus a rollback that routed *any* participant to `OFFLINE` never seats a `SetupRetryEvent`;
it aborts the round. This closes fault (3) of §2.

**Dispatch-time gate (every eligible participant re-enlistable).**
Even when the seat-time gate passed, `SetupRetryEvent` re-checks state compatibility before
re-running the setup, because time has advanced between seat and dispatch. The check requires
every eligible participant of the round to be in one of the three states the setup enlists
from (lines 1714–1719):

```
# W8 STATE COMPATIBILITY: every eligible participant of RoundID must be in a state the setup can legally re-enlist
#   ({REGISTERED, RESERVE, LOW_POWER_LISTEN}); if a prior rollback stranded a participant OFFLINE, ABORT rather than
#   retry (do NOT claim a retry path from an incompatible state).
IF NOT (every eligible participant of RoundID is in miner_state {REGISTERED, RESERVE, LOW_POWER_LISTEN}):
  RETURN CALL RoundAbort(RoundContext, reason = setup_retry_state_incompatible(setup_kind),
                         dispatch_envelope = dispatch_envelope, recovery_finalising = false)   # W8
```

The set `{REGISTERED, RESERVE, LOW_POWER_LISTEN}` is exactly the eligibility set the setups
enlist from (cf. `TemplateRefresh` line 4620: `eligible <- { m : miner_state(m) in
{REGISTERED, RESERVE, LOW_POWER_LISTEN} }`). An `OFFLINE` (or otherwise non-eligible)
participant therefore fails this test and the retry aborts under the named reason
`setup_retry_state_incompatible(setup_kind)` rather than "limping on" from a state it cannot
re-enlist.

## 5. Idempotence and boundedness

**Idempotence (`SetupRetryID` + `applied_setup_retry_ids`).**
Each seated retry carries a unique identity minted at the seat. In
`PrepareParticipantsForNewRound` (lines 1613–1620):

```
SET g <- setup_retry_generation[(RoundID_current, PARTICIPANT_SETUP)] + 1     # W8: advance the bounded generation
SET setup_retry_generation[(RoundID_current, PARTICIPANT_SETUP)] <- g
SET srid <- (RoundID_current, PARTICIPANT_SETUP, g)                            # W8: SetupRetryID
SET r <- CALL ScheduleEvent(EQ, RoundContext, SetupRetryEvent,
               target_event_time = next_representable_simulation_time(dispatch_envelope.event_time),
               target_microphase = ROUND_SETUP,
               {RoundID = RoundID_current, setup_kind = PARTICIPANT_SETUP, SetupRetryID = srid,
                setup_retry_generation = g, reason = setup_reason})            # W8
```

`TemplateRefresh` mints the analogous `(RoundID_current, TEMPLATE_REFRESH_SETUP, g)` at lines
4679–4685. The generation is *advanced before* the identity is minted, so each distinct seat
produces a distinct `SetupRetryID`. On dispatch, `SetupRetryEvent` receives `SetupRetryID` as
an explicit input (line 1700: `INPUTS: RoundContext, dispatch_envelope, RoundID, setup_kind,
SetupRetryID, setup_retry_generation, reason`) and suppresses a duplicate before doing any
work (lines 1708–1710):

```
# W8 IDEMPOTENCE: a replay of an already-applied SetupRetryID runs the setup at most ONCE.
IF SetupRetryID in applied_setup_retry_ids:
  RETURN setup_retry_duplicate_suppressed(SetupRetryID)
```

Critically, the idempotent marker is registered **before** the setup is re-invoked (line
1720: `ADD SetupRetryID to applied_setup_retry_ids   # W8: register the idempotent marker
BEFORE re-invoking`), so a re-dispatch of the same identity — even one racing the first — is
suppressed and the setup runs at most once per `SetupRetryID`. This closes fault (1) of §2.

**Boundedness (`setup_retry_generation <= maximum_setup_retries`).**
The bound is enforced at both layers. At the seat, each caller refuses to mint a further
retry once the generation has reached the budget (`PrepareParticipantsForNewRound` lines
1609–1611; `TemplateRefresh` lines 4675–4677):

```
IF setup_retry_generation[(RoundID_current, PARTICIPANT_SETUP)] >= maximum_setup_retries:
  RETURN CALL RoundAbort(RoundContext, reason = participant_setup_retries_exhausted(setup_reason),
                         dispatch_envelope = dispatch_envelope, recovery_finalising = false)   # W8: bounded
```

At dispatch, `SetupRetryEvent` re-verifies the bound before running (lines 1712–1713):

```
# W8 BOUND: never run a retry beyond the budget.
IF setup_retry_generation > maximum_setup_retries:
  RETURN setup_retry_exhausted(SetupRetryID)
```

Because `setup_retry_generation[(RoundID, setup_kind)]` strictly increases by one per seat and
the caller aborts once it reaches `maximum_setup_retries`, the number of retries per
`(RoundID, setup_kind)` is bounded by the config budget and the retry chain provably
terminates in either a completed setup, a `RoundAbort`, or an exhausted no-op. This closes
fault (2) of §2. The retry is additionally horizon-guarded: it is only seated when
`next_representable_simulation_time(dispatch_envelope.event_time) <= run_horizon_T` (lines
1612 / 4678), and a strictly-later target ensures the retry never re-enqueues work at the
already-draining event_time.

`SetupRetryEvent` also carries the pre-existing stale guard (lines 1705–1707): if the round
moved on (`RoundID != RoundID_current` or `round_state NOT in {ASSIGNMENT,
ROUND_INITIALISING, TEMPLATE_COMMITMENT}`) it returns `setup_retry_stale_noop(SetupRetryID)`.
The declared result union is therefore `setup_retry_stale_noop |
setup_retry_duplicate_suppressed | setup_retry_exhausted | round_aborted | (the re-run
setup's disposition)` (line 1724).

## 6. Seat-vs-abort decision table

The following table records, in the order the guards are evaluated, the observable outcome
for each condition. "Seat site" columns are `PrepareParticipantsForNewRound` (lines
1606–1622) / `TemplateRefresh` (lines 4672–4688); "dispatch" is `SetupRetryEvent` (lines
1705–1723).

| Stage | Condition | Outcome | Grounding |
|-------|-----------|---------|-----------|
| Seat | `rb = rollback_failed(rr)` | `RoundAbort` (`participant_setup_rollback_failed` / `template_refresh_rollback_failed`) | 1602–1605 / 4668–4671 |
| Seat | `rb.rolled_to_offline = true` | `RoundAbort` — **no** retry (state-incompatible) | 1606–1608 / 4672–4674 |
| Seat | `setup_retry_generation[...] >= maximum_setup_retries` | `RoundAbort` (`*_retries_exhausted`) — budget spent | 1609–1611 / 4675–4677 |
| Seat | strictly-later target `> run_horizon_T` | falls through to `RoundAbort` (`*_failed`) — no in-horizon retry slot | 1612 / 4678 + 1622 / 4688 |
| Seat | rollback clean, budget left, in horizon, `ScheduleEvent` returns `scheduled(...)` | **Seat** `SetupRetryEvent`; return `participant_set_setup_retry_seated(srid, …)` / `template_refresh_retry_seated(srid, …)` | 1621 / 4687 |
| Seat | `ScheduleEvent` did not return `scheduled(...)` | `RoundAbort` (`*_failed`) | 1622–1623 / 4688–4689 |
| Dispatch | round moved on (stale) | `setup_retry_stale_noop(SetupRetryID)` — no-op | 1705–1707 |
| Dispatch | `SetupRetryID in applied_setup_retry_ids` | `setup_retry_duplicate_suppressed(SetupRetryID)` — runs at most once | 1708–1710 |
| Dispatch | `setup_retry_generation > maximum_setup_retries` | `setup_retry_exhausted(SetupRetryID)` | 1712–1713 |
| Dispatch | not every eligible participant re-enlistable | `RoundAbort` (`setup_retry_state_incompatible(setup_kind)`) | 1714–1719 |
| Dispatch | all guards pass | `ADD SetupRetryID`; re-invoke `PrepareParticipantsForNewRound` / `TemplateRefresh` (its own liveness path governs) | 1720–1723 |

The invariant across the table: whenever the state is incompatible (`rolled_to_offline`, or a
participant not in `{REGISTERED, RESERVE, LOW_POWER_LISTEN}`) or the budget is exhausted, the
outcome is a **declared** `RoundAbort` or a suppressed/exhausted no-op — never a retry seated
from an incompatible state and never an unbounded re-invocation.

## 7. Mapping to TV196 / TV197

Both W8 vectors are present in `STAGE_01W_SEMANTIC_TEST_VECTORS.md` (a control-flow /
rollback / result-contract check, so the A1 baseline `8.420833333 kWh` is preserved by each).

- **TV196 — Rollback that routes miners OFFLINE seats no retry and aborts (W8)** (lines
  134–142). Setup: a participant setup fails after at least one miner reached `WAKING`, so
  `RollbackParticipantSetup` returns `rollback_completed(rolled_to_offline = true)`. Expected:
  `PrepareParticipantsForNewRound` observes `rb.rolled_to_offline = true`, seats **no**
  `SetupRetryEvent`, and returns `RoundAbort(reason = participant_setup_failed(setup_reason),
  …)`. This exercises the §4 seat-time state-compatibility gate (pseudocode 1606–1608). Coverage
  map (line 176): procedures `RollbackParticipantSetup`, `PrepareParticipantsForNewRound`,
  `RoundAbort`.

- **TV197 — A bounded legal retry is idempotent and generation-bounded (W8)** (lines
  144–158). Setup: a setup failed *before* any miner reached `WAKING`, so the rollback
  reported `rolled_to_offline = false` and a `SetupRetryEvent` with `SetupRetryID = (RoundID,
  PARTICIPANT_SETUP, g)` is seated, then re-dispatched twice. Expected: the first dispatch
  passes the stale guard, finds `SetupRetryID ∉ applied_setup_retry_ids`, `g <=
  maximum_setup_retries`, and every eligible participant re-enlistable, so it adds the id and
  re-invokes the setup; the second dispatch of the SAME id finds `SetupRetryID ∈
  applied_setup_retry_ids` and returns `setup_retry_duplicate_suppressed(SetupRetryID)`; and a
  retry with `setup_retry_generation > maximum_setup_retries` returns `setup_retry_exhausted`.
  This exercises the §5 idempotence and boundedness contract (pseudocode 1708–1720). Coverage
  map (line 177): procedures `SetupRetryEvent`, `PrepareParticipantsForNewRound`.

Together TV196 and TV197 witness the two halves of W8: an incompatible (OFFLINE) rollback
aborts rather than retries, and a compatible retry runs at most once per identity within the
generation bound.

## 8. Traceability

- **Round state machine — §3.10a (Stage-1W addendum), W8.**
  `STAGE_01_ROUND_STATE_MACHINE.md` lines 675–679 state the rule: "A `SetupRetryEvent` is
  seated only when the rollback left every eligible participant in a state the setup can
  legally re-enlist (`rolled_to_offline = false`), the retry budget is not exhausted
  (`setup_retry_generation <= maximum_setup_retries`), and the strictly-later target is within
  horizon; otherwise the round `RoundAbort`s. Each retry carries a `SetupRetryID = (RoundID,
  setup_kind, generation)` and is idempotent (`applied_setup_retry_ids`) and bounded." This
  matches the pseudocode seat/dispatch guards of §§4–5 exactly.

- **Terminology — Stage-1W addendum, W8.**
  `STAGE_01_TERMINOLOGY.md` lines 851–853 define the term: "`SetupRetryID` / bounded retry
  (W8). `SetupRetryID = (RoundID, setup_kind, setup_retry_generation)`; a retry is seated only
  when it is state-compatible (no participant `OFFLINE`), idempotent (`applied_setup_retry_ids`),
  and within `maximum_setup_retries`; otherwise `RoundAbort`." The identity tuple and the three
  properties agree with the registries of §3.

- **Invariant catalogue — I16, W8 amendment.**
  `STAGE_01_INVARIANT_CATALOGUE.md` lines 331–334 carry the W8 amendment to I16: "**W8
  (bounded state-compatible retry):** a `SetupRetryEvent` is seated only when rollback left
  every eligible participant re-enlistable (never routed to `OFFLINE`), the retry generation
  is within `maximum_setup_retries`, and the target is within horizon; it is idempotent on
  `SetupRetryID`, else the round aborts." I16 is the "security-floor breaches are recorded,
  not silently repaired" invariant (line 284); the W8 amendment binds the setup-retry liveness
  discipline into that recorded-not-repaired guarantee — an unrecoverable setup is declared as
  a `RoundAbort`, never masked by an unbounded or state-incompatible retry.

- **Traceability matrix — R167 (with R168/TV196–TV197).**
  `STAGE_01_TRACEABILITY_MATRIX.csv` line 168 (R167): "Make setup retry state-compatible and
  bounded (W8); `SetupRetryEvent` carries `SetupRetryID = (RoundID setup_kind
  setup_retry_generation)` is idempotent on `applied_setup_retry_ids` and bounded by
  `maximum_setup_retries`; a retry is seated only when rollback left every eligible participant
  re-enlistable (`rolled_to_offline` false) the budget is not exhausted and the strictly-later
  target is within horizon; otherwise the round aborts and no incompatible retry is seated."
  State/event: `SetupRetryEvent; PrepareParticipantsForNewRound; TemplateRefresh; RoundAbort`;
  invariant `I16`; threat "a setup retry seated from an incompatible OFFLINE state or an
  unbounded retry that never terminates"; status `SPECIFIED`. The two paper vectors are logged
  under R168 (line 169): "TV196 rollback leaving miners OFFLINE seats no retry and RoundAbort
  executes; TV197 a bounded legal retry is replayed with `SetupRetryID` suppressing duplicates
  and generation bounded by `maximum_setup_retries`."

## 9. Completeness note

Every artefact W8 requires is present in the current specification: the three registries with
their declared scope and reset owners (§3); the seat-time `rolled_to_offline → RoundAbort`
and `generation >= maximum_setup_retries → RoundAbort` gates in both callers (§§4–5); the
generation-advance, `SetupRetryID` mint, and `ScheduleEvent(SetupRetryEvent, {…, SetupRetryID,
setup_retry_generation, …})` seat (§5); and the `SetupRetryEvent` stale guard, duplicate
suppression, exhaustion guard, state-compatibility abort, and pre-invocation `ADD SetupRetryID
to applied_setup_retry_ids` (§§4–5). No expected element of the W8 contract was found absent.
The correction is control-flow / event-identity / liveness only; the A1 energy-accounting
baseline `8.420833333 kWh` is preserved unchanged.
