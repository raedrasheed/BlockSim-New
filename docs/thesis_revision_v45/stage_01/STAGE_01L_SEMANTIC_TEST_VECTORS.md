# Stage 1L — Semantic Test Vectors (TV91–TV97)

Seven blocking test vectors for the Stage-1L final contract reconciliation. Each names the exact
procedure(s) in `STAGE_01_PROTOCOL_PSEUDOCODE.md` and its exact preconditions; none assumes an unmodeled
external action. These extend TV1–TV90 (historical, in `STAGE_01C..K_*`, which are NOT modified in Stage
1L). No property (energy, security, fairness, incentive) is claimed. The A1 baseline (`8.420833333 kWh`)
is unchanged. Name remains **PoCol**; mechanism is **the idle policy within PoCol**.

---

## TV91 — every miner transition carries the dispatch envelope; no ambient or hand-stamped seq (L1)

**Preconditions.** In round `r`'s `ASSIGNMENT` phase, `PrepareParticipantsForNewRound` is dispatched by
`ProcessEventTime` at `event_time = t`. Two miners are eligible: a `REGISTERED` miner `m1` and a parked
`LOW_POWER_LISTEN` miner `m2` whose `entry_stop_reason = RANGE_EXHAUSTED` and for which the new-round
policy offers a range.

**Trace.** `ProcessEventTime` materialises the ONE `dispatch_envelope = (t, dc, seq)` from the dispatched
event's own enqueued envelope and sets `EQ.current_event_seq = seq`. `PrepareParticipantsForNewRound`
receives that `dispatch_envelope` (it did NOT stamp `next EQ.event_creation_seq`). For `m1` it calls
`StartWake(…, from_state = REGISTERED, dispatch_envelope = dispatch_envelope)`; StartWake's WAKING
`ApplyMinerStateTransition` binds `event_time = dispatch_envelope.event_time`, `delta_cycle =
dispatch_envelope.delta_cycle`, `event_seq = dispatch_envelope.event_seq`. For `m2` the `T10` StartWake
threads the same `dispatch_envelope`. The two WAKING `TransitionEventID`s differ (distinct MinerID /
old_state) even though they share `seq`.

**Expected.** No `ApplyMinerStateTransition` executes with a missing or ambient `event_seq`; both
transitions bind all three envelope fields from the single dispatch envelope; the removed `driver_envelope
= env` form does not appear. Reqs: **L1**, §0.7/§0.7e/§0.7f/§0.9; K4/J4.

## TV92 — TemplateRefresh reaches HASHING only through the single CompleteAssignmentPhase owner (L2)

**Preconditions.** Round `r` is in `ROUND_EXHAUSTED`; `FullRangeExhaustNoSolution` (dispatched, carrying
its `dispatch_envelope`) calls `TemplateRefresh` under `policy = continue_mining`. Eligible miners are
re-bound to the new template.

**Trace.** `TemplateRefresh` closes old-template assignments, commits the new `TemplateID`
(`TemplateCommit` → `ASSIGNMENT`), binds a fresh `ORIGINAL` `PENDING` for each eligible miner and
`StartWake`s each (threading `dispatch_envelope`). It then executes `ASSERT round_state = ASSIGNMENT`
followed by `CALL CompleteAssignmentPhase(RoundContext)` — NOT an in-line `TRANSITION round_state ->
HASHING`. `CompleteAssignmentPhase` asserts the intended set is well-formed, performs `TRANSITION
round_state -> HASHING` (R4), and captures the K7 applicability-entry census. Any `HashWorkEvent`
dispatched while `round_state = ASSIGNMENT` is a no-op.

**Expected.** The round reaches `HASHING` through the SOLE `CompleteAssignmentPhase` owner; the census is
captured on entry; no second in-line `ASSIGNMENT → HASHING` path exists. Reqs: **L2**, §2b/§19; K2/K7.

## TV93 — a solution discovered exactly at a lease boundary stays valid (discovery before lease expiry) (L3)

**Preconditions.** At `event_time = t`, miner `H` holds a `CURRENT` assignment `X` whose `lease_expiry =
t`. At the SAME `event_time t`, `H`'s pending `HashWorkEvent` unit yields a solution hit for `X`, and a
`LeaseExpiry(X, t)` event is also due.

**Trace.** By the canonical order (§0.7 microphase list; §21 priority items: solution discovery = 7,
lease expiry = 10; `STAGE_01G_EVENT_MICROPHASE_SPEC.md §4`), solution discovery is processed FIRST:
`ScheduleSolutionPropagation` takes the immutable `SolutionEligibilitySnapshot` (E1) against the
still-`CURRENT` `X`, and `H` pauses via `EnterLowPowerListen(stop_reason = VALID_SOLUTION_VERIFIED)`. THEN
`LeaseExpiry(X, t)` runs, sees `status(X) = PAUSED`, and takes the L4 `CASE PAUSED` (canonical CLOSE
without a wake; reassign the accepted unsearched suffix). The captured discovery snapshot is immutable and
is not retracted.

**Expected.** The boundary discovery is captured before the lease can expire and stays verifiable
(`ValidateCandidate` resolves against the immutable snapshot); no `HashWorkEvent` no-ops away a valid
solution. No corpus statement orders lease expiry first. Reqs: **L3**, §21/§0.7; E1/I2; interacts with
**L4**.

## TV94 — lease expiry on a CURRENT non-renewing holder closes the source before reassigning (L4)

**Preconditions.** Miner `H` holds a `CURRENT` assignment `X` in `ACTIVE_HASHING`; the lease elapsed at
`t`; `H` does not continue (or policy disallows renewal). `X` has an accepted searched prefix and an
accepted unsearched suffix `S`.

**Trace.** `LeaseExpiry(X, t)` takes `CASE CURRENT`; renewal is declined; it calls
`EnterLowPowerListen(H, stop_reason = ASSIGNMENT_REVOKED, assignment_ref = X, custody_on_close = expired,
termination_reason = lease_expiry)` (K6) — the single canonical closer sets `status(X) = CLOSED` and moves
`H` off `ACTIVE_HASHING` (T27). The common tail asserts `status(X) = CLOSED`, marks `S` reassignable, and
calls `RangeReassign(S, reason = lease_expiry, from_miner = H, dispatch_envelope = …)`. `RangeReassign`
asserts `status(source_assignment(S)) = CLOSED`.

**Expected.** The source is CLOSED (`expired`/`lease_expiry`) BEFORE `RangeReassign` runs; only the
accepted unsearched suffix is reassigned; one live head before, zero after (I18a/I18b). Reqs: **L4**,
§12/§13; K6/J7/C4.

## TV95 — lease expiry is status-aware for PAUSED and is a no-op for an already-terminal version (L4)

**Preconditions.** (a) Miner `P` holds a PATH-B `PAUSED` assignment `Y` (`P` is `LOW_POWER_LISTEN`,
`entry_stop_reason = VALID_SOLUTION_VERIFIED`); its lease elapsed at `t`. (b) Separately, a
`LeaseExpiry(Z, t')` fires for a version `Z` whose `status(Z) = SUPERSEDED` (it was renewed onto a new
CURRENT head).

**Trace.** For `Y`: `LeaseExpiry` takes `CASE PAUSED`, asserts `P` is `LOW_POWER_LISTEN /
VALID_SOLUTION_VERIFIED`, atomically sets `status(Y) = CLOSED` / `custody = expired` /
`termination_reason = lease_expiry`, clears the pause bookkeeping, and re-classifies
`entry_stop_reason(P) = ASSIGNMENT_REVOKED` — WITHOUT a wake (no `StartWake`, no second live head). The
common tail reassigns the accepted unsearched suffix (source now CLOSED). For `Z`: `LeaseExpiry` takes
`CASE SUPERSEDED OR CLOSED` and returns `lease_expiry_noop_terminal` — no close, no reassign; the live
head on that lineage is the separate CURRENT version with its own lease.

**Expected.** A PAUSED head is CLOSED without a wake and its suffix reassigned; a lease event for a
terminal (`SUPERSEDED`/`CLOSED`) version is a stale no-op; `SUPERSEDED` stays renewal-only; I18a/I18b hold
throughout. Reqs: **L4**, §12; J7/I18b.

## TV96 — the cross-round residency rebase is a single idempotent owner (L5)

**Preconditions.** Round `r` closed at `round_terminal_time = b` (recorded by `CloseRoundAssignments`); a
miner `m` was in `LOW_POWER_LISTEN` with an OPEN residency interval that continues across the boundary.
`RoundInitialise` for round `r+1` computes `boundary_id = (RoundID_r, RoundID_{r+1})` and calls
`RebaseResidencyAtRoundBoundary(prior_state, this, boundary_id)`.

**Trace.** First call: `boundary_id` is not in `rebased_boundaries`, so it CLOSES `m`'s open interval at
`b` (energy attributed to `RoundID_r`), REOPENS the same `LOW_POWER_LISTEN` state at the identical `b` in
round `r+1`'s ledger (no transition energy), and adds `boundary_id` to `rebased_boundaries`. A second call
with the same `boundary_id` (e.g. a replayed/retried `RoundInitialise`) hits the idempotence guard and
returns `rebase_noop` — no re-close, no re-attribution, no re-open. `CloseRoundAssignments` performed no
rebase; `ApplyMinerStateTransition` still owns intervals for an actual state change.

**Expected.** Exactly one close+reopen per boundary; the idle interval between round closure and the next
`StartWake` is counted exactly once (I19); the A1 baseline (`8.420833333 kWh`) is unchanged — the rebase
changes only how time is split across rounds, never the total. Reqs: **L5**, §1a/§1/§17a; I19.

## TV97 — StartWake schedules WakeCompleteEvent with no explicit delta_cycle (L6)

**Preconditions.** `StartWake` is invoked for miner `m` at dispatch `event_time = now`. Two sub-cases:
(a) positive wake latency `wake_latency > 0`; (b) zero-latency wake `wake_latency = 0` (H5).

**Trace.** `StartWake` draws `wake_latency` and schedules `WakeCompleteEvent` through
`ScheduleEvent`, supplying ONLY `(target_event_time, target_microphase = WAKE_COMPLETE)` and NO
`delta_cycle`: (a) `target_event_time = now + wake_latency` — a future time, so `ScheduleEvent` derives
`delta_cycle = 0`; (b) `target_event_time = now` — a same-time schedule, so `ScheduleEvent` derives the
forward delta-cycle at `WAKE_COMPLETE` (never backward). No `SCHEDULE`/`ScheduleEvent` argument supplies
`delta_cycle`; `ScheduleEvent` is the sole authority.

**Expected.** `WakeCompleteEvent` is enqueued with the `delta_cycle` that `ScheduleEvent` derived; the
caller cannot bypass the forward-scheduling rule; the zero-latency wake still advances a forward cycle.
Reqs: **L6**, §0.7e/§0.10; K8/H5/H2.

---

**Coverage.** TV91 (L1 envelope threading), TV92 (L2 single ASSIGNMENT→HASHING owner), TV93 (L3
discovery-before-lease-expiry), TV94/TV95 (L4 status-aware lease expiry), TV96 (L5 idempotent boundary
rebase), TV97 (L6 sole delta-cycle authority). Every vector names exact procedures and preconditions,
assumes no unmodeled external action, preserves the A1 baseline (`8.420833333 kWh`), and claims no
property. Name remains PoCol; mechanism is the idle policy within PoCol.
