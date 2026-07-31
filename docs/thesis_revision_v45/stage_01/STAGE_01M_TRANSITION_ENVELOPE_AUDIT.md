# Stage 1M — Transition-Envelope Audit (M1)

A structural audit of the Stage-1M correction **M1** (*remove the transition-envelope shorthand;
explicit envelope threading everywhere*) in the **PoCol** protocol pseudocode
(`STAGE_01_PROTOCOL_PSEUDOCODE.md`). M1 retires the Stage-1L *POSITIONAL SHORTHAND* — the convention
by which a call `ApplyMinerStateTransition(..., now, reason = …)` implicitly read
`EQ.current_event_time / current_delta_cycle / current_event_seq`. In its place, **every** call to the
central hook now spells the three event-envelope fields out at the call site as
`event_time = dispatch_envelope.event_time`, `delta_cycle = dispatch_envelope.delta_cycle`,
`event_seq = dispatch_envelope.event_seq`, and **every** procedure that directly or indirectly reaches
the hook carries an explicit `dispatch_envelope` parameter and threads it unchanged. This document is
documentation only; it audits wording and control structure, changes no executable code, describes only
**the idle policy within PoCol**, introduces no new consensus feature, and claims **no** security,
fairness, energy, or incentive property. The A1 baseline (`8.420833333 kWh`) is unchanged; any energy
change is attributable ONLY to reduced active power-time.

---

## 1. What M1 changed

- **M1a — the transition-envelope shorthand is removed (§0.9).** `ApplyMinerStateTransition`'s INPUTS
  note is now *"M1 ENVELOPE SOURCE (EXPLICIT THREADING; no shorthand)"*: the three fields are *"ALWAYS
  supplied EXPLICITLY at the call site"*, and *"a call of the form `ApplyMinerStateTransition(..., now,
  reason=...)` is NOT permitted, and NO call reads `EQ.current_event_time/current_delta_cycle/current_event_seq`
  implicitly."* The Stage-1L positional-`now` form (form (b) of the L1 audit) no longer exists.
- **M1b — every live hook call names all three fields.** Each surviving `CALL ApplyMinerStateTransition`
  now carries `event_time = dispatch_envelope.event_time`, `delta_cycle = dispatch_envelope.delta_cycle`,
  `event_seq = dispatch_envelope.event_seq` verbatim. The literal string
  `event_seq = dispatch_envelope.event_seq` occurs **exactly 14 times** — once per live call site (§3).
- **M1c — one materialised envelope, threaded from `ProcessEventTime` (§0.7d).** `ProcessEventTime` still
  materialises exactly ONE `dispatch_envelope = { event_time = t, delta_cycle = current_delta_cycle,
  event_seq = seq(e), microphase = microphase(e) }` per dispatched event `e` and `DISPATCH e WITH
  dispatch_envelope`; the handler *"threads dispatch_envelope onward"*.
- **M1d — explicit threading everywhere (§0.9 taxonomy).** A **queued handler** obtains its envelope from
  its OWN dispatched event; a **sim-driver entry point** is itself dispatched and receives the same; a
  **synchronous nested procedure** receives the SAME envelope as an explicit input from its caller. Every
  such procedure declares `dispatch_envelope` in its INPUTS and passes it unchanged.
- **M1e — the seq is owned solely by `ScheduleEvent`.** *"NO procedure stamps `next EQ.event_creation_seq`"*
  (§0.9); the six surviving mentions of `next EQ.event_creation_seq` are all prohibition/withdrawal clauses
  (§4). The Stage-1L `driver_envelope = env` argument is fully gone (zero occurrences).

## 2. Mechanism — one envelope, one syntax, one source

`ProcessEventTime` (§0.7d) drains each `event_time = t` to quiescence in deterministic
`(delta_cycle, microphase, stable_tie_key, seq)` order, and for each dispatched event `e` builds the ONE
`dispatch_envelope` from `e`'s own enqueued envelope, setting `EQ.current_event_seq <- seq(e)`. Under M1
there is now a **single** syntactic form at the hook: the explicit three-field form
`event_time = dispatch_envelope.event_time, delta_cycle = dispatch_envelope.delta_cycle,
event_seq = dispatch_envelope.event_seq`. There is no longer a second (positional-`now`) form that binds
the same triple by convention — that convention is withdrawn, and §0.9 step (4) still REJECTS any call
whose *"envelope is incomplete (missing event_time/delta_cycle/event_seq)"* as `illegal_or_malformed`, so
an omission is unrepresentable syntactically as well as semantically. Every `event_seq` still terminates
at the single per-run `event_creation_seq`, minted atomically by `ScheduleEvent` (§0.7e, J4/K8) after the
deterministic stable order is fixed (§0.7a).

## 3. Call-site inventory — every `CALL ApplyMinerStateTransition` occurrence

A grep for the exact string `CALL ApplyMinerStateTransition` returns **15** lines. **Fourteen** are live
invocation sites; the fifteenth (line 69, §0.3) is the normative sentence *"a state change is always
written `CALL ApplyMinerStateTransition(...)`"* — prose defining the convention, **not** an invocation.
Each of the 14 live sites spells out all three event-envelope fields explicitly; the "all three explicit"
column is confirmed field-by-field against the pseudocode.

| # | Occurrence (procedure §) | Line | Kind | Edge (old → new) | Reason | All three fields explicit? |
|---|---|---|---|---|---|---|
| 1 | `StartWake` (§0.10) | 569 | live | `from_state → WAKING` | `wake_start` | ✓ `event_time`/`delta_cycle`/`event_seq` = `dispatch_envelope.*` (570–572) |
| 2 | `WakeCompleteEvent` (§0.10) success | 617 | live | `WAKING → ACTIVE_HASHING` | `ramp_complete` | ✓ (618–620) |
| 3 | `WakeCompleteEvent` (§0.10) failure | 629 | live | `WAKING → OFFLINE` | `wake_deadline_expiry` | ✓ (630–632) |
| 4 | `MinerRegister` (§3) T1 | 1044 | live | `NONE → REGISTERED` | `register` | ✓ (1045–1047) |
| 5 | `MinerRegister` (§3) T2 (OPTIONAL) | 1049 | live | `REGISTERED → RESERVE` | `admit_to_reserve` | ✓ (1050–1052) |
| 6 | `ExhaustionAdjudicate` (§6) | 1240 | live | `ACTIVE_HASHING → EXHAUSTED_PENDING` | `RANGE_EXHAUSTED` | ✓ (1241–1243) |
| 7 | `EnterLowPowerListen` (§7) | 1327 | live | `from_state → LOW_POWER_LISTEN` | `stop_reason` | ✓ (1328–1330) |
| 8 | `AdversarialParticipationChangeEvent` (§8a) exit | 1413 | live | `ACTIVE_HASHING → OFFLINE` | `adversarial_withdrawal` | ✓ (1414–1415) |
| 9 | `AdversarialParticipationChangeEvent` (§8a) OFFLINE-enter | 1433 | live | `OFFLINE → REGISTERED` | `adversarial_rejoin` | ✓ (1434–1435) |
| 10 | `LeaseExpiry` (§12) PENDING case | 1792 | live | `WAKING → OFFLINE` | `lease_expired_while_waking` | ✓ (1793–1794) |
| 11 | `CloseRoundAssignments` (§17a) EXHAUSTED_PENDING | 2398 | live | `EXHAUSTED_PENDING → LOW_POWER_LISTEN` | `RANGE_EXHAUSTED` | ✓ (2399–2400) |
| 12 | `CloseRoundAssignments` (§17a) WAKING | 2415 | live | `WAKING → OFFLINE` | `round_closed_while_waking` | ✓ (2416–2417) |
| 13 | `CloseTemplateAssignments` (§19) EXHAUSTED_PENDING | 2522 | live | `EXHAUSTED_PENDING → LOW_POWER_LISTEN` | `RANGE_EXHAUSTED` | ✓ (2523–2524) |
| 14 | `CloseTemplateAssignments` (§19) WAKING | 2533 | live | `WAKING → OFFLINE` | `template_refresh_wake_abort` | ✓ (2534–2535) |
| — | §0.3 convention sentence | 69 | prose (not an invocation) | — | — | n/a (no call, no fields) |

**Tally: 15 grep lines = 14 live call sites + 1 normative sentence.** All 14 live sites use the single
explicit three-field form; none uses a positional-`now` shorthand and none reads `EQ.current_*` implicitly.
`MinerRegister`'s two calls (T1, T2) both name `dispatch_envelope.event_time`,
`dispatch_envelope.delta_cycle`, `dispatch_envelope.event_seq` explicitly (they reference the threaded
`dispatch_envelope` parameter directly, not an abbreviated `env.*`).

## 4. Prohibition-text / seq-ownership scan

| Textual probe | Result | Interpretation |
|---|---|---|
| `, now,` | 1 occurrence (line 466) | The only `, now,` is inside the §0.9 prohibition sentence; no live positional call remains. |
| `POSITIONAL SHORTHAND` / `positional shorthand` | 1 occurrence (line 466) | The sole mention is the §0.9 prohibition (*"There is NO positional shorthand …"*). |
| `driver_envelope` | 0 occurrences | The Stage-1L `driver_envelope = env` argument is fully removed. |
| implicit read of `EQ.current_event_time/current_delta_cycle/current_event_seq` by the hook | 1 occurrence (line 467) | The only reference is the §0.9 prohibition; other `EQ.current_*` reads are legitimate `EventQueueContext` dispatch-state internals in `ProcessEventTime` (§0.7d) and `ScheduleEvent` (§0.7e), not the withdrawn shorthand. |
| `next EQ.event_creation_seq` | 6 occurrences (294, 478, 563, 878, 961, 1036) | Every occurrence is a prohibition/withdrawal clause; none is a live stamp. The seq is minted only by `ScheduleEvent` (§0.7e, J9 step 3: `SET EQ.event_creation_seq <- EQ.event_creation_seq + 1`). |

## 5. Threading inventory — the procedures that carry/thread `dispatch_envelope`

The §0.9 M1 note gives the authoritative taxonomy — a **queued handler**, a **sim-driver entry point**,
and a **synchronous nested procedure** — and names 26 procedures (5 / 7 / 14). Grounded in the actual
INPUTS signatures, **26 procedures carry `dispatch_envelope`**; the membership differs from the §0.9 named
list by a single documented swap (see the two notes below): `TransitionRoundState` (§2a-bis) carries it and
`BlockAcceptancePoint` (§16d, register-only) does not. Each row below is confirmed against the procedure's
`INPUTS` line.

### 5.1 Queued handlers — envelope is the handler's OWN dispatched-event envelope

| Procedure (§) | Carries `dispatch_envelope` in INPUTS | Reaches the hook |
|---|---|---|
| `WakeCompleteEvent` (§0.10) | ✓ (line 595) | directly (calls 2, 3) + via `StartHashing` |
| `HashWorkEvent` (§5) | ✓ (line 1117) | indirectly (threads to `ExhaustionAdjudicate`, `ScheduleSolutionPropagation`) |
| `CertificateArrival` (§16c) | ✓ (line 2136) | indirectly (threads to `EarlyStopVerify`) |
| `ResumeFromPause` (§16a) | ✓ (line 2004) | indirectly (threads to `StartWake`) |

### 5.2 Sim-driver entry points — itself dispatched; receives its envelope from `ProcessEventTime`

| Procedure (§) | Carries `dispatch_envelope` in INPUTS | Reaches the hook |
|---|---|---|
| `MinerRegister` (§3) | ✓ (line 1032) | directly (calls 4, 5) |
| `PrepareParticipantsForNewRound` (§2a) | ✓ (line 873) | indirectly (`StartWake`, `CompleteAssignmentPhase`) |
| `ReserveActivate` (§10) | ✓ (line 1650) | indirectly (`StartWake`) |
| `LeaseExpiry` (§12) | ✓ (line 1732) | directly (call 10) + via `EnterLowPowerListen` / `RangeReassign` |
| `AdversarialParticipationChangeEvent` (§8a) | ✓ (line 1372) | directly (calls 8, 9) + via `RangeAssign` / `ResumeFromPause` / `StartWake` |
| `AcceptanceBatchFinalize` (§16d-bis) | ✓ (line 2280) | indirectly (`ValidBlockAccept`, `HandlePropagationFailure`) |
| `FullRangeExhaustNoSolution` (§18) | ✓ (line 2458) | indirectly (`TemplateRefresh`, `RoundAbort`) |

### 5.3 Synchronous nested procedures — receive the SAME envelope from the caller

| Procedure (§) | Carries `dispatch_envelope` in INPUTS | Reaches the hook |
|---|---|---|
| `StartWake` (§0.10) | ✓ (line 557) | directly (call 1) |
| `EnterLowPowerListen` (§7) | ✓ (line 1270) | directly (call 7) |
| `ExhaustionAdjudicate` (§6) | ✓ (line 1214) | directly (call 6) |
| `CloseRoundAssignments` (§17a) | ✓ (line 2369) | directly (calls 11, 12) + via `EnterLowPowerListen` |
| `CloseTemplateAssignments` (§19) | ✓ (line 2499) | directly (calls 13, 14) + via `EnterLowPowerListen` |
| `ScheduleSolutionPropagation` (§16b) | ✓ (line 2080) | indirectly (`EnterLowPowerListen`) |
| `EarlyStopVerify` (§16) | ✓ (line 1965) | indirectly (`EnterLowPowerListen`) |
| `CompleteAssignmentPhase` (§2b) | ✓ (line 1010) | indirectly (`TransitionRoundState`; census only) |
| `HandlePropagationFailure` (§16d-bis) | ✓ (line 2193) | indirectly (`ResumeFromPause`, `TransitionRoundState`) |
| `ValidBlockAccept` (§17) | ✓ (line 2325) | indirectly (`CloseRoundAssignments`) |
| `RoundAbort` (§20) | ✓ (line 2616) | indirectly (`CloseRoundAssignments`) |
| `RangeAssign` (§4) | ✓ (line 1064) | indirectly (`StartWake`) |
| `RangeReassign` (§13) | ✓ (line 1835) | indirectly (`StartWake`) |
| `TemplateRefresh` (§19) | ✓ (line 2559) | indirectly (`CloseTemplateAssignments`, `StartWake`, `CompleteAssignmentPhase`) |
| `TransitionRoundState` (§2a-bis) | ✓ (line 981) | census capture only (`CaptureSecurityCensusOnApplicabilityEntry` at `dispatch_envelope.event_time`) |

**Total carriers: 4 + 7 + 15 = 26.**

- **Note A (`BlockAcceptancePoint`, §16d).** The §0.9 note lists it among the queued handlers, but its
  §16d body is **register-only** (INPUTS: `RoundContext, certificate, snapshot, CandidateID, PropagationID,
  outcome` — no `dispatch_envelope`): it performs no miner transition and reaches no hook. It merely
  REGISTERS the arrival and ensures one `AcceptanceBatchFinalize` is scheduled; that finalize is the
  dispatched handler that carries its own envelope (§5.2). Hence `BlockAcceptancePoint` needs no
  `dispatch_envelope` to thread and correctly declares none.
- **Note B (`TransitionRoundState`, §2a-bis).** This M2 round-state helper carries `dispatch_envelope` and
  threads it (as `at = dispatch_envelope.event_time`) to the applicability-entry census capture. It is not
  in the §0.9 hook-threading list because it reaches no `ApplyMinerStateTransition` — it captures a census,
  not a miner-state change — but it is genuinely part of the envelope-threading chain and is counted here.

The net membership (`TransitionRoundState` in, `BlockAcceptancePoint` out) keeps the total at 26, matching
the §0.9 M1 count.

## 6. Acceptance properties

| # | Property | Result | Ground |
|---|---|---|---|
| P1 | Every `ApplyMinerStateTransition` call passes all three event-envelope fields explicitly | **PASS** | 14 live calls (§3), each with `event_time`/`delta_cycle`/`event_seq` = `dispatch_envelope.*`; the literal `event_seq = dispatch_envelope.event_seq` occurs exactly 14× |
| P2 | No transition-envelope shorthand remains | **PASS** | `, now,` and `POSITIONAL SHORTHAND` each occur only in the §0.9 prohibition (line 466); the implicit `EQ.current_*` read appears only in the §0.9 prohibition (line 467); `driver_envelope` = 0 (§4) |
| P3 | No procedure stamps `next EQ.event_creation_seq`; the seq is owned by `ScheduleEvent` | **PASS** | All 6 `next EQ.event_creation_seq` mentions are prohibition/withdrawal clauses; `ScheduleEvent` (§0.7e, J9 step 3) is the sole minter (§4) |
| P4 | `ProcessEventTime` materialises ONE `dispatch_envelope` per event and dispatches with it | **PASS** | §0.7d (lines 196–198): `SET dispatch_envelope <- {…}`; `DISPATCH e WITH dispatch_envelope` |
| P5 | Every procedure that directly OR indirectly reaches the hook carries `dispatch_envelope` and threads it unchanged | **PASS** | §5 inventory: 26 carriers (4 queued / 7 driver / 15 synchronous), each confirmed against its INPUTS line |
| P6 | §0.9 step (4) rejects any call with an incomplete envelope (`illegal_or_malformed`) | **PASS** | §0.9 step (4), lines 509–513 |
| P7 | The two §0.9 taxonomy edge cases are reconciled (register-only `BlockAcceptancePoint`; census-only `TransitionRoundState`) | **PASS** | §5 Notes A/B; §16d INPUTS (no envelope) vs §2a-bis INPUTS (envelope) |
| P8 | Documentation-only; no executable code changed; only the idle policy within PoCol; no property claimed | **PASS** | §0 preamble; this audit |
| P9 | A1 baseline unchanged; energy change attributable only to reduced active power-time | **PASS** | A1 = `8.420833333 kWh` |

---

## Result

**TRANSITION-ENVELOPE AUDIT (Stage 1M): PASS** — The Stage-1L transition-envelope shorthand is removed:
§0.9's *"M1 ENVELOPE SOURCE (EXPLICIT THREADING; no shorthand)"* note forbids the positional
`ApplyMinerStateTransition(..., now, reason=...)` form and any implicit read of
`EQ.current_event_time/current_delta_cycle/current_event_seq`, and the only surviving `, now,` /
`POSITIONAL SHORTHAND` / implicit-`EQ.current_*` mentions are that prohibition text (lines 466–467), with
`driver_envelope` gone entirely. A grep for `CALL ApplyMinerStateTransition` returns 15 lines — **14 live
call sites** (each spelling out `event_time = dispatch_envelope.event_time`,
`delta_cycle = dispatch_envelope.delta_cycle`, `event_seq = dispatch_envelope.event_seq`, confirmed by the
exactly-14 occurrences of `event_seq = dispatch_envelope.event_seq`) plus the §0.3 normative sentence at
line 69, which is not an invocation. `ProcessEventTime` (§0.7d) materialises the one `dispatch_envelope`
and dispatches with it, and **26 procedures** carry `dispatch_envelope` and thread it unchanged
(4 queued handlers, 7 sim-driver entry points, 15 synchronous callees — including the M2 helper
`TransitionRoundState` and excluding the register-only `BlockAcceptancePoint`, reconciled with the §0.9
M1 named taxonomy). The seq is owned solely by `ScheduleEvent` (J4/K8); no procedure stamps
`next EQ.event_creation_seq`. This is a documentation-only wording/threading audit that changed no
executable code, describes only the idle policy within PoCol, adds no consensus feature, claims no
security/fairness/energy/incentive property, and leaves the A1 baseline (`8.420833333 kWh`) unchanged —
any energy change being attributable ONLY to reduced active power-time.
