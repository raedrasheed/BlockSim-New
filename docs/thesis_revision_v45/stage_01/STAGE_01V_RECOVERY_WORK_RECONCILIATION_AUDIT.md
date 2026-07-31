# Stage 1V — Recovery-Work Reconciliation Audit (V1)

**Scope.** This audit documents correction **V1** of the Stage-1V thesis revision: the
introduction of the procedure `ReconcilePendingRecoveryWork` and the *reconcile-before-seat*
discipline it imposes on the security-floor recovery-work timeline. The correction closes a
liveness hole in which an already-`DUE` in-flight recovery-work record could be orphaned when the
final recovery census advanced its version during the same `SECURITY_RECOVERY` episode, leaving a
non-consumable `DUE` record that violates the `ProcessEventTime` finalisation assertion. All
findings below are grounded in the current contents of
`STAGE_01_PROTOCOL_PSEUDOCODE.md`, cross-checked against
`STAGE_01_ROUND_STATE_MACHINE.md` (§3.10 Stage-1V addendum), `STAGE_01_INVARIANT_CATALOGUE.md`
(I16 addendum), and `STAGE_01_TERMINOLOGY.md` (Stage-1V addendum). This is a descriptive audit;
no pseudocode or specification file is modified by it. Line numbers cite the state of the
pseudocode file at the time of the audit and are provided for traceability, not as normative
anchors.

---

## 1. The defect in the pre-V1 specification

### 1.1 The invariant that must hold at event-time finalisation

`ProcessEventTime` closes an `event_time` `t` only after its epilogue chain has run to quiescence,
and it guards closure with an explicit finalisation assertion over recovery-work due facts
(`STAGE_01_PROTOCOL_PSEUDOCODE.md`, in `ProcessEventTime`, line 276):

```
ASSERT no recovery_work[*].due_status = DUE with due_at_event_time = t
        # U1/U4: every DUE recovery-work fact at t was explicitly consumed by ApplyRecoveryWorkAfterEpilogue
```

The assertion is total over `recovery_work[*]` — *every* work record in the store, not only the
one currently referenced by `pending_recovery_work[episode]`. It therefore demands that no
recovery-work record anywhere retains `due_status = DUE` bound to the timestamp being finalised.

### 1.2 Why the post-epilogue consumer cannot discharge a stranded record

The only procedure that legitimately consumes a `DUE` recovery-work fact is
`ApplyRecoveryWorkAfterEpilogue` (line 2802). That hook is *singular in its reach*: it reads
`work_id <- pending_recovery_work[episode]` and operates on exactly that one record
(lines 2810–2812):

```
IF pending_recovery_work[episode] = null: RETURN nothing_due
SET work_id <- pending_recovery_work[episode] ; SET W <- recovery_work[work_id]
IF W.due_status != DUE OR W.due_at_event_time != t: RETURN nothing_applicable_due(t)
```

Consequently, a `DUE` record that is *no longer* the one named by `pending_recovery_work[episode]`
is unreachable by the consumer. Its `due_status` stays `DUE`, and the line-276 assertion fires.

### 1.3 The orphaning sequence

Under the pre-V1 specification, seating of recovery work was the sole in-recovery work operation
in the epilogue, and it replaced a stale prior in-flight record before publishing a new one.
Because the final recovery census is re-versioned on *every* pass through the `SECURITY_RECOVERY`
branch (`CommitRecoveryCensus`, Q1, line 2354), the following invalid due-time sequence was
reachable:

1. At an earlier `event_time`, `SeatRecoveryWork` armed work `W1` bound to census version `v1`;
   its `RecoveryWorkDueEvent` later fired at `t`, so `RecoveryWorkDueEvent` set
   `recovery_work[W1].status = DUE`, `due_status = DUE`, and `due_at_event_time = t`
   (lines 2788–2790).
2. At the *same* `event_time` `t`, a further final census was committed, advancing the version to
   `v2` (e.g. a same-timestamp `MINER_STATE_TRANSITION` census overwrite followed by a fresh
   `CommitRecoveryCensus`).
3. The epilogue, still classifying a breach-before-deadline and finding work warranted, called
   `SeatRecoveryWork`, which — lacking any prohibition against replacing a `DUE`-at-`t` record —
   superseded `W1`'s *reference* and published a second record `W2` bound to `v2`, setting
   `pending_recovery_work[episode] <- W2`.
4. `W1` remained in the store with `due_status = DUE` and `due_at_event_time = t`, but was no
   longer named by `pending_recovery_work[episode]`. `ApplyRecoveryWorkAfterEpilogue` therefore
   consumed only `W2`, leaving `W1` stranded.
5. The finalisation assertion at line 276 failed on `W1`.

This is a **liveness hole**: an in-flight `DUE` unit of recovery work that was already scheduled,
already fired, and already warranted became non-consumable purely because the census version
advanced beneath it. The correction records the defect narrative in-line in the
`ReconcilePendingRecoveryWork` NOTE (lines 2549–2553):

> V1: closes the invalid due-time sequence where a DUE work W1 (bound to v1) is orphaned by a
> newer census v2 and replaced by a second work W2, leaving W1 DUE and failing the
> ProcessEventTime finalisation assertion.

---

## 2. The corrected mechanism: reconcile before seat

Correction V1 introduces a dedicated reconciliation procedure that runs on every
`SECURITY_RECOVERY` epilogue pass and adjudicates the *already-in-flight* work record against the
newest final census **before** any fresh work is seated. Its signature and preconditions
(`STAGE_01_PROTOCOL_PSEUDOCODE.md`, lines 2515–2518) are:

```
PROCEDURE ReconcilePendingRecoveryWork      # V1: reconcile in-flight recovery WORK against the newest final census BEFORE seating new work
  INPUTS: RoundContext, episode, latest_census_version, event_time   # latest_census_version = census.RecoveryCensusVersion just published
  PRECONDITIONS: called by SecurityFloorEvaluate AFTER CommitRecoveryCensus + ReconcilePendingRecoveryDecisions and
                 BEFORE it considers SeatRecoveryWork; round_state = SECURITY_RECOVERY; episode = current_recovery_episode
```

The procedure first resolves the single in-flight record and the warrant predicate
(lines 2520–2524):

```
IF pending_recovery_work[episode] = null: RETURN no_pending_recovery_work(episode)
SET W <- recovery_work[pending_recovery_work[episode]]
SET census <- latest_recovery_census[episode]
SET still_warranted <- (census.breach = true AND census.deadline_reached = false
                        AND CALL ClassifyRecoveryWork(RoundContext, episode, census) != NONE)   # V6
```

`still_warranted` couples the census verdict to the work classifier: work remains warranted only
while the newest final census shows a breach *before* the deadline **and** `ClassifyRecoveryWork`
still selects a census-changing action other than `NONE` (`ClassifyRecoveryWork`, lines 2683–2704;
this is the V6 restriction to actions that can change the `ACTIVE_HASHING` census). The reconciler
then applies exactly one of three dispositions.

### 2.1 Disposition (1) — rebind a still-warranted `DUE` record (same identity)

When the in-flight record is `DUE` at the current `event_time` and remains warranted, it is
**rebound** to the latest census version *in place*, keeping the same `RecoveryWorkID`, with no
replacement seated (lines 2525–2530):

```
IF W.due_status = DUE AND W.due_at_event_time = event_time:
  IF still_warranted:
    SET recovery_work[W.work_id].bound_census_version <- latest_census_version   # V1: rebind (same WorkID) so the DUE record is consumable
    RETURN recovery_work_reconciled_rebound(W.work_id, latest_census_version)
```

Rebinding updates `bound_census_version` only; `status`, `due_status`, `due_at_event_time`,
`work_id`, and `due_dispatch_envelope` are untouched. The record therefore remains the one named
by `pending_recovery_work[episode]` and is consumed later in the same epilogue chain by
`ApplyRecoveryWorkAfterEpilogue`, whose freshness gate now passes because
`W.bound_census_version = census.RecoveryCensusVersion` holds (line 2818).

### 2.2 Disposition (2) — supersede a no-longer-warranted record

When the record is no longer warranted (whether currently `DUE` at `event_time` or `ARMED` for the
future), it is atomically superseded, its queued event cancelled if still pending, and the
controller cleared (lines 2531–2535 for the `DUE` case; lines 2542–2545 for the `ARMED` case):

```
SET recovery_work[W.work_id].status <- SUPERSEDED ; SET recovery_work[W.work_id].due_status <- SUPERSEDED   # V1/V7
IF W.work_due_event_ref != null AND W.work_due_event_ref is still pending on EQ: CANCEL W.work_due_event_ref on EQ
SET pending_recovery_work[episode] <- null
RETURN recovery_work_reconciled_superseded(W.work_id)
```

Because both `status` and `due_status` move to the terminal `SUPERSEDED`, the record can no longer
match the line-276 assertion, and clearing `pending_recovery_work[episode]` leaves the epilogue
free to classify and seat fresh work if the census still warrants it.

### 2.3 Disposition (3) — re-affirm or supersede an `ARMED` future record

When the record is `ARMED` for a *future* event (not due at the current `event_time`), it is
re-affirmed to the latest version under the same identity if still warranted, or else superseded
and cancelled (lines 2536–2545):

```
IF W.status = ARMED:
  IF still_warranted:
    SET recovery_work[W.work_id].bound_census_version <- latest_census_version   # V1: re-affirm the same ARMED identity
    RETURN recovery_work_reconciled_reaffirmed(W.work_id, latest_census_version)
  SET recovery_work[W.work_id].status <- SUPERSEDED ; SET recovery_work[W.work_id].due_status <- SUPERSEDED   # V1/V7
  IF W.work_due_event_ref != null AND W.work_due_event_ref is still pending on EQ: CANCEL W.work_due_event_ref on EQ
  SET pending_recovery_work[episode] <- null
  RETURN recovery_work_reconciled_superseded(W.work_id)
RETURN recovery_work_reconciled_noop(W.work_id)
```

Either arm yields exactly one live disposition for the episode: re-affirmation keeps the single
`ARMED` record live (identity preserved, future event untouched), and supersession terminates it
and cancels its queued `RecoveryWorkDueEvent`. As the in-line comment states, the policy is to
"NEVER leave two live in-flight" work records (line 2537). Any record in a state other than
`DUE`-at-`event_time` or `ARMED` (e.g. `APPLYING`) is a no-op — `recovery_work_reconciled_noop`
(line 2546).

### 2.4 Disposition table

Columns: pre-state of the in-flight record `W`; census verdict via `still_warranted`; action taken;
resulting `RecoveryWorkID` identity; disposition of the queued `RecoveryWorkDueEvent`
(`work_due_event_ref`); structured return.

| Pre-state of `W` | Census verdict (`still_warranted`) | Action | Resulting `RecoveryWorkID` identity | Queued-event disposition | Return |
|---|---|---|---|---|---|
| `pending_recovery_work[episode] = null` | — (no record) | none | — | — | `no_pending_recovery_work(episode)` |
| `DUE` at `event_time` | warranted | rebind `bound_census_version ← latest`; leave `status`/`due_status`/`due_at_event_time` | **same** `W.work_id` (no replacement) | event already fired (set `DUE`); left for `ApplyRecoveryWorkAfterEpilogue` to consume | `recovery_work_reconciled_rebound(W.work_id, latest_census_version)` |
| `DUE` at `event_time` | not warranted | `status`/`due_status ← SUPERSEDED`; clear `pending_recovery_work` | **terminated** (`SUPERSEDED`) | `CANCEL work_due_event_ref` if still pending on EQ | `recovery_work_reconciled_superseded(W.work_id)` |
| `ARMED` (future event) | warranted | re-affirm `bound_census_version ← latest` | **same** `W.work_id` (identity re-affirmed) | left live (future `RecoveryWorkDueEvent` untouched) | `recovery_work_reconciled_reaffirmed(W.work_id, latest_census_version)` |
| `ARMED` (future event) | not warranted | `status`/`due_status ← SUPERSEDED`; clear `pending_recovery_work` | **terminated** (`SUPERSEDED`) | `CANCEL work_due_event_ref` if still pending on EQ | `recovery_work_reconciled_superseded(W.work_id)` |
| other (e.g. `APPLYING`) | — | none | unchanged | unchanged | `recovery_work_reconciled_noop(W.work_id)` |

The complete `RETURNS` set of the procedure is (lines 2547–2548):
`recovery_work_reconciled_rebound | recovery_work_reconciled_reaffirmed |
recovery_work_reconciled_superseded | recovery_work_reconciled_noop | no_pending_recovery_work`.

---

## 3. Call-site integration in `SecurityFloorEvaluate`

The reconciler is wired into the `SECURITY_RECOVERY` branch of `SecurityFloorEvaluate`
(`STAGE_01_PROTOCOL_PSEUDOCODE.md`, procedure at line 2276; branch beginning at line 2347). The
ordering is explicit and total (lines 2352–2375, abridged to the ordered calls):

```
SET episode <- current_recovery_episode
IF breach: RECORD_ONCE breach_persists(t)                             # I16 persistence; no self-transition
CALL CommitRecoveryCensus(RoundContext, episode, t, breach)          # (a) Q1: version + publish latest_recovery_census
CALL ReconcilePendingRecoveryDecisions(RoundContext, episode)        # (b) Q1/Q3: supersede/cancel or re-affirm decisions
SET census <- latest_recovery_census[episode]
CALL ReconcilePendingRecoveryWork(RoundContext, episode, census.RecoveryCensusVersion, t)   # (c) V1
...
SET work_action <- CALL ClassifyRecoveryWork(RoundContext, episode, census)   # only after (a)-(c)
IF work_action != NONE:
  RETURN CALL SeatRecoveryWork(RoundContext, episode, work_action, t, census.RecoveryCensusVersion)   # (d) U1/U3/V1
```

The mandated order is therefore **(a) census commit → (b) decision reconcile → (c) work reconcile
→ (d) seat**. The order is load-bearing for three reasons:

1. **Census before either reconcile.** Both reconcilers judge freshness against the *newest* final
   census version. `ReconcilePendingRecoveryWork` reads `latest_recovery_census[episode]` and is
   passed `census.RecoveryCensusVersion` as `latest_census_version`; unless `CommitRecoveryCensus`
   has already published the version for `t`, the reconciler would rebind or re-affirm against a
   stale version. Placing (a) first makes the version passed to (c) the authoritative one for `t`.

2. **Work reconcile before seat.** This is the crux of V1. Seating must never observe an
   in-flight `DUE`-at-`t` record that the current census has already re-versioned; the reconciler
   must first either rebind that record to the new version (preserving identity) or terminate it.
   By the time `SeatRecoveryWork` is reached, `pending_recovery_work[episode]` is guaranteed to
   hold either a rebound/re-affirmed live record or `null`, so seating can no longer strand a
   `DUE` record. The in-line rationale is at lines 2357–2360.

3. **Decision reconcile alongside work reconcile.** `ReconcilePendingRecoveryDecisions` (b) and
   `ReconcilePendingRecoveryWork` (c) address disjoint stores — pending *decisions*
   (`RESTORED`/`UNRECOVERABLE` completions) versus pending *work* (reserve activation /
   participation replacement). Running (b) before (c) keeps the decision store consistent with the
   same census the work reconciler then reads, so a warranted-outcome decision and an in-flight
   work record are adjudicated against one coherent census snapshot for `t`.

The `SecurityFloorEvaluate` NOTE (lines 2386–2396) and the round-state-machine §3.10 V1 block
(`STAGE_01_ROUND_STATE_MACHINE.md`, lines 578–584) both restate this ordering as normative.

---

## 4. The `SeatRecoveryWork` non-replacement rule and the partition of responsibility

Correction V1 also hardens `SeatRecoveryWork` (procedure at line 2706) with a guard that forbids
it from replacing a `DUE` record at the current `event_time`. Under its "at most one in-flight
recovery-work action per episode" pre-check (lines 2714–2720):

```
IF pending_recovery_work[episode] != null:
  SET W0 <- recovery_work[pending_recovery_work[episode]]
  # V1: NEVER replace a DUE work record at the CURRENT event_time. If W0 is DUE at t, ReconcilePendingRecoveryWork
  #   already rebound it (if warranted) or superseded it — SeatRecoveryWork must not seat a second record over it.
  IF W0.status = DUE AND W0.due_at_event_time = t:
    RETURN recovery_work_already_pending(W0.action)   # V1: do not replace a DUE record at the current event_time
```

This guard is the direct counterpart of the reconciler's disposition (1). It ensures that the two
procedures **partition** responsibility over the in-flight record cleanly:

- **`ReconcilePendingRecoveryWork` owns the already-in-flight record.** Any record that is `DUE` at
  the current `event_time`, or `ARMED` from an earlier pass, is adjudicated *only* by the
  reconciler — rebind, re-affirm, or supersede. Seating never touches such a record at `t`.

- **`SeatRecoveryWork` owns brand-new work.** Seating mints a fresh `RecoveryWorkID`
  (`candidate_seq <- recovery_work_seq + 1`, line 2732) and publishes an `ARMED` record with a
  future `RecoveryWorkDueEvent` *only* when there is no live in-flight record to defer to. Its
  remaining branches (lines 2721–2728) still handle a *stale* prior record that is neither
  `DUE`-at-`t` nor current — atomically superseding and cancelling it before publishing the
  replacement (the V7 "never two live in-flight" rule) — but the `DUE`-at-`t` case is explicitly
  excluded from that replacement path by the guard above.

The result is that at the current `event_time` there is exactly one authority for the in-flight
record (the reconciler) and exactly one authority for fresh work (the seater), and the two never
act on the same record at `t`. The `SecurityFloorEvaluate` comment restates this partition at
lines 2370–2372: "SeatRecoveryWork does NOT replace a DUE work record at THIS event_time (Reconcile
already rebound it); it only seats FRESH work when there is no live in-flight work."

---

## 5. Liveness argument

**Claim.** After correction V1, every `RecoveryWorkID` carries exactly one live-or-terminal
disposition, and no orphaned `DUE` record survives a census-version advance within an episode.

**Argument.**

1. *At most one live in-flight record per episode.* The store admits a single controller
   `pending_recovery_work[episode]`. The reconciler either preserves that single record (rebind /
   re-affirm, same `work_id`) or terminates it and clears the controller (supersede). The seater
   publishes a new record only when the controller is `null` or holds a stale non-`DUE`-at-`t`
   record it first supersedes and cancels (lines 2723–2728). Neither procedure ever leaves two
   records simultaneously in `{ARMED, DUE, APPLYING}` for one episode — the V7 property recorded in
   `STAGE_01_INVARIANT_CATALOGUE.md` (I16 addendum, lines 319–321): "each `RecoveryWorkID` has
   exactly one live or terminal disposition and at most one per episode is `{ARMED, DUE,
   APPLYING}`".

2. *No stranded `DUE` record at finalisation.* Consider any record `W` with
   `due_status = DUE` and `due_at_event_time = t` at the point `SecurityFloorEvaluate` runs its
   `SECURITY_RECOVERY` branch for `t`. Because a `DUE`-at-`t` fact is set only by the fired
   `RecoveryWorkDueEvent` on the record named by `pending_recovery_work[episode]`
   (`RecoveryWorkDueEvent` gate, lines 2778–2790), `W` is exactly that named record when the
   reconciler runs. The reconciler's disposition (1)/(2) then applies:
   - if warranted, `W` is rebound (same identity) and its `bound_census_version` equals the current
     census version, so `ApplyRecoveryWorkAfterEpilogue`'s freshness gate passes and it consumes
     `W` (`due_status → CONSUMED`, lines 2860–2862) — or, if a later same-`t` census made it
     unfresh, that hook consumes it as `SUPERSEDED` (lines 2820–2823);
   - if not warranted, `W` is superseded in place (`due_status → SUPERSEDED`) and the controller is
     cleared.
   In every arm, `W`'s `due_status` leaves `DUE` before finalisation. Seating cannot re-create the
   orphan: the `DUE`-at-`t` guard (lines 2719–2720) prevents it from publishing a second record
   over `W`. Hence no record satisfies the line-276 assertion predicate
   `due_status = DUE with due_at_event_time = t` at closure, and the assertion holds.

3. *Terminal closure leaves no orphan either.* Independently of the epilogue path, terminal
   round closure runs `CancelActiveRecoveryEpisode` (line 2427), which iterates **every**
   nonterminal work record of the episode — not merely the one named by `pending_recovery_work` —
   moving each to `CANCELLED` and explicitly consuming any `DUE` fact (lines 2445–2454). This is
   the V7 backstop guaranteeing that "no orphan `ARMED/DUE/APPLYING` work record survives terminal
   closure".

Together, (1)–(3) establish the single-disposition and no-orphan properties: a census-version
advance during an episode now *rebinds* the still-warranted `DUE` record rather than stranding it,
and the finalisation assertion is discharged on every path.

---

## 6. Traceability

### 6.1 Pseudocode procedures (`STAGE_01_PROTOCOL_PSEUDOCODE.md`)

| Procedure | Location (current) | Role in V1 |
|---|---|---|
| `ReconcilePendingRecoveryWork` | line 2515 | New procedure; the three-disposition reconciler (rebind / supersede / re-affirm) |
| `SecurityFloorEvaluate` | line 2276; `SECURITY_RECOVERY` branch from line 2347; V1 call at line 2361 | Call site enforcing census → decisions → work-reconcile → seat ordering |
| `SeatRecoveryWork` | line 2706; V1 guard at lines 2717–2720 | Non-replacement of a `DUE`-at-`event_time` record |
| `ClassifyRecoveryWork` | line 2683 | Supplies the `!= NONE` term of `still_warranted` (V6 census-changing actions only) |
| `ApplyRecoveryWorkAfterEpilogue` | line 2802 | Post-epilogue consumer of the (rebound) `DUE` record |
| `CommitRecoveryCensus` | line 2467 | Publishes the versioned final census the reconciler judges against |
| `ReconcilePendingRecoveryDecisions` | called at line 2355 | Runs immediately before the work reconciler in the epilogue order |
| `CancelActiveRecoveryEpisode` | line 2427 | V7 terminal backstop; cancels every nonterminal work record |
| `ProcessEventTime` | finalisation assertion at line 276 | The assertion the orphaned `DUE` record previously violated |

### 6.2 Structured return tokens introduced/used by the reconciler

`recovery_work_reconciled_rebound`, `recovery_work_reconciled_reaffirmed`,
`recovery_work_reconciled_superseded`, `recovery_work_reconciled_noop`,
`no_pending_recovery_work` (lines 2547–2548). The seater's `DUE`-at-`t` return is
`recovery_work_already_pending(W0.action)` (line 2720).

### 6.3 Cross-document entries this correction touches

- **`STAGE_01_ROUND_STATE_MACHINE.md` — §3.10 Stage-1V addendum, V1 block (lines 578–584).**
  States the epilogue ordering (`CommitRecoveryCensus`, `ReconcilePendingRecoveryDecisions`,
  `ReconcilePendingRecoveryWork` — "in that order — BEFORE it considers `SeatRecoveryWork`"), the
  rebind-same-`RecoveryWorkID` rule for a `v1 → v2` move, the supersede/re-affirm arms, and the
  `SeatRecoveryWork` non-replacement rule; explicitly attributes the fix to removing "the invalid
  due-time sequence where an orphaned DUE record fails the `ProcessEventTime` finalisation
  assertion".
- **`STAGE_01_TERMINOLOGY.md` — Stage-1V terminology addendum (lines 788–795).** Defines
  `ReconcilePendingRecoveryWork` (V1) with its ordering, the rebind/supersede/re-affirm
  dispositions, and the `SeatRecoveryWork` "never replaces a DUE record at the current
  `event_time`" clause. The related lifecycle vocabulary appears in the V7 entry
  (`RECOVERY_WORK_STATUS` = {CREATED, ARMED, DUE, APPLYING, CONSUMED, SUPERSEDED, SCHEDULE_FAILED,
  HORIZON_DEFERRED, CANCELLED}; one disposition per `RecoveryWorkID`) at lines 814–816.
- **`STAGE_01_INVARIANT_CATALOGUE.md` — I16 addendum, V7 clause (lines 319–321).** Records the
  single-live-or-terminal-disposition property per `RecoveryWorkID` and that terminal closure
  cancels every nonterminal work record — the invariant basis for the §5 liveness argument. (No
  distinct V1-numbered invariant is introduced; V1 is enforced procedurally at the
  `SecurityFloorEvaluate` call site and asserted at the `ProcessEventTime` finalisation gate, and
  is catalogued under the V7 recovery-work disposition invariant.)

### 6.4 Audit note on grounding

Every construct cited above was verified against the current file contents. The task brief
described the signature as
`ReconcilePendingRecoveryWork(RoundContext, RecoveryEpisodeID, latest RecoveryCensusVersion,
event_time)`; the pseudocode's actual `INPUTS` line names these parameters
`RoundContext, episode, latest_census_version, event_time` (line 2516), where `episode` is the
`RecoveryEpisodeID` and `latest_census_version` is passed the value `census.RecoveryCensusVersion`
at the call site (line 2361). This is a naming difference only; the semantics match the brief. No
expected V1 construct was found missing.
