# Stage 1M — Applicability-Entry Census Audit (M2: census on EVERY floor-applicable round entry)

Documentation-only audit of correction **M2**: a coherent applicability-entry census (K7) is now
captured on EVERY entry into a floor-applicable round state, not only on the assignment-phase entry to
`HASHING`. Correction M2 introduces the single round-state helper `TransitionRoundState` (§2a-bis),
which bumps `state_version` (G10) and, whenever the new state is floor-applicable
(`HASHING`, `SOLUTION_PROPAGATION`, `SECURITY_RECOVERY`), calls
`CaptureSecurityCensusOnApplicabilityEntry` (§9) at `dispatch_envelope.event_time`. All three executable
floor-applicable ENTRY transitions route through the helper: `ASSIGNMENT -> HASHING` via
`CompleteAssignmentPhase` (§2b), `HASHING -> SOLUTION_PROPAGATION` via `ScheduleSolutionPropagation`
(§16b), and — the KEY fix — the `SOLUTION_PROPAGATION -> HASHING` re-entry via `HandlePropagationFailure`
(§16d-bis), which now captures the census directly on `HASHING` entry rather than relying on resumed
miners' boundaries. The ONE floor-applicable entry not routed through the helper is the
`SecurityFloorEvaluate` epilogue's direct `HASHING`/`SOLUTION_PROPAGATION -> SECURITY_RECOVERY` (§9): its
census is the one the epilogue has just evaluated, so re-capturing would re-dirty a finalising
`event_time` (forbidden) — a documented exception, not a gap. This binds to
`STAGE_01_PROTOCOL_PSEUDOCODE.md` §2a-bis (`PROCEDURE TransitionRoundState`), §2b
(`PROCEDURE CompleteAssignmentPhase`), §16b (`PROCEDURE ScheduleSolutionPropagation`), §16d-bis
(`PROCEDURE HandlePropagationFailure`), §9 (`CaptureSecurityCensusOnApplicabilityEntry`,
`FinalizeEventTimeSecurityCensus`, `SecurityFloorEvaluate`), §0.8 (registries; J1/K7 two coherent
writers) and §0.9 (`ApplyMinerStateTransition`, F6); and to `STAGE_01_ROUND_STATE_MACHINE.md` R4
(`ASSIGNMENT -> HASHING`) and R13 (the non-executable `SECURITY_RECOVERY -> HASHING` restore). It
describes **PoCol** with **the idle policy within PoCol** enabled and claims **no property** (energy,
security, fairness, incentive) beyond the census-capture structure defined here; no new consensus
feature is introduced, the eight miner states and the round-state machine are unchanged, and the A1
continuous full-participation baseline (`8.420833333 kWh`) is UNCHANGED — any modeled energy change is
attributable ONLY to reduced active power-time.

---

## 1. The corrected-away problem (a floor-applicable re-entry captured no census of its own)

Under Stage 1K, `CaptureSecurityCensusOnApplicabilityEntry` (§9) was wired at exactly two entry points —
`CompleteAssignmentPhase` for `HASHING` and `ScheduleSolutionPropagation` for `SOLUTION_PROPAGATION` —
so the `ASSIGNMENT -> HASHING` (R4) and `HASHING -> SOLUTION_PROPAGATION` (E6) entries each captured a
census on entry. But the `SOLUTION_PROPAGATION -> HASHING` re-entry inside `HandlePropagationFailure`
(§16d-bis) did NOT capture a census of its own. Stage 1L documented that re-entry's census as
"captured at resumed miners' `ApplyMinerStateTransition` boundaries (J1)" — i.e. it depended on some
miner-state boundary occurring at the re-entry's `event_time` to mark `security_census_dirty[t]`.

That dependence is not guaranteed at the re-entry `event_time`. A `HandlePropagationFailure` may return
the round to `HASHING` while:
- **no miner was paused by the failing candidate** (nothing to resume, so no boundary fires),
- **all resumes carry positive wake latency** (their `WAKING -> ACTIVE_HASHING` boundary fires at a
  strictly LATER `event_time`, not at the re-entry), or
- **`H_active` did not change** at the exact re-entry transition (no census-changing boundary at `t`).

In any of these cases `security_census_dirty[t]` stayed unset at the re-entry `event_time`, so the
event-time epilogue `FinalizeEventTimeSecurityCensus(t)` (§9) returned `no_census_change` and **no floor
decision fired on the `HASHING` re-entry**, even though `HASHING` is floor-applicable (J6). The floor
could therefore be un-evaluated at a re-entry into a floor-applicable state — a narrower version of the
same gap Stage 1K closed for the assignment-phase entry.

## 2. The correction (M2) — one round-state helper captures on every floor-applicable entry

M2 makes census capture a property of the round-state transition itself. §2a-bis introduces the single
helper `TransitionRoundState(RoundContext, new_state, dispatch_envelope)`, whose body is:

```
    TRANSITION round_state -> new_state                          # bumps state_version (G10)
    IF new_state in {HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY}:      # floor-applicable states (J6)
      CALL CaptureSecurityCensusOnApplicabilityEntry(RoundContext, entered_state = new_state,
                                                     at = dispatch_envelope.event_time)   # M2/K7
```

Because the capture is guarded ONLY by `new_state in {HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY}`,
any transition routed through the helper into a floor-applicable state captures a coherent census
UNCONDITIONALLY — independent of whether any miner-state boundary occurred at that `event_time`.
`CaptureSecurityCensusOnApplicabilityEntry` (§9) writes `security_census_dirty[at]` **and**
`latest_security_census[at]` (with full J8 provenance) TOGETHER in one `ATOMICALLY` block, so J1 coherence
(`dirty[t] = true => latest[t] exists`) holds for the helper's writer exactly as for
`ApplyMinerStateTransition` (§0.9 step (5f), F6). It remains the SECOND of the two coherent writers (§0.8
J1/K7 note); M2 does not add a third writer, it only wires the existing second writer onto every
floor-applicable entry through one helper.

The three executable floor-applicable ENTRY transitions are routed through the helper:

- **§2b `CompleteAssignmentPhase`** — `CALL TransitionRoundState(RoundContext, HASHING, dispatch_envelope)`
  (`# R4 + K7 capture (M2)`) is the SOLE executable `ASSIGNMENT -> HASHING` step (R4). The former in-line
  `TRANSITION round_state -> HASHING` is subsumed by the helper's primitive; both assignment-phase routes
  (§2a `PrepareParticipantsForNewRound`, §19 `TemplateRefresh`) reach it through this one procedure (L2).
- **§16b `ScheduleSolutionPropagation`** — on the FIRST propagation-active context while `round_state =
  HASHING`, `CALL TransitionRoundState(RoundContext, SOLUTION_PROPAGATION, dispatch_envelope)`
  (`# M2 (+ K7 capture)`) performs `HASHING -> SOLUTION_PROPAGATION` (E6) and captures on entry.
- **§16d-bis `HandlePropagationFailure`** — when the failure makes propagation quiescent and the round is
  still `SOLUTION_PROPAGATION`, `CALL TransitionRoundState(RoundContext, HASHING, dispatch_envelope)`
  (`# M2: re-entry + applicability census`) performs the `SOLUTION_PROPAGATION -> HASHING` re-entry AND
  captures the census on that `HASHING` entry. The §16d-bis text states verbatim that this capture "is
  REQUIRED even when no miner was paused, all resumes carry positive wake latency, or `H_active` did not
  change at this exact transition." **This is the M2 fix**: the Stage-1L "captured at resumed miners'
  boundaries" reliance is replaced by a direct, unconditional capture on the re-entry.

The re-entry is still NOT routed through `CompleteAssignmentPhase` (whose precondition is `round_state =
ASSIGNMENT` with a freshly-bound `PENDING` set); it is a distinct round-state-machine re-entry. Under M2,
BOTH the assignment-phase `HASHING` entry and the propagation-failure `HASHING` re-entry capture the
census, via the same helper — the requirement is no longer restricted to assignment-phase entries.

## 3. Every round-state transition site, classified

The following table enumerates every `TRANSITION round_state -> X` and every `TransitionRoundState(...,
X, ...)` site in `STAGE_01_PROTOCOL_PSEUDOCODE.md`, its target's floor-applicability (J6), whether it is
routed through the §2a-bis helper, and whether/where a census is captured.

| Site (procedure, §) | Form | Edge | Floor-applicable target? | Routed via `TransitionRoundState`? | Census capture? |
|---|---|---|---|:--:|---|
| §2a-bis `TransitionRoundState` | `TRANSITION round_state -> new_state` (helper primitive) | parameterised | depends on `new_state` | is the helper | captures IFF `new_state in {HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY}` (§9) |
| §2b `CompleteAssignmentPhase` | `CALL TransitionRoundState(…, HASHING, …)` (`# R4 + K7`) | `ASSIGNMENT -> HASHING` (R4) | **Yes** | **Yes** | **captures** on `HASHING` entry (K7); floor decided even at `H_active = 0` |
| §16b `ScheduleSolutionPropagation` | `CALL TransitionRoundState(…, SOLUTION_PROPAGATION, …)` (`# M2`) | `HASHING -> SOLUTION_PROPAGATION` (E6) | **Yes** | **Yes** | **captures** on `SOLUTION_PROPAGATION` entry (K7) |
| §16d-bis `HandlePropagationFailure` | `CALL TransitionRoundState(…, HASHING, …)` (`# M2: re-entry`) | `SOLUTION_PROPAGATION -> HASHING` re-entry | **Yes** | **Yes** | **captures** on `HASHING` re-entry (K7) — regardless of pause/resume-latency/`H_active` (**the M2 fix**) |
| §9 `SecurityFloorEvaluate` | `TRANSITION round_state -> SECURITY_RECOVERY` (direct) | `HASHING`/`SOLUTION_PROPAGATION -> SECURITY_RECOVERY` | **Yes** | **No** (documented exception) | none — census already evaluated by the epilogue at this `event_time`; re-capturing would re-dirty a finalising `event_time` (forbidden) |
| §1 `RoundInitialise` | `TRANSITION round_state -> ROUND_INITIALISING` (direct) | (round start) `-> ROUND_INITIALISING` | No (setup) | No | none (non-applicable, correct) |
| §1 `RoundInitialise` | `TRANSITION round_state -> TEMPLATE_COMMITMENT` (direct) | `ROUND_INITIALISING -> TEMPLATE_COMMITMENT` | No (setup) | No | none (non-applicable, correct) |
| §2 `TemplateCommit` | `TRANSITION round_state -> ASSIGNMENT` (direct) | `TEMPLATE_COMMITMENT -> ASSIGNMENT` | No (setup) | No | none (non-applicable, correct) |
| §17 `ValidBlockAccept` | `TRANSITION round_state -> ROUND_ACCEPTED` (direct) | `SOLUTION_PROPAGATION`/`SECURITY_RECOVERY -> ROUND_ACCEPTED` | No (terminal) | No | none (non-applicable, correct) |
| §18 `FullRangeExhaustNoSolution` | `TRANSITION round_state -> ROUND_EXHAUSTED` (direct) | `HASHING -> ROUND_EXHAUSTED` | No (exhausted) | No | none (non-applicable, correct) |
| §19 `TemplateRefresh` | `TRANSITION round_state -> TEMPLATE_REFRESH` (direct) | `ROUND_EXHAUSTED`/`HASHING -> TEMPLATE_REFRESH` | No (refresh) | No | none (non-applicable, correct) |
| §19 `TemplateRefresh` | `TRANSITION round_state -> TEMPLATE_COMMITMENT` (direct) | `TEMPLATE_REFRESH -> TEMPLATE_COMMITMENT` | No (setup) | No | none (non-applicable, correct) |
| §20 `RoundAbort` | `TRANSITION round_state -> ROUND_ABORTED` (direct) | `* -> ROUND_ABORTED` | No (terminal) | No | none (non-applicable, correct) |

Reading the table: EVERY floor-applicable target is either captured through the helper (the three
`CALL TransitionRoundState` rows) or is the single epilogue exception (`SecurityFloorEvaluate`'s
`-> SECURITY_RECOVERY`). No floor-applicable entry other than that exception is reached by a direct
`TRANSITION round_state -> X`. The remaining direct transitions all target non-applicable states
(setup / refresh / exhausted / terminal), for which capturing nothing is correct — and would be a
no-op through the helper's guard in any case. There is no executable `SECURITY_RECOVERY -> HASHING`
restore transition anywhere in the pseudocode (round SM R13 is described but not executable; §2a-bis and
§16d-bis both note this), so there is no fourth floor-applicable entry to wire.

## 4. Acceptance properties (asserted with evidence)

| # | Property | Result | Evidence |
|---|----------|--------|----------|
| P1 | EVERY entry into `HASHING` captures a coherent applicability census | **HOLDS** | The only two executable `HASHING` entries are `ASSIGNMENT -> HASHING` (§2b `CompleteAssignmentPhase`, `CALL TransitionRoundState(…, HASHING, …)`) and the `SOLUTION_PROPAGATION -> HASHING` re-entry (§16d-bis `HandlePropagationFailure`, `CALL TransitionRoundState(…, HASHING, …)`); both route through the §2a-bis helper, whose guard fires `CaptureSecurityCensusOnApplicabilityEntry(HASHING, at)` (§9) writing `dirty` + `latest` atomically (J1). No `SECURITY_RECOVERY -> HASHING` restore exists (R13 non-executable) |
| P2 | The `SOLUTION_PROPAGATION -> HASHING` re-entry captures a census regardless of whether any miner was paused or `H_active` changed | **HOLDS** | §16d-bis routes the re-entry through the helper; the helper's capture is guarded ONLY by floor-applicability, not by any boundary. §16d-bis states the capture "is REQUIRED even when no miner was paused, all resumes carry positive wake latency, or `H_active` did not change at this exact transition." The Stage-1L "captured at resumed miners' boundaries" reliance is removed |
| P3 | The requirement is NOT weakened to "assignment-phase `HASHING` entries only" | **HOLDS** | The census is captured on the assignment-phase entry (§2b) AND on the non-assignment-phase propagation-failure re-entry (§16d-bis), through the same §2a-bis helper. The re-entry is a distinct round-SM edge (NOT R4) and is correctly not routed through `CompleteAssignmentPhase`, yet still captures via the helper |
| P4 | A single round-state helper captures automatically whenever the new state is floor-applicable, with the epilogue `SECURITY_RECOVERY` entry as the sole principled exception | **HOLDS** | §2a-bis `TransitionRoundState` is the single owner; its `IF new_state in {HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY}` captures automatically. The lone floor-applicable entry not routed through it is §9 `SecurityFloorEvaluate`'s direct `-> SECURITY_RECOVERY`, whose census the epilogue just evaluated (§9 NOTE; re-dirtying a mid-epilogue `event_time` is forbidden) |

## 5. The `SECURITY_RECOVERY` epilogue entry is the sole principled exception

Entry to `SECURITY_RECOVERY` is reached ONLY from inside `SecurityFloorEvaluate` (§9), which is itself
invoked by the event-time epilogue `FinalizeEventTimeSecurityCensus(at)` (I-01/I-02) on an
already-coherent census that the epilogue has just read and whose `security_census_dirty[at]` it has
just cleared. That entry is the RESULT of a floor decision on the census at `at`, not a fresh
applicability boundary needing its own census. Routing it through `TransitionRoundState` would call
`CaptureSecurityCensusOnApplicabilityEntry(SECURITY_RECOVERY, at)`, which sets
`security_census_dirty[at] <- true` while the epilogue for `at` is mid-run and about to finalise it —
re-dirtying an `event_time` whose epilogue has already consumed its census. The §9 NOTE forbids this
verbatim, and §2a-bis records that `SecurityFloorEvaluate` "therefore keeps its direct transition …
and it is the ONLY round-state transition not routed through this helper." The round-state enum still
admits `SECURITY_RECOVERY` as a floor-applicable value for `SecurityFloorEvaluate`'s own applicability
guard; no call site captures on entry to it. This is a documented exception, not a coverage gap.

## 6. Acceptance-style PASS checklist

| # | Check | Result | Ground |
|---|-------|--------|--------|
| C1 | A single helper `TransitionRoundState` owns non-epilogue round-state transitions and captures on floor-applicable targets | PASS | §2a-bis `PROCEDURE TransitionRoundState`; `IF new_state in {HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY}` |
| C2 | `ASSIGNMENT -> HASHING` (R4) captures on entry via the helper | PASS | §2b `CALL TransitionRoundState(…, HASHING, …)` (`# R4 + K7`) |
| C3 | `HASHING -> SOLUTION_PROPAGATION` (E6) captures on entry via the helper | PASS | §16b `CALL TransitionRoundState(…, SOLUTION_PROPAGATION, …)` on the first propagation-active context |
| C4 | The `SOLUTION_PROPAGATION -> HASHING` re-entry captures on entry via the helper — the M2 fix, unconditional of pause / resume-latency / `H_active` | PASS | §16d-bis `CALL TransitionRoundState(…, HASHING, …)`; §16d-bis capture-required note |
| C5 | The re-entry is a distinct round-SM edge (NOT R4), correctly not routed through `CompleteAssignmentPhase`, yet still captures | PASS | §16d-bis gate `IF round_state = SOLUTION_PROPAGATION AND propagation_quiescent`; §2b precondition `round_state = ASSIGNMENT` |
| C6 | Capture writes `security_census_dirty[at]` and `latest_security_census[at]` together atomically (J1) with full provenance (J8) | PASS | §9 `CaptureSecurityCensusOnApplicabilityEntry` `ATOMICALLY` block; §0.8 J1/K7 two-writer note |
| C7 | The epilogue `SECURITY_RECOVERY` entry is the sole floor-applicable entry not routed through the helper (re-dirtying a finalising `event_time` forbidden) | PASS | §9 `SecurityFloorEvaluate` direct `TRANSITION round_state -> SECURITY_RECOVERY`; §9 NOTE; §2a-bis NOTE |
| C8 | Non-applicable transitions (setup / refresh / exhausted / terminal) capture nothing — correct | PASS | §1/§2/§17/§18/§19/§20 direct `TRANSITION round_state -> X` for non-applicable targets |
| C9 | No executable `SECURITY_RECOVERY -> HASHING` restore transition exists (round SM R13) | PASS | No such site in the pseudocode; §2a-bis and §16d-bis notes; `STAGE_01_ROUND_STATE_MACHINE.md` R13 |
| C10 | No new consensus feature; the idle policy within PoCol; A1 baseline `8.420833333 kWh` unchanged | PASS | Census-capture-triggering audit only; §0.8/§0.9/§9 registries and hook unchanged in kind |

Exercised by **TV99** (M2 census on the `SOLUTION_PROPAGATION -> HASHING` re-entry with no paused miner)
in `STAGE_01M_SEMANTIC_TEST_VECTORS.md`; the J1 atomic-coherence structure and the K7 applicability-entry
capture are corroborated by `STAGE_01K_SECURITY_APPLICABILITY_AUDIT.md` (TV90) and
`STAGE_01J_SECURITY_CENSUS_COHERENCE_AUDIT.md`; the single-owner routing of the `ASSIGNMENT -> HASHING`
edge is corroborated by `STAGE_01L_ASSIGNMENT_PHASE_UNIFICATION_AUDIT.md`.

---

## Result

**Result: APPLICABILITY-ENTRY CENSUS AUDIT (Stage 1M): PASS** — correction M2 makes the applicability-entry
census (K7) capture on EVERY entry into a floor-applicable round state through the single helper
`TransitionRoundState` (§2a-bis), which bumps `state_version` (G10) and, whenever the new state is
`HASHING`/`SOLUTION_PROPAGATION`/`SECURITY_RECOVERY`, calls `CaptureSecurityCensusOnApplicabilityEntry`
(§9) at `dispatch_envelope.event_time`, writing `security_census_dirty`/`latest_security_census`
together atomically (J1/J8); all three executable floor-applicable ENTRY transitions route through it —
`ASSIGNMENT -> HASHING` via `CompleteAssignmentPhase` (§2b, R4), `HASHING -> SOLUTION_PROPAGATION` via
`ScheduleSolutionPropagation` (§16b, E6), and the KEY fix, the `SOLUTION_PROPAGATION -> HASHING` re-entry
via `HandlePropagationFailure` (§16d-bis), which now captures a census directly on `HASHING` entry even
when no miner was paused, all resumes carry positive wake latency, or `H_active` did not change (replacing
the Stage-1L "captured at resumed miners' boundaries" reliance) — so every `HASHING` entry captures a
coherent census, the re-entry captures regardless of pause/`H_active`, and the requirement is NOT weakened
to assignment-phase entries only; the sole floor-applicable entry not routed through the helper is the
`SecurityFloorEvaluate` epilogue's direct `-> SECURITY_RECOVERY` (§9), whose census the epilogue has just
evaluated and where re-capturing would re-dirty a finalising `event_time` (forbidden) — a documented
exception, not a gap — while all non-applicable transitions (setup/refresh/exhausted/terminal) correctly
capture nothing and no executable `SECURITY_RECOVERY -> HASHING` restore transition exists (round SM R13);
with §2a-bis/§2b/§16b/§16d-bis/§9, R4/R13, and J1/K7 all agreeing, no new consensus feature, the idle
policy within PoCol described as a mechanism only, and the A1 baseline `8.420833333 kWh` unchanged (any
energy change attributable only to reduced active power-time).
