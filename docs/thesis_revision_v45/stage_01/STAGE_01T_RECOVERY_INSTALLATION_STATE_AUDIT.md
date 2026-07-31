# Stage 1T — Recovery Installation-Phase State + Invariant Audit (T3)

This is a documentation-only paper audit of Stage-1T correction **T3 — installation-phase
state + episode invariant** as edited in
`docs/thesis_revision_v45/stage_01/STAGE_01_PROTOCOL_PSEUDOCODE.md`. T3 closes one gap: the
redistribution-only branch-C install inside `ApplyRecoveryAssignmentContinuationAfterEpilogue`
is a SYNCHRONOUS sub-computation during which the round is transiently `ASSIGNMENT` while a
recovery episode is still active. T3 (a) names three per-round registries that scope that
window — `recovery_install_in_progress`, `RecoveryInstallID = (episode, recovery_install_seq)`,
and `active_recovery_install_decision` — (b) expands the plain S4 episode invariant so the
transient state is admitted explicitly, and (c) fixes a single EXIT invariant so every install
exit lands in exactly one coherent `(round_state, episode, decision-status)` triple with the
install registries cleared. The consensus specification is named **PoCol**; **the idle policy
within PoCol** is referenced only as a mechanism, and this audit claims no energy, security, or
fairness property of it. T3 is a lifecycle / state-integrity correction to the recovery-episode
and installation registries; it is NOT a change to how time or energy is counted — it touches no
census value, residency interval, or transition-energy term — so the **A1 accepted accounting
baseline of 8.420833333 kWh is UNCHANGED**. No new consensus feature is introduced; every claim
below is checked against the pseudocode as edited.

## 1. §0.8 registries the correction touches

- `recovery_install_in_progress` (§0.8 lines 676–678): boolean, "true ONLY during the
  SYNCHRONOUS branch-C installation sub-computation (`round_state = ASSIGNMENT`) inside
  `ApplyRecoveryAssignmentContinuationAfterEpilogue`; false otherwise. It appears in the T3
  episode invariant below."
- `recovery_install_seq` (§0.8 line 679): "monotonic per-round counter; `RecoveryInstallID =
  (episode, recovery_install_seq)`."
- `RecoveryInstallID` (§0.8 line 680): "the deterministic identity of one branch-C
  installation."
- `active_recovery_install_decision` (§0.8 line 681): "the `RecoveryDecisionID` whose branch-C
  installation is in progress (null otherwise)."
- `recovery_outcome_finalised` (§0.8 lines 662–667): set ONCE, only on an actually-applied
  outcome — by this hook "when branch C reaches HASHING (RESTORED)" (lines 664–665). T4:
  explicitly "NOT set on a failed branch-C install" (lines 665–667).
- `recovery_episode_disposition` (§0.8 lines 668–674): records how an episode ended WITHOUT an
  applied outcome; `RECOVERY_INSTALL_FAILED_ABORTED` "when a branch-C RESTORED installation
  failed after the irreversible mutation and the round was aborted (T4, §10a)" (lines 671–673).
- **T3 EPISODE INVARIANT** (§0.8 lines 691–699, "supersedes the S4 form"):
  `current_recovery_episode != null` IFF ( `round_state = SECURITY_RECOVERY` OR (
  `round_state = ASSIGNMENT` AND `recovery_install_in_progress = true` AND
  `recovery_decisions[active_recovery_install_decision].status = APPLYING` ) ). The text fixes
  that "the ASSIGNMENT branch is exercised ONLY inside the SYNCHRONOUS branch-C installation (no
  event boundary occurs within it), so the invariant holds at every event boundary," and
  enumerates the three install exits.

## 2. §1.0 `RoundInitialise` — the three registries init to false / 0 / null

`RoundInitialise` (§1.0) resets the T3 installation registries at the top of every round
(lines 1241–1243):

- `SET recovery_install_in_progress <- false` (line 1241) — "no branch-C installation in
  progress at round start";
- `SET recovery_install_seq <- 0` (line 1242) — "deterministic `RecoveryInstallID` counter";
- `SET active_recovery_install_decision <- null` (line 1243) — "no installation decision at
  round start".

All three are RETURNED explicitly from `RoundInitialise` (line 1267) alongside the other
per-round recovery registries, so none exists as an implicit global (the Q5/I-04 explicit-
ownership rule). At a round boundary, therefore, the invariant's second disjunct is vacuously
false (`recovery_install_in_progress = false`), so the invariant reduces to the plain S4 form.

## 3. §10a `ApplyRecoveryAssignmentContinuationAfterEpilogue` — the install phase and its exits

This post-epilogue hook (§10a header line 2741, "the ONLY place branch-C RESTORED is APPLIED")
enters the installation phase ONLY on the redistribution-only predicate — "the FINAL census at
`t` satisfies the floor using ONLY currently `ACTIVE_HASHING` miners" (line 2769). The install
BEGINS (lines 2770–2780):

- `TRANSITION round_state -> ASSIGNMENT` (line 2772);
- `SET recovery_install_in_progress <- true` (line 2773);
- `SET recovery_install_seq <- recovery_install_seq + 1 ; SET RecoveryInstallID <- (episode,
  recovery_install_seq)` (line 2774);
- `SET active_recovery_install_decision <- decision_id` (line 2775);
- INSTALL the disjoint assignment set under `(RoundID_current, TemplateID_committed)`
  (lines 2776–2780; I1 disjoint, NO new template).

Inside this window the round is transiently `ASSIGNMENT`, the episode is still active, and
`recovery_decisions[decision_id].status = APPLYING` — exactly the invariant's second disjunct.
The install then reaches EXACTLY ONE of three terminal exits:

- **Exit (i) — HASHING + APPLIED (redistribution-only success), lines 2792–2800.** When
  `install_ok` and `CompleteAssignmentPhase` returns `assignment_phase_completed` (the round is
  now HASHING; §17 lines 1524–1527 perform the sole `ASSIGNMENT -> HASHING` step),
  `SetRecoveryDecisionStatus(... APPLIED)` (line 2795), `recovery_outcome_finalised[episode] <-
  RESTORED` (line 2796), remove the decision from `pending_recovery_decisions` (line 2797),
  clear the install registries (line 2798), and `current_recovery_episode <- null` (line 2799).
  Returns `recovery_continuation_applied(decision_id, RESTORED)` (line 2800).
- **Exit (ii) — SECURITY_RECOVERY + APPLY_FAILED (reversible rollback), lines 2801–2809.** When
  `install_ok` but `CompleteAssignmentPhase` returns `assignment_phase_failed` (round still
  ASSIGNMENT — reversible per §17 line 1521): UNDO the partial install (line 2804),
  `TRANSITION round_state -> SECURITY_RECOVERY` (line 2805, "rollback complete"), clear the
  install registries (line 2806), `SetRecoveryDecisionStatus(... APPLY_FAILED)` (line 2807), and
  remove the decision (line 2808). The episode is PRESERVED (`current_recovery_episode` is NOT
  cleared) "so a later epilogue may re-seat if still warranted." Returns
  `recovery_continuation_failed(decision_id)` (line 2809).
- **Exit (iii) — ROUND_ABORTED + RECOVERY_INSTALL_FAILED_ABORTED (irreversible install
  failure), lines 2781–2791.** When `NOT install_ok` (an irreversible post-mutation failure):
  `SetRecoveryDecisionStatus(... APPLY_FAILED_TERMINAL)` (line 2784), remove the decision
  (line 2785), `recovery_episode_disposition[episode] <- RECOVERY_INSTALL_FAILED_ABORTED`
  ("NOT `recovery_outcome_finalised`", line 2786), clear the install registries (line 2787),
  `current_recovery_episode <- null` ("cleared exactly once", line 2788), and close the round
  via the declared `RoundAbort(reason = recovery_install_failed_aborted, recovery_finalising =
  true)` (lines 2789–2790). Returns `recovery_continuation_install_aborted(decision_id)` (line
  2791).

The reserve-dependent restoration (`ELSE`, T6-B, lines 2810–2832) is NOT an install exit: it
never enters the install phase — the round STAYS `SECURITY_RECOVERY`, the decision stays
`APPLYING`, and a strictly-later continuation is re-armed. So `recovery_install_in_progress`
never becomes true on that path and the invariant reduces to its first disjunct throughout.

### 3.1 Each exit clears the registries and leaves a coherent triple

| Install exit | `round_state` at exit | `current_recovery_episode` | decision status | install registries | outcome / disposition key | Return |
|---|---|---|---|---|---|---|
| (i) success (line 2800) | `HASHING` | `null` (2799) | `APPLIED` (2795) | `in_progress<-false`, `active<-null` (2798) | `recovery_outcome_finalised = RESTORED` (2796) | `recovery_continuation_applied` |
| (ii) reversible fail (line 2809) | `SECURITY_RECOVERY` (2805) | non-null (PRESERVED) | `APPLY_FAILED` (2807) | `in_progress<-false`, `active<-null` (2806) | none set (episode still open) | `recovery_continuation_failed` |
| (iii) irreversible fail (line 2791) | `ROUND_ABORTED` (via 2789) | `null` (2788) | `APPLY_FAILED_TERMINAL` (2784) | `in_progress<-false`, `active<-null` (2787) | `recovery_episode_disposition = RECOVERY_INSTALL_FAILED_ABORTED` (2786) | `recovery_continuation_install_aborted` |

In every exit `recovery_install_in_progress <- false` and `active_recovery_install_decision <-
null`; `recovery_install_seq` remains monotonic (the `RecoveryInstallID` identity is simply
retired when `recovery_install_in_progress` goes false), so no exit leaves a live install
identity. Each resulting `(round_state, episode, decision-status)` triple is coherent under the
invariant: (i) `HASHING` with a null episode (both invariant sides false); (ii)
`SECURITY_RECOVERY` with an active episode (first disjunct — both sides true); (iii)
`ROUND_ABORTED` with a null episode (both sides false).

## 4. The synchronous-install argument — no epilogue observes the transient state

The whole install between the BEGIN block (line 2770) and whichever exit fires is a SYNCHRONOUS
sub-computation: it dispatches no queued event, so no `ProcessEventTime` / epilogue runs within
it. The comment at lines 2770–2771 states this directly — the install is "a SYNCHRONOUS
sub-computation; NO event boundary occurs within it, so no epilogue observes the transient
ASSIGNMENT-with-active-episode state (the T3 invariant holds at every boundary)." The T7
discipline reinforces it: any `StartWake` the install seats places its `WakeCompleteEvent`
STRICTLY LATER through the post-epilogue context (lines 2776–2779), never at the current
`event_time` `t`, so nothing the install schedules can interpose a boundary before it exits.

Consequently the invariant's second disjunct (`ASSIGNMENT` + `recovery_install_in_progress` +
`APPLYING`) is true ONLY across an interval that contains no observable event boundary. At every
quiescent boundary the round is in one of the three exit states of §3.1, each of which satisfies
the invariant. During the synchronous install the round is indeed transiently `ASSIGNMENT` with
an active episode, but that state is never observed at a boundary because there is no boundary
within the synchronous computation; T3 makes this explicit rather than leaving it implicit.

## 5. The T3 exit invariant and how it supersedes the plain S4 form

The plain S4 form is `current_recovery_episode != null` IFF `round_state = SECURITY_RECOVERY`.
It is correct at boundaries but says nothing about the transient install window, where the round
is `ASSIGNMENT` yet the episode is still active. T3 SUPERSEDES it (§0.8 line 691) by adding the
guarded ASSIGNMENT disjunct, so the transient state is admitted explicitly and provably confined:
the disjunct can be true only while `recovery_install_in_progress = true` and the named decision
is `APPLYING`, both of which hold only inside the synchronous sub-computation of §4.

The T3 EXIT INVARIANT (§0.8 lines 696–698) then states that every installation exit ends in
EXACTLY ONE of: (i) `HASHING` + decision `APPLIED`; (ii) `SECURITY_RECOVERY` + decision
`APPLY_FAILED` (rollback complete); (iii) `ROUND_ABORTED` + `recovery_episode_disposition =
RECOVERY_INSTALL_FAILED_ABORTED`. §3.1 confirms each exit realises exactly one of these and
clears the install registries, so on exit `recovery_install_in_progress` is false, the second
disjunct collapses, and the invariant reduces cleanly to the plain S4 form — the two are
consistent, and S4 is the boundary-time restriction of the expanded T3 statement.

## 6. PASS-check table (exact names)

| PASS check | Where | Cited names / lines |
|---|---|---|
| Registries init false / 0 / null each round | §1.0 | `recovery_install_in_progress<-false` (1241); `recovery_install_seq<-0` (1242); `active_recovery_install_decision<-null` (1243); returned (1267) |
| Install BEGINS only on redistribution-only predicate | §10a | predicate (2769); `TRANSITION -> ASSIGNMENT` (2772); `recovery_install_in_progress<-true` (2773); `RecoveryInstallID` (2774); `active_recovery_install_decision<-decision_id` (2775) |
| Exit (i) coherent + registries cleared | §10a | `APPLIED` (2795); `recovery_outcome_finalised<-RESTORED` (2796); registries cleared (2798); `current_recovery_episode<-null` (2799) |
| Exit (ii) coherent + registries cleared, episode preserved | §10a | `TRANSITION -> SECURITY_RECOVERY` (2805); registries cleared (2806); `APPLY_FAILED` (2807) |
| Exit (iii) coherent + registries cleared, round aborted | §10a | `APPLY_FAILED_TERMINAL` (2784); `RECOVERY_INSTALL_FAILED_ABORTED` (2786); registries cleared (2787); `current_recovery_episode<-null` (2788); `RoundAbort(recovery_install_failed_aborted, recovery_finalising=true)` (2789–2790) |
| Synchronous — no intra-install boundary | §10a / §0.8 | "NO event boundary occurs within it" (2770–2771, 695); T7 strictly-later wake (2776–2779) |
| Invariant expands + supersedes S4 | §0.8 | T3 EPISODE INVARIANT (691–699, "supersedes the S4 form") |

## 7. Contrast with the failure mode

Two failure modes T3 forecloses:

- **An epilogue observing the transient `ASSIGNMENT`-with-active-episode state.** This could
  arise only if the install spanned an event boundary — i.e. dispatched a queued event and let
  `ProcessEventTime` run mid-install. The install does not: it is synchronous (§4), and any wake
  it seats fires strictly later through the post-epilogue context (lines 2776–2779). No epilogue
  ever sees the second-disjunct state, so it cannot mis-decide a census against a half-installed
  round.
- **An install exit stranding the round in `ASSIGNMENT` with an active episode and no live
  continuation.** None of the three exits does this: exit (i) advances to `HASHING` and clears
  the episode, exit (ii) rolls back to `SECURITY_RECOVERY` (episode preserved, decision
  `APPLY_FAILED`), and exit (iii) aborts to `ROUND_ABORTED` and clears the episode — matching
  the standing guarantee that "the round never lingers in `ASSIGNMENT` with an active episode and
  no live continuation" (line 2472). A stranded `ASSIGNMENT`-plus-active-episode residue with
  `recovery_install_in_progress` never reset would violate BOTH the plain S4 form and the
  expanded T3 invariant; the three exits, each clearing the install registries, are precisely
  what prevents it.

## 8. Result

Under T3 the redistribution-only branch-C install is a synchronous sub-computation scoped by
`recovery_install_in_progress`, `RecoveryInstallID = (episode, recovery_install_seq)`, and
`active_recovery_install_decision` — all initialised to false / 0 / null by `RoundInitialise`
(lines 1241–1243) and returned explicitly. Because the install contains no event boundary
(lines 2770–2771), no epilogue observes the transient `ASSIGNMENT`-with-active-episode window,
and the invariant `current_recovery_episode != null` IFF ( `SECURITY_RECOVERY` OR
`ASSIGNMENT`-during-synchronous-install ) holds at every event boundary, superseding and
reducing to the plain S4 form `current_recovery_episode != null` IFF `round_state =
SECURITY_RECOVERY`. Every install exit ends in exactly one coherent triple — (i) `HASHING` +
`APPLIED` + `recovery_outcome_finalised = RESTORED`; (ii) `SECURITY_RECOVERY` + `APPLY_FAILED`
with the episode preserved; (iii) `ROUND_ABORTED` + `RECOVERY_INSTALL_FAILED_ABORTED` — and in
every exit `recovery_install_in_progress <- false` and `active_recovery_install_decision <-
null`. T3 is a lifecycle / state-integrity correction to the recovery-episode and installation
registries only; it is not a change to how time or energy is counted, so the A1 accepted
baseline of 8.420833333 kWh is unchanged, and no new consensus feature is introduced.

The prohibited rebranded-algorithm-name variants are not used anywhere in this document.
