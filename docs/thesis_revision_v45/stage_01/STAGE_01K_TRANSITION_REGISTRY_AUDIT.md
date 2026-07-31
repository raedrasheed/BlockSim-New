# Stage 1K — Transition Registry Audit (K5)

A structural audit of Stage-1K correction **K5** (register ONLY applied transitions) in the **PoCol**
protocol pseudocode (`STAGE_01_PROTOCOL_PSEUDOCODE.md`): in `ApplyMinerStateTransition` (§0.9) the
`TransitionEventID` enters `applied_transition_registry` ONLY inside the atomic apply — step (5) — after
the replay guard (step (2)), the old-state validation (step (3)), and the legality/envelope validation
(step (4)) have all passed. A suppressed replay or a rejected (stale / illegal / malformed) transition is
NEVER added to the applied registry; a rejection is recorded in the SEPARATE `transition_rejection_log`
(§0.8) with its reason. This document is documentation only; it audits wording and control structure,
describes only the idle policy within PoCol, introduces no new consensus feature, and claims **no**
security, fairness, energy, or incentive property. The A1 baseline (`8.420833333 kWh`) is unchanged.

---

## 1. The corrected-away problem (a rejected transition polluting the registry)

In the earlier design the id was ADDed to the registry immediately AFTER the replay guard and BEFORE the
old-state and legality/envelope validations (the pre-K5 §0.9 ordering: replay guard, then `ADD
TransitionEventID to transition_event_registry`, then the old-state precondition). The defect: a
transition whose source is stale, whose edge is illegal, or whose envelope is malformed would ALREADY be
in the registry when the validation that rejects it runs. Two consequences follow. First, the registry no
longer means "successfully applied" — it holds ids for transitions that were rejected and never applied.
Second, a later EXACT replay of that rejected edge would find its id already present and be wrongly
reported `duplicate_suppressed`, a rejected transition masquerading as an applied one. K5 removes both by
moving the single `ADD` into the atomic apply: an id enters the registry if and only if the transition is
actually applied.

## 2. Mechanism (register-inside-the-atomic-apply; validate first)

`ApplyMinerStateTransition` (§0.9, F6) is the SOLE writer of `miner_state` (§0.3), the SOLE owner of
`residency_ledger` accounting and one-shot boundary energy (I5/I6/I19), and a writer of the security
census bookkeeping (I-01/J1). Its ordered steps, quoting the actual §0.9 step labels:

```
# (1) J2/J3/K5 EVENT-IDENTITY. Build the immutable TransitionEventID from the FULL envelope.
SET TransitionEventID <- (event_time, delta_cycle, event_seq, MinerID, old_state, new_state, reason,
                          AssignmentID(assignment_ref), assignment_version(assignment_ref),
                          candidate_id, propagation_id)
# (2) K5 REPLAY GUARD — check the APPLIED registry (no old-state read, no charge).
IF TransitionEventID in applied_transition_registry:
  RETURN duplicate_suppressed
# (3) K5 VALIDATE OLD-STATE (non-replay). A stale source is REJECTED and logged, NOT applied.
IF old_state != NONE AND old_state != miner_state(MinerID):
  RECORD transition_rejection_log(TransitionEventID, reason_rejected = stale_source,
                                  observed_state = miner_state(MinerID))
  RETURN illegal_stale_source
# (4) K5 VALIDATE LEGALITY + ENVELOPE. Illegal edge / incomplete envelope / missing candidate ids:
#     REJECT, log, NOT apply.
IF (old_state -> new_state) is NOT a legal miner transition
   OR envelope is incomplete (missing event_time/delta_cycle/event_seq)
   OR (candidate-triggered AND (candidate_id = null OR propagation_id = null)):
  RECORD transition_rejection_log(TransitionEventID, reason_rejected = illegal_or_malformed)
  RETURN illegal_transition
# (5) K5 ATOMIC APPLY — the id enters the APPLIED registry ONLY here.
ATOMICALLY:
  ADD TransitionEventID to applied_transition_registry           # (5)  only APPLIED transitions registered
  # then, in ONE atomic step: (5a) close old / open new residency (I5/I6/I19/K3); (5b) one-shot
  # E_transition/E_coordination (I6); (5c) assignment status per edge (J7); (5d) SET miner_state <- new;
  # (5e/5f) recompute H_active/H_honest/H_adversarial/q_adv + census (I17/I-01/J1/J8).
```

**Ordering.** Step (1) builds the immutable id; step (2) consults `applied_transition_registry` and, on a
hit, returns `duplicate_suppressed` before any state read or charge; step (3) rejects a stale source into
`transition_rejection_log` (`stale_source`) → `illegal_stale_source`; step (4) rejects an illegal edge, an
incomplete envelope, or a candidate-triggered call missing `candidate_id`/`propagation_id` into
`transition_rejection_log` (`illegal_or_malformed`) → `illegal_transition`. Control reaches the atomic
apply of step (5) — the ONLY site of `ADD TransitionEventID to applied_transition_registry` — only when
(2) misses and (3) and (4) both pass.

**Registry fields (§0.8).** `applied_transition_registry` is *"set of TransitionEventIDs that were
SUCCESSFULLY APPLIED (K5, formerly `transition_event_registry`) … enters ONLY inside … the atomic apply; a
suppressed replay or a rejected (stale/illegal/malformed) event is NEVER here. Replay suppression checks
THIS set."* `transition_rejection_log` is *"K5 — log of rejected transitions … SEPARATE from
`applied_transition_registry` (rejections are never registered as applied)."* Both are per-run bookkeeping
preserved across rounds (§1 `RoundInitialise`, I-04).

## 3. Outcome → registry effect → energy table

| Outcome | §0.9 step that returns | In `applied_transition_registry`? | In `transition_rejection_log`? | Residency / energy charged? | Return value |
|---|---|---|---|---|---|
| **Exact replay** (id already applied) | (2) | already present from the genuine apply; **no new add** | No | **No** (returns before any charge) | `duplicate_suppressed` |
| **Stale source** (`old_state != miner_state`) | (3) | **No** | Yes — `stale_source` | **No** | `illegal_stale_source` |
| **Illegal / malformed** (illegal edge, incomplete envelope, or missing candidate ids) | (4) | **No** | Yes — `illegal_or_malformed` | **No** | `illegal_transition` |
| **Applied** (all checks pass) | (5) | **Yes** — added inside the atomic apply | No | **Yes** — `E_transition`/`E_coordination` + residency boundary | `transition_record` |

Only the last row adds to `applied_transition_registry` and charges boundary energy / a `residency_ledger`
interval; the two rejected rows are the only rows that write `transition_rejection_log`; the replay row
writes neither structure.

## 4. Proof that only applied transitions are registered, and rejections never are

The sole statement that mutates `applied_transition_registry` by insertion is `ADD TransitionEventID to
applied_transition_registry`, inside the ATOMIC apply of step (5). Control reaches step (5) only after:
step (2) MISSED (the id was not an already-applied replay), step (3) PASSED (`old_state` matches the live
`miner_state`, or `old_state = NONE`), and step (4) PASSED (the edge is legal and the envelope is
complete). Each of the three preceding returns — `duplicate_suppressed` (step 2), `illegal_stale_source`
(step 3), `illegal_transition` (step 4) — exits STRICTLY BEFORE step (5), hence before any `ADD`.
Therefore every id in `applied_transition_registry` is an id whose transition passed (2), (3), and (4) and
executed the atomic apply: **only applied transitions are registered.** Conversely, a stale source (step 3)
and an illegal/malformed transition (step 4) each return after writing `transition_rejection_log` and
before step (5)'s `ADD`, so **a rejected transition is written only to `transition_rejection_log`, never to
`applied_transition_registry`** — the two structures are disjoint by construction. Because step (2)'s
replay guard reads `applied_transition_registry`, which now holds applied ids only, no rejected edge can be
mistaken for an applied one on a later replay. ∎

## 5. Worked example A — matching TV87 (stale source rejected, absent from applied)

Preconditions (TV87): `ApplyMinerStateTransition` is called with `old_state = WAKING` but
`miner_state(M) = ACTIVE_HASHING` already — a stale source that is NOT an exact replay.

Trace:
1. Step (1) builds the id; step (2) finds it NOT in `applied_transition_registry` (not a replay).
2. Step (3) evaluates `old_state (WAKING) != miner_state(M) (ACTIVE_HASHING)` → TRUE: `RECORD
   transition_rejection_log(TransitionEventID, reason_rejected = stale_source, observed_state =
   ACTIVE_HASHING)` and `RETURN illegal_stale_source`.
3. The atomic apply of step (5) never runs: the id is NEVER added to `applied_transition_registry`; no
   `residency_ledger` interval opens/closes; no `E_transition`/`E_coordination`; no census recompute.

Expected (TV87): the stale transition is rejected, logged in `transition_rejection_log` with reason
`stale_source`, and absent from `applied_transition_registry`; no residency/energy is charged. Reqs:
**K5**, J2.

## 6. Worked example B — matching TV88 (exact replay suppressed)

Preconditions (TV88): a transition was successfully applied, so its `TransitionEventID` is in
`applied_transition_registry` (added in step (5) of the genuine apply); the IDENTICAL `TransitionEventID`
is now replayed.

Trace:
1. Step (1) rebuilds the id; it equals the id the genuine apply recorded. Step (2) finds it in
   `applied_transition_registry` → `RETURN duplicate_suppressed`, BEFORE the step (3) old-state check.
2. Steps (3)–(5) do not run: no old-state read, no second `applied_transition_registry` add, no second
   `residency_ledger` boundary, no second `E_transition`, no census recompute (I19 preserved).

Expected (TV88): the exact replay is suppressed by identity; no second residency boundary or energy.
Reqs: **K5**, J2, I19.

## 7. Reconciliation with I5 / I6 / I19

Because a suppressed replay (step 2) and both rejections (steps 3, 4) return before step (5), none opens or
closes a `residency_ledger` interval and none charges a one-shot `E_transition`/`E_coordination`: the
`ACTIVE_HASHING`/`t_hash` boundary is crossed exactly once per genuine apply (**I19**), the
OPEN-at-entry / CLOSE-at-exit partition still gives `Σ_states t_state,i = T = 10,000 s` (**I5**), and
`E_i` holds with exact equality so the A1 baseline (`8.420833333 kWh`) is unchanged (**I6**).

## 8. Acceptance-style PASS checklist

| # | Check | Result | Ground |
|---|---|---|---|
| C1 | The single `ADD TransitionEventID to applied_transition_registry` is inside the atomic apply (step 5), never earlier | PASS | §0.9 step (5) |
| C2 | Replay guard (step 2) reads `applied_transition_registry` and returns `duplicate_suppressed` before any charge | PASS | §0.9 step (2) |
| C3 | Stale source (step 3) → `transition_rejection_log(…, stale_source)` + `illegal_stale_source`; illegal/malformed (step 4) → `transition_rejection_log(…, illegal_or_malformed)` + `illegal_transition`; neither in applied registry | PASS | §0.9 steps (3),(4); TV87 |
| C5 | Applied transition (all checks pass) → id added in step (5), boundary energy + residency charged, `transition_record` | PASS | §0.9 step (5)/(5a)/(5b) |
| C6 | Exact replay of an applied id → suppressed, no second registry add, no second residency/energy | PASS | §0.9 step (2); TV88; I19 |
| C7 | `applied_transition_registry` and `transition_rejection_log` are SEPARATE; rejections never registered as applied | PASS | §0.8 registry notes; §4 proof |
| C8 | Corrected-away pollution impossible: a rejected edge can never later be mis-suppressed as applied | PASS | §1; §4 proof |
| C9 | Reconciles with I5 / I6 / I19; A1 baseline unchanged; no new consensus feature | PASS | §7; I5/I6/I19; A1 = 8.420833333 kWh |

---

## Result

**Result: TRANSITION REGISTRY AUDIT (Stage 1K): PASS** — in `ApplyMinerStateTransition` (§0.9) the
`TransitionEventID` enters `applied_transition_registry` ONLY inside the atomic apply (step (5)), reached
solely after the replay guard (step (2)) misses and the old-state validation (step (3)) and the
legality/envelope validation (step (4)) both pass; a stale source is recorded in the SEPARATE
`transition_rejection_log` with reason `stale_source` and returns `illegal_stale_source` (TV87), an
illegal edge / incomplete envelope / missing-candidate-id call is recorded there with reason
`illegal_or_malformed` and returns `illegal_transition`, and an exact replay of an already-applied id
returns `duplicate_suppressed` before any charge (TV88) — so a rejected or suppressed transition is NEVER
in the applied registry, the two structures are disjoint by construction, and the earlier
add-before-validate pollution (a rejected edge later mis-suppressed as applied) is eliminated; the result
reconciles with I5/I6/I19, leaves the A1 baseline (8.420833333 kWh) unchanged, and adds no new consensus
feature.
