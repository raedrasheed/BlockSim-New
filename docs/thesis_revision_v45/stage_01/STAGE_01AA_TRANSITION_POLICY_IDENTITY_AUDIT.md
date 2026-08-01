# Stage 1AA — Transition-Policy Identity Audit (AA4)

This audit verifies correction **AA4** (design A): `assignment_effect_policy` is a FIELD of the immutable
`TransitionEventID`, so that two otherwise-identical transitions that differ ONLY in their assignment-effect policy are
DISTINCT ids. The consequence is that the applied/replay registry (`applied_transition_registry`) can never alias a
state-only rollback (which suppresses the edge's assignment side effect) with an edge-default transition (which would have
applied it): a replay is duplicate-suppressed only against an EXACTLY matching policy. Design A (policy inside the id) was
adopted over design B (deriving the policy deterministically outside the id); this audit confirms the id genuinely
contains the field, quoting the tuple.

Scope is documentation-only. The algorithm is **PoCol** and the mechanism is the idle policy within PoCol — an operating
policy inside PoCol, not a variant or fork. The A1 baseline `8.420833333 kWh` is unchanged. No Stage-1A–1Z historical
artifact is modified. All quoted lines are from the current normative documents; line anchors are approximate.

Sources of truth (read-only): `STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_MINER_STATE_MACHINE.md`,
`STAGE_01AA_SEMANTIC_TEST_VECTORS.md`.

---

## 1. `assignment_effect_policy` is the final field of `TransitionEventID` and defaults to `EDGE_DEFAULT` — PASS

### 1.1 The signature declares the executable default

`PROCEDURE ApplyMinerStateTransition` (`STAGE_01_PROTOCOL_PSEUDOCODE.md`, §0.9, procedure header at line 1109) declares
the policy as a first-class INPUT with an executable default in the signature — not as narrative (line 1114):

```
1113          assignment_ref, candidate_id, propagation_id,    # J3: explicit ids; J4: event_seq owned by ScheduleEvent
1114          assignment_effect_policy = EDGE_DEFAULT    # Z4: EDGE_DEFAULT (apply the edge's assignment-status change) | STATE_ONLY_ROLLBACK
```

Because the default is bound in the signature (`assignment_effect_policy = EDGE_DEFAULT`), any caller that omits the
parameter selects `EDGE_DEFAULT` by construction, not by prose convention. The enum over
`{ EDGE_DEFAULT, STATE_ONLY_ROLLBACK }` is also declared in the §0.8 module preamble (lines 860–865, Z4).

### 1.2 The policy is the last element of the immutable `TransitionEventID` tuple

Step (1) of the hook builds the immutable `TransitionEventID`. Quoting the construction verbatim (lines 1168–1172):

```
1168    SET TransitionEventID <- (envelope_namespace, hook_id, event_time, delta_cycle, event_seq,
1169                              MinerID, old_state, new_state, reason,
1170                              AssignmentID(assignment_ref), assignment_version(assignment_ref),
1171                              candidate_id, propagation_id,
1172                              assignment_effect_policy)                           # R3 + AA4-A: policy in the id (immutable, J3)
```

`assignment_effect_policy` is the **fourteenth and final element** of the tuple — placed after `candidate_id` and
`propagation_id` — and the inline anchor names it explicitly: `# R3 + AA4-A: policy in the id (immutable, J3)`. This is
the direct, grounded confirmation that design A was implemented: the field is physically inside the id, not derived
elsewhere. The immediately following AA4-A comment states the consequence (lines 1173–1175):

```
1173    # AA4-A: assignment_effect_policy is a FIELD of TransitionEventID, so two otherwise-identical transitions with
1174    #     DIFFERENT assignment side effects (EDGE_DEFAULT vs STATE_ONLY_ROLLBACK) are DISTINCT ids — the applied/replay
1175    #     registry never aliases transitions whose assignment mutation differs.
```

The §0.8 module preamble records the same design-A statement (lines 899–902):

```
899  # --- AA4 assignment-effect policy is part of transition identity (design A) ---
900  # assignment_effect_policy in { EDGE_DEFAULT, STATE_ONLY_ROLLBACK } is a field of TransitionEventID (AA4-A). Two otherwise
901  #   identical transitions with different assignment_effect_policy are DISTINCT ids, so the applied/replay registry never
902  #   aliases transitions with different assignment side effects.
```

**Finding: PASS.** `assignment_effect_policy` is the final field of the immutable `TransitionEventID` tuple (line 1172)
and defaults to `EDGE_DEFAULT` in the signature (line 1114). Design A — policy IN the id — is realised, not merely
described.

---

## 2. Replay-guard consequence: no aliasing of transitions whose assignment side effect differs — PASS

The applied/replay registry is `applied_transition_registry`, declared as "set of TransitionEventIDs that were
SUCCESSFULLY APPLIED … Replay suppression checks THIS set" (lines 959–962). The step-(2) replay guard tests the id
against exactly that set (lines 1176–1179):

```
1176    # (2) K5 REPLAY GUARD — check the APPLIED registry. Suppress ONLY an exact-same-id replay of an
1177    #     ALREADY-APPLIED transition; do NOT read old_state and do NOT charge energy.
1178    IF TransitionEventID in applied_transition_registry:
1179      RETURN duplicate_suppressed(TransitionEventID)        # W6: exact replay of an applied transition; no state check, no charge
```

Because `assignment_effect_policy` is part of the id (§1.2), an `EDGE_DEFAULT` transition and a `STATE_ONLY_ROLLBACK`
transition that are identical in every OTHER field (same `MinerID`, edge `old_state -> new_state`, envelope,
`reason`, `assignment_ref`, `candidate_id`, `propagation_id`) produce DIFFERENT `TransitionEventID` values. The membership
test `TransitionEventID in applied_transition_registry` therefore CANNOT match one against the other: presence of the
edge-default id in the registry does not duplicate-suppress the state-only-rollback id, and vice versa. Only an
**exact-same-policy** replay of an already-applied transition returns `duplicate_suppressed`.

This is the precise safety property AA4 is designed to guarantee. Had the policy been derived outside the id (design B),
the two forms would have collided on the same id, and a `STATE_ONLY_ROLLBACK` departure could be duplicate-suppressed by
an earlier `EDGE_DEFAULT` departure at the same envelope/edge — silently skipping the state-only apply, or conversely a
state-only rollback could mask an edge-default transition that WOULD have applied the edge's assignment side effect. The
in-id field forecloses both. Registration is confined to the atomic apply — "A TransitionEventID enters ONLY inside
ApplyMinerStateTransition's atomic apply; a suppressed replay or a rejected … event is NEVER here" (lines 960–962) — so
the registry only ever holds ids for transitions whose full effect (including their policy) actually ran.

**Finding: PASS.** Because the policy is in the id, the step-(2) `duplicate_suppressed` check cannot alias two
transitions whose assignment side effect differs; suppression fires only for an exact-same-policy replay.

---

## 3. Sole `STATE_ONLY_ROLLBACK` caller is `AbortPendingWakeForRollback`; all others use `EDGE_DEFAULT` — PASS

Required grep (`STAGE_01_PROTOCOL_PSEUDOCODE.md`) for the policy passed as a CALL argument:

```
$ grep -n "assignment_effect_policy = STATE_ONLY_ROLLBACK" STAGE_01_PROTOCOL_PSEUDOCODE.md
1874:             assignment_effect_policy = STATE_ONLY_ROLLBACK)   # Z4: state-only; the caller owns the assignment close
1895:        with assignment_effect_policy = STATE_ONLY_ROLLBACK, so ApplyMinerStateTransition changes miner state / residency /
```

Only two lines match. Line 1874 is the argument line of the single `CALL ApplyMinerStateTransition(...)` invocation that
passes `STATE_ONLY_ROLLBACK`, inside `PROCEDURE AbortPendingWakeForRollback` (procedure header at line 1844); line 1895 is
that procedure's own NOTE describing the same call, not a second call site. The invocation in full (lines 1870–1874):

```
1870      SET tr <- CALL ApplyMinerStateTransition(MinerID, WAKING, OFFLINE,
1871             transition_envelope = rollback_envelope, reason = validation_abort,                      # Y5: authoritative T12 trigger
1872             assignment_ref = assignment_version_ref(AssignmentID, assignment_version),               # Y2/X2: EXACT version, never null
1873             candidate_id = null, propagation_id = null,
1874             assignment_effect_policy = STATE_ONLY_ROLLBACK)   # Z4: state-only; the caller owns the assignment close
```

**Every other caller uses `EDGE_DEFAULT` by omission.** The pseudocode has fifteen actual `CALL ApplyMinerStateTransition(...)`
invocation sites (lines 1306, 1356, 1366, 1870, 2193, 2196, 2430, 2515, 2599, 2618, 4189, 4847, 4863, 4982, 4992; the
mentions at lines 77 and 1129 are prose about the calling convention). Of these, exactly one (line 1870) passes
`STATE_ONLY_ROLLBACK`; the other fourteen omit the parameter and therefore bind the signature default `EDGE_DEFAULT`
(line 1114). Notably, the OTHER `T12` (`WAKING -> OFFLINE`) departures do NOT use the rollback policy — they carry
different reasons and default `EDGE_DEFAULT`:

```
1366      CALL ApplyMinerStateTransition(MinerID, WAKING, OFFLINE,
1367                                     transition_envelope = dispatch_envelope, reason = wake_deadline_expiry,   # S1: ONE envelope object
1368                                     assignment_ref = target_assignment, candidate_id = null, propagation_id = null)   # T12 (M1)
```

```
4189          CALL ApplyMinerStateTransition(holder, WAKING, OFFLINE,
4190                 transition_envelope = dispatch_envelope, reason = lease_expired_while_waking,   # S1: ONE envelope object
4191                 assignment_ref = assignment, candidate_id = null, propagation_id = null)   # T12 (M3/M1)
```

Neither names `assignment_effect_policy`, so both bind `EDGE_DEFAULT`. Consequently step (5c)'s assignment-status update
runs under `EDGE_DEFAULT` for every non-rollback transition; only `AbortPendingWakeForRollback`'s `validation_abort`
departure runs under `STATE_ONLY_ROLLBACK`, where the caller owns the single canonical assignment close (comment at lines
1867–1869; close at step (3), lines 1879–1883). Step (5c) itself (lines 1211–1215):

```
1211      # (5c) Z4 assignment status update where the edge specifies one (J7 terminal status) — ONLY under EDGE_DEFAULT.
1212      #      STATE_ONLY_ROLLBACK (AbortPendingWakeForRollback's ValidationAbort form) performs NO assignment status /
1213      #      custody / coverage mutation here; the caller owns the single canonical close.
1214      IF assignment_effect_policy = EDGE_DEFAULT AND edge specifies an assignment status change:
1215        UPDATE status(assignment_ref) accordingly
```

**Finding: PASS.** `STATE_ONLY_ROLLBACK` is passed at exactly one call site, inside `AbortPendingWakeForRollback`
(line 1870–1874); every other transition uses `EDGE_DEFAULT` via the signature default, so the step-(5c) assignment
update runs under `EDGE_DEFAULT` only.

---

## 4. Design A composes with the AA5 tuple guard

Design A (policy in the id) and the AA5 legal-tuple guard are complementary layers that together close the policy-misuse
surface, and they compose without conflict:

- **AA5 restricts WHICH edge may carry `STATE_ONLY_ROLLBACK`.** Step (4b) rejects the policy on any edge that is not the
  exact `ValidationAbort` rollback tuple, BEFORE the atomic apply (lines 1194–1202):

  ```
  1197    IF assignment_effect_policy = STATE_ONLY_ROLLBACK
  1198       AND NOT (old_state = WAKING AND new_state = OFFLINE AND reason = validation_abort
  1199                AND assignment_ref is exact and non-null
  1200                AND waking_origin_assignment_ref[MinerID] = assignment_version_ref(AssignmentID(assignment_ref), assignment_version(assignment_ref))):
  1201      RECORD transition_rejection_log(TransitionEventID, reason_rejected = illegal_state_only_rollback_tuple)   # AA5
  1202      RETURN illegal_transition(TransitionEventID)   # AA5: NO state/residency/energy/census/assignment mutation
  ```

  So no caller can smuggle `STATE_ONLY_ROLLBACK` onto `T5`, `T21`, or any other edge to bypass its assignment effects — a
  misuse is rejected with no mutation and no registry entry.

- **AA4 ensures the policy that AA5 admits is part of replay identity.** For the one edge AA5 does admit
  (`WAKING -> OFFLINE`, `validation_abort`), the state-only form and a hypothetical edge-default form of the same edge are
  DISTINCT ids (§1–§2), so replay suppression can never let one stand in for the other.

The two are non-redundant: AA5 is an admission guard on the CALL (it decides whether a `STATE_ONLY_ROLLBACK` transition
may apply at all); AA4 is an identity property of the id (it decides whether an admitted transition aliases another in the
replay registry). AA5's guard runs in step (4b), strictly before the step-(5) atomic apply that registers the id, and both
the AA5 rejection log entry and the AA4 registry membership test key off the SAME `TransitionEventID` built in step (1) —
which already contains the policy field. Design A thus makes AA5's per-edge decision and the registry's per-id decision
consistent by construction: the field the tuple guard reasons about is the same field the replay guard distinguishes on.
The miner-state-machine narrative states both corrections together in §3.5 (see §5).

---

## 5. Miner state machine §3.5 documents AA4 (and AA5) — PASS

`STAGE_01_MINER_STATE_MACHINE.md` §3.5 is the normative narrative for Stage-1AA. The heading and the AA4 clause
(lines 668, 674–680):

```
668 ### 3.5 Stage-1AA addendum — `assignment_effect_policy` in the transition identity and the legal `STATE_ONLY_ROLLBACK` tuple
...
674 - **`assignment_effect_policy` is part of `TransitionEventID` (AA4, design A).** `ApplyMinerStateTransition` builds
675   `TransitionEventID` from the full dispatch envelope plus the transition-specific fields INCLUDING
676   `assignment_effect_policy in { EDGE_DEFAULT, STATE_ONLY_ROLLBACK }`. Two transitions that are otherwise identical
677   (same miner, edge, envelope, reason, assignment, candidate ids) but carry a different `assignment_effect_policy` are
678   therefore DISTINCT ids. The applied/replay registry can never alias a state-only rollback with an edge-default
679   transition that would have applied the edge's assignment side effect — a replay is suppressed only against an exactly
680   matching policy.
```

§3.5 also records the AA5 legal tuple (lines 681–687), that AA4/AA5 do not change the authoritative `T12` trigger set
(still Departure / WakeDeadlineExpiry / ValidationAbort, lines 671–672), and that this addendum supersedes the Stage-1Z
framing in which `assignment_effect_policy` was a caller-passed argument OUTSIDE the transition identity and was not
tuple-guarded, while §3.4 is retained as the frozen Z layer and Stage-1A–1Z lettered artifacts are unchanged (lines
689–691).

**Finding: PASS.** Miner-SM §3.5 documents AA4 (policy in `TransitionEventID`, design A), its replay-guard consequence,
and its composition with the AA5 tuple guard, and correctly frames it as superseding the Stage-1Z outside-the-id framing.

---

## 6. Test-vector linkage (TV232)

`STAGE_01AA_SEMANTIC_TEST_VECTORS.md` exercises AA4 as **TV232 — Two transitions differing only in
assignment_effect_policy are distinct replay ids (AA4)** (line 71). Its setup and expected behaviour match this audit
exactly (lines 73–79):

```
73 - **Procedures:** `ApplyMinerStateTransition`.
74 - **Setup:** consider a `WAKING -> OFFLINE` transition for one miner with a fixed dispatch envelope, reason, and exact
75   `assignment_ref`. One form carries `assignment_effect_policy = EDGE_DEFAULT`; the other carries `STATE_ONLY_ROLLBACK`.
76 - **Expected:** `TransitionEventID` includes `assignment_effect_policy` as a field, so the two forms are DISTINCT ids.
77   Registering (or replaying) one does NOT duplicate-suppress the other via the applied-transition registry; the registry
78   never aliases a state-only rollback with an edge-default transition that would have applied the edge's assignment
79   side effect.
```

TV232 is registered against AA4 in the coverage summary (line 127: `| TV232 | AA4 | ApplyMinerStateTransition |`) and
preserves the A1 baseline `8.420833333 kWh`. It is a direct, one-to-one exercise of the verification points in §1–§2:
same edge, envelope, reason, and `assignment_ref`, differing only in policy, yielding distinct ids and no cross-aliasing
in `applied_transition_registry`. (The adjacent AA5 vectors TV233 and TV234, lines 81–100, exercise the tuple guard that
§4 shows composing with AA4.)

---

## 7. Verification summary

| # | Check | Evidence (approx. lines) | Result |
|---|-------|--------------------------|--------|
| 1 | `assignment_effect_policy` is the final field of the immutable `TransitionEventID` tuple | pseudocode l.1168–1172 (field at l.1172); AA4-A comment l.1173–1175; preamble l.899–902 | PASS |
| 2 | The policy defaults to `EDGE_DEFAULT` in the signature | pseudocode l.1114 | PASS |
| 3 | Step-(2) replay guard cannot alias two transitions whose assignment side effect differs; only exact-same-policy replay is suppressed | pseudocode l.1176–1179; registry decl l.959–962 | PASS |
| 4 | Sole `STATE_ONLY_ROLLBACK` caller is `AbortPendingWakeForRollback` (single call site) | pseudocode l.1870–1874; grep = 1 argument line | PASS |
| 5 | Every other caller uses `EDGE_DEFAULT`, so step (5c)'s assignment update runs under `EDGE_DEFAULT` only | pseudocode l.1366, l.4189 (other T12), l.1211–1215 (5c) | PASS |
| 6 | Design A composes with the AA5 tuple guard (admission vs. identity, same id) | pseudocode l.1194–1202; miner-SM §3.5 l.681–687 | PASS |
| 7 | Miner-SM §3.5 documents AA4 (policy in the id, design A) | miner-SM l.668, l.674–680 | PASS |
| 8 | TV232 exercises AA4 (linkage confirmed) | test vectors l.71–79, l.127 | PASS |

---

## 8. Result

**AA4 PASS.** Design A is realised: `assignment_effect_policy in { EDGE_DEFAULT, STATE_ONLY_ROLLBACK }` is the final
element of the immutable `TransitionEventID` tuple (`STAGE_01_PROTOCOL_PSEUDOCODE.md` line 1172, anchor `AA4-A`), and it
defaults to `EDGE_DEFAULT` in the `ApplyMinerStateTransition` signature (line 1114). Because the policy is inside the id,
the step-(2) `duplicate_suppressed` replay check against `applied_transition_registry` cannot alias a state-only rollback
with an edge-default transition that would have applied the edge's assignment side effect — only an exact-same-policy
replay is suppressed. `STATE_ONLY_ROLLBACK` is passed at exactly one call site, inside `AbortPendingWakeForRollback`
(lines 1870–1874) with `reason = validation_abort`; every other `ApplyMinerStateTransition` caller — including the other
`T12` `WAKING -> OFFLINE` departures at lines 1366 and 4189 — omits the parameter and binds `EDGE_DEFAULT`, so step (5c)'s
assignment-status update runs under `EDGE_DEFAULT` only. Design A composes cleanly with the AA5 legal-tuple guard (step
4b): AA5 admits the policy on exactly one edge, and AA4 ensures that the admitted policy is part of replay identity so it
can never be aliased away. The correction is documented in miner-SM §3.5 and exercised by TV232.

This audit is documentation-only; it modifies no algorithm. The algorithm is **PoCol** and the mechanism is the idle
policy within PoCol. The A1 baseline `8.420833333 kWh` is preserved.
