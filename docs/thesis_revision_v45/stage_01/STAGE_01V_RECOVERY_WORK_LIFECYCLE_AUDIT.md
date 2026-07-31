# Stage 1V — Recovery-Work Lifecycle Audit (V7)

This is a documentation-only paper audit of the Stage-1V correction **V7 — the complete
recovery-work lifecycle** as edited in
`docs/thesis_revision_v45/stage_01/STAGE_01_PROTOCOL_PSEUDOCODE.md`. V7 promotes the recovery-WORK
record (introduced in Stage-1U as the reserve-activation / redistribution action attempted WHILE
the security floor is still breached) from an object with an *implicit* status model into an object
with an EXPLICIT, complete, single-disposition lifecycle: a nine-value `RECOVERY_WORK_STATUS`
enum, two lifecycle invariants (exactly one live-or-terminal disposition per `RecoveryWorkID`; at
most one in-flight record per episode), an atomic supersede-before-publish rule, and a terminal
cleanup that iterates EVERY non-terminal work record of a closing episode rather than only the
single `pending_recovery_work` pointer.

**Scope and standing conventions.** The consensus algorithm is named **PoCol**; the idle policy
within PoCol is referenced only as a named mechanism, and this audit claims no energy, security, or
fairness property of it. V7 is a recovery-LIFECYCLE bookkeeping refinement — an explicit status
model and a leak-closing cancellation sweep — and is NOT a change to how time, energy, or the
security census are counted. No census value, residency interval, transition-energy term, or
accounting quantity is edited; the A1 accepted accounting baseline is UNCHANGED. Every claim below
is checked against the pseudocode as edited and against its three companion documents
(`STAGE_01_INVARIANT_CATALOGUE.md`, `STAGE_01_ROUND_STATE_MACHINE.md`, `STAGE_01_TERMINOLOGY.md`);
no behaviour is inferred beyond the text. Line numbers are those of the audited files at the time
of writing.

---

## 1. The defect V7 closes

Before V7 the recovery-work record carried a status field, but only a partial and implicit status
vocabulary. Two distinct hazards followed.

**(a) No complete status model — terminal/superseded/failed/deferred states were implicit.** A
recovery-work identity can end its life in several distinct ways: it can be consumed by the
post-epilogue hook, superseded by a newer census version, rejected by the scheduler, deferred past
the run horizon, or cancelled at round closure. Without a closed enumeration naming each of these,
the "one disposition per identity" property could not be stated, let alone checked: a record could
in principle be read as still-ARMED after its due event had already been cancelled, or two records
of the same episode could both appear live because nothing named the moment one of them became
terminal.

**(b) The episode-cancel path only touched the pending pointer — a leak / liveness hazard.** The
Stage-1U / S4 terminal cleanup `CancelActiveRecoveryEpisode` cancelled the episode's pending and
applying recovery *decisions* and their queued events, but for recovery *work* it reasoned only
about the single at-most-one pointer `pending_recovery_work[episode]`. If, through any
supersede-then-reseat interleaving, a second non-terminal work record and its queued
`RecoveryWorkDueEvent` had ever been left reachable while the pointer named a different record,
terminal closure would clear the pointer and mark TERMINAL_CANCELLED while an orphaned
ARMED/DUE/APPLYING work record — and its live queued event — survived the closing round. That is
both a state leak (a live work record for a dead episode) and a liveness hazard (a queued event
with no owning episode, which could later fire against a stale round). V7 removes the possibility
structurally by (i) forbidding two live in-flight records ever coexisting and (ii) sweeping ALL
non-terminal records, not just the pointer, at closure.

---

## 2. The complete status enum

The enum is declared verbatim in the §0.8 registries block:

> `# RECOVERY_WORK_STATUS in { CREATED, ARMED, DUE, APPLYING, CONSUMED, SUPERSEDED, SCHEDULE_FAILED, HORIZON_DEFERRED, CANCELLED }   # V7 (complete lifecycle)`
> — `STAGE_01_PROTOCOL_PSEUDOCODE.md` line 742

Nine values, three live / transient and six terminal. The `work_record` that carries the status is
declared immediately above (lines 732–737): `recovery_work : map RecoveryWorkID -> work_record {
episode, action (RECOVERY_WORK_ACTION), work_class (RECOVERY_WORK_CLASS, V6), bound_census_version
(RecoveryCensusVersion), work_generation, work_id (RecoveryWorkID), status (RECOVERY_WORK_STATUS),
work_due_event_ref, due_at_event_time, due_dispatch_envelope, due_status (CONTINUATION_DUE_STATUS)
}`, with the closing sentence "V7: EVERY RecoveryWorkID has exactly one live or terminal
disposition" (line 737).

| # | Status | Live / Terminal | Meaning | Entry condition (grounded) | Exit transitions |
|---|--------|-----------------|---------|-----------------------------|-------------------|
| 1 | `CREATED` | live (nominal / pre-publication) | Identity `(episode, candidate_seq)` computed but not yet published. | Compute-only: `candidate_seq`/`work_id` set before any mutation (lines 2732–2733). | → `ARMED` atomically on `ScheduleEvent` success; never persisted (see §7 note). |
| 2 | `ARMED` | live | Work record published; its `RecoveryWorkDueEvent` is queued at `t_due`. | `SeatRecoveryWork` publishes `work_record(... status = ARMED ...)` after a successful enqueue (line 2748). | → `DUE` (due event fires); → `SUPERSEDED` (reconcile/reseat, stale version); → `CANCELLED` (episode cancel). |
| 3 | `DUE` | live | The due event fired at `t`; the due FACT is recorded and the census refreshed; no work performed yet. | `RecoveryWorkDueEvent` sets `status <- DUE` and `due_status <- DUE` (lines 2788–2789). | → `APPLYING` (fresh, breach-before-deadline); → `SUPERSEDED` (no longer warranted / stale version); → `CONSUMED` (freshness fail as superseded — see note); → `CANCELLED` (episode cancel). |
| 4 | `APPLYING` | live (transient) | The post-epilogue work transaction (plan / commit / rollback) is in progress. | `ApplyRecoveryWorkAfterEpilogue` sets `status <- APPLYING` when the work begins (line 2825). | → `CONSUMED` (applied, rolled back, commit-failed, or plan-invalid); → the abort path on an irreversible rollback failure. |
| 5 | `CONSUMED` | **terminal** | The due fact was explicitly consumed by the post-epilogue hook; work applied or legally reversed. | `ApplyRecoveryWorkAfterEpilogue` sets `status <- CONSUMED` on every completed disposition (lines 2832, 2839, 2846, 2854, 2861). | none (terminal). |
| 6 | `SUPERSEDED` | **terminal** | A newer census version, a reseat, or a freshness failure retired this identity; its queued event was cancelled and its due fact consumed. | Set in `SeatRecoveryWork` (2725), `ReconcilePendingRecoveryWork` (2532, 2542), `ApplyRecoveryWorkAfterEpilogue` freshness gate (2821). | none (terminal). |
| 7 | `SCHEDULE_FAILED` | **terminal** | The scheduler rejected the `RecoveryWorkDueEvent` enqueue; the would-be identity was never published. | Nominal disposition of a rejected enqueue; returned as `recovery_work_not_seated` (lines 2753–2755). Not stamped onto a record (see §7). | none (terminal). |
| 8 | `HORIZON_DEFERRED` | **terminal** | `t_due` fell beyond `run_horizon_T`; no event was enqueued and no identity published. | Nominal disposition of the horizon guard; returned as `recovery_work_horizon_deferred` (lines 2735–2737). Not stamped onto a record (see §7). | none (terminal). |
| 9 | `CANCELLED` | **terminal** | The episode closed unfinished; the non-terminal work record and its queued event were cancelled. | `CancelActiveRecoveryEpisode` sets `status <- CANCELLED` for every non-terminal record (line 2452). | none (terminal). |

The `due_status` field (typed `CONTINUATION_DUE_STATUS in {NOT_DUE, DUE, CONSUMED, SUPERSEDED,
CANCELLED}`, §0.8 line 745) is a SEPARATE, parallel fact — "is the due event's DUE fact still
outstanding" — that `ProcessEventTime` asserts on explicitly (see §5). V7's `status` is the
lifecycle of the *identity*; `due_status` is the lifecycle of the *due fact*. They move together at
every terminal transition (e.g. lines 2452–2453 set `status <- CANCELLED` and, when the due fact
was outstanding, `due_status <- CANCELLED`).

---

## 3. State-transition model for a single `RecoveryWorkID`

The following table is the complete transition relation for one work identity, each arrow annotated
with the procedure and line that writes it.

| From | To | Trigger (procedure → line) |
|------|----|-----------------------------|
| — | `CREATED` | identity computed compute-only in `SeatRecoveryWork` (2732–2733); not persisted |
| `CREATED` | `ARMED` | `SeatRecoveryWork` publishes the record after `ScheduleEvent` succeeds (2748) |
| `CREATED` | `SCHEDULE_FAILED` | `SeatRecoveryWork` enqueue rejected → `recovery_work_not_seated` (2753–2755); disposition only |
| `CREATED` | `HORIZON_DEFERRED` | `SeatRecoveryWork` `t_due > run_horizon_T` → `recovery_work_horizon_deferred` (2735–2737); disposition only |
| `ARMED` | `DUE` | `RecoveryWorkDueEvent` records the due fact (2788–2789) |
| `ARMED` | `SUPERSEDED` | `SeatRecoveryWork` stale-prior reseat (2725); `ReconcilePendingRecoveryWork` ARMED-not-warranted (2542) |
| `ARMED` | `CANCELLED` | `CancelActiveRecoveryEpisode` (2452) |
| `DUE` | `APPLYING` | `ApplyRecoveryWorkAfterEpilogue` when the work begins (2825) |
| `DUE` | `SUPERSEDED` | `ReconcilePendingRecoveryWork` DUE-not-warranted (2532); `ApplyRecoveryWorkAfterEpilogue` freshness gate (2821) |
| `DUE` | `CANCELLED` | `CancelActiveRecoveryEpisode` (2452) |
| `APPLYING` | `CONSUMED` | `ApplyRecoveryWorkAfterEpilogue` applied / rolled-back / commit-failed / plan-invalid (2832, 2839, 2846, 2854, 2861) |
| `APPLYING` | (episode abort) | `ApplyRecoveryWorkAfterEpilogue` irreversible rollback → `RECOVERY_INSTALL_FAILED_ABORTED` (2846–2852) |

**Happy path.** `CREATED → ARMED → DUE → APPLYING → CONSUMED`. A breach-before-deadline census in
`SecurityFloorEvaluate` classifies the work and calls `SeatRecoveryWork` (line 2375), which
publishes the record `ARMED` (2748); the queued `RecoveryWorkDueEvent` fires and sets `DUE`
(2788); the post-epilogue `ApplyRecoveryWorkAfterEpilogue` sets `APPLYING` (2825), runs the
Prepare / Commit plan, and sets `CONSUMED` (2861). The round STAYS `SECURITY_RECOVERY` throughout —
recovery work is never an outcome and is never marked `APPLIED`/`RESTORED` (NOTE, lines 2866–2872).

**Supersession path.** A newer final census retires an in-flight record before it applies:
`ReconcilePendingRecoveryWork` rebinds a still-warranted DUE record to the latest version (same
`RecoveryWorkID`, lines 2529–2530) or, when no longer warranted, sets `SUPERSEDED`, cancels the
queued event, and clears the pointer (2532–2534); an ARMED future record is symmetrically
re-affirmed (2540) or superseded (2542). `SeatRecoveryWork` supersedes a *stale prior* in-flight
record before publishing a replacement (2725–2728).

**Failure / deferral paths.** A rejected enqueue yields `SCHEDULE_FAILED` (disposition
`recovery_work_not_seated`, 2753–2755); a past-horizon `t_due` yields `HORIZON_DEFERRED`
(disposition `recovery_work_horizon_deferred`, 2735–2737). In both cases the atomic protocol
publishes NO record and the round stays `SECURITY_RECOVERY` (§7 note).

**Cancel path.** Any non-terminal record of a closing, non-finalising episode is set `CANCELLED`
by `CancelActiveRecoveryEpisode` (2452); see §6.

---

## 4. Lifecycle invariant I — exactly one disposition per `RecoveryWorkID`

The §0.8 registry states the invariant directly:

> `recovery_work : ... A work action is an explicit identity with a COMPLETE lifecycle; it is NEVER a RecoveryDecisionID and is NEVER APPLIED. V7: EVERY RecoveryWorkID has exactly one live or terminal disposition.`
> — lines 736–737

This is enforced by construction: the status field is single-valued, and every write in the entire
pseudocode is either the initial publication as `ARMED` (2748) or a single further transition
guarded so it fires at most once for a given identity (the terminal statuses have no exit edge —
see §3). The companion catalogue restates it as part of invariant I16:

> "**V7:** each `RecoveryWorkID` has exactly one live or terminal disposition and at most one per
> episode is {ARMED, DUE, APPLYING}; terminal closure cancels EVERY nonterminal work record, so no
> orphan survives."
> — `STAGE_01_INVARIANT_CATALOGUE.md` lines 319–321

## 4b. Lifecycle invariant II — at most one in-flight record per episode, with atomic supersede-before-publish

The at-most-one property and the atomicity rule that maintains it are declared together on
`pending_recovery_work`:

> `pending_recovery_work : U1/V7 — map RecoveryEpisodeID -> the AT-MOST-ONE in-flight RecoveryWorkID (null otherwise). V7 INVARIANT: at most one work record per episode is in {ARMED, DUE, APPLYING}; before a new work identity is published, the prior one is atomically SUPERSEDED/CANCELLED, its queued event cancelled, and its due fact consumed (SeatRecoveryWork / ReconcilePendingRecoveryWork).`
> — `STAGE_01_PROTOCOL_PSEUDOCODE.md` lines 738–741

The **supersede-before-publish** rule is realised in `SeatRecoveryWork` in the exact order the
invariant demands — retire the stale prior record FIRST, publish the replacement only afterwards:

```
IF pending_recovery_work[episode] != null:
  SET W0 <- recovery_work[pending_recovery_work[episode]]
  IF W0.status = DUE AND W0.due_at_event_time = t:
    RETURN recovery_work_already_pending(W0.action)   # V1: never replace a DUE record at the current event_time
  IF W0.status in {ARMED, DUE, APPLYING} AND W0.bound_census_version = census_version:
    RETURN recovery_work_already_pending(W0.action)   # V7: one live in-flight, still current -> do not re-seat
  # V7: a STALE prior in-flight record exists ... ATOMICALLY SUPERSEDE/CANCEL it and consume its due fact BEFORE publishing
  SET recovery_work[W0.work_id].status <- SUPERSEDED
  IF W0.due_status = DUE: SET recovery_work[W0.work_id].due_status <- SUPERSEDED
  IF W0.work_due_event_ref != null AND W0.work_due_event_ref is still pending on EQ: CANCEL W0.work_due_event_ref on EQ
  SET pending_recovery_work[episode] <- null
```
— lines 2715–2728

Only after this retirement does the atomic seat compute the new identity, schedule, and publish the
replacement `ARMED` record and repoint `pending_recovery_work[episode]` (lines 2732–2752). The
publish is gated on `ScheduleEvent` success (`IF result = scheduled(...)`, line 2744), so the seq
is never advanced and no record is published on a rejected enqueue (2753–2755). Two consequences
follow, both explicit in the text:

- **No two live in-flight records coexist.** The stale prior is `SUPERSEDED` (terminal) before the
  replacement exists, so at every point at most one record of the episode is in {ARMED, DUE,
  APPLYING}. The NOTE confirms: "It is idempotent per episode (at most one in-flight
  RecoveryWorkID)" (line 2763).
- **A DUE-at-current-time record is never replaced.** The V1 guard (lines 2717–2720) returns
  `recovery_work_already_pending` rather than seating a second record over a record that is DUE at
  `t`; `ReconcilePendingRecoveryWork` has already rebound or superseded it (lines 2717–2718). This
  is the property the task singles out at ~line 2717 and it is present verbatim.

`ReconcilePendingRecoveryWork` (lines 2515–2553) is the second maintainer of the same invariant,
run by `SecurityFloorEvaluate` after `CommitRecoveryCensus` + `ReconcilePendingRecoveryDecisions`
and BEFORE `SeatRecoveryWork` is considered (call site line 2361). Its dispositions map onto the
V7 statuses exactly: a still-warranted DUE record is REBOUND (same id, no new record, lines
2528–2530); a no-longer-warranted DUE record is `SUPERSEDED` (2532); an ARMED future record is
re-affirmed (2540) or `SUPERSEDED` (2542) — "NEVER leaving two live in-flight work records"
(NOTE, line 2553).

---

## 5. `ApplyRecoveryWorkAfterEpilogue` sets `APPLYING`; the finalisation assertion

The post-epilogue hook is the sole place recovery work is performed. It sets `APPLYING` at the
instant the work transaction begins, immediately after the freshness gate passes:

```
# ---- FRESH: perform the WORK. It runs WHILE the floor is still breached; it NEVER applies RESTORED. ----
SET recovery_work[work_id].status <- APPLYING   # V7: DUE -> APPLYING while the work transaction runs (lifecycle)
```
— lines 2824–2825

Every exit of the transaction then writes a terminal status: `CONSUMED` on applied (2861),
rolled-back (2854), commit-failed (2839), or plan-invalid (2832); `SUPERSEDED` when the freshness
gate fails before work begins (2820–2821); and, on an irreversible rollback failure, `CONSUMED`
plus the `RECOVERY_INSTALL_FAILED_ABORTED` episode disposition and a recovery-finalising
`RoundAbort` (2846–2852). No path leaves the record `APPLYING`.

`ProcessEventTime` closes the loop with an explicit finalisation assertion keyed on the parallel
due fact, not on a timestamp:

> `ASSERT no recovery_work[*].due_status = DUE with due_at_event_time = t`
> `# U1/U4: every DUE recovery-work fact at t was explicitly consumed by ApplyRecoveryWorkAfterEpilogue`
> — lines 276–277

Because every terminal `status` transition co-writes `due_status` (CONSUMED / SUPERSEDED /
CANCELLED), a record cannot be left DUE-at-`t` after the hook runs; the assertion would fail
otherwise, making the "one disposition, explicitly consumed" property machine-checkable at every
finalised event time.

---

## 6. Terminal cleanup — `CancelActiveRecoveryEpisode` iterates ALL non-terminal records

The task's central liveness requirement is that episode cancellation must sweep every non-terminal
work record, not only the `pending_recovery_work` pointer. The audited procedure does exactly this
(the V7 loop, quoted verbatim):

```
# V7: cancel EVERY NONTERMINAL recovery-WORK record of the episode — NOT only the one currently referenced by
#   pending_recovery_work — so no orphan ARMED/DUE/APPLYING work record survives terminal closure.
FOR EACH work_id in recovery_work WHERE recovery_work[work_id].episode = episode
         AND recovery_work[work_id].status in {CREATED, ARMED, DUE, APPLYING} (stable order by work_id):
  SET W <- recovery_work[work_id]
  IF W.work_due_event_ref != null AND W.work_due_event_ref is still pending on EQ:
    CANCEL W.work_due_event_ref on EQ                       # V7: cancel the queued RecoveryWorkDueEvent
  SET recovery_work[work_id].status <- CANCELLED
  IF W.due_status = DUE: SET recovery_work[work_id].due_status <- CANCELLED   # U4/V7: explicit terminal consumption
SET pending_recovery_work[episode] <- null                  # V7: no live in-flight work remains
```
— `STAGE_01_PROTOCOL_PSEUDOCODE.md` lines 2445–2454

The `FOR EACH ... WHERE ... status in {CREATED, ARMED, DUE, APPLYING}` iterates the whole
`recovery_work` map filtered by episode and by the non-terminal status set — this is the fix: it no
longer depends on the pointer, so an orphaned record that the pointer does not name is still swept.
Each such record has its queued `RecoveryWorkDueEvent` cancelled, is set `CANCELLED`, and (if its
due fact was outstanding) has `due_status <- CANCELLED`. Only after the sweep is the pointer nulled
(2454), the disposition recorded `TERMINAL_CANCELLED`, and `current_recovery_episode` cleared
(2457–2458). Recovery-work events are also cancelled generically at the queue level in
`CloseRoundAssignments` (line 4295), and this procedure is invoked only from that single closure
path for every terminal closure except the recovery-finalising abort (guard `IF
current_recovery_episode != null AND NOT recovery_finalising`, lines 4302–4303; preconditions,
lines 2429–2431).

**Effect on each status at episode cancel:**

| Record status at closure | Action in the V7 sweep | Resulting status |
|--------------------------|------------------------|-------------------|
| `CREATED` | included in the non-terminal set (defensive; not normally persisted, §7) | `CANCELLED` |
| `ARMED` | queued `RecoveryWorkDueEvent` cancelled (if pending); status set | `CANCELLED` |
| `DUE` | queued event cancelled (if pending); `due_status <- CANCELLED`; status set | `CANCELLED` |
| `APPLYING` | in-set; status set (its own transaction would already be terminalising) | `CANCELLED` |
| `CONSUMED` | terminal — excluded by the `status in {...}` filter | unchanged |
| `SUPERSEDED` | terminal — excluded | unchanged |
| `SCHEDULE_FAILED` | terminal — excluded (and no record persisted) | unchanged |
| `HORIZON_DEFERRED` | terminal — excluded (and no record persisted) | unchanged |
| `CANCELLED` | terminal — excluded (idempotent under re-entry) | unchanged |

The NOTE confirms the invariant this establishes: "a terminal round NEVER leaves an active recovery
episode (S4 invariant)" (lines 2460–2465), now extended by V7 to "no orphan ARMED/DUE/APPLYING
record survives terminal closure."

---

## 7. Where each status is set — procedure → status-write map

Grounding the enum against the actual writes (`grep 'recovery_work[...].status <-'` and the
`work_record(... status = ...)` constructor) yields the following map. Six of the nine values are
written onto a persisted `work_record`; three are lifecycle DISPOSITIONS that name a would-be or
pre-publication state and are, by the atomic-seat design, never stamped onto a persisted record.

| Status | Written by (procedure → line) | Persisted onto a `work_record`? |
|--------|-------------------------------|----------------------------------|
| `ARMED` | `SeatRecoveryWork` — `work_record(... status = ARMED ...)` (2747–2748) | yes |
| `DUE` | `RecoveryWorkDueEvent` — `status <- DUE` (2788) | yes |
| `APPLYING` | `ApplyRecoveryWorkAfterEpilogue` — `status <- APPLYING` (2825) | yes |
| `CONSUMED` | `ApplyRecoveryWorkAfterEpilogue` — 2832, 2839, 2846, 2854, 2861 | yes |
| `SUPERSEDED` | `SeatRecoveryWork` 2725; `ReconcilePendingRecoveryWork` 2532, 2542; `ApplyRecoveryWorkAfterEpilogue` 2821 | yes |
| `CANCELLED` | `CancelActiveRecoveryEpisode` — `status <- CANCELLED` (2452) | yes |
| `CREATED` | nominal pre-publication state; identity computed compute-only (2732–2733) | **no** — see note |
| `SCHEDULE_FAILED` | disposition of a rejected enqueue; `recovery_work_not_seated` (2753–2755) | **no** — see note |
| `HORIZON_DEFERRED` | disposition of the horizon guard; `recovery_work_horizon_deferred` (2735–2737) | **no** — see note |

**Faithful-reading note (three non-persisted statuses).** This is an honest finding, not a defect.
`SeatRecoveryWork` implements the U3/V7 ATOMIC-SEAT protocol: it computes the candidate identity
and target compute-only, calls `ScheduleEvent` WITHOUT mutating any active state, and publishes the
`work_record` (as `ARMED`) and advances `recovery_work_seq` ONLY after a successful enqueue (NOTE,
lines 2757–2766). Consequently:

- `CREATED` is the conceptual pre-publication phase (identity computed at 2732–2733, record not yet
  created). No record is ever persisted at `CREATED`, because the first persisted status is `ARMED`
  (2748). The enum nonetheless lists `CREATED`, and `CancelActiveRecoveryEpisode`'s non-terminal
  filter includes it (line 2448), as a defensive completeness measure so the sweep is total even
  under a future variant that persisted a pre-armed record.
- `SCHEDULE_FAILED` and `HORIZON_DEFERRED` are the two ways the seat can fail to publish. Because
  the protocol publishes NO record on either (it "does NOT advance recovery_work_seq, publishes NO
  event reference", lines 2753–2761, and for horizon "no event enqueued", lines 2735–2737), these
  two enum values name the lifecycle DISPOSITION returned to the caller (`recovery_work_not_seated`
  / `recovery_work_horizon_deferred`) rather than a status ever written onto a `work_record`. They
  complete the vocabulary symbolically so that every terminal outcome of a work seat has a named
  status, while the atomic design guarantees there is no half-published record to carry it. A future
  revision wishing to make these fully observable would publish a terminal `work_record` in the
  rejected/horizon branches; the current text deliberately does not, to preserve "never advance the
  seq on a rejected enqueue."

The `RECOVERY_DECISION_STATUS` enum (§0.8 lines 700–701) is the deliberate analogue for recovery
*decisions* and DOES persist `SCHEDULE_FAILED` / `HORIZON_DEFERRED` onto a decision record (e.g.
`SetRecoveryDecisionStatus(..., SCHEDULE_FAILED)` at line 2601), because decision seating mints the
record BEFORE scheduling (line 2577) whereas work seating mints it only after. The asymmetry is
intrinsic to the two seat protocols and is faithfully reflected in this audit.

---

## 8. Traceability

**Pseudocode (`STAGE_01_PROTOCOL_PSEUDOCODE.md`).**
- §0.8 registries — `RECOVERY_WORK_STATUS` enum (742); `work_record` fields incl. `status`,
  `work_class` (732–737); `pending_recovery_work` at-most-one + atomic supersede-before-publish
  (738–741); `RECOVERY_WORK_CLASS` (720–727).
- `SecurityFloorEvaluate` — reconcile-then-seat flow (2347–2379); `ReconcilePendingRecoveryWork`
  call before `SeatRecoveryWork` (2361, 2375).
- `CancelActiveRecoveryEpisode` — V7 all-non-terminal sweep (2427–2465, loop 2445–2454).
- `ReconcilePendingRecoveryWork` — rebind / re-affirm / supersede dispositions (2515–2553).
- `SeatRecoveryWork` — atomic supersede-before-publish; never replace DUE-at-`t`; publish `ARMED`
  only on schedule success (2706–2766).
- `RecoveryWorkDueEvent` — `status <- DUE` (2768–2800).
- `ApplyRecoveryWorkAfterEpilogue` — `status <- APPLYING` at work start; terminal `CONSUMED` /
  `SUPERSEDED` / abort (2802–2872).
- `ProcessEventTime` — hook ordering (268) and the explicit `due_status = DUE` finalisation
  assertion (276–277).
- `CloseRoundAssignments` — sole caller gate (4295, 4302–4303).

**Invariant catalogue (`STAGE_01_INVARIANT_CATALOGUE.md`).** I16 V7 clause — one live/terminal
disposition per id; at most one {ARMED, DUE, APPLYING} per episode; terminal closure cancels every
non-terminal record so no orphan survives (lines 319–321), within the U1/V6 recovery-work-vs-outcome
context (306–318).

**Round state machine (`STAGE_01_ROUND_STATE_MACHINE.md`).** §3.10 addendum V7 block — the nine-value
enum, the two invariants, atomic supersede/cancel-and-consume before publish, and the
`CancelActiveRecoveryEpisode` all-non-terminal sweep (lines 616–621).

**Terminology (`STAGE_01_TERMINOLOGY.md`).** Stage-1V addendum, `RECOVERY_WORK_STATUS` complete
lifecycle (V7) entry (lines 814–816); `ReconcilePendingRecoveryWork` (V1) entry (790–795);
`CONTINUATION_DUE_STATUS` (U4) parallel due-fact vocabulary (767–770); the U1 work-vs-outcome and
U3 atomic-re-arm entries this refinement builds on (751–766).

**Standing.** V7 is a lifecycle-bookkeeping refinement: an explicit status enumeration, a
single-disposition invariant, an at-most-one-in-flight invariant with atomic supersede-before-publish,
and a leak-closing all-non-terminal cancellation sweep. It edits no census, residency, or
transition-energy quantity; the A1 accepted accounting baseline is unaffected. The one faithful-reading
qualification recorded above (§7) — that `CREATED`, `SCHEDULE_FAILED`, and `HORIZON_DEFERRED` are
enum-declared dispositions that the atomic-seat protocol never persists onto a `work_record` — is a
property of the audited text, reported rather than repaired, consistent with the documentation-only
mandate of this stage.
