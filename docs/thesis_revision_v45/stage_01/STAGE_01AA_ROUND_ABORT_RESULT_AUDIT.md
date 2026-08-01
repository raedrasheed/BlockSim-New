# Stage 1AA — RoundAbort Result-Contract Audit (AA1)

This audit verifies correction **AA1**: the `RoundAbort` result contract is now standardised on the single canonical
result `round_aborted(abort_record)` (where `abort_record = abort_record(RoundID, TemplateID, reason)`), replacing the
former bare `abort_record`. It confirms that (i) `RoundAbort` returns exactly this result, (ii) every named propagator
lists and classifies the EXACT result rather than aliasing it by prose, and (iii) `SetupRetryEvent` maps a target
`round_aborted(abort_record)` to `setup_retry_record.status = ABORTED` — never `CANCELLED` — at both its guard branches
and its captured-result classification.

Scope is documentation-only. The algorithm is **PoCol** and the mechanism is the idle policy within PoCol. The A1
baseline `8.420833333 kWh` is unchanged. No Stage-1A–1Z historical artifact is modified. All lines are quoted from the
current normative documents; line anchors are approximate.

Sources of truth (read-only): `STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_ROUND_STATE_MACHINE.md` (§3.10e).

---

## 1. `RoundAbort` returns the single canonical `round_aborted(abort_record)` — PASS

`RoundAbort` (`STAGE_01_PROTOCOL_PSEUDOCODE.md`, `PROCEDURE RoundAbort`, line 5162, §20) records the abort fact and then
returns the one canonical result. Quoting the terminal RETURN and its RETURNS line verbatim (lines 5205–5207):

```
5205    # AA1: ONE canonical result — round_aborted carrying the abort_record. Every caller/propagator classifies THIS name.
5206    RETURN round_aborted(abort_record(RoundID, TemplateID, reason))
5207  RETURNS: round_aborted(abort_record)   # AA1: canonical result name across every contract (was bare abort_record)
```

The `abort_record` payload is constructed inline from the round's identity at the RETURN (`abort_record(RoundID,
TemplateID, reason)`, line 5206), and matches the recorded abort fact captured earlier in the procedure (line 5175):

```
5175    RECORD round_abort(RoundID, TemplateID, reason)
```

The module preamble states the AA1 rule normatively (lines 882–887):

```
882  # --- AA1 canonical RoundAbort result ---
883  # RoundAbort RETURNS round_aborted(abort_record) (AA1) — ONE canonical result name across EVERY contract. Every procedure
884  #   that propagates it (SetupRetryEvent, PrepareParticipantsForNewRound, ContinueTemplateRefreshAssignmentSetup,
885  #   TemplateRefresh, and the recovery paths) lists round_aborted in its RETURNS union and classifies the EXACT
886  #   round_aborted(abort_record) result — no alias-by-prose. RULE: a target's round_aborted result maps
887  #   setup_retry_record.status = ABORTED (NEVER CANCELLED).
```

`RoundAbort` has exactly one RETURN of an abort result, and it is `round_aborted(abort_record(...))`. There is no second
abort result and no bare `abort_record` return anywhere in the procedure.

**Finding: PASS.** `RoundAbort` returns the single canonical `round_aborted(abort_record(RoundID, TemplateID, reason))`;
the RETURNS line names exactly `round_aborted(abort_record)` and explicitly records that this supersedes the former bare
`abort_record`.

---

## 2. Every direct value-propagator lists and classifies the exact result — PASS

Five procedures propagate the abort by returning it up the call chain via `RETURN CALL RoundAbort(...)`. Because
`RoundAbort`'s sole abort result is `round_aborted(abort_record)` (§1), the EXACT result flows out of each unchanged, and
each lists `round_aborted` in its RETURNS union.

**(a) `SetupRetryEvent`** (`PROCEDURE SetupRetryEvent`, line 1970). RETURNS union (lines 2063–2064):

```
2063  RETURNS: setup_retry_stale_noop | setup_retry_terminal_stale_noop | setup_retry_duplicate_suppressed |
2064           round_aborted(abort_record) | (the re-run target procedure's disposition)   # AA1: canonical round_aborted(abort_record)
```

**(b) `PrepareParticipantsForNewRound`** (`PROCEDURE PrepareParticipantsForNewRound`, line 1706). RETURNS union
(line 1831), with four `RETURN CALL RoundAbort(...)` abort exits at lines 1801, 1807, 1810 and 1829:

```
1831  RETURNS: participant_set_prepared | participant_set_setup_retry_seated | round_aborted
```

**(c) `ContinueTemplateRefreshAssignmentSetup`** (`PROCEDURE ContinueTemplateRefreshAssignmentSetup`, line 5054). RETURNS
union (line 5149), with `RETURN CALL RoundAbort(...)` abort exits at lines 5121, 5125, 5128 and 5147:

```
5149  RETURNS: TemplateID | template_refresh_retry_seated | template_refresh_retry_stale_noop | round_aborted
```

**(d) `TemplateRefresh`** (`PROCEDURE TemplateRefresh`, line 5016) delegates its assignment phase to (c) and propagates
its disposition. RETURNS union (line 5046):

```
5046  RETURNS: new_TemplateID | template_refresh_retry_seated | template_refresh_retry_stale_noop | round_aborted   # (propagates ContinueTemplateRefreshAssignmentSetup's disposition; the initial call cannot be stale)
```

**(e) `FullRangeExhaustNoSolution`** (`PROCEDURE FullRangeExhaustNoSolution`, line 4917) has two `RETURN CALL
RoundAbort(...)` abort exits (line 4944, `false_exhaustion_claim`; line 4951, `exhausted_no_solution`) and delegates the
`continue_mining` branch to `TemplateRefresh` (line 4949). Its RETURNS names the exact result twice (line 4952):

```
4952  RETURNS: (TemplateRefresh disposition: new_TemplateID | template_refresh_retry_seated | template_refresh_retry_stale_noop | round_aborted(abort_record)) | round_aborted(abort_record)   # AA1: the RoundAbort branch propagates the canonical round_aborted(abort_record), never a prose "abort"
```

Each of the five names `round_aborted` in its RETURNS union and reaches the abort by `RETURN CALL RoundAbort(...)`, so the
propagated value is exactly `RoundAbort`'s single canonical result — no alias-by-prose.

**Finding: PASS.** All five direct value-propagators list `round_aborted` in their RETURNS union and propagate the exact
`round_aborted(abort_record)` result by returning `RoundAbort`'s call value.

---

## 3. `SetupRetryEvent` guard branches set `ABORTED` before `RETURN CALL RoundAbort` — PASS

`SetupRetryEvent` has three guard branches that abort the round: (6) wrong round state, (7) budget exhausted, and (7)
state incompatible. Each sets `rec.status <- ABORTED` (with `rec.target_disposition <- round_aborted`) BEFORE the
`RETURN CALL RoundAbort(...)`. Quoting verbatim (lines 2022–2036):

```
2022    # (6) X4 TARGET ROUND STATE. BOTH targets require ASSIGNMENT; a non-terminal non-ASSIGNMENT dispatch is a declared abort.
2023    IF round_state != ASSIGNMENT:
2024      SET rec.status <- ABORTED ; SET rec.target_disposition <- round_aborted   # AA1: target RoundAbort -> ABORTED
2025      RETURN CALL RoundAbort(RoundContext, reason = setup_retry_wrong_round_state(setup_kind, round_state),
2026                             dispatch_envelope = dispatch_envelope, recovery_finalising = false)   # X4 (returns round_aborted(abort_record), AA1)
2027    # (7) X4/W8 BOUND (Y3: scalar retry_generation vs the maximum) + STATE COMPATIBILITY. An over-budget retry ABORTS
2028    #     (never merely "exhausted"); an OFFLINE-stranded eligible participant ABORTS rather than retry from an incompatible state.
2029    IF retry_generation > maximum_setup_retries:
2030      SET rec.status <- ABORTED ; SET rec.target_disposition <- round_aborted   # AA1
2031      RETURN CALL RoundAbort(RoundContext, reason = setup_retry_budget_exhausted(setup_kind),
2032                             dispatch_envelope = dispatch_envelope, recovery_finalising = false)   # X4/Y3
2033    IF NOT (every eligible participant of RoundID is in miner_state {REGISTERED, RESERVE, LOW_POWER_LISTEN}):
2034      SET rec.status <- ABORTED ; SET rec.target_disposition <- round_aborted   # AA1
2035      RETURN CALL RoundAbort(RoundContext, reason = setup_retry_state_incompatible(setup_kind),
2036                             dispatch_envelope = dispatch_envelope, recovery_finalising = false)   # W8
```

In all three guard branches the terminal status is set to `ABORTED` (lines 2024, 2030, 2034) — never `CANCELLED` — and
only then does the branch `RETURN CALL RoundAbort(...)`. The three abort reasons are `setup_retry_wrong_round_state`,
`setup_retry_budget_exhausted`, and `setup_retry_state_incompatible`, matching the three conditions the task names.

**Finding: PASS.** The wrong-round-state, budget-exhausted, and state-incompatible guard branches each set
`rec.status = ABORTED` before `RETURN CALL RoundAbort`; none sets `CANCELLED`.

---

## 4. `SetupRetryEvent` step-8 classification maps `round_aborted(abort_record)` to `ABORTED` (never `CANCELLED`) — PASS

On a first dispatch, step (8) transitions `SEATED -> APPLYING`, CAPTURES the target's disposition, and classifies it into
a terminal status. The classification maps a target `round_aborted(abort_record)` to `ABORTED` in both classification
arms — the ordinary arm and the round-closed-while-APPLYING (`terminal_closure_pending`) arm. Quoting verbatim
(lines 2046–2062):

```
2046    # Z1/AA2 CLASSIFY the captured result into the terminal status:
2047    SET rec.target_disposition <- disp
2048    IF rec.terminal_closure_pending = true:
2049      # AA2: the round CLOSED while this record was APPLYING (CancelSetupRetriesForRound flagged it); the record MUST finish
2050      #   terminal — NEVER APPLIED. A target round_aborted(abort_record) maps to ABORTED (AA1); any other captured
2051      #   disposition maps to CANCELLED.
2052      IF disp = round_aborted(abort_record): SET rec.status <- ABORTED
2053      ELSE:                                  SET rec.status <- CANCELLED
2054    ELSE IF disp = participant_set_prepared OR disp is a committed TemplateID value:
2055      SET rec.status <- APPLIED                 # Z1: setup succeeded (round now HASHING)
2056    ELSE IF disp = participant_set_setup_retry_seated(...) OR disp = template_refresh_retry_seated(...):
2057      SET rec.status <- SUPERSEDED              # Z1: a later generation was seated by the target
2058    ELSE IF disp = round_aborted(abort_record):
2059      SET rec.status <- ABORTED                 # AA1: a target RoundAbort result maps to ABORTED (never CANCELLED)
2060    ELSE:   # disp = template_refresh_retry_stale_noop or another declared stale disposition
2061      SET rec.status <- CANCELLED               # Z1: a declared stale cancellation
2062    RETURN disp
```

The classification predicate is the EXACT result name in both arms: line 2052 (`terminal_closure_pending = true` arm) and
line 2058 (ordinary arm) both test `disp = round_aborted(abort_record)` and set `rec.status <- ABORTED`. The `CANCELLED`
outcomes (lines 2053, 2061) are reserved for a NON-abort captured disposition (any other terminal-closure result) and for
a declared stale disposition (`template_refresh_retry_stale_noop` or similar). Thus `round_aborted(abort_record)` never
maps to `CANCELLED`, and `CANCELLED` never captures an abort — exactly the AA1 rule. The procedure NOTE restates this
(lines 2070–2072): "… `ABORTED` (a target `round_aborted(abort_record)`, AA1 — never `CANCELLED`) / `CANCELLED` (a
declared stale/terminal disposition)."

The other `CANCELLED` settings in `SetupRetryEvent` are the pre-target stale/terminal guards — closed round (line 2008,
`setup_retry_terminal_stale_noop`) and stale template identity (lines 2014, 2020, `setup_retry_stale_noop`). None of these
is a `round_aborted` target, so the ABORTED-only mapping for `round_aborted(abort_record)` is not weakened by them.

**Finding: PASS.** `SetupRetryEvent` maps a captured `disp = round_aborted(abort_record)` to `rec.status = ABORTED` in
both the ordinary arm (line 2059) and the `terminal_closure_pending` arm (line 2052); `CANCELLED` is confined to
non-abort dispositions.

---

## 5. Recovery paths route through the single canonical result (recovery-finalising form) — PASS

The recovery paths propagate a round abort in its recovery-FINALISING form: they issue `CALL RoundAbort(...,
recovery_finalising = true)` — the abort IS the application of a recovery outcome, so the CALLER finalises the episode —
and then return their own recovery-specific disposition after observing the terminal `ROUND_ABORTED` round-state effect.
The abort itself still returns the single canonical `round_aborted(abort_record)` of §1; there is no bare `abort_record`
and no alternate abort result at any of these call sites.

**(a) `CompleteSecurityRecovery`** (`PROCEDURE CompleteSecurityRecovery`, line 3620), branch D (`UNRECOVERABLE`), classifies
the abort by its `ROUND_ABORTED` effect (lines 3636–3640):

```
3636      CALL RoundAbort(RoundContext, reason = floor_unrecoverable, dispatch_envelope = dispatch_envelope,
3637                      recovery_finalising = true)                                  # S4: this closure finalises the episode; do NOT cancel it
3638      IF round_state = ROUND_ABORTED:
3639        RETURN recovery_branch_result(kind = SUCCESS, target = ROUND_ABORTED)      # R4: successful RoundAbort
3640      RETURN recovery_branch_result(kind = FAILED, reason = abort_did_not_terminate)   # R4: defensive (should not occur)
```

Its RETURNS is the recovery branch-result contract (line 3700): `recovery_branch_result(kind, target | reason |
continuation_ref)`.

**(b) `ApplyRecoveryWorkAfterEpilogue`** (`PROCEDURE ApplyRecoveryWorkAfterEpilogue`, line 3290) issues the finalising
abort on an irreversible partial install (lines 3339–3341) and returns `recovery_work_install_aborted(work_id)`:

```
3339        CALL RoundAbort(RoundContext, reason = recovery_install_failed_aborted,
3340                        dispatch_envelope = W.due_dispatch_envelope, recovery_finalising = true)   # T4/S4
3341        RETURN recovery_work_install_aborted(work_id)
```

Its RETURNS (lines 3357–3358) lists `recovery_work_install_aborted`, not `round_aborted`.

**(c) `ApplyRecoveryAssignmentContinuationAfterEpilogue`** (`PROCEDURE ApplyRecoveryAssignmentContinuationAfterEpilogue`,
line 3752) issues the finalising abort at two irreversible-rollback points (lines 3827–3828 and 3854–3855) and returns
`recovery_continuation_install_aborted(decision_id)`. Its RETURNS (lines 3863–3864) lists
`recovery_continuation_install_aborted`, not `round_aborted`.

These three are recovery-FINALISING invokers: they do not re-export `round_aborted` as a value (doing so would drop the
episode-finalisation semantics the recovery caller needs), but they call the SAME single canonical `RoundAbort` whose only
abort result is `round_aborted(abort_record)`, and they classify it by its `ROUND_ABORTED` round-state effect. The AA1
guarantee — one canonical abort-result name, no bare `abort_record`, no alias — therefore holds across the recovery paths
as well: `RoundAbort` is the sole abort producer and its sole result is `round_aborted(abort_record)`.

**Finding: PASS.** The recovery paths invoke the single canonical `RoundAbort` in its recovery-finalising form
(`recovery_finalising = true`), classify it by its `ROUND_ABORTED` effect, and return their own recovery-specific
disposition; no bare `abort_record` or alias abort result exists at any recovery call site.

---

## 6. No bare `abort_record` and no alias-by-prose anywhere — PASS

A whole-file scan for the token confirms every `abort_record` occurrence is either the canonical wrapper
`round_aborted(abort_record)`, the inline constructor `abort_record(RoundID, TemplateID, reason)`, or AA1 commentary — and
there is no bare `RETURN abort_record` or `RETURNS: abort_record`:

```
$ grep -n "abort_record" STAGE_01_PROTOCOL_PSEUDOCODE.md
883:  # RoundAbort RETURNS round_aborted(abort_record) (AA1) — ONE canonical result name across EVERY contract...
886:  #   round_aborted(abort_record) result — no alias-by-prose. RULE: a target's round_aborted result maps
2026: ...   # X4 (returns round_aborted(abort_record), AA1)
2050: ...   #   terminal — NEVER APPLIED. A target round_aborted(abort_record) maps to ABORTED (AA1); ...
2052:      IF disp = round_aborted(abort_record): SET rec.status <- ABORTED
2058:    ELSE IF disp = round_aborted(abort_record):
2064:           round_aborted(abort_record) | (the re-run target procedure's disposition)   # AA1: ...
2071: ...   round_aborted(abort_record), AA1 — never CANCELLED) / CANCELLED (a declared stale/terminal disposition)...
2074: ...   round_aborted(abort_record) — NEVER leaving ASSIGNMENT with no controller.
4952:  RETURNS: (TemplateRefresh disposition: ... | round_aborted(abort_record)) | round_aborted(abort_record)   # AA1: ...
5205:    # AA1: ONE canonical result — round_aborted carrying the abort_record...
5206:    RETURN round_aborted(abort_record(RoundID, TemplateID, reason))
5207:  RETURNS: round_aborted(abort_record)   # AA1: canonical result name across every contract (was bare abort_record)
```

Every result-bearing occurrence is `round_aborted(abort_record)` (or the constructor inside it). The former bare
`abort_record` result no longer appears as a return value.

**Finding: PASS.** The single canonical result name `round_aborted(abort_record)` is used at every abort contract; no bare
`abort_record` return and no prose alias remains.

---

## 7. Cross-document consistency — round-SM §3.10e AA1 — PASS

`STAGE_01_ROUND_STATE_MACHINE.md` §3.10e is the normative narrative for AA1. Its statement matches the pseudocode exactly
(lines 812–817):

```
812 **AA1 (canonical `RoundAbort` result).** `RoundAbort` RETURNS `round_aborted(abort_record)` — ONE canonical result name
813 across every contract (it was a bare `abort_record`). Every procedure that propagates it (`SetupRetryEvent`,
814 `PrepareParticipantsForNewRound`, `ContinueTemplateRefreshAssignmentSetup`, `TemplateRefresh`, `FullRangeExhaustNoSolution`,
815 and the recovery paths) lists `round_aborted` in its RETURNS union and classifies the exact `round_aborted(abort_record)`
816 result — no alias-by-prose. RULE: a target's `round_aborted` result maps `setup_retry_record.status = ABORTED` (NEVER
817 `CANCELLED`).
```

The round-SM names the same canonical result, the same propagator set, and the same ABORTED-mapping rule as the
pseudocode preamble (§1, lines 882–887) and the executable guard/classification steps (§3, §4). §3.10e also records
(line 810) that these Stage-1AA statements supersede the Stage-1Z ones they name while §3.10a–§3.10d remain the frozen
W/X/Y/Z layers.

**Finding: PASS.** Pseudocode and round-SM §3.10e agree on the canonical result, the propagator set, and the ABORTED
mapping.

---

## 8. Test-vector linkage (TV227)

`STAGE_01AA_SEMANTIC_TEST_VECTORS.md` exercises AA1 as **TV227 — RoundAbort returns the canonical result and a target
abort maps a retry to ABORTED (AA1)** (line 18). Its procedures are `RoundAbort`, `SetupRetryEvent`, and the target
propagators `PrepareParticipantsForNewRound` / `ContinueTemplateRefreshAssignmentSetup` (lines 20–21), and its expected
behaviour matches this audit exactly (lines 24–27):

```
24  - **Expected:** `RoundAbort` returns exactly `round_aborted(abort_record)` (`abort_record(RoundID, TemplateID, reason)`);
25    `SetupRetryEvent` captures `disp = round_aborted(abort_record)` and classifies `rec.status = ABORTED` (never `CANCELLED`)
26    with `rec.target_disposition = disp`. Every propagating procedure in the chain lists `round_aborted` in its RETURNS
27    union and matches the exact result name — no bare `abort_record` and no prose alias.
```

TV227 is registered in the vector coverage summary against AA1 (line 122: `TV227 | AA1 | RoundAbort, SetupRetryEvent,
targets`). It is a direct, one-to-one exercise of §1–§4 above and preserves the A1 baseline `8.420833333 kWh`.

---

## 9. Verification summary

| # | Check | Result |
|---|-------|--------|
| 1 | `RoundAbort` returns the single canonical `round_aborted(abort_record(RoundID, TemplateID, reason))` (l.5206–5207) | PASS |
| 2 | `SetupRetryEvent` lists & propagates the exact `round_aborted(abort_record)` (RETURNS l.2063–2064) | PASS |
| 3 | `PrepareParticipantsForNewRound` lists `round_aborted`; abort exits `RETURN CALL RoundAbort` (l.1831; 1801/1807/1810/1829) | PASS |
| 4 | `ContinueTemplateRefreshAssignmentSetup` lists `round_aborted`; abort exits `RETURN CALL RoundAbort` (l.5149; 5121/5125/5128/5147) | PASS |
| 5 | `TemplateRefresh` lists `round_aborted` (propagates the continuation's disposition) (l.5046) | PASS |
| 6 | `FullRangeExhaustNoSolution` lists `round_aborted(abort_record)`; abort exits `RETURN CALL RoundAbort` (l.4952; 4944/4951) | PASS |
| 7 | Guard branches set `ABORTED` (never `CANCELLED`) before `RETURN CALL RoundAbort`: wrong round state / budget exhausted / state incompatible (l.2024/2030/2034) | PASS |
| 8 | Step-8 classification maps `disp = round_aborted(abort_record)` -> `ABORTED` in both arms (l.2052, 2059); `CANCELLED` only for non-abort/stale dispositions | PASS |
| 9 | Recovery paths route through the single canonical `RoundAbort` (recovery-finalising form) with no bare `abort_record`/alias (l.3636–3639, 3339–3341, 3827–3829/3854–3856) | PASS |
| 10 | No bare `abort_record` return and no alias-by-prose anywhere (whole-file scan) | PASS |
| 11 | Cross-document consistency (pseudocode preamble ↔ round-SM §3.10e AA1) | PASS |
| 12 | TV227 exercises AA1 (linkage confirmed) | PASS |

**Result:** AA1 PASS — `RoundAbort` returns the single canonical `round_aborted(abort_record(RoundID, TemplateID,
reason))`, and every named propagator either lists `round_aborted` in its RETURNS union and returns the exact result by
`RETURN CALL RoundAbort` (`SetupRetryEvent`, `PrepareParticipantsForNewRound`, `ContinueTemplateRefreshAssignmentSetup`,
`TemplateRefresh`, `FullRangeExhaustNoSolution`) or routes through that same single canonical result in its
recovery-finalising form (the recovery paths). `SetupRetryEvent` maps a target `round_aborted(abort_record)` to
`rec.status = ABORTED` at all three guard branches (wrong round state / budget exhausted / state incompatible) and at
both arms of its step-8 classification — never `CANCELLED`. No bare `abort_record` return and no prose alias remains; the
statement is consistent between the pseudocode and round-SM §3.10e, and it is exercised by TV227.

This change is documentation-only. The algorithm is **PoCol**, the mechanism is the idle policy within PoCol, and the A1
baseline `8.420833333 kWh` is preserved.
