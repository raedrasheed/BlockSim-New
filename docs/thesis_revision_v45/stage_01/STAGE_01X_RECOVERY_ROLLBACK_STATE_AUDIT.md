# STAGE 01X — Recovery-Rollback Complete-State-Transaction Audit (correction X1)

**Deliverable:** `STAGE_01X_RECOVERY_ROLLBACK_STATE_AUDIT.md`
**Stage / correction:** Stage 1X, correction **X1** — "make `RollbackRecoveryAssignmentPlan` a COMPLETE state transaction."
**Algorithm:** PoCol. **Mechanism under audit:** the idle policy within PoCol (recovery-plan installation and its rollback path).
**Source of truth (READ-ONLY):** `STAGE_01_PROTOCOL_PSEUDOCODE.md` (5108 lines).
**Cross-referenced:** `STAGE_01_MINER_STATE_MACHINE.md` (T12 edge), `STAGE_01_ROUND_STATE_MACHINE.md` §3.10b (X1 block), `STAGE_01_INVARIANT_CATALOGUE.md` I16 (Stage-1X clause), `STAGE_01_TRACEABILITY_MATRIX.csv` (R177 / TV198–TV200).

## Purpose and method

Correction X1 requires that reverting a partially- or fully-committed recovery-assignment plan be a *complete state transaction*: every wake cancelled, every still-`WAKING` miner legally departed to `OFFLINE`, every plan-created head closed, every ledger restored, and a structured result returned — with a coherence check that makes a silent half-rollback impossible. This audit verifies that the correction is fully and consistently realised, grounding each claim in the actual current text of `STAGE_01_PROTOCOL_PSEUDOCODE.md` by procedure name and quoted `file:line`.

The relevant procedures and their current anchors are:

- `CommitRecoveryAssignmentPlan` — `STAGE_01_PROTOCOL_PSEUDOCODE.md:3610`
- `RollbackRecoveryAssignmentPlan` — `STAGE_01_PROTOCOL_PSEUDOCODE.md:3695`
- `ApplyRecoveryWorkAfterEpilogue` — `STAGE_01_PROTOCOL_PSEUDOCODE.md:2986`
- `ApplyRecoveryAssignmentContinuationAfterEpilogue` — `STAGE_01_PROTOCOL_PSEUDOCODE.md:3448`
- `ApplyMinerStateTransition` (F6) — `STAGE_01_PROTOCOL_PSEUDOCODE.md:997`

The `rollback_record` / `rollback_item` record definitions live in §0.8 at `STAGE_01_PROTOCOL_PSEUDOCODE.md:776–791`:

> `776  # --- X1/X5 recovery-plan rollback record (a COMPLETE state transaction; returned EXPLICITLY, never pass-by-reference) ---`
> `777  # rollback_record = { RecoveryInstallID, items : [rollback_item] }.  CommitRecoveryAssignmentPlan builds it and returns`
> `781  #   rollback_item = { MinerID, AssignmentID, assignment_version, WakeEventRef, pre_wake_state, rollback_envelope,`
> `782  #                     coverage_custody_before_image, kind, provenance }.`

The nine `rollback_item` fields named in §0.8 are exactly the nine that Claim 1 requires and that `RollbackRecoveryAssignmentPlan` consumes; the definition also fixes that the legal rollback edge is `WAKING -> OFFLINE` (T12) and that `assignment_version` identifies the EXACT head:

> `784  #                                       RESERVE / LOW_POWER_LISTEN) — for audit; the legal rollback edge is WAKING -> OFFLINE (T12).`
> `788  #     - assignment_version            : the immutable version, so the T12 release + close identify the EXACT head (X2).`

---

## Claim-by-claim verification

### Claim 1 — Every committed item captures its complete `rollback_item` pre-image BEFORE the constructor mutates — PASS

`CommitRecoveryAssignmentPlan` initialises the per-item record set and, for each spec in stable creation order, captures the three pre-images BEFORE calling any plan-bound constructor (`STAGE_01_PROTOCOL_PSEUDOCODE.md:3621–3630`):

> `3621    SET created_items <- empty   # X1: per-item rollback records (a COMPLETE state transaction)`
> `3624      #   plan-selected values (no SELECT). X1: BEFORE the constructor mutates, capture the per-item rollback pre-images —`
> `3627      SET pre_wake_state <- miner_state(spec.MinerID)                                            # X1`
> `3628      SET before_image   <- coverage_custody_before_image(spec.range)                            # X1: I8a/I8b snapshot`
> `3629      SET rbenv          <- (scheduling_context is POST_EPILOGUE(pctx) ? pctx.source_envelope`
> `3630                                                                       : scheduling_context.dispatch_envelope)   # X1: complete transition envelope`

These three reads (`pre_wake_state`, `before_image`, `rbenv`) occur textually before the `ReserveActivateFromPlan` / `RangeReassignFromPlan` / `RangeAssignFromPlan` calls that perform the mutating wake, so the pre-image is genuinely pre-mutation.

**Reserve-activation path** (`kind = RESERVE_ACTIVATION`, `STAGE_01_PROTOCOL_PSEUDOCODE.md:3631–3639`) records the item from the ACTUAL references returned by the constructor:

> `3635        IF r = reserve_activation_committed(mid, aid, aver, wref):`
> `3636          ADD rollback_item(MinerID = spec.MinerID, AssignmentID = aid, assignment_version = aver, WakeEventRef = wref,`
> `3637                pre_wake_state = pre_wake_state, rollback_envelope = rbenv, coverage_custody_before_image = before_image,`
> `3638                kind = spec.kind, provenance = spec.source_assignment) to created_items          # X1: ACTUAL refs`

**Redistribution path** (`REASSIGNED` reassignment or plan assignment, `STAGE_01_PROTOCOL_PSEUDOCODE.md:3662–3668`) records the item symmetrically, resolving the exact version from the returned AssignmentID:

> `3662        IF rr = range_reassigned(prov, aid, wref) OR rr = range_assigned(aid, wref, ws):`
> `3665          ADD rollback_item(MinerID = spec.MinerID, AssignmentID = rr.AssignmentID,`
> `3666                assignment_version = assignment_version(rr.AssignmentID), WakeEventRef = rr.WakeEventRef,`
> `3667                pre_wake_state = pre_wake_state, rollback_envelope = rbenv, coverage_custody_before_image = before_image,`
> `3668                kind = spec.kind, provenance = (rr = range_reassigned(prov, aid, wref) ? rr.provenance : null)) to created_items   # X1/W4`

Both `ADD rollback_item(...)` sites populate all nine §0.8 fields — `MinerID`, exact `AssignmentID`, `assignment_version`, `WakeEventRef`, `pre_wake_state`, `rollback_envelope`, `coverage_custody_before_image`, `kind`, `provenance` — for BOTH item kinds. The success disposition returns the assembled record explicitly (`STAGE_01_PROTOCOL_PSEUDOCODE.md:3682`):

> `3682    RETURN install_committed(rollback_record(RecoveryInstallID = plan.RecoveryInstallID, items = created_items))`

**Verdict: PASS.** Every committed item (reserve activation and redistribution) captures the complete nine-field pre-image, from ACTUAL returned references, before the constructor mutates.

### Claim 2 — Every `WakeEventRef` is cancelled FIRST, before any head closure — PASS

`RollbackRecoveryAssignmentPlan` orders its transaction as numbered steps. Step (1) cancels every captured wake, and its rationale is stated inline (`STAGE_01_PROTOCOL_PSEUDOCODE.md:3702–3704`):

> `3702    # (1) X1: cancel every captured WakeCompleteEvent FIRST (so no wake can activate a head being closed).`
> `3703    FOR EACH item in rollback_record.items (stable order):`
> `3704      IF item.WakeEventRef is still pending on EQ: CANCEL item.WakeEventRef on EQ`

Head closure is step (3), strictly later in the procedure body (`STAGE_01_PROTOCOL_PSEUDOCODE.md:3717–3721`):

> `3717    # (3) X1/X7: close the exact plan-created head legally with CANONICAL closure fields; (4) restore the before-image.`
> `3718    FOR EACH item in rollback_record.items (stable order):`
> `3719      IF item.AssignmentID is a live head:`

Cancellation (step 1) precedes departure (step 2, lines 3705–3716) which precedes closure (step 3), guaranteeing no live wake can seat a head that is being torn down.

**Verdict: PASS.** WakeEventRef cancellation is the first step of the transaction, before departure and before any closure.

### Claim 3 — Every still-`WAKING` miner departs to `OFFLINE` via the legal T12 edge ONLY, with the EXACT `assignment_ref` (never null) and the item's complete rollback envelope — PASS

Step (2) departs each still-`WAKING` miner (`STAGE_01_PROTOCOL_PSEUDOCODE.md:3705–3716`):

> `3705    # (2) X1/X2/X8: for every miner still WAKING on its plan-created assignment, depart it to OFFLINE via the LEGAL T12`
> `3710    FOR EACH item in rollback_record.items (stable order):`
> `3711      IF miner_state(item.MinerID) = WAKING AND item.AssignmentID is item.MinerID's bound live head:`
> `3712        SET tr <- CALL ApplyMinerStateTransition(item.MinerID, WAKING, OFFLINE,`
> `3713               transition_envelope = item.rollback_envelope, reason = cancellation,           # X2/X7: complete envelope; legal T12`
> `3714               assignment_ref = assignment_version_ref(item.AssignmentID, item.assignment_version),   # X2: EXACT version, never null`
> `3715               candidate_id = null, propagation_id = null)   # F6/X8`
> `3716        IF tr is transition_applied(teid): SET rolled_to_offline <- true`

The call passes `old_state = WAKING, new_state = OFFLINE` (no other target state is ever passed), `transition_envelope = item.rollback_envelope` (the complete `{ envelope_namespace, event_time, delta_cycle, event_seq, hook_id }` captured at commit, §0.8:785–786), and `assignment_ref = assignment_version_ref(item.AssignmentID, item.assignment_version)` — the exact version, never null.

`WAKING -> OFFLINE` is the legal **T12** edge per `STAGE_01_MINER_STATE_MACHINE.md:530`:

> `| T12 | WAKING | Departure / WakeDeadlineExpiry / ValidationAbort | ... | OFFLINE | End P_wake; begin P_offline residency | No census change (never entered H_active(t)) | ...`

`ApplyMinerStateTransition` (F6) accepts the transition only if the edge is legal (`STAGE_01_PROTOCOL_PSEUDOCODE.md:1028`, "old_state -> new_state is a legal miner transition") and returns exactly one of `{transition_applied, duplicate_suppressed, illegal_stale_source, illegal_transition}` (`STAGE_01_PROTOCOL_PSEUDOCODE.md:1105–1106`); the rollback only marks `rolled_to_offline` on `transition_applied`. No `WAKING -> REGISTERED / RESERVE / LOW_POWER_LISTEN` edge is ever constructed here. The Stage-1X invariant clause reinforces the exclusivity for exactly this procedure (`STAGE_01_INVARIANT_CATALOGUE.md:334–337`, X1/X2: departs "via the legal `T12` edge using the EXACT assignment version ... never `assignment_ref = null`").

**Verdict: PASS.** Departure is `WAKING -> OFFLINE` (T12) only, with the exact non-null versioned assignment_ref and the item's complete rollback envelope, routed through the sole state-transition owner.

### Claim 4 — Each exact plan-created head is closed legally; the coverage/custody ledgers are restored from the before-image — PASS

Steps (3) and (4) close and restore per item (`STAGE_01_PROTOCOL_PSEUDOCODE.md:3718–3723`):

> `3718    FOR EACH item in rollback_record.items (stable order):`
> `3719      IF item.AssignmentID is a live head:`
> `3720        CLOSE item.AssignmentID as CLOSED (status = CLOSED, custody_status = revoked, termination_reason = cancellation,`
> `3721              revocation_reason = assignment_revoked, closure_detail = recovery_install_rolled_back)   # X7: canonical fields (J7/I18b)`
> `3722      RESTORE the coverage-state / custody ledgers for item.AssignmentID's range FROM item.coverage_custody_before_image (I8a/I8b)`
> `3723      ADD item to rolled_back_items`

The close targets `item.AssignmentID` — the exact head, disambiguated by the item's `assignment_version` (§0.8:788) — and sets only canonical enum fields (`status`, `custody_status`, `termination_reason`, `revocation_reason`) plus the non-enum `closure_detail = recovery_install_rolled_back`, matching X7 (`STAGE_01_ROUND_STATE_MACHINE.md:718–721`) and traceability R175. The ledger restore reads the exact I8a/I8b snapshot captured pre-mutation at `STAGE_01_PROTOCOL_PSEUDOCODE.md:3628`.

**Verdict: PASS.** Each exact head is closed with canonical fields and its coverage/custody ledgers are restored from the item's before-image.

### Claim 5 — Coherence is verified; `rollback_completed` can NEVER be returned while a miner is `WAKING` with no live event — PASS

Step (5) is a hard three-way coherence gate before any success return (`STAGE_01_PROTOCOL_PSEUDOCODE.md:3724–3729`):

> `3724    # (5) X1: verify a coherent state — NEVER return rollback_completed while an affected miner is WAKING with no live event.`
> `3725    IF any item.WakeEventRef remains pending on EQ`
> `3726       OR any item.AssignmentID remains a live head`
> `3727       OR any item.MinerID remains WAKING on a plan-created head:`
> `3728      RETURN rollback_failed(reason = residual_partial_assignment)  # X1/T4: caller takes RECOVERY_INSTALL_FAILED_ABORTED / RoundAbort`
> `3729    RETURN rollback_completed(rolled_to_offline, rolled_back_items)  # X1: structured result`

The disjunctive guard fails the rollback if ANY wake is still pending, ANY head is still live, OR ANY miner is still `WAKING` on a plan-created head. Since the third disjunct forces `rollback_failed` whenever a plan-affected miner remains `WAKING`, the procedure structurally cannot reach line 3729 (`rollback_completed`) in that condition. The closing NOTE restates the guarantee (`STAGE_01_PROTOCOL_PSEUDOCODE.md:3734–3735`): "it CANNOT return `rollback_completed` while any affected miner is `WAKING` without a live `WakeCompleteEvent`."

**Verdict: PASS.** The coherence check exists and makes a `WAKING`-with-no-live-event `rollback_completed` unreachable; the alternative is `rollback_failed(residual_partial_assignment)`.

### Claim 6 — A STRUCTURED result is returned: `rollback_completed(rolled_to_offline, rolled_back_items) | rollback_failed(reason)` — PASS

The declared result union (`STAGE_01_PROTOCOL_PSEUDOCODE.md:3730`):

> `3730  RETURNS: rollback_completed(rolled_to_offline, rolled_back_items) | rollback_failed(reason)`

The two payload fields are live values, not placeholders: `rolled_to_offline` is initialised false at `STAGE_01_PROTOCOL_PSEUDOCODE.md:3701` and set true only on an applied T12 departure (line 3716); `rolled_back_items` accumulates every reversed item (line 3723). The success and failure returns at lines 3729 and 3728 respectively realise the union.

**Verdict: PASS.** The procedure returns exactly the two-arm structured union with populated payloads.

### Claim 7 — Both callers capture the structured result and, on incoherence, take RECOVERY_INSTALL_FAILED_ABORTED / RoundAbort — never fabricate UNRECOVERABLE — PASS

**Caller A — `ApplyRecoveryWorkAfterEpilogue`** captures the structured rollback result on an `install_failed_after_mutation` and branches on it (`STAGE_01_PROTOCOL_PSEUDOCODE.md:3026–3037`):

> `3026    IF commit = install_failed_after_mutation(reason, rollback_record):`
> `3027      SET rb <- CALL RollbackRecoveryAssignmentPlan(RoundContext, rollback_record)   # U5/X1: structured rollback result`
> `3028      IF rb = rollback_failed(rr):`
> `3033        SET recovery_episode_disposition[episode] <- RECOVERY_INSTALL_FAILED_ABORTED   # T4 (NOT recovery_outcome_finalised)`
> `3035        CALL RoundAbort(RoundContext, reason = recovery_install_failed_aborted,`
> `3036                        dispatch_envelope = W.due_dispatch_envelope, recovery_finalising = true)   # T4/S4`

The `rollback_completed` arm keeps the episode and stays `SECURITY_RECOVERY` (lines 3038–3042); it never fabricates `UNRECOVERABLE` (comment 3029–3030: "abort (never fabricate UNRECOVERABLE)").

**Caller B — `ApplyRecoveryAssignmentContinuationAfterEpilogue`** captures the structured result on BOTH rollback trigger points:

Post-mutation commit failure (`STAGE_01_PROTOCOL_PSEUDOCODE.md:3507–3524`):

> `3507    IF commit = install_failed_after_mutation(reason, rollback_record):`
> `3508      SET rb <- CALL RollbackRecoveryAssignmentPlan(RoundContext, rollback_record)   # U5/X1: structured rollback result`
> `3509      IF rb = rollback_completed(rolled_to_offline, rolled_back_items):   # X1: no live partial assignment AND no affected miner WAKING`
> `3516      # rb = rollback_failed: an irreversible partial mutation — T4 abort (never fabricate UNRECOVERABLE).`
> `3520      SET recovery_episode_disposition[episode] <- RECOVERY_INSTALL_FAILED_ABORTED       # T4 (NOT recovery_outcome_finalised)`
> `3523      CALL RoundAbort(RoundContext, reason = recovery_install_failed_aborted,`

Post-`CompleteAssignmentPhase` failure, using the captured explicit record `commit_rollback_record` (set at line 3528) (`STAGE_01_PROTOCOL_PSEUDOCODE.md:3540–3552`):

> `3541      SET rb <- CALL RollbackRecoveryAssignmentPlan(RoundContext, commit_rollback_record)   # U5/X5: the EXPLICIT record returned by install_committed`
> `3542      IF rb = rollback_failed(rr):`
> `3543        # irreversible — T4 abort (never fabricate UNRECOVERABLE).`
> `3547        SET recovery_episode_disposition[episode] <- RECOVERY_INSTALL_FAILED_ABORTED`
> `3550        CALL RoundAbort(RoundContext, reason = recovery_install_failed_aborted,`

In both callers the `rollback_completed` arm rolls the round state back to `SECURITY_RECOVERY` with `APPLY_FAILED` and preserves the episode (lines 3509–3515, 3553–3558), while the `rollback_failed` arm takes `RECOVERY_INSTALL_FAILED_ABORTED` + recovery-finalising `RoundAbort`. This matches I16's T4 clause (`STAGE_01_INVARIANT_CATALOGUE.md:292–298`): an irreversible install failure is recorded as `RECOVERY_INSTALL_FAILED_ABORTED` / `APPLY_FAILED_TERMINAL` and "is NEVER relabelled as an `UNRECOVERABLE` floor outcome."

**Verdict: PASS.** Both callers capture the structured result and, on `rollback_failed`, take the declared `RECOVERY_INSTALL_FAILED_ABORTED` / `RoundAbort` path without fabricating `UNRECOVERABLE`.

---

## Test-vector linkage

Traceability row **R177** (`STAGE_01_TRACEABILITY_MATRIX.csv:178`) declares the blocking Stage-1X test vectors that exercise the X1 behaviours audited above, targeting `STAGE_01X_SEMANTIC_TEST_VECTORS` and the named procedures:

- **TV198** — `CommitRecoveryAssignmentPlan` builds a `rollback_record` whose items carry the exact `AssignmentID`, `assignment_version`, `WakeEventRef`, and before-image for every committed activation (exercises **Claim 1**).
- **TV199** — `RollbackRecoveryAssignmentPlan` departs a still-`WAKING` committed miner to `OFFLINE` via **T12** with the exact `assignment_version_ref` and `rollback_envelope`, and returns `rollback_completed` only after no miner is `WAKING` (exercises **Claims 3, 5, 6**).
- **TV200** — a recovery-plan rollback restores the coverage/custody ledgers to the before-image (exercises **Claim 4**).

(The same row continues with TV201–TV209 covering the sibling X2–X8 corrections; TV205 in particular exercises the caller capturing `commit.rollback_record` for a post-`CompleteAssignmentPhase` rollback, i.e. Caller B above.)

## Cross-document consistency

The pseudocode's X1 realisation is consistent with, and mutually reinforced by, the two governing specification documents:

- **Round state machine §3.10b, X1** (`STAGE_01_ROUND_STATE_MACHINE.md:683–689`) states that `RollbackRecoveryAssignmentPlan` consumes a `rollback_record` of the nine-field per-item records, "cancels every `WakeEventRef`, departs every still-`WAKING` miner to `OFFLINE` via the legal `T12` edge, closes the exact head, and restores the before-image," "CANNOT return `rollback_completed` while any affected miner is `WAKING` with no live `WakeCompleteEvent`," and on an irreversible residual "the caller takes the declared `RECOVERY_INSTALL_FAILED_ABORTED` / `RoundAbort` path." This matches `STAGE_01_PROTOCOL_PSEUDOCODE.md:3695–3738` step-for-step (also summarised at §3.9 U5, `STAGE_01_ROUND_STATE_MACHINE.md:560–566`).
- **Invariant I16, Stage-1X clause X1/X2** (`STAGE_01_INVARIANT_CATALOGUE.md:334–338`) states that `RollbackRecoveryAssignmentPlan` departs every still-`WAKING` miner to `OFFLINE` "via the legal `T12` edge using the EXACT assignment version (`rollback_record` items ..., never `assignment_ref = null`) and a complete rollback envelope; [it] cannot report `rollback_completed` while any affected miner is `WAKING` without a live `WakeCompleteEvent`," with T4 (`:292–298`) forbidding a fabricated `UNRECOVERABLE`. This is exactly the pseudocode's behaviour at lines 3711–3715 (exact version, complete envelope), 3724–3729 (coherence gate), and the two callers at 3033–3037 / 3520–3524 / 3547–3552.

No inconsistency was found between the pseudocode, the round state machine §3.10b (X1), the miner state machine (T12 legality, `STAGE_01_MINER_STATE_MACHINE.md:530`), and invariant I16 (Stage-1X clause). This is a documentation-only audit; no pseudocode or other artifact was modified, and no executable experiment was run.

---

## Result

**RESULT: PASS** — correction X1 ("make `RollbackRecoveryAssignmentPlan` a COMPLETE state transaction") is fully and consistently realised in `STAGE_01_PROTOCOL_PSEUDOCODE.md`; all seven audited claims verify PASS, are exercised by TV198–TV200, and are consistent with round-SM §3.10b (X1) and invariant I16 (Stage-1X).
