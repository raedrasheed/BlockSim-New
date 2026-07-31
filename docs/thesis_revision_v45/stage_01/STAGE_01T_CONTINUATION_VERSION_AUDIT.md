# STAGE 01T — Recovery Continuation Version Binding and Generation Identity Audit (T2)

## Intro

This audit records ONE Stage-1T correction (T2) to the PoCol protocol pseudocode in
`STAGE_01_PROTOCOL_PSEUDOCODE.md`. T2 is a PROVENANCE / VERSIONING correction to the deferred branch-C
recovery continuation: it fixes WHERE a continuation reads its bound census version and WHICH continuation
identity is allowed to apply. It adds no consensus feature. The immutable, queued
`RecoveryAssignmentContinuationDueEvent` carries ONLY a `ContinuationGeneration`; the AUTHORITATIVE bound
census version is the decision-record field `continuation_bound_census_version`, which
`ReconcilePendingRecoveryDecisions` keeps current and which `ApplyRecoveryAssignmentContinuationAfterEpilogue`
reads and COMPARES against the latest final census before it applies branch C.

T2 changes how a deferred continuation is VERSIONED and IDENTIFIED — not how time or energy is counted. The
A1 accepted baseline of **8.420833333 kWh is UNCHANGED**. No new features are introduced; this is
documentation of a version-binding and identity discipline within the existing PoCol specification, and the
energy mechanism under discussion is the idle policy within PoCol. This document asserts no property; it
describes the exact tests the named procedures perform.

## T2 — the authoritative bound version versus the immutable due event

Each branch-C continuation carries a `RecoveryContinuationID = (RecoveryDecisionID, continuation_generation)`
(§0.8), where `RecoveryDecisionID = (RecoveryEpisodeID, recovery_decision_seq)` (§0.8, P5). The §0.8
`recovery_decisions` `decision_record` holds three continuation fields relevant here — `continuation_generation`,
`continuation_id`, and `continuation_bound_census_version` — and the §0.8 registry states their roles
verbatim: "T2: `continuation_generation` / `continuation_id` identify the ACTIVE continuation (a
reserve-dependent re-arm bumps the generation), and `continuation_bound_census_version` is the AUTHORITATIVE
bound version that `ReconcilePendingRecoveryDecisions` keeps current and that
`ApplyRecoveryAssignmentContinuationAfterEpilogue` reads + verifies against the latest final census — the
immutable due event carries only the generation, never a stale version."

The split has two consequences, one per axis of staleness:

- **Version axis.** The version a continuation binds to is NOT frozen into the queued event at seat time.
  If it were, a re-affirmation of the decision against a newer final census could not update it, and the
  continuation would apply against an outdated census version. Instead the version lives in the mutable
  record field `continuation_bound_census_version` and is advanced by rule B of
  `ReconcilePendingRecoveryDecisions` (§9) on every re-affirming epilogue.
- **Identity axis.** The `ContinuationGeneration` carried by the event is COMPARED against the record's
  ACTIVE `continuation_generation`. A reserve-dependent re-arm mints a FRESH generation, so any
  superseded/older Due event no longer matches the active generation and stale-noops rather than reviving a
  superseded continuation.

## The mint -> reconcile -> due-guard -> apply flow

`ProcessEventTime` runs the T1 canonical tail — the ONE epilogue `FinalizeEventTimeSecurityCensus(t)` (which
publishes the final census via `CommitRecoveryCensus` and runs `ReconcilePendingRecoveryDecisions`), then
`ApplyRecoveryCompletionAfterEpilogue(t)`, then `ApplyRecoveryAssignmentContinuationAfterEpilogue(t)`. Version
binding is exercised across four named points in that flow.

### 1. Mint — `CompleteSecurityRecovery` branch C (§10a)

Branch C (RESTORED requiring range redistribution or new reserve assignment) is DEFERRED. After computing
`t_cont <- next_representable_simulation_time(t)` and validating `t_cont <= T`, the procedure MINTS the
continuation identity and binds it to the current version BEFORE seating anything:

```
SET recovery_decisions[decision_id].continuation_generation <- 1
SET recovery_decisions[decision_id].continuation_id <- (decision_id, 1)
SET recovery_decisions[decision_id].continuation_bound_census_version <- bound_census_version
```

It then seats ONE `RecoveryAssignmentContinuationDueEvent` at `t_cont` whose payload carries
`ContinuationGeneration = 1` — the GENERATION, "not a raw census version" (§10a). The authoritative version
is the record field just set; the event deliberately does not embed it.

### 2. Reconcile — `ReconcilePendingRecoveryDecisions` rule B (§9)

On every final census, this procedure supersedes-or-re-affirms each pending decision. For a decision whose
outcome is still consistent with the newer final census (rule B, the re-affirm branch), it advances the
authoritative continuation version to the latest `RecoveryCensusVersion`:

```
IF recovery_decisions[decision_id].continuation_id != null:
  SET recovery_decisions[decision_id].continuation_bound_census_version <- census.RecoveryCensusVersion   # T2
```

The inline comment states the intent: "keep the AUTHORITATIVE continuation bound version CURRENT too, so a
re-affirmed DEFERRED branch-C decision's continuation applies against the LATEST final census (its immutable
due event carries only the generation, never a stale version)." A decision CONTRADICTED by the census takes
the supersede branch instead: `SetRecoveryDecisionStatus(..., SUPERSEDED)`, its
`continuation_event_ref` is CANCELLED on EQ, and it is removed from `pending_recovery_decisions[episode]` — so
a superseded continuation is cancelled rather than re-versioned, and "a superseded decision NEVER becomes
valid again."

### 3. Due-guard — `RecoveryAssignmentContinuationDueEvent` (§10a)

When the Due event dispatches at `t_cont`, its stale + identity guard checks the ACTIVE generation among
its other predicates:

```
OR ContinuationGeneration != D.continuation_generation                    # T2: only the ACTIVE continuation generation
```

alongside `round_state != SECURITY_RECOVERY`, `current_recovery_episode != episode`, the decision not being
in the pending set, `D.status != APPLYING`, a finalised outcome, or a mismatched
round/template/state_version. If the carried generation is not the active one — the case a superseded or
older Due event lands after a re-arm — the handler returns `recovery_continuation_due_stale_noop` and records
NO due fact. This event never applies branch C; it only records the due fact and refreshes the census.

### 4. Apply (freshness + version binding) — `ApplyRecoveryAssignmentContinuationAfterEpilogue` (§10a)

This post-epilogue hook is the ONLY place branch-C RESTORED is applied. After locating the decision whose
`continuation_due_at_event_time = t`, it performs the T2 freshness + version-binding check by READING the
authoritative record field and COMPARING it to the just-published final census version:

```
IF round_state != SECURITY_RECOVERY
   OR D.status != APPLYING
   OR D.continuation_bound_census_version != census.RecoveryCensusVersion
   OR NOT outcome_consistent_with_census(RESTORED, census):
  RECORD recovery_continuation_apply_stale_noop(decision_id)
  RETURN recovery_continuation_apply_stale(decision_id)
```

with `census <- latest_recovery_census[episode]`. The comment is explicit that the version "is READ from the
AUTHORITATIVE decision record (`continuation_bound_census_version`, kept current by
`ReconcilePendingRecoveryDecisions`, T2 rule B) and COMPARED to
`latest_recovery_census[episode].RecoveryCensusVersion` — the carried version is not silently ignored."
Branch C is applied ONLY when the ACTIVE generation matched at the Due-guard, the bound version equals the
final census version, and `outcome_consistent_with_census(RESTORED, census)` still holds. Otherwise it is a
stale-noop — never a wrong-version application.

### Reserve-dependent re-arm — a FRESH generation (§10a)

When the final census warrants RESTORED only via reserves not yet ACTIVE_HASHING (T6-B), the hook does not
finalise. It activates the reserve(s), keeps the decision APPLYING with the round in SECURITY_RECOVERY, and
re-arms a strictly-later continuation with a bumped generation:

```
SET recovery_decisions[decision_id].continuation_generation <- D.continuation_generation + 1
SET recovery_decisions[decision_id].continuation_id <- (decision_id, recovery_decisions[decision_id].continuation_generation)   # T2: fresh ACTIVE continuation
```

The re-armed Due event carries the NEW `ContinuationGeneration`. Any earlier/superseded Due event for the
same decision now carries a generation `!= D.continuation_generation` and stale-noops at the §10a Due-guard,
so an older continuation cannot revive after the fresh one is armed.

## PASS-check table

| Check | Procedure (§) | Exact test / assignment (verbatim) | What it prevents |
|-------|---------------|-------------------------------------|------------------|
| Identity is `(decision, generation)` | §0.8 registry | `RecoveryContinuationID = (RecoveryDecisionID, continuation_generation)` | An unversioned continuation with no active-identity comparison |
| Mint binds current version | `CompleteSecurityRecovery` branch C (§10a) | `SET recovery_decisions[decision_id].continuation_bound_census_version <- bound_census_version` | The bound version being frozen into the immutable event |
| Event carries generation only | `CompleteSecurityRecovery` branch C (§10a) | payload `ContinuationGeneration = 1` (comment: "carries the GENERATION, not a raw census version") | A stale raw census version travelling in the queue |
| Re-affirm keeps version current | `ReconcilePendingRecoveryDecisions` rule B (§9) | `SET recovery_decisions[decision_id].continuation_bound_census_version <- census.RecoveryCensusVersion` | A re-affirmed continuation applying against an outdated version |
| Supersede cancels continuation | `ReconcilePendingRecoveryDecisions` (§9) | `CANCEL D.continuation_event_ref on EQ` + remove from `pending_recovery_decisions[episode]` | A contradicted continuation surviving to apply |
| Due-guard checks active generation | `RecoveryAssignmentContinuationDueEvent` (§10a) | `OR ContinuationGeneration != D.continuation_generation` -> `recovery_continuation_due_stale_noop` | A superseded/older Due event recording a due fact |
| Apply verifies version + freshness | `ApplyRecoveryAssignmentContinuationAfterEpilogue` (§10a) | `OR D.continuation_bound_census_version != census.RecoveryCensusVersion` -> `recovery_continuation_apply_stale` | Applying branch C against a stale census version |
| Apply re-checks warrant | `ApplyRecoveryAssignmentContinuationAfterEpilogue` (§10a) | `OR NOT outcome_consistent_with_census(RESTORED, census)` | Restoring when the final census no longer warrants RESTORED |
| Re-arm mints fresh generation | `ApplyRecoveryAssignmentContinuationAfterEpilogue` (§10a, T6-B) | `SET recovery_decisions[decision_id].continuation_generation <- D.continuation_generation + 1` | An older continuation reviving after a newer final census |

## Failure mode contrasted

Without T2 the deferred continuation would be exposed on both axes. On the VERSION axis, if the bound
census version were embedded in the immutable `RecoveryAssignmentContinuationDueEvent` at seat time, a later
re-affirming epilogue (`ReconcilePendingRecoveryDecisions`) could advance the decision to a newer
`RecoveryCensusVersion` while the queued event still named the old one — and, with the apply hook trusting
the carried value instead of `continuation_bound_census_version`, branch C could install a redistribution
computed against an OUTDATED census version. T2 removes this by keeping the version in the mutable record,
advancing it in rule B, and forcing
`D.continuation_bound_census_version != census.RecoveryCensusVersion -> stale-noop` at
`ApplyRecoveryAssignmentContinuationAfterEpilogue`.

On the IDENTITY axis, without a generation comparison a reserve-dependent path could leave an OLDER Due event
live on the queue; after the reserve wakes and a newer final census re-checks, that stale event could fire
and revive a superseded continuation, applying an install the latest census no longer justifies. T2 removes
this by bumping `continuation_generation` on every re-arm and rejecting any event whose
`ContinuationGeneration != D.continuation_generation` at the §10a Due-guard, so only the ACTIVE continuation
proceeds and a superseded/older one stale-noops.

## Result

After T2 the deferred branch-C continuation is version-bound and identity-checked on both axes. The
`RecoveryAssignmentContinuationDueEvent` carries ONLY `ContinuationGeneration`; the authoritative bound
version is `continuation_bound_census_version`, minted current by `CompleteSecurityRecovery` branch C, kept
current by rule B of `ReconcilePendingRecoveryDecisions` (§9), and READ + COMPARED against
`latest_recovery_census[episode].RecoveryCensusVersion` by `ApplyRecoveryAssignmentContinuationAfterEpilogue`
(§10a) before any application. A superseded decision has its continuation CANCELLED at reconcile; an older
generation stale-noops at the §10a Due-guard against the ACTIVE `continuation_generation`; and a
reserve-dependent re-arm mints a FRESH generation so no earlier continuation revives after a newer final
census. No accounting of time or energy changed: the A1 accepted baseline of 8.420833333 kWh is UNCHANGED,
and no consensus feature was added. T2 is a provenance and version-binding correction documented here only,
and the mechanism under discussion is the idle policy within PoCol.

The prohibited rebranded-algorithm-name variants are not used anywhere in this document.
