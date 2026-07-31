# Stage 1R — Transition-Envelope Namespace Threading Audit (R3)

## Intro

This audit is a **documentation-only** record of ONE Stage 1R correction in
`docs/thesis_revision_v45/stage_01/STAGE_01_PROTOCOL_PSEUDOCODE.md`: **R3 — thread the
full transition envelope**. The consensus specification under revision is **PoCol**.
Within PoCol, *the idle policy within PoCol* is referenced only as the mechanism that
parks a miner in `LOW_POWER_LISTEN`; R3 introduces no behavioural change to it and no
new consensus feature. R3 is an **identity/threading correction**: it fixes how a
miner-state transition names its envelope, never how time or energy is counted, so it
revises no measured quantity — the A1 accepted baseline **8.420833333 kWh is UNCHANGED**.

**Scope.** Exactly R3: `ApplyMinerStateTransition` (§0.9) must receive ONE explicit
transition envelope carrying `envelope_namespace`, `event_time`, `delta_cycle`,
`event_seq`, and `hook_id` (when applicable), sourced from the caller's
`dispatch_envelope` (§0.2). The namespace fields are NEVER decomposed away in favour of
only the three numeric fields. The two threading paths — the `ORDINARY_EVENT` envelope
materialised by `ProcessEventTime` (§0.7d) and the `RUN_HOOK` envelope preserved by
`CloseRoundAtHorizon` (§20b) through §17a → §7 → §0.9 — are documented in §2 below.

## 1. `TransitionEventID` composition (§0.9, J3/R3)

`ApplyMinerStateTransition` (§0.9) builds the immutable event identity from the FULL
envelope. Per §0.9 step (1), with `envelope_namespace` and `hook_id` as the LEADING
fields:

```
SET TransitionEventID <- (envelope_namespace, hook_id, event_time, delta_cycle, event_seq,
                          MinerID, old_state, new_state, reason,
                          AssignmentID(assignment_ref), assignment_version(assignment_ref),
                          candidate_id, propagation_id)
```

The `INPUTS` of §0.9 list the five identity fields explicitly —
`envelope_namespace, event_time, delta_cycle, event_seq, hook_id` — annotated "R3: the
FULL transition envelope (§0.2)". The construction places `envelope_namespace` first and
`hook_id` second, BEFORE the numeric fields, so the namespace tag partitions the identity
space at the head of the tuple. `envelope_namespace` ∈ `{ORDINARY_EVENT, RUN_HOOK}` (the
§0.2/Q6 tag); `hook_id` is `null` on an `ORDINARY_EVENT` transition and
`HorizonHookID = (RunID, run_horizon_T, HORIZON_CLOSE)` on the horizon-close `RUN_HOOK`
transition (§20b).

Validation is explicit (§0.9 step (4)): an envelope "missing
`envelope_namespace`/`event_time`/`delta_cycle`/`event_seq`" is REJECTED, and — R3 — so
is "`envelope_namespace = RUN_HOOK AND hook_id = null`" (`illegal_or_malformed`): a
`RUN_HOOK` envelope MUST carry its `hook_id`. The five identity fields are threaded from
ONE `dispatch_envelope`, never decomposed to only the numeric three (§0.9 INPUTS,
"no decomposition-and-discard").

## 2. Threading paths

### 2.1 The `ORDINARY_EVENT` path (§0.7d → §0.9)

`ProcessEventTime` (§0.7d) MATERIALISES the one dispatch envelope for each event `e`,
carrying the full ordinary identity:

```
SET dispatch_envelope <- { envelope_namespace = ORDINARY_EVENT, hook_id = null,
                           event_time = t, delta_cycle = current_delta_cycle,
                           event_seq = seq(e), microphase = microphase(e) }
DISPATCH e WITH dispatch_envelope
```

Per the §0.7d R3 comment, "every ordinary dispatch envelope carries
`envelope_namespace = ORDINARY_EVENT` and `hook_id = null`", and every miner transition
performed while handling `e` "threads the COMPLETE identity (namespace fields included)
into `ApplyMinerStateTransition` (§0.9/R3), never only the numeric
(`event_time`, `delta_cycle`, `event_seq`)." Each queued handler (`WakeCompleteEvent`,
`HashWorkEvent`, `CertificateArrival`, `BlockAcceptancePoint`, `ResumeFromPause`) and each
sim-driver entry point receives THIS envelope and threads it unchanged into §0.9, so its
`TransitionEventID` carries `ORDINARY_EVENT` and `hook_id = null`.

### 2.2 The `RUN_HOOK` path (§20b → §17a → §7 → §0.9)

`CloseRoundAtHorizon` (§20b) mints the ONE deterministic run-hook envelope in the
`RUN_HOOK` namespace:

```
SET HorizonHookID   <- (RunID, run_horizon_T, HORIZON_CLOSE)
SET horizon_envelope <- { envelope_namespace = RUN_HOOK, event_time = run_horizon_T,
                          delta_cycle = RUN_HOOK_CYCLE, event_seq = RunHookContext.run_hook_seq,
                          hook_id = HorizonHookID }
CALL CloseRoundAssignments(RoundContext, disposition = ROUND_ABORTED,
                           stop_reason = ROUND_ABORTED, dispatch_envelope = horizon_envelope)
```

`CloseRoundAssignments` (§17a) takes `dispatch_envelope` as an INPUT and PRESERVES its
`envelope_namespace` + `hook_id` at each nested miner transition. The preservation is
shown EXPLICITLY at the call sites:

- `ACTIVE_HASHING` holder → `EnterLowPowerListen(..., dispatch_envelope = dispatch_envelope)`.
- `EXHAUSTED_PENDING` holder (T8) → `ApplyMinerStateTransition(h, EXHAUSTED_PENDING,
  LOW_POWER_LISTEN, envelope_namespace = dispatch_envelope.envelope_namespace, …,
  hook_id = dispatch_envelope.hook_id, …)`.
- `WAKING` holder (T12) → `ApplyMinerStateTransition(h, WAKING, OFFLINE,
  envelope_namespace = dispatch_envelope.envelope_namespace, …, hook_id = dispatch_envelope.hook_id, …)`.

`EnterLowPowerListen` (§7) in turn threads the same envelope into §0.9, shown at that
call site:

```
CALL ApplyMinerStateTransition(MinerID, from_state, LOW_POWER_LISTEN,
       envelope_namespace = dispatch_envelope.envelope_namespace,   # preserve RUN_HOOK at horizon close
       event_time = dispatch_envelope.event_time, delta_cycle = dispatch_envelope.delta_cycle,
       event_seq = dispatch_envelope.event_seq,
       hook_id = dispatch_envelope.hook_id,                         # HorizonHookID on RUN_HOOK, null otherwise
       reason = stop_reason, assignment_ref = assignment_ref, …)
```

Per the §20b R3 NOTE, the `horizon_envelope`'s `envelope_namespace = RUN_HOOK` and
`hook_id = HorizonHookID` are "THREADED unchanged" through §17a → §7 → §0.9, so EVERY
nested miner transition of the horizon close carries `RUN_HOOK` + `HorizonHookID` in its id.

## 3. Distinctness proof (R3 acceptance requirement)

Construct two transitions of the SAME edge, for the SAME miner, at the SAME numeric
`(event_time, delta_cycle, event_seq)`, differing ONLY in `envelope_namespace`. Per §0.9
the leading tuple fields diverge, so the two `TransitionEventID`s are DISTINCT:

| Field (tuple order) | Ordinary transition | Run-hook transition |
|---|---|---|
| `envelope_namespace` | `ORDINARY_EVENT` | `RUN_HOOK` |
| `hook_id` | `null` | `HorizonHookID = (RunID, T, HORIZON_CLOSE)` |
| `event_time` | `T` | `T` (identical) |
| `delta_cycle` | `d` | `d` (identical) |
| `event_seq` | `s` | `s` (identical) |
| `MinerID` / edge | `m`, ACTIVE_HASHING→LOW_POWER_LISTEN | `m`, ACTIVE_HASHING→LOW_POWER_LISTEN |
| Resulting `TransitionEventID` | `(ORDINARY_EVENT, null, T, d, s, …)` | `(RUN_HOOK, HorizonHookID, T, d, s, …)` |
| **Distinct?** | — | **YES — leading `(envelope_namespace, hook_id)` differ** |

The numeric coincidence of `(T, d, s)` is immaterial: because
`(envelope_namespace, hook_id)` head the tuple, the two ids never alias, so both the K5
replay guard and the `applied_transition_registry` treat them as different transitions
(§0.9 step (2), R3 NOTE). This satisfies the R3 acceptance requirement — two transitions
with identical numeric `event_time`/`delta_cycle`/`event_seq` but DIFFERENT
`envelope_namespace` values produce DIFFERENT `TransitionEventID`s. Collision freedom
derives from the namespace TAG (§0.2), not from the `RUN_HOOK_CYCLE` number.

## 4. Result

R3 threads ONE complete transition envelope from each caller's `dispatch_envelope` into
`ApplyMinerStateTransition`: the `ORDINARY_EVENT` path materialised by `ProcessEventTime`
(§0.7d, `hook_id = null`) and the `RUN_HOOK` path minted by `CloseRoundAtHorizon` (§20b,
`hook_id = HorizonHookID`) preserved verbatim through `CloseRoundAssignments` (§17a) and
`EnterLowPowerListen` (§7) to their §0.9 call sites. The namespace fields are never
dropped in favour of the three numeric fields, and `TransitionEventID` leads with
`(envelope_namespace, hook_id)`, so a run-hook transition and an ordinary transition
sharing identical numeric `(event_time, delta_cycle, event_seq)` receive distinct ids.
This is an identity/threading correction only: it changes no state transition, no
residency boundary, and no energy figure. The A1 accepted baseline **8.420833333 kWh is
UNCHANGED**. No new consensus feature is introduced; PoCol's behaviour, and the idle
policy within PoCol, are unaltered.

The prohibited rebranded-algorithm-name variants are not used anywhere in this document.
