# Stage 1AE — Global Queue-Owner Cancellation Audit (corrections AE1 + AE2)

This is a documentation-only audit of corrections **AE1** ("one global queue-owner cancellation operation") and **AE2**
("every cancel site reconciled") in the Stage-1 formal specification of **PoCol** and the idle policy within PoCol. It
verifies, against the after-final, frozen source of truth `STAGE_01_PROTOCOL_PSEUDOCODE.md` (read-only), that a single
procedure `CancelQueuedEvent(EventRef, cancellation_reason, cancellation_context)` is the SOLE operation that removes an
`EventRef` from `EQ`, that it owns the atomic EQ-removal together with the central `queued_event_registry` state update
(`QUEUED → CANCELLED`), that NO procedure executes a raw `CANCEL <ref> on EQ`, that every remaining textual `CANCEL `
occurrence is a comment or the `CancelQueuedEvent` doc line (never an executable raw cancel), that every protocol cancel
site is reconciled to a `CALL CancelQueuedEvent`, that set cancellations iterate their EventRefs in stable order calling
the owner once each, that no event removed from EQ can remain `QUEUED` in the registry (both structures change
atomically), and that `CancelSetupRetriesForRound` no longer performs its own separate `queue_status <- CANCELLED` write.
No specification document is modified by this audit; every quoted line is a current line of the after-final frozen source
of truth, quoted with an approximate line anchor. The algorithm remains **PoCol** and the mechanism remains the idle
policy within PoCol. The A1 baseline `8.420833333 kWh` is preserved.

- **Corrections:** AE1 (one global cancellation operation); AE2 (every cancel site reconciled).
- **Source of truth (read-only):** `STAGE_01_PROTOCOL_PSEUDOCODE.md`.
- **Owner procedure:** `PROCEDURE CancelQueuedEvent` (`STAGE_01_PROTOCOL_PSEUDOCODE.md:642`–`:676`).
- **Cross-references:** `STAGE_01_ROUND_STATE_MACHINE.md` §3.10i **AE1/AE2** (`:1034`–`:1042`);
  `STAGE_01_TERMINOLOGY.md` Stage-1AE addendum (`:1116`–`:1121`); `STAGE_01AE_SEMANTIC_TEST_VECTORS.md`
  **TV262 / TV263 / TV272**.

---

## The one queue-owner cancellation operation (AE1)

`CancelQueuedEvent` has EXACTLY the four declared branches, verbatim from the after-final pseudocode
(`STAGE_01_PROTOCOL_PSEUDOCODE.md:649`–`:667`):

- unknown EventRef → `RETURN cancellation_unknown_event(EventRef)` (`:651`–`:652`) — a declared no-op, not an assert;
- `QUEUED` → `ATOMICALLY: REMOVE EventRef FROM EQ.event_queue` + `SET queued_event_registry[EventRef].queue_status <-
  CANCELLED` + `RECORD queued_event_cancelled(...)` then `RETURN event_cancelled(EventRef)` (`:657`–`:661`);
- `DISPATCHING` → `RETURN event_already_dispatching(EventRef)` with NO mutation (`:662`–`:665`);
- `CONSUMED` / `CANCELLED` (terminal) → `RETURN cancellation_terminal_noop(EventRef)` (`:666`–`:667`).

Ownership is stated globally at `:534`–`:535`: "`CancelQueuedEvent` is the SOLE writer of the CANCELLATION edge
(`QUEUED -> CANCELLED`) and the SOLE operation that removes an EventRef from EQ. No other procedure writes queue_status or
removes an EventRef from EQ." A whole-file search confirms the ONLY executable `REMOVE ... FROM EQ.event_queue` is `:658`
and the ONLY executable `queued_event_registry[...].queue_status <- CANCELLED` is `:659` — both inside this procedure.

---

## Reconciled cancel sites — every `CALL CancelQueuedEvent` (AE2)

A whole-file search returns EXACTLY **31** `CALL CancelQueuedEvent` sites; every former raw cancel now routes through the
owner. The "old raw form" column reconstructs the pre-AE2 raw operation (a raw `CANCEL <ref> on EQ`, plus for the setup
terminaliser an additional separate `queue_status <- CANCELLED` write); the current spec contains none of these raw forms.

| # | ~L | Enclosing procedure (site) | Old raw form (pre-AE2) | Now (AE2) |
|---|----|----------------------------|------------------------|-----------|
| 1 | 1701 | `StartWake` — transition-failure rollback | `CANCEL wake_event_ref on EQ` | `CALL CancelQueuedEvent(wake_event_ref, wake_rollback_before_transition, …)` |
| 2 | 2259 | `AbortPendingWakeForRollback` (null-guarded) | `CANCEL WakeEventRef on EQ` | `CALL CancelQueuedEvent(WakeEventRef, wake_abort_for_rollback, …)` |
| 3 | 2555 | `CancelSetupRetriesForRound` — per-record | `CANCEL seat_event_ref on EQ` + separate `queue_status <- CANCELLED` | `CALL CancelQueuedEvent(snapshot.seat_event_ref, cancellation_reason, …)` |
| 4 | 2776 | `RangeAssignFromPlan` — wake rollback | `CANCEL wref on EQ` | `CALL CancelQueuedEvent(wref, wake_superseded_rollback, …)` |
| 5 | 3127 | `AdversarialParticipationChangeEvent` — hash-work set | `CANCEL er on EQ` (per HashWorkEvent) | `CALL CancelQueuedEvent(er, adversarial_withdrawal, …)` |
| 6 | 3457 | `CancelActiveRecoveryEpisode` — decision due | `CANCEL D.due_event_ref on EQ` | `CALL CancelQueuedEvent(D.due_event_ref, recovery_episode_cancelled, …)` |
| 7 | 3459 | `CancelActiveRecoveryEpisode` — continuation | `CANCEL D.continuation_event_ref on EQ` | `CALL CancelQueuedEvent(D.continuation_event_ref, recovery_episode_cancelled, …)` |
| 8 | 3469 | `CancelActiveRecoveryEpisode` — work due | `CANCEL W.work_due_event_ref on EQ` | `CALL CancelQueuedEvent(W.work_due_event_ref, recovery_episode_cancelled, …)` |
| 9 | 3513 | `ReconcilePendingRecoveryDecisions` — due | `CANCEL D.due_event_ref on EQ` | `CALL CancelQueuedEvent(D.due_event_ref, recovery_decision_superseded, …)` |
| 10 | 3515 | `ReconcilePendingRecoveryDecisions` — continuation | `CANCEL D.continuation_event_ref on EQ` | `CALL CancelQueuedEvent(D.continuation_event_ref, recovery_decision_superseded, …)` |
| 11 | 3551 | `ReconcilePendingRecoveryWork` (null-guarded) | `CANCEL W.work_due_event_ref on EQ` | `CALL CancelQueuedEvent(W.work_due_event_ref, recovery_work_superseded, …)` |
| 12 | 3561 | `ReconcilePendingRecoveryWork` (null-guarded) | `CANCEL W.work_due_event_ref on EQ` | `CALL CancelQueuedEvent(W.work_due_event_ref, recovery_work_superseded, …)` |
| 13 | 3748 | `SeatRecoveryWork` — stale prior work (null-guarded) | `CANCEL W0.work_due_event_ref on EQ` | `CALL CancelQueuedEvent(W0.work_due_event_ref, recovery_work_stale_superseded, …)` |
| 14 | 3962 | `ReserveActivateFromPlan` — wake rollback | `CANCEL wref on EQ` | `CALL CancelQueuedEvent(wref, wake_superseded_rollback, …)` |
| 15 | 4541 | `RollbackRecoveryAssignmentPlan` — per-item wake | `CANCEL item.WakeEventRef on EQ` | `CALL CancelQueuedEvent(item.WakeEventRef, recovery_plan_rolled_back, …)` |
| 16 | 4707 | `LeaseExpiry` — CLOSED head, ResumeFromPause set | `CANCEL er on EQ` | `CALL CancelQueuedEvent(er, assignment_closed_lease_expiry, …)` |
| 17 | 4713 | `LeaseExpiry` — CLOSED head, WakeCompleteEvent set | `CANCEL er on EQ` | `CALL CancelQueuedEvent(er, assignment_closed_lease_expiry, …)` |
| 18 | 4732 | `LeaseExpiry` — PENDING head, WakeCompleteEvent set | `CANCEL er on EQ` | `CALL CancelQueuedEvent(er, pending_lease_expiry, …)` |
| 19 | 4841 | `RangeReassignFromPlan` — wake rollback | `CANCEL wref on EQ` | `CALL CancelQueuedEvent(wref, wake_superseded_rollback, …)` |
| 20 | 5211 | `HandlePropagationFailure` — certificate-arrival set | `CANCEL er on EQ` | `CALL CancelQueuedEvent(er, propagation_failed(failure_reason), …)` |
| 21 | 5212 | `HandlePropagationFailure` — block-arrival (null-guarded) | `CANCEL block_arrival_event(cpc) on EQ` | `CALL CancelQueuedEvent(block_arrival_event(cpc), propagation_failed(…), …)` |
| 22 | 5352 | `ValidBlockAccept` — cross-candidate cert set | `CANCEL er on EQ` | `CALL CancelQueuedEvent(er, candidate_superseded_by_acceptance, …)` |
| 23 | 5353 | `ValidBlockAccept` — loser block-arrival (null-guarded) | `CANCEL block_arrival_event(other) on EQ` | `CALL CancelQueuedEvent(block_arrival_event(other), candidate_superseded_by_acceptance, …)` |
| 24 | 5426 | `CloseRoundAssignments` — WAKING wake set | `CANCEL er on EQ` | `CALL CancelQueuedEvent(er, round_closed_while_waking, …)` |
| 25 | 5451 | `CloseRoundAssignments` — closing-round sweep | `CANCEL er on EQ` | `CALL CancelQueuedEvent(er, round_closed(RoundID), …)` |
| 26 | 5565 | `CloseTemplateAssignments` — WAKING wake set | `CANCEL er on EQ` | `CALL CancelQueuedEvent(er, template_refresh_wake_abort, …)` |
| 27 | 5577 | `CloseTemplateAssignments` — candidate cert set | `CANCEL er on EQ` | `CALL CancelQueuedEvent(er, template_refresh_discard, …)` |
| 28 | 5578 | `CloseTemplateAssignments` — candidate block (null-guarded) | `CANCEL block_arrival_event(cpc) on EQ` | `CALL CancelQueuedEvent(block_arrival_event(cpc), template_refresh_discard, …)` |
| 29 | 5585 | `CloseTemplateAssignments` — old-template sweep | `CANCEL er on EQ` | `CALL CancelQueuedEvent(er, template_closure(old_TemplateID), …)` |
| 30 | 5766 | `RoundAbort` — candidate cert set | `CANCEL er on EQ` | `CALL CancelQueuedEvent(er, round_aborted_cleanup, …)` |
| 31 | 5767 | `RoundAbort` — candidate block (null-guarded) | `CANCEL block_arrival_event(cpc) on EQ` | `CALL CancelQueuedEvent(block_arrival_event(cpc), round_aborted_cleanup, …)` |

**Minimum-set coverage (from the correction spec).** Every named minimum-set site is present above:
`AbortPendingWakeForRollback` (#2), `StartWake` transition-failure rollback (#1), `HandlePropagationFailure` (#20–#21),
`ValidBlockAccept` (#22–#23), `CloseTemplateAssignments` (#26–#29), `CloseRoundAssignments` (#24–#25), `RoundAbort`
(#30–#31), recovery deadline / completion / work cancellation (`CancelActiveRecoveryEpisode` #6–#8,
`ReconcilePendingRecoveryDecisions` #9–#10, `ReconcilePendingRecoveryWork` #11–#12, `SeatRecoveryWork` #13,
`RollbackRecoveryAssignmentPlan` #15), candidate event cleanup (#20–#23, #27–#28, #30–#31, plus the adversarial
hash-work set #5), setup-retry cancellation (`CancelSetupRetriesForRound` #3), and `LeaseExpiry` (#16–#18). No
minimum-set site is unreconciled.

**Every remaining textual `CANCEL ` occurrence is a comment or the owner doc line — none executable.** A whole-file
search for `CANCEL ` returns eight occurrences; all are prose:

| ~L | Occurrence | Classification |
|----|-----------|----------------|
| 210 | `# AE3: … a handler may CANCEL a LATER` | comment (AE3 dispatch-loop note) |
| 645 | `PRECONDITIONS: … NO procedure executes a raw \`CANCEL <ref> on EQ\`` | `CancelQueuedEvent` doc line (the prohibition itself) |
| 846 | `#   target, O2 — the event was never enqueued); every CANCEL of it is null-guarded.` | comment |
| 1698 | `#     the seat -> CANCEL the seated WakeCompleteEvent …` | comment (describes site #1) |
| 3744 | `# V7: … ATOMICALLY SUPERSEDE/CANCEL it and` | comment (describes site #13) |
| 4700 | `# M3: explicitly CANCEL any candidate-specific resume/wake events …` | comment (describes sites #16–#17) |
| 4726 | `# (1)-(2) M3: identify and CANCEL the exact pending WakeCompleteEvent …` | comment (describes site #18) |
| 5115 | `#      rejection leaves block_arrival_event(cpc) = null so a later CANCEL is a no-op …` | comment |

No occurrence is an executable raw cancel; there is no residual `CANCEL <ref> on EQ` statement anywhere in the pseudocode.

---

## Checks

| Check | Result |
|-------|--------|
| C1. `PROCEDURE CancelQueuedEvent(EventRef, cancellation_reason, cancellation_context)` exists with EXACTLY the four branches — unknown → `cancellation_unknown_event`; `QUEUED` → atomic EQ-remove + `QUEUED → CANCELLED` + `event_cancelled`; `DISPATCHING` → `event_already_dispatching` (no mutation); `CONSUMED`/`CANCELLED` → `cancellation_terminal_noop`. | **PASS** — `PROCEDURE CancelQueuedEvent` `:642`; `INPUTS: EventRef, cancellation_reason, cancellation_context` `:643`; unknown `RETURN cancellation_unknown_event(EventRef)` `:652`; QUEUED branch `:654`–`:661`; `RETURN event_already_dispatching(EventRef)` `:665`; `RETURN cancellation_terminal_noop(EventRef)` `:667`. Confirmed by **TV272** (a `DISPATCHING` cancel is a no-op). |
| C2. `CancelQueuedEvent` OWNS the atomic EQ-removal + central registry update. | **PASS** — `ATOMICALLY: REMOVE EventRef FROM EQ.event_queue` `:658` + `SET queued_event_registry[EventRef].queue_status <- CANCELLED` `:659`; "the SOLE writer of the CANCELLATION edge … and the SOLE operation that removes an EventRef from EQ" `:534`–`:535`. |
| C3. NO procedure executes a raw `CANCEL <ref> on EQ`; every remaining `CANCEL ` occurrence is a comment or the owner doc line. | **PASS** — `PRECONDITIONS: … NO procedure executes a raw \`CANCEL <ref> on EQ\`` `:645`; the eight `CANCEL ` hits (`:210`, `:645`, `:846`, `:1698`, `:3744`, `:4700`, `:4726`, `:5115`) are all comments or the doc line (table above). No residual executable raw cancel. Confirmed by **TV262** ("No raw `CANCEL E on EQ` occurs"). |
| C4. Exactly ~31 `CALL CancelQueuedEvent` sites; the spec's minimum set is covered. | **PASS** — a whole-file search returns 31 `CALL CancelQueuedEvent` sites (enumerated #1–#31, `:1701`–`:5767`); every minimum-set site — `AbortPendingWakeForRollback`, `StartWake` rollback, `HandlePropagationFailure`, `ValidBlockAccept`, `CloseTemplateAssignments`, `CloseRoundAssignments`, `RoundAbort`, recovery deadline/completion/work cancellation, candidate event cleanup, `CancelSetupRetriesForRound`, `LeaseExpiry` — appears in the table. Confirmed by **TV262**/**TV263**. |
| C5. Set cancellations iterate EventRefs in stable order, calling `CancelQueuedEvent` once each. | **PASS** — `FOR EACH er IN certificate_arrival_events(cpc) IN stable EventRef order: CALL CancelQueuedEvent(er, …)` `:5211`; `FOR EACH er IN SORT({ … QUEUED … RoundID = RoundID } IN stable EventRef order): CALL CancelQueuedEvent(er, …)` `:5448`–`:5451`; `FOR EACH other cpc in SORT(active_propagation_set BY CandidateID ascending) … CALL CancelQueuedEvent(er, …)` `:5350`–`:5352`; NOTE "a set cancellation iterates its EventRefs in stable order and calls this once each" `:675`–`:676`. Confirmed by **TV262**. |
| C6. No event removed from EQ remains `QUEUED` in the registry (both change atomically). | **PASS** — the QUEUED branch removes from EQ and sets `CANCELLED` inside one `ATOMICALLY` block `:657`–`:659` ("so no event ever leaves EQ while still QUEUED in the registry and no QUEUED ghost survives" `:655`–`:656`); AE10 coherence "CancelQueuedEvent removes both together" `:546`. Confirmed by **TV262** ("no QUEUED ghost of `E` remains (I21)") and **TV263** ("a later re-read of `W` yields `CANCELLED`"). |
| C7. `CancelSetupRetriesForRound` no longer does a separate `queue_status <- CANCELLED` write — the owner does it. | **PASS** — `CALL CancelQueuedEvent(snapshot.seat_event_ref, …)` `:2555`, with the inline note "no separate queue_status write here — AE1 owns it" `:2552`–`:2553`; a whole-file search finds the ONLY executable `queued_event_registry[...].queue_status <- CANCELLED` at `:659` (inside `CancelQueuedEvent`), none inside `CancelSetupRetriesForRound` (`:2536`–`:2593`). |
| C8. `AbortPendingWakeForRollback` cancels its `QUEUED` `WakeCompleteEvent` through the same owner. | **PASS** — `IF WakeEventRef != null: CALL CancelQueuedEvent(WakeEventRef, wake_abort_for_rollback, …)` `:2259` (null-guarded, "no-op if not QUEUED"). Confirmed by **TV263**. |

---

## Result

**PASS — all checks PASS; no FAIL found.** AE1 and AE2 are faithfully specified in the after-final frozen source.
`PROCEDURE CancelQueuedEvent` (`:642`–`:676`) is the ONE queue-owner cancellation operation, with exactly the four
declared branches (unknown → `cancellation_unknown_event`; `QUEUED` → atomic EQ-remove + `QUEUED → CANCELLED` +
`event_cancelled`; `DISPATCHING` → `event_already_dispatching` with no mutation; `CONSUMED`/`CANCELLED` →
`cancellation_terminal_noop`), and it owns the single atomic block (`:657`–`:659`) that removes an `EventRef` from
`EQ.event_queue` and writes `queue_status <- CANCELLED` together, so no event ever leaves EQ while still `QUEUED`. A
whole-file search confirms the only executable `REMOVE ... FROM EQ.event_queue` (`:658`) and the only executable
`queued_event_registry[...].queue_status <- CANCELLED` (`:659`) are inside this procedure. All 31 `CALL CancelQueuedEvent`
sites are reconciled and cover the full minimum set; every set cancellation iterates in stable EventRef order and calls
the owner once each; and every remaining textual `CANCEL ` occurrence is a comment or the owner's prohibition doc line —
there is NO residual executable raw `CANCEL <ref> on EQ` and NO unreconciled cancel site. `CancelSetupRetriesForRound`
routes through the owner and performs no separate `queue_status <- CANCELLED` write. The pseudocode, round state machine
§3.10i AE1/AE2, the terminology Stage-1AE addendum, and TV262 / TV263 / TV272 are mutually consistent. The algorithm
remains **PoCol** and the mechanism remains the idle policy within PoCol; the A1 baseline `8.420833333 kWh` is preserved.
