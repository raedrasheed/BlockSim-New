# Stage 1Q — Run-Hook Namespace & Completion-Time Audit (Q6/Q7)

## Intro

This audit is a **documentation-only** record of two Stage 1Q corrections in
`docs/thesis_revision_v45/stage_01/STAGE_01_PROTOCOL_PSEUDOCODE.md`: **Q6 — the
tagged run-hook namespace** and **Q7 — the deterministic recovery-completion
time**. The consensus specification under revision is **PoCol**. Within PoCol,
*the idle policy within PoCol* is referenced strictly as a mechanism; it is not
the subject of Q6 or Q7 and no behavioural change to it is described here. This
audit claims no property of PoCol and revises no measured quantity: the A1
baseline of **8.420833333 kWh** is UNCHANGED — neither correction alters a state
transition or an energy figure, only how a run-level hook names its envelope and
how a completion instant is derived.

**Scope.** Exactly Q6 and Q7: the `envelope_namespace` tag and optional `hook_id`
on the event envelope (§0.2), the ordinary-vs-run-hook partition minted by
`ScheduleEvent` (§0.7e CREATE envelope) versus `CloseRoundAtHorizon` (§20b), the
`TransitionEventID` inclusion of the tag (J3), the `IN_PROGRESS`/`APPLIED` replay
state on `applied_run_hook_ids` (§0.8/§20b), and the deterministic `target_time`
in `SeatRecoveryCompletion` (§9) with its `horizon_deferred` path.

## 1. The `envelope_namespace` tag and `hook_id` (§0.2)

The immutable event envelope (§0.2) gains two fields:
`{ envelope_namespace, event_type, event_time, delta_cycle, microphase, RoundID,
TemplateID, …, seq, hook_id? }`. Per Q6, `envelope_namespace in {ORDINARY_EVENT,
RUN_HOOK}` partitions the identity space:

- Ordinary queued events, minted by `ScheduleEvent`, carry
  `envelope_namespace = ORDINARY_EVENT`. The §0.7e CREATE envelope sets this
  explicitly: `CREATE envelope = { envelope_namespace = ORDINARY_EVENT, … }`.
- The run-level horizon hook `CloseRoundAtHorizon` (§20b) carries
  `envelope_namespace = RUN_HOOK` and a `hook_id`, namely
  `HorizonHookID = (RunID, run_horizon_T, HORIZON_CLOSE)`.

`hook_id` is present ONLY on `RUN_HOOK` envelopes; it is the optional trailing
field of the envelope tuple and identifies the specific run-hook.

## 2. Collision freedom derives from the TAG (§0.2, §20b)

Per §0.2, "Collision freedom derives from the namespace TAG, not from a magic
delta-cycle number": an `ORDINARY_EVENT` envelope and a `RUN_HOOK` envelope are
DISTINCT even if their numeric `event_seq`/`delta_cycle` coincide, because their
`envelope_namespace` (and `hook_id`) differ. `RUN_HOOK_CYCLE` is a **declared
non-queue `delta_cycle` value** for run-hook envelopes and is illustrative only;
§0.8 and §20b state it is NOT the source of collision freedom — the namespace tag
is. `ScheduleEvent` never produces `RUN_HOOK_CYCLE`.

*Note (TV132) — same numeric `event_seq` distinguished by tag.* Construct an
`ORDINARY_EVENT` envelope and the horizon `RUN_HOOK` envelope with the same
numeric `event_seq` (and the same numeric `delta_cycle`). They remain distinct
identities: the run-hook envelope's `envelope_namespace = RUN_HOOK` plus its
`hook_id = HorizonHookID` separate it from the ordinary one whose
`envelope_namespace = ORDINARY_EVENT` and which carries no `hook_id`. The numeric
coincidence is immaterial — the TAG decides.

## 3. `TransitionEventID` includes the namespace (J3, §20b)

Per §0.2, a `TransitionEventID` (J3) includes `envelope_namespace` (and `hook_id`
when `RUN_HOOK`), so a run-hook transition and an ordinary transition can NEVER
share a `TransitionEventID`. Inside `CloseRoundAtHorizon` (§20b) every miner
transition threads the tagged `horizon_envelope`, so — per the §20b construction
comment — "its `TransitionEventID` carries `envelope_namespace = RUN_HOOK` +
`hook_id` (J3/Q6) — distinct from any ordinary transition." An ordinary
transition, dispatched from an `ORDINARY_EVENT` envelope, carries the
`ORDINARY_EVENT` tag and no `hook_id`, so the two identity spaces cannot alias
even when their remaining tuple fields (`event_time`, `MinerID`, edge) coincide.

## 4. `IN_PROGRESS`/`APPLIED` replay state — partial close cannot replay as full (§0.8, §20b)

`applied_run_hook_ids` is now a **map** `RunHookID -> RUN_HOOK_STATE` with
`RUN_HOOK_STATE in {IN_PROGRESS, APPLIED}` (§0.8, `STRUCTURE RunHookContext`),
initialised empty at run start and preserved across rounds. `CloseRoundAtHorizon`
(§20b) drives the state machine in order:

1. Compute `HorizonHookID <- (RunID, run_horizon_T, HORIZON_CLOSE)`.
2. **Replay guard:** `IF HorizonHookID in RunHookContext.applied_run_hook_ids`
   (state is `IN_PROGRESS` or `APPLIED`) then
   `RETURN horizon_close_duplicate_noop(HorizonHookID)`.
3. **Mark `IN_PROGRESS` BEFORE any mutation:**
   `SET applied_run_hook_ids[HorizonHookID] <- IN_PROGRESS`.
4. Mint the tagged run-hook envelope, run the single `CloseRoundAssignments`
   closure path, record the horizon-end disposition, and transition
   `round_state -> ROUND_ABORTED`.
5. **Mark `APPLIED` atomically with the completed close:**
   `SET applied_run_hook_ids[HorizonHookID] <- APPLIED`.

Because `IN_PROGRESS` is written before any mutation (step 3) and the guard
(step 2) treats both `IN_PROGRESS` and `APPLIED` as a deterministic no-op, a
PARTIAL invocation — one interrupted mid-close — can NEVER be replayed as a
second FULL close. The retry sees `IN_PROGRESS` and returns
`horizon_close_duplicate_noop`, so there is no second transition energy and no
second residency boundary. Exactly one horizon close occurs per run.

## 5. Deterministic completion time replaces `t_next` (§9)

`SeatRecoveryCompletion` (§9) now computes the completion instant as
`SET target_time <- t + configured_recovery_completion_delay`, where
`configured_recovery_completion_delay` is a **declared config constant `> 0`** (or
the next-representable simulation instant). This REPLACES the previously undefined
`t_next`: §0.8 records that the constant "must be `> 0` … supplies the
`RecoveryCompletionDueEvent` `target_time` (replaces the undefined `t_next`)." The
`RecoveryCompletionDueEvent` is then seated at that deterministic `target_time`
through `ScheduleEvent`, and `pending_recovery_decisions[episode]` is updated ONLY
on scheduler success (P4). The completion instant is thus fully defined and
reproducible, not an unspecified "next event time."

## 6. The `target_time > T` horizon-deferred path (§9, §20b)

Per Q7/O2, a completion is NEVER seated beyond the fixed horizon `T`. In
`SeatRecoveryCompletion` (§9), after the decision record is created:

```
IF target_time > run_horizon_T:
  SET recovery_decisions[decision_id].status <- CANCELLED
  RECORD horizon_deferred(decision_id, target_time)
  RETURN recovery_completion_horizon_deferred(decision_id)
```

No `RecoveryCompletionDueEvent` is seated; the decision record is marked
`CANCELLED` and `horizon_deferred(decision_id, target_time)` is recorded. A
superseded decision stays invalid (its status is terminal-negative and is never
revived by a later failed or deferred schedule, §9 NOTE). Run end in this case is
governed by `CloseRoundAtHorizon` (§20b), the run-level hook that closes a
still-nonterminal round at `T` — consistent with the O2 binding rule that
`ScheduleEvent` rejects any `target_event_time > run_horizon_T`.

## 7. Acceptance checks

| # | Check (gate) | §-evidence | Result |
|---|--------------|-----------|--------|
| 1 | Envelope (§0.2) carries `envelope_namespace in {ORDINARY_EVENT, RUN_HOOK}` and optional `hook_id` | §0.2 envelope tuple; Q6 note | PASS |
| 2 | Ordinary `ScheduleEvent` envelopes are `ORDINARY_EVENT`; `CloseRoundAtHorizon` is `RUN_HOOK` with `hook_id = HorizonHookID` | §0.7e CREATE envelope; §20b `horizon_envelope` | PASS |
| 3 | (Gate 8) Collision freedom is from the TAG, not `RUN_HOOK_CYCLE`; equal numeric `event_seq` stays distinct (TV132) | §0.2; §0.8 constants; §20b NOTE | PASS |
| 4 | `TransitionEventID` (J3) includes `envelope_namespace` (and `hook_id` when `RUN_HOOK`); run-hook and ordinary transitions never share an id | §0.2 (J3 note); §20b transition-threading comment | PASS |
| 5 | (Gate 8) `applied_run_hook_ids` is `RunHookID -> {IN_PROGRESS, APPLIED}`; `IN_PROGRESS` set before mutation, `APPLIED` after completion; partial close cannot replay as full (`horizon_close_duplicate_noop`) | §0.8 `RunHookContext`; §20b replay guard | PASS |
| 6 | (Gate 9) `target_time = t + configured_recovery_completion_delay`, a declared config constant `> 0`, replaces the undefined `t_next`; event seated at that instant | §9 `SeatRecoveryCompletion`; §0.8 constant note | PASS |
| 7 | (Gate 9) `target_time > run_horizon_T` seats no completion: decision `CANCELLED`, `horizon_deferred` recorded, superseded decision stays invalid | §9 horizon branch | PASS |
| 8 | Run end when deferred is governed by `CloseRoundAtHorizon` (§20b), consistent with O2 (`ScheduleEvent` rejects `> T`) | §20b; §9 NOTE; §0.7e O2 | PASS |

---

Documentation only. The consensus specification is named **PoCol**; *the idle
policy within PoCol* is referenced here as a mechanism only. No property is
claimed. The **A1 baseline 8.420833333 kWh is unchanged**. The prohibited
rebranded-algorithm-name variants are not used anywhere in this document.
