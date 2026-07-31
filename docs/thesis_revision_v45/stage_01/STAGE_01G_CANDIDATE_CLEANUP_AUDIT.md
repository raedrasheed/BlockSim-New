# Stage 1G — Candidate-Cleanup & Recovery-Coexistence Audit (G8)

**Document status:** Stage-1 audit deliverable, documentation only. This audit confirms the
structure of correction **G8** in the PoCol specification: propagation during
`SECURITY_RECOVERY`, the per-round registries, and the complete cleanup / disposition of live
candidate contexts on abort, closure, and template refresh. It cross-checks
`STAGE_01_PROTOCOL_PSEUDOCODE.md` (RoundInitialise, ValidBlockAccept, RoundAbort,
CloseRoundAssignments, CloseTemplateAssignments, SecurityFloorEvaluate, HandlePropagationFailure)
and `STAGE_01_ROUND_STATE_MACHINE.md` (§2.5, R6, R13). It claims no property beyond structure.

## 1. Round registries

`RoundInitialise` establishes the per-round propagation/acceptance registries and counters (G8):

| Registry / counter | Initial value | Purpose |
|--------------------|---------------|---------|
| `active_propagation_set` | empty | holds propagation-active CPCs (`PROPAGATING`/`PENDING_ACCEPTANCE`) |
| `acceptance_batch_registry` | empty | maps `(acceptance_timestamp, acceptance_point) -> registered block arrivals` |
| `candidate_discovery_seq` | `0` | monotonic per-round counter for deterministic `CandidateID` (G7) |
| `block_accepted` | `false` | single-closure guard, set true only once a block is accepted |
| `state_version` | `0` | monotonic round-state epoch, bumped on every round-state transition (G10) |

## 2. SECURITY_RECOVERY coexistence

- `SECURITY_RECOVERY` MAY coexist with a **non-empty** `active_propagation_set`. The round-state
  and the propagation set are NOT identified (§0.6, §2.5).
- Entering `SECURITY_RECOVERY` (via the scheduled `SecurityFloorEvaluate`) does **NOT** cancel
  live candidate contexts; the breach transition preserves them.
- Block arrivals and `AcceptanceBatchFinalize` remain processable during recovery.
- `ValidBlockAccept`'s precondition allows `round_state in {SOLUTION_PROPAGATION,
  SECURITY_RECOVERY}` (winner's `RoundID`/`TemplateID` still valid), so a valid candidate MAY
  close a recovery-state round in a single transition (round SM **R6**: `SECURITY_RECOVERY ->
  ROUND_ACCEPTED`).
- After recovery (round SM **R13**): return to `SOLUTION_PROPAGATION` when live candidates remain
  in `active_propagation_set`, else to `HASHING` (via re-`ASSIGNMENT`) once `propagation_quiescent`
  holds.
- `HandlePropagationFailure` keeps the round in `SECURITY_RECOVERY` (it does NOT force `HASHING`)
  while in recovery; it returns to `HASHING` only when `round_state = SOLUTION_PROPAGATION` AND
  `propagation_quiescent`.

## 3. Cleanup on closure / abort / refresh

| Procedure | Disposition of live contexts | Event cancellation | Registry effect |
|-----------|------------------------------|--------------------|-----------------|
| `ValidBlockAccept` (acceptance) | winner -> `ACCEPTED`; every OTHER live context -> `COMPETING`/`STALE`/`CANCELLED` | cancels every other context's certificate-arrival + block-arrival events | `CLEAR active_propagation_set`; single `ROUND_ACCEPTED` transition; closes exactly once under the `block_accepted` guard |
| `RoundAbort` | FOR EACH `cpc` in sorted `active_propagation_set` set `CANCELLED`, cancel its events, remove | cancels each context's certificate-arrival + block-arrival events | `CLEAR active_propagation_set` and `acceptance_batch_registry`; then `CloseRoundAssignments(ROUND_ABORTED)` cancels wake/resume/certificate/BlockAcceptancePoint/HashWorkEvent events |
| `CloseRoundAssignments` | closes every open assignment under the closing `RoundID`/`TemplateID` via legal per-state edges | cancels wake/resume/certificate-arrival/BlockAcceptancePoint/HashWorkEvent/AdversarialParticipationChangeEvent events for `RoundID` | `CLEAR active_propagation_set` and `acceptance_batch_registry` |
| `CloseTemplateAssignments` (template refresh) | old-template candidate contexts -> `CANCELLED`, cancel their events, remove from set | cancels certificate-arrival/BlockAcceptancePoint/resume/HashWorkEvent events bound to `old_TemplateID` | clears matching `acceptance_batch_registry` entries — WITHOUT modifying any historical record |

Notes on the four paths:

- **Acceptance** is the ONE place cross-candidate cancellation is legitimate; the `block_accepted`
  guard makes a second same-round acceptance a no-op, so closure happens exactly once.
- **RoundAbort** iterates in stable `CandidateID` order, dispositions every live context, clears
  both registries, then routes closure through the single centralised path.
- **CloseRoundAssignments** is the SOLE round-closure path (called by `ValidBlockAccept` with
  `ROUND_ACCEPTED` and by `RoundAbort` with `ROUND_ABORTED`); it preserves coverage/custody/
  provenance and reassigns nothing under the closed `TemplateID`.
- **CloseTemplateAssignments** discards the OLD search domain without ending the round; coverage
  and provenance are retained as history (F9 / C5 preserved).

## 4. Properties

| # | Property | Result | Why (structural) |
|---|----------|--------|------------------|
| P1 | Recovery coexists with live candidates | PASS | §0.6/§2.5: `SECURITY_RECOVERY` may hold a non-empty `active_propagation_set`; entering it cancels nothing |
| P2 | A valid candidate closes a recovery-state round | PASS | `ValidBlockAccept` precondition allows `SECURITY_RECOVERY`; round SM R6 gives `SECURITY_RECOVERY -> ROUND_ACCEPTED` |
| P3 | RoundInitialise / RoundAbort init & clear registries | PASS | `RoundInitialise` sets the five registries/counters; `RoundAbort` clears `active_propagation_set` and `acceptance_batch_registry` |
| P4 | Abort dispositions every live context and clears registries | PASS | `RoundAbort` sets each CPC `CANCELLED`, cancels its events, clears both registries — no stale candidate/batch survives |
| P5 | Template refresh clears old-template contexts/batches/hash/propagation events without touching history | PASS | `CloseTemplateAssignments` cancels old-`TemplateID` contexts, events, hash events, and batch entries while preserving all historical records (F9) |
| P6 | Acceptance clears the set and closes exactly once | PASS | `ValidBlockAccept` clears `active_propagation_set`, single `ROUND_ACCEPTED` transition, `block_accepted` guard |

## 5. Result

**CANDIDATE-CLEANUP & RECOVERY-COEXISTENCE AUDIT (G8): PASS**

Exercised by test vectors **TV46**, **TV47**, and **TV50**.
