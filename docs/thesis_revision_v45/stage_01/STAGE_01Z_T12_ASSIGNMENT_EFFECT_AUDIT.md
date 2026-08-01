# Stage 1Z — T12 Assignment-Effect Policy Audit (Z4)

This audit verifies correction **Z4**: the `T12` `ValidationAbort` rollback form's assignment-effect policy is now
**executable** rather than prose-only. Concretely, `ApplyMinerStateTransition` carries an explicit
`assignment_effect_policy` parameter defaulting to `EDGE_DEFAULT`, its assignment-status write (step 5c) is gated on that
parameter, and `AbortPendingWakeForRollback` is the sole call site that passes `STATE_ONLY_ROLLBACK` and the sole owner of
the canonical assignment close. This preserves single-owner closure: under `STATE_ONLY_ROLLBACK` the transition hook and
the rollback operation never both close the same assignment.

Scope is documentation-only. The algorithm is **PoCol** and the mechanism is the idle policy within PoCol. The A1
baseline `8.420833333 kWh` is unchanged. No Stage-1A–1Y historical artifact is modified. All lines are quoted from the
current normative documents; line anchors are approximate.

Sources of truth (read-only): `STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_MINER_STATE_MACHINE.md`.

---

## 1. Executable `assignment_effect_policy` parameter (default `EDGE_DEFAULT`) — PASS

`ApplyMinerStateTransition` (`STAGE_01_PROTOCOL_PSEUDOCODE.md`, `PROCEDURE ApplyMinerStateTransition`, line 1074) declares
the policy as a first-class INPUT with an executable default in the signature — not as narrative:

```
1078          assignment_ref, candidate_id, propagation_id,    # J3: explicit ids; J4: event_seq owned by ScheduleEvent
1079          assignment_effect_policy = EDGE_DEFAULT    # Z4: EDGE_DEFAULT (apply the edge's assignment-status change) | STATE_ONLY_ROLLBACK
```

The enum and its two members are documented on the signature and in the procedure preamble:

```
1080          # Z4 ASSIGNMENT-EFFECT POLICY. EDGE_DEFAULT (the default for EVERY caller except the rollback) applies the edge's
1081          # declared assignment-status change in step (5c). STATE_ONLY_ROLLBACK — passed ONLY by AbortPendingWakeForRollback
1082          # for the ValidationAbort rollback form — changes miner state / residency / one-shot energy / census ONLY and
1083          # performs NO assignment status / custody / coverage mutation; the caller then performs the single canonical close.
```

The enum is also declared in the module preamble (lines 859–864):

```
859  # --- Z4 executable T12 assignment-effect policy ---
860  # assignment_effect_policy in { EDGE_DEFAULT, STATE_ONLY_ROLLBACK }. ApplyMinerStateTransition takes it (default
861  #   EDGE_DEFAULT). EDGE_DEFAULT applies the edge's declared assignment-status change (as before). STATE_ONLY_ROLLBACK
862  #   (passed ONLY by AbortPendingWakeForRollback) changes miner state / residency / one-shot energy ONLY and performs NO
863  #   assignment status / custody / coverage mutation; AbortPendingWakeForRollback then performs the SINGLE canonical
864  #   assignment close and ledger restoration. Every OTHER caller uses EDGE_DEFAULT.
```

Because the default is declared in the signature (`assignment_effect_policy = EDGE_DEFAULT`, line 1079), the policy is
executable: any caller that omits the parameter binds `EDGE_DEFAULT` by construction, not by prose convention.

**Finding: PASS.** `ApplyMinerStateTransition` has an executable `assignment_effect_policy` parameter over
`{ EDGE_DEFAULT, STATE_ONLY_ROLLBACK }` defaulting to `EDGE_DEFAULT`.

---

## 2. Step (5c) gated on `EDGE_DEFAULT` — PASS

The assignment-status write in the atomic apply is now conditional on the policy. Quoting the gated step verbatim
(lines 1163–1167):

```
1163      # (5c) Z4 assignment status update where the edge specifies one (J7 terminal status) — ONLY under EDGE_DEFAULT.
1164      #      STATE_ONLY_ROLLBACK (AbortPendingWakeForRollback's ValidationAbort form) performs NO assignment status /
1165      #      custody / coverage mutation here; the caller owns the single canonical close.
1166      IF assignment_effect_policy = EDGE_DEFAULT AND edge specifies an assignment status change:
1167        UPDATE status(assignment_ref) accordingly
```

The gating predicate is exactly `assignment_effect_policy = EDGE_DEFAULT AND edge specifies an assignment status change`.
Under `STATE_ONLY_ROLLBACK` the predicate is false, so `UPDATE status(assignment_ref)` is skipped. The surrounding atomic
apply confirms the rest of the hook's effects are policy-independent — residency boundary (5a, lines 1158–1160), one-shot
boundary energy (5b, lines 1161–1162), miner-state write (5d, line 1173), census recompute (5e, lines 1174–1179), and
the census commit through the sole writer (5f, lines 1183–1189) all run regardless of policy. Only the assignment-status
mutation at 5c is gated.

**Finding: PASS.** Step (5c) is gated on `assignment_effect_policy = EDGE_DEFAULT`; `STATE_ONLY_ROLLBACK` skips the
assignment-status write while leaving miner state / residency / energy / census effects intact.

---

## 3. `STATE_ONLY_ROLLBACK` passed only by `AbortPendingWakeForRollback` (single call site) — PASS

Required grep (`STAGE_01_PROTOCOL_PSEUDOCODE.md`):

```
$ grep -n "assignment_effect_policy = STATE_ONLY_ROLLBACK" STAGE_01_PROTOCOL_PSEUDOCODE.md
1821:             assignment_effect_policy = STATE_ONLY_ROLLBACK)   # Z4: state-only; the caller owns the assignment close
1842:        with assignment_effect_policy = STATE_ONLY_ROLLBACK, so ApplyMinerStateTransition changes miner state / residency /
```

Only two lines match. Line 1821 is the argument line of the single `CALL ApplyMinerStateTransition(...)` invocation that
passes the policy — inside `PROCEDURE AbortPendingWakeForRollback` (line 1791). Line 1842 is a NOTE describing that same
call, not a second call site. There is therefore exactly one call site that passes `STATE_ONLY_ROLLBACK`, and it lives in
`AbortPendingWakeForRollback`:

```
1817      SET tr <- CALL ApplyMinerStateTransition(MinerID, WAKING, OFFLINE,
1818             transition_envelope = rollback_envelope, reason = validation_abort,                      # Y5: authoritative T12 trigger
1819             assignment_ref = assignment_version_ref(AssignmentID, assignment_version),               # Y2/X2: EXACT version, never null
1820             candidate_id = null, propagation_id = null,
1821             assignment_effect_policy = STATE_ONLY_ROLLBACK)   # Z4: state-only; the caller owns the assignment close
```

**Every other caller uses `EDGE_DEFAULT` by omission.** The full set of `assignment_effect_policy` occurrences in the
pseudocode is lines 860 (preamble), 1079 (signature default), 1166 (the step-5c gate), 1821 (this call), and 1842 (the
NOTE). No invocation other than line 1817–1821 names the parameter. The pseudocode has fifteen actual
`CALL ApplyMinerStateTransition(...)` invocation sites (lines 1258, 1308, 1318, 1817, 2094, 2097, 2331, 2416, 2500, 2519,
4090, 4748, 4764, 4878, 4888; the mention at line 77 is prose about the calling convention). Of the fifteen, one (line
1817) passes `STATE_ONLY_ROLLBACK`; the other fourteen omit the parameter and therefore bind the default `EDGE_DEFAULT`
declared in the signature (line 1079). The default is executable — the omission itself selects `EDGE_DEFAULT`; no prose
convention is relied upon.

**Finding: PASS.** `STATE_ONLY_ROLLBACK` is passed at exactly one call site, inside `AbortPendingWakeForRollback`; every
other transition uses `EDGE_DEFAULT` via the signature default.

---

## 4. Single-owner property: hook mutates no assignment; operation owns the single close — PASS

Under `STATE_ONLY_ROLLBACK` the hook does no assignment mutation (§2 above: step 5c skipped). The canonical assignment
close is performed exactly once, by `AbortPendingWakeForRollback` itself, immediately after the state-only departure. The
operation's comment at the T12 departure states the split explicitly (lines 1814–1816):

```
1814      # Z4: STATE_ONLY_ROLLBACK — ApplyMinerStateTransition (F6/X8) changes miner state + residency + one-shot energy +
1815      #   census ONLY, performs NO assignment mutation, and CLEARS waking_origin_assignment_ref[MinerID] on the WAKING
1816      #   departure (5c-Z5). The canonical assignment close is owned HERE (step 3).
```

The single canonical close (step 3) is then performed by the operation (lines 1826–1830):

```
1826    # (3) Y5: the SINGLE canonical assignment close (X7 fields). Performed EXACTLY ONCE here, only if the head is still
1827    #   live (a head already CLOSED by an earlier self-rollback is left as-is — idempotent).
1828    IF AssignmentID (version assignment_version) is a live head:
1829      CLOSE AssignmentID (version assignment_version) as CLOSED (status = CLOSED, custody_status = revoked,
1830            termination_reason = cancellation, revocation_reason = assignment_revoked, closure_detail = closure_detail)   # X7 canonical; Y5 sole owner
```

The procedure's own NOTE ties the two together and states the single-owner guarantee (lines 1841–1845):

```
1841        wake_abort_failed and departs no miner); it departs a still-WAKING miner via the LEGAL T12 ValidationAbort trigger
1842        with assignment_effect_policy = STATE_ONLY_ROLLBACK, so ApplyMinerStateTransition changes miner state / residency /
1843        energy / census ONLY (and clears the wake-origin) while THIS operation performs the single canonical close (Z4) and
1844        restores the PRE-CONSTRUCTOR before-image (Z2). It resolves a WAKING miner UNCONDITIONALLY (Y4). The transition hook
1845        and this operation never both close the same assignment.
```

Thus on the rollback path there is precisely one writer of assignment status/custody/coverage: the hook writes none
(step 5c gated off), and `AbortPendingWakeForRollback` writes exactly one canonical close (step 3, idempotent on an
already-CLOSED head) plus the ledger restore from the pre-constructor before-image (step 6, line 1831–1832). On the
non-rollback path (`EDGE_DEFAULT`, every other caller) the edge's declared status change is applied by the hook at step
5c and no rollback operation runs — again one owner. The hook and the operation never both close the same assignment.

**Finding: PASS.** Single-owner closure holds: under `STATE_ONLY_ROLLBACK` the hook performs no assignment
status/custody/coverage mutation and `AbortPendingWakeForRollback` performs the sole canonical close; the two never both
close the same assignment.

---

## 5. Miner state machine §3.4 documents the policy — PASS

`STAGE_01_MINER_STATE_MACHINE.md` §3.4 is the normative narrative for Z4. The heading and the `assignment_effect_policy`
clause (lines 642, 648–655):

```
642 ### 3.4 Stage-1Z addendum — the `STATE_ONLY_ROLLBACK` assignment-effect policy and the wake-origin binding
...
648 - **`assignment_effect_policy` (Z4).** `ApplyMinerStateTransition` takes `assignment_effect_policy in { EDGE_DEFAULT,
649   STATE_ONLY_ROLLBACK }` (default `EDGE_DEFAULT`). Under `EDGE_DEFAULT` (every non-rollback caller) the hook applies the
650   edge's declared assignment-status change as before. Under `STATE_ONLY_ROLLBACK` — passed ONLY by
651   `AbortPendingWakeForRollback` for the `ValidationAbort` `T12` rollback — the hook changes miner state / residency /
652   one-shot energy / census ONLY and performs NO assignment status / custody / coverage mutation; the caller
653   (`AbortPendingWakeForRollback`) then performs the single canonical assignment close. This replaces the prose-only "the
654   rollback form changes miner state only" statement with an executable policy: the hook and the caller never both mutate
655   the same assignment.
```

§3.4 also records that Z4 does not change the authoritative `T12` trigger set (still Departure / WakeDeadlineExpiry /
ValidationAbort, §3 row T12) (lines 644–646), and that this addendum supersedes the Stage-1Y prose that the rollback
"changes miner state only" while Stage-1A–1Y lettered artifacts are unchanged (lines 664–666).

**Finding: PASS.** Miner-SM §3.4 documents the `STATE_ONLY_ROLLBACK` policy, its single-caller restriction, the
single-close ownership, and its status as an executable replacement for the prior prose-only statement.

---

## 6. Test-vector linkage (TV223)

`STAGE_01Z_SEMANTIC_TEST_VECTORS.md` exercises Z4 as **TV223 — Rollback ValidationAbort uses STATE_ONLY_ROLLBACK; one
close owner (Z4)** (line 58). Its expected behaviour matches this audit exactly (lines 62–65):

```
62 - **Expected:** `AbortPendingWakeForRollback` calls `ApplyMinerStateTransition(..., reason = validation_abort,
63   assignment_effect_policy = STATE_ONLY_ROLLBACK)`. Under `STATE_ONLY_ROLLBACK` the hook changes miner state / residency /
64   one-shot energy / census ONLY and mutates NO assignment status/custody/coverage; `AbortPendingWakeForRollback` then
65   performs the canonical assignment close EXACTLY ONCE. The hook and the operation never both close the assignment.
```

The vector names both `AbortPendingWakeForRollback` and `ApplyMinerStateTransition` as its procedures (line 60) and is
registered in the coverage summary against Z4 (line 106). TV223 preserves the A1 baseline `8.420833333 kWh`. This is a
direct, one-to-one exercise of the five verification points above.

---

## 7. Cross-document consistency

The Z4 statement is identical in substance across the six touchpoints (pseudocode ↔ miner-SM §3.4 ↔ round-SM §3.10d ↔
invariant I16 Stage-1Z ↔ terminology ↔ traceability R187):

| Document | Anchor | Statement of Z4 |
|----------|--------|-----------------|
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` | signature l.1079; preamble l.859–864; step 5c l.1166; call l.1817–1821; NOTE l.1838–1845 | `assignment_effect_policy = EDGE_DEFAULT` default; 5c gated on `EDGE_DEFAULT`; single `STATE_ONLY_ROLLBACK` call in the rollback op; single canonical close owned by the op |
| `STAGE_01_MINER_STATE_MACHINE.md` | §3.4 l.642, l.648–655 | executable policy; `STATE_ONLY_ROLLBACK` passed ONLY by `AbortPendingWakeForRollback`; hook and caller never both mutate the same assignment |
| `STAGE_01_ROUND_STATE_MACHINE.md` | §3.10d **Z4** l.790–793 | `assignment_effect_policy in { EDGE_DEFAULT, STATE_ONLY_ROLLBACK }` (default `EDGE_DEFAULT`); the rollback passes `STATE_ONLY_ROLLBACK`; hook does state/residency/energy/census only; op owns the single close — never both (cross-refs miner-SM §3.4) |
| `STAGE_01_INVARIANT_CATALOGUE.md` | I16 Stage-1Z clause **Z4** l.360–361, l.370–372 | the single-owner canonical-close invariant: the rollback passes `STATE_ONLY_ROLLBACK` so the hook mutates no assignment and `AbortPendingWakeForRollback` owns the single close; hook and op never both close |
| `STAGE_01_TERMINOLOGY.md` | `assignment_effect_policy` (Z4) l.957–960 | parameter in `{ EDGE_DEFAULT, STATE_ONLY_ROLLBACK }` (default `EDGE_DEFAULT`); `STATE_ONLY_ROLLBACK` passed only by `AbortPendingWakeForRollback`; every other caller uses `EDGE_DEFAULT` |
| `STAGE_01_TRACEABILITY_MATRIX.csv` | **R187** l.188 | "Make the T12 assignment-effect policy executable (Z4)…"; procedures `ApplyMinerStateTransition;AbortPendingWakeForRollback`; invariants `I16;I18b;I19`; status `SPECIFIED` |

All six agree: the parameter and its default are declared in the executable signature; `STATE_ONLY_ROLLBACK` is confined
to the single rollback call site; step 5c is gated on `EDGE_DEFAULT`; and the canonical close has exactly one owner. No
contradiction was found across the documents. This Z4 audit fills the `STAGE_01Z_T12_ASSIGNMENT_EFFECT_AUDIT.md` slot of
the Stage-1Z deliverable set recorded in `STAGE_01Z_CORRECTION_REPORT.md` (Z4).

---

## 8. Verification summary

| # | Check | Result |
|---|-------|--------|
| 1 | `ApplyMinerStateTransition` has an executable `assignment_effect_policy` parameter (default `EDGE_DEFAULT`) | PASS |
| 2 | Step (5c) is gated on `assignment_effect_policy = EDGE_DEFAULT` | PASS |
| 3 | `STATE_ONLY_ROLLBACK` is passed only by `AbortPendingWakeForRollback` (single call site; all others default to `EDGE_DEFAULT`) | PASS |
| 4 | Under `STATE_ONLY_ROLLBACK` the hook mutates no assignment and `AbortPendingWakeForRollback` owns the single close — never both | PASS |
| 5 | Miner-SM §3.4 documents the policy | PASS |
| 6 | TV223 exercises Z4 (linkage confirmed) | PASS |
| 7 | Cross-document consistency (pseudocode ↔ miner-SM §3.4 ↔ round-SM §3.10d ↔ I16 ↔ terminology ↔ R187) | PASS |

**Result:** Z4 PASS — the T12 assignment-effect policy is executable, step 5c is gated on `EDGE_DEFAULT`,
`STATE_ONLY_ROLLBACK` is passed only by `AbortPendingWakeForRollback` (single call site), and the rollback hook and
operation never both close the same assignment; consistent across all six documents and exercised by TV223.
