# Stage 1Z — Waking-Origin Binding Audit (Z5)

This audit verifies correction **Z5** of the Stage-1 formal specification of **PoCol** and the idle policy within PoCol:
the definition of the `T12` `ValidationAbort` rollback for a **detached / closed head** via an immutable wake-origin
binding, `waking_origin_assignment_ref`. It is a documentation-only audit; no executable source, configuration, or
experiment is touched, and the A1 baseline (`8.420833333 kWh`) is unchanged.

Correction Z5 answers the Stage-1Y residual question: a `WAKING` miner whose assignment head has since become
`CLOSED` / revoked / detached is *not* safe, but a rollback must depart only the miner whose CURRENT `WAKING` residency
was actually initiated by the exact assignment being rolled back. Z5 introduces a per-miner map
`waking_origin_assignment_ref : MinerID -> assignment_version_ref`, SET on entry to `WAKING` and CLEARED on any `WAKING`
departure inside `ApplyMinerStateTransition`, and makes `AbortPendingWakeForRollback` verify that binding BEFORE the
`T12` departure. Head liveness stays unconditional (Y4); the wake-origin must match (Z5).

## Sources of truth (read-only)

- `STAGE_01_PROTOCOL_PSEUDOCODE.md` — §0.8 data-model declaration; `ApplyMinerStateTransition` (§0.9);
  `StartWake` (§0.10); `AbortPendingWakeForRollback`; the two rollback callers `RollbackParticipantSetup` and
  `RollbackRecoveryAssignmentPlan`.
- `STAGE_01_MINER_STATE_MACHINE.md` — §3.4 Stage-1Z addendum.

Corroborating (skimmed, all present): `STAGE_01_ROUND_STATE_MACHINE.md` §3.10d (Z5); `STAGE_01_INVARIANT_CATALOGUE.md`
I16 Stage-1Z clause (Z5) and I19; `STAGE_01_TERMINOLOGY.md` (`waking_origin_assignment_ref`);
`STAGE_01Z_SEMANTIC_TEST_VECTORS.md` (TV224, TV225); `STAGE_01_TRACEABILITY_MATRIX.csv` (R188).

---

## §0.8 — the wake-origin association is declared

`STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.8 (core data model) declares the field and its lifetime contract
(lines 865–872):

```
  # --- Z5 wake-origin binding for the ValidationAbort rollback of a detached / closed head ---
  # waking_origin_assignment_ref : map MinerID -> assignment_version_ref. It is SET when a miner ENTERS WAKING (new_state =
  #   WAKING) to the exact assignment_version_ref being woken, and CLEARED when the miner LEAVES WAKING (old_state = WAKING),
  #   both inside ApplyMinerStateTransition (so it is total for a WAKING miner). A rollback ValidationAbort is LEGAL only when
  #   miner_state = WAKING AND waking_origin_assignment_ref[MinerID] = assignment_version_ref(AssignmentID,
  #   assignment_version) of the rollback item — the assignment may be live, CLOSED, revoked, or detached, but the immutable
  #   wake-origin association must match. On a mismatch AbortPendingWakeForRollback returns wake_abort_failed and departs NO
  #   miner; the association is cleared exactly once by the successful T12 departure.
```

The field is a genuine per-run state variable: `RunInitialise` initialises it and threads it into `RunContext`
(lines 1478, 1484):

```
    INITIALISE waking_origin_assignment_ref <- empty map    # Z5: MinerID -> assignment_version_ref (set on WAKING entry, cleared on WAKING exit)
...
                      setup_retry_records, waking_origin_assignment_ref, maximum_setup_retries)   # Z1/Z5
```

Declaration present and total for a `WAKING` miner. **PASS.**

---

## Check 1 — SET on WAKING entry, CLEARED on WAKING exit, both inside `ApplyMinerStateTransition`

The central miner-state transition hook `ApplyMinerStateTransition` (§0.9), the SOLE writer of `miner_state`, performs
the association maintenance inside its atomic apply, step **(5c-Z5)** (lines 1168–1171):

```
      # (5c-Z5) wake-origin association: SET on entry to WAKING (to the EXACT version being woken), CLEAR on any WAKING
      #      departure (T5/T12/T21), both here so the map is total for a WAKING miner and cleared exactly once on departure.
      IF new_state = WAKING: SET waking_origin_assignment_ref[MinerID] <- assignment_version_ref(AssignmentID(assignment_ref), assignment_version(assignment_ref))   # Z5: bind the wake origin (canonical exact-version ref)
      IF old_state = WAKING: CLEAR waking_origin_assignment_ref[MinerID]                                    # Z5: cleared exactly once by the departure
```

Because this happens inside the single atomic apply (step 5) that also sets `miner_state(MinerID) <- new_state`
(line 1173), the binding is established at exactly the instant a miner becomes `WAKING` and removed at exactly the
instant it ceases to be `WAKING` — it is therefore total for the duration of any `WAKING` residency and never orphaned.
Placement in the hook is authoritative: `ApplyMinerStateTransition` is documented as "the ONLY writer of miner_state"
(line 1212), so no other procedure can enter or leave `WAKING` without traversing (5c-Z5).

The `SET` binds the canonical **exact-version** reference `assignment_version_ref(AssignmentID(assignment_ref),
assignment_version(assignment_ref))` derived from the same `assignment_ref` that identifies the transition — not a bare
`AssignmentID` — so a later re-wake for a different version cannot spuriously match an earlier rollback item.

Set-on-entry and clear-on-exit are both realised, in the sole state writer. **PASS.**

---

## Check 2 — `AbortPendingWakeForRollback` verifies the exact binding BEFORE the T12 and departs no miner on mismatch

`AbortPendingWakeForRollback` is "the ONE named legal-T12 rollback wake-abort + SOLE canonical assignment-close owner."
Its precondition fixes head-liveness unconditionality (Y4) — the wake-origin, not the head, is what is checked
(lines 1798–1801):

```
  PRECONDITIONS: called by RollbackRecoveryAssignmentPlan / RollbackParticipantSetup / RollbackTemplateRefreshSetup to
                 resolve ONE affected miner. Y4: it resolves a WAKING miner UNCONDITIONALLY — it does NOT require
                 AssignmentID to still be a live bound head; a CLOSED / revoked / detached assignment does NOT make a
                 WAKING miner safe.
```

Step (2) performs the wake-origin check FIRST, inside the `IF miner_state(MinerID) = WAKING` guard, and returns before
any transition on a mismatch (lines 1806–1825):

```
    SET departed_to_offline <- false
    IF miner_state(MinerID) = WAKING:
      IF waking_origin_assignment_ref[MinerID] != assignment_version_ref(AssignmentID, assignment_version):   # Z5: exact wake-origin binding
        RETURN wake_abort_failed(MinerID = MinerID, AssignmentID = AssignmentID, reason = waking_origin_mismatch)   # Z5: do NOT depart an unrelated WAKING miner
      ...
      SET tr <- CALL ApplyMinerStateTransition(MinerID, WAKING, OFFLINE,
             transition_envelope = rollback_envelope, reason = validation_abort,                      # Y5: authoritative T12 trigger
             assignment_ref = assignment_version_ref(AssignmentID, assignment_version),               # Y2/X2: EXACT version, never null
             candidate_id = null, propagation_id = null,
             assignment_effect_policy = STATE_ONLY_ROLLBACK)   # Z4: state-only; the caller owns the assignment close
```

The mismatch `RETURN` at line 1813 is textually and control-flow BEFORE the `ApplyMinerStateTransition` call at line
1817 that fires the `T12` `validation_abort` edge. So on a wake-origin mismatch the procedure returns
`wake_abort_failed(reason = waking_origin_mismatch)` and never reaches the departure — it departs NO miner and mutates
no state, exactly as §0.8 requires.

The escalation chain of that failure is explicit. Each rollback caller maps `wake_abort_failed` to `rollback_failed`:
`RollbackRecoveryAssignmentPlan` — `RETURN rollback_failed(reason = residual_partial_assignment)  # Y4/T4: caller takes
RECOVERY_INSTALL_FAILED_ABORTED / RoundAbort` (line 3925); `RollbackParticipantSetup` —
`RETURN rollback_failed(reason = residual_partial_setup)   # Y4: never leave an affected miner WAKING` (line 1870). The
recovery-install caller then records `recovery_episode_disposition[episode] <- RECOVERY_INSTALL_FAILED_ABORTED`
(lines 3725, 3752) and calls `RoundAbort(RoundContext, reason = recovery_install_failed_aborted, ...)` (lines 3728,
3755); the participant-setup caller calls `RoundAbort(RoundContext, reason = participant_setup_rollback_failed, ...)`
(line 1749). No unrelated `WAKING` miner is silently departed.

Binding verified before the T12; mismatch departs no miner and escalates to `RECOVERY_INSTALL_FAILED_ABORTED` /
`RoundAbort`. **PASS.**

---

## Check 3 — a matching binding legally departs a WAKING miner even when the head is CLOSED / detached

When the wake-origin matches, the guarded block proceeds to the `T12` `validation_abort` departure with
`assignment_effect_policy = STATE_ONLY_ROLLBACK` (lines 1817–1823). Under that policy `ApplyMinerStateTransition`
changes miner state / residency / one-shot energy / census ONLY and performs no assignment mutation (§0.9 step 5c,
lines 1163–1167; the `IF assignment_effect_policy = EDGE_DEFAULT ...` guard skips the status update), while
`AbortPendingWakeForRollback` owns the single canonical close.

Crucially, that departure does not depend on the head being live. The canonical close is a SEPARATE, later step (3),
guarded by liveness and therefore idempotent (lines 1826–1830):

```
    # (3) Y5: the SINGLE canonical assignment close (X7 fields). Performed EXACTLY ONCE here, only if the head is still
    #   live (a head already CLOSED by an earlier self-rollback is left as-is — idempotent).
    IF AssignmentID (version assignment_version) is a live head:
      CLOSE AssignmentID (version assignment_version) as CLOSED (status = CLOSED, custody_status = revoked, ...)
```

So the state departure (step 2) runs whenever `miner_state = WAKING` and the binding matches, independent of head
liveness; the close (step 3) simply no-ops for a head that some earlier self-rollback already closed. The procedure's
NOTE confirms this jointly with Y4 (lines 1838–1844): it "verifies the exact wake-origin binding
`waking_origin_assignment_ref[MinerID]` before departing (Z5 — a mismatch returns `wake_abort_failed` and departs no
miner) ... and it resolves a WAKING miner UNCONDITIONALLY (Y4)." The recovery-install caller reinforces the same for a
`CLOSED / revoked / detached` head (lines 3910–3915).

A matching binding legally departs a `WAKING` miner regardless of head liveness. **PASS.**

---

## Check 4 — the association is cleared exactly once, by the successful departure

The clear is realised solely by the `IF old_state = WAKING: CLEAR waking_origin_assignment_ref[MinerID]` line inside the
atomic apply (line 1171). The only way to satisfy `old_state = WAKING` in the rollback path is the successful
`WAKING -> OFFLINE` `T12` transition invoked at line 1817. Therefore:

- On a **mismatch** the procedure returns at line 1813 before that call, so no clear occurs and the (correctly
  unrelated) miner's binding is untouched.
- On a **match** the single `T12` apply both departs the miner and clears its binding, atomically, exactly once — the
  clear cannot run twice because `ApplyMinerStateTransition`'s replay guard (step 2, lines 1137–1140) suppresses an
  exact-same-`TransitionEventID` replay, and `AbortPendingWakeForRollback` treats a `duplicate_suppressed` result as
  already-resolved (`ELSE IF tr is duplicate_suppressed(teid): SET departed_to_offline <- true`, line 1823) rather than
  re-departing.

The §0.8 contract states this directly: "the association is cleared exactly once by the successful T12 departure"
(line 872) and (5c-Z5)'s own comment: "cleared exactly once on departure" (line 1169) / "cleared exactly once by the
departure" (line 1171).

Cleared exactly once, by the successful departure, never on the mismatch path. **PASS.**

---

## Supporting check — `StartWake` binds the correct origin

The wake-origin is only correct if the `WAKING` entry carries the assignment actually being woken. `StartWake` (§0.10)
applies the `WAKING` transition passing `assignment_ref = target_assignment` (lines 1258–1261):

```
    SET tr <- CALL ApplyMinerStateTransition(MinerID, from_state, WAKING,
                     transition_envelope = dispatch_envelope,           # S1: ONE explicit transition-envelope object
                     reason = wake_start, assignment_ref = target_assignment,
                     candidate_id = null, propagation_id = null)         # F6
```

`target_assignment` is, by `StartWake`'s precondition, "a bound PENDING (or PAUSED-resumed) assignment for MinerID"
(line 1224). Its `AssignmentID` / `assignment_version` flow straight into (5c-Z5)'s
`assignment_version_ref(AssignmentID(assignment_ref), assignment_version(assignment_ref))`, so the binding recorded at
entry is exactly the assignment version the rollback item later names. The hook binds the correct origin. **PASS.**

---

## Test-vector linkage (TV224, TV225)

`STAGE_01Z_SEMANTIC_TEST_VECTORS.md` exercises both arms of Z5:

- **TV224 — ValidationAbort legally departs a WAKING miner whose head is CLOSED/detached (Z5)**
  (procedures `AbortPendingWakeForRollback`, `ApplyMinerStateTransition`). Setup: a miner remains `WAKING` after its
  head became `CLOSED` / detached; the rollback item's `assignment_version_ref` equals the immutable
  `waking_origin_assignment_ref[MinerID]`. Expected: because the binding matches, the `T12` `ValidationAbort` legally
  departs the miner to `OFFLINE` (the head need not be live, Y4/Z5); the departure clears
  `waking_origin_assignment_ref[MinerID]` exactly once; the rollback resolves the miner. This is precisely Checks 3 and 4.

- **TV225 — A wake-origin mismatch rejects the departure (Z5)** (procedure `AbortPendingWakeForRollback`). Setup: a
  `WAKING` miner whose current `waking_origin_assignment_ref[MinerID]` names a DIFFERENT assignment version than the
  rollback item's `assignment_version_ref` (e.g. re-woken for another assignment). Expected:
  `wake_abort_failed(reason = waking_origin_mismatch)`, departs NO miner, the caller returns `rollback_failed` and takes
  the declared `RECOVERY_INSTALL_FAILED_ABORTED` / `RoundAbort` path; no unrelated `WAKING` miner is silently departed.
  This is precisely Check 2.

The vector coverage summary lists `TV224 | Z5 | AbortPendingWakeForRollback, ApplyMinerStateTransition` and
`TV225 | Z5 | AbortPendingWakeForRollback`. Both audited behaviours are covered. **PASS.**

---

## Cross-document consistency

| Source | Statement of the Z5 wake-origin binding | Agrees |
|--------|------------------------------------------|--------|
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.8 + §0.9 (5c-Z5) + `AbortPendingWakeForRollback` | field declared; SET/CLEAR in the hook; verified before the T12; mismatch → `wake_abort_failed`; cleared once by the departure | yes |
| `STAGE_01_MINER_STATE_MACHINE.md` §3.4 | "SETS `waking_origin_assignment_ref[MinerID]` on entry to `WAKING` and CLEARS it on any `WAKING` departure (T5/T12/T21), so it is total for a `WAKING` miner and cleared exactly once by the departure ... head may be live, `CLOSED`, revoked, or detached, but the wake-origin must match ... a mismatch ... returns `wake_abort_failed` and departs NO miner" | yes |
| `STAGE_01_ROUND_STATE_MACHINE.md` §3.10d (Z5) | "set on WAKING entry and cleared on WAKING exit inside `ApplyMinerStateTransition` ... legal only when `miner_state = WAKING` AND the association equals the rollback item's exact `assignment_version_ref` — even if the head is `CLOSED`/detached; a mismatch returns `wake_abort_failed` and departs no miner" | yes |
| `STAGE_01_INVARIANT_CATALOGUE.md` I16 Stage-1Z clause Z5 | "the `T12` `ValidationAbort` rollback is bound to the exact `waking_origin_assignment_ref[MinerID]` (set on WAKING entry, cleared on WAKING exit); a mismatch departs no miner" | yes |
| `STAGE_01_INVARIANT_CATALOGUE.md` I19 | state-residency time has a single owner (residency_ledger via `ApplyMinerStateTransition`); the same sole owner that maintains the binding closes/opens residency, so no double-count arises from the `T12` departure | yes |
| `STAGE_01_TERMINOLOGY.md` (`waking_origin_assignment_ref`) | "`MinerID -> assignment_version_ref`, set on entry to `WAKING` and cleared on any `WAKING` departure inside `ApplyMinerStateTransition` ... legal only when `miner_state = WAKING` and this association equals the rollback item's exact `assignment_version_ref` — even for a `CLOSED` / detached head; a mismatch returns `wake_abort_failed` and departs no miner" | yes |
| `STAGE_01_TRACEABILITY_MATRIX.csv` R188 | maps Z5 to `AbortPendingWakeForRollback; ApplyMinerStateTransition; StartWake` and invariants `I16; I19`; risk = "a rollback that silently departs an unrelated WAKING miner whose current wake origin differs"; status `SPECIFIED` | yes |

All seven sources describe the identical contract: the binding is set on `WAKING` entry to the exact
`assignment_version_ref` woken and cleared on `WAKING` exit inside the sole state writer `ApplyMinerStateTransition`;
`AbortPendingWakeForRollback` verifies it before the `T12` `validation_abort` departure; head liveness is unconditional
(Y4) but the wake-origin must match; a mismatch returns `wake_abort_failed` and departs no miner; and the association is
cleared exactly once by the successful departure. No divergence. **PASS.**

---

## Deliverable context

This audit is deliverable 6 of the Stage-1Z set (per `STAGE_01Z_CORRECTION_REPORT.md`). The final Stage-1Z tree
comprises the twelve `STAGE_01Z_*` deliverables — the correction report; the five per-correction audits
(`STAGE_01Z_SETUP_RETRY_LIFECYCLE_AUDIT.md` (Z1), `STAGE_01Z_PREMUTATION_SNAPSHOT_AUDIT.md` (Z2),
`STAGE_01Z_NULLABLE_WAKE_REFERENCE_AUDIT.md` (Z3), `STAGE_01Z_T12_ASSIGNMENT_EFFECT_AUDIT.md` (Z4), and this file (Z5));
the procedure signature/call audit (`STAGE_01Z_PROCEDURE_SIGNATURE_CALL_AUDIT.md`) and procedure call graph
(`STAGE_01Z_PROCEDURE_CALL_GRAPH.md`); the semantic test vectors (`STAGE_01Z_SEMANTIC_TEST_VECTORS.md`, TV219–TV226);
the supersession register (`STAGE_01Z_SUPERSESSION_REGISTER.md`); the cross-document audit
(`STAGE_01Z_CROSS_DOCUMENT_AUDIT.md`); and the checksum manifest (`STAGE_01Z_CHECKSUM_MANIFEST.sha256`) — alongside the
six modified normative `STAGE_01_*` documents (`STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_MINER_STATE_MACHINE.md`,
`STAGE_01_ROUND_STATE_MACHINE.md`, `STAGE_01_INVARIANT_CATALOGUE.md`, `STAGE_01_TERMINOLOGY.md`,
`STAGE_01_TRACEABILITY_MATRIX.csv`). The Stage-1A–1Y lettered artifacts are unchanged; Stage-1Z supersessions are
recorded in `STAGE_01Z_SUPERSESSION_REGISTER.md`. This revision is documentation-only: the algorithm remains PoCol, the
mechanism remains the idle policy within PoCol, and the A1 baseline `8.420833333 kWh` is preserved.

---

## Result

**PASS — Z5 fully realised: `waking_origin_assignment_ref[MinerID]` is SET on `WAKING` entry to the exact
`assignment_version_ref` woken and CLEARED on `WAKING` exit inside the sole state writer `ApplyMinerStateTransition`
(5c-Z5); `AbortPendingWakeForRollback` verifies that exact binding BEFORE the `T12` `validation_abort` and, on a
mismatch, returns `wake_abort_failed(reason = waking_origin_mismatch)` departing no miner (caller → `rollback_failed` →
`RECOVERY_INSTALL_FAILED_ABORTED` / `RoundAbort`); a matching binding legally departs a `WAKING` miner even when the head
is `CLOSED` / revoked / detached (head liveness unconditional, Y4); and the association is cleared exactly once by the
successful departure — consistent across the pseudocode, miner-SM §3.4, round-SM §3.10d, invariants I16/I19,
terminology, R188, and vectors TV224/TV225.**
