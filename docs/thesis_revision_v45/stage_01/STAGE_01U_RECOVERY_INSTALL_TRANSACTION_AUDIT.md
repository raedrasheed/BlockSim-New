# Stage 1U — Recovery-Install Transaction (Prepare / Commit / Rollback) Audit (U5)

This is a documentation-only paper audit of Stage-1U correction **U5 — replace the opaque
INSTALL / UNDO macros with named executable prepare / commit / rollback procedures** as edited in
`docs/thesis_revision_v45/stage_01/STAGE_01_PROTOCOL_PSEUDOCODE.md`. U5 closes one
executability gap: the branch-C redistribution install and the recovery-work reserve activation
used to be written as two hand-wave macros — "INSTALL the disjoint assignment set" and "UNDO the
partial install" — whose planning, verification, mutation, and reversal were all folded into one
opaque step. U5 splits that step into three named procedures with declared inputs, returns, and
effects: `PrepareRecoveryAssignmentPlan` (compute-only, builds the `recovery_assignment_plan`
value and VERIFIES the structural invariants BEFORE any mutation), `CommitRecoveryAssignmentPlan`
(applies a prepared plan in stable order, threading the explicit scheduling_context), and
`RollbackRecoveryAssignmentPlan` (reverts a partially or fully committed plan and leaves no live
partial assignment). The consensus specification is named **PoCol**; **the idle policy within
PoCol** is referenced only as a mechanism, and this audit claims no energy, security, or fairness
property of it. U5 is an install-transaction / executability correction to the recovery
assignment path; it is NOT a change to how time or energy is counted — it introduces no census
value, no residency interval, and no transition-energy term, and it never alters how the idle
policy within PoCol is accounted — so the **A1 accepted accounting baseline of 8.420833333 kWh is
UNCHANGED**. No new consensus feature is introduced; every claim below is checked against the
pseudocode as edited.

## 1. §0.8 — the `recovery_assignment_plan` record and what U5 replaces

The §0.8 declaration block adds the record and states outright what it retires (§0.8 line 744,
"U5 named recovery-assignment plan record (replaces the opaque INSTALL/UNDO macros)"):

- `recovery_assignment_plan = { RecoveryInstallID, source_assignment_versions,
  accepted_unsearched_suffixes, selected_reserve_miners, new_pending_assignment_specs (stable
  creation order), required_wake_operations, rollback_metadata }` (§0.8 lines 745–747).
- Provenance of each phase is fixed in the same declaration (§0.8 lines 747–748): the record is
  "Produced compute-only by `PrepareRecoveryAssignmentPlan` (verifies I1/I3/I10/I18b BEFORE any
  mutation); applied by `CommitRecoveryAssignmentPlan`; reverted by
  `RollbackRecoveryAssignmentPlan`."
- The plan is a first-class scheduling participant under U2: `CommitRecoveryAssignmentPlan` is
  listed among the procedures that "take an explicit scheduling_context" of type
  `SchedulingSourceContext` (§0.8 lines 739–743), alongside `ReserveActivate` / `RangeReassign` /
  `RangeAssign` / `StartWake`.

So the plan is a named value with an enumerated shape and a single deterministic identity,
`RecoveryInstallID`; there is no longer an unnamed "assignment set" that some macro both computes
and installs in one indivisible motion.

## 2. `PrepareRecoveryAssignmentPlan` — compute-only, verified before any mutation (TV168)

`PrepareRecoveryAssignmentPlan` (§10a lines 3163–3186) is declared "COMPUTE-ONLY — build a
deterministic recovery-assignment plan; NO mutation" (line 3163). Its precondition states it
"performs NO state mutation, creates NO assignment, and seats NO event" (lines 3165–3166), on
either entry — `SECURITY_RECOVERY` for recovery work (§9c) or `ASSIGNMENT` for a
redistribution-only continuation install (§10a).

It builds every enumerated field deterministically (lines 3170–3177):

- `recovery_install_seq_preview <- recovery_install_seq + 1` (line 3170) and
  `plan.RecoveryInstallID <- (episode, recovery_install_seq_preview)` (line 3171), "matches the
  id the caller mints";
- `plan.source_assignment_versions` — the immutable `(AssignmentID, assignment_version)` of every
  source range (I9) (line 3172);
- `plan.accepted_unsearched_suffixes` (line 3173);
- `plan.selected_reserve_miners` — the deterministic reserve set for
  `RESERVE_ACTIVATION_REQUIRED`, else empty (line 3174);
- `plan.new_pending_assignment_specs` — "in a STABLE creation order (by MinerID, then
  CandidateID)" (line 3175);
- `plan.required_wake_operations` (line 3176);
- `plan.rollback_metadata` — "an EMPTY rollback record keyed by `plan.RecoveryInstallID` (filled
  by Commit)" (line 3177).

It THEN verifies the structural invariants over the PROPOSED specs — BEFORE any caller mutates:
"VERIFY I1 (no overlap among valid active assignments), I3 (RoundID/TemplateID match), I10
(reserve activation adds no overlap), I18b (unique live head per lineage) over the PROPOSED specs
— BEFORE any mutation" (lines 3178–3179). On any violation it returns `plan_invalid(reason =
overlap_or_lineage_or_epoch_violation)` with the annotation "caller mutates NOTHING (TV168)"
(lines 3180–3181); otherwise `plan_ready(plan)` (line 3182). The return set is `plan_ready(plan)
| plan_invalid(reason)` (line 3183), and the NOTE is explicit that this "replaces the opaque
`INSTALL the disjoint assignment set` macro's PLANNING half ... a detected overlap creates NO
assignment, NO state transition, and NO wake event (TV168)" (lines 3184–3186).

**TV168** (a detected overlap creates nothing): because verification precedes every mutation and
the procedure is compute-only, an I1/I3/I10/I18b violation returns `plan_invalid` while the ledger
is untouched — no assignment is created, no `round_state` transition is taken, and no wake is
seated. The determinism note (line 3186) closes the loop: the stable creation order makes
`event_creation_seq` reproducible, so the plan a caller receives is a pure function of the census
and the source versions.

## 3. `CommitRecoveryAssignmentPlan` — stable-order creation, threaded context, pre- vs post-mutation failure (TV169)

`CommitRecoveryAssignmentPlan` (§10a lines 3188–3233) is declared "apply a prepared plan; thread
the explicit scheduling_context" (line 3188) and takes `INPUTS: RoundContext, plan,
scheduling_context` where the context is "`POST_EPILOGUE(pctx)` here" (line 3189). Its
preconditions record that the plan was "produced by `PrepareRecoveryAssignmentPlan`
(I1/I3/I10/I18b already verified compute-only)" and that "A POST_EPILOGUE scheduling_context is
threaded to every nested `ScheduleEvent` (U2), so every wake targets a STRICTLY LATER event_time"
(lines 3190–3193).

- **Re-verify, then create in stable order.** It re-verifies against CURRENT state and, on a
  violation before any assignment is created, returns `install_failed_before_mutation(reason =
  revalidation_failed)` with "nothing created" (lines 3195–3198). It initialises `created_assignments
  <- empty ; created_events <- empty` (line 3199) and iterates `plan.new_pending_assignment_specs`
  "(STABLE creation order)" (line 3200).
- **Threading through the four named constructors.** A `RESERVE_ACTIVATION` spec goes through
  `ReserveActivate(... scheduling_context = scheduling_context)` "which bundles
  CreatePendingAssignment + StartWake, threading scheduling_context" (lines 3203, 3205–3209); a
  REDISTRIBUTION spec goes through "`RangeReassign` / `RangeAssign`" (lines 3211–3213) and its
  wakes through `StartWake(... scheduling_context = scheduling_context)` (lines 3223–3226). Every
  created assignment is tracked in `created_assignments` and every scheduled event in
  `created_events` (lines 3208, 3222, 3226).
- **The pre- vs post-mutation distinction.** On a `creation_failed(reason)`: if
  `created_assignments is empty AND created_events is empty` it returns
  `install_failed_before_mutation(reason)` (lines 3217–3218); otherwise it fills
  `plan.rollback_metadata <- rollback_record(RecoveryInstallID = plan.RecoveryInstallID,
  created_assignments = ..., created_events = ...)` and returns `install_failed_after_mutation(reason,
  plan.rollback_metadata)` (lines 3219–3221). On success it stamps the same rollback record "for a
  later CompleteAssignmentPhase-fail rollback" (lines 3227–3228) and returns `install_committed`
  (line 3229). The return set is `install_committed | install_failed_before_mutation(reason) |
  install_failed_after_mutation(reason, rollback_record)` (line 3230).

**TV169** (the two failure classes are distinguished by what was created): the NOTE states the
procedure "replaces the opaque `INSTALL` macro's MUTATION half ... creates assignments in a
STABLE order, threads the explicit scheduling_context ... and distinguishes a reversible
pre-mutation failure from an irreversible post-mutation one (returning a rollback record)" (lines
3231–3233). A commit that fails before touching the ledger is reversible and hands back nothing to
undo; a commit that fails after at least one creation returns a `rollback_record` naming exactly
the assignments and events it created, so the caller can revert precisely that set and no more.

## 4. `RollbackRecoveryAssignmentPlan` — cancel events, close heads legally, no residual (TV170)

`RollbackRecoveryAssignmentPlan` (§10a lines 3235–3256) is declared "explicitly revert a
partially/fully committed plan" (line 3235) and takes `INPUTS: RoundContext, rollback_record`
where the record is `{ RecoveryInstallID, created_assignments, created_events }` (line 3236). Its
precondition names the two callers and the standing obligation: it is "called by
`ApplyRecoveryAssignmentContinuationAfterEpilogue` / `ApplyRecoveryWorkAfterEpilogue` on an
`install_failed_after_mutation` or a post-commit `CompleteAssignmentPhase` failure. It must leave
NO live partial assignment" (lines 3237–3239).

- **Events first, then heads.** "Order: events first (so no wake can activate a head being
  closed), then heads" (lines 3241–3242). For each `event_ref` in `created_events` "IF event_ref is
  still pending on EQ: CANCEL event_ref on EQ" (lines 3243–3244).
- **Legal closure of every plan-created head.** For each `a` in `created_assignments`: an already
  superseded/closed head is skipped "(already superseded/closed — idempotent)" (lines 3245–3246);
  otherwise `CLOSE a as CLOSED (status = CLOSED, custody_status = revoked, reason =
  recovery_install_rolled_back)`, annotated "J7: legal close, no live head (I18b)" (line 3247), and
  the coverage-state / custody ledgers are RESTORED "to their pre-plan values for a's range (I8a/I8b)"
  (line 3248).
- **No residual partial assignment.** "IF any plan-created PENDING head remains live OR any
  created event remains pending on EQ: RETURN `rollback_failed(reason = residual_partial_assignment)`"
  with "caller aborts the round (never fabricate UNRECOVERABLE)" (lines 3249–3250); otherwise
  `rollback_completed` (line 3251). The return set is `rollback_completed | rollback_failed(reason)`
  (line 3252).

**TV170** (a failed rollback forces the declared abort, never a fabricated UNRECOVERABLE): the
NOTE states the procedure "replaces the opaque `UNDO the partial install` macro. It cancels every
plan event, closes every plan-created live head legally (I18b), and restores the coverage/custody
ledgers — leaving NO live partial assignment. If a residual partial assignment cannot be removed,
it returns `rollback_failed` and the caller takes the declared `RECOVERY_INSTALL_FAILED_ABORTED` /
`RoundAbort` path (T4) — it NEVER fabricates an `UNRECOVERABLE` outcome" (lines 3253–3256). The
two consumers honour this exactly: in `ApplyRecoveryAssignmentContinuationAfterEpilogue` a
`rollback_failed` sets `recovery_episode_disposition[episode] <- RECOVERY_INSTALL_FAILED_ABORTED`
and calls `RoundAbort(... reason = recovery_install_failed_aborted, recovery_finalising = true)`
(lines 3108–3117), and in `ApplyRecoveryWorkAfterEpilogue` the same `rollback_failed` sets the
same disposition and `RoundAbort` (lines 2664–2672) — never `UNRECOVERABLE`.

## 5. The two consumers route through the named procedures

Both post-epilogue hooks now call the three procedures by name; neither contains an INSTALL or
UNDO macro.

- `ApplyRecoveryWorkAfterEpilogue` (§9c, lines 2623–2692, header "U1/U3/U4/U5"): it builds
  `plan <- PrepareRecoveryAssignmentPlan(RoundContext, episode, W.action, census)` "compute-only;
  verifies I1/I3/I10/I18b" (line 2648), applies `commit <- CommitRecoveryAssignmentPlan(...,
  scheduling_context = POST_EPILOGUE(pctx))` (line 2656), and on `install_failed_after_mutation`
  calls `RollbackRecoveryAssignmentPlan(RoundContext, rollback_record)` (line 2663). A
  `rollback_failed` sets `recovery_episode_disposition[episode] <- RECOVERY_INSTALL_FAILED_ABORTED`
  and calls `RoundAbort(... recovery_install_failed_aborted ...)` (lines 2664–2672); a
  `plan_invalid` or `install_failed_before_mutation` leaves the round `SECURITY_RECOVERY` with no
  mutation (lines 2649–2661). Its NOTE names all three procedures as the mechanism (lines 2686–2688).
- `ApplyRecoveryAssignmentContinuationAfterEpilogue` (§10a, lines 3040–3161, "the ONLY place
  branch-C RESTORED is APPLIED"): it builds the plan with "No opaque INSTALL macro" (lines
  3075–3076), begins the T3 install phase, commits (line 3090), and reverts through
  `RollbackRecoveryAssignmentPlan` on both an `install_failed_after_mutation` (line 3100) and a
  post-commit `assignment_phase_failed` (line 3130, "undo the committed install"). Its NOTE
  records that it "uses the named `PrepareRecoveryAssignmentPlan` / `CommitRecoveryAssignmentPlan`
  / `RollbackRecoveryAssignmentPlan` (U5, no opaque INSTALL/UNDO macro) ... never fabricates
  `UNRECOVERABLE` on an irreversible install failure (T4: `RECOVERY_INSTALL_FAILED_ABORTED`)"
  (lines 3154–3157).

## 6. PASS-check table (exact names)

| PASS check | Where | Cited names / lines |
|---|---|---|
| §0.8 record replaces the INSTALL/UNDO macros | §0.8 | "replaces the opaque INSTALL/UNDO macros" (744); `recovery_assignment_plan = { RecoveryInstallID, source_assignment_versions, accepted_unsearched_suffixes, selected_reserve_miners, new_pending_assignment_specs (stable creation order), required_wake_operations, rollback_metadata }` (745–747); produced/applied/reverted by the three procedures (747–748) |
| Prepare is compute-only | §10a | "COMPUTE-ONLY ... NO mutation" (3163); "performs NO state mutation, creates NO assignment, and seats NO event" (3165–3166) |
| Prepare builds every enumerated field in stable order | §10a | `plan.RecoveryInstallID` (3171); `source_assignment_versions` (3172); `accepted_unsearched_suffixes` (3173); `selected_reserve_miners` (3174); `new_pending_assignment_specs` "STABLE creation order (by MinerID, then CandidateID)" (3175); `required_wake_operations` (3176); `rollback_metadata` (3177) |
| Prepare verifies I1/I3/I10/I18b BEFORE any mutation (TV168) | §10a | "VERIFY I1 ... I3 ... I10 ... I18b ... BEFORE any mutation" (3178–3179); `plan_invalid(reason = overlap_or_lineage_or_epoch_violation)` "caller mutates NOTHING (TV168)" (3180–3181); "creates NO assignment, NO state transition, and NO wake event (TV168)" (3185–3186) |
| Commit re-verifies then creates in stable order, threading scheduling_context (TV169) | §10a | re-verify -> `install_failed_before_mutation(reason = revalidation_failed)` (3197–3198); FOR EACH spec "(STABLE creation order)" (3200); `ReserveActivate(... scheduling_context)` (3206); `RangeReassign / RangeAssign(... scheduling_context)` (3212–3213); `StartWake(... scheduling_context)` (3224–3225) |
| Commit tracks every created assignment/event; distinguishes pre- vs post-mutation failure (TV169) | §10a | `created_assignments`/`created_events` (3199, 3208, 3222, 3226); empty -> `install_failed_before_mutation(reason)` (3217–3218); non-empty -> `install_failed_after_mutation(reason, plan.rollback_metadata)` (3219–3221); returns (3230) |
| Rollback cancels events, closes heads legally (I18b), restores ledgers, leaves no residual (TV170) | §10a | "events first ... then heads" (3241–3242); `CANCEL event_ref on EQ` (3244); `CLOSE a as CLOSED (... reason = recovery_install_rolled_back)` "no live head (I18b)" (3247); RESTORE coverage/custody (I8a/I8b) (3248); residual -> `rollback_failed(reason = residual_partial_assignment)` (3249–3250) |
| A failed rollback -> RECOVERY_INSTALL_FAILED_ABORTED + RoundAbort, never UNRECOVERABLE (TV170) | §9c / §10a | "never fabricate UNRECOVERABLE" (3250, 3256); continuation abort (3108–3117); work abort (2664–2672) |
| Both consumers call the three procedures by name | §9c / §10a | Prepare (2648, 3076); Commit (2656, 3090); Rollback (2663, 3100, 3130); "no opaque INSTALL/UNDO macro" (2686–2688, 3154–3157) |

## 7. Contrast with the failure mode

Three failure modes U5 forecloses:

- **An opaque macro doing planning, verification, mutation, and reversal in one indivisible
  step.** The retired "INSTALL the disjoint assignment set" / "UNDO the partial install" phrasing
  named no inputs, no return set, and no verification order, so a reader could not tell whether an
  overlap was caught before or after ranges were created, nor what "UNDO" was obliged to reverse.
  U5 replaces both with `PrepareRecoveryAssignmentPlan` / `CommitRecoveryAssignmentPlan` /
  `RollbackRecoveryAssignmentPlan`, each with declared `INPUTS` / `RETURNS` / `EFFECTS` and NOTEs
  stating exactly which macro half each one replaces (lines 3184, 3231, 3253).
- **A plan that mutates before it verifies.** If verification followed creation, a detected
  overlap would already have seated assignments, transitions, or wakes that then had to be swept
  up. U5 forbids this structurally: `PrepareRecoveryAssignmentPlan` is compute-only and returns
  `plan_invalid` while "the caller mutates NOTHING" (line 3181), and `CommitRecoveryAssignmentPlan`
  re-verifies against current state and returns `install_failed_before_mutation` with "nothing
  created" (line 3198) before it enters its stable-order creation loop — so a caught violation
  never leaves a half-installed round (TV168).
- **A residual live partial assignment surviving a rollback.** A rollback that closed some heads
  but left others live, or cancelled some events but left others pending on EQ, would strand a
  partial install with no live continuation. `RollbackRecoveryAssignmentPlan` cancels every plan
  event first, then closes every plan-created head legally (I18b) and restores the coverage/custody
  ledgers, and explicitly returns `rollback_failed(reason = residual_partial_assignment)` if any
  head remains live or any event remains pending (lines 3249–3250). That `rollback_failed` does not
  invent an outcome: the caller takes the declared `RECOVERY_INSTALL_FAILED_ABORTED` +
  `RoundAbort(recovery_install_failed_aborted)` path (lines 3108–3117, 2664–2672) rather than
  fabricating an `UNRECOVERABLE` result (TV170).

## 8. Result

Under U5 the branch-C redistribution install and the recovery-work reserve activation are no
longer opaque macros but a three-procedure transaction over a named `recovery_assignment_plan`
value (§0.8 lines 744–748). `PrepareRecoveryAssignmentPlan` is compute-only, returns a
deterministic `plan_ready(plan) | plan_invalid(reason)` with every enumerated field in stable
creation order, and verifies I1/I3/I10/I18b before any mutation, so a detected overlap creates no
assignment, no transition, and no wake (TV168). `CommitRecoveryAssignmentPlan` receives the
explicit `POST_EPILOGUE` scheduling_context, creates assignments in stable order threading that
context through `ReserveActivate` / `RangeReassign` / `RangeAssign` / `StartWake`, tracks every
created assignment and event, and distinguishes `install_failed_before_mutation` (reversible,
nothing created) from `install_failed_after_mutation(reason, rollback_record)` (TV169).
`RollbackRecoveryAssignmentPlan` cancels every plan event, closes and removes every plan-created
PENDING head legally (I18b), restores the coverage/custody ledgers, leaves no live partial
assignment, and returns `rollback_completed | rollback_failed`; a `rollback_failed` after mutation
forces `RECOVERY_INSTALL_FAILED_ABORTED` + `RoundAbort` in both consumers, never a fabricated
`UNRECOVERABLE` (TV170). U5 is an install-transaction / executability correction to the recovery
assignment path only; it is not a change to how time or energy is counted, and it leaves the idle
policy within PoCol accounted exactly as before, so the A1 accepted baseline of 8.420833333 kWh is
unchanged, and no new consensus feature is introduced.

The prohibited rebranded-algorithm-name variants are not used anywhere in this document.
