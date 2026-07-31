# Stage 1I — Transition Identity Audit (I-03)

A structural audit of Stage-1I correction **I-03** (event-identity idempotence) in the **PoCol**
protocol pseudocode (`STAGE_01_PROTOCOL_PSEUDOCODE.md`): miner-state transition idempotence is keyed
by an immutable `TransitionEventID` built in step (0) of `ApplyMinerStateTransition` (§0.9) from the
FULL event envelope (§0.2), so that only an EXACT-same-id replay is suppressed while a legitimate
repeat of the same state edge at the same `event_time` in a DIFFERENT `delta_cycle` is applied. This
document is documentation only; it audits wording and control structure, describes only the idle
policy within PoCol, introduces no new consensus feature, and claims **no** security, fairness, or
incentive property.

---

## 1. The corrected-away problem (over-suppression on a coarse key)

Suppose duplicate transitions were suppressed by the coarse key `(MinerID, event_time, old_state,
new_state)`. Then a **legitimate** second occurrence of the SAME state edge for the SAME miner at the
SAME wall-clock `event_time` would be wrongly discarded whenever it recurs in a different causal
generation. The canonical case (§0.7-H2 delta-cycle scheduling): at `event_time = t` a miner completes
`WAKING → ACTIVE_HASHING` (T5) in `delta_cycle = k`; a same-`t` revoke + re-wake sequence returns it to
`WAKING` and it again completes `WAKING → ACTIVE_HASHING` (T5) in a later `delta_cycle = k' > k`. Both
edges are legal miner transitions (`STAGE_01_MINER_STATE_MACHINE.md §3`) and are two distinct causal
events, but they share `(MinerID, t, WAKING, ACTIVE_HASHING)`. A coarse-key check would suppress the
second — dropping a real residency interval and a real boundary crossing, corrupting I5/I6 accounting.

## 2. Mechanism (immutable `TransitionEventID`, suppression BEFORE any residency/energy step)

`ApplyMinerStateTransition` (§0.9, F6) is the SOLE owner of residency accounting, one-shot transition
energy, and the census recompute (§0.3). Its step (0) builds the id from the full envelope and checks
the registry before opening any interval or charging any energy:

```
# (0) I-03 EVENT-IDENTITY IDEMPOTENCE.
SET TransitionEventID <- (event_time, current_delta_cycle, seq, MinerID, old_state, new_state, reason,
                          AssignmentID(assignment_ref), assignment_version(assignment_ref),
                          CandidateID(candidate_ref)?, PropagationID(candidate_ref)?)   # immutable
IF TransitionEventID in transition_event_registry:
  RETURN duplicate_suppressed        # exact replay only; charges NO second residency boundary or energy
ADD TransitionEventID to transition_event_registry
```

The id embeds, at minimum: `event_time`, `current_delta_cycle`, event `seq`, `MinerID`, `old_state`,
`new_state`, `reason`, `AssignmentID`, `assignment_version`, and (where applicable) `CandidateID` and
`PropagationID`. These fields are exactly the immutable envelope of §0.2
(`{ event_type, event_time, delta_cycle, microphase, RoundID, TemplateID, CandidateID?, PropagationID?,
MinerID?, AssignmentID?, assignment_version?, seq }`); `delta_cycle` is the causal generation within
one `event_time` and `seq` is the strictly monotonic per-run creation counter (§0.2, §0.7a).

**Ordering.** The registry check and `RETURN duplicate_suppressed` occur in step (0), STRICTLY BEFORE:
step (1) `CLOSE residency(MinerID, old_state)`, step (2) `OPEN residency(MinerID, new_state)`, step (3)
`RECORD E_transition/E_coordination`, step (5) `SET miner_state`, and step (6) the census recompute. So
a suppressed replay opens/closes NO residency interval and charges NO boundary energy.

**Registry field.** `transition_event_registry` (§0.8, `RoundContext registries`) is *"set of
`TransitionEventID`s already applied (I-03)"*; its field note states `ApplyMinerStateTransition`
*"suppresses ONLY the exact-same `TransitionEventID` replay; a legitimate repeat of the same state edge
at the same `event_time` in a DIFFERENT `delta_cycle` is NOT suppressed."* It is per-run bookkeeping —
`RoundInitialise` initialises it ONCE at run start (`prior_state = null`) and PRESERVES it across rounds
(§1, I-04), so replay-suppression state is never dropped at a round boundary.

**Audit record.** On an applied transition, step (6) executes
`RECORD transition_audit(TransitionEventID, MinerID, old_state, new_state, event_time,
current_delta_cycle, reason, assignment_ref, candidate_ref)` (§0.9) — the `TransitionEventID` is
recorded, so every applied edge is auditable by its immutable identity.

## 3. OLD coarse key vs NEW `TransitionEventID` — two scenarios

The OLD key is `(MinerID, event_time, old_state, new_state)`. The NEW key is the full step-(0)
`TransitionEventID`. Row A is the legitimate same-edge recurrence (TV64); row B is an exact replay
(TV65).

| Scenario | Two occurrences differ in… | OLD key `(MinerID, event_time, old_state, new_state)` | NEW key `TransitionEventID` (full envelope) |
|---|---|---|---|
| **A. Same edge, same `event_time = t`, different `delta_cycle`** (e.g. two legal `WAKING→ACTIVE_HASHING` T5 edges, one in `delta_cycle k`, one in `k' > k`, after a same-`t` revoke + re-wake) | `current_delta_cycle` (`k` vs `k'`) and `seq` | Keys are IDENTICAL → the second is **suppressed** — **WRONG** (a real edge and residency interval are lost) | Ids DIFFER (distinct `current_delta_cycle` and `seq`) → **both apply** — **CORRECT**; each opens a fresh `ACTIVE_HASHING` residency interval via steps (1)–(2) |
| **B. Exact replay** (identical `event_time`, `current_delta_cycle`, `seq`, `MinerID`, `old_state`, `new_state`, `reason`, `AssignmentID`, `assignment_version`, ids — e.g. a duplicated dispatch) | nothing (all id fields equal) | Keys identical → **suppressed** (correct outcome) | Id already in `transition_event_registry` → `RETURN duplicate_suppressed` in step (0) → **suppressed**; unlike OLD it returns BEFORE step (1), charging **no second residency boundary and no second `E_transition`/`E_coordination`** |

Both keys reach the correct verdict in row B; only the NEW key is correct in row A, and only the NEW key
guarantees the row-B no-op crosses no residency/energy boundary.

## 4. Proof that idempotence is safe

Let an *occurrence* of a miner-state transition be one `ApplyMinerStateTransition` call, tagged by its
step-(0) `TransitionEventID` id. Two claims:

1. **A replay is EXACTLY a collision on the full id.** Suppression fires iff `id ∈
   transition_event_registry`, i.e. iff every field of the id — `event_time`, `current_delta_cycle`,
   `seq`, `MinerID`, `old_state`, `new_state`, `reason`, `AssignmentID`, `assignment_version`, and any
   `CandidateID`/`PropagationID` — equals that of an already-applied occurrence. Equality on all fields,
   including the strictly monotonic per-run `seq`, means the two calls are the SAME dispatched event
   (a genuine replay), not two distinct events. Hence suppression is sound: it never discards a distinct
   event.

2. **Two distinct legitimate occurrences NEVER collide.** `seq` is a strictly monotonic per-run
   creation counter assigned after the deterministic order is established (§0.2, §0.7a); distinct events
   therefore carry distinct `seq`, so their ids differ in at least that field (and, for the row-A case,
   also in `current_delta_cycle`, since `k ≠ k'`). A distinct occurrence is thus never in the registry
   when it is applied. Hence suppression is complete: it never fails to apply a genuine new edge.

Together: `id ∈ transition_event_registry` is an exact characterisation of "this precise event was
already applied". Idempotence is therefore safe — a replay is a no-op and a legitimate distinct
occurrence always applies — because the key is the full immutable identity, not the coarse
`(MinerID, event_time, old_state, new_state)` tuple.

## 5. Reconciliation with I5 / I6 / I19

- **I19 (single-owner, no-double-count residency).** A suppressed replay returns in step (0) before
  step (1)/(2), so it opens/closes NO `residency_ledger` interval; the `ACTIVE_HASHING`/`t_hash`
  boundary is crossed exactly once per genuine edge, preserving I19's single boundary-to-boundary
  interval. A legitimate row-A recurrence opens a fresh, distinct interval — a real second occupancy,
  not a double count of one.
- **I5 (durations reconcile to `T`).** Because neither the replay (no interval) nor the legitimate
  recurrence (a real, separate interval) perturbs the OPEN-at-entry / CLOSE-at-exit partition,
  `Σ_states t_state,i = T = 10,000 s` with no gap or overlap is unaffected.
- **I6 (per-miner energies sum exactly).** The replay charges no second `E_transition`/`E_coordination`;
  boundary energies remain one-shot per genuine crossing (§0.9 step (3)), added on top of residency
  energies and never double-counted, so `E_i` holds with exact equality.

## 6. Acceptance-style PASS checklist

| # | Check | Result | Ground |
|---|---|---|---|
| C1 | `TransitionEventID` built from the FULL envelope (incl. `event_time`, `current_delta_cycle`, `seq`, `MinerID`, `old_state`, `new_state`, `reason`, `AssignmentID`, `assignment_version`, `CandidateID?`, `PropagationID?`) | PASS | §0.9 step (0); §0.2 event envelope |
| C2 | Suppression check + `RETURN duplicate_suppressed` occur BEFORE any residency/energy step | PASS | §0.9 step (0) precedes steps (1)–(3), (5)–(6) |
| C3 | Legitimate same edge in a different `delta_cycle` is NOT suppressed (both apply, each a fresh residency interval) | PASS | §0.8 `transition_event_registry` note; §0.9 step (0); TV64 |
| C4 | Exact replay is suppressed and charges NO second `E_transition`/`E_coordination` and NO second residency boundary | PASS | §0.9 step (0) comment "charges NO second residency boundary or energy"; TV65 |
| C5 | Distinct occurrences never collide (differ in `current_delta_cycle` and/or strictly monotonic `seq`) | PASS | §4 proof; §0.2 / §0.7a `seq` monotonic |
| C6 | `TransitionEventID` recorded in `transition_audit` on every applied edge | PASS | §0.9 step (6) `RECORD transition_audit(TransitionEventID, …)` |
| C7 | Envelope completeness — id fields are exactly the immutable §0.2 envelope | PASS | §0.2 envelope vs §0.9 step (0) tuple |
| C8 | `transition_event_registry` persists across rounds (per-run, keyed by run-monotonic id) | PASS | §0.8 field note; §1 `RoundInitialise` (I-04, preserve on `prior_state ≠ null`) |
| C9 | Reconciles with I5 / I6 / I19; A1 baseline unchanged; no new consensus feature | PASS | §5; I5/I6/I19; A1 = 8.420833333 kWh |

---

## Result

**TRANSITION IDENTITY AUDIT (Stage 1I): PASS** — miner-state transition idempotence is keyed by the
immutable `TransitionEventID` built in step (0) of `ApplyMinerStateTransition` (§0.9) from the full
`event_time`/`current_delta_cycle`/`seq`/`MinerID`/`old_state`/`new_state`/`reason`/`AssignmentID`/
`assignment_version`/`CandidateID?`/`PropagationID?` envelope (§0.2), so a legitimate repeat of the same
state edge at the same `event_time` in a different `delta_cycle` has a DISTINCT id and is applied (each
opening a fresh residency interval), while an EXACT-same-id replay returns `duplicate_suppressed` before
any residency interval is opened or any `E_transition`/`E_coordination` is charged; the id is recorded in
`transition_audit`, the check is sound and complete (§4), and the result reconciles with I5/I6/I19 and
leaves the A1 baseline (8.420833333 kWh) unchanged with no new consensus feature.
