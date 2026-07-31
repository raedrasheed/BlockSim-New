# Stage 1I — Semantic Test Vectors (TV61–TV70)

Ten blocking test vectors for the Stage-1I execution-contract lock. Each names the exact procedure(s)
in `STAGE_01_PROTOCOL_PSEUDOCODE.md` and its exact preconditions; none assumes an unmodeled external
action. These extend TV1–TV60 (historical, in `STAGE_01C/D/E/F/G/H_*`, which are NOT modified in Stage
1I). No property (energy, security, fairness) is claimed. The A1 baseline (`8.420833333 kWh`) is
unchanged. Name remains **PoCol**; mechanism is **the idle policy within PoCol**.

---

## TV61 — a late-microphase ACTIVE_HASHING exit does not lose the dirty flag; the epilogue reads its census

**Preconditions.** At `event_time = t`, in a LATE microphase of `delta_cycle = k`, a miner leaves
`ACTIVE_HASHING` (e.g. `EnterLowPowerListen` or `AdversarialParticipationChangeEvent(exit)`), routed
through `ApplyMinerStateTransition`. No further event exists at any microphase after it in cycle `k`.

**Trace.** `ApplyMinerStateTransition` recomputes the census, sets `security_census_dirty[t] <- true`
and overwrites `latest_security_census[t]` with the post-transition census (I-01). The flag is keyed by
`t` ALONE, so it is NOT tied to the completing microphase or to `delta_cycle k`. `ProcessEventTime(t)`
drains `t` to quiescence and, because `security_census_dirty[t]`, runs
`FinalizeEventTimeSecurityCensus(t)` exactly once, reading `latest_security_census[t]`.

**Expected.** The dirty flag survives to the epilogue (it cannot be stranded by a late microphase), and
the single decision uses the exit's census. Reqs: **I-01**, I-02, §0.7d.

## TV62 — census changes across delta-cycles k, k+1, k+2 yield exactly one decision on the last census

**Preconditions.** At `event_time = t`, census-changing transitions occur in `delta_cycle` `k`, then
`k+1`, then `k+2` (each a handler-generated forward event per §0.7-H2), each via
`ApplyMinerStateTransition`.

**Trace.** Each transition OVERWRITES `latest_security_census[t]` with its newest census and re-asserts
`security_census_dirty[t]` (I-01); none schedules a floor decision. `ProcessEventTime(t)` completes all
of cycles `k`, `k+1`, `k+2` (no backward travel, §0.7-H2) until `t` is quiescent, THEN runs
`FinalizeEventTimeSecurityCensus(t)` ONCE, deciding from the census left by the `k+2` transition.

**Expected.** Exactly one floor decision, on the FINAL (k+2) census; no intermediate delta-cycle census
independently triggers recovery. Reqs: **I-01**, I-02, H2.

## TV63 — the epilogue runs even when the census transition is the last ordinary event at t

**Preconditions.** At `event_time = t`, the census-changing transition is the LAST ordinary event; the
queue holds NO later event at `t` and no later microphase/delta-cycle event.

**Trace.** `ProcessEventTime(t)` drains `t`, finds the queue quiescent, and — because
`FinalizeEventTimeSecurityCensus` is a STRUCTURAL EPILOGUE invoked by the driver, NOT a queued event —
still calls it once (`security_census_dirty[t]` is set), then marks `t` finalised.

**Expected.** The security decision is made even with no later event to "carry" it; an epilogue can
never be missed the way a queued microphase-5 event could. Reqs: **I-02**, §0.7d.

## TV64 — two legitimate same-timestamp WAKING→ACTIVE_HASHING edges in different delta-cycles both apply

**Preconditions.** At `event_time = t`, a miner completes `WAKING → ACTIVE_HASHING` (T5) in
`delta_cycle = k`; a same-`t` revocation + re-wake sequence returns it to `WAKING` and it again
completes `WAKING → ACTIVE_HASHING` (T5) in a later `delta_cycle = k'` (`k' > k`). Both edges are legal
per the miner state machine.

**Trace.** Each call builds a `TransitionEventID = (t, delta_cycle, seq, MinerID, WAKING,
ACTIVE_HASHING, …)` (I-03). The two ids DIFFER (distinct `delta_cycle` and `seq`), so neither is in
`transition_event_registry` when applied; BOTH transitions execute, each opening a fresh
`ACTIVE_HASHING` residency interval via `ApplyMinerStateTransition`.

**Expected.** The second transition is NOT suppressed (idempotence is keyed by `TransitionEventID`, not
by `(MinerID, event_time, old_state, new_state)`); both legitimate edges apply. Reqs: **I-03**.

## TV65 — an exact TransitionEventID replay is suppressed and charges no second boundary

**Preconditions.** `ApplyMinerStateTransition` is invoked twice with the IDENTICAL
`TransitionEventID` (same `event_time`, `delta_cycle`, `seq`, `MinerID`, `old_state`, `new_state`,
`reason`, `AssignmentID`, `assignment_version`, ids) — a replay (e.g. a duplicated dispatch).

**Trace.** The first call adds the id to `transition_event_registry` and applies the transition. The
second call finds the id already present and `RETURN duplicate_suppressed` BEFORE step (1): no residency
interval is opened/closed, no `E_transition`/`E_coordination` is charged, no census recompute occurs.

**Expected.** The replay is a no-op that charges no second transition energy and no second residency
boundary; `t_<state>` and energy are unaffected (I19 preserved). Reqs: **I-03**, I5, I6, I19.

## TV66 — RoundInitialise creates every runtime registry; no field is read before initialisation

**Preconditions.** `RoundInitialise` is invoked at run start (`prior_state = null`) and again for a
subsequent round.

**Trace.** At run start it initialises the PER-ROUND registries (`active_propagation_set`,
`acceptance_batch_registry`, `candidate_discovery_seq`, `block_accepted`, `state_version`,
`residency_ledger`) AND the PER-RUN event-loop bookkeeping (`security_census_dirty`,
`latest_security_census`, `transition_event_registry`, `finalised_event_times`, `current_delta_cycle`),
and RETURNS them in the `RoundContext`. On a subsequent round it resets the per-round registries and
PRESERVES the per-run bookkeeping (§3.12).

**Expected.** Every normative registry is explicitly initialised and returned; none is an implicit
global; no procedure reads a registry before `RoundInitialise` created it. Reqs: **I-04**.

## TV67 — a persistent breach already in SECURITY_RECOVERY does not self-transition or bump state_version

**Preconditions.** The round is in `SECURITY_RECOVERY` (`state_version = v`); the quiescent event-time
census is still a breach when `FinalizeEventTimeSecurityCensus → SecurityFloorEvaluate` runs.

**Trace.** `SecurityFloorEvaluate` passes the terminal-first guard (not terminal) and the stale guard,
records the breach (I16), then reaches the persistent-recovery branch: `round_state =
SECURITY_RECOVERY` → `RECORD_ONCE breach_persists(t)` and RETURN `breach_persists`. It performs NO
`SECURITY_RECOVERY → SECURITY_RECOVERY` transition and does NOT bump `state_version`.

**Expected.** No self-transition; `state_version` remains `v` (so carried epochs are not spuriously
staled); persistence is recorded, not silently repaired. Reqs: **I-05**, I16.

## TV68 — an adversarial-enter event for a ROUND_ACCEPTED-idle miner creates no assignment/wake in the closed round

**Preconditions.** A miner is in `LOW_POWER_LISTEN` with `entry_stop_reason = ROUND_ACCEPTED` (its
assignment closed because the round ended). `AdversarialParticipationChangeEvent(enter)` fires while the
`RoundContext` is the closed round.

**Trace.** The `enter` switch takes `CASE LOW_POWER_LISTEN`; the `entry_stop_reason` sub-switch takes
`CASE ROUND_ACCEPTED OR ROUND_ABORTED` → `RETURN deferred_round_terminal`. It does NOT call
`CreatePendingAssignment`, does NOT `StartWake`, and creates NO assignment in the closed `RoundContext`.
Participation is deferred to the next `RoundInitialise`/`TemplateCommit`/`ASSIGNMENT` phase.

**Expected.** No assignment or wake in the closed round; the miner re-participates only under a fresh
`RoundID`/`TemplateID`. Reqs: **I-06**, I18b, I3.

## TV69 — an adversarial ACTIVE_HASHING withdrawal records revoked + revocation_reason, not an invented custody value

**Preconditions.** An adversarial miner is `ACTIVE_HASHING` on `CURRENT` version `X`;
`AdversarialParticipationChangeEvent(exit)` fires.

**Trace.** The exit path sets `custody_status(range(X)) <- revoked` (a CANONICAL enum value) and
`revocation_reason(X) <- adversarial_withdrawal` (the two-field representation, I-07), records the I9
provenance, closes/supersedes `X`, and departs via T11 through `ApplyMinerStateTransition`. It never
assigns `custody_status <- revoked_adversarial_exit` or any non-enum value.

**Expected.** `custody_status = revoked` AND `revocation_reason = adversarial_withdrawal`; no undeclared
custody value exists; I8b's canonical enum holds. Reqs: **I-07**, I8b, I9.

## TV70 — current normative files reference I1..I19; historical Stage-1A..1H files are unchanged

**Preconditions.** The un-suffixed normative Stage-1 documents and the frozen `STAGE_01[A-H]_*`
artifacts as committed on the Stage-1I branch.

**Trace.** Every un-suffixed normative file that references the invariant range now reads `I1..I19`
(including `I18a`/`I18b`); no residual `I1..I17`-only range text remains (I-08). A `git diff --name-only`
against the base shows NO `STAGE_01[A-H]_*` file modified; the checksum manifest records the frozen
artifacts unchanged.

**Expected.** Consistent `I1..I19` referencing across current normative files; all Stage-1A..1H
historical artifacts byte-frozen. Reqs: **I-08**, A–H frozen.

---

## Coverage

TV61/TV62/TV63 (I-01/I-02 event-time epilogue and quiescence), TV64/TV65 (I-03 TransitionEventID
idempotence), TV66 (I-04 registry initialisation), TV67 (I-05 persistent-recovery), TV68 (I-06 closed-
round re-entry deferral), TV69 (I-07 canonical custody enum), TV70 (I-08 reference consistency + A–H
frozen). Every vector names exact procedures and preconditions and assumes no unmodeled external action;
the A1 baseline is unchanged.
