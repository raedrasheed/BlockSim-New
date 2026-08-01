# Stage 1AA — `STATE_ONLY_ROLLBACK` Legal-Tuple Guard Audit (AA5)

This audit verifies correction **AA5**: the `assignment_effect_policy = STATE_ONLY_ROLLBACK` value — which suppresses the
edge's assignment-status effect in the atomic apply — is now bound to an **executable legal-tuple guard** inside
`ApplyMinerStateTransition`. `STATE_ONLY_ROLLBACK` is legal IFF the EXACT `T12` `ValidationAbort` rollback tuple holds
(`WAKING -> OFFLINE`, `reason = validation_abort`, an exact non-null `assignment_ref`, and a matching wake-origin binding).
Any other use is rejected as `illegal_transition` with NO state / residency / one-shot energy / census / assignment
mutation and NO registry entry, because the guard sits BEFORE the atomic apply. No non-rollback caller can smuggle
`STATE_ONLY_ROLLBACK` onto `T5` / `T21` / any other edge to bypass that edge's assignment effects: every non-rollback
caller binds the signature default `EDGE_DEFAULT`, and the sole accepting call site is `AbortPendingWakeForRollback`,
whose invocation satisfies the tuple exactly and which additionally performs its own wake-origin pre-check.

Scope is documentation-only. The algorithm is **PoCol**; the mechanism is the idle policy within PoCol. The A1 baseline
`8.420833333 kWh` is unchanged. No Stage-1A–1Z historical artifact is modified. All lines are quoted from the current
normative documents; line anchors are approximate.

Sources of truth (read-only): `STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_MINER_STATE_MACHINE.md`.

---

## 1. The AA5 legal-tuple guard — step (4b) — PASS

### 1.1 The conjunctive guard and its rejection/return

`ApplyMinerStateTransition` (`STAGE_01_PROTOCOL_PSEUDOCODE.md`, `PROCEDURE ApplyMinerStateTransition`, line 1109) carries
the AA5 guard as step **(4b)**. Quoting it verbatim (lines 1194–1202):

```
1194    # (4b) AA5 LEGAL STATE_ONLY_ROLLBACK TUPLE. STATE_ONLY_ROLLBACK (which suppresses the edge's assignment effect, 5c)
1195    #     is legal IFF the EXACT ValidationAbort rollback tuple holds; any other use is rejected with NO mutation, so no
1196    #     caller can use it on T5 / T21 / any other edge to bypass assignment effects.
1197    IF assignment_effect_policy = STATE_ONLY_ROLLBACK
1198       AND NOT (old_state = WAKING AND new_state = OFFLINE AND reason = validation_abort
1199                AND assignment_ref is exact and non-null
1200                AND waking_origin_assignment_ref[MinerID] = assignment_version_ref(AssignmentID(assignment_ref), assignment_version(assignment_ref))):
1201      RECORD transition_rejection_log(TransitionEventID, reason_rejected = illegal_state_only_rollback_tuple)   # AA5
1202      RETURN illegal_transition(TransitionEventID)   # AA5: NO state/residency/energy/census/assignment mutation
```

The guard fires only when `assignment_effect_policy = STATE_ONLY_ROLLBACK` (line 1197). It is legal exactly when the
five-way conjunction holds (lines 1198–1200):

1. `old_state = WAKING`
2. `new_state = OFFLINE`
3. `reason = validation_abort`
4. `assignment_ref is exact and non-null`
5. `waking_origin_assignment_ref[MinerID] = assignment_version_ref(AssignmentID(assignment_ref), assignment_version(assignment_ref))`

On the NEGATION of that conjunction (`AND NOT (...)`), the guard records
`transition_rejection_log(TransitionEventID, reason_rejected = illegal_state_only_rollback_tuple)` (line 1201) and returns
`illegal_transition(TransitionEventID)` (line 1202). The inline comment on line 1202 states the effect explicitly: NO
state / residency / energy / census / assignment mutation.

This matches the §0.8 AA5 addendum block (lines 903–907), which is the normative statement of the rule:

```
903  # --- AA5 legal STATE_ONLY_ROLLBACK tuple ---
904  # STATE_ONLY_ROLLBACK is legal IFF old_state = WAKING AND new_state = OFFLINE AND reason = validation_abort AND
905  #   assignment_ref is exact and non-null AND waking_origin_assignment_ref[MinerID] = assignment_ref. Any other use returns
906  #   illegal_transition and performs NO mutation. Every non-rollback caller uses EDGE_DEFAULT (the declared signature
907  #   default). No caller can use STATE_ONLY_ROLLBACK on T5 / T21 / any other edge to bypass assignment effects.
```

The addendum's `waking_origin_assignment_ref[MinerID] = assignment_ref` is the same predicate the executable guard writes
as `= assignment_version_ref(AssignmentID(assignment_ref), assignment_version(assignment_ref))` (line 1200): the guard
resolves `assignment_ref` to its canonical exact-version reference before comparison, so the addendum and the executable
form are the same equality.

### 1.2 The guard sits AFTER legality/envelope validation and BEFORE the atomic apply

The guard's position in the procedure is load-bearing: a rejection at (4b) must mutate nothing. The ordering in the
current pseudocode is:

- Step (2) replay guard — line 1178 (returns `duplicate_suppressed` on an exact replay).
- Step (3) old-state validation — lines 1182–1185 (returns `illegal_stale_source`, logged, NOT applied).
- Step (4) legality + envelope validation — lines 1188–1193 (returns `illegal_transition`, logged `illegal_or_malformed`).
- **Step (4b) AA5 legal-tuple guard — lines 1197–1202** (the subject of this audit).
- Step (5) `ATOMICALLY:` atomic apply — begins at line 1204.

The `ATOMICALLY:` block opens at line 1204 and its FIRST action is the registry insert (line 1205):

```
1203    # (5) K5 ATOMIC APPLY. Register-then-apply in ONE atomic step; the id enters the APPLIED registry ONLY here.
1204    ATOMICALLY:
1205      ADD TransitionEventID to applied_transition_registry             # K5: only APPLIED transitions are registered
```

Because step (4b) (line 1197) precedes step (5) (`ATOMICALLY:`, line 1204), an AA5 rejection returns at line 1202 BEFORE
the atomic block runs. Consequently a rejected `STATE_ONLY_ROLLBACK` transition:

- does NOT enter `applied_transition_registry` (that insert is at line 1205, inside step 5);
- does NOT run the residency boundary close/open (5a, lines 1207–1208);
- does NOT record one-shot boundary energy (5b, line 1210);
- does NOT update assignment status (5c, lines 1214–1215);
- does NOT set/clear the wake-origin binding (5c-Z5, lines 1218–1219);
- does NOT write `miner_state` (5d, line 1221);
- does NOT recompute or commit the census (5e/5f, lines 1222–1237).

The trailing NOTE confirms the registry discipline (lines 1250–1252): "the TransitionEventID enters
applied_transition_registry ONLY inside the atomic apply (step 5), so a suppressed replay or a rejected (stale/illegal/
malformed) event is NEVER in the applied registry — rejections go to `transition_rejection_log`." An AA5 rejection is one
such rejection: it is logged to `transition_rejection_log` (line 1201), never to the applied registry.

The guard also sits AFTER the step-(4) legality/envelope check (lines 1188–1193), so a malformed envelope or illegal edge
is caught first by (4); (4b) adds the additional, policy-specific legality condition on top of an already-legal edge.

**Finding: PASS.** Step (4b) is an executable five-way conjunctive guard that rejects any non-tuple use of
`STATE_ONLY_ROLLBACK` with `illegal_state_only_rollback_tuple` and `illegal_transition`, and it is positioned after
legality/envelope validation (step 4) and before the atomic apply (step 5), so a rejection mutates nothing and leaves no
registry entry.

---

## 2. Step (5c) is gated on `EDGE_DEFAULT`; single accepting call site — PASS

### 2.1 The suppressed assignment effect is gated on `EDGE_DEFAULT`

The assignment-status write inside the atomic apply is conditional on the policy. Quoting step (5c) verbatim
(lines 1211–1215):

```
1211      # (5c) Z4 assignment status update where the edge specifies one (J7 terminal status) — ONLY under EDGE_DEFAULT.
1212      #      STATE_ONLY_ROLLBACK (AbortPendingWakeForRollback's ValidationAbort form) performs NO assignment status /
1213      #      custody / coverage mutation here; the caller owns the single canonical close.
1214      IF assignment_effect_policy = EDGE_DEFAULT AND edge specifies an assignment status change:
1215        UPDATE status(assignment_ref) accordingly
```

The gating predicate is exactly `assignment_effect_policy = EDGE_DEFAULT AND edge specifies an assignment status change`
(line 1214). Under `STATE_ONLY_ROLLBACK` the predicate is false, so `UPDATE status(assignment_ref)` (line 1215) is
skipped. This is precisely the effect AA5 protects: the legal `STATE_ONLY_ROLLBACK` tuple exists so the hook can perform
the state-only departure (residency 5a, energy 5b, wake-origin clear 5c-Z5, miner-state 5d, census 5e/5f — all
policy-independent) while suppressing the assignment mutation at 5c, leaving the single canonical close to the caller.
AA5 (§1) ensures this suppression can be requested ONLY on the exact rollback tuple, so it can never be used to skip a
legitimate edge's assignment status change.

### 2.2 The single accepting call site

`STATE_ONLY_ROLLBACK` is passed as an argument at exactly one invocation. The value appears as a call argument only at
line 1874 (the mentions at lines 861–865, 900–907, 1114–1118, 1174, 1194–1202, 1211–1213 are the preamble, signature,
identity note, guard, and step-5c comment; line 1895 is a NOTE). The sole accepting call site is inside
`AbortPendingWakeForRollback` (line 1844), lines 1870–1874:

```
1870      SET tr <- CALL ApplyMinerStateTransition(MinerID, WAKING, OFFLINE,
1871             transition_envelope = rollback_envelope, reason = validation_abort,                      # Y5: authoritative T12 trigger
1872             assignment_ref = assignment_version_ref(AssignmentID, assignment_version),               # Y2/X2: EXACT version, never null
1873             candidate_id = null, propagation_id = null,
1874             assignment_effect_policy = STATE_ONLY_ROLLBACK)   # Z4: state-only; the caller owns the assignment close
```

Every OTHER caller of `ApplyMinerStateTransition` omits the parameter and therefore binds the signature default
`assignment_effect_policy = EDGE_DEFAULT` (line 1114):

```
1114          assignment_effect_policy = EDGE_DEFAULT    # Z4: EDGE_DEFAULT (apply the edge's assignment-status change) | STATE_ONLY_ROLLBACK
```

The default is executable — omission binds `EDGE_DEFAULT` by construction, not by prose convention — so no non-rollback
transition can suppress step (5c). Combined with the AA5 guard (§1), a caller cannot even pass `STATE_ONLY_ROLLBACK`
explicitly on a non-rollback edge: the guard rejects it before step (5) runs.

**Finding: PASS.** Step (5c)'s assignment-status update is gated on `assignment_effect_policy = EDGE_DEFAULT`;
`STATE_ONLY_ROLLBACK` suppresses it. `STATE_ONLY_ROLLBACK` is passed at exactly one call site (line 1874, inside
`AbortPendingWakeForRollback`); all other callers bind the `EDGE_DEFAULT` signature default.

---

## 3. `AbortPendingWakeForRollback`'s call exactly satisfies the tuple; its own wake-origin pre-check — PASS

The single accepting call site must itself satisfy the AA5 tuple, or the guard would reject the legitimate rollback.
Element-by-element, the call at lines 1870–1874 supplies each conjunct of the guard (lines 1198–1200):

| AA5 tuple conjunct (line) | Value at the call site (line) | Satisfied |
|---|---|---|
| `old_state = WAKING` (1198) | `ApplyMinerStateTransition(MinerID, WAKING, OFFLINE, ...)` — `old_state = WAKING` (1870) | yes |
| `new_state = OFFLINE` (1198) | `... WAKING, OFFLINE, ...` — `new_state = OFFLINE` (1870) | yes |
| `reason = validation_abort` (1198) | `reason = validation_abort` (1871) | yes |
| `assignment_ref is exact and non-null` (1199) | `assignment_ref = assignment_version_ref(AssignmentID, assignment_version)` — EXACT version, never null (1872) | yes |
| `waking_origin_assignment_ref[MinerID] = assignment_version_ref(AssignmentID(assignment_ref), assignment_version(assignment_ref))` (1200) | pre-checked equal at lines 1864–1865 before the call | yes |
| `assignment_effect_policy = STATE_ONLY_ROLLBACK` (1197) | `assignment_effect_policy = STATE_ONLY_ROLLBACK` (1874) | yes (this is the policy the guard governs) |

The call's `assignment_ref` (line 1872) is `assignment_version_ref(AssignmentID, assignment_version)`; the guard resolves
its equality conjunct (line 1200) to `assignment_version_ref(AssignmentID(assignment_ref), assignment_version(assignment_ref))`,
which is the same canonical exact-version reference. Because `waking_origin_assignment_ref[MinerID]` is SET on WAKING
entry to that exact version and CLEARED on WAKING departure (step 5c-Z5, lines 1216–1219), the equality holds for a
correctly woken miner and the guard admits the transition.

`AbortPendingWakeForRollback` also performs its OWN wake-origin pre-check before making the call, so a mismatch never
reaches the hook. Lines 1864–1866:

```
1864    IF miner_state(MinerID) = WAKING:
1865      IF waking_origin_assignment_ref[MinerID] != assignment_version_ref(AssignmentID, assignment_version):   # Z5: exact wake-origin binding
1866        RETURN wake_abort_failed(MinerID = MinerID, AssignmentID = AssignmentID, reason = waking_origin_mismatch)   # Z5: do NOT depart an unrelated WAKING miner
```

This is defence in depth: on a wake-origin mismatch the operation returns `wake_abort_failed(reason = waking_origin_mismatch)`
and departs no miner (line 1866), so the hook is not even invoked; and if some future caller invoked the hook with a
mismatch directly, the AA5 guard's fifth conjunct (line 1200) would still reject it. The operation's NOTE records the same
guarantee (lines 1893–1898): it "verifies the exact wake-origin binding `waking_origin_assignment_ref[MinerID]` before
departing (Z5 — a mismatch returns `wake_abort_failed` and departs no miner)" and departs a still-WAKING miner "via the
LEGAL T12 ValidationAbort trigger with `assignment_effect_policy = STATE_ONLY_ROLLBACK`."

**Finding: PASS.** The sole `STATE_ONLY_ROLLBACK` call site (`AbortPendingWakeForRollback`, lines 1870–1874) supplies
every conjunct of the AA5 tuple exactly, and the operation performs its own `waking_origin_assignment_ref` pre-check
(lines 1864–1866) before the call, so a mismatch returns `wake_abort_failed` and departs no miner.

---

## 4. Illegal-use cases the guard rejects — PASS

Each conjunct of the guard (lines 1197–1200) is independently necessary; violating any one drives the `AND NOT (...)`
predicate true and yields `illegal_state_only_rollback_tuple` / `illegal_transition` with no mutation (lines 1201–1202).
Because step (4b) precedes step (5) (§1.2), every rejection below mutates nothing and leaves no applied-registry entry.

| # | Illegal use | Which conjunct fails (line) | Result |
|---|---|---|---|
| 1 | Wrong edge — `old_state != WAKING` and/or `new_state != OFFLINE` (e.g. `STATE_ONLY_ROLLBACK` on `T5`, `T21`, or any non-`WAKING->OFFLINE` edge) | `old_state = WAKING AND new_state = OFFLINE` (1198) | `illegal_transition(TransitionEventID)`; logged `illegal_state_only_rollback_tuple`; no mutation |
| 2 | Non-`validation_abort` reason on the `WAKING->OFFLINE` edge | `reason = validation_abort` (1198) | same |
| 3 | Null or inexact `assignment_ref` | `assignment_ref is exact and non-null` (1199) | same |
| 4 | Wake-origin mismatch — `waking_origin_assignment_ref[MinerID]` != the resolved exact-version ref | `waking_origin_assignment_ref[MinerID] = assignment_version_ref(...)` (1200) | same |

In every row the guard records `transition_rejection_log(TransitionEventID, reason_rejected =
illegal_state_only_rollback_tuple)` (line 1201) and returns `illegal_transition(TransitionEventID)` (line 1202) with NO
state / residency / one-shot energy / census / assignment mutation and no registry entry. The §0.8 AA5 addendum states
the closure explicitly: "No caller can use `STATE_ONLY_ROLLBACK` on T5 / T21 / any other edge to bypass assignment
effects" (line 907).

Case 4 (wake-origin mismatch) is also caught earlier by `AbortPendingWakeForRollback`'s own pre-check (lines 1864–1866,
§3), which returns `wake_abort_failed(reason = waking_origin_mismatch)` and never invokes the hook; the AA5 guard is the
backstop that would still reject a mismatch reaching the hook by any other path.

**Finding: PASS.** All four illegal-use classes (wrong edge, non-`validation_abort` reason, null/inexact `assignment_ref`,
wake-origin mismatch) are rejected by the step-(4b) guard as `illegal_transition` with `illegal_state_only_rollback_tuple`
and no mutation.

---

## 5. Miner state machine §3.5 documents AA5 — PASS

`STAGE_01_MINER_STATE_MACHINE.md` §3.5 is the normative narrative for AA5. The heading (line 668) and the legal-tuple
clause (lines 681–687):

```
668 ### 3.5 Stage-1AA addendum — `assignment_effect_policy` in the transition identity and the legal `STATE_ONLY_ROLLBACK` tuple
...
681 - **Legal `STATE_ONLY_ROLLBACK` tuple (AA5).** `STATE_ONLY_ROLLBACK` (which suppresses the edge's assignment-status
682   change in the atomic apply) is legal IFF `old_state = WAKING` AND `new_state = OFFLINE` AND `reason = validation_abort`
683   AND `assignment_ref` is exact and non-null AND `waking_origin_assignment_ref[MinerID] = assignment_ref`. Any other use
684   — a different edge (`T5`, `T21`, …), a null/inexact `assignment_ref`, a wake-origin mismatch, or a non-`validation_abort`
685   reason — is REJECTED as `illegal_transition` with NO state/residency/energy/census/assignment mutation and a logged
686   `illegal_state_only_rollback_tuple`. Every non-rollback caller uses the signature default `EDGE_DEFAULT`, so no caller
687   can smuggle `STATE_ONLY_ROLLBACK` onto another edge to bypass its assignment effects.
```

§3.5 states the same five-way tuple, the same rejection (`illegal_transition` with a logged
`illegal_state_only_rollback_tuple` and no mutation), and the same closure (every non-rollback caller uses `EDGE_DEFAULT`)
as the executable guard verified in §1. §3.5 also confirms AA5 does not change the authoritative `T12` trigger set (still
Departure / WakeDeadlineExpiry / ValidationAbort, §3 row T12) or any legal edge (lines 671–672), and records that the
addendum supersedes the Stage-1Z framing while §3.4 is retained frozen and Stage-1A–1Z lettered artifacts are unchanged
(lines 689–691).

**Finding: PASS.** Miner-SM §3.5 documents the AA5 legal-tuple guard consistently with the executable pseudocode.

---

## 6. Test-vector linkage (TV233, TV234)

`STAGE_01AA_SEMANTIC_TEST_VECTORS.md` exercises AA5 with two vectors that map one-to-one onto this audit.

**TV233 — STATE_ONLY_ROLLBACK on a non-rollback edge is rejected with no mutation (AA5)** (line 81). Procedure:
`ApplyMinerStateTransition`. It sets up a `STATE_ONLY_ROLLBACK` call on an edge that is not the rollback tuple (a
non-`WAKING` `old_state`, a `new_state` other than `OFFLINE`, a `reason` other than `validation_abort`, or a null/inexact
`assignment_ref`) and expects the guard to fail: record `transition_rejection_log(..., illegal_state_only_rollback_tuple)`
and return `illegal_transition(TransitionEventID)` with no state / residency / one-shot energy / census / assignment
mutation and no registry entry (lines 87–90). This directly exercises §1, §2, and illegal-use cases 1–3 of §4.

**TV234 — STATE_ONLY_ROLLBACK with a wake-origin mismatch is rejected with no mutation (AA5)** (line 92). Procedures:
`ApplyMinerStateTransition`, `AbortPendingWakeForRollback`. It sets up a `WAKING -> OFFLINE` / `validation_abort`
transition with an exact non-null `assignment_ref` but `waking_origin_assignment_ref[MinerID]` unequal to it, and expects
the fifth conjunct to fail so the hook returns `illegal_transition` with no mutation, while
`AbortPendingWakeForRollback` additionally returns `wake_abort_failed(reason = waking_origin_mismatch)` from its own
pre-call check and departs no miner (lines 98–101). This directly exercises §3 and illegal-use case 4 of §4.

Both vectors are registered in the coverage summary against AA5 (lines 128–129) and preserve the A1 baseline
`8.420833333 kWh`.

---

## 7. Verification summary

| # | Check | Result |
|---|-------|--------|
| 1 | Step (4b) is an executable five-way conjunctive guard: `STATE_ONLY_ROLLBACK` legal IFF `WAKING->OFFLINE` AND `validation_abort` AND exact non-null `assignment_ref` AND wake-origin match (lines 1197–1200) | PASS |
| 2 | On failure the guard records `illegal_state_only_rollback_tuple` and returns `illegal_transition` with no mutation (lines 1201–1202) | PASS |
| 3 | The guard sits AFTER legality/envelope validation (step 4, lines 1188–1193) and BEFORE the atomic apply (step 5 `ATOMICALLY:`, line 1204), so a rejection leaves no state/residency/energy/census/assignment change and no registry entry (line 1205 insert is inside step 5) | PASS |
| 4 | Step (5c) assignment-status update is gated on `assignment_effect_policy = EDGE_DEFAULT` (lines 1214–1215); `STATE_ONLY_ROLLBACK` suppresses it | PASS |
| 5 | `STATE_ONLY_ROLLBACK` is passed at exactly one call site (line 1874, `AbortPendingWakeForRollback`); every other caller binds the `EDGE_DEFAULT` signature default (line 1114) | PASS |
| 6 | The single call site satisfies every AA5 tuple conjunct exactly (lines 1870–1874) | PASS |
| 7 | `AbortPendingWakeForRollback` performs its own `waking_origin_assignment_ref` pre-check before the call (lines 1864–1866) | PASS |
| 8 | All four illegal-use classes (wrong edge, non-`validation_abort` reason, null/inexact `assignment_ref`, wake-origin mismatch) are rejected with `illegal_transition` and no mutation (§4) | PASS |
| 9 | Miner-SM §3.5 documents the AA5 legal-tuple guard consistently (lines 668, 681–687) | PASS |
| 10 | TV233 and TV234 exercise AA5 (linkage confirmed) | PASS |

**Result:** AA5 PASS. The `STATE_ONLY_ROLLBACK` assignment-effect suppression is now bound to an executable legal-tuple
guard at step (4b) of `ApplyMinerStateTransition`. The guard admits `STATE_ONLY_ROLLBACK` only on the exact `T12`
`ValidationAbort` rollback tuple (`WAKING -> OFFLINE`, `reason = validation_abort`, exact non-null `assignment_ref`,
matching `waking_origin_assignment_ref[MinerID]`) and rejects every other use as `illegal_transition` with a logged
`illegal_state_only_rollback_tuple`. Because step (4b) precedes the atomic apply (step 5), a rejection mutates no state,
residency, one-shot energy, census, or assignment and leaves no applied-registry entry. Step (5c)'s assignment-status
write is gated on `EDGE_DEFAULT`, so the suppression takes effect only under `STATE_ONLY_ROLLBACK`; and the sole accepting
call site — `AbortPendingWakeForRollback` — satisfies the tuple exactly and additionally pre-checks the wake-origin
binding, so no caller can smuggle `STATE_ONLY_ROLLBACK` onto `T5` / `T21` / any other edge to bypass its assignment
effects. This is documentation-only; the algorithm is PoCol, the mechanism is the idle policy within PoCol, and the A1
baseline `8.420833333 kWh` is preserved.
