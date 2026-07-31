# Stage 1Q — Recovery Application-Order Audit (Q2)

**Consensus mechanism.** This audit concerns the consensus specification named **PoCol**. Within PoCol,
**the idle policy within PoCol** is referenced solely as a mechanism; no property of the consensus
mechanism is claimed here. This is documentation only, describing the frozen behaviour of
`STAGE_01_PROTOCOL_PSEUDOCODE.md`; it neither introduces nor amends any procedure. The A1 baseline of
**8.420833333 kWh** is UNCHANGED by this correction and is restated only for provenance.

**Scope.** This audit covers Stage 1Q correction **Q2 — do not apply recovery before the dispatch-time
epilogue**. It verifies that a security-recovery outcome is applied only *after* the FINAL security census
of its own application `event_time` has been published, never before. Q2 relies on the recovery-census
version published by correction Q1 (audited separately) but re-verifies the ordering here.

## 1. The two-step recovery-exit contract (§10a)

Section **§10a — "Executable security-recovery completion — two-step contract (Q2/Q3; R13/R14;
RecoveryOutcome O3)"** splits the recovery exit into two disjoint steps so that no outcome is applied
before the final census of its own application `event_time` is known:

- **Step 1 — `RecoveryCompletionDueEvent`** (microphase `RECOVERY_COMPLETION_DUE`, an ordinary queued event
  seated through `SeatRecoveryCompletion`, §10a). It only RECORDS that a `RecoveryDecisionID` is due at the
  current `event_time` (`recovery_decisions[id].due_at_event_time <- dispatch_envelope.event_time`), STASHES
  the `dispatch_envelope` (`recovery_decisions[id].due_dispatch_envelope`), and REFRESHES the census via
  `CaptureSecurityCensusOnRecoveryDeadline(RoundContext, dispatch_envelope.event_time)` (§9a, the sole
  coherent writer at that timestamp). It performs **NO** round-state transition and **NO** `RoundAbort`,
  returning `recovery_completion_due` (or `recovery_due_stale_noop` under the stale guard).

- **Step 2 — `ApplyRecoveryCompletionAfterEpilogue`** (§10a). A POST-epilogue hook invoked structurally by
  `ProcessEventTime`; it is **not** a queued microphase. It applies the recorded decision only after the
  epilogue has published the final census for that `event_time`.

Because recording and application are separated by the event-time epilogue, the census justifying the
outcome is the FINAL census at the application timestamp, not an intermediate delta-cycle census.

## 2. `ProcessEventTime` ordering: epilogue, then apply, then bounded re-evaluation (§0.7d)

Section **§0.7d — "Explicit event-time driver and security epilogue (I-02)"** fixes the order inside
`ProcessEventTime(RoundContext, t)` for a quiescent `event_time = t`:

1. **DRAIN `t`** — every ordinary and delta-cycle event at `t` is dispatched in
   `(delta_cycle, microphase, stable_tie_key, seq)` order until no ordinary event at `t` remains. A
   `RecoveryCompletionDueEvent` due at `t` is dispatched here (Step 1: records + refreshes).
2. **[horizon close]** — if `t = T` and the round is nonterminal, `CloseRoundAtHorizon` (§20b) runs between
   drain and epilogue.
3. **Epilogue #1 — `FinalizeEventTimeSecurityCensus(RoundContext, t)`** (run once if
   `security_census_dirty[t]`). While `round_state = SECURITY_RECOVERY` this is where Q1 VERSIONS the final
   recovery census (`CommitRecoveryCensus`) and RECONCILES pending decisions (`ReconcilePendingRecoveryDecisions`).
4. **Apply — `ApplyRecoveryCompletionAfterEpilogue(RoundContext, t)`** (Q2). Only now, with the final
   census/version for `t` published, is a due decision applied.
5. **Epilogue #2 — a BOUNDED re-evaluation** — if the application re-dirtied `t` (a pure round-state change,
   or a `UNRECOVERABLE` abort moving miners off `ACTIVE_HASHING`), `FinalizeEventTimeSecurityCensus(RoundContext, t)`
   runs once more. The round has now LEFT recovery (RESTORED) or is TERMINAL (UNRECOVERABLE), so this re-run
   seats no new recovery decision (`terminal_stale_noop` or a plain HASHING `no_breach`).
6. **ADD `t` to `finalised_event_times`** — `t` is closed to ordinary events. Any participation-changing
   action the applied decision creates is scheduled at a STRICTLY LATER `event_time` (I-02), so it cannot
   alter the census the epilogue already finalised at `t`.

## 3. The freshness + match check in `ApplyRecoveryCompletionAfterEpilogue` (§10a)

For each `decision_id` in `pending_recovery_decisions[episode]` whose `due_at_event_time = t` (stable order
by `decision_id`), the procedure applies the decision **only if all three conditions hold**: (i)
`D.status = SCHEDULED`; (ii) `D.bound_census_version == latest_recovery_census[episode].RecoveryCensusVersion`
(Q1 re-affirmed it — no newer final census superseded it); and (iii)
`outcome_consistent_with_census(D.outcome, census)` is true — the outcome still matches the FINAL census at
`t` (`RESTORED` requires `census.breach = false`; `UNRECOVERABLE` requires `census.breach = true AND
census.deadline_reached = true`).

If any condition fails, the decision is marked `status <- SUPERSEDED`, REMOVED from
`pending_recovery_decisions[episode]`, and `recovery_apply_stale_noop(decision_id)` is recorded; the loop
continues. On success the procedure sets `status <- APPLIED`, `recovery_outcome_finalised[episode] <-
D.outcome`, removes the decision from the pending set, sets `current_recovery_episode <- null`, and CALLS
`CompleteSecurityRecovery(RoundContext, D.due_dispatch_envelope, D.outcome)`. At most one outcome is applied
per episode (O4).

## 4. `CompleteSecurityRecovery` as internal branch dispatch (§10a)

`CompleteSecurityRecovery` (§10a) is now **INTERNAL**: NOT a queued event, called ONLY by
`ApplyRecoveryCompletionAfterEpilogue`. Because its caller has already finalised the outcome and performed
the freshness + match check, it carries **no version or idempotence guards of its own** — it is a pure
branch dispatch on `RecoveryOutcome`:

- **(A)** RESTORED with a non-empty `active_propagation_set` → `TransitionRoundState(SOLUTION_PROPAGATION)`,
  contexts + events preserved (R13/G8).
- **(B)** RESTORED with unchanged coverage → `TransitionRoundState(HASHING)` (R13).
- **(C)** RESTORED requiring redistribution/reserves → `ASSIGNMENT` then `CompleteAssignmentPhase` →
  `HASHING` under the same committed `TemplateID` (R13; no new template).
- **(D)** UNRECOVERABLE → `RoundAbort(reason = floor_unrecoverable)`, round only (R14/N1).

## 5. Worked example — a RESTORED decision rejected as stale

Let a `RESTORED` decision `D` be seated at `event_time = t` (Step 1 dispatched its
`RecoveryCompletionDueEvent`, recording `D.due_at_event_time = t`, `D.bound_census_version = v1`,
`D.status = SCHEDULED`; census at that moment showed no breach).

- During the DRAIN of `t`, a same-`t` miner departure moves that miner off `ACTIVE_HASHING`, setting
  `security_census_dirty[t]`. The FINAL census at `t` now shows a **breach**.
- Epilogue #1 `FinalizeEventTimeSecurityCensus(t)` runs: `CommitRecoveryCensus` publishes a NEWER final
  recovery census at version `v2` with `breach = true`; `ReconcilePendingRecoveryDecisions` finds
  `outcome_consistent_with_census(RESTORED, v2) = false` and SUPERSEDES `D` immediately.
- `ApplyRecoveryCompletionAfterEpilogue(t)` then examines `D`: whether via `D.status != SCHEDULED` (already
  SUPERSEDED) or via `D.bound_census_version (v1) != v2` and failing `outcome_consistent_with_census`, the
  guard fails. `D` is marked `SUPERSEDED`, removed from the pending set, `recovery_apply_stale_noop(D)` is
  recorded, and `CompleteSecurityRecovery` is NEVER called — the round does NOT leave recovery under the
  breach census, precisely because the departure altered the FINAL census of `D`'s own application
  `event_time` before the application step ran.

## 6. Proof sketch — no outcome applies before the final census of its application timestamp

Let outcome `O` from decision `D` be due at application `event_time = t`.

1. By §10a, the ONLY place an outcome is applied is `ApplyRecoveryCompletionAfterEpilogue`
   (`CompleteSecurityRecovery` is internal, called nowhere else). Step 1 `RecoveryCompletionDueEvent`
   performs no transition and no abort, so `O` cannot be applied during the drain of `t`.
2. By §0.7d, `ProcessEventTime` invokes `ApplyRecoveryCompletionAfterEpilogue(t)` strictly AFTER
   `FinalizeEventTimeSecurityCensus(t)`, itself run only once `t` is quiescent (I-01/I-02). Hence when `O`
   is applied, the FINAL security census at `t` — and, in recovery, the FINAL versioned recovery census
   (Q1) — is already published.
3. The apply guard requires `D.bound_census_version == latest_recovery_census[episode].RecoveryCensusVersion`
   AND `outcome_consistent_with_census(D.outcome, census)` against that FINAL census. Any event at `t` that
   changed participation set `security_census_dirty[t]`, forcing the epilogue to publish a newer version
   that `ReconcilePendingRecoveryDecisions` uses to supersede a contradicted `D` before the apply step
   reads it.
4. Therefore an outcome applies only when the FINAL census at `t` is known AND still justifies it; a
   RESTORED decision NEVER leaves recovery when that final census shows a breach — it is superseded/stale
   (`recovery_apply_stale_noop`). This is the KEY PROPERTY (gate 3). ∎

## 7. Acceptance checks

| # | Check | Evidence (§ / procedure) | Result |
|---|-------|--------------------------|--------|
| 1 | Recovery exit is a two-step contract; Step 1 records due + refreshes census, no transition, no abort | §10a `RecoveryCompletionDueEvent` (`RECOVERY_COMPLETION_DUE`) | PASS |
| 2 | Application runs only after the epilogue publishes the final census for `t` | §0.7d `ProcessEventTime`: epilogue #1 → `ApplyRecoveryCompletionAfterEpilogue(t)` | PASS |
| 3 | Bounded re-evaluation (epilogue #2) settles `t` and seats no new decision | §0.7d `FinalizeEventTimeSecurityCensus(t)` re-run; `terminal_stale_noop` / `no_breach` | PASS |
| 4 | Apply requires `SCHEDULED` + `bound_census_version == latest RecoveryCensusVersion` + outcome match | §10a `ApplyRecoveryCompletionAfterEpilogue`; `outcome_consistent_with_census` | PASS |
| 5 | Failing decisions are SUPERSEDED, removed from pending, `recovery_apply_stale_noop` recorded | §10a `ApplyRecoveryCompletionAfterEpilogue` | PASS |
| 6 | `CompleteSecurityRecovery` is internal, no version/idempotence guards, sole caller is the apply hook | §10a `CompleteSecurityRecovery` NOTE (R13/R14/O3) | PASS |
| 7 | KEY PROPERTY (gate 3): no outcome applied before the final census of its application `event_time`; RESTORED never exits under a breach census | §0.7d + §10a; worked example §5; proof §6 | PASS |

## Footer

This document is documentation only; it makes no property claim about the consensus mechanism. The
consensus mechanism is named **PoCol**. **The idle policy within PoCol** is referenced solely as a
mechanism. The A1 baseline of **8.420833333 kWh** is unchanged. The prohibited rebranded-algorithm-name
variants are not used anywhere in this document.
