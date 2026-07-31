# Stage 1F — Correction Report (concurrency & event contract)

**Branch.** `thesis-v45-pocol-stage1f-concurrency-event-contract`
**Base.** `71396bbdea59e7884ea8259ccb234adb882acb45` (Stage 1E).
**Scope.** Documentation only — no executable source, configuration, DOCX, PDF, or experiment
changes. Protected DOCX drafts are byte-identical; Stage 1A–1E artifacts are frozen (F9).

**Naming rule (binding).** The algorithm is **PoCol**; the mechanism is **the idle policy within
PoCol**. The strings "PoCol-E", "Energy-Aware PoCol", "Enhanced PoCol" are prohibited and appear
only in prohibition clauses. No property (energy, security, fairness, incentive) is claimed; the
accepted baseline (A1) is unchanged; no new consensus feature is introduced — F1–F9 add concurrency
and discrete-event structure to the existing PoCol idle-policy specification.

This report enumerates the nine corrections F1–F9 with the defect, the fix, and the affected
artifact(s).

## F1 — Candidate-scoped propagation context

**Defect (1E).** Propagation state was effectively keyed by the round; concurrent candidates could be
conflated.
**Fix.** Added immutable unique `CandidateID`/`PropagationID` per candidate and a
`CandidatePropagationContext` (§0.8) with the required fields and a 9-status lifecycle
(`DISCOVERED → SELF_VALIDATED → PROPAGATING → PENDING_ACCEPTANCE → {ACCEPTED | FAILED}` plus
`COMPETING`/`STALE`/`CANCELLED`). `CreatePropagationContext` mints the ids; every
certificate-arrival, block-arrival, validation, timeout, cancellation, and resume event carries the
ids (§0.2). Contexts are never identified by `RoundID` alone.
**Artifacts.** pseudocode §0.8/§16b–§16e; `STAGE_01F_CANDIDATE_LIFECYCLE_SPEC.md`. TV28–TV30.

## F2 — Candidate-scoped pause and resume

**Defect (1E).** `HandlePropagationFailure` resumed every PATH-B paused miner and cancelled events by
certificate, not by candidate.
**Fix.** Pause records `pause_cause_candidate_id`/`pause_cause_propagation_id`/`paused_assignment_id`/
`retained_actual_frontier`. `HandlePropagationFailure(CandidateID)` resumes ONLY miners with a
matching pause cause and cancels ONLY that candidate's events; a miner paused by another live
candidate is untouched. Explicit multi-candidate policy: a miner verifies only while `ACTIVE_HASHING`,
so it has at most one pause cause.
**Artifacts.** pseudocode `EnterLowPowerListen`, `EarlyStopVerify`, `CertificateArrival`,
`HandlePropagationFailure`, `ResumeFromPause`; lifecycle spec §3. TV28/TV29.

## F3 — Active propagation set and round-state rule

**Defect (1E).** A single candidate's failure returned the round to HASHING unconditionally.
**Fix.** `active_propagation_set` holds every live context; the round is `SOLUTION_PROPAGATION` iff
non-empty. Failure removes only that candidate; `SOLUTION_PROPAGATION → HASHING` occurs only when
`propagation_quiescent` (§0.6). Acceptance marks all other live contexts COMPETING/STALE/CANCELLED,
cancels their events, and closes the round exactly once. Floor breach → SECURITY_RECOVERY preserving
live contexts.
**Artifacts.** pseudocode §0.6, `ScheduleSolutionPropagation`, `HandlePropagationFailure`,
`AcceptanceTimestampBatch`, `ValidBlockAccept`; round-SM §2.6/R6–R8. TV28/TV30/TV38.

## F4 — Correct reserve-activation provenance

**Defect (1E).** `ReserveActivate` always set `custody_status = original`, even for a reassignable
suffix.
**Fix.** Shared `CreatePendingAssignment(assignment_origin ∈ {ORIGINAL, RENEWED, REASSIGNED})` used by
`RangeAssign`, `ReserveActivate`, `RangeReassign`, `TemplateRefresh`. `ReserveActivate` selects
ORIGINAL for a fresh range and REASSIGNED (with source + reason + I9 provenance) for a prior
unsearched suffix.
**Artifacts.** pseudocode §0.11, `ReserveActivate`, `RangeReassign`, `RangeAssign`, `TemplateRefresh`;
`STAGE_01F_ASSIGNMENT_VERSION_AUDIT.md`. TV31/TV32.

## F5 — Event-scheduled wake

**Defect (1E).** `WakeComplete` executed the wake latency synchronously, serialising concurrent
miners.
**Fix.** `StartWake` (non-blocking) transitions to WAKING, draws the latency, schedules
`WakeCompleteEvent`, and returns immediately; `WakeCompleteEvent` activates (T5) or fails (T12) at
its own timestamp. All five activation callers use `StartWake`; the synchronous `WakeComplete` is
removed.
**Artifacts.** pseudocode §0.10, five callers; miner-SM §1.7/§2.6/T5; `STAGE_01F_WAKE_EVENT_AUDIT.md`.
TV33/TV37.

## F6 — Central miner-state transition hook

**Defect (1E).** Miner-state changes were scattered `TRANSITION miner_state` statements with
per-site energy/security handling.
**Fix.** `ApplyMinerStateTransition` is the sole writer of `miner_state`; it closes/opens residency,
charges transition energy, recomputes `H_active = H_honest + H_adversarial` (I17) at every
`ACTIVE_HASHING` boundary, sets `q_adv`/NA, schedules `SecurityFloorEvaluate`, and suppresses
duplicates. All 12 transition sites route through it (0 direct mutations). Its legality precondition
surfaced and fixed the illegal `WAKING → LOW_POWER_LISTEN` closure edge (now `WAKING → OFFLINE`, T12).
**Artifacts.** pseudocode §0.3/§0.9 + all transition sites; miner-SM §1.7; I17 note;
`STAGE_01F_STATE_TRANSITION_HOOK.md`. TV34/TV37.

## F7 — Atomic assignment renewal versioning

**Defect (1E).** Renewal mutated `AssignmentID`/`assignment_version` in place, which could invalidate
a discovery snapshot.
**Fix.** Immutable versioned `Assignment`; `RenewAssignment` atomically supersedes the old version
and publishes a new CURRENT version on the same range with copied frontiers/provenance. New invariant
**I18**: exactly one CURRENT version per lineage. Old versions stay resolvable, so a solution
discovered under an old version remains verifiable (E1).
**Artifacts.** pseudocode §0.8, `RenewAssignment`, `LeaseExpiry`, `ValidateCandidate`;
`STAGE_01_INVARIANT_CATALOGUE.md` I18; `STAGE_01F_ASSIGNMENT_VERSION_AUDIT.md`. TV35.

## F8 — Global event-priority contract

**Defect (1E).** Same-timestamp event ordering was implicit / potentially iteration-order-dependent.
**Fix.** A deterministic inter-type priority table (14 ranks) plus a `(CandidateID, MinerID,
AssignmentID, seq)` intra-type tie-break, resolving all six required races, independent of iteration
order and reproducible across reruns.
**Artifacts.** pseudocode §0.2/§0.7/§21; round-SM §2.6 note; `STAGE_01F_EVENT_PRIORITY_TABLE.md`.
TV36/TV37/TV38.

## F9 — Preserve historical stage artifacts

**Fix.** No `STAGE_01[A-E]_*` file is modified (verified by git delta); supersessions are recorded in
`STAGE_01F_HISTORICAL_ARTIFACT_REGISTER.md`, not by rewriting prior-stage evidence.

## F10 — Blocking test vectors

Added TV28–TV38 in `STAGE_01F_SEMANTIC_TEST_VECTORS.md`, each naming exact procedures and
preconditions.

## Summary of changed / added artifacts

| Artifact | Change |
|----------|--------|
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` | §0 model + §0.9–§0.11 hooks; F1–F8 threaded through all procedures; §21 priority |
| `STAGE_01_MINER_STATE_MACHINE.md` | §1.7 conventions; WAKING/T5 event-scheduling |
| `STAGE_01_ROUND_STATE_MACHINE.md` | §2.6 active-set rule; R6–R8; F8 note |
| `STAGE_01_INVARIANT_CATALOGUE.md` | I17 boundary note; new I18 |
| `STAGE_01_TRACEABILITY_MATRIX.csv` | R32–R38 |
| `STAGE_01F_*` (12 new deliverables) | this report + candidate lifecycle + concurrency/wake/hook/version audits + event-priority table + test vectors + call graph + historical register + cross-document audit + checksum manifest |

No executable source, configuration, DOCX, or PDF file is modified; no Stage 1A–1E artifact is
modified.
