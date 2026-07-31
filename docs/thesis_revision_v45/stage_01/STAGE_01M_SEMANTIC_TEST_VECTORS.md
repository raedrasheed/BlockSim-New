# Stage 1M — Semantic Test Vectors (TV98–TV103)

Six blocking test vectors for the Stage-1M minimal executable closure. Each names the exact procedure(s)
in `STAGE_01_PROTOCOL_PSEUDOCODE.md` and its exact preconditions; none assumes a guard or cancellation not
present in the pseudocode, and none assumes an unmodeled external action. These extend TV1–TV97 (historical,
in `STAGE_01C..L_*`, which are NOT modified in Stage 1M); where they overlap a prior vector they SUPERSEDE
it on paper (TV102 supersedes TV96's residency-owner naming — see `STAGE_01M_SUPERSESSION_REGISTER.md`). No
property (energy, security, fairness, incentive) is claimed. The A1 baseline (`8.420833333 kWh`) is
unchanged. Name remains **PoCol**; mechanism is **the idle policy within PoCol**.

---

## TV98 — REGISTERED, RESERVE and LOW_POWER_LISTEN wakes all carry explicit dispatch envelopes (M1)

**Preconditions.** In the `ASSIGNMENT` phase of round `r`, `PrepareParticipantsForNewRound` is dispatched
by `ProcessEventTime` at `event_time = t` with `dispatch_envelope = (t, dc, seq)`. Three eligible miners:
`m1` REGISTERED, `m2` RESERVE, `m3` parked LOW_POWER_LISTEN (`entry_stop_reason = RANGE_EXHAUSTED`, policy
offers a range).

**Trace.** For each miner, `PrepareParticipantsForNewRound` calls `StartWake(…, dispatch_envelope =
dispatch_envelope)` (T3 / T4 / T10). Inside `StartWake`, the WAKING `ApplyMinerStateTransition` is written
with `event_time = dispatch_envelope.event_time`, `delta_cycle = dispatch_envelope.delta_cycle`,
`event_seq = dispatch_envelope.event_seq` — no positional `now` form, no `EQ.current_*` read. Then
`CompleteAssignmentPhase(RoundContext, dispatch_envelope)` performs the ASSIGNMENT → HASHING via the M2
helper.

**Expected.** All three WAKING transitions bind the SAME dispatch envelope's three fields EXPLICITLY; no
hook call relies on a shorthand; the seq is the dispatched event's own (owned by `ScheduleEvent`). Reqs:
**M1**, §0.9/§0.10/§2a/§2b.

## TV99 — a candidate failure with no paused miners still captures a HASHING-entry census (M2)

**Preconditions.** Round `r` is in `SOLUTION_PROPAGATION` with exactly one live candidate `C` (finder
`F` paused; assume `F` already resumed or was closed so NO miner is currently paused by `C`), and `C`'s
block arrival registered `outcome = REJECTED`. `AcceptanceBatchFinalize` is dispatched at `event_time = t`
with `dispatch_envelope`.

**Trace.** `AcceptanceBatchFinalize` calls `HandlePropagationFailure(RoundContext, C, PropagationID,
failure_reason = REJECTED, dispatch_envelope)`. `HandlePropagationFailure` fails `C`, cancels its events,
finds no paused miner to resume, and — propagation now quiescent while `round_state = SOLUTION_PROPAGATION`
— calls `TransitionRoundState(RoundContext, HASHING, dispatch_envelope)`. The helper transitions to HASHING
and, HASHING being floor-applicable, calls `CaptureSecurityCensusOnApplicabilityEntry(entered_state =
HASHING, at = dispatch_envelope.event_time)`, writing a coherent `security_census_dirty[t]` +
`latest_security_census[t]`.

**Expected.** The `SOLUTION_PROPAGATION → HASHING` re-entry captures a coherent applicability-entry census
even though no miner was paused and `H_active` did not change at `t`; the event-time epilogue therefore
evaluates the floor on the HASHING re-entry. Reqs: **M2**, §16d/§2a-bis; K7/J1.

## TV100 — a PENDING lease expires while the miner is WAKING (M3)

**Preconditions.** Miner `h` holds a `PENDING` assignment `X` (bound, not yet activated) and is `WAKING`
for `X` (a `WakeCompleteEvent` is scheduled). The lease elapses at `t`; `LeaseExpiry(X, t,
dispatch_envelope)` is dispatched. `X` has an accepted searched prefix and an accepted unsearched suffix `S`.

**Trace.** `LeaseExpiry` takes `CASE PENDING`: it CANCELS the scheduled `WakeCompleteEvent` for `(h,
AssignmentID(X), assignment_version(X))`; since `miner_state(h) = WAKING` and `target_assignment(h) = X`,
it calls `ApplyMinerStateTransition(h, WAKING, OFFLINE, event_time = dispatch_envelope.event_time,
delta_cycle = …, event_seq = …, reason = lease_expired_while_waking, assignment_ref = X)` (T12); PRESERVES
the accepted searched prefix; sets `status(X) = CLOSED` / `custody = expired` / `termination_reason =
lease_expiry`. The common tail asserts `status(X) = CLOSED`, exposes `S`, and calls `RangeReassign(S, reason
= lease_expiry, from_miner = h, dispatch_envelope)` (which asserts `status(source) = CLOSED`).

**Expected.** The pending wake is cancelled and the WAKING holder resolved to OFFLINE BEFORE the head is
closed and the suffix reassigned; the accepted prefix is preserved; reassignment happens only after the
source is CLOSED. Reqs: **M3**, §12; L4/C4; interacts with **M1**.

## TV101 — a stale WakeCompleteEvent for a CLOSED assignment cannot activate the miner (M3)

**Preconditions.** A `WakeCompleteEvent` for `(h, X)` was scheduled, then `X` was CLOSED (e.g. by the
TV100 PENDING lease expiry, or a round closure) — but the scheduled event is dispatched anyway (a stale
event that cancellation raced). `dispatch_envelope` is supplied by `ProcessEventTime`.

**Trace.** `WakeCompleteEvent` BEGINS with its M3 stale-target guard: `status(X)` is `CLOSED` (not in
`{PENDING, PAUSED}`), so the guard fires and returns `stale_wake_noop` before any `ApplyMinerStateTransition`.
No `WAKING → ACTIVE_HASHING` occurs; `h` is unchanged. The guard is independent of the `HashWorkEvent` G9
guard (which does not protect `WakeCompleteEvent`).

**Expected.** A wake targeting a CLOSED (or superseded / stale-epoch / non-live-head) assignment returns
`stale_wake_noop` and CANNOT activate the miner. Reqs: **M3**, §0.10; I18b.

## TV102 — CloseRoundAssignments records round_terminal_time but does not close a residency interval (M4)

**Preconditions.** Round `r` is accepted: `ValidBlockAccept` calls `CloseRoundAssignments(…, disposition =
ROUND_ACCEPTED, dispatch_envelope)` at `event_time = t`. Miner `m` continues in `LOW_POWER_LISTEN` across
the boundary with an OPEN residency interval. Round `r+1` then runs `RoundInitialise`.

**Trace.** `CloseRoundAssignments` closes assignments, transitions the required miners (each hook call
explicit, M1), cancels round events, records the round disposition, and `RECORD round_terminal_time(r) <-
dispatch_envelope.event_time` — it performs NO residency/energy finalisation (the former in-line finalise
line is removed, M4). `m`'s residency interval stays OPEN. `RoundInitialise` for `r+1` calls
`SettleResidencyBoundary(this, mode = REBASE_TO_NEXT_ROUND, boundary_id = (r, r+1), prior_state = r)`, which
CLOSES `m`'s interval at `round_terminal_time(r)` (energy to `r`), REOPENS the same `LOW_POWER_LISTEN` state
at the identical time in `r+1` (no transition energy), and adds `boundary_id` to `rebased_boundaries`; a
repeat is a `settle_noop`.

**Expected.** `CloseRoundAssignments` records `round_terminal_time` only and closes no residency interval;
the single owner `SettleResidencyBoundary` closes/reopens the interval exactly once (idempotent via
`boundary_id`); the idle interval is counted once (I19); the A1 baseline (`8.420833333 kWh`) is unchanged.
Reqs: **M4**, §17a/§1a/§1; I19.

## TV103 — every scheduled event has a microphase and every event-producing miner loop is stably sorted (M5)

**Preconditions.** `TemplateRefresh` (dispatched, with `dispatch_envelope`) rebinds several eligible
miners over a new template; separately, a finder's `HashWorkEvent` hit schedules propagation, and a
candidate failure schedules resumes.

**Trace.** `TemplateRefresh` iterates `FOR EACH miner m IN SORT(eligible BY MinerID ascending)` and, for
each, `StartWake(…, dispatch_envelope)` schedules a `WakeCompleteEvent` via `ScheduleEvent(…,
target_microphase = WAKE_COMPLETE)`. `ScheduleNextHashWork` schedules `HashWorkEvent` via `ScheduleEvent(…,
target_microphase = HASH_WORK)`. `ScheduleSolutionPropagation` schedules `CertificateArrival`
(`CERTIFICATE_ARRIVAL`) and `BlockAcceptancePoint` (`FULL_BLOCK_ARRIVAL`) in stable MinerID order.
`HandlePropagationFailure` schedules each `ResumeFromPause` (`RESUME`) in stable MinerID order. Every
`ScheduleEvent` supplies an explicit `target_microphase` from the §0.7g canonical mapping; the sort
precedes the `event_creation_seq` assignment (J4/G7).

**Expected.** No enqueue omits a target microphase; every event-producing miner loop is deterministically
sorted before seq assignment, so the same-timestamp processing order is reproducible across reruns. Reqs:
**M5**, §0.7g/§5/§16b/§16d/§19; G7/J4.

---

**Coverage.** TV98 (M1 explicit envelopes), TV99 (M2 census on SOLUTION_PROPAGATION→HASHING re-entry),
TV100 (M3 executable PENDING lease expiry while WAKING), TV101 (M3 stale-wake no-op), TV102 (M4 single
residency-boundary owner; CloseRoundAssignments records round_terminal_time only), TV103 (M5 explicit
microphases + sorted loops). Every vector names exact procedures and preconditions, assumes no guard or
cancellation absent from the pseudocode, preserves the A1 baseline (`8.420833333 kWh`), and claims no
property. Name remains PoCol; mechanism is the idle policy within PoCol.
