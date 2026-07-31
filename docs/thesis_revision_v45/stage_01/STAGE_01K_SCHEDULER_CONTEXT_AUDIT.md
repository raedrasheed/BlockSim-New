# Stage 1K — Scheduler Context Audit (K8)

A structural audit of the Stage-1K correction **K8** (complete scheduler dispatch context,
requirement **R82**) in the **PoCol** protocol pseudocode (`STAGE_01_PROTOCOL_PSEUDOCODE.md`): every
event enters the queue through ONE interface, `ScheduleEvent` (§0.7e), reading and updating a single
explicit `EventQueueContext`; the caller supplies only `target_event_time` and `target_microphase`,
and `ScheduleEvent` DERIVES the target `delta_cycle` from the dispatch context — the caller cannot
override it. This document is documentation only; it audits wording and control structure, describes
only the idle policy within PoCol, introduces no new consensus feature, and claims **no** security,
fairness, energy, or incentive property. The A1 baseline (`8.420833333 kWh`) is unchanged.

---

## 1. The corrected-away problem

- **Before K8.** `ScheduleEvent` took an arbitrary `target_delta_cycle` input, so a caller could
  supply a `delta_cycle` that bypassed the forward-scheduling rule (§0.7-H2) — the dispatch state
  (which `event_time`/`delta_cycle`/`microphase` is currently firing) was implicit, not a declared
  object the scheduler could derive from.
- **After K8.** The dispatch/scheduling state is one explicit `EventQueueContext EQ` (§0.7e). It holds
  `event_queue`, `current_event_time`, `current_delta_cycle`, `current_microphase`,
  `event_creation_seq`, and `finalised_event_times`. `ScheduleEvent` takes **NO** `target_delta_cycle`
  input (`# K8: NO target_delta_cycle input — the caller cannot set it.`) and DERIVES the target
  `delta_cycle` from `(target_event_time, target_microphase)` versus `EQ.current_*`. R82 forbidden
  behaviour: *"caller bypassing the forward-scheduling rule with an arbitrary delta_cycle."*

## 2. Mechanism

### 2.1 The explicit `EventQueueContext` (§0.7e)

```
STRUCTURE EventQueueContext (per-RUN; K8; the sole dispatch/scheduling state)
  event_queue           : the discrete-event priority queue (ordered by the total-order key below)
  current_event_time    : the event_time currently being dispatched (set by ProcessEventTime)
  current_delta_cycle   : the delta_cycle currently being dispatched (H2)
  current_microphase    : the microphase of the event currently being dispatched
  event_creation_seq    : the ONE per-run monotonic event-creation counter (J4); owned SOLELY here
  finalised_event_times : set of event_times whose epilogue has run (I-02)
```

`EQ.current_event_time`, `EQ.current_delta_cycle`, and `EQ.current_microphase` are SET by
`ProcessEventTime` (§0.7d): it sets `current_delta_cycle <- smallest delta_cycle with a pending event
at t` and dispatches `FOR EACH event e at (t, current_delta_cycle) IN ASCENDING (microphase,
stable_tie_key, seq)`, so at every `DISPATCH` the `EQ.current_*` triple is the exact
`(event_time, delta_cycle, microphase)` of the firing handler. `event_creation_seq` is owned SOLELY
inside `EQ` by `ScheduleEvent` (§0.2: *"every envelope's `seq` comes from `ScheduleEvent`"*).

### 2.2 The derive-`delta_cycle` logic (§0.7e, K8 step (2))

`ScheduleEvent` INPUTS are `EventQueueContext EQ, RoundContext, event_type, target_event_time,
target_microphase, envelope_fields` — with `# K8: NO target_delta_cycle input`. Its body derives `dc`:

```
IF target_event_time in EQ.finalised_event_times:
  RETURN rejected_finalised_time        # K8/J9 (1): I-02, epilogue already ran
IF target_event_time > EQ.current_event_time:
  SET dc <- 0                            # a FUTURE event_time starts its delta_cycle numbering at 0
ELSE IF target_event_time = EQ.current_event_time:
  IF target_microphase > EQ.current_microphase: SET dc <- EQ.current_delta_cycle
  ELSE:                                          SET dc <- EQ.current_delta_cycle + 1   # never backward
ELSE:                                    # target_event_time < EQ.current_event_time
  RETURN rejected_backward_time          # K8: never schedule into the past
```

`ScheduleEvent` then assigns `seq` atomically (`SET EQ.event_creation_seq <- EQ.event_creation_seq +
1; SET seq <- EQ.event_creation_seq`), attaches the RoundID/TemplateID epoch and candidate fields, and
inserts by the deterministic total-order key `(event_time, delta_cycle, microphase,
(CandidateID, MinerID, AssignmentID), seq)`. The `delta_cycle = …` shown in any `SCHEDULE` expression
elsewhere is the DERIVED value (e.g. the H5 zero-latency wake's `delta_cycle+1`), *"not a caller
override."*

## 3. Derivation cases — input → derived `delta_cycle` or rejection

| # | Case | Guard on `EQ` | Derived `dc` / result | Ground (§0.7e) |
|---|---|---|---|---|
| D1 | Future `event_time` | `target_event_time > EQ.current_event_time` | `dc <- 0` | step (2), branch 1 |
| D2 | Same `event_time`, target microphase LATER | `target_event_time = EQ.current_event_time` AND `target_microphase > EQ.current_microphase` | `dc <- EQ.current_delta_cycle` (same cycle) | step (2), branch 2a |
| D3 | Same `event_time`, target microphase AT-OR-EARLIER | `target_event_time = EQ.current_event_time` AND `target_microphase <= EQ.current_microphase` | `dc <- EQ.current_delta_cycle + 1` (never backward) | step (2), branch 2b |
| D4 | Past `event_time` | `target_event_time < EQ.current_event_time` | `RETURN rejected_backward_time` | step (2), branch 3 |
| D5 | Finalised `event_time` | `target_event_time in EQ.finalised_event_times` | `RETURN rejected_finalised_time` | step (1) |

The caller reaches D1–D3 with `event_time` + `microphase` ONLY; it never names `dc`. D4 and D5 are
rejections, not derivations — no envelope is created and `event_creation_seq` is NOT advanced.

## 4. No caller can bypass the forward rule — gate: *"ScheduleEvent has a complete current-dispatch context"*

Because `ScheduleEvent` reads `EQ.current_event_time`, `EQ.current_delta_cycle`, and
`EQ.current_microphase` — all SET by `ProcessEventTime` (§0.7d) or supplied by a `DriverEventEnvelope`
(§0.7f/K4) — and DERIVES `dc` from them, there is no argument through which a caller could inject a
`delta_cycle`. Every `SCHEDULE event E(...) AT event_time = τ, microphase = m` is SHORTHAND for `CALL
ScheduleEvent(EventQueueContext, RoundContext, E, τ, m, envelope_fields)`, so no ad-hoc enqueue path
exists that could name `dc`. `RoundInitialise` (§1) INITIALISES `EventQueueContext EQ` ONCE at run
start (`prior_state = null`: `event_queue = empty, current_event_time = 0, current_delta_cycle = 0,
current_microphase = 0, event_creation_seq = 0, finalised_event_times = empty set`) and PRESERVES it
across rounds (`prior_state != null`: `PRESERVE ... EventQueueContext EQ (incl. event_queue,
event_creation_seq, finalised_event_times, current_delta_cycle) from prior_state (§3.12)`) (I-04/K8),
so the dispatch context is always complete and never re-zeroed mid-run. Gate: **`ScheduleEvent` has a
complete current-dispatch context** (R82; invariant tie I17).

## 5. Worked examples

### WE1 — a future `event_time` derives `dc = 0` (D1)

A handler firing at `EQ.current_event_time = 100`, `current_delta_cycle = 2`, `current_microphase = 3`
schedules a wake for `target_event_time = 140` (`target_microphase = 0`). Since `140 > 100`,
`ScheduleEvent` derives `dc <- 0` — the future `event_time` starts its own `delta_cycle` numbering at
0, independent of the creator's `current_delta_cycle = 2`. The caller supplied only `event_time = 140`
and `microphase = 0`; it never named `dc`.

### WE2 — a same-time, at-or-earlier-microphase event derives `dc = current + 1` (D3)

A handler firing at `EQ.current_event_time = 100`, `current_delta_cycle = 2`, `current_microphase = 5`
schedules a follow-up at the SAME `target_event_time = 100` with `target_microphase = 5` (equal, so
at-or-earlier). Since `100 = 100` and `5 <= 5`, `ScheduleEvent` derives `dc <- EQ.current_delta_cycle
+ 1 = 3` — a strictly later delta-cycle, never backward. Had the target microphase been LATER
(`target_microphase = 7 > 5`, D2), it would instead derive `dc <- EQ.current_delta_cycle = 2` (same
cycle). Either way the caller could not have pinned `dc` to `2`, `0`, or any smaller value.

## 6. Acceptance-style PASS checklist

| # | Check | Result | Ground |
|---|---|---|---|
| C1 | `EventQueueContext` holds `event_queue`, `current_event_time`, `current_delta_cycle`, `current_microphase`, `event_creation_seq`, `finalised_event_times` | PASS | §0.7e STRUCTURE |
| C2 | `ScheduleEvent` INPUTS carry NO `target_delta_cycle` | PASS | §0.7e INPUTS (`# K8: NO target_delta_cycle input`) |
| C3 | Future `event_time` → `dc <- 0` (D1) | PASS | §0.7e step (2) branch 1; WE1 |
| C4 | Same time, later microphase → `dc <- current_delta_cycle` (D2) | PASS | §0.7e step (2) branch 2a |
| C5 | Same time, at-or-earlier microphase → `dc <- current_delta_cycle + 1`, never backward (D3) | PASS | §0.7e step (2) branch 2b; WE2 |
| C6 | Past `event_time` → `rejected_backward_time` (D4) | PASS | §0.7e step (2) branch 3 |
| C7 | Finalised `event_time` → `rejected_finalised_time` (D5) | PASS | §0.7e step (1); I-02 |
| C8 | `EQ.current_*` SET by `ProcessEventTime` at each dispatch | PASS | §0.7d (`current_delta_cycle <- smallest delta_cycle …`, ASCENDING microphase) |
| C9 | `event_creation_seq` owned SOLELY by `ScheduleEvent` inside `EQ` | PASS | §0.7e STRUCTURE; §0.2 |
| C10 | `RoundInitialise` initialises `EQ` once at run start and preserves it across rounds | PASS | §1 (`prior_state = null` init / else `PRESERVE … EventQueueContext EQ … (§3.12)`); I-04/K8 |
| C11 | Gate: `ScheduleEvent` has a complete current-dispatch context; no caller can bypass the forward rule | PASS | §0.7e/K8; R82; I17 |
| C12 | A1 baseline unchanged; no new consensus feature; no property claimed | PASS | A1 = 8.420833333 kWh; §0 |

---

## Result

**SCHEDULER CONTEXT AUDIT (Stage 1K): PASS** — the dispatch/scheduling state is one explicit
`EventQueueContext` (§0.7e/K8) holding `event_queue`, `current_event_time`, `current_delta_cycle`,
`current_microphase`, `event_creation_seq`, and `finalised_event_times`; `ScheduleEvent` takes NO
`target_delta_cycle` input and DERIVES the target `delta_cycle` from the dispatch context (future →
`0`; same time with later target microphase → `current_delta_cycle`, else `current_delta_cycle + 1`,
never backward; past → `rejected_backward_time`; finalised → `rejected_finalised_time`) so no caller
can bypass the forward-scheduling rule (gate: *`ScheduleEvent` has a complete current-dispatch
context*, R82/I17); `EQ.current_*` is SET by `ProcessEventTime` (§0.7d) and the context is initialised
once at run start and preserved across rounds by `RoundInitialise` (§1/§3.12, I-04/K8) — leaving the
A1 baseline (8.420833333 kWh) unchanged, with no new consensus feature and no property claimed.
