# STAGE 01S — Census Settlement Ownership and Unconditional Epilogue Audit (S5, S6)

## Intro

This audit records TWO Stage-1S corrections (S5 and S6) to the PoCol protocol pseudocode in
`STAGE_01_PROTOCOL_PSEUDOCODE.md`. Both are OWNERSHIP / INVOCATION corrections to the event-time
security-census machinery; neither adds any consensus feature. S5 introduces ONE canonical clearer of
`security_census_dirty[event_time]` and removes the earlier contradiction in which
`FinalizeEventTimeSecurityCensus` was called the SOLE clearer while `FinalizePostRecoveryApplicationState`
(R2) also cleared the flag. S6 makes the epilogue CALL in `ProcessEventTime` unconditional and singular.

S5 and S6 change WHO clears the dirty flag and HOW the epilogue is invoked — not how time or energy is
counted. The A1 accepted baseline of **8.420833333 kWh is UNCHANGED**. No new features are introduced;
this is documentation of a settlement-ownership and invocation discipline within the existing PoCol
specification, and the mechanism under discussion is the idle policy within PoCol.

## S5 — one setter, one clearer

The two census maps `latest_security_census[event_time]` and `security_census_dirty[event_time]` retain
EXACTLY ONE writer/setter, `CommitSecurityCensus` (§0.8a). S5 adds EXACTLY ONE clearer of the dirty
flag, `SettleSecurityCensusDirty` (§0.8a), parameterised by `settlement_kind`. The two sides are now
strictly separated:

| Role | Procedure (§) | Effect on `security_census_dirty[t]` | Fan-in |
|------|---------------|--------------------------------------|--------|
| **SOLE setter / writer** | `CommitSecurityCensus` (§0.8a) | `SET … <- true` (with `latest_security_census[t]`, atomically) | FIVE `census_source` values: `MINER_STATE_TRANSITION` (`ApplyMinerStateTransition`, §0.9), `APPLICABILITY_ENTRY` (`CaptureSecurityCensusOnApplicabilityEntry`, §9), `RECOVERY_DEADLINE` (`CaptureSecurityCensusOnRecoveryDeadline` via `RecoveryDeadlineEvent`, §9a), `RECOVERY_COMPLETION_DUE` (same producer via `RecoveryCompletionDueEvent`, §10a), `POST_RECOVERY_APPLICATION` (`FinalizePostRecoveryApplicationState`, §10a) |
| **SOLE clearer** | `SettleSecurityCensusDirty` (§0.8a) | `CLEAR …` (and `RECORD security_census_dirty_settled`) | TWO `settlement_kind` values: `PRIMARY_EPILOGUE` (`FinalizeEventTimeSecurityCensus`, §9), `POST_RECOVERY_APPLICATION` (`FinalizePostRecoveryApplicationState`, §10a) |

The clearer's body is minimal and is the ONLY place the flag is cleared:

```
CLEAR security_census_dirty[event_time]
RECORD security_census_dirty_settled(event_time, settlement_kind)
```

`FinalizeEventTimeSecurityCensus` (§9), after reading the coherent census, calls
`SettleSecurityCensusDirty(RoundContext, event_time, PRIMARY_EPILOGUE)` before invoking
`SecurityFloorEvaluate`. `FinalizePostRecoveryApplicationState` (§10a), after committing the
post-application census through `CommitSecurityCensus` (source `POST_RECOVERY_APPLICATION`), calls
`SettleSecurityCensusDirty(RoundContext, t, POST_RECOVERY_APPLICATION)`. BOTH now clear ONLY through the
one procedure. The §0.8 data-model comment for `security_census_dirty` states this explicitly: the flag
is "Cleared ONLY by `SettleSecurityCensusDirty`, called by `FinalizeEventTimeSecurityCensus`
(`PRIMARY_EPILOGUE`) and `FinalizePostRecoveryApplicationState` (`POST_RECOVERY_APPLICATION`) — no
procedure clears the flag directly." The superseded normative claim that
`FinalizeEventTimeSecurityCensus` was the SOLE clearer is withdrawn, and `CommitSecurityCensus` remains
the sole setter/writer of `dirty = true` and the latest census record.

## S6 — one unconditional epilogue in the ProcessEventTime tail

S6 fixes HOW the epilogue is invoked. `ProcessEventTime` (§0.7d) must call
`FinalizeEventTimeSecurityCensus(RoundContext, t)` EXACTLY ONCE and UNCONDITIONALLY after the ordinary
drain and (at the horizon) `CloseRoundAtHorizon`. The CALL is NOT guarded by `IF security_census_dirty[t]`
— the procedure OWNS that check and returns `no_census_change` when nothing is dirty:

```
IF NOT security_census_dirty[event_time]:
  RETURN no_census_change
```

Because the check lives inside the procedure, the driver need not (and must not) replicate it. This is
what makes the epilogue impossible to "miss": it is invoked structurally by the driver after quiescence,
not dispatched from the queue and not gated by an ambient flag test at the call site.

### Walk of the canonical event-time tail (§0.7d)

After the drain LOOP has emptied every ordinary and delta-cycle event at `t` (and, at `t = T`, after the
`CloseRoundAtHorizon` horizon-close hook has run), `ProcessEventTime` executes exactly three ordered
CALLs, then asserts and finalises:

```
CALL FinalizeEventTimeSecurityCensus(RoundContext, t)        # step 1: the ONE (UNCONDITIONAL) security epilogue
CALL ApplyRecoveryCompletionAfterEpilogue(RoundContext, t)   # step 2: post-quiescence recovery application (Q2/R4)
CALL FinalizePostRecoveryApplicationState(RoundContext, t)   # step 3: single post-application settlement (NOT a 2nd decision)
ASSERT no ordinary event remains with event_time = t         # R1: the application enqueued NOTHING at t
ASSERT security_census_dirty[t] = false                      # settled: step 1 and/or step 3 cleared the flag
ADD t to finalised_event_times
```

- **Step 1 (unconditional single epilogue).** `FinalizeEventTimeSecurityCensus` runs once. If `t` was
  dirty it reads `latest_security_census[t]`, clears the flag via `SettleSecurityCensusDirty(…,
  PRIMARY_EPILOGUE)`, then runs the ONE `SecurityFloorEvaluate` for `t`. If `t` was NOT dirty it returns
  `no_census_change` and clears nothing. Either way the CALL happened exactly once and was not guarded.
- **Step 2 (apply).** `ApplyRecoveryCompletionAfterEpilogue` applies AT MOST ONE fresh, matching, due
  recovery decision. Its exit transition may re-dirty `t` (a `MINER_STATE_TRANSITION` for an unrecoverable
  abort, or an `APPLICABILITY_ENTRY` restatement for a restored exit) — always through the sole setter
  `CommitSecurityCensus`. R1 forbids it from enqueuing any ordinary event at the already-drained `t`.
- **Step 3 (settlement).** `FinalizePostRecoveryApplicationState` runs once. If step 2 re-dirtied `t` it
  archives that terminal/post-application census through `CommitSecurityCensus` (source
  `POST_RECOVERY_APPLICATION`) and clears the flag via
  `SettleSecurityCensusDirty(…, POST_RECOVERY_APPLICATION)` — WITHOUT a second `SecurityFloorEvaluate`.
  If `t` was not re-dirtied it
  is a `post_recovery_settlement_noop`.

The declared order is therefore epilogue → apply → settlement, with `ApplyRecoveryCompletionAfterEpilogue`
and `FinalizePostRecoveryApplicationState` running after the single unconditional epilogue, exactly as S6
requires. The `ASSERT security_census_dirty[t] = false` then holds because whichever of step 1 or step 3
last touched the flag cleared it through the one clearer, guaranteeing `t` is quiescent AND settled before
it enters `finalised_event_times`.

## Confirmation: no stray `CLEAR security_census_dirty`

A full-document scan finds exactly ONE `CLEAR security_census_dirty[…]` statement, and it is inside the
body of `SettleSecurityCensusDirty` (§0.8a). No other procedure — not
`FinalizeEventTimeSecurityCensus`, not `FinalizePostRecoveryApplicationState`, not
`ProcessEventTime`, not any capture procedure — clears the flag directly. Every clear is routed through
the one clearer with an explicit `settlement_kind`, and every set is routed through the one setter
`CommitSecurityCensus` with an explicit `census_source`. The setter/clearer separation is therefore
STRUCTURAL, not a per-caller discipline.

## Result

After S5 and S6 the event-time dirty flag has exactly one setter and exactly one clearer:
`CommitSecurityCensus` (§0.8a) SETS `security_census_dirty[t] = true` (atomically with
`latest_security_census[t]`) from FIVE named sources, and `SettleSecurityCensusDirty` (§0.8a) is the ONLY
procedure that CLEARS it, from TWO named `settlement_kind` callers — `FinalizeEventTimeSecurityCensus`
(`PRIMARY_EPILOGUE`) and `FinalizePostRecoveryApplicationState` (`POST_RECOVERY_APPLICATION`). The §0.8
data model and every normative statement now agree, and the earlier "sole clearer =
`FinalizeEventTimeSecurityCensus`" contradiction is removed. `ProcessEventTime` (§0.7d) calls the epilogue
EXACTLY ONCE and UNCONDITIONALLY after the drain and horizon close — the CALL is never guarded by
`IF security_census_dirty[t]` because the procedure owns that check and returns `no_census_change` when
nothing is dirty — after which `ApplyRecoveryCompletionAfterEpilogue` and
`FinalizePostRecoveryApplicationState` run in the declared order, and the tail asserts
`security_census_dirty[t] = false` before finalising `t`. No accounting of time or energy changed: the A1
accepted baseline of 8.420833333 kWh is UNCHANGED, and no consensus feature was added. S5 and S6 are
ownership and invocation corrections documented here only.

The prohibited rebranded-algorithm-name variants are not used anywhere in this document.
