# Stage 1L — Scheduler Conformance Audit (L6)

A structural audit of the Stage-1L correction **L6** (`ScheduleEvent` is the sole delta-cycle
authority) in the **PoCol** protocol pseudocode (`STAGE_01_PROTOCOL_PSEUDOCODE.md`): every event
enters the queue through ONE interface, `ScheduleEvent` (§0.7e), which is now the SOLE authority over
`delta_cycle` — no `SCHEDULE` expression, no `CALL ScheduleEvent(...)` argument, and no handler
anywhere supplies, writes, or overrides a `delta_cycle`. The caller supplies only `target_event_time`
and `target_microphase`; `ScheduleEvent` DERIVES the delta-cycle from the dispatch context, and every
`delta_cycle` that appears in the text is either that derived value or the
`dispatch_envelope.delta_cycle` that `ProcessEventTime` (§0.7d) reads back at dispatch. This document
is documentation only; it audits wording and control structure, describes only the idle policy within
PoCol, introduces no new consensus feature, and claims **no** security, fairness, energy, or incentive
property. The A1 baseline (`8.420833333 kWh`) is unchanged; any energy change is attributable ONLY to
reduced active power-time.

---

## 1. The corrected-away problem

- **Before L6.** The forward-scheduling rule (§0.7-H2) was owned by `ScheduleEvent`'s derivation, but
  a caller could still name a `delta_cycle` in a `SCHEDULE` expression. In particular, `StartWake`
  (§0.10) scheduled its `WakeCompleteEvent` with an explicit delta-cycle — `delta_cycle = 0` on the
  positive-latency branch and `delta_cycle = current_delta_cycle + 1` on the zero-latency (H5) branch —
  so the same delta-cycle appeared twice: once as a caller argument and once as the value the scheduler
  would compute. A caller-supplied delta-cycle is a channel through which the forward rule could be
  bypassed or contradicted.
- **After L6.** §0.7e states the strengthened norm: *"`ScheduleEvent` is the SOLE authority over
  `delta_cycle`: NO `SCHEDULE` expression, NO `CALL ScheduleEvent(...)` argument, and NO handler
  anywhere in this document supplies, writes, or overrides a `delta_cycle`."* `StartWake` now supplies
  ONLY `(target_event_time, target_microphase)`; `ScheduleEvent` alone derives the delta-cycle (future
  time → `0`; zero-latency same-time wake → the forward cycle, never backward). Every `delta_cycle = …`
  still shown beside a `SCHEDULE` is the DERIVED value, *"illustrative of what `ScheduleEvent`
  computes … never a caller override."*

## 2. Mechanism

### 2.1 The strengthened normative statement (§0.7e)

§0.7e now carries the L6 clause on top of the K8 derive-only contract:

> **L6 (sole delta-cycle authority).** `ScheduleEvent` is the SOLE authority over `delta_cycle`: NO
> `SCHEDULE` expression, NO `CALL ScheduleEvent(...)` argument, and NO handler anywhere in this document
> supplies, writes, or overrides a `delta_cycle`. Every `delta_cycle` value that appears in the text is
> EITHER the value `ScheduleEvent` derived for an enqueued event OR the `dispatch_envelope.delta_cycle`
> that `ProcessEventTime` read back from an already-derived envelope at dispatch.

`ScheduleEvent`'s INPUTS remain `EventQueueContext EQ, RoundContext, event_type, target_event_time,
target_microphase, envelope_fields`, with `# K8: NO target_delta_cycle input — the caller cannot set
it.` The only assignments of a delta-cycle value in the whole document are therefore (a) inside
`ScheduleEvent`'s derivation — `SET dc <- 0` / `SET dc <- EQ.current_delta_cycle` / `SET dc <-
EQ.current_delta_cycle + 1`, then `delta_cycle = dc` in the created envelope (§0.7e step (2)); and (b)
`ProcessEventTime`'s dispatch read-back — `SET current_delta_cycle <- smallest delta_cycle with a
pending event at t` and the `dispatch_envelope = { … delta_cycle = current_delta_cycle … }` it
materialises for the firing event (§0.7d). Every `delta_cycle = dispatch_envelope.delta_cycle` passed
onward (e.g. into `ApplyMinerStateTransition` on the `StartWake` chain) is a READ of that read-back
value, never an enqueue-time override.

### 2.2 `StartWake` supplies only `(target_event_time, target_microphase)` (§0.10)

Under L6, `StartWake` schedules `WakeCompleteEvent` through `ScheduleEvent` with only the two target
fields plus the envelope identity `{MinerID, AssignmentID(target_assignment)}`:

```
IF wake_latency > 0:
  CALL ScheduleEvent(EQ, RoundContext, WakeCompleteEvent,
                     target_event_time = now + wake_latency, target_microphase = WAKE_COMPLETE,
                     {MinerID, AssignmentID(target_assignment)})   # future event_time -> ScheduleEvent derives dc = 0
ELSE:  # wake_latency = 0 (zero-latency wake, H5)
  CALL ScheduleEvent(EQ, RoundContext, WakeCompleteEvent,
                     target_event_time = now, target_microphase = WAKE_COMPLETE,
                     {MinerID, AssignmentID(target_assignment)})   # same event_time -> ScheduleEvent derives the forward dc (H5)
```

Positive latency → `target_event_time = now + wake_latency` (future time, so `ScheduleEvent` derives
`dc = 0`); zero latency → `target_event_time = now, target_microphase = WAKE_COMPLETE` (same time, so
`ScheduleEvent` derives the forward cycle at `WAKE_COMPLETE`, never backward). Neither branch names a
`delta_cycle`. The §0.10 NOTE confirms: *"WakeCompleteEvent is scheduled via ScheduleEvent with ONLY
(target_event_time, target_microphase); ScheduleEvent alone derives delta_cycle … No caller of
ScheduleEvent writes delta_cycle."*

## 3. Every scheduling call site → fields supplied → no `delta_cycle`

Enumerating every enqueue in the document. Each `SCHEDULE event E(...) AT …` is shorthand for a `CALL
ScheduleEvent(...)` (§0.7e); the columns list exactly the fields the call site supplies.

| # | Call site (procedure §) | Event scheduled | Fields supplied by caller | `delta_cycle` supplied? |
|---|---|---|---|---|
| S1 | `StartWake` §0.10 (positive latency) | `WakeCompleteEvent` | `target_event_time = now + wake_latency`, `target_microphase = WAKE_COMPLETE`, `{MinerID, AssignmentID}` | **No** — derived `dc = 0` (future time) |
| S2 | `StartWake` §0.10 (zero latency, H5) | `WakeCompleteEvent` | `target_event_time = now`, `target_microphase = WAKE_COMPLETE`, `{MinerID, AssignmentID}` | **No** — derived forward cycle at `WAKE_COMPLETE`, never backward |
| S3 | `ScheduleNextHashWork` §5 | `HashWorkEvent` | event payload `(MinerID, AssignmentID, assignment_version, RoundID, TemplateID, from_cursor)`, `AT now + modeled_hash_step_time` | **No** |
| S4 | `ScheduleSolutionPropagation` §16b | `CertificateArrival` | payload `(recipient r, certificate, snapshot, CandidateID, PropagationID)`, `AT now + cert_delay(r)` | **No** |
| S5 | `ScheduleSolutionPropagation` §16b | `BlockAcceptancePoint` | payload `(certificate, snapshot, CandidateID, PropagationID, outcome)`, `AT now + block_delay` | **No** |
| S6 | `HandlePropagationFailure` §16d-bis | `ResumeFromPause` | payload `(M, trigger = failure_reason, pause_cause_candidate_id, pause_cause_propagation_id)` | **No** — `dispatch_envelope` (incl. `delta_cycle`) supplied by `ProcessEventTime` at dispatch, not in the payload |

Every row supplies at most `target_event_time`/`AT`, `target_microphase`, and envelope identity
fields. No row supplies, writes, or overrides `delta_cycle`. S6's `ResumeFromPause` receives its
`(event_time, delta_cycle, event_seq)` only when `ProcessEventTime` dispatches it — its own enqueued
envelope, read back per §0.7d — not from the payload (§16d-bis NOTE / L1). The one direct `CALL
ResumeFromPause(...)` (§8a, `adversarial_reactivation`) is a synchronous call, not an enqueue, and
threads the caller's own `dispatch_envelope`; it likewise names no `delta_cycle`.

## 4. The only two places a delta-cycle is assigned

| Site | Assignment | Role | Ground |
|---|---|---|---|
| `ScheduleEvent` derivation (§0.7e step (2)) | `SET dc <- 0` / `EQ.current_delta_cycle` / `EQ.current_delta_cycle + 1`; then `delta_cycle = dc` in the envelope | The derived enqueue-time value | §0.7e |
| `ProcessEventTime` dispatch read-back (§0.7d) | `SET current_delta_cycle <- smallest delta_cycle with a pending event at t`; `dispatch_envelope = { … delta_cycle = current_delta_cycle … }` | Reading back an already-derived envelope for the firing handler | §0.7d |

No third writer exists. Every other `delta_cycle` token in the document — including each
`delta_cycle = dispatch_envelope.delta_cycle` threaded into `ApplyMinerStateTransition` (§0.9, §0.10,
§16a) — is a READ of the §0.7d read-back value, never a caller override at enqueue. The forward-
scheduling rule (§0.7-H2) therefore cannot be bypassed: there is no argument through which a caller
could inject a delta-cycle, so the derivation in §0.7e step (2) is the only path a delta-cycle can be
computed, and `ProcessEventTime` is the only path it can be read back.

## 5. Acceptance-style PASS checklist

| # | Check | Result | Ground |
|---|---|---|---|
| C1 | `ScheduleEvent` is the single enqueue interface and the sole delta-cycle authority | PASS | §0.7e (L6 clause; *"the SOLE authority over `delta_cycle`"*) |
| C2 | No caller supplies or overrides `delta_cycle` — no `SCHEDULE` expression and no `CALL ScheduleEvent(...)` argument names it | PASS | §0.7e (L6); call-site table S1–S6 (§3) |
| C3 | `StartWake` schedules `WakeCompleteEvent` with only `target_event_time` + `target_microphase` (positive latency `now + wake_latency`; zero latency `now` at `WAKE_COMPLETE`) | PASS | §0.10 (S1/S2); §0.10 NOTE |
| C4 | `ScheduleNextHashWork`'s `HashWorkEvent` carries no `delta_cycle` | PASS | §5 (S3) |
| C5 | `ScheduleSolutionPropagation`'s `CertificateArrival` and `BlockAcceptancePoint` carry no `delta_cycle` | PASS | §16b (S4/S5) |
| C6 | `HandlePropagationFailure`'s `ResumeFromPause` carries no `delta_cycle`; its envelope is supplied by `ProcessEventTime` at dispatch | PASS | §16d-bis (S6); §16d-bis NOTE / L1 |
| C7 | The only delta-cycle assignments are `ScheduleEvent`'s derivation and `ProcessEventTime`'s dispatch read-back | PASS | §0.7e step (2); §0.7d (§4 table) |
| C8 | The forward-scheduling rule (§0.7-H2) cannot be bypassed — no argument injects a delta-cycle | PASS | §0.7e; §0.7-H2; §4 |
| C9 | Every `delta_cycle = …` shown beside a `SCHEDULE` is the DERIVED value, illustrative, never a caller override | PASS | §0.7e (*"the DERIVED value, illustrative … never a caller override"*) |
| C10 | A1 baseline unchanged; no new consensus feature; no property claimed; only the idle policy within PoCol described | PASS | A1 = 8.420833333 kWh; §0 |

---

## Result

**SCHEDULER CONFORMANCE AUDIT (Stage 1L): PASS** — `ScheduleEvent` (§0.7e) is the single enqueue
interface and the SOLE authority over `delta_cycle`: no `SCHEDULE` expression, no `CALL
ScheduleEvent(...)` argument, and no handler supplies, writes, or overrides a `delta_cycle` (L6). All
six scheduling call sites — `StartWake`'s `WakeCompleteEvent` (positive latency `now + wake_latency`;
zero latency `now` at `WAKE_COMPLETE`, §0.10), `ScheduleNextHashWork`'s `HashWorkEvent` (§5),
`ScheduleSolutionPropagation`'s `CertificateArrival` and `BlockAcceptancePoint` (§16b), and
`HandlePropagationFailure`'s `ResumeFromPause` (§16d-bis) — supply only `target_event_time`/`AT`,
`target_microphase`, and envelope identity fields, never a delta-cycle. The only delta-cycle
assignments are `ScheduleEvent`'s derivation (§0.7e step (2)) and `ProcessEventTime`'s dispatch
read-back (§0.7d), so the forward-scheduling rule (§0.7-H2) cannot be bypassed — leaving the A1
baseline (8.420833333 kWh) unchanged, with no new consensus feature and no property claimed, describing
only the idle policy within PoCol.
