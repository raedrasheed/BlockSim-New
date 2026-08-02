# Stage 1AH — Bootstrap-Chain Seat-Result + First-Round-Admission Audit (AH6 / AH5)

This audit verifies corrections **AH6** (every bootstrap-chain successor seat result is INSPECTED and turned into a
declared disposition — never a silently-ignored seat, never a success returned over a failed successor, never a null
`RoundContext` dereference) and **AH5** (first-round miner admission: the genesis miner set is imported as `MINER_JOIN`
driver requests behind an initial-registration barrier, and participant setup is deferred until that barrier is
satisfied). It confirms each step of the round-bootstrap chain
`SeatNextRoundBootstrap -> RoundInitialiseEvent -> SeatTemplateCommit -> TemplateCommitEvent -> SeatPrepareParticipants
-> PrepareParticipantsEvent` inspects the result of the successor it is required to seat.

Scope is documentation-only. The algorithm is **PoCol** and the mechanism is **the idle policy within PoCol**. The A1
baseline `8.420833333 kWh` is unchanged. No Stage-1A–1AG historical artifact is modified; only this audit file is
created. All lines are quoted from the current normative document; line anchors are exact.

Source of truth (read-only): `STAGE_01_PROTOCOL_PSEUDOCODE.md` (the FINAL normative tree under
`docs/thesis_revision_v45/stage_01/`).

---

## 1. `RunEventLoopToHorizon` captures the FIRST bootstrap seat result and takes the safe no-round path — PASS

`RunEventLoopToHorizon` (`PROCEDURE RunEventLoopToHorizon`, line 487) seats the first-round bootstrap through the named
owner BEFORE the loop and captures the result into `boot0`:

```
499    SET boot0 <- CALL SeatNextRoundBootstrap(RunContext)          # AG4/AH2: seats RoundInitialiseEvent (the first driver event)
500    IF boot0 = round_bootstrap_seat_failed(_, reason):
503      RECORD run_bootstrap_failed(reason)                          # AH6
504      CALL FinalizeSimulationRunNoRound(RunContext, reason = bootstrap_seat_failed_run_abort)   # AH6: safe null-round finaliser (§20a)
505      RETURN run_aborted_no_round(reason)                          # AH6: declared run disposition; no null RoundContext dereferenced
```

On `round_bootstrap_seat_failed` it records `run_bootstrap_failed(reason)` (line 503), calls
`FinalizeSimulationRunNoRound(RunContext, reason = bootstrap_seat_failed_run_abort)` (line 504), and returns
`run_aborted_no_round(reason)` (line 505) — WITHOUT entering the `WHILE true` loop (which begins at line 514) and
WITHOUT resolving `RunContext.current_round_context` (that resolution is at line 530, on the success path only).
`current_round_context` is `null` at entry per the precondition (line 493), so the failure branch never dereferences a
null `RoundContext`. The disposition is declared in the RETURNS union (`run_completed(T) | run_aborted_no_round(reason)`,
line 532) and restated in the procedure NOTE (lines 541–543).

**Finding: PASS.** The first seat result is inspected; failure records `run_bootstrap_failed`, calls
`FinalizeSimulationRunNoRound(reason = bootstrap_seat_failed_run_abort)`, and returns `run_aborted_no_round` before the
loop and without a null-`RoundContext` dereference.

---

## 2. `RoundInitialiseEvent` inspects `SeatTemplateCommit`; failure aborts the round — PASS

`RoundInitialiseEvent` (`PROCEDURE RoundInitialiseEvent`, line 1231) publishes the new `RoundContext` (line 1241) and
then seats the round's own `TemplateCommitEvent`, capturing the result:

```
1244    SET tc <- CALL SeatTemplateCommit(RunContext, RoundID_at_seat = rc.RoundID, candidate_template = candidate_template_for_round(rc))
1245    SWITCH tc:
1246      CASE template_commit_seated(_) | template_commit_already_seated(_):
1247        RETURN round_initialised(rc.RoundID)                      # AF4/AH6: the required successor is seated
1248      CASE template_commit_seat_failed(reason):
1255        SET disp <- CALL RoundAbort(rc, reason = template_commit_seat_failed_round_abort(reason), dispatch_envelope = abort_envelope)
1256        RETURN round_initialise_aborted(rc.RoundID, template_commit_seat_failed_round_abort(reason))   # AH6: declared disposition; round is terminal, not stranded
```

On `template_commit_seat_failed(reason)` it calls `RoundAbort(rc, reason =
template_commit_seat_failed_round_abort(reason), ...)` (line 1255) using the dispatched round-setup event's own envelope
(built at lines 1253–1254) and returns `round_initialise_aborted(...)` (line 1256). The round is aborted (terminal),
not left stranded in `TEMPLATE_COMMITMENT`. The RETURNS union names both dispositions (line 1257).

**Finding: PASS.** `template_commit_seat_failed` -> `RoundAbort(template_commit_seat_failed_round_abort(...))` ->
`round_initialise_aborted`; the round is not stranded in `TEMPLATE_COMMITMENT`.

---

## 3. `TemplateCommitEvent` inspects participant setup (via `SeatParticipantSetupOrAbort`); AH5 deferral — PASS

`TemplateCommitEvent` (`PROCEDURE TemplateCommitEvent`, line 1259) commits the template (line 1265) and then, only when
the initial-registration barrier is satisfied, seats participant setup through `SeatParticipantSetupOrAbort`:

```
1272    IF NOT RoundContext.initial_registration_barrier.satisfied:
1273      RETURN template_committed_participant_setup_deferred(RoundID_current, TemplateID)   # AH5: barrier pending; MinerRegister will seat
1275    SET ps <- CALL SeatParticipantSetupOrAbort(RoundContext.RunContext, RoundContext,
1276                     RoundID_at_seat = RoundID_current, TemplateID_at_seat = TemplateID, abort_envelope = abort_envelope)   # AH5/AH6
1277    SWITCH ps:
1278      CASE participant_setup_seated(_) | participant_setup_already_seated:
1279        RETURN template_committed(RoundID_current, TemplateID)    # AF4/AH6: the required successor is seated
1280      CASE participant_setup_aborted(reason):
1281        RETURN template_commit_participant_setup_aborted(RoundID_current, reason)   # AH6: declared disposition; round terminal, not stranded
```

The AH5 deferral is correct: when `initial_registration_barrier.satisfied` is false (line 1272) it returns
`template_committed_participant_setup_deferred(...)` (line 1273) WITHOUT seating participant setup — a distinct
"deferred" disposition, not a false success. `SeatParticipantSetupOrAbort` (`PROCEDURE SeatParticipantSetupOrAbort`,
line 1427) inspects the underlying `SeatPrepareParticipants` result and, on failure, aborts the round:

```
1438      CASE prepare_participants_seat_failed(reason):
1441        SET disp <- CALL RoundAbort(RoundContext, reason = participant_setup_seat_failed_round_abort(reason),
1442                                    dispatch_envelope = abort_envelope)
1443        RETURN participant_setup_aborted(participant_setup_seat_failed_round_abort(reason))
```

So a participant-setup seat failure aborts the round with `participant_setup_seat_failed_round_abort` (line 1441) and
surfaces as `template_commit_participant_setup_aborted` at the wrapper (line 1281). The barrier deferral is the first-
round admission path (AH5), enumerated in the RETURNS union (lines 1282–1284).

**Finding: PASS.** Participant setup is seated via `SeatParticipantSetupOrAbort`; failure aborts the round with
`participant_setup_seat_failed_round_abort`; a pending initial-registration barrier returns
`template_committed_participant_setup_deferred` (AH5).

---

## 4. `ExhaustionAdjudicate` inspects `SeatFullRangeExhaust`; failure aborts the round — PASS

`ExhaustionAdjudicate` (`PROCEDURE ExhaustionAdjudicate`, line 3853), on the ACCEPTED path where this acceptance makes
the entire assigned domain accepted-searched with no live block (guard at lines 3887–3889), seats the
`FullRangeExhaustEvent` and inspects the result:

```
3890        SET fre <- CALL SeatFullRangeExhaust(RoundContext.RunContext, RoundID_at_seat = RoundID_current,
3891                                  TemplateID_at_seat = TemplateID_committed)   # AG4: reachable named seating path
3892        SWITCH fre:
3893          CASE full_range_exhaust_seated(_) | full_range_exhaust_already_seated(_):
3894            SKIP   # AH6: the exhaustion adjudication event is (or was already) seated — the dispatched handler adjudicates
3895          CASE full_range_exhaust_seat_failed(reason):
3900            CALL RoundAbort(RoundContext, reason = full_range_exhaust_seat_failed_round_abort(reason), dispatch_envelope = abort_envelope)   # AH6
```

On `full_range_exhaust_seat_failed(reason)` (line 3895) it aborts the round with
`RoundAbort(RoundContext, reason = full_range_exhaust_seat_failed_round_abort(reason), ...)` (line 3900), using this
handler's own dispatched frame (built at lines 3898–3899), so the round is never left stranded fully-searched with no
adjudication event.

**Finding: PASS.** `full_range_exhaust_seat_failed` -> `RoundAbort(full_range_exhaust_seat_failed_round_abort(...))`.

---

## 5. `FinalizeSimulationRunNoRound` is defined, settles nothing, dereferences no null `RoundContext` — PASS

`FinalizeSimulationRunNoRound` (`PROCEDURE FinalizeSimulationRunNoRound`, line 6944) is the dedicated finaliser for the
no-round run:

```
6946  PRECONDITIONS: RunEventLoopToHorizon's FIRST SeatNextRoundBootstrap returned round_bootstrap_seat_failed, so
6947                 RunContext.current_round_context is STILL null — NO round was ever created and NO miner was ever activated.
6951    IF run_finalised: RETURN run_already_finalised               # N1: idempotent
6955    RECORD run_no_round_disposition(RunID, reason)               # AH6: declared run-abort disposition (bootstrap_seat_failed_run_abort)
6956    ADD run_horizon_T TO EQ.finalised_event_times               # close T to ordinary events (no epilogue: no round/census exists)
6957    SET run_finalised <- true
6958  RETURNS: run_finalised_no_round(reason)
```

It performs NO residency settle and NO per-round reconciliation: the AH6 comment at lines 6952–6953 states
"`SettleResidencyBoundary` and the I5/I6/I7 per-round reconciliation are INAPPLICABLE (they require a `RoundContext`)",
and the body contains no `SettleResidencyBoundary` / I5 / I6 / I7 call — it only records the declared disposition (line
6955), finalises `T` (line 6956), and sets `run_finalised` (line 6957). Because `current_round_context` is still null by
precondition (lines 6946–6947) and no `RoundContext` field is read, no null `RoundContext` is dereferenced. The NOTE
(lines 6959–6961) restates that this is the ONLY finalisation path for a run whose first bootstrap could not be seated
and that it performs no settle and no reconciliation. (Contrast `FinalizeSimulationRun`, line 6915, which ASSERTs
`round_state in {ROUND_ACCEPTED, ROUND_ABORTED}` at line 6926 and performs the FINAL_RUN_END settle — it is never
reached on the no-round path.)

**Finding: PASS.** `FinalizeSimulationRunNoRound` is defined, does no residency settle / no per-round reconciliation,
finalises `T`, and dereferences no null `RoundContext`.

---

## 6. AH5 first-round admission: genesis import, barrier advance, and setup guard — PASS

**Genesis import + barrier creation.** `RoundInitialise` (`PROCEDURE RoundInitialise`) initialises the per-round
barrier as already satisfied by default (a subsequent round), then, for the FIRST round only, imports the genesis miner
set as `MINER_JOIN` driver requests and sets the barrier unsatisfied:

```
2847    SET        initial_registration_barrier <- { expected = empty set, registered = empty set, satisfied = true }   # AH5
2865    IF prior_state = null AND RunContext.genesis_miner_registry is non-empty:
2867      FOR EACH genesis_entry g IN SORT(RunContext.genesis_miner_registry BY MinerID ascending):
2868        CALL AdmitDriverRequest(RunContext, kind = MINER_JOIN, requested_event_time = EQ.current_event_time,
2869                                payload = { join_request = g.join_request })   # AH4/AH5: a genesis join request
2870        ADD MinerID(g.join_request) TO expected
2871      SET initial_registration_barrier <- { expected = expected, registered = empty set, satisfied = false }   # AH5: not yet complete
2872      SET RunContext.genesis_miner_registry <- empty          # AH5: imported exactly once
```

`genesis_miner_registry` is a declared `RunContext` field (definition line 2699) populated from `config.initial_miner_set`
by `RunInitialise` (line 2766). Each genesis entry is admitted as a `MINER_JOIN` driver request (line 2868), the
barrier `expected` set is the declared genesis MinerID set (lines 2870–2871), and the registry is consumed exactly once
(line 2872). The barrier is returned as a per-round registry (line 2887).

**Barrier advance + seat-on-completion.** `MinerRegister` (`PROCEDURE MinerRegister`, line 3593) advances the barrier
and, on completion during ASSIGNMENT (i.e. after `TemplateCommitEvent` deferred), seats participant setup exactly once:

```
3617    IF MinerID in RoundContext.initial_registration_barrier.expected:
3618      ADD MinerID TO RoundContext.initial_registration_barrier.registered
3619      IF RoundContext.initial_registration_barrier.registered CONTAINS every member of RoundContext.initial_registration_barrier.expected
3620         AND NOT RoundContext.initial_registration_barrier.satisfied:
3621        SET RoundContext.initial_registration_barrier.satisfied <- true          # AH5: declared initial miner set complete
3622        IF round_state = ASSIGNMENT AND TemplateID_committed != null:
3625          CALL SeatParticipantSetupOrAbort(RoundContext.RunContext, RoundContext,
3626                 RoundID_at_seat = RoundID_current, TemplateID_at_seat = TemplateID_committed, abort_envelope = abort_envelope)   # AH5/AH6: seat once ready (idempotent)
```

The seat goes through the idempotent `SeatParticipantSetupOrAbort` owner (line 3625), so it fires exactly once when the
declared genesis set completes, and its seat-failure branch (audited in §3) still aborts the round.

**Setup guard.** `PrepareParticipantsForNewRound` (`PROCEDURE PrepareParticipantsForNewRound`, line 2990) guards on the
barrier defensively:

```
3004    IF NOT RoundContext.initial_registration_barrier.satisfied:
3005      RETURN participant_setup_registration_barrier_pending   # AH5: no participants established; MinerRegister re-seats on completion
```

If the barrier is not satisfied it returns `participant_setup_registration_barrier_pending` (line 3005) and establishes
no participant set. `PrepareParticipantsEvent` (line 1294) enumerates this disposition in its RETURNS union (line 1302).

**Finding: PASS.** `RoundInitialise` imports `genesis_miner_registry` as `MINER_JOIN` requests and sets the
initial-registration barrier (lines 2865–2872); `MinerRegister` advances the barrier and seats participant setup on
completion (lines 3617–3626); `PrepareParticipantsForNewRound` guards on `initial_registration_barrier.satisfied`,
returning `participant_setup_registration_barrier_pending` when pending (lines 3004–3005).

---

## 7. No caller returns success after a required successor failed to seat — PASS

Every point in the chain that seats a REQUIRED successor turns a seat failure into an abort/no-round disposition, never
a success:

| Caller (procedure) | Required successor seated | On seat failure | file:line |
| --- | --- | --- | --- |
| `RunEventLoopToHorizon` | `SeatNextRoundBootstrap` (first round) | `run_aborted_no_round(reason)` | lines 500–505 |
| `RoundInitialiseEvent` | `SeatTemplateCommit` | `round_initialise_aborted(...)` | lines 1248–1256 |
| `TemplateCommitEvent` | participant setup (`SeatParticipantSetupOrAbort`) | `template_commit_participant_setup_aborted(...)` | lines 1280–1281 |
| `SeatParticipantSetupOrAbort` | `SeatPrepareParticipants` | `participant_setup_aborted(...)` (round aborted) | lines 1438–1443 |
| `ExhaustionAdjudicate` | `SeatFullRangeExhaust` | `RoundAbort(full_range_exhaust_seat_failed_round_abort(...))` | lines 3895–3900 |
| `PublishTerminalRoundAndSeatNext` | `SeatNextRoundBootstrap` (rotation) | `terminal_round_published_seat_failed(brid, reason)` | lines 6564–6566 |

The rotation owner `PublishTerminalRoundAndSeatNext` (`PROCEDURE PublishTerminalRoundAndSeatNext`, line 6527) confirms
the same discipline for the NEXT round:

```
6560    SET boot <- CALL SeatNextRoundBootstrap(RunContext)
6561    SWITCH boot:
6562      CASE round_bootstrap_seated(event_ref, _, _):      RETURN terminal_round_published_and_seated(brid, event_ref)
6564      CASE round_bootstrap_seat_failed(_, reason):
6565        RECORD next_round_bootstrap_seat_failed(brid, reason)     # AH6: the next round could not be seated (declared)
6566        RETURN terminal_round_published_seat_failed(brid, reason)
```

The AH5 deferral in `TemplateCommitEvent` (line 1273, `template_committed_participant_setup_deferred`) is NOT a false
success: it is a distinct declared disposition that explicitly signals participant setup is not yet seated, with
`MinerRegister` (§6) seating it on barrier completion. No caller returns a "seated"/"committed"/"completed" success
result when its required successor's seat failed.

**Finding: PASS.** Every required-successor seat failure yields a declared abort / no-round / seat-failed disposition;
no success is returned over a failed successor.

---

## Overall verdict

**PASS.** All seven verification items pass. Across the round-bootstrap chain
(`SeatNextRoundBootstrap -> RoundInitialiseEvent -> SeatTemplateCommit -> TemplateCommitEvent ->
SeatPrepareParticipants -> PrepareParticipantsEvent`) every required-successor seat result is inspected and turned into
a declared disposition: the first bootstrap failure takes the safe `FinalizeSimulationRunNoRound` /
`run_aborted_no_round` no-round path with no null-`RoundContext` dereference; template-commit, participant-setup, and
full-range-exhaust seat failures each abort the round with their declared `*_round_abort` reason; and the AH5 first-round
admission imports the genesis miner set behind the initial-registration barrier, advances it in `MinerRegister`, seats
participant setup exactly once on completion, and guards `PrepareParticipantsForNewRound` with
`participant_setup_registration_barrier_pending`. The algorithm remains **PoCol** with **the idle policy within PoCol**,
and the A1 baseline of `8.420833333 kWh` is unchanged.
