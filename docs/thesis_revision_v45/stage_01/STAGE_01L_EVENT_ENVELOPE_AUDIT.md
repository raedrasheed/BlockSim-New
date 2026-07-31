# Stage 1L — Event Envelope Audit (L1)

A structural audit of the Stage-1L correction **L1** (thread the event envelope through every miner
transition) in the **PoCol** protocol pseudocode (`STAGE_01_PROTOCOL_PSEUDOCODE.md`): every
`ApplyMinerStateTransition` call — dispatched from a queued handler or reached synchronously from a
sim-driver entry point — carries a DEFINED `(event_time, delta_cycle, event_seq)` bound from the ONE
`dispatch_envelope` that `ProcessEventTime` (§0.7d) materialises for the event under dispatch. L1
retires the last two ways a transition could otherwise acquire an undeclared `event_seq`: it removes
the unsupported `driver_envelope = env` arguments and WITHDRAWS the manual `next EQ.event_creation_seq`
stamp (§0.7f). `event_seq` is now minted SOLELY by `ScheduleEvent` (§0.7e, J4/K8) and reaches every
transition only as the dispatched event's own enqueued seq. This document is documentation only; it
audits wording and control structure, claims that NO executable code was changed, describes only the
idle policy within PoCol, introduces no new consensus feature, and claims **no** security, fairness,
energy, or incentive property. The A1 baseline (`8.420833333 kWh`) is unchanged; any energy change is
attributable ONLY to reduced active power-time.

---

## 1. What L1 changed

- **L1a — one materialised dispatch envelope per event.** `ProcessEventTime` (§0.7d) now materialises
  exactly ONE `dispatch_envelope = { event_time = t, delta_cycle = current_delta_cycle, event_seq =
  seq(e), microphase = microphase(e) }` per dispatched event `e`, taken from `e`'s OWN enqueued
  envelope, and sets `EQ.current_event_seq <- seq(e)`. Every miner transition and every `StartWake`
  performed synchronously while handling `e` binds all three fields from THIS record.
- **L1b — new `EventQueueContext` field.** §0.7e adds `current_event_seq` (the `event_creation_seq` of
  the event currently being dispatched). Together with `current_event_time` and `current_delta_cycle`
  it forms the CURRENT `dispatch_envelope` — an EXPLICIT dispatched-envelope field, NOT an ambient seq.
- **L1c — every `StartWake` caller threads `dispatch_envelope`.** `StartWake` (§0.10) gained
  `dispatch_envelope` in its INPUTS and binds all three envelope fields into its WAKING
  `ApplyMinerStateTransition`. The unsupported `driver_envelope = env` arguments (previously passed to
  `StartWake`, whose signature did not accept them) are REMOVED; every caller now passes
  `dispatch_envelope = dispatch_envelope`.
- **L1d — driver entry points stop hand-stamping the seq.** `MinerRegister` (§3),
  `PrepareParticipantsForNewRound` (§2a), and `ReserveActivate` (§10) no longer construct an envelope
  by `next EQ.event_creation_seq`; each receives its `dispatch_envelope` from `ProcessEventTime`
  because it is itself seated on the queue through `ScheduleEvent` (§0.7e, the sole minter of
  `event_creation_seq`, J4/K8). §0.7f records that the K4 manual-stamp alternative is WITHDRAWN by L1.
- **L1e — normative positional shorthand (§0.9).** A positional call
  `ApplyMinerStateTransition(MinerID, old, new, now, reason = …, …)` inside a dispatched context BINDS
  `event_time = dispatch_envelope.event_time (= now)`, `delta_cycle = dispatch_envelope.delta_cycle`,
  `event_seq = dispatch_envelope.event_seq` — available IDENTICALLY as the threaded `dispatch_envelope`
  parameter OR the `EventQueueContext` current-dispatch fields (`EQ.current_event_time`,
  `EQ.current_delta_cycle`, `EQ.current_event_seq`). The two forms denote the SAME triple, so NO call
  omits any of the three fields semantically or syntactically.

## 2. Mechanism — one envelope, two syntaxes, one source

### 2.1 `ProcessEventTime` materialises the envelope (§0.7d)

`ProcessEventTime` drains each `event_time = t` to quiescence in deterministic
`(delta_cycle, microphase, stable_tie_key, seq)` order. For each dispatched event `e` it sets
`EQ.current_microphase` and `EQ.current_event_seq <- seq(e)`, builds
`dispatch_envelope = { event_time = t, delta_cycle = current_delta_cycle, event_seq = seq(e),
microphase = microphase(e) }` from `e`'s own enqueued envelope, and `DISPATCH e WITH dispatch_envelope`
(§0.7d). The handler threads `dispatch_envelope` onward; no handler reads an ambient/undeclared seq and
none manually stamps `EQ.event_creation_seq`.

### 2.2 The two syntactic forms bind the same envelope (§0.9)

`ApplyMinerStateTransition` (§0.9) receives `event_time, delta_cycle, event_seq` in its INPUTS with the
K4/L1 note that they are *"ALWAYS defined, never ambient, and bind from the ONE dispatch envelope of the
event being handled."* A call takes one of two equivalent forms:

| Form | Syntax | Field source |
|---|---|---|
| **(a) explicit three-field** | `event_time = dispatch_envelope.event_time, delta_cycle = dispatch_envelope.delta_cycle, event_seq = dispatch_envelope.event_seq` | the threaded `dispatch_envelope` parameter (StartWake chain; driver entry points) |
| **(b) positional-`now` shorthand** | `ApplyMinerStateTransition(MinerID, old, new, now, reason = …, …)` | the §0.9 L1 POSITIONAL SHORTHAND binds `now = dispatch_envelope.event_time`, `delta_cycle = dispatch_envelope.delta_cycle`, `event_seq = dispatch_envelope.event_seq` — read from the threaded parameter or `EQ.current_*` |

Both forms terminate at the single per-run `event_creation_seq` (§0.7e, J4/K8). Step (4) of §0.9
REJECTS any call whose *"envelope is incomplete (missing event_time/delta_cycle/event_seq)"*
(`illegal_or_malformed`), so a syntactic omission cannot apply either.

### 2.3 The single sanctioned source (§0.7f)

Per §0.7f (L1), a `DriverEventEnvelope` is obtained from EXACTLY ONE source: the entry point is itself
SEATED on the queue through `ScheduleEvent` and DISPATCHED by `ProcessEventTime`, so its
`dispatch_envelope` is `(EQ.current_event_time, EQ.current_delta_cycle, EQ.current_event_seq)`. *"A
driver entry point MUST NOT manually stamp `next EQ.event_creation_seq`"* — that manual form (permitted
as an alternative under K4) is WITHDRAWN by L1. `MinerRegister`, `PrepareParticipantsForNewRound`,
`ReserveActivate`, the `RoundInitialise`/`TemplateCommit` participant actions, and any direct
recovery/administrative entry each receive their `dispatch_envelope` from `ProcessEventTime` and THREAD
it to every `ApplyMinerStateTransition` and every `StartWake`.

## 3. Call-site inventory — every `ApplyMinerStateTransition` classified

The following table enumerates every `CALL ApplyMinerStateTransition(...)` site in the pseudocode and
classifies each as form **(a)** explicit three-field or form **(b)** positional-`now` shorthand, with
the `dispatch_envelope` that binds its three fields.

| # | Call site (procedure §) | Edge (old → new) | Reason | Form | Envelope binding |
|---|---|---|---|---|---|
| 1 | `StartWake` (§0.10) | `from_state → WAKING` | `wake_start` | (a) explicit | threaded `dispatch_envelope` (L1c) |
| 2 | `MinerRegister` (§3) T1 | `NONE → REGISTERED` | `register` | (a) explicit | this entry point's `dispatch_envelope` (L1d) |
| 3 | `MinerRegister` (§3) T2 (OPTIONAL) | `REGISTERED → RESERVE` | `admit_to_reserve` | (a) explicit | same `dispatch_envelope` (L1d) |
| 4 | `WakeCompleteEvent` (§0.10) success | `WAKING → ACTIVE_HASHING` | `ramp_complete` | (b) positional `now` | its own dispatching `WakeCompleteEvent` envelope |
| 5 | `WakeCompleteEvent` (§0.10) failure | `WAKING → OFFLINE` | `wake_deadline_expiry` | (b) positional `now` | its own dispatching `WakeCompleteEvent` envelope |
| 6 | `ExhaustionAdjudicate` (§6) | `ACTIVE_HASHING → EXHAUSTED_PENDING` | `RANGE_EXHAUSTED` | (b) positional `now` | dispatching `HashWorkEvent` envelope (§5) |
| 7 | `EnterLowPowerListen` (§7) | `from_state → LOW_POWER_LISTEN` | `stop_reason` | (b) positional `now` | dispatch envelope of its caller (`CloseRoundAssignments`/`CloseTemplateAssignments`/`LeaseExpiry`) |
| 8 | `AdversarialParticipationChangeEvent` (§8a) exit | `ACTIVE_HASHING → OFFLINE` | `adversarial_withdrawal` | (b) positional `now` | its own dispatching event envelope |
| 9 | `AdversarialParticipationChangeEvent` (§8a) enter/OFFLINE | `OFFLINE → REGISTERED` | `adversarial_rejoin` | (b) positional `now` | its own dispatching event envelope (comment cites §0.9/L1) |
| 10 | `CloseRoundAssignments` (§17a) EXHAUSTED_PENDING | `EXHAUSTED_PENDING → LOW_POWER_LISTEN` | `RANGE_EXHAUSTED` | (b) positional `now` | dispatch envelope of `ValidBlockAccept`/`RoundAbort` |
| 11 | `CloseRoundAssignments` (§17a) WAKING | `WAKING → OFFLINE` | `round_closed_while_waking` | (b) positional `now` | dispatch envelope of `ValidBlockAccept`/`RoundAbort` |
| 12 | `CloseTemplateAssignments` (§19) EXHAUSTED_PENDING | `EXHAUSTED_PENDING → LOW_POWER_LISTEN` | `RANGE_EXHAUSTED` | (b) positional `now` | `TemplateRefresh` ← `FullRangeExhaustNoSolution` dispatch envelope |
| 13 | `CloseTemplateAssignments` (§19) WAKING | `WAKING → OFFLINE` | `template_refresh_wake_abort` | (b) positional `now` | `TemplateRefresh` ← `FullRangeExhaustNoSolution` dispatch envelope |

**Tally: 13 call sites — 3 explicit three-field (form a), 10 positional-`now` shorthand (form b).**
Neither form omits `event_time`, `delta_cycle`, or `event_seq`: form (a) names them literally from
`dispatch_envelope`; form (b) binds them by the normative §0.9 convention. The threading chain that
carries `dispatch_envelope` to the driver-side `StartWake`/`ApplyMinerStateTransition` calls runs
through `PrepareParticipantsForNewRound` (§2a), `RangeAssign` (§4), `ReserveActivate` (§10),
`RangeReassign` (§13), `ResumeFromPause` (§16a), `TemplateRefresh` (§19),
`FullRangeExhaustNoSolution` (§18), `LeaseExpiry` (§12), and
`AdversarialParticipationChangeEvent` (§8a) — each of which now carries `dispatch_envelope` in its
INPUTS and passes it on.

## 4. No ambient seq

- Every `event_seq` resolves to the ONE per-run monotonic `event_creation_seq`
  (`EventQueueContext`, §0.7e), assigned ATOMICALLY by the sole enqueue interface `ScheduleEvent`
  (§0.7e, J4/K8) AFTER the deterministic stable ordering (§0.7a, G7) — never invented locally.
- `ProcessEventTime` (§0.7d) reads that seq back into `EQ.current_event_seq` and the materialised
  `dispatch_envelope` for exactly the event under dispatch; there is *"no ambient undeclared seq"*
  (§0.2/§0.7e).
- A form-(a) call names `dispatch_envelope.event_seq` directly; a form-(b) positional-`now` call binds
  the same `EQ.current_event_seq` by the §0.9 convention — an EXPLICIT declared record, not an ambient
  undeclared seq. Forms (a) and (b) denote the SAME `(event_time, delta_cycle, event_seq)`.
- The two former escape hatches are closed: the unsupported `driver_envelope = env` argument is gone
  (L1c), and no driver entry point stamps `next EQ.event_creation_seq` (L1d, §0.7f). A textual scan
  confirms every surviving mention of `next EQ.event_creation_seq` is a prohibition/withdrawal clause,
  never a live stamp.
- Step (4) of §0.9 rejects any call missing `event_time`/`delta_cycle`/`event_seq` as
  `illegal_or_malformed`, so an omission is unrepresentable syntactically as well as semantically.

## 5. Worked trace — the positional shorthand binds a defined envelope

`CloseTemplateAssignments` (§19) handling a `WAKING` holder `h` calls
`ApplyMinerStateTransition(h, WAKING, OFFLINE, now, reason = template_refresh_wake_abort,
assignment_ref = X, candidate_id = null, propagation_id = null)` (T12). This is form (b): `now` is the
`event_time` of the `dispatch_envelope` that `ProcessEventTime` materialised for the event driving
`FullRangeExhaustNoSolution → TemplateRefresh → CloseTemplateAssignments`. By the §0.9 L1 POSITIONAL
SHORTHAND the call BINDS `event_time = dispatch_envelope.event_time (= now)`,
`delta_cycle = dispatch_envelope.delta_cycle`, `event_seq = dispatch_envelope.event_seq`, whose
`event_seq` is that dispatched event's `event_creation_seq` (minted by `ScheduleEvent`, J4/K8). Step (1)
of §0.9 builds the `TransitionEventID` from these DEFINED fields; step (4)'s completeness guard passes;
step (5) applies atomically. Nothing is ambient, and no field is omitted.

## 6. Acceptance property

> **No `ApplyMinerStateTransition` call may omit `event_time`, `delta_cycle`, or `event_seq`
> semantically or syntactically.**

| # | Check | Result | Ground |
|---|---|---|---|
| C1 | `ProcessEventTime` materialises ONE `dispatch_envelope` per event and sets `EQ.current_event_seq` | PASS | §0.7d; §0.7e (L1) |
| C2 | `StartWake` INPUTS carry `dispatch_envelope`; its WAKING transition binds all three fields | PASS | §0.10 (L1c) |
| C3 | Every `StartWake` caller threads `dispatch_envelope`; no `driver_envelope = env` remains | PASS | §2a/§4/§8a/§10/§12/§13/§16a/§19 |
| C4 | `MinerRegister`/`PrepareParticipantsForNewRound`/`ReserveActivate` do not stamp `next EQ.event_creation_seq` | PASS | §3/§2a/§10; §0.7f |
| C5 | The K4 manual-stamp alternative is WITHDRAWN; seq is minted solely by `ScheduleEvent` | PASS | §0.7f; §0.7e (J4/K8) |
| C6 | Form (a) explicit calls name all three envelope fields (sites 1–3) | PASS | §0.10, §3 |
| C7 | Form (b) positional-`now` calls bind all three by the §0.9 normative convention (sites 4–13) | PASS | §0.9 L1 POSITIONAL SHORTHAND |
| C8 | Threaded-parameter and `EQ.current_*` bindings denote the SAME `(event_time, delta_cycle, event_seq)` | PASS | §0.9; §0.7e |
| C9 | `event_seq` always originates from the single per-run `event_creation_seq`; no ambient seq | PASS | §0.2; §0.7e (J4/K8) |
| C10 | §0.9 step (4) rejects any call with an incomplete envelope (`illegal_or_malformed`) | PASS | §0.9 step (4) |
| C11 | All 13 call sites classified; none omits a field (3 explicit + 10 positional) | PASS | §3 inventory |
| C12 | Documentation-only; no executable code changed; only the idle policy within PoCol; no property claimed | PASS | §0 preamble |
| C13 | A1 baseline unchanged; energy change attributable only to reduced active power-time | PASS | A1 = 8.420833333 kWh |

---

## Result

**EVENT ENVELOPE AUDIT (Stage 1L): PASS** — `ProcessEventTime` (§0.7d) materialises ONE
`dispatch_envelope = (event_time, delta_cycle, event_seq)` per dispatched event from that event's own
enqueued envelope and sets `EQ.current_event_seq` (§0.7e); `StartWake` (§0.10) and every caller now
thread `dispatch_envelope`, the unsupported `driver_envelope = env` arguments are removed, and the K4
manual `next EQ.event_creation_seq` stamp is WITHDRAWN so `event_seq` is minted solely by
`ScheduleEvent` (J4/K8) and reaches each transition only as the dispatched event's own seq (§0.7f). All
13 `ApplyMinerStateTransition` call sites are accounted for — 3 as explicit three-field driver/threaded
calls (`StartWake`, `MinerRegister` T1/T2) and 10 as positional-`now` shorthand bound by the §0.9 L1
POSITIONAL SHORTHAND, whose threaded-parameter and `EventQueueContext` current-dispatch forms denote the
SAME triple — so no call omits `event_time`, `delta_cycle`, or `event_seq` semantically or
syntactically, and none depends on an ambient undeclared seq (§0.2/§0.7e), with the §0.9 step (4)
completeness guard rejecting any incomplete envelope. This is a documentation-only wording/threading
audit that changed no executable code, describes only the idle policy within PoCol, adds no consensus
feature, claims no security/fairness/energy/incentive property, and leaves the A1 baseline
(8.420833333 kWh) unchanged — any energy change being attributable ONLY to reduced active power-time.
