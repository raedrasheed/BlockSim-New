# Stage 1J — Semantic Test Vectors (TV71–TV80)

Ten blocking test vectors for the Stage-1J implementation-handoff lock. Each names the exact
procedure(s) in `STAGE_01_PROTOCOL_PSEUDOCODE.md` and its exact preconditions; none assumes an
unmodeled external action. These extend TV1–TV70 (historical, in `STAGE_01C..I_*`, which are NOT
modified in Stage 1J). No property (energy, security, fairness) is claimed. The A1 baseline
(`8.420833333 kWh`) is unchanged. Name remains **PoCol**; mechanism is **the idle policy within PoCol**.

---

## TV71 — a candidate failure with no paused miner sets no dirty flag and reads no missing census

**Preconditions.** `HandlePropagationFailure(CandidateID, PropagationID, failure_reason)` runs; NO miner
is paused by this candidate, and the failure causes NO miner-state transition at this `event_time`.

**Trace.** The procedure marks the candidate `FAILED`, removes it from `active_propagation_set`, cancels
its own events, and finds no paused miner to resume. Per J1 it sets NO `security_census_dirty` flag
(candidate failure changes no `ACTIVE_HASHING` census). At the epilogue, `security_census_dirty[event_time]`
is false, so `FinalizeEventTimeSecurityCensus` returns `no_census_change` WITHOUT reading
`latest_security_census`.

**Expected.** No dirty flag is set; the epilogue never reads a (possibly absent) latest census; the J1
coherence invariant is trivially preserved. Reqs: **J1**, I-01.

## TV72 — a candidate failure with positive-latency paused miners creates the census update only at the later wake boundary

**Preconditions.** A candidate fails; miners paused by it have positive `wake_latency`. The candidate-
scoped resume is scheduled; the miners re-activate at a LATER `event_time`.

**Trace.** `HandlePropagationFailure` schedules `ResumeFromPause` events (candidate-scoped, two ids) and
sets NO dirty flag (J1). Each resume later runs `StartWake` (T30) and, at `now + wake_latency`, a
`WakeCompleteEvent` performs `WAKING -> ACTIVE_HASHING` (T5) through `ApplyMinerStateTransition`. THAT
boundary — the sole writer — sets `security_census_dirty[wake_time]` AND writes
`latest_security_census[wake_time]` together, and the epilogue at `wake_time` decides once.

**Expected.** The failure `event_time` carries no dirty census; the security update happens only at the
re-activation `event_time`, coherently. Reqs: **J1**, I-01, I-02.

## TV73 — an exact TransitionEventID replay after the state already changed is suppressed before the precondition

**Preconditions.** The first event applied `WAKING -> ACTIVE_HASHING` (so `miner_state = ACTIVE_HASHING`).
The IDENTICAL `TransitionEventID` (same `event_time`, `delta_cycle`, `event_seq`, MinerID, `old_state =
WAKING`, `new_state = ACTIVE_HASHING`, …) is replayed.

**Trace.** `ApplyMinerStateTransition` step (0) builds the id; step (1) finds it in
`transition_event_registry` and returns `duplicate_suppressed` — BEFORE step (2), which is the
`old_state = miner_state(MinerID)` check. So the replay never fails the precondition (even though
`miner_state` is now `ACTIVE_HASHING`, not `WAKING`), and charges no second residency/energy.

**Expected.** The replay is suppressed by identity, not rejected as an illegal stale source; no second
boundary is charged (I19 preserved). Reqs: **J2**, J3, I19.

## TV74 — two legitimate same-timestamp same-edge occurrences in different delta-cycles both apply

**Preconditions.** At one `event_time`, a miner completes `WAKING -> ACTIVE_HASHING` (T5) in
`delta_cycle = k`; a same-`event_time` revoke + re-wake returns it to `WAKING`, and it again completes
`WAKING -> ACTIVE_HASHING` in `delta_cycle = k' > k`.

**Trace.** The two `TransitionEventID`s differ in `delta_cycle` (and `event_seq`, assigned by
`ScheduleEvent`, J4/J9), so neither collides in `transition_event_registry`; BOTH apply, each opening a
fresh `ACTIVE_HASHING` residency interval.

**Expected.** Both legitimate edges apply (idempotence keyed by the full `TransitionEventID`, not by
state+timestamp). Reqs: **J3**, J2, J4.

## TV75 — two propagation attempts of one CandidateID produce distinct TransitionEventIDs

**Preconditions.** One `CandidateID` has two propagation attempts (`PropagationID = p1`, then `p2`), each
causing a candidate-triggered miner transition (e.g. a PATH-B pause via `EnterLowPowerListen`).

**Trace.** `EnterLowPowerListen` passes BOTH `candidate_id` and `propagation_id` to
`ApplyMinerStateTransition` (J3). The `TransitionEventID` includes `(candidate_id, propagation_id)`, so
the `p1` transition and the `p2` transition have DIFFERENT ids even though `CandidateID` is identical.

**Expected.** The two propagation attempts are distinct transitions (not conflated / not falsely
suppressed); `candidate_ref` ambiguity is gone. Reqs: **J3**.

## TV76 — after ROUND_ACCEPTED, a parked LOW_POWER_LISTEN miner is explicitly re-assigned under the new template via T10

**Preconditions.** A miner is in `LOW_POWER_LISTEN` with `entry_stop_reason = ROUND_ACCEPTED` (its
old-round assignment is CLOSED, J7). A new round runs `RoundInitialise` then `TemplateCommit` (new
`RoundID`, new `TemplateID`), reaching `round_state = ASSIGNMENT`.

**Trace.** `PrepareParticipantsForNewRound` iterates miners in stable MinerID order; for this miner it
takes `CASE LOW_POWER_LISTEN / ROUND_ACCEPTED`: archives the previous `entry_stop_reason`, binds a fresh
`ORIGINAL` `PENDING` assignment under the NEW `RoundID`/`TemplateID` via `CreatePendingAssignment`, and
`StartWake(from_state = LOW_POWER_LISTEN)` (T10). It does NOT reopen the CLOSED old-round assignment.
The intended assignment set is established BEFORE `ASSIGNMENT -> HASHING` (R4).

**Expected.** The parked miner participates in the next round via a fresh new-template assignment (T10);
no old assignment is reopened. Reqs: **J5**, J7, I1, I18b.

## TV77 — H_active = 0 during ASSIGNMENT records an observation, not a breach

**Preconditions.** At an `event_time` while `round_state = ASSIGNMENT` (a setup state), a boundary yields
`H_active = 0`; the epilogue runs `FinalizeEventTimeSecurityCensus -> SecurityFloorEvaluate`.

**Trace.** `SecurityFloorEvaluate` passes the terminal-first guard (not terminal) and the J8 stale guard
(fresh census), then the J6 applicability check: `round_state = ASSIGNMENT` is NOT in
`{HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY}`, so it `RECORD security_census_observation(...)` and
returns `setup_observation_only` — WITHOUT evaluating thresholds or recording any active-floor /
honest-floor / adversarial-share breach event.

**Expected.** A census observation is recorded; NO I16 breach event is counted during setup; no recovery.
Reqs: **J6**, I16.

## TV78 — an adversarial withdrawal closes the assignment as CLOSED, never SUPERSEDED; zero live heads

**Preconditions.** An adversarial miner is `ACTIVE_HASHING` on `CURRENT` version `X`;
`AdversarialParticipationChangeEvent(exit)` fires.

**Trace.** The exit path preserves accepted coverage, sets `custody_status(range(X)) = revoked` +
`revocation_reason(X) = adversarial_withdrawal` (I-07), cancels `X`'s pending hash units, and sets
`status(X) <- CLOSED` (J7 — NOT `SUPERSEDED`, which is renewal-only), then departs via T11. The lineage
of `X` now has ZERO live heads (I18b).

**Expected.** `status(X) = CLOSED` (never `SUPERSEDED`); the lineage shows zero live heads. Reqs: **J7**,
I-07, I18a, I18b.

## TV79 — event_creation_seq is initialised once, preserved across rounds, and orders events deterministically

**Preconditions.** A run starts (`prior_state = null`), schedules events across round 1, then round 2
begins (`RoundInitialise` with a non-null `prior_state`).

**Trace.** `RoundInitialise` sets `event_creation_seq <- 0` ONLY at run start and PRESERVES it on round 2
(§3.12). Every `ScheduleEvent` call increments and stamps `seq = event_creation_seq` AFTER the
deterministic `(delta_cycle, microphase, stable_tie_key)` ordering. Two runs with the same seeds/inputs
assign identical seqs, so the total-order key `(event_time, delta_cycle, microphase, stable_tie_key,
seq)` yields identical processing order.

**Expected.** One owner, one initialisation, preserved across rounds; deterministic, reproducible event
ordering; no ambient seq. Reqs: **J4**, J9, I-04.

## TV80 — a census produced under an old TemplateID keeps that provenance and cannot trigger recovery in the new context

**Preconditions.** A census-changing boundary at `event_time = t` produces
`latest_security_census[t]` under `(RoundID_A, TemplateID_A, state_version_A)`. Before the epilogue for
`t` runs, a same-time template change commits `TemplateID_B` (new epoch).

**Trace.** `ApplyMinerStateTransition` stored the census WITH its provenance
`(RoundID_A, TemplateID_A, state_version_A)` (J8). `FinalizeEventTimeSecurityCensus` passes that STORED
provenance (not the current epoch) to `SecurityFloorEvaluate`. The J8 stale-context guard sees
`event_TemplateID = TemplateID_A != TemplateID_committed = TemplateID_B`, records
`security_census_observation(stale_census, …)`, and returns `stale_census_observation` — it does NOT
evaluate thresholds against `TemplateID_B` and does NOT trigger recovery in the new context.

**Expected.** The census stays tagged with `TemplateID_A`; the same-time template change cannot
re-interpret it as a `TemplateID_B` census or trigger recovery in the new round/template. Reqs: **J8**,
J1, G10.

---

## Coverage

TV71/TV72 (J1 coherence + candidate-failure no-false-dirty), TV73 (J2 replay-before-precondition),
TV74 (J3/J4 legitimate same-edge across delta-cycles), TV75 (J3 propagation-attempt distinctness), TV76
(J5 next-round participation via T10), TV77 (J6 observation-not-breach in setup), TV78 (J7 CLOSED-not-
SUPERSEDED), TV79 (J4/J9 event_creation_seq ownership + determinism), TV80 (J8 census provenance). Every
vector names exact procedures and preconditions and assumes no unmodeled external action; the A1
baseline is unchanged.
