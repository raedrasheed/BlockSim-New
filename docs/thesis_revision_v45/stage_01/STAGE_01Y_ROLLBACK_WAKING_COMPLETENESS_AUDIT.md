# STAGE 01Y — Rollback WAKING-Completeness Audit (correction Y4)

**Deliverable:** `STAGE_01Y_ROLLBACK_WAKING_COMPLETENESS_AUDIT.md`
**Stage / correction:** Stage 1Y, correction **Y4** — "a rollback resolves every affected `WAKING` miner UNCONDITIONALLY."
**Algorithm:** PoCol. **Mechanism under audit:** the idle policy within PoCol (setup / recovery-plan rollback and its wake resolution).
**Source of truth (READ-ONLY):** `STAGE_01_PROTOCOL_PSEUDOCODE.md` (5230 lines).
**Cross-referenced:** `STAGE_01_ROUND_STATE_MACHINE.md` §3.10c (Y4), `STAGE_01_INVARIANT_CATALOGUE.md` I16 (Stage-1Y clause) + I19 (residency single-owner), `STAGE_01_TERMINOLOGY.md` (`wake_by_miner` / `before_image_by_miner`, `AbortPendingWakeForRollback`), `STAGE_01Y_SEMANTIC_TEST_VECTORS.md` (TV214, TV215, TV217), `STAGE_01_TRACEABILITY_MATRIX.csv` (R181).

## Purpose and method

Correction Y4 requires that reverting a failed setup or a partially/fully-committed recovery-assignment plan resolve **every affected `WAKING` miner** — not only those whose assignment is still a live bound head. A `CLOSED` / revoked / detached head does **not** make a `WAKING` miner safe: the miner is the residency owner, so a rollback that returned `rollback_completed` while an affected miner was still `WAKING` would strand `WAKING` residency past the round and violate I16/I19. This audit verifies that the correction is fully and consistently realised across all three rollback owners and the shared named operation, grounding each claim in the actual current text of `STAGE_01_PROTOCOL_PSEUDOCODE.md` by procedure name and quoted `file:line`.

The relevant procedures and their current anchors are:

- `RollbackRecoveryAssignmentPlan` — `STAGE_01_PROTOCOL_PSEUDOCODE.md:3801`
- `RollbackParticipantSetup` — `STAGE_01_PROTOCOL_PSEUDOCODE.md:1769`
- `RollbackTemplateRefreshSetup` — `STAGE_01_PROTOCOL_PSEUDOCODE.md:1806`
- `AbortPendingWakeForRollback` — `STAGE_01_PROTOCOL_PSEUDOCODE.md:1721`
- `PrepareParticipantsForNewRound` (participant setup_txn capture) — `STAGE_01_PROTOCOL_PSEUDOCODE.md:1597`
- `ContinueTemplateRefreshAssignmentSetup` (refresh setup_txn capture) — `STAGE_01_PROTOCOL_PSEUDOCODE.md:4851`
- callers on the recovery-install path: `ApplyRecoveryWorkAfterEpilogue` — `:3133`; `ApplyRecoveryAssignmentContinuationAfterEpilogue` — `:3614` and `:3647`

The §0.8 preamble fixes the Y4/Y5 contract that the procedure bodies must realise (`STAGE_01_PROTOCOL_PSEUDOCODE.md:819–833`):

> `819  # --- Y4/Y5 unconditional WAKING resolution + one named legal-T12 rollback op with one closure owner ---`
> `820  # setup_transaction additionally carries (Y4): before_image_by_miner : map MinerID -> coverage_custody_before_image,`
> `821  #   captured immediately AFTER assignment_created and BEFORE StartWake, so a setup rollback can restore the ledgers`
> `822  #   through the same named operation regardless of whether the head is still live.`
> `831  #   (6) restores the ledgers from the before-image; (7) returns a structured result. It resolves a WAKING miner`
> `832  #   UNCONDITIONALLY (Y4) — a CLOSED / revoked / detached assignment does NOT make a WAKING miner safe — and the caller's`
> `833  #   final coherence gate is "no affected MinerID remains WAKING" (not "no miner WAKING on a plan-created head").`

---

## Claim-by-claim verification

### Claim 1 — All three rollback owners resolve EVERY affected `WAKING` miner unconditionally (no live-bound-head precondition) — PASS

**`RollbackRecoveryAssignmentPlan`.** After cancelling every captured wake first, it iterates *every* item and delegates to `AbortPendingWakeForRollback` with no gate on "item.AssignmentID is the miner's bound live head" (`STAGE_01_PROTOCOL_PSEUDOCODE.md:3811–3821`):

> `3811    # (2) Y4/Y5/X1/X2/X8: resolve EVERY affected miner through the ONE named rollback operation, UNCONDITIONALLY — it does`
> `3812    #   NOT require item.AssignmentID to remain a live bound head (a CLOSED / revoked / detached head does NOT make a`
> `3813    #   WAKING miner safe, Y4). ...`
> `3817    FOR EACH item in rollback_record.items (stable order):`
> `3818      SET wr <- CALL AbortPendingWakeForRollback(RoundContext, MinerID = item.MinerID, AssignmentID = item.AssignmentID,`

The loop condition is `FOR EACH item in rollback_record.items` — the call is made for each `item.MinerID` with no interposed `IF item.AssignmentID is a live head` guard.

**`RollbackParticipantSetup`.** It iterates `setup_txn.assignment_by_miner` (every miner given a setup-created assignment) and calls `AbortPendingWakeForRollback` for each, explicitly unconditionally (`STAGE_01_PROTOCOL_PSEUDOCODE.md:1779–1787`):

> `1779    # Y4/Y5: resolve EVERY affected miner (every miner given a setup-created assignment) through the ONE named rollback`
> `1780    #   operation, UNCONDITIONALLY — it does NOT require the head to remain a live bound head. ...`
> `1783    FOR EACH (MinerID m, (aid, ver)) in setup_txn.assignment_by_miner (stable order by MinerID):`
> `1784      SET wr <- CALL AbortPendingWakeForRollback(RoundContext, MinerID = m, AssignmentID = aid, assignment_version = ver,`

**`RollbackTemplateRefreshSetup`.** Identical discipline, same iteration over `setup_txn.assignment_by_miner`, same unconditional call (`STAGE_01_PROTOCOL_PSEUDOCODE.md:1812–1819`):

> `1812    # W1/W2/X2/X7/Y4/Y5: identical rollback discipline as RollbackParticipantSetup, for the refresh's just-created`
> `1813    #   assignments/wakes. It resolves EVERY affected miner through the ONE named operation UNCONDITIONALLY.`
> `1815    FOR EACH (MinerID m, (aid, ver)) in setup_txn.assignment_by_miner (stable order by MinerID):`
> `1816      SET wr <- CALL AbortPendingWakeForRollback(RoundContext, MinerID = m, AssignmentID = aid, assignment_version = ver,`

The shared operation itself states the unconditional precondition (`STAGE_01_PROTOCOL_PSEUDOCODE.md:1727–1730`):

> `1727  PRECONDITIONS: called by RollbackRecoveryAssignmentPlan / RollbackParticipantSetup / RollbackTemplateRefreshSetup to`
> `1728                 resolve ONE affected miner. Y4: it resolves a WAKING miner UNCONDITIONALLY — it does NOT require`
> `1729                 AssignmentID to still be a live bound head; a CLOSED / revoked / detached assignment does NOT make a`
> `1730                 WAKING miner safe.`

All three owners resolve every affected miner unconditionally; none gates the call on the assignment being a live bound head. **PASS.**

### Claim 2 — The final coherence gate is "no affected miner remains `WAKING`" in all three owners — PASS

**`RollbackRecoveryAssignmentPlan`** (`STAGE_01_PROTOCOL_PSEUDOCODE.md:3827–3833`):

> `3827    # (5) Y4/X1: verify a coherent state — NEVER return rollback_completed while ANY affected miner remains WAKING`
> `3828    #   (the gate is "no item.MinerID remains WAKING", NOT "no miner WAKING on a plan-created head").`
> `3829    IF any item.WakeEventRef remains pending on EQ`
> `3830       OR any item.AssignmentID remains a live head`
> `3831       OR any item.MinerID remains WAKING:`
> `3832      RETURN rollback_failed(reason = residual_partial_assignment)  # X1/T4: caller takes RECOVERY_INSTALL_FAILED_ABORTED / RoundAbort`
> `3833    RETURN rollback_completed(rolled_to_offline, rolled_back_items)  # X1: structured result`

The disjunct `any item.MinerID remains WAKING` keys on the miner, not on "a plan-created head." `rollback_completed` is reached only when that gate is clear.

**`RollbackParticipantSetup`** (`STAGE_01_PROTOCOL_PSEUDOCODE.md:1792–1797`):

> `1792    # Y4 FINAL COHERENCE GATE: NO affected miner remains WAKING (not merely "no miner WAKING on a live head").`
> `1793    IF any m in setup_txn.assignment_by_miner remains WAKING`
> `1794       OR any aid in setup_txn.assignment_by_miner remains a live head`
> `1795       OR any setup_txn.wakes entry remains pending on EQ:`
> `1796      RETURN rollback_failed(reason = residual_partial_setup)`
> `1797    RETURN rollback_completed(rolled_to_offline)   # W2/W8: report whether a retry is state-incompatible`

**`RollbackTemplateRefreshSetup`** (`STAGE_01_PROTOCOL_PSEUDOCODE.md:1824–1829`):

> `1824    # Y4 FINAL COHERENCE GATE: NO affected miner remains WAKING.`
> `1825    IF any m in setup_txn.assignment_by_miner remains WAKING`
> `1826       OR any aid in setup_txn.assignment_by_miner remains a live head`
> `1827       OR any setup_txn.wakes entry remains pending on EQ:`
> `1828      RETURN rollback_failed(reason = residual_partial_setup)`
> `1829    RETURN rollback_completed(rolled_to_offline)   # W2/W8`

In each owner the first disjunct of the gate is the residual-`WAKING` test keyed on the affected `MinerID` (`item.MinerID` / `m in setup_txn.assignment_by_miner`), and `rollback_completed` is the fall-through only after the gate passes. **PASS.**

### Claim 3 — `setup_txn` carries `wake_by_miner` + `before_image_by_miner`, captured after `assignment_created` and before `StartWake` — PASS

**Participant setup.** `PrepareParticipantsForNewRound` initialises the transaction with both maps (`STAGE_01_PROTOCOL_PSEUDOCODE.md:1611–1613`):

> `1611    SET participant_setup_txn <- setup_transaction(rollback_envelope = dispatch_envelope,`
> `1612          wakes = empty, created_assignments = empty, prior_states = empty, assignment_by_miner = empty,`
> `1613          wake_by_miner = empty, before_image_by_miner = empty)   # W1/V8/X2/Y4`

Inside the loop, the constructor result is inspected first (`SET a <- cr.assignment` at `:1659`, reached only on `assignment_created`); the before-image is then captured, and the wake is captured only after `StartWake` returns `wake_seated` (`STAGE_01_PROTOCOL_PSEUDOCODE.md:1662–1668`):

> `1662      SET participant_setup_txn.assignment_by_miner[m] <- (AssignmentID(a), assignment_version(a))   # X2: EXACT version, populated BEFORE StartWake`
> `1663      SET participant_setup_txn.before_image_by_miner[m] <- coverage_custody_before_image(spec.range)   # Y4: I8a/I8b snapshot BEFORE StartWake`
> `1664      SET wr <- CALL StartWake(RoundContext, m, target_assignment = a, from_state = spec.from,`
> `1666      IF wr = wake_seated(waid, wref, wtt, ws):`
> `1668        SET participant_setup_txn.wake_by_miner[m] <- wref                                # Y4: exact per-miner wake for AbortPendingWakeForRollback`

The `before_image_by_miner[m]` write at `:1663` sits after the assignment is created (`:1659`) and strictly before the `StartWake` call at `:1664`, exactly as the §0.8 contract requires. `RollbackParticipantSetup` then consumes both maps, passing `setup_txn.wake_by_miner[m]` and `setup_txn.before_image_by_miner[m]` into the named operation (`STAGE_01_PROTOCOL_PSEUDOCODE.md:1785,1787`).

**Template-refresh setup.** `ContinueTemplateRefreshAssignmentSetup` mirrors this exactly (`STAGE_01_PROTOCOL_PSEUDOCODE.md:4874–4897`):

> `4874    SET refresh_setup_txn <- setup_transaction(rollback_envelope = dispatch_envelope,`
> `4876          wake_by_miner = empty, before_image_by_miner = empty)   # W1/W3/X2/Y4`
> `4889      SET refresh_setup_txn.assignment_by_miner[m] <- (AssignmentID(assignment_m), assignment_version(assignment_m))   # X2: EXACT version BEFORE StartWake`
> `4890      SET refresh_setup_txn.before_image_by_miner[m] <- coverage_custody_before_image(fr)   # Y4: I8a/I8b snapshot BEFORE StartWake`
> `4893      SET wr <- CALL StartWake(RoundContext, m, target_assignment = assignment_m, from_state = miner_state(m),`
> `4897        SET refresh_setup_txn.wake_by_miner[m] <- wref                               # Y4: exact per-miner wake for AbortPendingWakeForRollback`

Here too the before-image is snapshotted (`:4890`) after `cr = assignment_created` (`SET assignment_m <- cr.assignment` at `:4886`) and before `StartWake` (`:4893`), and the wake is captured on `wake_seated`. Both setup transactions carry both per-miner maps captured before `StartWake`. The recovery-plan path uses the equivalent per-item pre-images (`WakeEventRef`, `coverage_custody_before_image`) captured in the `rollback_item` by `CommitRecoveryAssignmentPlan`, as fixed in §0.8 (`STAGE_01_PROTOCOL_PSEUDOCODE.md:781–788`). **PASS.**

### Claim 4 — An already-CLOSED / unbound head with a `WAKING` miner is still resolved (or `rollback_failed`) — never `rollback_completed` with the miner `WAKING` — PASS

`AbortPendingWakeForRollback` departs the miner and closes the head as two separable steps. The `WAKING -> OFFLINE` departure runs whenever the miner is `WAKING`, independent of head liveness (`STAGE_01_PROTOCOL_PSEUDOCODE.md:1740–1748`):

> `1740    IF miner_state(MinerID) = WAKING:`
> `1741      SET tr <- CALL ApplyMinerStateTransition(MinerID, WAKING, OFFLINE,`
> `1742             transition_envelope = rollback_envelope, reason = validation_abort,                      # Y5: authoritative T12 trigger`
> `1748        RETURN wake_abort_failed(MinerID = MinerID, AssignmentID = AssignmentID, reason = tr)   # Y4/T4: caller aborts`

The canonical close (step 3) is explicitly a no-op for an already-closed head — it is guarded by "still a live head," so a head already `CLOSED` by an earlier self-rollback is left as-is, making the operation idempotent (`STAGE_01_PROTOCOL_PSEUDOCODE.md:1749–1753`):

> `1749    # (3) Y5: the SINGLE canonical assignment close (X7 fields). Performed EXACTLY ONCE here, only if the head is still`
> `1750    #   live (a head already CLOSED by an earlier self-rollback is left as-is — idempotent).`
> `1751    IF AssignmentID (version assignment_version) is a live head:`
> `1752      CLOSE AssignmentID (version assignment_version) as CLOSED (status = CLOSED, custody_status = revoked,`

Step 7 then verifies the miner is no longer `WAKING`; a residual returns `wake_abort_failed` (`STAGE_01_PROTOCOL_PSEUDOCODE.md:1756–1759`):

> `1756    # (7) Y4: verify THIS miner is no longer WAKING; a residual is a failure the caller escalates.`
> `1757    IF miner_state(MinerID) = WAKING:`
> `1758      RETURN wake_abort_failed(MinerID = MinerID, AssignmentID = AssignmentID, reason = residual_waking)`
> `1759    RETURN wake_abort_completed(MinerID = MinerID, AssignmentID = AssignmentID, departed_to_offline = departed_to_offline)`

So for a rollback item whose head is already `CLOSED`/unbound but whose miner is `WAKING`: the departure still fires (Claim 1 delegation is unconditional), the close step is a harmless no-op, and either the miner is departed (`wake_abort_completed`) or the operation returns `wake_abort_failed`. In the owner, `wake_abort_failed` immediately returns `rollback_failed` (`:3825–3826`, `:1790–1791`, `:1822–1823`), and even a spurious `wake_abort_completed` cannot yield `rollback_completed` because the final `any … remains WAKING` gate (Claim 2) would still fail. This is precisely TV215. There is no path to `rollback_completed` with an affected miner still `WAKING`. **PASS.**

### Claim 5 — An unresolved affected miner → `rollback_failed` → `RECOVERY_INSTALL_FAILED_ABORTED` / `RoundAbort` — PASS

`AbortPendingWakeForRollback` returns `wake_abort_failed` when the miner cannot be legally departed (illegal/stale source → `:1747–1748`) or a residual `WAKING` survives (`:1758`). Each owner converts that into `rollback_failed` (`RollbackRecoveryAssignmentPlan` `:3825–3826`; `RollbackParticipantSetup` `:1790–1791`; `RollbackTemplateRefreshSetup` `:1822–1823`).

On the recovery-install path, the caller consumes `rollback_failed` and takes the declared abort. `ApplyRecoveryWorkAfterEpilogue` (`STAGE_01_PROTOCOL_PSEUDOCODE.md:3133–3143`):

> `3133      SET rb <- CALL RollbackRecoveryAssignmentPlan(RoundContext, rollback_record)   # U5/X1: structured rollback result`
> `3134      IF rb = rollback_failed(rr):`
> `3139        SET recovery_episode_disposition[episode] <- RECOVERY_INSTALL_FAILED_ABORTED   # T4 (NOT recovery_outcome_finalised)`
> `3141        CALL RoundAbort(RoundContext, reason = recovery_install_failed_aborted,`
> `3142                        dispatch_envelope = W.due_dispatch_envelope, recovery_finalising = true)   # T4/S4`

`ApplyRecoveryAssignmentContinuationAfterEpilogue` takes the same path on both its rollback sites — the post-mutation install failure (`:3622–3631`) and the post-`CompleteAssignmentPhase` rollback (`:3648–3658`):

> `3648      IF rb = rollback_failed(rr):`
> `3653        SET recovery_episode_disposition[episode] <- RECOVERY_INSTALL_FAILED_ABORTED`
> `3656        CALL RoundAbort(RoundContext, reason = recovery_install_failed_aborted,`

For the two setup owners the escalation is the corresponding declared `RoundAbort`: `PrepareParticipantsForNewRound` aborts with `participant_setup_rollback_failed` (`STAGE_01_PROTOCOL_PSEUDOCODE.md:1683–1685`) and `ContinueTemplateRefreshAssignmentSetup` aborts with `template_refresh_rollback_failed` (`STAGE_01_PROTOCOL_PSEUDOCODE.md:4911–4913`). In every case an unresolved affected miner escalates to a declared `RoundAbort` — never a fabricated `UNRECOVERABLE`, and never a silent completion. This is precisely TV217. **PASS.**

### Claim 6 — No rollback can return `rollback_completed` while an affected miner is `WAKING` (gate quotes) — PASS

This is the conjunction of Claims 1, 2, and 4, stated as a single reachability property. In each owner the only `rollback_completed` return is the fall-through *after* the residual-`WAKING` disjunct:

- `RollbackRecoveryAssignmentPlan`: `IF … OR any item.MinerID remains WAKING: RETURN rollback_failed(…)` then `RETURN rollback_completed(rolled_to_offline, rolled_back_items)` (`STAGE_01_PROTOCOL_PSEUDOCODE.md:3831–3833`).
- `RollbackParticipantSetup`: `IF any m in setup_txn.assignment_by_miner remains WAKING … RETURN rollback_failed(…)` then `RETURN rollback_completed(rolled_to_offline)` (`STAGE_01_PROTOCOL_PSEUDOCODE.md:1793–1797`).
- `RollbackTemplateRefreshSetup`: `IF any m in setup_txn.assignment_by_miner remains WAKING … RETURN rollback_failed(…)` then `RETURN rollback_completed(rolled_to_offline)` (`STAGE_01_PROTOCOL_PSEUDOCODE.md:1825–1829`).

The per-item early return on `wake_abort_failed` (`:3825–3826`, `:1790–1791`, `:1822–1823`) closes the other route: a miner the named operation could not resolve never reaches the `rollback_completed` line at all. The procedure NOTEs restate the guarantee in prose — e.g. `RollbackRecoveryAssignmentPlan`: "Its final gate is 'no affected MinerID remains WAKING' — it CANNOT return rollback_completed while any affected miner is WAKING." (`STAGE_01_PROTOCOL_PSEUDOCODE.md:3840–3841`). **PASS.**

---

## Test-vector linkage

| Vector | Correction | What it exercises | Verified by |
|--------|-----------|-------------------|-------------|
| **TV214** | Y4/Y5 | Two committed items enter `WAKING`, a third fails; the rollback cancels both wakes, then calls `AbortPendingWakeForRollback` for BOTH affected miners (each departs `WAKING -> OFFLINE` via `T12`, closes its exact head canonically, restores its before-image) and returns `rollback_completed` with both resolved — no affected miner remains `WAKING`. | Claims 1, 2, 3, 6 (`:3808–3833`, `:781–788`) |
| **TV215** | Y4 | A `rollback_item` whose `AssignmentID` is already `CLOSED`/unbound while `miner_state(item.MinerID) = WAKING`: the unconditional resolution still departs the `WAKING` miner (canonical close is a no-op for the already-closed head); if it cannot be departed, `wake_abort_failed` → `rollback_failed`; never `rollback_completed` with the miner `WAKING`. | Claim 4 (`:1740–1759`) |
| **TV217** | Y4 | One affected miner cannot complete the legal `T12` rollback (`ApplyMinerStateTransition` returns `illegal_stale_source` / `illegal_transition`): `AbortPendingWakeForRollback` → `wake_abort_failed`; `RollbackRecoveryAssignmentPlan` → `rollback_failed(residual_partial_assignment)`; caller records `RECOVERY_INSTALL_FAILED_ABORTED` and takes the declared `RoundAbort` — never a fabricated `UNRECOVERABLE`, never `rollback_completed`. | Claims 5, 6 (`:1747–1748`, `:3134–3143`) |

The three vectors are declared in `STAGE_01Y_SEMANTIC_TEST_VECTORS.md` (TV214 at line 60, TV215 at 72, TV217 at 93) and their coverage-summary rows (lines 125, 126, 128) name the same primary procedures audited above.

## Cross-document consistency

| Document | Statement | Agreement with the pseudocode |
|----------|-----------|-------------------------------|
| **Pseudocode** §0.8 + procedure bodies | Unconditional affected-`WAKING` resolution; gate "no affected `MinerID` remains `WAKING`"; `before_image_by_miner` / `wake_by_miner` captured after `assignment_created`, before `StartWake`. | Baseline (`:819–833`, `:1611–1613`, `:1662–1668`, `:1792–1797`, `:3811–3833`, `:4874–4897`). |
| **Round SM** §3.10c (Y4) | "resolve every affected `WAKING` miner REGARDLESS of whether its assignment remains a live bound head; … The final coherence gate is 'no affected miner remains `WAKING`'. A rollback with an unresolved affected `WAKING` miner returns `rollback_failed` and the caller takes the declared `RECOVERY_INSTALL_FAILED_ABORTED` / `RoundAbort` path." | Matches Claims 1, 2, 5 verbatim (`STAGE_01_ROUND_STATE_MACHINE.md:754–758`). |
| **Invariant I16** (Stage-1Y clause, Y4) | "a rollback resolves every affected `WAKING` miner UNCONDITIONALLY (independent of whether the head is still live) and its coherence gate is 'no affected miner remains `WAKING`'." | Matches Claims 1–2 (`STAGE_01_INVARIANT_CATALOGUE.md:356–357`). Consequence-of-violation names the exact defect Y4 closes: "a branch-C install failure silently reported as a genuine `UNRECOVERABLE`" (`:365–366`), consistent with Claim 5. |
| **Invariant I19** (residency single-owner) | Residency time has a single owner (`ApplyMinerStateTransition`) and is never double-counted; no `WAKING` residency may survive to horizon `T`. | The unconditional `WAKING -> OFFLINE` departure closes `WAKING` residency at the rollback time and charges the transition energy exactly once (`:1741–1744`), so a resolved rollback leaves no open `WAKING` interval — exactly what I19 requires (`STAGE_01_INVARIANT_CATALOGUE.md:460–499`). The A1 baseline `8.420833333 kWh` is unaffected (structural accounting only, I19 scope note). |
| **Terminology** | `setup_txn.wake_by_miner` / `setup_txn.before_image_by_miner` "captured after `assignment_created` and before `StartWake`"; `AbortPendingWakeForRollback` "resolves a `WAKING` miner UNCONDITIONALLY — a `CLOSED`/revoked/detached head does not make a `WAKING` miner safe." | Matches Claims 3, 1, 4 (`STAGE_01_TERMINOLOGY.md:925–936`). |
| **Traceability** R181 | "resolve every affected `WAKING` miner regardless of whether its assignment remains a live bound head … the final coherence gate is no affected miner remains `WAKING` … a rollback with an unresolved affected `WAKING` miner returns `rollback_failed` and the caller takes the declared `RECOVERY_INSTALL_FAILED_ABORTED` / `RoundAbort` path; setup_txn carries `wake_by_miner` and `before_image_by_miner`." Procedures: the three rollback owners + `AbortPendingWakeForRollback`; invariants I16/I19/I18b; vectors TV214/TV215/TV217. | Matches all six claims and the vector/invariant linkage above (`STAGE_01_TRACEABILITY_MATRIX.csv` line 182). |

All six sources describe the same Y4 contract with no divergence: the three rollback owners resolve every affected `WAKING` miner unconditionally through the one named operation `AbortPendingWakeForRollback`, gate on "no affected miner remains `WAKING`," carry the per-miner `wake_by_miner` / `before_image_by_miner` maps captured before `StartWake`, and escalate an unresolved miner to a declared `RoundAbort` (`RECOVERY_INSTALL_FAILED_ABORTED` on the recovery-install path).

## Deliverable context

This audit is deliverable 5 of the Stage-1Y set. The final Stage-1Y tree comprises the twelve `STAGE_01Y_*` deliverables — the correction report; the five per-correction audits (`STAGE_01Y_SETUP_RETRY_REPLAY_AUDIT.md` (Y1), `STAGE_01Y_TEMPLATE_RETRY_IDENTITY_AUDIT.md` (Y2), `STAGE_01Y_RETRY_GENERATION_OWNERSHIP_AUDIT.md` (Y3), this file (Y4), `STAGE_01Y_T12_CLOSURE_OWNERSHIP_AUDIT.md` (Y5)); the procedure signature/call audit and procedure call graph; the semantic test vectors (TV210–TV218); the supersession register; the cross-document audit; and the checksum manifest — alongside the six modified normative `STAGE_01_*` documents (`STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_MINER_STATE_MACHINE.md`, `STAGE_01_ROUND_STATE_MACHINE.md`, `STAGE_01_INVARIANT_CATALOGUE.md`, `STAGE_01_TERMINOLOGY.md`, `STAGE_01_TRACEABILITY_MATRIX.csv`). The Stage-1A–1X lettered artifacts are unchanged; Stage-1Y supersessions are recorded in `STAGE_01Y_SUPERSESSION_REGISTER.md`. This revision is documentation-only: the algorithm remains PoCol, the mechanism remains the idle policy within PoCol, and the A1 baseline `8.420833333 kWh` is preserved.

---

## Result

**PASS — Y4 fully realised: all three rollback owners (`RollbackRecoveryAssignmentPlan`, `RollbackParticipantSetup`, `RollbackTemplateRefreshSetup`) resolve every affected `WAKING` miner unconditionally through `AbortPendingWakeForRollback`, gate on "no affected miner remains `WAKING`" over `setup_txn`'s `wake_by_miner` / `before_image_by_miner` (captured before `StartWake`), can never return `rollback_completed` with an affected miner `WAKING`, and escalate an unresolved miner via `rollback_failed` to `RECOVERY_INSTALL_FAILED_ABORTED` / `RoundAbort` — consistent across pseudocode, round-SM §3.10c, invariants I16/I19, terminology, R181, and vectors TV214/TV215/TV217.**
