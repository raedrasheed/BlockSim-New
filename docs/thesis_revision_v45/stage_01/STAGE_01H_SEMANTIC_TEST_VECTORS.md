# Stage 1H — Semantic Test Vectors (TV51–TV60)

Ten blocking test vectors for the Stage-1H timestamp-causality lock. Each names the exact
procedure(s) in `STAGE_01_PROTOCOL_PSEUDOCODE.md` and its exact preconditions; none assumes an
unmodeled external action. These extend TV1–TV50 (historical, in `STAGE_01C/D/E/F/G_*`, which are NOT
modified in Stage 1H). No property (energy, security, fairness) is claimed. The A1 baseline
(`8.420833333 kWh`) is unchanged; any energy change is attributable ONLY to reduced active
power-time. Name remains **PoCol**; mechanism is **the idle policy within PoCol**.

---

## TV51 — a same-`event_time` event created inside a handler is scheduled forward, never into a completed microphase (H2)

**Preconditions.** A handler runs in microphase `m` of `(event_time = t, delta_cycle = k)` and, while
executing, creates a new event whose target microphase is `m' <= m` (same or earlier), all at the
same `event_time = t`.

**Trace.** By the delta-cycle rule (§0.7-H2): an event whose target microphase is later than `m` is
scheduled in the CURRENT `delta_cycle = k`; an event whose target microphase is `m' <= m` is
scheduled in `delta_cycle = k + 1` at microphase `m'`. The loop completes ALL microphases of
`delta_cycle k` before processing any event of `delta_cycle k + 1` at the same `event_time`. No event
is inserted into a microphase already completed in `delta_cycle k`. The total order key is
`(event_time, delta_cycle, microphase, stable_tie_key, seq)` with
`stable_tie_key = (CandidateID, MinerID, AssignmentID)`.

**Expected.** The created event fires at `(t, k+1, m')`, strictly after every event of `(t, k)` and
before any event of `(t, k+2)`; scheduling is causally forward and reproducible. Reqs: **H2**, §0.2,
§0.7-H2.

## TV52 — several same-timestamp miner transitions cause exactly ONE security evaluation, not one per transition (H3)

**Preconditions.** Three miners leave `ACTIVE_HASHING` at the same `(event_time = t, delta_cycle = k)`
(e.g. three `AdversarialParticipationChangeEvent(exit)` or `EnterLowPowerListen` events), each routed
through `ApplyMinerStateTransition`.

**Trace.** Each `ApplyMinerStateTransition` recomputes the census, `RECORD
intermediate_census_for_audit(t, k, …)` (audit only), and — because each changed the `ACTIVE_HASHING`
census — sets `security_evaluation_required[(t, k)] <- true`. NO transition schedules its own
`SecurityFloorEvaluate`. In microphase 5, `FinalizeTimestampSecurityCensus(RoundContext, t, k)` runs
EXACTLY ONCE: it sees the flag set, reads the FINAL settled census (after all three transitions
settled), clears the flag, and calls `SecurityFloorEvaluate` at most once carrying
`(RoundID, TemplateID, state_version)`.

**Expected.** One floor decision on the settled census; the FIRST of the three transitions never
independently triggers recovery from an intermediate census; intermediate census values are retained
for audit but drive no round-state transition. Reqs: **H3**, I16, I17.

## TV53 — a floor breach evaluated while the round is in TEMPLATE_REFRESH records observation-only, no recovery transition (H4)

**Preconditions.** `security_evaluation_required[(t, k)]` is set; when
`FinalizeTimestampSecurityCensus` runs in microphase 5, the round is in `TEMPLATE_REFRESH` (a legal
non-recovery state), and the settled census is a breach.

**Trace.** `FinalizeTimestampSecurityCensus → SecurityFloorEvaluate`. The terminal/stale guard passes
(same RoundID/TemplateID/state_version). Breach records are made (`RECORD_ONCE breach_event`, I16),
but the H4 source guard `round_state ∈ {HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY}` is FALSE,
so the ELSE branch returns `refresh_observation_only` and performs NO transition.

**Expected.** The breach is recorded (I16) but the round is NOT moved to `SECURITY_RECOVERY` from
`TEMPLATE_REFRESH`; setup states, `ROUND_EXHAUSTED`, and terminal rounds are handled the same way
(observation-only / `terminal_stale_noop`). Reqs: **H4**, I16, G10.

## TV54 — a zero-latency wake completes at the same `event_time` in the next delta-cycle, never backward (H5)

**Preconditions.** `StartWake(M, target, from_state)` runs at `(event_time = now, delta_cycle = c)`
and the wake-latency draw returns `wake_latency = 0` (a permitted experimental value).

**Trace.** `StartWake` applies `→ WAKING` (F6) then branches on latency: because `wake_latency = 0`
it schedules `WakeCompleteEvent` `AT event_time = now, delta_cycle = c + 1, microphase =
WAKE_COMPLETE` (NOT at a past microphase of cycle `c`). The `WAKING` residency interval and its
`P_wake · t_wake + E_transition` accounting path still exist (with `t_wake = 0` here), owned by
`ApplyMinerStateTransition` (I19).

**Expected.** The `WakeCompleteEvent` fires at `(now, c+1, WAKE_COMPLETE)`; a zero-latency resume
initiated after the wake microphase never travels backward into a completed phase; the WAKING
accounting path is preserved. Reqs: **H5**, §0.7-H2, D2, I19.

## TV55 — an adversarial re-entry of a still-PAUSED idle miner resumes its OWN head, minting no second live head (H6)

**Preconditions.** Adversarial miner `A` is in `LOW_POWER_LISTEN` with `entry_stop_reason =
VALID_SOLUTION_VERIFIED` and a `PAUSED` head `h` (a live head, I18b) carrying
`pause_cause_candidate_id`/`pause_cause_propagation_id`. `AdversarialParticipationChangeEvent(A,
enter)` fires.

**Trace.** The `enter` switch takes `CASE LOW_POWER_LISTEN` with `entry_stop_reason =
VALID_SOLUTION_VERIFIED`: it reads `h`'s own recorded ids and calls `ResumeFromPause(A, trigger =
adversarial_reactivation, pause_cause_candidate_id(h), pause_cause_propagation_id(h))`. It does NOT
call `RangeAssign`. `ResumeFromPause`'s two-id precondition matches (ids read from `A`'s own head), and
it wakes `h` back to `ACTIVE_HASHING` via `StartWake` (T30) from `retained_actual_frontier`.

**Expected.** `A` resumes its unique PAUSED head; no second live head is created (I18b upheld); the
adversarial re-entry uses the legal `ResumeFromPause` path, never `RangeAssign`. Reqs: **H6**, I18b,
G11, F2.

## TV56 — an adversarial re-entry of a post-closure idle miner opens a FRESH head via T10, not RangeAssign (H6)

**Preconditions.** Adversarial miner `B` is in `LOW_POWER_LISTEN` with `entry_stop_reason ∈
{RANGE_EXHAUSTED, ASSIGNMENT_REVOKED, ROUND_ACCEPTED, ROUND_ABORTED}` — its prior assignment is CLOSED
(no live head, I18b). `AdversarialParticipationChangeEvent(B, enter)` fires.

**Trace.** The `enter` switch takes `CASE LOW_POWER_LISTEN`, ELSE branch: it SELECTs a fresh
never-assigned range (I1), builds a fresh `ORIGINAL` `PENDING` via `CreatePendingAssignment` (a NEW
lineage, I18b), sets the lease, and `StartWake(B, target = fresh, from_state = LOW_POWER_LISTEN)` —
the legal `LOW_POWER_LISTEN → WAKING` edge (T10). It does NOT call `RangeAssign` (whose precondition is
`REGISTERED`/`RESERVE`, T3/T4), so no illegal transition is fabricated.

**Expected.** `B` re-enters via T10 with a fresh `ORIGINAL` lineage; `RangeAssign`'s precondition is
not violated; only a legal per-state edge is used. Reqs: **H6**, I1, I18b, T10.

## TV57 — an adversarial exit from ACTIVE_HASHING preserves accepted coverage and leaves no live head (H6)

**Preconditions.** Adversarial miner `C` is `ACTIVE_HASHING` on `CURRENT` version `X`
(`accepted_frontier = f`, `range = [s, e]`, `s ≤ f < e`) with pending `HashWorkEvent` units for
`(C, AssignmentID(X), assignment_version(X))`. `AdversarialParticipationChangeEvent(C, exit)` fires.

**Trace.** The `exit` path (`miner_state(C) = ACTIVE_HASHING`): PRESERVE the accepted searched prefix
`[s, f]`; expose ONLY `suffix = [f+1, e]` as `inactive_unsearched`/reassignable (C4); record the I9
withdrawal reason/provenance on `X`; `CANCEL pending HashWorkEvent units for (C, AssignmentID(X),
assignment_version(X))`; `CLOSE/SUPERSEDE X` (no live head remains, I18a); then
`ApplyMinerStateTransition(C, ACTIVE_HASHING, OFFLINE, now, reason = adversarial_withdrawal,
assignment_ref = X)` (T11) closes `P_hash` and recomputes I17.

**Expected.** Accepted coverage is preserved; only the accepted unsearched suffix is reassignable; the
version's pending hash units are cancelled; `C` has NO live `CURRENT` head after exit; the departure
is via the legal T11 through the hook. Reqs: **H6**, I8a, I8b, I9, I17, I18a.

## TV58 — an ACTIVE_HASHING occupancy with N hash units charges `t_hash` once at the boundary; each HashWorkEvent adds zero duration (H7/I19)

**Preconditions.** Miner `M` enters `ACTIVE_HASHING` at `t_in` and later leaves at `t_out`; between
them `N` `HashWorkEvent`s fire under its `CURRENT` version.

**Trace.** Entry: `ApplyMinerStateTransition(… → ACTIVE_HASHING, t_in)` OPENS the residency interval
in `residency_ledger`. Each `HashWorkEvent` records `hash_work_metadata(...)` ONLY (modeled hash
evaluations, cursor progress) and adds ZERO duration to any `t_<state>`. Exit:
`ApplyMinerStateTransition(ACTIVE_HASHING → …, t_out)` CLOSES the interval and accrues
`t_ACTIVE_HASHING = t_hash = t_out − t_in` once, with `P_hash · t_hash`.

**Expected.** `t_hash` for the occupancy equals `t_out − t_in` exactly, counted ONCE at the boundary;
the `N` hash units contribute no additional residency; `residency_ledger` is the sole owner (I19). The
A1 baseline is unaffected; any energy change comes only from reduced active power-time. Reqs: **H7**,
I19, I5, I6.

## TV59 — EnterLowPowerListen pauses/closes exactly the passed `assignment_ref`, never a stale historical version (H8)

**Preconditions.** Miner `M` holds a live head version `v_live` (`CURRENT` or `PAUSED`) in a lineage
that also contains an older `SUPERSEDED` version `v_old`. A caller invokes `EnterLowPowerListen(…,
assignment_ref = v_live)` — the exact live head.

**Trace.** `EnterLowPowerListen`'s precondition requires `assignment_ref` belongs to `M` AND
`status(assignment_ref) ∈ {CURRENT, PAUSED}`; `v_live` satisfies it, `v_old` (SUPERSEDED) would not.
Every SWITCH case operates on `assignment_ref` (not an undeclared free `assignment`): e.g.
`VALID_SOLUTION_VERIFIED` pauses `v_live` (CURRENT → PAUSED), retaining its frontier;
`ASSIGNMENT_REVOKED` closes/supersedes `v_live` after exposing only its accepted unsearched suffix.
`ApplyMinerStateTransition(…, assignment_ref = v_live, …)` records the edge.

**Expected.** Exactly `v_live` is paused/closed; the `SUPERSEDED` `v_old` is never touched by accident;
there is no reliance on an undeclared free variable. All five call sites (`LeaseExpiry`,
`EarlyStopVerify`, `ScheduleSolutionPropagation`, `CloseRoundAssignments`, `CloseTemplateAssignments`)
pass the exact version. Reqs: **H8**, I18a, I18b, I4.

## TV60 — a valid candidate preserved through SECURITY_RECOVERY is accepted; round-state is not identified with the propagation set (H1)

**Preconditions.** The round is in `SECURITY_RECOVERY` (entered on a floor breach from
`SOLUTION_PROPAGATION`, R8) while `active_propagation_set` still holds a `PENDING_ACCEPTANCE` context
`cpc` (G8 preserved it). A full block for `cpc` registers at the acceptance point.

**Trace.** At the acceptance timestamp, microphase 3 collects the block arrival
(`BlockAcceptancePoint` register-only); microphase 4 `AcceptanceBatchFinalize → ValidateCandidate(cpc)
→ ValidBlockAccept`. `ValidBlockAccept` accepts from `{SOLUTION_PROPAGATION, SECURITY_RECOVERY}` and
performs the atomic closure `→ ROUND_ACCEPTED` (R6), marking other live candidates
COMPETING/STALE/CANCELLED and closing the round exactly once. There is NO `iff` forcing the round to
be `SOLUTION_PROPAGATION` while candidates are live.

**Expected.** The recovery-state round is closed by the valid candidate (`SECURITY_RECOVERY →
ROUND_ACCEPTED`); acceptance is causally downstream of arbitration; the round-state and the
propagation set are not identified. Reqs: **H1**, G8, G5, I2, I3.

---

## Coverage

TV51 (H2 delta-cycle), TV52 (H3 single final census), TV53 (H4 legal recovery source), TV54 (H5
zero-latency wake), TV55/TV56/TV57 (H6 adversarial entry-paused / entry-post-closure / exit), TV58
(H7/I19 residency single owner), TV59 (H8 explicit `assignment_ref`), TV60 (H1 consolidated round
model / recovery-state acceptance). Every vector names exact procedures and preconditions and assumes
no unmodeled external action; H7 preserves the A1 baseline.
