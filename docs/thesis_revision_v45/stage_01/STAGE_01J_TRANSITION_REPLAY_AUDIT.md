# Stage 1J — Transition Replay Audit (J2)

A structural audit of Stage-1J correction **J2** (replay guard BEFORE the old-state precondition) in
the **PoCol** protocol pseudocode (`STAGE_01_PROTOCOL_PSEUDOCODE.md`): in `ApplyMinerStateTransition`
(§0.9) the exact-replay suppression check is evaluated in step (1) — STRICTLY BEFORE the old-state
precondition `old_state = miner_state(MinerID)`, which is relocated to step (2) and evaluated for a
NON-replay only. This document is documentation only; it audits wording and control structure,
describes only the idle policy within PoCol, introduces no new consensus feature, and claims **no**
security, fairness, energy, or incentive property. The A1 baseline (`8.420833333 kWh`) is unchanged.

---

## 1. The corrected-away problem (old-state check misclassifies an exact replay)

The old-state precondition compares the caller's declared `old_state` against the miner's LIVE
`miner_state(MinerID)`. An **exact replay** is the same dispatched event delivered twice: it necessarily
arrives AFTER the first (genuine) occurrence already ran `ApplyMinerStateTransition` and executed step
(6) `SET miner_state(MinerID) <- new_state`. So at replay time `miner_state(MinerID) = new_state`, not
`old_state`.

Suppose the old-state check ran as a top-level precondition (or as step (1)), BEFORE the replay guard.
Then the replay's `old_state` (e.g. `WAKING`) would be compared against the already-mutated live state
(`ACTIVE_HASHING`); the guard `old_state != miner_state(MinerID)` would be TRUE, and the call would
`RETURN illegal_stale_source` — mis-handling a benign exact-id duplicate as an illegal/stale transition
instead of a clean no-op. That is precisely why the §0.9 `PRECONDITIONS` note records that the old-state
equality is *"NOT a top-level precondition; it is checked in step (2) AFTER the replay guard, because an
exact replay necessarily arrives after the first event already changed `miner_state`."*

## 2. Mechanism (replay guard first, old-state precondition second)

`ApplyMinerStateTransition` (§0.9, F6) is the SOLE writer of `miner_state` (§0.3), the SOLE owner of
`residency_ledger` accounting and one-shot boundary energy, and the SOLE writer of the security census
bookkeeping (I-01/J1). Its ordered steps, quoting the actual §0.9 step labels:

```
# (0) J2/J3 EVENT-IDENTITY IDEMPOTENCE — evaluated FIRST, before any state or energy step.
SET TransitionEventID <- (event_time, delta_cycle, event_seq, MinerID, old_state, new_state, reason,
                          AssignmentID(assignment_ref), assignment_version(assignment_ref),
                          candidate_id, propagation_id)                       # immutable (J3)
# (1) J2 REPLAY GUARD BEFORE THE STATE PRECONDITION.
IF TransitionEventID in transition_event_registry:
  RETURN duplicate_suppressed        # exact replay only; NO old-state check, NO residency/energy charge
ADD TransitionEventID to transition_event_registry
# (2) J2 OLD-STATE PRECONDITION — for a NON-REPLAY only.
IF old_state != NONE AND old_state != miner_state(MinerID):
  RETURN illegal_stale_source        # a non-replay whose source no longer matches is rejected (not applied)
# (3) close the OLD residency interval at event_time; open the NEW one at event_time.  (I5/I6)
# (4) one-shot boundary energy for this crossing (E_transition and/or E_coordination).  (I6)
# (5) assignment status update where the edge specifies one.
# (6) atomically set the new miner_state.
# (7) recompute the census DETERMINISTICALLY from the post-transition ACTIVE_HASHING set (I17).
# (8) J1/I-01 EVENT-TIME SECURITY BOOKKEEPING (dirty flag + latest census, atomically together).
```

**Ordering.** Step (0) builds the immutable `TransitionEventID`; step (1) consults
`transition_event_registry` and, on a hit, returns `duplicate_suppressed` STRICTLY BEFORE step (2)'s
old-state precondition and before every apply step (3)–(8). Only for a NON-replay (id newly added to the
registry in step (1)) does control reach step (2), where `old_state != miner_state(MinerID)` yields
`illegal_stale_source`. The residual top-level `PRECONDITIONS` clause is legality alone — *"(old_state ->
new_state) is a legal miner transition (`STAGE_01_MINER_STATE_MACHINE.md §3`)"* — which is DISTINCT from
old-state matching and unaffected by this reordering.

**Registry field.** `transition_event_registry` (§0.8, `RoundContext registries`) is *"set of
`TransitionEventID`s already applied (I-03)"*; its note states `ApplyMinerStateTransition` *"suppresses
ONLY the exact-same `TransitionEventID` replay; a legitimate repeat of the same state edge at the same
`event_time` in a DIFFERENT `delta_cycle` is NOT suppressed."* It is per-run bookkeeping preserved across
rounds (§1 `RoundInitialise`, I-04).

**J3 interaction (why the guard catches EXACT-id replays only).** The step-(0) id embeds `delta_cycle`,
`event_seq`, and BOTH `candidate_id` and `propagation_id`. So a legitimate repeat of the same edge in a
DIFFERENT `delta_cycle`, or a different propagation attempt of one `CandidateID` (different
`PropagationID`), is a DISTINCT id — it misses the registry in step (1) and is APPLIED. The guard is an
exact-identity filter, never a coarse `(MinerID, event_time, old_state, new_state)` filter.

## 3. Scenarios — replay guard (step 1) vs old-state precondition (step 2)

| # | Scenario | `old_state` vs live `miner_state` | id in `transition_event_registry`? | Reaches step (2)? | Outcome | Ground |
|---|---|---|---|---|---|---|
| (a) | **Exact replay after state already changed** (identical `TransitionEventID`; first occurrence already ran step (6)) | mismatch (`WAKING` vs `ACTIVE_HASHING`) | YES | **No** — returns at step (1) | `duplicate_suppressed`; NO precondition failure, NO second residency/energy | §0.9 step (1); TV73 |
| (b) | **Non-replay, matching `old_state`** | match | no | Yes | precondition passes → applied atomically (3)–(8), `transition_record` | §0.9 steps (1)→(2); apply (3)–(8) |
| (c) | **Non-replay, non-matching `old_state`** (stale source) | mismatch | no | Yes | step (2) fails → `RETURN illegal_stale_source` | §0.9 step (2) |
| (d) | **Legitimate same edge, different `delta_cycle`** (same-`event_time` revoke + re-wake, re-completes T5 in `k' > k`) | match (re-wake restored `WAKING`) | no (distinct `delta_cycle`/`event_seq` ⇒ distinct id) | Yes | applied — a fresh residency interval | §0.8 registry note; §0.9 step (0); TV74 |

Only scenario (a) exercises the reordering: the exact replay is suppressed by identity at step (1) and
never reaches the step-(2) old-state check it would otherwise spuriously fail.

## 4. Proof that ordering matters

Let the first (genuine) occurrence of an edge `old_state -> new_state` for `MinerID` at `(event_time,
delta_cycle, event_seq)` run to completion; step (6) has set `miner_state(MinerID) = new_state`, and step
(1) has added the id to `transition_event_registry`. Now the SAME event is redispatched (an exact
replay), carrying the SAME `TransitionEventID` and the SAME declared `old_state`.

- **Actual order (1) before (2).** Step (1) finds the id already in `transition_event_registry` and
  returns `duplicate_suppressed` — WITHOUT reading `miner_state` and WITHOUT charging any boundary. The
  replay is a clean no-op keyed on the IMMUTABLE id, which the intervening state change did not perturb.
- **Hypothetical order (2) before (1).** The old-state check would compare `old_state` against the
  already-mutated `miner_state(MinerID) = new_state`; since `old_state != new_state`, the guard fires and
  returns `illegal_stale_source` — misclassifying a benign exact-id duplicate (scenario (a)) as an
  illegal stale transition.

Because an exact replay ALWAYS arrives after the first event changed `miner_state`, any old-state check
evaluated before the replay guard would spuriously fail it. Keying suppression on the immutable
`TransitionEventID` and checking it FIRST is therefore necessary and sufficient to classify the replay
correctly. ∎

## 5. Worked example (matching TV73)

Preconditions (TV73): the first event applied `WAKING -> ACTIVE_HASHING` (T5, `reason = ramp_complete`)
via `WakeCompleteEvent` (§0.10), so `miner_state(MinerID) = ACTIVE_HASHING`. The IDENTICAL
`TransitionEventID` — same `event_time`, `delta_cycle`, `event_seq`, `MinerID`, `old_state = WAKING`,
`new_state = ACTIVE_HASHING`, `reason`, `AssignmentID`, `assignment_version`, candidate ids — is replayed.

Trace:
1. Step (0) rebuilds the id from the full envelope; it equals the id the first occurrence recorded.
2. Step (1) finds it in `transition_event_registry` and returns `duplicate_suppressed` — BEFORE step (2).
3. Step (2) (the `old_state = miner_state(MinerID)` check) is NEVER reached; the replay does not fail the
   precondition even though live `miner_state` is now `ACTIVE_HASHING`, not `WAKING`.
4. Steps (3)–(8) do not run: no second `residency_ledger` interval, no second `E_transition`, no census
   recompute.

Expected (TV73): the replay is suppressed by identity, not rejected as `illegal_stale_source`; no second
boundary is charged (I19 preserved). Reqs: **J2**, J3, I19.

## 6. Reconciliation with I5 / I6 / I19

- **I19 (single-owner, no-double-count residency).** A suppressed replay returns at step (1) before step
  (3), so it opens/closes NO `residency_ledger` interval; the `ACTIVE_HASHING`/`t_hash` boundary is
  crossed exactly once per genuine edge. A legitimate scenario-(d) recurrence opens a fresh, distinct
  interval — a real second occupancy, not a double count of one.
- **I5 (durations reconcile to `T`).** Neither the suppressed replay (no interval) nor the distinct
  recurrence (a real, separate interval) perturbs the OPEN-at-entry / CLOSE-at-exit partition, so
  `Σ_states t_state,i = T = 10,000 s` with no gap or overlap is unaffected.
- **I6 (per-miner energies sum exactly).** The replay charges no second `E_transition`/`E_coordination`
  (step (4) is not reached); boundary energies stay one-shot per genuine crossing, so `E_i` holds with
  exact equality and the A1 baseline is unchanged.

## 7. Acceptance-style PASS checklist

| # | Check | Result | Ground |
|---|---|---|---|
| C1 | Replay guard (`IF TransitionEventID in transition_event_registry: RETURN duplicate_suppressed`) is step (1), evaluated BEFORE the old-state precondition | PASS | §0.9 step (1) precedes step (2) |
| C2 | `old_state = miner_state(MinerID)` is NOT a top-level precondition; checked in step (2) for a NON-replay only | PASS | §0.9 `PRECONDITIONS` note; step (2) |
| C3 | Exact replay after state changed → `duplicate_suppressed` at step (1), NO precondition failure, NO second residency/energy | PASS | §0.9 step (1); TV73 |
| C4 | Non-replay with matching `old_state` → applied atomically (3)–(8) | PASS | §0.9 steps (1)→(2)→(3)–(8) |
| C5 | Non-replay with non-matching `old_state` → `illegal_stale_source` | PASS | §0.9 step (2) |
| C6 | Legitimate same edge in a different `delta_cycle` → distinct id (embeds `delta_cycle`/`event_seq`/both candidate ids) → applied | PASS | §0.8 registry note; §0.9 step (0); TV74 |
| C7 | Ordering is load-bearing: an old-state-first order misclassifies scenario (a) as `illegal_stale_source` | PASS | §4 proof |
| C8 | Residual top-level precondition is edge legality only, distinct from old-state matching | PASS | §0.9 `PRECONDITIONS` (`STAGE_01_MINER_STATE_MACHINE.md §3`) |
| C9 | Reconciles with I5 / I6 / I19; A1 baseline unchanged; no new consensus feature | PASS | §6; I5/I6/I19; A1 = 8.420833333 kWh |

---

## Result

**Result: TRANSITION REPLAY AUDIT (Stage 1J): PASS** — in `ApplyMinerStateTransition` (§0.9) the
exact-replay suppression check is step (1) and returns `duplicate_suppressed` STRICTLY BEFORE the
old-state precondition `old_state = miner_state(MinerID)`, which is step (2) and runs for a NON-replay
only; because an exact replay necessarily arrives after the first genuine event set `miner_state <-
new_state` (step (6)), an old-state-first order would spuriously reject it as `illegal_stale_source`,
whereas keying suppression on the immutable `TransitionEventID` (embedding `delta_cycle`, `event_seq`,
and both candidate ids, §0.8/step (0)) and checking it first makes the replay a clean no-op charging no
second residency boundary or energy (TV73), while a legitimate same-edge repeat in a different
`delta_cycle` has a DISTINCT id and is applied (TV74); the result reconciles with I5/I6/I19, leaves the
A1 baseline (8.420833333 kWh) unchanged, and adds no new consensus feature.
