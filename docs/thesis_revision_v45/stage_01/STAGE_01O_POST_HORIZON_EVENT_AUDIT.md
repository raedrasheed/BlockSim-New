# Stage 1O — Post-Horizon Event Audit (O2)

## Intro

This audit is documentation only. The consensus algorithm audited here is named
**PoCol**. Its energy behaviour is referred to solely as *the idle policy within
PoCol*, described here as a mechanism and nothing more; this document asserts no
property of it. The A1 accounting baseline of **8.420833333 kWh** is UNCHANGED by
this correction and is neither recomputed nor reinterpreted here.

**Scope.** This file audits Stage 1O correction **O2 — the binding horizon rule for
`ScheduleEvent` and the absence of post-horizon events** in
`docs/thesis_revision_v45/stage_01/STAGE_01_PROTOCOL_PSEUDOCODE.md`. It records what
the specification now states about the fixed simulation horizon `T`, the single
enqueue bound that keeps every ordinary event at `event_time <= T`, and the two
security-floor branches (§9, §9a) that defer to horizon-close (§20b) rather than
seat an event past `T`. It quotes the authoritative procedures verbatim; it changes
no behaviour.

## 1. The `ScheduleEvent` binding horizon rule (§0.7e)

`ScheduleEvent` (§0.7e) is defined as the SOLE enqueue interface: "Every event
enters the queue through ONE interface, `ScheduleEvent`". The procedure carries an
O2 *binding horizon rule*, checked alongside the pre-existing rejection of
already-finalised `event_times` and of backward `event_times`:

```
    IF target_event_time > EQ.run_horizon_T:
      RECORD post_horizon_event(event_type, target_event_time, target_microphase)   # audit-only log
      RETURN post_horizon_event_rejected    # deterministic: the caller records the rejection; nothing is enqueued
```

Audited properties of the rule:

- **Deterministic result.** A rejected event returns `post_horizon_event_rejected`
  and is "never queued, never later dispatched"; the `post_horizon_event(...)` record
  is an audit-only log entry.
- **`T` is legal; only `> T` is rejected.** The specification states "`target_event_time
  = T` is LEGAL (it is the horizon itself); only `target_event_time > T` is rejected."
  The horizon boundary itself is a valid scheduling target.
- **Sole enqueue interface ⇒ no stranded event `> T`.** The closing note is explicit:
  "because this is the ONLY enqueue path and it rejects `target_event_time > T`, the
  queue can never hold an ordinary event beyond the horizon `T` — the run driver
  (§0.7d-run) drains every `event_time <= T`, so nothing is stranded past `T`." This
  combines O2 (the enqueue bound) with the O1 drain of every `event_time <= T`.

## 2. `run_horizon_T` lifecycle (§0.7e, `RoundInitialise`)

`EventQueueContext` (§0.7e) now carries `run_horizon_T`, defined as "the fixed
simulation horizon `T` (= run-end `event_time`)" with the "BINDING SCHEDULING BOUND:
`ScheduleEvent` REJECTS any `target_event_time > run_horizon_T`". Its lifecycle is
per-run:

- **Initialised at run start.** In `RoundInitialise`, at the genesis round
  (`prior_state = null`), the context is created with
  `run_horizon_T = config.horizon_T`.
- **Preserved across rounds.** On a subsequent round, `RoundInitialise` PRESERVES the
  single `EventQueueContext EQ` — including `run_horizon_T` — "from `prior_state`
  (§3.12)", annotated "the horizon bound is per-run, preserved across rounds."

The horizon value is thus identical for every round of a run and is the same value
the run driver (§0.7d-run) and `SettleResidencyBoundary` (`FINAL_RUN_END`) use.

## 3. The security-floor decision at `T` (§9)

`SecurityFloorEvaluate` (§9) has an O2 HORIZON GUARD on its floor-restored branch
(the `(NOT breach) AND round_state = SECURITY_RECOVERY` case):

```
      IF t = run_horizon_T:
        RECORD run_ending_no_recovery_action(episode)          # O2: no CompleteSecurityRecovery scheduled past T
        RETURN run_ending_no_recovery_action
```

A recovery-completion is otherwise seated at a strictly-later `event_time`
(`t_next > t`), which at `t = T` would be `> T` and rejected by `ScheduleEvent`.
The guard therefore seats NO `CompleteSecurityRecovery`; it records
`run_ending_no_recovery_action(episode)` and takes no participation action. At the
horizon the round is instead closed by `CloseRoundAtHorizon` (§20b).

Consequence (as stated at §0.7d and the §9 note): because any participation-changing
action from the security decision is scheduled at a strictly-later `event_time`, and
none can be scheduled past `T`, "a recovery action can never change `H_active` after
the final decision at `t`." No recovery participation action can alter `H_active`
after the final decision at `T`.

## 4. `RecoveryDeadlineEvent` seating bounded to `<= T` (§9, §9a)

The breach-entry branch of `SecurityFloorEvaluate` (§9) seats the named
`RecoveryDeadlineEvent` (§9a) with its target clamped to the horizon:

```
      SET r <- CALL ScheduleEvent(EQ, RoundContext, RecoveryDeadlineEvent,
                     target_event_time = min(t + recovery_deadline_window, run_horizon_T),
                     ...)
      IF r = post_horizon_event_rejected:
        RECORD recovery_deadline_past_horizon(episode)         # O2: none seated past T; horizon-close governs
```

The `min(..., run_horizon_T)` clamp keeps the deadline at `event_time <= T`. Should a
deadline still fall past `T`, `ScheduleEvent` rejects it, the branch records
`recovery_deadline_past_horizon(episode)`, and the round is instead terminated by
`CloseRoundAtHorizon` at the horizon (§20b). `RecoveryDeadlineEvent` (§9a) itself, and
any `CompleteSecurityRecovery` it seats, are likewise bounded to a strictly-later
`event_time <= run_horizon_T`.

## 5. Event types governed by the horizon rule

Every operational enqueue is a `ScheduleEvent` call (§0.7e/§0.7g), so the O2 horizon
rule governs every event type below. Each is therefore subject to the same
`target_event_time > run_horizon_T` rejection.

| Governed event type | Target microphase (§0.7g) | Routes through `ScheduleEvent` | Subject to O2 rule |
|---------------------|---------------------------|:------------------------------:|:------------------:|
| `WakeCompleteEvent` | `WAKE_COMPLETE` | Yes | Yes |
| `HashWorkEvent` | `HASH_WORK` | Yes | Yes |
| `CertificateArrival` | `CERTIFICATE_ARRIVAL` | Yes | Yes |
| `BlockAcceptancePoint` | `FULL_BLOCK_ARRIVAL` | Yes | Yes |
| `ResumeFromPause` | `RESUME` | Yes | Yes |
| `LeaseExpiry` | `LEASE_EXPIRY` | Yes | Yes |
| `CompleteSecurityRecovery` | `RECOVERY_COMPLETE` | Yes | Yes |
| `RecoveryDeadlineEvent` (§9a) | `RECOVERY_DEADLINE` | Yes | Yes |
| `AdversarialParticipationChangeEvent` | `PARTICIPATION_CHANGE` | Yes | Yes |
| `ActiveHashRateUpdate` / periodic monitoring | `MONITORING` | Yes | Yes |

Run-level hooks `CloseRoundAtHorizon` (§20b) and `FinalizeSimulationRun` (§20a) are
NOT queued events and do not pass through `ScheduleEvent`; they are invoked directly
by the run driver and are out of scope for the enqueue bound by construction.

## 6. Acceptance checks

| # | Check | Result | Evidence |
|---|-------|:------:|----------|
| 1 | `ScheduleEvent` rejects `target_event_time > run_horizon_T` deterministically | PASS | §0.7e: `RETURN post_horizon_event_rejected`; nothing enqueued |
| 2 | `target_event_time = T` is legal | PASS | §0.7e: "`target_event_time = T` is LEGAL … only `> T` is rejected" |
| 3 | `ScheduleEvent` is the sole enqueue interface ⇒ no ordinary event `> T` | PASS | §0.7e note: "the queue can never hold an ordinary event beyond the horizon `T`" |
| 4 | `run_horizon_T` initialised at run start and preserved across rounds | PASS | `RoundInitialise`: `run_horizon_T = config.horizon_T`; PRESERVE "from `prior_state` (§3.12)" |
| 5 | Floor-restored decision at `t = T` seats no `CompleteSecurityRecovery` | PASS | §9 O2 HORIZON GUARD: `RETURN run_ending_no_recovery_action` |
| 6 | No recovery action changes `H_active` after the final decision at `T` | PASS | §0.7d / §9 note: strictly-later action, none past `T`, cannot change `H_active` |
| 7 | `RecoveryDeadlineEvent` seating bounded to `<= T`; past-horizon deferred to §20b | PASS | §9: `min(t + recovery_deadline_window, run_horizon_T)`; `recovery_deadline_past_horizon` |
| 8 | Every governed event type routes through `ScheduleEvent` and is subject to O2 | PASS | §0.7g canonical event-type → microphase mapping; Section 5 table |

## Footer

Documentation only. The algorithm is named PoCol; the idle policy within PoCol is
described as a mechanism only and no property is claimed. The A1 accounting baseline
of 8.420833333 kWh is unchanged. The prohibited rebranded-algorithm-name variants are
not used anywhere in this document.
