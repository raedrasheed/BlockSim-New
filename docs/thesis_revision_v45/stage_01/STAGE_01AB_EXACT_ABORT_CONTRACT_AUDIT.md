# Stage 1AB — Exact Abort-Contract Audit (AB1, AB2)

This audit verifies corrections **AB1** and **AB2** of Stage 1AB. **AB1** requires that the sole abort producer's
result, `round_aborted(abort_record)`, appears as that EXACT shaped result in the RETURNS union of every direct
value-propagator, never as a bare `round_aborted` result-contract alias; and that `SetupRetryEvent`'s RETURNS names the
shaped result ONCE while ENUMERATING the re-run target dispositions explicitly. **AB2** requires that each guard-driven
abort in `SetupRetryEvent` CAPTURES the abort result before it persists `target_disposition`, so the stored disposition
is the exact `round_aborted(abort_record(RoundID, TemplateID, reason))` returned by `RoundAbort`.

Scope is documentation-only. The algorithm is **PoCol** and the mechanism is the idle policy within PoCol. The A1
baseline `8.420833333 kWh` is unchanged. No Stage-1A–1AA historical artifact is modified. All lines are quoted from the
current normative documents; line anchors are exact against the committed tree.

Sources of truth (read-only): `STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_ROUND_STATE_MACHINE.md` (§3.10f).

---

## 1. Whole-file `round_aborted` occurrence audit — zero bare-alias result contracts

Every `round_aborted` occurrence in `STAGE_01_PROTOCOL_PSEUDOCODE.md` was enumerated (`grep -n "round_aborted"`) and
classified as one of:

- **(a)** exact pattern match with payload — `IF disp = round_aborted(abort_record)`;
- **(b)** constructor invocation with payload — `RETURN round_aborted(abort_record(...))`;
- **(c)** type / RETURNS declaration with payload — `RETURNS: … | round_aborted(abort_record)`;
- **(d)** PROSE comment (a `#` line explaining the discipline).

| Line | Occurrence excerpt | Class |
|-----:|--------------------|:-----:|
| 883  | `# RoundAbort RETURNS round_aborted(abort_record) (AA1) — ONE canonical result name; RoundAbort is the SOLE abort producer` | d |
| 886  | `#   FullRangeExhaustNoSolution) lists round_aborted in its RETURNS union and classifies the EXACT round_aborted(abort_record)` | d |
| 890  | `#   effect. RULE: a target's round_aborted result maps setup_retry_record.status = ABORTED (NEVER CANCELLED).` | d |
| 919  | `# RoundAbort returns round_aborted(abort_record). EVERY direct value-propagator lists that EXACT shaped result in its RETURNS` | d |
| 920  | `#   union — never the bare constructor name round_aborted. Direct propagators: PrepareParticipantsForNewRound,` | d |
| 922  | `#   RETURNS names round_aborted(abort_record) ONCE and ENUMERATES the re-run target dispositions explicitly (no vague` | d |
| 923  | `` #   "target procedure's disposition"). Occurrence discipline: a bare `round_aborted` may appear ONLY as an exact pattern `` | d |
| 924  | `#   match with payload (IF disp = round_aborted(abort_record)), a constructor invocation with payload` | d |
| 925  | `#   (RETURN round_aborted(abort_record(...))), or a type declaration with payload — never as a result-contract alias.` | d |
| 930  | `#   round_aborted(abort_record(RoundID, TemplateID, reason)) returned by RoundAbort — never a bare token written before the` | d |
| 1871 | `RETURNS: participant_set_prepared \| participant_set_setup_retry_seated(SetupRetryID, reason) \| round_aborted(abort_record)` | **c** |
| 2052 | `UPDATE setup_retry_records[SetupRetryID].target_disposition <- disp   # AB2: store the EXACT round_aborted(abort_record)` | d |
| 2089 | `UPDATE setup_retry_records[SetupRetryID].target_disposition <- disp   # AB2: EXACT round_aborted(abort_record)` | d |
| 2121 | `#   MUST finish terminal — NEVER APPLIED. A target round_aborted(abort_record) maps to ABORTED (AA1); any other` | d |
| 2123 | `IF disp = round_aborted(abort_record): UPDATE setup_retry_records[SetupRetryID].status <- ABORTED` | **a** |
| 2129 | `ELSE IF disp = round_aborted(abort_record):` | **a** |
| 2135 | `setup_retry_duplicate_suppressed(SetupRetryID) \| round_aborted(abort_record) \|` (SetupRetryEvent RETURNS union) | **c** |
| 2138 | `# AB1: the exact round_aborted(abort_record) shape once; the re-run target's dispositions are ENUMERATED explicitly` | d |
| 2149 | `returned round_aborted(abort_record) by key, then RETURNs \`disp\`. RE-READ (AB4) — after the target returns (it may` | d |
| 2152 | `generation seated) / ABORTED (a target round_aborted(abort_record), AA1 — never CANCELLED) / CANCELLED (a declared` | d |
| 2155 | `` enumerated disposition; or a declared round_aborted(abort_record) — NEVER leaving ASSIGNMENT with no controller. `` | d |
| 5043 | `RETURNS: (… round_aborted(abort_record)) \| round_aborted(abort_record)` (FullRangeExhaustNoSolution — two shaped decls) | **c** |
| 5137 | `RETURNS: new_TemplateID \| … \| round_aborted(abort_record)` (TemplateRefresh) | **c** |
| 5240 | `RETURNS: TemplateID \| … \| round_aborted(abort_record)` (ContinueTemplateRefreshAssignmentSetup) | **c** |
| 5296 | `# AA1: ONE canonical result — round_aborted carrying the abort_record. Every caller/propagator classifies THIS name.` | d |
| 5297 | `RETURN round_aborted(abort_record(RoundID, TemplateID, reason))` | **b** |
| 5298 | `RETURNS: round_aborted(abort_record)   # AA1: canonical result name across every contract (was bare abort_record)` | **c** |

**Class tally (27 occurrence lines):** (a) = 2 lines (2123, 2129); (b) = 1 line (5297); (c) = 6 lines
(1871, 2135, 5043 — two shaped declarations on that single line, 5137, 5240, 5298); (d) = 18 prose-comment lines. Every
executable occurrence carries the `(abort_record)` payload.

**Bare-token confinement.** The bare form `round_aborted` (the token NOT immediately followed by `(`) was isolated with
`grep -Pn 'round_aborted(?!\()'`, which returns EXACTLY five lines — **886, 890, 920, 923, 5296** — every one a `#`
prose comment explaining the discipline (class d). No bare `round_aborted` appears in any executable statement, and in
particular **no RETURNS union or type declaration uses a bare `round_aborted` alias**: all six result-contract lines
(1871, 2135, 5043, 5137, 5240, 5298) carry `round_aborted(abort_record)` with its payload.

**Finding: PASS.** Every `round_aborted` occurrence is classified (a/b/c/d); zero result contracts use the bare alias;
the bare token appears only in prose comments.

---

## 2. Each of the five propagators' RETURNS lists `round_aborted(abort_record)` — PASS

`RoundAbort` is the SOLE abort producer. Its own contract fixes the canonical shape (`PROCEDURE RoundAbort`, line 5253);
the constructor and its declaration:

```
5296    # AA1: ONE canonical result — round_aborted carrying the abort_record. Every caller/propagator classifies THIS name.
5297    RETURN round_aborted(abort_record(RoundID, TemplateID, reason))
5298  RETURNS: round_aborted(abort_record)   # AA1: canonical result name across every contract (was bare abort_record)
```

The five direct value-propagators each list that EXACT shaped result in their RETURNS union (verbatim quotations):

**(1) `PrepareParticipantsForNewRound`** (`PROCEDURE` at line 1746), RETURNS at line 1871:

```
1871  RETURNS: participant_set_prepared | participant_set_setup_retry_seated(SetupRetryID, reason) | round_aborted(abort_record)   # AB1: exact shaped abort result
```

Its abort exit at lines 1869–1870 propagates the canonical value directly (`RETURN CALL RoundAbort(...)`).

**(2) `ContinueTemplateRefreshAssignmentSetup`** (`PROCEDURE` at line 5145), RETURNS at line 5240:

```
5240  RETURNS: TemplateID | template_refresh_retry_seated(SetupRetryID, reason) | template_refresh_retry_stale_noop(TemplateRefreshSetupID) | round_aborted(abort_record)   # AB1: exact shaped abort result
```

Its declared abort at lines 5238–5239 is `RETURN CALL RoundAbort(...)`.

**(3) `TemplateRefresh`** (`PROCEDURE` at line 5107), RETURNS at line 5137:

```
5137  RETURNS: new_TemplateID | template_refresh_retry_seated(SetupRetryID, reason) | template_refresh_retry_stale_noop(TemplateRefreshSetupID) | round_aborted(abort_record)   # AB1: exact shaped abort result (propagates ContinueTemplateRefreshAssignmentSetup's disposition; the initial call cannot be stale)
```

It propagates the shaped result by delegating to `ContinueTemplateRefreshAssignmentSetup` (`RETURN CALL …`, lines 5134–5136).

**(4) `FullRangeExhaustNoSolution`** (`PROCEDURE` at line 5008), RETURNS at line 5043:

```
5043  RETURNS: (TemplateRefresh disposition: new_TemplateID | template_refresh_retry_seated(SetupRetryID, reason) | template_refresh_retry_stale_noop(TemplateRefreshSetupID) | round_aborted(abort_record)) | round_aborted(abort_record)   # AA1/AB1: the RoundAbort branch propagates the canonical round_aborted(abort_record), never a bare alias or prose "abort"
```

Both the `TemplateRefresh`-continue disposition and the direct-abort branch (lines 5040 / 5042) carry the shaped
`round_aborted(abort_record)` — neither is a bare alias.

**(5) `SetupRetryEvent`** (`PROCEDURE` at line 2010), RETURNS at lines 2134–2139:

```
2134  RETURNS: setup_retry_stale_noop(SetupRetryID) | setup_retry_terminal_stale_noop(SetupRetryID) |
2135           setup_retry_duplicate_suppressed(SetupRetryID) | round_aborted(abort_record) |
2136           participant_set_prepared | participant_set_setup_retry_seated(SetupRetryID, reason) | TemplateID |
2137           template_refresh_retry_seated(SetupRetryID, reason) | template_refresh_retry_stale_noop(TemplateRefreshSetupID)
2138           # AB1: the exact round_aborted(abort_record) shape once; the re-run target's dispositions are ENUMERATED explicitly
2139           #   (no vague "target procedure's disposition"). The abort covers both the guard-driven aborts and a target abort.
```

`SetupRetryEvent` names `round_aborted(abort_record)` exactly ONCE (line 2135) and ENUMERATES the re-run target
dispositions explicitly — `participant_set_prepared`, `participant_set_setup_retry_seated(...)`, `TemplateID`,
`template_refresh_retry_seated(...)`, `template_refresh_retry_stale_noop(...)` (lines 2136–2137) — with no vague "target
procedure's disposition" catch-all. The module preamble records the same discipline for all five propagators (lines
918–925).

**Finding: PASS.** All five propagators — `PrepareParticipantsForNewRound` (1871),
`ContinueTemplateRefreshAssignmentSetup` (5240), `TemplateRefresh` (5137), `FullRangeExhaustNoSolution` (5043),
`SetupRetryEvent` (2135) — list the exact `round_aborted(abort_record)`; `SetupRetryEvent` names it once and enumerates
the re-run dispositions explicitly.

---

## 3. AB2 — capture the RoundAbort result BEFORE persisting `target_disposition` — PASS

`SetupRetryEvent` has four guard-driven abort branches. Each executes `SET disp <- CALL RoundAbort(...)` FIRST, then the
two keyed persistent updates (`status <- ABORTED`, then `target_disposition <- disp`), then `RETURN disp`. Quoted
verbatim:

**Guard — AB5-C payload-integrity abort** (the genuine owning event with a mismatched payload), lines 2046–2053:

```
2046    IF NOT (RoundID = rec.RoundID AND setup_kind = rec.setup_kind AND TemplateID_at_seat = rec.TemplateID_at_seat
2047            AND TemplateRefreshSetupID = rec.TemplateRefreshSetupID AND retry_generation = rec.retry_generation):
2048      IF rec.event_ref != null AND rec.event_ref is still pending on EQ: CANCEL rec.event_ref on EQ   # AB5-C: no live event left
2049      SET disp <- CALL RoundAbort(RoundContext, reason = setup_retry_payload_integrity_failure(setup_kind),
2050                        dispatch_envelope = dispatch_envelope, recovery_finalising = false)   # AB2/AB5-C: capture the abort FIRST
2051      UPDATE setup_retry_records[SetupRetryID].status <- ABORTED                              # AB3: keyed persistent UPDATE
2052      UPDATE setup_retry_records[SetupRetryID].target_disposition <- disp                     # AB2: store the EXACT round_aborted(abort_record)
2053      RETURN disp
```

**Guard — wrong round state** (target requires ASSIGNMENT), lines 2085–2090:

```
2085    IF round_state != ASSIGNMENT:
2086      SET disp <- CALL RoundAbort(RoundContext, reason = setup_retry_wrong_round_state(setup_kind, round_state),
2087                        dispatch_envelope = dispatch_envelope, recovery_finalising = false)   # X4/AB2: capture FIRST
2088      UPDATE setup_retry_records[SetupRetryID].status <- ABORTED                              # AB3: keyed persistent UPDATE
2089      UPDATE setup_retry_records[SetupRetryID].target_disposition <- disp                     # AB2: EXACT round_aborted(abort_record)
2090      RETURN disp
```

**Guard — retry budget exhausted** (scalar `retry_generation` over the maximum), lines 2093–2098:

```
2093    IF retry_generation > maximum_setup_retries:
2094      SET disp <- CALL RoundAbort(RoundContext, reason = setup_retry_budget_exhausted(setup_kind),
2095                        dispatch_envelope = dispatch_envelope, recovery_finalising = false)   # X4/Y3/AB2: capture FIRST
2096      UPDATE setup_retry_records[SetupRetryID].status <- ABORTED                              # AB3
2097      UPDATE setup_retry_records[SetupRetryID].target_disposition <- disp                     # AB2
2098      RETURN disp
```

**Guard — incompatible participant state** (an eligible participant not in `{REGISTERED, RESERVE, LOW_POWER_LISTEN}`),
lines 2099–2104:

```
2099    IF NOT (every eligible participant of RoundID is in miner_state {REGISTERED, RESERVE, LOW_POWER_LISTEN}):
2100      SET disp <- CALL RoundAbort(RoundContext, reason = setup_retry_state_incompatible(setup_kind),
2101                        dispatch_envelope = dispatch_envelope, recovery_finalising = false)   # W8/AB2: capture FIRST
2102      UPDATE setup_retry_records[SetupRetryID].status <- ABORTED                              # AB3
2103      UPDATE setup_retry_records[SetupRetryID].target_disposition <- disp                     # AB2
2104      RETURN disp
```

In all four branches the ordering is identical and correct: the abort result is captured into `disp` FIRST (never a bare
token written before the abort result exists), then `status` is set to `ABORTED` by key, then `target_disposition` is set
to `disp` by key, then `disp` is returned. Because `disp` is exactly what `RoundAbort` returns
(`round_aborted(abort_record(RoundID, TemplateID, reason))`, line 5297), the stored `target_disposition` is that exact
shaped value. The AA1 rule that a target `round_aborted` maps `status = ABORTED` (never CANCELLED) is preserved: all four
guards set `ABORTED`. The procedure NOTE restates the discipline (lines 2147–2149): "every guard-driven abort CAPTURES
`disp <- CALL RoundAbort(...)` FIRST, then persists ABORTED + the EXACT returned round_aborted(abort_record) by key, then
RETURNs `disp`."

**Finding: PASS.** All four guard-driven aborts in `SetupRetryEvent` (payload-integrity AB5-C, wrong round state, budget
exhausted, incompatible participant state) capture the abort result before persisting, store the exact
`round_aborted(abort_record(RoundID, TemplateID, reason))` as `target_disposition` by key, and return it.

---

## 4. Round state machine §3.10f documents AB1 and AB2 — PASS

`STAGE_01_ROUND_STATE_MACHINE.md` §3.10f is the normative narrative for Stage 1AB. The heading (line 855) and the two
clauses under audit:

```
855 ### 3.10f Stage-1AB addendum (retry-record persistence & exact abort-contract lock)
…
862 **AB1 (exact `round_aborted(abort_record)` in every contract).** Every direct value-propagator lists the EXACT shaped
863 result `round_aborted(abort_record)` in its RETURNS union, never the bare constructor name: `PrepareParticipantsForNewRound`,
864 `ContinueTemplateRefreshAssignmentSetup`, `TemplateRefresh`, and `FullRangeExhaustNoSolution` are shaped, and
865 `SetupRetryEvent`'s RETURNS names the shaped result ONCE and ENUMERATES the re-run target dispositions explicitly (no vague
866 "target procedure's disposition"). A bare `round_aborted` may appear only as an exact pattern match, a constructor
867 invocation, or a type declaration — each with its payload — never as a result-contract alias.
…
869 **AB2 (capture the abort result before persisting `target_disposition`).** Each guard-driven abort in `SetupRetryEvent`
870 (wrong round state, retry budget exhausted, incompatible participant state, and the AB5 payload-integrity abort) executes
871 `SET disp <- CALL RoundAbort(...)` FIRST, then persists `status <- ABORTED` and `target_disposition <- disp` by key, then
872 returns `disp`. The stored `target_disposition` is the exact `round_aborted(abort_record(RoundID, TemplateID, reason))`
873 returned by `RoundAbort` — never a bare token written before the abort result exists.
```

The §3.10f AB1 clause names exactly the four shaped propagators plus `SetupRetryEvent`, matching the pseudocode RETURNS
lines verified in §2; the AB2 clause names exactly the four guards verified in §3, in the same capture-then-persist
order. The addendum states these supersede the Stage-1AA statements they name while §3.10a–§3.10e remain the frozen
W/X/Y/Z/AA layers (line 860), and AB7 (lines 901–904) records that the Stage-1AA audit claims treating bare
`round_aborted` declarations as exact contracts are superseded — the corrections are registered in
`STAGE_01AB_SUPERSESSION_REGISTER.md`.

**Finding: PASS.** §3.10f documents AB1 (five shaped propagators, single-shape-plus-enumeration for `SetupRetryEvent`)
and AB2 (capture-before-persist for the four guards), consistent with the pseudocode.

---

## 5. Test-vector linkage (TV236, TV237, TV238)

`STAGE_01AB_SEMANTIC_TEST_VECTORS.md` exercises AB1 and AB2:

- **TV236 — PrepareParticipantsForNewRound's declared and actual abort result are the exact shape (AB1)** (line 17).
  Expected: the RETURNS union lists `round_aborted(abort_record)` (not a bare `round_aborted`) and the actual value from
  `RoundAbort` is `round_aborted(abort_record(RoundID, TemplateID, reason))` — declared shape and actual value coincide,
  payload included. This is the one-to-one exercise of §2 (line 1871) and §1 class (b)/(c).
- **TV237 — ContinueTemplateRefreshAssignmentSetup and TemplateRefresh propagate the exact shape (AB1)** (line 27).
  Expected: both RETURNS unions list `round_aborted(abort_record)` with no bare alias, and each propagates the exact value
  from `RoundAbort`. This exercises §2 lines 5240 and 5137 (and, transitively, `FullRangeExhaustNoSolution` at 5043).
- **TV238 — A SetupRetryEvent guard abort captures the result, then stores that exact disp (AB2)** (line 35). Expected:
  `SET disp <- CALL RoundAbort(...)` FIRST, then `UPDATE … status <- ABORTED` and `UPDATE … target_disposition <- disp`,
  then `RETURN disp`; the stored `target_disposition` is the exact `round_aborted(abort_record(RoundID, TemplateID,
  reason))`, not a bare token written before the abort result existed. This is the direct exercise of §3.

The coverage summary registers TV236/TV237 against AB1 and TV238 against AB2 (lines 103–105), naming `RoundAbort` and the
relevant propagators. All three vectors preserve the A1 baseline `8.420833333 kWh`.

---

## 6. Verification summary

| # | Check | Result |
|---|-------|:------:|
| 1 | Whole-file `round_aborted` occurrence audit complete; every occurrence classified (a/b/c/d) | PASS |
| 2 | Zero result contracts use a bare `round_aborted` alias (bare token only in prose comments 886/890/920/923/5296) | PASS |
| 3 | `PrepareParticipantsForNewRound` RETURNS lists `round_aborted(abort_record)` (line 1871) | PASS |
| 4 | `ContinueTemplateRefreshAssignmentSetup` RETURNS lists `round_aborted(abort_record)` (line 5240) | PASS |
| 5 | `TemplateRefresh` RETURNS lists `round_aborted(abort_record)` (line 5137) | PASS |
| 6 | `FullRangeExhaustNoSolution` RETURNS lists `round_aborted(abort_record)` (line 5043) | PASS |
| 7 | `SetupRetryEvent` RETURNS names `round_aborted(abort_record)` ONCE + enumerates re-run dispositions (lines 2134–2137) | PASS |
| 8 | AB2 — payload-integrity guard captures before store (lines 2049–2053) | PASS |
| 9 | AB2 — wrong-round-state guard captures before store (lines 2086–2090) | PASS |
| 10 | AB2 — budget-exhausted guard captures before store (lines 2094–2098) | PASS |
| 11 | AB2 — incompatible-participant-state guard captures before store (lines 2100–2104) | PASS |
| 12 | Stored `target_disposition` is the exact `round_aborted(abort_record(RoundID, TemplateID, reason))` | PASS |
| 13 | Round-SM §3.10f documents AB1 and AB2 consistently with the pseudocode | PASS |
| 14 | TV236 / TV237 (AB1) and TV238 (AB2) linkage confirmed | PASS |

### Propagator RETURNS map

| Propagator | `PROCEDURE` line | RETURNS line | Shaped result present | Bare alias |
|------------|:---------------:|:------------:|:---------------------:|:----------:|
| `PrepareParticipantsForNewRound` | 1746 | 1871 | `round_aborted(abort_record)` | none |
| `ContinueTemplateRefreshAssignmentSetup` | 5145 | 5240 | `round_aborted(abort_record)` | none |
| `TemplateRefresh` | 5107 | 5137 | `round_aborted(abort_record)` | none |
| `FullRangeExhaustNoSolution` | 5008 | 5043 | `round_aborted(abort_record)` (×2 branches) | none |
| `SetupRetryEvent` | 2010 | 2134–2137 | `round_aborted(abort_record)` (once) + enumerated dispositions | none |
| `RoundAbort` (source) | 5253 | 5298 | `round_aborted(abort_record)` | none |

### AB2 guard order-of-operations

| Guard | Predicate line | `SET disp <- CALL RoundAbort` | `status <- ABORTED` | `target_disposition <- disp` | `RETURN disp` |
|-------|:--------------:|:-----------------------------:|:-------------------:|:----------------------------:|:-------------:|
| Payload-integrity (AB5-C) | 2046 | 2049 | 2051 | 2052 | 2053 |
| Wrong round state | 2085 | 2086 | 2088 | 2089 | 2090 |
| Retry budget exhausted | 2093 | 2094 | 2096 | 2097 | 2098 |
| Incompatible participant state | 2099 | 2100 | 2102 | 2103 | 2104 |

---

## 7. Result

**AB1 PASS.** `RoundAbort` is the sole abort producer and returns the single canonical result
`round_aborted(abort_record(RoundID, TemplateID, reason))` (line 5297; contract line 5298). Every direct value-propagator
lists that EXACT shaped result in its RETURNS union — `PrepareParticipantsForNewRound` (1871),
`ContinueTemplateRefreshAssignmentSetup` (5240), `TemplateRefresh` (5137), `FullRangeExhaustNoSolution` (5043), and
`SetupRetryEvent` (2135) — and `SetupRetryEvent` names the shape ONCE while enumerating the re-run target dispositions
explicitly, with no vague "target procedure's disposition" catch-all. The whole-file occurrence audit classifies all 27
occurrence lines; every executable occurrence carries the `(abort_record)` payload, and the bare `round_aborted` token is
confined to five prose comments (886, 890, 920, 923, 5296). No result contract uses a bare `round_aborted` alias.

**AB2 PASS.** Each of the four guard-driven aborts in `SetupRetryEvent` — payload-integrity (2049–2053), wrong round
state (2086–2090), retry budget exhausted (2094–2098), and incompatible participant state (2100–2104) — captures
`SET disp <- CALL RoundAbort(...)` FIRST, then performs the two keyed persistent updates
(`setup_retry_records[SetupRetryID].status <- ABORTED`, then `…target_disposition <- disp`), then `RETURN disp`. The
stored `target_disposition` is therefore the exact `round_aborted(abort_record(RoundID, TemplateID, reason))` produced by
`RoundAbort`, never a bare token written before the abort result exists, and the AA1 mapping (a target
`round_aborted` → `status = ABORTED`, never CANCELLED) holds across all four guards.

Both corrections are documented in round-SM §3.10f (AB1 lines 862–867; AB2 lines 869–873) consistently with the
pseudocode, and are exercised by TV236, TV237 (AB1) and TV238 (AB2) in `STAGE_01AB_SEMANTIC_TEST_VECTORS.md`. This audit
is documentation-only; the algorithm is **PoCol**, the mechanism is the idle policy within PoCol, and the A1 baseline
`8.420833333 kWh` is preserved.
