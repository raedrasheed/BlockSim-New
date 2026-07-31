# Stage 1E — Semantic Test Vectors (TV18–TV27)

Ten blocking test vectors for the Stage-1E pre-implementation contract. Each vector names the
exact procedure(s) in `STAGE_01_PROTOCOL_PSEUDOCODE.md` that cause every transition and states
its exact preconditions; no vector assumes an unmodeled external action. These extend TV1–TV17
(`STAGE_01D_SEMANTIC_TEST_VECTORS.md`); they do not supersede them.

**Naming rule (binding).** The algorithm is **PoCol**; the mechanism is **the idle policy within
PoCol**. No property (energy, security, fairness) is claimed — these vectors exercise structure.

---

## TV18 — a finder that has PAUSED still has a solution that validates against the discovery snapshot

**Preconditions.** Miner F is `ACTIVE_HASHING` with a CURRENT assignment `A` (version `v`,
range `[s,e]`); F finds a valid candidate at nonce `n ∈ [s,e]`.

**Trace.** `ActiveHashing` (hit): builds `candidate_solution`; `CreateSolutionEligibilitySnapshot`
captures an IMMUTABLE snapshot (`assignment_status_at_discovery = CURRENT`, `assignment_version = v`,
`range_start=s`, `range_end=e`, `discovery_time`, `candidate_hash`, `target`); `EarlyStopGenerate`
produces the SIGNED certificate bound to that snapshot (`snapshot_ref`); `SelfValidateFoundSolution
→ ValidateCandidate(certificate, snapshot)` passes; `ScheduleSolutionPropagation` performs
`HASHING → SOLUTION_PROPAGATION` (E6) and `EnterLowPowerListen(F, VALID_SOLUTION_VERIFIED)` — F
is now `LOW_POWER_LISTEN`, assignment PAUSED (`actual_frontier` retained), **A becomes PAUSED, not
searched**. Later, at the acceptance point, `ValidateCandidate(certificate, snapshot)` is invoked
again by `AcceptanceTimestampBatch`.

**Expected.** `ValidateCandidate` returns `ok` **even though A is now PAUSED**: it validates against
`snapshot` (E1), requiring only that the snapshot was CURRENT at discovery, the assignment was not
revoked before `discovery_time`, `s ≤ n ≤ e`, and the bound RoundID/TemplateID/target/signature
hold. Invariants: **E1**, I2, I3, I11.

## TV19 — a paused assignment is valid for its discovered solution but NOT for new hashing

**Preconditions.** After TV18, F is `LOW_POWER_LISTEN` with assignment `A` PAUSED
(`entry_stop_reason = VALID_SOLUTION_VERIFIED`).

**Trace.** (a) Solution path: `ValidateCandidate(certificate, snapshot)` for F's certificate → `ok`
(the paused state does not invalidate the already-discovered solution). (b) New-hashing path: any
attempt to score new nonces requires `ACTIVE_HASHING`; F is not `ACTIVE_HASHING`, so `ActiveHashing`
is not runnable for F. Re-entry to hashing is possible ONLY via `ResumeFromPause` → `WAKING` (T30) →
`ACTIVE_HASHING` (T5), which restores `A` to CURRENT.

**Expected.** The PAUSED assignment authenticates F's discovered solution but authorises no new
scored search until a legal `ResumeFromPause` restores CURRENT. There is no direct
`LOW_POWER_LISTEN → ACTIVE_HASHING`. Invariants: **E1**, I4, I5/I6 (wake energy on resume), D2.

## TV20 — signed-certificate self-validation succeeds; an unsigned candidate fails authentication

**Preconditions.** A valid found solution exists; two objects are considered: the SIGNED
`early_stop_certificate` from `EarlyStopGenerate`, and the raw `candidate_solution` (no
`signature/authentication` field in its schema).

**Trace.** `SelfValidateFoundSolution(RoundContext, certificate, snapshot) → ValidateCandidate`:
the last conjunct checks `certificate.signature/authentication valid for certificate.MinerID over
the signed fields` → passes. If instead the raw `candidate_solution` were passed where a certificate
is required, the authentication conjunct has no field to check and cannot be satisfied.

**Expected.** Self-validation is over the AUTHENTICATED certificate object (E2), never over an
unsigned candidate; the finder stops only after this passes (D4). Certificate GENERATION does not by
itself satisfy validation. Invariants: **E2**, D4, I11.

## TV21 — an empty valid batch resumes ALL paused miners through HandlePropagationFailure

**Preconditions.** Round in `SOLUTION_PROPAGATION`; one or more miners PAUSED with
`entry_stop_reason = VALID_SOLUTION_VERIFIED`; a `BlockAcceptancePoint(outcome = ACCEPTED_CANDIDATE)`
fires, but every batched candidate fails validation.

**Trace.** `BlockAcceptancePoint(ACCEPTED_CANDIDATE) → AcceptanceTimestampBatch`: for each event
`c`, `ValidateCandidate(c.certificate, c.snapshot)` fails ⇒ `valid` is empty ⇒
`HandlePropagationFailure(RoundContext, batch.first.certificate, batch.first.snapshot,
failure_reason = NO_VALID_CANDIDATE)`. `HandlePropagationFailure`: `SecurityFloorEvaluate`; if no
breach `SOLUTION_PROPAGATION → HASHING`; cancels obsolete `CertificateArrival`/`BlockAcceptancePoint`
events for the failed certificate; `FOR EACH` PAUSED `VALID_SOLUTION_VERIFIED` miner `M` `SCHEDULE
ResumeFromPause(M)`. `ResumeFromPause`: `WAKING` (T30) → restore CURRENT from `actual_frontier` →
`ACTIVE_HASHING` (T5) → `ActiveHashRateUpdate`.

**Expected.** No paused miner is stranded; the round returns to HASHING (or SECURITY_RECOVERY on a
breach) and no block is accepted. Invariants: **E3**, D5, I4, I5/I6, I17.

## TV22 — ReserveActivate creates and ledgers a PENDING assignment BEFORE WAKING

**Preconditions.** `round_state = SECURITY_RECOVERY` (or `ASSIGNMENT`); miner R in `RESERVE`; an
unsearched/reassignable `candidate_range` exists (`custody_status != completed`,
`coverage_state != searched`).

**Trace.** `ReserveActivate`: overlap guard (I10/I1); `CREATE assignment(R, candidate_range, …)
WITH status = PENDING`; `APPEND` to `assignment_ledger`; `custody_status(candidate_range) <-
original`; `RESERVE → WAKING` (T4); `WakeComplete`: on success activate `PENDING → CURRENT`, `WAKING
→ ACTIVE_HASHING` (T5). On wake failure: `reserve_wake_failure`, R → OFFLINE (T12), and
`ReserveActivate` releases the range (`inactive_unsearched`, `custody_status <- abandoned`),
returning `activation_failure` with **no CURRENT assignment recorded**.

**Expected.** A PENDING `Assignment` object exists and is ledgered before the wake; `PENDING →
CURRENT` occurs ONLY on a successful wake; a failed wake records no successful assignment.
Invariants: **E4**, D2, I1/I10, I6.

## TV23 — a changed-range reassignment CANNOT use the removed T6 shortcut

**Preconditions.** Miner M is `ACTIVE_HASHING` on range `[s,e]`; a DIFFERENT disjoint range
`[s',e']` is to be worked.

**Trace.** There is no `ACTIVE_HASHING → ACTIVE_HASHING` transition (T6 retired, E5). Acquiring
`[s',e']` is a reassignment: `RangeReassign` binds the (unsearched) range to a `to_miner`, whose
activation passes `to_miner → WAKING → ACTIVE_HASHING` (T3/T4/T9/T10 → T5). The only same-holder,
same-range operation is `LeaseExpiry` **renewal** — range unchanged, fresh
`AssignmentID`/`assignment_version`, status stays CURRENT, no wake cycle — which is NOT a state
transition.

**Expected.** No changed-range self-loop exists; a different range is always acquired through
`WAKING`; a changed-range replacement is never labelled a renewal. Invariants: **E5**, D2, I1.

## TV24 — SOLUTION_PROPAGATION allows unpaused miners to keep hashing (and to find more candidates)

**Preconditions.** Round moved `HASHING → SOLUTION_PROPAGATION` at the first found solution
(`ScheduleSolutionPropagation`, E6); miner G is `ACTIVE_HASHING` and has NOT verified any
certificate.

**Trace.** `ActiveHashing` precondition/`WHILE` admits `round_state ∈ {HASHING,
SOLUTION_PROPAGATION, SECURITY_RECOVERY}` (E6), so G keeps searching and stays in `H_active(t)`. If G
finds its own valid candidate, `ScheduleSolutionPropagation` runs again; its `IF round_state =
HASHING` transition is a no-op (already `SOLUTION_PROPAGATION`), and a further
`CertificateArrival`/`BlockAcceptancePoint` pair is scheduled. G pauses (PATH B) only when it itself
verifies a certificate via `CertificateArrival → EarlyStopVerify`.

**Expected.** Entry to `SOLUTION_PROPAGATION` is at propagation START, not after acceptance; unpaused
miners continue hashing; further candidates may be scheduled. Invariants: **E6**, CR2, I11, I17.

## TV25 — CloseRoundAssignments has a deterministic action for EVERY holder state

**Preconditions.** A round closes (`ValidBlockAccept` with `ROUND_ACCEPTED`, or `RoundAbort` with
`ROUND_ABORTED`) with open assignments held by miners spanning all eight states.

**Trace.** `CloseRoundAssignments(disposition, stop_reason)` records
`round_closure_disposition(X) <- disposition` SEPARATELY from `entry_stop_reason(holder)`, then
switches on holder state: `ACTIVE_HASHING` → `EnterLowPowerListen(disposition)` (its stop event);
`EXHAUSTED_PENDING` → close X, `→ LOW_POWER_LISTEN` (RANGE_EXHAUSTED preserved); `LOW_POWER_LISTEN`
→ close X, state unchanged (VALID_SOLUTION_VERIFIED / RANGE_EXHAUSTED / ASSIGNMENT_REVOKED
preserved, NOT overwritten); `WAKING` → cancel pending `WakeComplete`, close X, `→ LOW_POWER_LISTEN`;
`REGISTERED`/`RESERVE` → close any bound PENDING X, state unchanged; `OFFLINE`/`DISQUALIFIED` →
close X, state unchanged. Then cancel pending wake/resume/certificate/BlockAcceptancePoint events and
finalise durations/energy.

**Expected.** Every holder state has an explicit outcome (no "update state consistently"); a
prior `RANGE_EXHAUSTED` or `VALID_SOLUTION_VERIFIED` is never overwritten by closure; `RoundAbort`
and accepted-block closure use the same table. Invariants: **E7**, D7, I4, I5/I6/I7.

## TV26 — template refresh excludes OFFLINE/DISQUALIFIED and reaches HASHING explicitly

**Preconditions.** `round_state = ROUND_EXHAUSTED`; participants span REGISTERED, RESERVE,
LOW_POWER_LISTEN, WAKING, OFFLINE, DISQUALIFIED.

**Trace.** `TemplateRefresh`: `→ TEMPLATE_REFRESH`; `CloseTemplateAssignments(old_TemplateID)` routes
each old holder off the old template via a LEGAL edge (`ACTIVE_HASHING`→T27; `EXHAUSTED_PENDING`→T8;
`LOW_POWER_LISTEN` stays; `WAKING`→T12 OFFLINE), preserving history; build template; `→
TEMPLATE_COMMITMENT`; `TemplateCommit → ASSIGNMENT`; select `eligible = {m : state ∈ {REGISTERED,
RESERVE, LOW_POWER_LISTEN}}`; for each, CREATE fresh ORIGINAL PENDING and use the per-state legal edge
into `WAKING` (T3/T4/T10) → `WakeComplete` (T5); OFFLINE and DISQUALIFIED miners are NOT selected;
finally `ASSERT round_state = ASSIGNMENT` then `ASSIGNMENT → HASHING` (R4).

**Expected.** OFFLINE/DISQUALIFIED receive no assignment; every activation uses a legal miner-state
transition; `TEMPLATE_COMMITMENT` is never bypassed; the round reaches `HASHING` explicitly.
Invariants: **E8**, D8, C5, I1, I3, I12.

## TV27 — lease renewal preserves CURRENT; expiry without renewal invalidates and reassigns only the suffix

**Preconditions.** Miner H is `ACTIVE_HASHING` on range `[s,e]` with `accepted_frontier = f`
(`s ≤ f < e`); `t ≥ lease_expiry`.

**Trace.** `LeaseExpiry` DECIDES renewal BEFORE invalidating (E9). (a) **Renewal** (H continues,
policy allows): assert `custody_status != completed`; bump `assignment_version`; mint fresh
`AssignmentID` on the SAME range/holder; extend `lease_start`/`lease_expiry`; `custody_status <-
renewed`; PRESERVE range, `actual_frontier`, `accepted_frontier`, `reported_frontier`, provenance;
KEEP status CURRENT; H stays `ACTIVE_HASHING`, no WAKING, no `RangeReassign`. (b) **Expiry without
renewal**: INVALIDATE the assignment; `EnterLowPowerListen(H, ASSIGNMENT_REVOKED)` (T27);
`reassignable_suffix = [f+1, e]` marked `inactive_unsearched`; `RangeReassign(suffix,
reason=lease_expiry)` — the accepted searched prefix `[s,f]` is never reassigned.

**Expected.** Renewal yields a valid CURRENT assignment on the same range with retained
progress/provenance and no wake cycle; expiry-without-renewal invalidates and reassigns ONLY the
accepted unsearched suffix. Invariants: **E9**, C4, D2, I2, I8a/I8b.

---

## Coverage summary

| Vector | Correction | Named procedure(s) exercised |
|--------|-----------|------------------------------|
| TV18 | E1 | `ActiveHashing`, `CreateSolutionEligibilitySnapshot`, `EarlyStopGenerate`, `ValidateCandidate`, `AcceptanceTimestampBatch` |
| TV19 | E1 | `ResumeFromPause`, `ValidateCandidate`, `ActiveHashing` (not runnable while paused) |
| TV20 | E2 | `SelfValidateFoundSolution`, `ValidateCandidate`, `EarlyStopGenerate` |
| TV21 | E3 | `BlockAcceptancePoint`, `AcceptanceTimestampBatch`, `HandlePropagationFailure`, `ResumeFromPause` |
| TV22 | E4 | `ReserveActivate`, `WakeComplete` |
| TV23 | E5 | `RangeReassign`, `LeaseExpiry` (renewal), miner T-table (T6 retired) |
| TV24 | E6 | `ActiveHashing`, `ScheduleSolutionPropagation`, `CertificateArrival`/`EarlyStopVerify` |
| TV25 | E7 | `CloseRoundAssignments`, `ValidBlockAccept`, `RoundAbort` |
| TV26 | E8 | `TemplateRefresh`, `CloseTemplateAssignments`, `TemplateCommit`, `WakeComplete` |
| TV27 | E9 | `LeaseExpiry`, `EnterLowPowerListen`, `RangeReassign` |

Every vector uses named procedures and exact preconditions; no vector assumes an unmodeled external
action, and no property is claimed (Stage 1 specifies structure only).
