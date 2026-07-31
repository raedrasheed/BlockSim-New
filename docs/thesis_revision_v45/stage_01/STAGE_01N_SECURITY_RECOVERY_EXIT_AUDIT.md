# Stage 1N — Security-Recovery Exit Audit (N2: executable recovery-completion path, round-SM R13/R14)

Documentation-only audit of correction **N2**: the round-state-machine recovery-**exit** contracts
R13 (`FloorRestored`) and R14 (`FloorUnrecoverable`) are now EXECUTABLE through a single named
procedure `CompleteSecurityRecovery` (§10a), a dispatched sim-driver entry point seated on the queue by
the event-time epilogue's floor-restored decision (§9/N2) at `(t_next, RECOVERY_COMPLETE)` (§0.7g-driver/N3).
The `SecurityFloorEvaluate` epilogue itself performs **no** inline recovery-exit transition (I-02): on the
new floor-restored branch (`NOT breach AND round_state = SECURITY_RECOVERY`) it SEATS exactly one
`CompleteSecurityRecovery` event at a **strictly-later** `event_time`, microphase `RECOVERY_COMPLETE`,
carrying the settled `floor_result` and the decision epoch (`RoundID`/`TemplateID`/`state_version`, J8).
The dispatched procedure then executes one of four branches — **A** live propagation contexts remain
(`SECURITY_RECOVERY → SOLUTION_PROPAGATION` via `TransitionRoundState`, preserving those candidates'
contexts and events); **B** no context and no assignment change (`SECURITY_RECOVERY → HASHING` via
`TransitionRoundState`); **C** redistribution needed (`SECURITY_RECOVERY → ASSIGNMENT`, build the valid
disjoint set via `ReserveActivate` / reassignment, then `CompleteAssignmentPhase → HASHING`, **no new
template**); **D** floor unrecoverable (`RoundAbort(reason = floor_unrecoverable)`, N1). This binds to
`STAGE_01_PROTOCOL_PSEUDOCODE.md` §10a (`PROCEDURE CompleteSecurityRecovery`), §9
(`SecurityFloorEvaluate` floor-restored branch + `FinalizeEventTimeSecurityCensus`,
`CaptureSecurityCensusOnApplicabilityEntry`), §2a-bis (`TransitionRoundState`, whose NOTE now records the
recovery-EXIT transitions as executable and routed through the helper), §2b (`CompleteAssignmentPhase`),
§10 (`ReserveActivate`), §20 (`RoundAbort`), §0.7g-driver (the `CompleteSecurityRecovery` seating row) and
§21 (item 13a); and to `STAGE_01_ROUND_STATE_MACHINE.md` rows R13/R14 and §3.10 (now marked EXECUTABLE via
`CompleteSecurityRecovery`). It describes **PoCol** with **the idle policy within PoCol** enabled and
claims **no property** (energy, security, fairness, incentive) beyond the executable-completion-path
structure defined here; no new consensus feature is introduced (R13/R14 are EXISTING round-SM contracts made
executable, not new transitions), the ten round states and eight miner states are unchanged, and the A1
continuous full-participation baseline (`8.420833333 kWh`) is UNCHANGED — any modeled energy change is
attributable ONLY to reduced active power-time. The prohibited rebranded-algorithm name variants are not
used anywhere in this document.

---

## 1. The corrected-away problem (R13/R14 described but non-executable)

The round transition table gives R13 (`SECURITY_RECOVERY → {ASSIGNMENT/HASHING/SOLUTION_PROPAGATION}` on
`FloorRestored`) and R14 (`SECURITY_RECOVERY → ROUND_ABORTED` on `FloorUnrecoverable`) as legal round
transitions. Before N2, no procedure PERFORMED them: the security path could ENTER `SECURITY_RECOVERY`
(via `SecurityFloorEvaluate`'s breach branch, §9), but there was no named, dispatched step that EXITED it.
The prior Stage-1M audit recorded this verbatim — "There is no executable `SECURITY_RECOVERY → HASHING`
restore transition anywhere in the pseudocode (round SM R13 is described but not executable)" — and §2a-bis
and §16d-bis both carried the same "described but not executable" note. Two consequences followed:

- **R13/R14 had no owner.** The recovery-EXIT edge existed only as a table row and prose; nothing seated
  or dispatched it, so the round-state machine could reach `SECURITY_RECOVERY` with no specified executable
  return to a hashing/propagation state or to `ROUND_ABORTED`.
- **The exit, if written inline, would have violated I-02.** The single floor decision is the event-time
  epilogue `FinalizeEventTimeSecurityCensus(t) → SecurityFloorEvaluate` (§9), run once after `t` is
  quiescent. Performing a participation-changing recovery-exit transition INSIDE that epilogue would alter
  the census the epilogue has just finalised at `t` — forbidden by I-02 (a participation action produced by
  the security decision must be scheduled at a **strictly later** `event_time`).

## 2. The correction (N2) — one named procedure, seated by the epilogue at a strictly-later `event_time`

N2 makes the recovery exit an executable, dispatched step and leaves the epilogue as a pure census
decision. Two coordinated edits:

**(a) §9 `SecurityFloorEvaluate` — the floor-restored branch SEATS, never transitions.** On
`(NOT breach) AND round_state = SECURITY_RECOVERY`, the epilogue performs NO round-state transition; it
ensures exactly one `CompleteSecurityRecovery` is scheduled for this recovery episode via

```
    ENSURE exactly one CompleteSecurityRecovery is scheduled for THIS recovery episode via
           CALL ScheduleEvent(EQ, RoundContext, CompleteSecurityRecovery,
                              target_event_time = t_next (strictly > t), target_microphase = RECOVERY_COMPLETE,
                              {floor_result = restored, RoundID_at_decision = RoundID_current,
                               TemplateID_at_decision = TemplateID_committed,
                               state_version_at_decision = state_version_current})   # N2/N3/I-02
    RETURN floor_restored_scheduled
```

so the R13 transition happens in a dispatched handler with its own `dispatch_envelope`, carrying the
settled floor result and the epoch the decision was produced under (J8). The persistent-breach and
breach-entry branches are unchanged (a continuing breach in `SECURITY_RECOVERY` still records
`breach_persists` with no self-transition and no `state_version` bump).

**(b) §10a `CompleteSecurityRecovery` — the executable owner.** A dispatched sim-driver entry point
(§0.7g-driver row: event type `CompleteSecurityRecovery`, microphase `RECOVERY_COMPLETE`, stable tie key
`(RoundID, state_version)`, may create same-time delta-cycle events for branch C's
`CompleteAssignmentPhase`/`ReserveActivate`). It opens with a **stale-decision guard** and then dispatches
the four branches:

```
    IF round_state != SECURITY_RECOVERY
       OR RoundID_at_decision != RoundID_current OR TemplateID_at_decision != TemplateID_committed
       OR state_version_at_decision != state_version_current:
      RETURN recovery_completion_stale_noop
    IF NOT floor_result = restored:                       # (D) R14 -> abort THIS round (N1)
      RETURN CALL RoundAbort(RoundContext, reason = floor_unrecoverable, dispatch_envelope = dispatch_envelope)
    IF active_propagation_set is non-empty:               # (A) R13/G8 -> resume propagation, contexts preserved
      ASSERT every cpc ... retains its status in {PROPAGATING, PENDING_ACCEPTANCE} AND its scheduled events are intact
      CALL TransitionRoundState(RoundContext, SOLUTION_PROPAGATION, dispatch_envelope)
    ELSE IF recovery restored coverage WITHOUT any range redistribution or new reserve assignment:
      CALL TransitionRoundState(RoundContext, HASHING, dispatch_envelope)               # (B) R13 -> HASHING
    ELSE:                                                 # (C) R13 -> ASSIGNMENT -> CompleteAssignmentPhase -> HASHING
      TRANSITION round_state -> ASSIGNMENT
      BUILD/COMPLETE the valid disjoint set under (RoundID_current, TemplateID_committed)  # no new template
      CALL CompleteAssignmentPhase(RoundContext, dispatch_envelope)
```

The `RECOVERY_COMPLETE` event is always seated at a **strictly-later** `event_time` than the decision that
produced it (§21 item 13a; I-02/N2), so the recovery participation action can never alter the census the
epilogue already finalised at `t`. Every prior "described but non-executable" claim for R13 is removed;
§3.10 and rows R13/R14 of `STAGE_01_ROUND_STATE_MACHINE.md` now read EXECUTABLE via
`CompleteSecurityRecovery`, and the §2a-bis NOTE records that the recovery-EXIT transitions
`SECURITY_RECOVERY → HASHING` and `SECURITY_RECOVERY → SOLUTION_PROPAGATION` route through the helper.

## 3. Branch table (condition → target state → census-capture procedure → preservation/notes)

The four branches of §10a `CompleteSecurityRecovery`. "Census-capture procedure" is the procedure through
which the branch reaches a floor-applicable state and thereby captures the M2/K7 applicability-entry census
(`CaptureSecurityCensusOnApplicabilityEntry`, §9).

| Branch | Condition (in `CompleteSecurityRecovery`, guard passed, `round_state = SECURITY_RECOVERY`) | Target round state | Census-capture procedure (→ applicability-entry census, M2/K7) | Preservation / notes |
|:--:|---|---|---|---|
| **A** (R13) | `active_propagation_set` is non-empty — live propagation contexts remain (G8) | `SECURITY_RECOVERY → SOLUTION_PROPAGATION` | `TransitionRoundState(…, SOLUTION_PROPAGATION, …)` → captures on `SOLUTION_PROPAGATION` entry | PRESERVES every live `cpc` (status in `{PROPAGATING, PENDING_ACCEPTANCE}`) AND its scheduled certificate/block-arrival events; `ASSERT`ed intact, none cancelled or fabricated (G8) |
| **B** (R13) | no live contexts AND coverage restored WITHOUT any range redistribution or new reserve assignment | `SECURITY_RECOVERY → HASHING` | `TransitionRoundState(…, HASHING, …)` → captures on `HASHING` entry | assignment set unchanged; direct resume of hashing |
| **C** (R13) | range redistribution or reserve assignment is required (else-branch) | `SECURITY_RECOVERY → ASSIGNMENT`, then `ASSIGNMENT → HASHING` | `CompleteAssignmentPhase(…)` → `TransitionRoundState(…, HASHING, …)` (R4/L2) → captures on `HASHING` entry | `SECURITY_RECOVERY → ASSIGNMENT` is a direct `TRANSITION` (not floor-applicable → captures nothing, correct); valid disjoint set rebuilt via `ReserveActivate` (§10) / reassigned accepted unsearched suffixes under the SAME `(RoundID_current, TemplateID_committed)` — **NO new template** (a template change is `TemplateRefresh`, not a recovery exit) |
| **D** (R14) | `NOT floor_result = restored` — floor unrecoverable | `SECURITY_RECOVERY → ROUND_ABORTED` | none — terminal target is not floor-applicable (no census, matching `ValidBlockAccept`) | `RoundAbort(reason = floor_unrecoverable, …)` closes ONLY this round (N1): dispositions candidates, closes assignments, records `round_terminal_time`; performs NO run-end residency settle and NO horizon-`T` reconciliation |
| — | guard fails: `round_state != SECURITY_RECOVERY` OR decision epoch (`RoundID`/`TemplateID`/`state_version`) superseded | none (no-op) | none | `RETURN recovery_completion_stale_noop` — a later decision or the terminal round governs |

Reading the table: every recovery-**success** branch (A/B/C) reaches a floor-applicable state
(`SOLUTION_PROPAGATION` for A, `HASHING` for B and C) through `TransitionRoundState` /
`CompleteAssignmentPhase`, so the M2/K7 applicability-entry census is ALWAYS captured on that entry
(independent of whether any miner-state boundary occurred at the `RECOVERY_COMPLETE` `event_time`). Branch D
targets a terminal state, for which capturing nothing is correct. The intermediate `SECURITY_RECOVERY →
ASSIGNMENT` step of branch C targets a non-applicable state, so its direct `TRANSITION` correctly captures
nothing; the census is captured one step later on the `ASSIGNMENT → HASHING` entry through
`CompleteAssignmentPhase`, the sole executable R4 owner (L2/M2).

## 4. Acceptance properties (asserted with evidence)

| # | Property | Result | Evidence |
|---|----------|--------|----------|
| P1 | R13 has an executable named procedure | **HOLDS** | §10a `PROCEDURE CompleteSecurityRecovery` is a dispatched sim-driver entry point (§0.7g-driver row; §21 item 13a) seated by §9's floor-restored branch (`RETURN floor_restored_scheduled`) at `(t_next, RECOVERY_COMPLETE)`; it performs the `SECURITY_RECOVERY → SOLUTION_PROPAGATION`/`HASHING`/`ASSIGNMENT` transitions. `STAGE_01_ROUND_STATE_MACHINE.md` R13 and §3.10 read "EXECUTABLE via `CompleteSecurityRecovery`"; the §2a-bis NOTE confirms the recovery-EXIT transitions route through the helper. Every "described but non-executable" claim is removed |
| P2 | Every recovery-success branch (A/B/C) captures the required applicability census | **HOLDS** | A: `CALL TransitionRoundState(…, SOLUTION_PROPAGATION, …)`; B: `CALL TransitionRoundState(…, HASHING, …)`; C: `CALL CompleteAssignmentPhase(…)` which calls `TransitionRoundState(…, HASHING, …)` (§2b, R4). §2a-bis's `IF new_state in {HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY}` fires `CaptureSecurityCensusOnApplicabilityEntry` (§9) at `dispatch_envelope.event_time`, writing `security_census_dirty` + `latest_security_census` together atomically (J1/K7). §10a NOTE: "Branches A/B/C reach a floor-applicable state through `TransitionRoundState`/`CompleteAssignmentPhase`, so the applicability-entry census is ALWAYS captured (M2)" |
| P3 | Branch A preserves live candidate contexts + events | **HOLDS** | §10a branch A `ASSERT every cpc in active_propagation_set retains its status in {PROPAGATING, PENDING_ACCEPTANCE} AND its scheduled events are intact` before the transition; NOTE "(A) live candidates → SOLUTION_PROPAGATION (contexts + events PRESERVED, G8)". Consistent with G8 (`SECURITY_RECOVERY` may coexist with a non-empty `active_propagation_set`; entering it does not cancel live contexts) and §16d-bis note that the executable exit "later returns it to SOLUTION_PROPAGATION (live candidates) or HASHING" |
| P4 | Branch C does not fabricate a template | **HOLDS** | §10a branch C rebuilds the valid disjoint set "under `(RoundID_current, TemplateID_committed)`" and comments "A recovery redistribution NEVER fabricates a new template (I1 disjoint ranges under the SAME committed TemplateID)"; NOTE "(C) … no new template". `TemplateID` is unchanged; a template change is `TemplateRefresh` (R11/R15/R17), a distinct edge. R13 note in `STAGE_01_ROUND_STATE_MACHINE.md`: "No new template is fabricated (§3.6)" |
| P5 | Branch D aborts only the round (N1) | **HOLDS** | §10a branch D `RETURN CALL RoundAbort(RoundContext, reason = floor_unrecoverable, …)`. §20 `RoundAbort` (N1) terminates ONE round — dispositions candidates, closes assignments, records `round_terminal_time`, `TRANSITION round_state -> ROUND_ABORTED` — and performs NO run-end residency settle and NO horizon-`T` reconciliation (those belong to `FinalizeSimulationRun`, §20a). §10a NOTE: "(D) floor unrecoverable → RoundAbort(floor_unrecoverable)"; "It never fabricates a template and never settles residency". `STAGE_01_ROUND_STATE_MACHINE.md` R14: "closes ONLY this round (N1)" |
| P6 | The epilogue performs no inline recovery-exit transition; the seated event is strictly later (I-02) | **HOLDS** | §9 floor-restored branch: "The epilogue itself performs NO round-state transition … It SEATS the executable recovery-completion driver `CompleteSecurityRecovery` (§10a) on the queue at a STRICTLY LATER event_time (I-02)"; `ScheduleEvent(… target_event_time = t_next (strictly > t), target_microphase = RECOVERY_COMPLETE …)`; §21 item 13a "always seated at a STRICTLY LATER event_time than the floor decision that produced it (I-02/N2)". §2a-bis precondition: `TransitionRoundState` is "NOT called by the SecurityFloorEvaluate epilogue" |
| P7 | The recovery completion is idempotent-guarded against a stale/superseded decision | **HOLDS** | §10a stale-decision guard `IF round_state != SECURITY_RECOVERY OR RoundID_at_decision != RoundID_current OR TemplateID_at_decision != TemplateID_committed OR state_version_at_decision != state_version_current: RETURN recovery_completion_stale_noop`; §9 seats "exactly one CompleteSecurityRecovery … for THIS recovery episode" |

## 5. Acceptance-style PASS checklist

| # | Check | Result | Ground |
|---|-------|--------|--------|
| C1 | R13/R14 are EXECUTABLE through the single named procedure `CompleteSecurityRecovery` | PASS | §10a `PROCEDURE CompleteSecurityRecovery`; `STAGE_01_ROUND_STATE_MACHINE.md` R13/R14, §3.10 |
| C2 | The epilogue's floor-restored branch SEATS the completion event (no inline transition, I-02) | PASS | §9 `SecurityFloorEvaluate` `(NOT breach) AND round_state = SECURITY_RECOVERY` → `RETURN floor_restored_scheduled`; §9 NOTE |
| C3 | The `RECOVERY_COMPLETE` event is seated at a strictly-later `event_time`, carrying the decision epoch (J8) | PASS | §9 `ScheduleEvent(… t_next (strictly > t) …, {floor_result = restored, RoundID/TemplateID/state_version_at_decision})`; §21 item 13a; §0.7g-driver row |
| C4 | Branch A → `SOLUTION_PROPAGATION` preserving live contexts + events (G8) | PASS | §10a branch A `ASSERT … status in {PROPAGATING, PENDING_ACCEPTANCE} AND scheduled events intact`; `CALL TransitionRoundState(…, SOLUTION_PROPAGATION, …)` |
| C5 | Branch B → `HASHING` directly (no context, no assignment change) via the helper | PASS | §10a branch B `CALL TransitionRoundState(…, HASHING, …)` |
| C6 | Branch C → `ASSIGNMENT` → `CompleteAssignmentPhase` → `HASHING`, no new template | PASS | §10a branch C `TRANSITION → ASSIGNMENT`; build valid set via `ReserveActivate` (§10)/reassignment under `(RoundID_current, TemplateID_committed)`; `CALL CompleteAssignmentPhase(…)` (R4/L2); "no new template" |
| C7 | Every recovery-success branch (A/B/C) captures the applicability-entry census (M2/K7) | PASS | A/B via `TransitionRoundState`; C via `CompleteAssignmentPhase → TransitionRoundState(HASHING)`; §2a-bis guard → `CaptureSecurityCensusOnApplicabilityEntry` (§9); §10a NOTE |
| C8 | Branch D → `RoundAbort(reason = floor_unrecoverable)` closes ONLY this round (N1) | PASS | §10a branch D `CALL RoundAbort(… reason = floor_unrecoverable …)`; §20 `RoundAbort` N1 (no run-end settle, no horizon reconciliation); `STAGE_01_ROUND_STATE_MACHINE.md` R14 |
| C9 | Stale/superseded recovery decision is a no-op | PASS | §10a stale-decision guard → `recovery_completion_stale_noop`; §9 "exactly one per recovery episode" |
| C10 | The `SECURITY_RECOVERY → ASSIGNMENT` intermediate step (branch C) correctly captures nothing (non-applicable) | PASS | §10a branch C direct `TRANSITION round_state -> ASSIGNMENT`; §2a-bis guard fires only for `{HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY}` |
| C11 | No new consensus feature (R13/R14 are existing round-SM contracts made executable); the idle policy within PoCol; A1 baseline `8.420833333 kWh` unchanged | PASS | Executable-completion-path audit only; §10a/§9/§2a-bis wire existing procedures; ten round states / eight miner states unchanged; the idle policy within PoCol |

Corroborated by the applicability-entry census structure of `STAGE_01M_APPLICABILITY_ENTRY_AUDIT.md` (the
M2 `TransitionRoundState` helper and its `CaptureSecurityCensusOnApplicabilityEntry` writer), the K7
capture of `STAGE_01K_SECURITY_APPLICABILITY_AUDIT.md`, and the J1 atomic-coherence of
`STAGE_01J_SECURITY_CENSUS_COHERENCE_AUDIT.md`; the round-abort round-scope (N1) is corroborated by
`STAGE_01_ROUND_STATE_MACHINE.md` §2.10/§3.14 and §20 `RoundAbort`.

---

## Result

**Result: SECURITY-RECOVERY EXIT AUDIT (Stage 1N): PASS** — correction N2 makes the round-SM recovery-EXIT
contracts R13 (`FloorRestored`) and R14 (`FloorUnrecoverable`) EXECUTABLE through the single named procedure
`CompleteSecurityRecovery` (§10a), a dispatched sim-driver entry point (microphase `RECOVERY_COMPLETE`,
§0.7g-driver/§21 item 13a) seated by the event-time epilogue's floor-restored decision (§9,
`RETURN floor_restored_scheduled`) at a STRICTLY-LATER `event_time` (I-02) carrying the settled
`floor_result` and the decision epoch (`RoundID`/`TemplateID`/`state_version`, J8) — the epilogue performing
NO inline transition; a stale-decision guard no-ops a superseded episode, and the four branches are
**A** live contexts remain → `SECURITY_RECOVERY → SOLUTION_PROPAGATION` via `TransitionRoundState`
preserving every live candidate's context and scheduled events (G8), **B** no context / no assignment change
→ `SECURITY_RECOVERY → HASHING` via `TransitionRoundState`, **C** redistribution needed →
`SECURITY_RECOVERY → ASSIGNMENT` (`ReserveActivate`/reassignment under the SAME committed `TemplateID`, no
new template) → `CompleteAssignmentPhase → HASHING` (R4), and **D** floor unrecoverable →
`RoundAbort(reason = floor_unrecoverable)` closing ONLY this round (N1); every recovery-success branch
(A/B/C) reaches a floor-applicable state through `TransitionRoundState`/`CompleteAssignmentPhase`, so the
M2/K7 applicability-entry census is ALWAYS captured (`CaptureSecurityCensusOnApplicabilityEntry`, §9, writing
`security_census_dirty`/`latest_security_census` together atomically, J1) — with §10a/§9/§2a-bis/§2b/§10/§20,
R13/R14 and §3.10, M2 and I-02 all agreeing, no new consensus feature (R13/R14 are existing round-SM
contracts made executable), the idle policy within PoCol described as a mechanism only, and the A1 baseline
`8.420833333 kWh` unchanged (any energy change attributable only to reduced active power-time).
