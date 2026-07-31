# Stage 1G — Semantic Test Vectors (TV39–TV50)

Twelve blocking test vectors for the Stage-1G pre-implementation lock. Each names the exact
procedure(s) in `STAGE_01_PROTOCOL_PSEUDOCODE.md` and its exact preconditions; none assumes an
unmodeled external action. These extend TV1–TV38 (historical, in `STAGE_01C/D/E/F_*`, which are NOT
modified in Stage 1G). No property (energy, security, fairness) is claimed. Name remains **PoCol**;
mechanism is **the idle policy within PoCol**.

---

## TV39 — a solution discovered under v1 is accepted after the finder pauses and v1 is no longer CURRENT

**Preconditions.** Miner `F` `ACTIVE_HASHING` on assignment version `v1` (`CURRENT`); `HashWorkEvent`
hit under `v1` produces a `SolutionEligibilitySnapshot` binding `(AssignmentID(v1), version = v1)`; `F`
then pauses (PATH B), so `v1` becomes `PAUSED` (and may later be `SUPERSEDED` by a renewal to `v2`).

**Trace.** At the acceptance point `AcceptanceBatchFinalize → ValidateCandidate(certificate, snapshot)`
resolves the snapshot's `(AssignmentID(v1), v1)` to the IMMUTABLE `v1` and checks I2 (G1): `v1` was
VALID+`CURRENT` at `discovery_time`, not revoked before it, `nonce ∈ range(v1)`, RoundID/TemplateID/
target/signature bound. It does NOT require `v1` to be `CURRENT` now.

**Expected.** The solution is ACCEPTED via the immutable discovery snapshot even though `v1` is no
longer `CURRENT` (I2 corrected to discovery-time eligibility). Reqs: **G1**, I2, I18b, E1.

## TV40 — a lineage through PENDING, CURRENT, PAUSED, CURRENT, CLOSED upholds I18a/I18b at every point

**Preconditions.** A lineage `L` created via `CreatePendingAssignment(ORIGINAL)` (`PENDING`).

**Trace.** (1) `PENDING` — zero CURRENT in `L` (legal, I18a); one live head (I18b). (2)
`WakeCompleteEvent` T5 → `CURRENT` — one CURRENT (I18a); one live head. (3) `EnterLowPowerListen(
VALID_SOLUTION_VERIFIED)` → `PAUSED` — zero CURRENT (legal); one live head. (4) `ResumeFromPause →
WakeCompleteEvent` → `CURRENT` again — one CURRENT; one live head. (5) round closure →
`CloseRoundAssignments` closes `L` — zero CURRENT and zero live heads (CLOSED lineage).

**Expected.** `I18a` (`count(CURRENT) <= 1`) and `I18b` (one live head while open, zero after
closure) hold at every step; zero CURRENT is legal in the `PENDING`, `PAUSED`, and CLOSED points.
Reqs: **G2**, I18a, I18b.

## TV41 — an adversarial miner stops hashing only through the state hook; energy and I17 update at the exact time

**Preconditions.** Adversarial miner `A` is `ACTIVE_HASHING` at time `t`; the adversarial-participation
model schedules `AdversarialParticipationChangeEvent(A, exit)` at `t`.

**Trace.** `AdversarialParticipationChangeEvent(A, exit)`: `ApplyMinerStateTransition(A,
ACTIVE_HASHING, OFFLINE, t, reason = adversarial_withdrawal, …)` (T11) closes `A`'s `P_hash`
residency at `t`, opens `P_offline`, charges the transition energy, and recomputes
`H_active(t) = H_honest(t) + H_adversarial(t)` (I17) from the post-transition census. `ActiveHashRateUpdate`,
if it runs, only READS the census. `A` is never removed from `H_active` by a direct census edit.

**Expected.** The participation change is applied ONLY through the hook; energy and I17 update at the
exact event time `t`; `ActiveHashRateUpdate` never mutates the census. Reqs: **G3**, I17, I5/I6.

## TV42 — a PAUSED resume wake failure reassigns only the accepted unsearched suffix

**Preconditions.** Miner `M` is resuming a `PAUSED` assignment (`accepted_frontier = f`, `s ≤ f < e`)
via `ResumeFromPause → StartWake`; its `WakeCompleteEvent` fires past the wake deadline.

**Trace.** `WakeCompleteEvent` failure branch, `status(target) = PAUSED` (case B): `ApplyMinerStateTransition(
M, WAKING, OFFLINE, T12)`; PRESERVE `actual/reported/accepted` frontiers; `reassignable = [f+1, e]`
(suffix only; whole range only if no accepted position); mark it `inactive_unsearched`;
`custody_status ← abandoned`; close under `disposition = resume_wake_failed`; clear the candidate pause
fields; record resume-failure energy/provenance. It does NOT use the PENDING-only whole-range rule.

**Expected.** Only `[f+1, e]` becomes reassignable; the accepted prefix `[s,f]` is preserved; no
whole-range `inactive_unsearched`. Reqs: **G4**, I8a, I8b.

## TV43 — two same-timestamp full-block arrivals are collected before one atomic finalize and one closure

**Preconditions.** Candidates `X` and `Y` each have a `BlockAcceptancePoint(outcome =
ACCEPTED_CANDIDATE)` scheduled at the EXACT same `event_time` `t` for the same acceptance point.

**Trace.** Microphase 3: both `BlockAcceptancePoint` handlers only REGISTER into
`acceptance_batch_registry[(t, point)]` (each sets its context `PENDING_ACCEPTANCE`) and return; ONE
`AcceptanceBatchFinalize(t, point)` is scheduled. Microphase 4: `AcceptanceBatchFinalize` validates
both, selects the winner (`candidate_hash` then `MinerID`, G7), and `ValidBlockAccept` accepts +
closes the round EXACTLY ONCE (`block_accepted` guard), marking the loser COMPETING.

**Expected.** Both arrivals are collected before arbitration; exactly one arbitration and one
closure occur; no arrival accepts directly. Reqs: **G5**, D6, F3.

## TV44 — a same-timestamp security-floor event cannot reopen the round the acceptance batch closed

**Preconditions.** At `t`, a valid `AcceptanceBatchFinalize` and a scheduled `SecurityFloorEvaluate`
(from an earlier boundary carrying `state_version = k`) both exist.

**Trace.** Microphase 4 runs `AcceptanceBatchFinalize` → `ValidBlockAccept` → `ROUND_ACCEPTED`
(bumps `state_version` to `k+1`). Microphase 5 runs `SecurityFloorEvaluate(…, event_state_version =
k)`: its terminal/stale guard sees `round_state = ROUND_ACCEPTED` (and `k ≠ k+1`) and returns
`stale_noop` — no breach recorded, no transition.

**Expected.** Acceptance closure precedes the floor event (microphase order); the floor event
cannot transition the terminal round to `SECURITY_RECOVERY`. Reqs: **G5, G10**, I16.

## TV45 — identifiers and recipient scheduling are identical across reruns with the same seeds/inputs

**Preconditions.** Two runs with identical seeds and inputs; the same sequence of discoveries.

**Trace.** `CreatePropagationContext` mints `CandidateID = (RoundID, candidate_discovery_seq)` and
`PropagationID = (CandidateID, propagation_attempt_seq)` — deterministic (G7). `ScheduleSolutionPropagation`
iterates recipients in `SORT(... BY MinerID ascending)`; `seq` is assigned only after this order is
established. No step reads hash-map/set iteration order.

**Expected.** The `CandidateID`/`PropagationID` values and the recipient certificate-arrival
scheduling order are byte-identical across the two runs. Reqs: **G7**, F8.

## TV46 — a live candidate reaches acceptance while the round is SECURITY_RECOVERY and is not rejected for that

**Preconditions.** Round in `SECURITY_RECOVERY` (a floor breach fired while `active_propagation_set`
was non-empty; G8 preserved the contexts); candidate `Z` (`PENDING_ACCEPTANCE`) has a valid block.

**Trace.** `Z`'s `BlockAcceptancePoint` registers; `AcceptanceBatchFinalize → ValidBlockAccept(Z…)`:
precondition `round_state in {SOLUTION_PROPAGATION, SECURITY_RECOVERY}` holds and `Z`'s
RoundID/TemplateID are valid, so it accepts and transitions `SECURITY_RECOVERY → ROUND_ACCEPTED` (R6).

**Expected.** `Z` is accepted and closes the recovery-state round; it is not rejected merely because
the round was in `SECURITY_RECOVERY`. Reqs: **G8**, I2/I3.

## TV47 — RoundAbort with multiple live contexts cancels and dispositions all of them and clears the registries

**Preconditions.** Round in `SOLUTION_PROPAGATION`; `active_propagation_set = {A, B, C}`; a pending
acceptance batch may exist.

**Trace.** `RoundAbort`: `FOR EACH cpc in SORT(active_propagation_set BY CandidateID)` set
`status ← CANCELLED`, cancel its certificate-arrival + block-arrival events, remove from the set;
`CLEAR active_propagation_set`; `CLEAR acceptance_batch_registry`; `CloseRoundAssignments(ROUND_ABORTED)`
(cancels wake/resume/certificate/BlockAcceptancePoint/HashWorkEvent events); `→ ROUND_ABORTED`.

**Expected.** Every live context is CANCELLED with its events cancelled; both registries are cleared;
no stale candidate/batch survives the abort. Reqs: **G8**, D7.

## TV48 — two miners hash concurrently and a certificate arrival between their hash units is not delayed

**Preconditions.** Miners `M1`, `M2` each hashing via `HashWorkEvent` chains; a `CertificateArrival`
for `M2` is scheduled at a time between `M1`'s consecutive `HashWorkEvent`s.

**Trace.** Each `HashWorkEvent` evaluates ONE unit then `ScheduleNextHashWork` and returns to the
loop (G9). Because no `WHILE` loop blocks, the queue processes `M1.HashWorkEvent(k)`, then the
`CertificateArrival` at its scheduled time, then `M1.HashWorkEvent(k+1)` / `M2`'s units in timestamp
order.

**Expected.** The certificate arrival is processed in queue order, not delayed by a blocking hash
loop; miners hash through independently scheduled events. Reqs: **G9**, F5.

## TV49 — a resume event carries both ids and cannot resume a miner paused by another context

**Preconditions.** Miner `M` paused with `pause_cause_candidate_id = CID_A`,
`pause_cause_propagation_id = PID_A`. Candidate `B` (`CID_B`/`PID_B`) fails.

**Trace.** `HandlePropagationFailure(CID_B, PID_B, …)` iterates only miners with BOTH
`pause_cause_candidate_id = CID_B` AND `pause_cause_propagation_id = PID_B`; `M` (paused by `A`) is
NOT selected. When `A` fails, `HandlePropagationFailure(CID_A, PID_A, …)` schedules
`ResumeFromPause(M, …, CID_A, PID_A)`, whose precondition matches BOTH ids on `M`'s paused assignment.

**Expected.** A candidate's failure resumes only miners whose BOTH pause-cause ids match; `M` is
never resumed by `B`'s failure. Reqs: **G11**, F2.

## TV50 — template refresh clears old-template candidate contexts, batches, hash events, and propagation events without touching history

**Preconditions.** Round in `SOLUTION_PROPAGATION` under old `TemplateID_old` with live contexts and
scheduled events; a `TemplateRefresh` is triggered.

**Trace.** `TemplateRefresh → CloseTemplateAssignments(old_TemplateID)`: for each `cpc` with
`TemplateID(cpc) = old_TemplateID` set `status ← CANCELLED`, cancel its certificate-arrival +
block-arrival events, remove from the set; cancel all pending certificate-arrival / BlockAcceptancePoint
/ resume / `HashWorkEvent` events bound to `old_TemplateID`; clear the matching `acceptance_batch_registry`
entries. It PRESERVEs historical coverage/provenance and modifies NO Stage-1A–1F artifact.

**Expected.** All old-template candidate contexts, batch registries, hash events, and propagation
events are cleared; historical records are untouched; the refresh then commits the new template
(TEMPLATE_COMMITMENT) and reaches HASHING (E8). Reqs: **G8/G9**, C5, F9.

---

## Coverage summary

| Vector | Requirement(s) | Named procedure(s) |
|--------|----------------|--------------------|
| TV39 | G1, I2 | `ValidateCandidate`, `AcceptanceBatchFinalize`, snapshot |
| TV40 | G2, I18a/b | `CreatePendingAssignment`, `WakeCompleteEvent`, `EnterLowPowerListen`, `ResumeFromPause`, `RenewAssignment` |
| TV41 | G3, I17 | `AdversarialParticipationChangeEvent`, `ApplyMinerStateTransition`, `ActiveHashRateUpdate` |
| TV42 | G4 | `WakeCompleteEvent` (PAUSED failure) |
| TV43 | G5 | `BlockAcceptancePoint` (register), `AcceptanceBatchFinalize`, `ValidBlockAccept` |
| TV44 | G5, G10 | `AcceptanceBatchFinalize`, `SecurityFloorEvaluate` (terminal guard) |
| TV45 | G7 | `CreatePropagationContext`, `ScheduleSolutionPropagation` |
| TV46 | G8 | `ValidBlockAccept` (SECURITY_RECOVERY) |
| TV47 | G8 | `RoundAbort` |
| TV48 | G9 | `HashWorkEvent`, `ScheduleNextHashWork`, `CertificateArrival` |
| TV49 | G11 | `HandlePropagationFailure`, `ResumeFromPause` |
| TV50 | G8/G9, F9 | `TemplateRefresh`, `CloseTemplateAssignments` |

Every vector uses named procedures and exact preconditions; none assumes an unmodeled external
action; no property is claimed (Stage 1 specifies structure only).
