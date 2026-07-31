# Stage 1K — Driver Event Envelope Audit (K4)

A structural audit of the Stage-1K correction **K4** (explicit driver event envelopes) in the
**PoCol** protocol pseudocode (`STAGE_01_PROTOCOL_PSEUDOCODE.md`): every `ApplyMinerStateTransition`
call — whether dispatched from a queued handler or initiated at a sim-driver entry point — carries a
DEFINED `(event_time, delta_cycle, event_seq)`, never an ambient one. A sim-driver entry point supplies
an explicit `DriverEventEnvelope` (§0.7f) or seats its action on the queue through `ScheduleEvent`
(§0.7e); no transition depends on an undeclared ambient `event_seq`. This document is documentation
only; it audits wording and control structure, describes only the idle policy within PoCol, introduces
no new consensus feature, and claims **no** security, fairness, energy, or incentive property. The A1
baseline (`8.420833333 kWh`) is unchanged.

---

## 1. The corrected-away ambiguity

- **K4.** Before Stage-1K, a miner-state transition raised by a sim-driver entry point (not a queued
  handler) had no declared source for its `event_seq` — an *ambient undeclared* `event_seq` could
  differ across reruns, making the `TransitionEventID` non-reproducible. Stage-1K requires every such
  entry point to pass an explicit `DriverEventEnvelope` (or to be scheduled through `ScheduleEvent`),
  so `(event_time, delta_cycle, event_seq)` are always DEFINED (§0.7f, requirement **R78**). The
  forbidden behaviour is precisely *"a driver transition depending on an undeclared ambient
  `event_seq`"* (R78).

## 2. Mechanism

### 2.1 `DriverEventEnvelope` (§0.7f)

Per §0.7f, *"a miner-state transition originated by a SIM-DRIVER entry point (not a queued handler)
carries an explicit `DriverEventEnvelope` so its `(event_time, delta_cycle, event_seq)` are DEFINED,
never ambient."* A `DriverEventEnvelope` is created one of two ways:

1. **Seat on the queue via `ScheduleEvent` (preferred).** The driver action enters through the sole
   enqueue interface `ScheduleEvent` (§0.7e/K8), which derives `delta_cycle` and assigns `event_seq`
   from the per-run `event_creation_seq` it owns — the caller supplies only `event_time` + `microphase`.
2. **Explicit stamp from the `EventQueueContext`.** The driver stamps
   `{ event_time = now, delta_cycle = 0, event_seq = next EQ.event_creation_seq }` directly from the
   single `EventQueueContext` (§0.7e), i.e. `event_time = now`, `delta_cycle = 0`, and `event_seq`
   drawn from the ONE per-run monotonic `event_creation_seq` (J4/K8).

Either way the three fields are DEFINED and the `event_seq` originates from the single per-run
`event_creation_seq` counter (`EventQueueContext.event_creation_seq`, §0.7e), never invented locally.

### 2.2 How `ApplyMinerStateTransition` resolves the three fields (§0.9)

`ApplyMinerStateTransition` (§0.9) receives `event_time, delta_cycle, event_seq` in its INPUTS with the
K4 envelope-source note: *"`event_time`/`delta_cycle`/`event_seq` are ALWAYS defined, never ambient."*
Resolution depends on the caller:

| Caller kind | Source of `(event_time, delta_cycle, event_seq)` |
|---|---|
| **QUEUED handler** | the DISPATCHING event's envelope (§0.2); `event_seq =` that event's `event_creation_seq`, assigned by `ScheduleEvent` (J9) |
| **SIM-DRIVER entry point** | an explicit `DriverEventEnvelope` (§0.7f) — or the entry point is itself scheduled through `ScheduleEvent` |

Step (1) of §0.9 then builds the immutable `TransitionEventID` from the full envelope, embedding
`event_time, delta_cycle, event_seq`. Because both branches terminate at the single per-run
`event_creation_seq` (§0.8, J4/K8), *"NO transition depends on an undeclared ambient `event_seq`"*
(§0.9 INPUTS, K4). Step (4)'s envelope-completeness guard REJECTS any call *"missing
event_time/delta_cycle/event_seq"* (`illegal_or_malformed`), so a malformed envelope can never apply.

### 2.3 Driver entry points construct `env`

The driver entry points that transition miners each construct a `DriverEventEnvelope` and pass its
fields (§0.7f):

- **`MinerRegister` (§3).** `SET env <- DriverEventEnvelope(event_time = now, delta_cycle = 0,
  event_seq = next EQ.event_creation_seq)`, then two `ApplyMinerStateTransition` calls pass its fields:
  T1 (`NONE -> REGISTERED`) uses `env.event_time`, `env.delta_cycle`, `env.event_seq`; the OPTIONAL T2
  (`REGISTERED -> RESERVE`) reuses `env.event_time`/`env.delta_cycle` with a FRESH
  `event_seq = next EQ.event_creation_seq`, so the two transitions carry DISTINCT `event_seq`s and
  DISTINCT `TransitionEventID`s.
- **`PrepareParticipantsForNewRound` (§2a).** `SET env <- DriverEventEnvelope(event_time = now,
  delta_cycle = 0, event_seq = next EQ.event_creation_seq)`; every `StartWake` (T3/T4/T10) is invoked
  with `driver_envelope = env`, and `CompleteAssignmentPhase` performs the explicit `ASSIGNMENT ->
  HASHING` step (K2). Enumeration is in stable `MinerID` order (G7) and every action is scheduled via
  `ScheduleEvent` (J9/K8).
- **`RoundInitialise`/`TemplateCommit` participant actions**, and **any direct
  recovery/administrative entry** — each passes a `DriverEventEnvelope` (or is scheduled through
  `ScheduleEvent`); *"no such transition depends on an undeclared ambient `event_seq`"* (§0.7f).

## 3. Entry point → envelope source → `(event_time, delta_cycle, event_seq)`

| Entry point | Kind | Envelope source | `event_time` | `delta_cycle` | `event_seq` |
|---|---|---|---|---|---|
| `MinerRegister` T1 (§3) | sim-driver | explicit `env` (§0.7f) | `now` | `0` | `env.event_seq = next EQ.event_creation_seq` |
| `MinerRegister` T2 (§3, optional) | sim-driver | `env` + fresh seq | `now` | `0` | `next EQ.event_creation_seq` (distinct) |
| `PrepareParticipantsForNewRound` (§2a) | sim-driver | explicit `env` (§0.7f) | `now` | `0` | `env.event_seq = next EQ.event_creation_seq` |
| `RoundInitialise`/`TemplateCommit` participant actions | sim-driver | `DriverEventEnvelope` / `ScheduleEvent` | `now` | `0` | `next EQ.event_creation_seq` |
| Direct recovery/administrative entry | sim-driver | `DriverEventEnvelope` / `ScheduleEvent` | `now` | `0` | `next EQ.event_creation_seq` |
| Any QUEUED handler (e.g. `WakeCompleteEvent` §0.10, `CertificateArrival` §16b) | queued | dispatching event's envelope (§0.2) | dispatch `event_time` | dispatch `delta_cycle` | dispatch `seq` (its `event_creation_seq`) |

Every `event_seq` column resolves to the ONE per-run monotonic `event_creation_seq`
(`EventQueueContext`, §0.7e, J4/K8) — there is no ambient undeclared seq.

## 4. The `TransitionEventID` is deterministic because `event_seq` is defined

The `TransitionEventID` (§0.9 step (1)) is
`(event_time, delta_cycle, event_seq, MinerID, old_state, new_state, reason, AssignmentID,
assignment_version, candidate_id, propagation_id)`. Its `event_seq` component is DEFINED for every
caller — from the dispatching envelope (queued) or from the `DriverEventEnvelope`/`ScheduleEvent`
(driver), both terminating at the single per-run `event_creation_seq`. Because no field is ambient, the
`TransitionEventID` is DETERMINISTIC: two reruns with the same seeds and inputs assign identical
`event_seq`s and therefore identical `TransitionEventID`s, so replay suppression
(`applied_transition_registry`, K5) and the audit trail are reproducible.

## 5. Worked example — TV86

`MinerRegister` (a sim-driver entry point, §3) registers a miner `M`. It constructs
`env = DriverEventEnvelope(event_time = now, delta_cycle = 0, event_seq = next EQ.event_creation_seq)`
and calls `ApplyMinerStateTransition(M, old_state = NONE, new_state = REGISTERED,
event_time = env.event_time, delta_cycle = env.delta_cycle, event_seq = env.event_seq, reason =
register, …)` (T1). Step (1) builds the `TransitionEventID` from these DEFINED fields; step (4)'s
completeness guard passes because none of the three envelope fields is missing; step (5) applies
atomically. Nothing is ambient (K4): the driver transition has a complete
`(event_time, delta_cycle, event_seq)` and a deterministic `TransitionEventID`. (Reqs: **K4**, J3;
matches TV86.)

## 6. Acceptance-style PASS checklist

| # | Check | Result | Ground |
|---|---|---|---|
| C1 | `ApplyMinerStateTransition` INPUTS carry `event_time`, `delta_cycle`, `event_seq`, ALWAYS defined, never ambient | PASS | §0.9 INPUTS (K4) |
| C2 | QUEUED handlers resolve the three fields from the dispatching event's envelope | PASS | §0.9 INPUTS; §0.2 |
| C3 | SIM-DRIVER entry points use an explicit `DriverEventEnvelope` or are scheduled through `ScheduleEvent` | PASS | §0.7f; §0.7e |
| C4 | `DriverEventEnvelope` = `{ event_time = now, delta_cycle = 0, event_seq = next EQ.event_creation_seq }` (or seated via `ScheduleEvent`) | PASS | §0.7f |
| C5 | `MinerRegister` constructs `env` and both `ApplyMinerStateTransition` calls (T1, optional T2) pass its fields | PASS | §3 |
| C6 | `PrepareParticipantsForNewRound` constructs `env` and passes it to every `StartWake`/action | PASS | §2a |
| C7 | `RoundInitialise`/`TemplateCommit` participant actions and any direct recovery/administrative entry pass a `DriverEventEnvelope` | PASS | §0.7f |
| C8 | `event_seq` always comes from the single per-run `event_creation_seq` (`EventQueueContext`); no ambient seq | PASS | §0.7e (J4/K8); §0.8 |
| C9 | Envelope-completeness guard REJECTS a call missing `event_time`/`delta_cycle`/`event_seq` | PASS | §0.9 step (4) |
| C10 | `TransitionEventID` is deterministic because `event_seq` is defined | PASS | §0.9 step (1); §4 |
| C11 | No new consensus feature; only the idle policy within PoCol described; no property claimed | PASS | §0 preamble |
| C12 | A1 baseline unchanged | PASS | A1 = 8.420833333 kWh |

---

## Result

**DRIVER EVENT ENVELOPE AUDIT (Stage 1K): PASS** — every `ApplyMinerStateTransition` call carries a
DEFINED `(event_time, delta_cycle, event_seq)`, never ambient: a QUEUED handler resolves the three
fields from the dispatching event's envelope (§0.2), while a SIM-DRIVER entry point supplies an explicit
`DriverEventEnvelope` (`event_time = now`, `delta_cycle = 0`, `event_seq = next EQ.event_creation_seq`,
§0.7f) or is seated on the queue through the sole enqueue interface `ScheduleEvent` (§0.7e/K8);
`MinerRegister` (§3) and `PrepareParticipantsForNewRound` (§2a) both construct `env` and pass its fields
(the two `MinerRegister` transitions carrying distinct `event_seq`s), as do the
`RoundInitialise`/`TemplateCommit` participant actions and any direct recovery/administrative entry
(§0.7f); every `event_seq` originates from the single per-run `event_creation_seq`
(`EventQueueContext`, J4/K8) so no transition depends on an undeclared ambient `event_seq` (R78), the
completeness guard rejects any malformed envelope (§0.9 step (4)), and the `TransitionEventID` (§0.9
step (1)) is therefore deterministic (TV86) — leaving the A1 baseline (8.420833333 kWh) unchanged with
no new consensus feature and no property claimed.
