# Stage 1V — Setup Rollback & Liveness Audit (V8)

## Scope

This document audits correction **V8 (executable ordinary assignment-setup rollback +
setup-retry liveness)** of the Stage-1V thesis revision. It is a *descriptive* audit: it
records and cross-checks the current specification and introduces no normative change. The
subject matter is the failure behaviour of the two *ordinary* round-setup procedures —
`PrepareParticipantsForNewRound` (the new-round participant activation path) and
`TemplateRefresh` (the exhaustion/disagreement template rebuild path) — as opposed to the
*recovery-installation* setup path (branch C / U5), which is governed separately.

All line references are to the current contents of the companion artifacts in this
directory as read during the audit:

- `STAGE_01_PROTOCOL_PSEUDOCODE.md` (the executable specification);
- `STAGE_01_ROUND_STATE_MACHINE.md` (§3.10 Stage-1V addenda);
- `STAGE_01_INVARIANT_CATALOGUE.md`;
- `STAGE_01_TERMINOLOGY.md` (Stage-1V addendum);
- `STAGE_01_TRACEABILITY_MATRIX.csv` (row `R157`).

The claims below are grounded exclusively in those file contents; where an expected artifact
is absent it is reported as absent rather than inferred (see §8).

---

## 1. The defect V8 repairs

Pre-V8, both ordinary round-setup procedures established an intended assignment set by
iterating eligible miners in stable `MinerID` order, creating a fresh `PENDING` assignment
per miner and issuing a `StartWake` for each, then performing the `ASSIGNMENT -> HASHING`
transition through `CompleteAssignmentPhase`. Two failure modes were reachable *after* work
had already been committed but *before* the irreversible `HASHING` transition:

1. a `StartWake` inside the activation loop could fail (its structured result is
   `wake_schedule_failed_before_transition` or `wake_transition_failed_after_seat`,
   pseudocode lines 1126–1127); and
2. `CompleteAssignmentPhase` could return `assignment_phase_failed(malformed_assignment_set)`
   or `assignment_phase_failed(transition_failed)` (pseudocode lines 1722, 1727, 1729),
   which — by construction — leaves the round in `ASSIGNMENT` (reversible).

The pre-V8 specification named no executable procedure to *undo* the assignments and wakes
already created on such a failure, and prescribed no explicit *continuation*. The consequent
hazards are exactly the two the traceability matrix records as the negative test for `R157`:
"a setup failure returning while `round_state = ASSIGNMENT` with no controller; a participant
left `WAKING` for a rolled-back head." Concretely, a half-built setup could leave (a) orphaned
`WakeCompleteEvent`s seated on the event queue for heads that ought not to exist, (b)
half-created `PENDING` heads never closed, and (c) miners stranded in `WAKING` bound to those
heads — with the round frozen in `ASSIGNMENT` and no seated event to advance it, i.e. a silent
stall.

V8 closes both hazards by (i) capturing every structured `StartWake` result into a *named
local setup-transaction record* as the loop proceeds, (ii) introducing two *named, executable
rollback procedures* that consume that record, and (iii) mandating an *explicit liveness path*
(deterministic retry or declared abort) after a successful rollback. The round is thereby
never left in `ASSIGNMENT` with no controller.

---

## 2. The setup-transaction record

Both procedures maintain a `setup_transaction(...)` value with three fields. The record is
*local* to the setup invocation and is the sole input (besides `RoundContext`) to the matching
rollback.

| Field | Contents | Populated by |
|---|---|---|
| `wakes` | the list of **actual `WakeEventRef`s** returned inside each `wake_seated(...)` result | `ADD wref to …wakes` on every `IF wr = wake_seated(waid, wref, wtt, ws)` branch |
| `created_assignments` | the list of `AssignmentID`s of the `PENDING` heads this setup created | `ADD AssignmentID(a) to …created_assignments` immediately after each `CreatePendingAssignment` |
| `prior_states` | a map `{MinerID -> state}` giving each activated miner's pre-wake state | `RECORD …prior_states[m] <- <state>` alongside the assignment record |

The captured `WakeEventRef` is not a reconstructed reference: `StartWake`'s structured success
result is `wake_seated(AssignmentID, WakeEventRef, wake_target_time, resulting_state = WAKING)`
(pseudocode lines 1124–1126), and step (6) of `StartWake` publishes that reference on the
assignment's wake registry — `SET wake_event_ref_of(target_assignment) <- wake_event_ref` —
explicitly "so a later rollback/cancel (V4/V8) can find it" (lines 1121–1122). The setup
procedures capture the *same* reference the scheduler actually seated (the comment at line 1497
reads "capture ACTUAL WakeEventRef"), so cancellation targets the real queued event rather than
a guess.

**`participant_setup_txn` (`PrepareParticipantsForNewRound`).** Initialised at pseudocode line
1482:

```
SET participant_setup_txn <- setup_transaction(wakes = empty, created_assignments = empty, prior_states = empty)   # V8
```

Every `CASE` of the activation `SWITCH` that creates a head records into it — `REGISTERED`
(lines 1494, 1497), `RESERVE` (lines 1511, 1514), and the two `LOW_POWER_LISTEN` sub-cases that
bind a fresh head (lines 1533/1536 and 1548/1551). A companion scalar
`participant_setup_error` (line 1483) latches the first failing `StartWake` result so the
post-loop code can distinguish a wake failure from a well-formed set.

**`refresh_setup_txn` (`TemplateRefresh`).** Assembled at pseudocode lines 4474–4477 *after*
the activation loop, from the same three constituents:

```
SET refresh_setup_txn <- setup_transaction(
      created_assignments = the PENDING AssignmentIDs created by THIS TemplateRefresh (stable order by MinerID, then CandidateID),
      wakes = the ACTUAL WakeEventRefs returned by their StartWake transactions,
      prior_states = each such miner's pre-refresh state)   # V8
```

Within the refresh loop each successful wake is captured as `refresh_wake(m, assignment_m,
wref)` and each failure as `refresh_wake_failed(m, assignment_m, wr)` (lines 4460–4461); these
feed the `refresh_setup_txn` assembled at 4474.

Both records therefore hold, per activated miner, the triple **(created head, its live wake
reference, its restorable prior state)** — precisely the state a rollback must reverse.

---

## 3. The two rollback procedures

`RollbackParticipantSetup` (pseudocode lines 1600–1626) and `RollbackTemplateRefreshSetup`
(lines 1628–1648) are the two *named, executable* rollbacks V8 introduces. They share an
identical four-step discipline, differing only in the `reason` string stamped on the closures
and in the identity of the setup being reversed.

| Step | `RollbackParticipantSetup` (1600–1626) | `RollbackTemplateRefreshSetup` (1628–1648) | Grounding invariant |
|---|---|---|---|
| **1. Cancel captured wakes first** | `FOR EACH wref in setup_txn.wakes (stable order): IF wref is still pending on EQ: CANCEL wref on EQ` (1607–1608) | identical (1633–1634) | gate 4 (V3): no live wake may survive to activate a head being closed |
| **2. Close each created head legally** | `FOR EACH aid in setup_txn.created_assignments (stable order): IF aid is a live head: CLOSE aid as CLOSED (status = CLOSED, custody_status = revoked, reason = participant_setup_rolled_back)` (1609–1611) | identical but `reason = template_refresh_rolled_back` (1635–1637) | J7 canonical terminal status; I18b (zero live heads after closure) |
| **3. Restore ledgers** | `RESTORE the coverage-state / custody ledgers for aid's range` (1612) | identical (1638) | I8a (coverage-state partition); I8b (custody/provenance) |
| **4. Assert no miner left WAKING** | `FOR EACH MinerID m in setup_txn.prior_states: IF miner_state(m) = WAKING AND m's bound head was rolled back: CALL ApplyMinerStateTransition(m, WAKING, setup_txn.prior_states[m], …, reason = participant_setup_rolled_back, …)` (1613–1618) | identical but `reason = template_refresh_rolled_back` (1639–1643) | gate 4 (V3); F6 central transition hook |

The ordering is deliberate and is documented in the effects comment at pseudocode lines
1605–1606: wakes are cancelled **first** "so none can activate a head being closed," *then* the
heads are closed and the ledgers restored, *then* any residual `WAKING` miner is transitioned
back to its captured prior state through the single sanctioned hook `ApplyMinerStateTransition`
(F6). Closure is *legal* in the J7 sense — every non-renewal end-of-life sets `status = CLOSED`
(never `SUPERSEDED`), and a CLOSED lineage has zero live heads under I18b (catalogue lines
407–412) — so the rollback never reopens or mutates an assignment in place.

**Checked postcondition (no silent partial rollback).** Each procedure ends with an explicit
residual check:

```
IF any setup_txn.created_assignments entry remains a live head OR any setup_txn.wakes entry remains pending on EQ
   OR any m in setup_txn.prior_states remains WAKING for a rolled-back head:
  RETURN rollback_failed(reason = residual_partial_setup)
RETURN rollback_completed
```
(participant: lines 1619–1622; refresh: lines 1644–1646). The return signature is therefore the
two-valued `rollback_completed | rollback_failed(reason)` (lines 1623, 1647): a `rollback_completed`
is a *certificate* that no created head is live, no captured wake is pending, and no miner is
`WAKING` for a rolled-back head; a residual it cannot clear is surfaced as `rollback_failed` for
the caller to escalate (see §6). This is the executable form of the V8 addendum's promise that the
rollbacks "verify no participant remains WAKING for a rolled-back head" (round-SM lines 623–627).

---

## 4. The explicit liveness path

After a *successful* rollback, each setup procedure takes one of two explicit continuations —
it never returns quietly with the round still in `ASSIGNMENT`.

**`SetupRetryEvent` (deterministic retry).** Defined at pseudocode lines 1650–1662. It is a
seated, dispatched handler whose inputs are `RoundContext, dispatch_envelope, RoundID,
setup_kind, reason` with `setup_kind in {PARTICIPANT_SETUP, TEMPLATE_REFRESH_SETUP}`. Two
properties make the retry safe:

- *Strictly-later event_time.* It is always seated at
  `next_representable_simulation_time(dispatch_envelope.event_time)` (participant: line 1583;
  refresh: line 4489), so the retry fires at a `target_event_time` strictly after the failing
  setup's own event_time — the retry cannot re-enqueue work at the already-draining event_time.
- *Stale-guard on RoundID.* On dispatch it first checks
  `IF RoundID != RoundID_current OR round_state NOT in {ASSIGNMENT, ROUND_INITIALISING,
  TEMPLATE_COMMITMENT}: RETURN setup_retry_stale_noop(RoundID)` (lines 1655–1656). A round that
  has advanced past the setup window therefore makes the retry an explicit no-op rather than a
  spurious re-activation.

If still current, it re-invokes the matching setup — `PrepareParticipantsForNewRound` for
`PARTICIPANT_SETUP` (line 1658) or `TemplateRefresh` for `TEMPLATE_REFRESH_SETUP` (line 1659) —
and returns *that* re-run's disposition ("its own liveness path governs"), so the retry is
idempotent with respect to the setup's own rollback/retry/abort logic.

**`RoundAbort` (declared termination).** When a retry is not warranted, or a retry seat itself
fails, the setup procedure returns a *declared* `RoundAbort` carrying a named reason (§6). This
is the terminal-abort branch, not a silent exit.

**Decision conditions.** Both procedures gate the retry identically (participant: line 1581;
refresh: line 4487):

```
IF a setup retry is warranted (bounded by the retry policy)
   AND next_representable_simulation_time(dispatch_envelope.event_time) <= run_horizon_T:
```

Thus a retry is seated only when (a) the retry policy permits it (bounding the number of
retries) and (b) the strictly-later retry time still lies within the run horizon `T`.
Otherwise, or if the `ScheduleEvent` seat does not return `scheduled(...)`, control falls to
`RoundAbort`.

**Microphase & seating-table rows.** `SetupRetryEvent` is registered in the §0.7g maps as an
ordinary queued driver event:

- *Event → microphase → priority map* (pseudocode line 516):
  `| SetupRetryEvent (V8: deterministic retry of a rolled-back participant / template-refresh
  setup at a strictly-later event_time; stale-guarded on RoundID) | ROUND_SETUP | 0 |`.
- *Driver-entry-point seating rules* (line 563):
  `| SetupRetryEvent | SetupRetryEvent | ROUND_SETUP | (RoundID, setup_kind) | event_time,
  delta_cycle, event_seq | no (V8: re-invokes PrepareParticipantsForNewRound / TemplateRefresh
  at a strictly-later event_time after a rolled-back setup; stale-guarded on RoundID) |`.

It thus shares the `ROUND_SETUP` microphase with `RoundInitialise` (line 553), carries the
stable tie key `(RoundID, setup_kind)`, requires the full `(event_time, delta_cycle,
event_seq)` envelope, and declares *no* right to create same-time delta-cycle events —
consistent with a fresh-event_time retry.

---

## 5. Caller-handles-disposition (no silent fall-through)

**`PrepareParticipantsForNewRound` failure handler** (pseudocode lines 1564–1588). The
post-loop logic is a total decision tree:

1. If a loop `StartWake` failed, `setup_reason <- participant_setup_error` (1565–1566);
   otherwise it branches on `CompleteAssignmentPhase`'s disposition, returning
   `participant_set_prepared` on `assignment_phase_completed` (1571) and setting `setup_reason
   <- disp.reason` on `assignment_phase_failed` (1572).
2. `SET rb <- CALL RollbackParticipantSetup(RoundContext, participant_setup_txn)` (1575). If
   `rb = rollback_failed(rr)`, it returns `RoundAbort(reason =
   participant_setup_rollback_failed, …)` (1576–1578).
3. Otherwise it attempts the retry seat (1581–1585); on a successful `scheduled(...)` seat it
   returns `participant_set_setup_retry_seated(setup_reason)` (1585).
4. Failing all of the above it returns `RoundAbort(reason =
   participant_setup_failed(setup_reason), …)` (1586–1587).

The declared return signature is `participant_set_prepared | participant_set_setup_retry_seated
| round_aborted` (line 1588) — every path lands on exactly one of these three, with no default
fall-through leaving `ASSIGNMENT` uncontrolled. The procedure NOTE at lines 1593–1598 states the
guarantee: a `StartWake` failure or `assignment_phase_failed` "is rolled back by the NAMED
`RollbackParticipantSetup` … and then takes an explicit liveness path (SetupRetryEvent or
RoundAbort) — the round is NEVER left in ASSIGNMENT with no controller."

**`TemplateRefresh` failure handler** (pseudocode lines 4478–4494). Structurally identical:

1. `SET disp <- CALL CompleteAssignmentPhase(...)`; `IF disp = assignment_phase_completed:
   RETURN new_TemplateID` (4479–4480).
2. `SET rb <- CALL RollbackTemplateRefreshSetup(RoundContext, refresh_setup_txn)` (4483); on
   `rollback_failed(rr)`, `RoundAbort(reason = template_refresh_rollback_failed, …)`
   (4484–4486).
3. Retry seat under the same policy/horizon gate (4487–4491), returning
   `template_refresh_retry_seated(disp.reason)` on a successful seat.
4. Otherwise `RoundAbort(reason = template_refresh_failed(disp.reason), …)` (4492–4493).

Return signature `new_TemplateID | template_refresh_retry_seated | round_aborted` (line 4494).

**Upstream callers.** `TemplateRefresh` is invoked by `FullRangeExhaustNoSolution` at pseudocode
line 4358 as `RETURN CALL TemplateRefresh(…)`, so the refresh's three-valued disposition is
returned through the exhaustion handler unchanged (its own `RETURNS: disposition (refresh |
abort)`, line 4361). Both setup procedures are themselves seated SIM-DRIVER entry points
(`PrepareParticipants` at `ASSIGNMENT_SETUP`, seating-table line 555; `TemplateRefresh` reached
from the exhaustion path), so their explicit dispositions are consumed by the dispatcher rather
than discarded. Their one in-specification re-invoker, `SetupRetryEvent`, likewise `RETURN`s the
re-run disposition directly (lines 1658–1659). No caller of either procedure silently ignores a
failure disposition.

---

## 6. Liveness and no-orphan argument

Let a setup invocation fail after creating a non-empty `setup_txn`. The following hold.

**(a) No live wake event survives.** Step 1 of the rollback cancels every captured `wref` that
is still pending on `EQ` (lines 1607–1608 / 1633–1634). This composes with the V3 gate-4
discipline already inside `StartWake`: a `StartWake` that fails *before* its transition leaves
the miner untouched with nothing seated (lines 1106–1108), and one that fails *after* the seat
cancels its own `WakeCompleteEvent` (lines 1116–1120). Hence every wake that reached
`setup_txn.wakes` is a genuinely seated event, and the rollback cancels exactly those.

**(b) No half-created head remains open.** Step 2 closes every `created_assignments` entry that
is still a live head as `CLOSED / revoked` (J7/I18b), and step 3 restores its coverage/custody
ledgers (I8a/I8b). By I18b a CLOSED lineage has zero live heads.

**(c) No miner remains WAKING for a rolled-back head.** Step 4 transitions any such miner from
`WAKING` back to its captured `prior_states[m]` through `ApplyMinerStateTransition` (F6). This
is the executable analogue of gate 4's guarantee that "no failure leaves `miner_state = WAKING`
with no live WakeCompleteEvent" (pseudocode lines 1089, 1130).

**(d) The postcondition is checked, not assumed.** The residual guard (lines 1619–1621 /
1644–1645) re-verifies (a)–(c) and downgrades to `rollback_failed(residual_partial_setup)` if
any orphan persists, so a returned `rollback_completed` is a verifiable no-orphan certificate.

**(e) The round deterministically retries or aborts.** On `rollback_completed` the caller either
seats a `SetupRetryEvent` at a strictly-later, horizon-bounded, retry-policy-bounded event_time
(then returns `…_retry_seated`), or returns a declared `RoundAbort` with a named reason. On
`rollback_failed` it returns `RoundAbort(participant_setup_rollback_failed /
template_refresh_rollback_failed)`. In every branch the round leaves `ASSIGNMENT` under an
explicit disposition. Progress is guaranteed because retries are bounded by the retry policy and
by `run_horizon_T`, and because a superseded/advanced round makes a pending retry a
`setup_retry_stale_noop`; the round therefore cannot silently stall, nor retry unboundedly, nor
retry a round that has moved on.

Together (a)–(e) discharge exactly the two negative-test hazards recorded for `R157`: a setup
returning while `round_state = ASSIGNMENT` with no controller, and a participant left `WAKING`
for a rolled-back head.

---

## 7. Traceability to invariants, terminology, and the round state machine

**Traceability matrix.** Row `R157` of `STAGE_01_TRACEABILITY_MATRIX.csv` records V8 verbatim,
naming the artifacts `RollbackParticipantSetup; RollbackTemplateRefreshSetup; SetupRetryEvent;
PrepareParticipantsForNewRound; TemplateRefresh`, the related invariants `I16; I17; I18b`, and
the negative test quoted in §1/§6. Status `SPECIFIED`.

**Invariant catalogue.** `STAGE_01_INVARIANT_CATALOGUE.md` contains no dedicated "V8" row; V8 is
grounded on pre-existing invariants that the rollback discipline enforces:

- **I18b — unique live head** (catalogue lines 384–399): a CLOSED lineage has zero live heads,
  the property step 2 of each rollback establishes.
- **J7 canonical terminal status** (lines 407–412): every non-renewal end-of-life (including
  "wake failure, cancellation") sets `status = CLOSED` with `custody_status = revoked` — the
  exact closure the rollbacks perform.
- **I8a / I8b — coverage and custody ledgers** (lines 150–199): restored in step 3.
- **I16 / I17** (lines 284–347) are the census-integrity invariants the matrix binds to `R157`,
  reflecting that closing heads and un-`WAKING` miners must leave the security census coherent.

The audit notes this honestly: the catalogue supports V8 through these standing invariants
rather than a bespoke V8 entry.

**Terminology.** `STAGE_01_TERMINOLOGY.md` (lines 817–821) defines the V8 triple
`RollbackParticipantSetup / RollbackTemplateRefreshSetup / SetupRetryEvent` as "the named
executable rollbacks (cancel captured `WakeEventRef`s, close created heads legally, restore
ledgers, verify no participant stays WAKING) and the deterministic strictly-later retry event,"
matching the pseudocode.

**Round state machine.** `STAGE_01_ROUND_STATE_MACHINE.md` carries the V8 addendum under the
§3.10 Stage-1V corrections block (lines 623–627): the two rollbacks "cancel the captured
`WakeEventRef`s, close every created head legally, restore the ledgers, and verify no
participant remains WAKING for a rolled-back head," and the setup procedures "on
`assignment_phase_failed`, roll back and take an explicit liveness path (a strictly-later
`SetupRetryEvent` or a declared `RoundAbort`) — never leaving `round_state = ASSIGNMENT` with no
controller." The addendum is consistent with the pseudocode audited here.

---

## 8. Findings and residual observations

1. **All four named artifacts are present and mutually consistent.** `RollbackParticipantSetup`
   (1600), `RollbackTemplateRefreshSetup` (1628), `SetupRetryEvent` (1650), and the two capturing
   setup procedures (`PrepareParticipantsForNewRound` 1469, `TemplateRefresh` 4425) agree on the
   `setup_transaction` shape, the rollback discipline, and the liveness path across the
   pseudocode, round-SM, terminology, and traceability artifacts.

2. **The `setup_transaction` capture is exhaustive over the activation cases.** Every `CASE` in
   `PrepareParticipantsForNewRound` that creates a head records into `participant_setup_txn`; the
   non-creating dispositions (`parked_no_range_offered`, `deferred_no_assignment`, the `DEFAULT`
   `CONTINUE`) create nothing to roll back, consistent with the K1 "explicit disposition"
   requirement (lines 1554, 1560, 1562–1563).

3. **The rollbacks are order-safe.** Cancelling wakes before closing heads (documented at lines
   1605–1606) prevents a captured `WakeCompleteEvent` from activating a head mid-closure.

4. **No standalone `STAGE_01V_*` artifacts exist yet in this directory.** The terminology
   addendum (line 824) refers forward to `STAGE_01V_SUPERSESSION_REGISTER.md`, but no
   `STAGE_01V_*` file is currently present (the lettered series ends at `STAGE_01U_*`). This is a
   cross-reference to a not-yet-materialised register, not a defect in V8's specification, and is
   reported here for completeness rather than as a V8 inconsistency.

No contradictions between the pseudocode and its companion artifacts were found for V8.
