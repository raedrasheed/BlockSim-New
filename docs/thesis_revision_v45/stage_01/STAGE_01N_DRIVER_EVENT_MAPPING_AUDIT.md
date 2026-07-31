# Stage 1N — Driver Event-Mapping Audit (N3)

A structural audit of the Stage-1N correction **N3** (complete the driver-event microphase map) in the
**PoCol** protocol pseudocode (`STAGE_01_PROTOCOL_PSEUDOCODE.md`). N3 adds §0.7g-driver, a normative
table that gives EVERY sim-driver entry point seated on the event queue a declared event type, target
microphase, stable tie key, required envelope fields, and a declared right (or not) to create SAME-TIME
delta-cycle events. It extends the M5 event-type → microphase mapping (§0.7g) from the ordinary queued
event types to the nine driver entry points, so no driver entry point receives a `dispatch_envelope`
without a normative `ScheduleEvent` seating rule (the envelope is always the dispatched event's own,
§0.7f). This document is documentation only; it audits wording and control structure, describes only
the idle policy within PoCol, introduces no new consensus feature, and claims **no** security, fairness,
energy, or incentive property. The A1 baseline (`8.420833333 kWh`) is unchanged.

---

## 1. The corrected-away problem

- **Before N3.** §0.7g (M5) fixed the target microphase of each ORDINARY queued event type
  (`BlockAcceptancePoint`, `CertificateArrival`, `HashWorkEvent`, `LeaseExpiry`, `WakeCompleteEvent`,
  `ResumeFromPause`, `AdversarialParticipationChangeEvent`, `ActiveHashRateUpdate`). §0.7f/L1 already
  required each SIM-DRIVER entry point to obtain its `dispatch_envelope` as the dispatched event's own
  (seated through `ScheduleEvent`, dispatched by `ProcessEventTime`), but there was no single normative
  table stating, for each driver entry point, its event type, target microphase, stable tie key,
  required envelope fields, and whether it may create same-time delta-cycle events. The driver entry
  points' seating on the queue was therefore governed only by the general §0.7f/L1 prose, not by a
  per-entry-point mapping analogous to the M5 table.
- **After N3.** §0.7g-driver states the seating rules for all nine driver entry points
  (`RoundInitialise`, `TemplateCommit`, `PrepareParticipantsForNewRound`, `MinerRegister`,
  `ReserveActivate`, `FullRangeExhaustNoSolution`, `CompleteSecurityRecovery`, `RoundAbort`,
  `FinalizeSimulationRun`), each with all five columns. §0.7g-driver closes the norm: *"No driver entry
  point receives a `dispatch_envelope` without such a normative `ScheduleEvent` seating rule (the
  envelope is always the dispatched event's own, per §0.7f). `RoundAbort` retains TERMINAL-ABORT
  priority (§21 item 1); `FinalizeSimulationRun` is a RUN-LEVEL terminal action (microphase
  `RUN_FINALISE` …), NOT an ordinary round event."*

## 2. Mechanism

### 2.1 The §0.7g-driver seating table (N3)

N3 adds the fixed table below. Same-timestamp ordering among these driver microphases follows the §21
inter-type order, with `TERMINAL_ABORT` retaining top priority and `RUN_FINALISE` last (a run-level
action processed after every ordinary round microphase). A lower §21 ordinal is the queue order, not a
claim.

| Driver entry point | Event type | Target microphase | Stable tie key | Required envelope fields | May create same-time delta-cycle events? |
|--------------------|-----------|-------------------|----------------|--------------------------|:--:|
| `RoundInitialise` | `RoundInitialise` | `ROUND_SETUP` | `(RoundID)` | `event_time, delta_cycle, event_seq` | no (round setup is a fresh event_time) |
| `TemplateCommit` | `TemplateCommit` | `TEMPLATE_COMMIT` | `(RoundID, TemplateID)` | `event_time, delta_cycle, event_seq` | no |
| `PrepareParticipantsForNewRound` | `PrepareParticipants` | `ASSIGNMENT_SETUP` | `(RoundID, TemplateID)` | `event_time, delta_cycle, event_seq` | yes — its `StartWake`s may seat same-time `WakeCompleteEvent`s (H2/H5) |
| `MinerRegister` | `MinerRegister` | `REGISTRATION` | `(MinerID)` | `event_time, delta_cycle, event_seq` | no |
| `ReserveActivate` | `ReserveActivate` | `RECOVERY_ACTIVATE` | `(MinerID)` | `event_time, delta_cycle, event_seq` | yes — its `StartWake` may seat a same-time `WakeCompleteEvent` (H5) |
| `FullRangeExhaustNoSolution` | `FullRangeExhaust` | `RANGE_EXHAUST_ADJUDICATE` | `(RoundID, TemplateID)` | `event_time, delta_cycle, event_seq` | no |
| `CompleteSecurityRecovery` | `CompleteSecurityRecovery` | `RECOVERY_COMPLETE` | `(RoundID, state_version)` | `event_time, delta_cycle, event_seq` | yes — branch C's `CompleteAssignmentPhase`/`ReserveActivate` may seat same-time events |
| `RoundAbort` | `RoundAbort` | `TERMINAL_ABORT` (§21 item 1) | `(RoundID)` | `event_time, delta_cycle, event_seq` | no |
| `FinalizeSimulationRun` | `FinalizeSimulationRun` | `RUN_FINALISE` (run-level terminal) | `(RunID)` | `event_time (= T), delta_cycle, event_seq` | no (run-level; nothing is scheduled past `T`) |

### 2.2 Relationship to the M5 mapping and the security-floor epilogue

The §0.7g-driver table EXTENDS the §0.7g (M5) event-type → microphase mapping: M5 covers the ordinary
queued events, N3 covers the driver entry points that are themselves seated on the queue. Two
distinctions carry over unchanged:

- The **event-time security-floor decision** (`FinalizeEventTimeSecurityCensus → SecurityFloorEvaluate`)
  is NOT a queued microphase — it is the I-01/I-02 epilogue `ProcessEventTime` runs once after
  quiescence (§0.7d) — so it has no mapping entry in either M5 or the driver table.
- `CompleteSecurityRecovery` (microphase `RECOVERY_COMPLETE`) IS a queued driver event, distinct from
  that epilogue. §0.7g-driver states the two are ordered per I-02: the recovery-completion event is
  always seated at a STRICTLY LATER `event_time` than the floor decision that produced it. This matches
  §9/N2, where the epilogue `ENSURE`s exactly one `CompleteSecurityRecovery` is scheduled via `CALL
  ScheduleEvent(… target_event_time = t_next (strictly > t), target_microphase = RECOVERY_COMPLETE …)`,
  and §10a, which performs the R13 recovery-exit transition in a dispatched handler with its own
  `dispatch_envelope`.

## 3. Cross-check against the procedure signatures (properties 1 and 4)

Each of the nine entry points is a named `PROCEDURE`. The table below cross-checks the §0.7g-driver
seating rule against each procedure's INPUTS.

| # | Driver entry point (§) | Declared seating rule in §0.7g-driver? | Explicit `dispatch_envelope` INPUT? | Threads envelope to a miner transition / `StartWake`? |
|---|---|:--:|:--:|---|
| D1 | `RoundInitialise` §1 | yes (`ROUND_SETUP`) | no | no — round-registry setup + round-state `TRANSITION`s only (no `ApplyMinerStateTransition`, no `StartWake`) |
| D2 | `TemplateCommit` §2 | yes (`TEMPLATE_COMMIT`) | no | no — `BROADCAST` + round-state `TRANSITION` only |
| D3 | `PrepareParticipantsForNewRound` §2a | yes (`ASSIGNMENT_SETUP`) | yes | yes — threads to each `StartWake` / `ApplyMinerStateTransition` |
| D4 | `MinerRegister` §3 | yes (`REGISTRATION`) | yes | yes — threads to the T1 (and optional T2) `ApplyMinerStateTransition` |
| D5 | `ReserveActivate` §10 | yes (`RECOVERY_ACTIVATE`) | yes | yes — threads to `StartWake` (T4) |
| D6 | `FullRangeExhaustNoSolution` §18 | yes (`RANGE_EXHAUST_ADJUDICATE`) | yes | yes — threads to `RoundAbort` / `TemplateRefresh` |
| D7 | `CompleteSecurityRecovery` §10a | yes (`RECOVERY_COMPLETE`) | yes | yes — threads to `TransitionRoundState` / `CompleteAssignmentPhase` / `ReserveActivate` / `RoundAbort` |
| D8 | `RoundAbort` §20 | yes (`TERMINAL_ABORT`) | yes | yes — threads to `CloseRoundAssignments` |
| D9 | `FinalizeSimulationRun` §20a | yes (`RUN_FINALISE`) | yes | yes — threads to `CloseRoundAssignments` / `SettleResidencyBoundary` |

**Property 1 — every listed driver entry point has a declared microphase and envelope seating rule.**
PASS. All nine rows of §0.7g-driver (§2.1) declare a target microphase and required envelope fields
(`event_time, delta_cycle, event_seq`; `event_time = T` for `FinalizeSimulationRun`).

**Property 4 — no driver entry point receives a `dispatch_envelope` without a normative `ScheduleEvent`
seating rule.** PASS. Seven of the nine entry points (D3–D9) carry an explicit `dispatch_envelope`
parameter in their INPUTS, and each has a §0.7g-driver seating rule. `RoundInitialise` (D1) and
`TemplateCommit` (D2) perform only round-registry setup and round-state `TRANSITION`s — they call no
`ApplyMinerStateTransition` and no `StartWake` — so their current signatures list no `dispatch_envelope`
parameter and they receive no envelope to thread; the §0.7g-driver seating rule nonetheless declares
their seated event's required envelope fields. Both directions of property 4 therefore hold: every
entry point that DOES receive a `dispatch_envelope` (D3–D9) has a declared seating rule, and the two
that thread none (D1, D2) receive no undeclared envelope. This is consistent with §0.7f/L1, which binds
a driver `DriverEventEnvelope` to EXACTLY ONE source — the entry point seated through `ScheduleEvent`
and dispatched by `ProcessEventTime` — and withdraws the manual `next EQ.event_creation_seq` form.

## 4. §21-consistency check (properties 2 and 3)

The driver microphases are ordered by the §21 inter-type contract. The relevant §21 items:

| §21 ordinal / line | §21 entry | Driver microphase | Consistent with §0.7g-driver? |
|---|---|---|:--:|
| item **1** | `RoundAbort` closure (`ROUND_ABORTED`) | `TERMINAL_ABORT` | yes — top same-timestamp priority |
| item **13a** | Recovery completion (`CompleteSecurityRecovery → R13 exit`), *"always seated at a STRICTLY LATER `event_time` than the floor decision that produced it (I-02/N2)"* | `RECOVERY_COMPLETE` | yes — seated at `t_next` (strictly `> t`) by §9/N2 |
| run-level line `—` | Run-level finalisation (`FinalizeSimulationRun`), *"processed AFTER every ordinary round event of every event_time up to and including the horizon `T`; NOT a round event and NOT the same as RoundAbort (item 1)"* | `RUN_FINALISE` | yes — run-level terminal, after all ordinary round events |

**Property 2 — `RoundAbort` retains terminal-abort priority.** PASS. §0.7g-driver maps `RoundAbort`
to `TERMINAL_ABORT` and annotates it "(§21 item 1)"; §21's inter-type list places `RoundAbort` closure
(`ROUND_ABORTED`) at ordinal 1, the highest same-timestamp priority. `RoundAbort` §20 records the abort,
dispositions live candidates, closes assignments via `CloseRoundAssignments`, and `TRANSITION
round_state -> ROUND_ABORTED`; §20 explicitly notes it terminates ONE round and reconciles nothing to
`T` (that is `FinalizeSimulationRun`).

**Property 3 — `FinalizeSimulationRun` is a run-level terminal action, not an ordinary round event.**
PASS. §0.7g-driver maps `FinalizeSimulationRun` to `RUN_FINALISE`, labelled "(run-level terminal)",
with `event_time (= T)` and the note that it is processed after every ordinary round event of every
event_time up to and including the horizon `T`. §21's run-level line states `FinalizeSimulationRun`
(microphase `RUN_FINALISE`, N1) is a RUN-LEVEL terminal action processed AFTER every ordinary round
event, "NOT a round event and NOT the same as RoundAbort (item 1)." §20a confirms it is *"a RUN-LEVEL
terminal event seated on the queue at `(T, RUN_FINALISE)` (§0.7g/N3), NOT an ordinary round event,"* runs
EXACTLY ONCE at `T` (guarded by `run_finalised`), drains every `event_time <= T`, horizon-closes a
nonterminal round, performs the single `FINAL_RUN_END` `SettleResidencyBoundary`, and then runs the
I5/I6/I7 reconciliation.

## 5. Acceptance-style PASS checklist

| # | Check | Result | Ground |
|---|---|---|---|
| C1 | Property 1 — every listed driver entry point has a declared microphase and envelope seating rule | PASS | §0.7g-driver table (§2.1); cross-check D1–D9 (§3) |
| C2 | All nine entry points appear with all five columns (event type, microphase, tie key, envelope fields, delta-cycle right) | PASS | §0.7g-driver table (§2.1) |
| C3 | Property 4 — no driver entry point receives a `dispatch_envelope` without a normative `ScheduleEvent` seating rule | PASS | §3 (D3–D9 carry the envelope + a rule; D1/D2 thread none); §0.7f/L1 |
| C4 | The seven envelope-threading entry points carry an explicit `dispatch_envelope` INPUT | PASS | `PrepareParticipantsForNewRound` §2a; `MinerRegister` §3; `ReserveActivate` §10; `CompleteSecurityRecovery` §10a; `FullRangeExhaustNoSolution` §18; `RoundAbort` §20; `FinalizeSimulationRun` §20a |
| C5 | `RoundInitialise` §1 / `TemplateCommit` §2 do only round-registry setup + round-state `TRANSITION`s (no `ApplyMinerStateTransition`, no `StartWake`), so carry no `dispatch_envelope` parameter, yet still have a declared seating rule | PASS | §1; §2; §0.7g-driver rows 1–2 |
| C6 | Property 2 — `RoundAbort` retains terminal-abort priority | PASS | §0.7g-driver (`TERMINAL_ABORT`, "§21 item 1"); §21 item 1; §20 |
| C7 | Property 3 — `FinalizeSimulationRun` is a run-level terminal action, not an ordinary round event | PASS | §0.7g-driver (`RUN_FINALISE`, "run-level terminal"); §21 run-level line; §20a |
| C8 | `CompleteSecurityRecovery` (`RECOVERY_COMPLETE`) is a queued driver event, seated at a strictly-later `event_time` than the floor decision (I-02/N2) | PASS | §0.7g-driver; §21 item 13a; §9/N2; §10a |
| C9 | The security-floor decision has NO driver-mapping entry (it is the I-01/I-02 epilogue, not a queued microphase) | PASS | §0.7g-driver; §0.7d; §21 |
| C10 | The driver table extends the §0.7g (M5) event-type → microphase mapping | PASS | §0.7g (M5); §0.7g-driver (§2.1) |
| C11 | Same-time delta-cycle rights match handler bodies (D3/D5/D7 seat same-time events via `StartWake`/branch-C; D1/D2/D4/D6/D8/D9 do not) | PASS | §2a; §10; §10a; §3 (MinerRegister, no `StartWake`); §18; §20 |
| C12 | A1 baseline unchanged; no new consensus feature; no property claimed; only the idle policy within PoCol described | PASS | A1 = 8.420833333 kWh; §0 |

---

## Result

**DRIVER EVENT-MAPPING AUDIT (Stage 1N): PASS** — N3 adds §0.7g-driver, the seating-rules table that
gives all nine sim-driver entry points a declared event type, target microphase, stable tie key,
required envelope fields, and delta-cycle right: `RoundInitialise` (`ROUND_SETUP`), `TemplateCommit`
(`TEMPLATE_COMMIT`), `PrepareParticipantsForNewRound` (`ASSIGNMENT_SETUP`), `MinerRegister`
(`REGISTRATION`), `ReserveActivate` (`RECOVERY_ACTIVATE`), `FullRangeExhaustNoSolution`
(`RANGE_EXHAUST_ADJUDICATE`), `CompleteSecurityRecovery` (`RECOVERY_COMPLETE`), `RoundAbort`
(`TERMINAL_ABORT`), and `FinalizeSimulationRun` (`RUN_FINALISE`). Every listed entry point has a
declared microphase and envelope seating rule (property 1); `RoundAbort` retains terminal-abort
priority at §21 item 1 (property 2); `FinalizeSimulationRun` is a run-level terminal action processed
after every ordinary round event of every event_time up to and including the horizon `T`, not an
ordinary round event (property 3); and no driver entry point receives a `dispatch_envelope` without a
normative `ScheduleEvent` seating rule — the seven envelope-threading entry points (§2a, §3, §10, §10a,
§18, §20, §20a) each carry an explicit `dispatch_envelope` INPUT with a declared rule, while
`RoundInitialise` (§1) and `TemplateCommit` (§2) perform only round-registry setup and round-state
`TRANSITION`s and thread no envelope, so receive none undeclared (property 4). The security-floor
decision remains the I-01/I-02 epilogue with no mapping entry, and `CompleteSecurityRecovery` is a
queued driver event seated at a strictly-later `event_time` than the decision that produced it (I-02/N2).
This leaves the A1 baseline (8.420833333 kWh) unchanged, with no new consensus feature and no property
claimed, describing only the idle policy within PoCol.
