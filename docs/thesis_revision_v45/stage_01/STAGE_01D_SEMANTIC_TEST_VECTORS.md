# Stage 1D — Semantic Test Vectors (authoritative; named-procedure execution)

The 12 Stage-1C vectors, corrected to name the exact pseudocode procedure causing every
transition, plus TV13–TV17. No vector assumes an unmodeled external action; every transition is
caused by a named procedure in `STAGE_01_PROTOCOL_PSEUDOCODE.md`. This file supersedes
`STAGE_01C_SEMANTIC_TEST_VECTORS.md` for executable-procedure conformance.

Transition IDs (T*) refer to the miner state machine; procedures are UpperCamelCase.

## TV1 — Honest full range exhaustion
`ActiveHashing` (cursor beyond range) → `ActualRangeCompletion` (ground truth: actual_frontier=range_end) → `ReportedExhaustionClaim` (reported_*) → `ExhaustionAdjudicate` (honest, ACCEPTED): sets accepted_frontier=range_end, accepted_searched=full, coverage=searched, custody=completed, `stop_reason=RANGE_EXHAUSTED`, **T7** ACTIVE_HASHING→EXHAUSTED_PENDING → `EnterLowPowerListen(RANGE_EXHAUSTED)` **T8** →LOW_POWER_LISTEN. Energy: t_hash sweep, P_hash transient, then P_listen. Hash-rate: removed at T7. Invariants: I4, I8a(accepted), I5/I6.

## TV2 — False exhaustion, audited and rejected
`ReportedExhaustionClaim` callable with actual_frontier<range_end (reported_exhaustion=true) → `ExhaustionAdjudicate` (adversarial; `[SIMULATION SAMPLING] audit_selection_model`=selected; compare inconsistent → REJECTED): **no transition**, records false_exhaustion_detected (progress/audit, not I11), accepted coverage preserved, miner stays ACTIVE_HASHING. Invariants: I8a, C2 order, I16.

## TV3 — False exhaustion, unaudited under the modeled policy
`ReportedExhaustionClaim` → `ExhaustionAdjudicate` (adversarial; audit not selected; `modeled_unaudited_acceptance_policy`): if policy=ACCEPTED, promote to accepted coverage + T7/T8 as TV1 but flagged **modeled acceptance** (not proof); if policy=REJECTED, as TV2. Invariants: I8a, C9 (defined adjudication outcome).

## TV4 — Verified certificate → accepted full block
`ActiveHashing` (hit) → `EarlyStopGenerate` → `ScheduleSolutionPropagation`: `SelfValidateFoundSolution(finder)` passes (D4) → `EnterLowPowerListen(finder, VALID_SOLUTION_VERIFIED)` (**T26** direct →LOW_POWER_LISTEN, PAUSED); schedules `CertificateArrival(r)` and `BlockAcceptancePoint(ACCEPTED_CANDIDATE)`. `CertificateArrival(r)` → `EarlyStopVerify(r)` passes → **T26** r →LOW_POWER_LISTEN (PAUSED). `BlockAcceptancePoint(ACCEPTED_CANDIDATE)` → `AcceptanceTimestampBatch` → `ValidateCandidate` → `ValidBlockAccept` → ROUND_ACCEPTED → `CloseRoundAssignments(ROUND_ACCEPTED)`. Energy: t_hash to pause, E_verification (finder self + recipients), block-propagation E_coordination. Invariants: I2, I3, I11 (self+recipient validation), I4, I6.

## TV5 — Verified certificate → rejected full block → resume
As TV4 to recipient PAUSED. `BlockAcceptancePoint(REJECTED)` (D5): `SecurityFloorEvaluate` (no breach) → ensure HASHING; FOR EACH paused VALID_SOLUTION_VERIFIED miner M, `SCHEDULE ResumeFromPause(M, trigger=BLOCK_REJECTED)`. `ResumeFromPause(M)`: **T30** LOW_POWER_LISTEN→WAKING, `[SIMULATION SAMPLING] wake_latency_model`, t_wake+E_transition, restore assignment CURRENT from actual_frontier, **T5** →ACTIVE_HASHING, `ActiveHashRateUpdate`. Every transition is caused by a named procedure. Invariants: CR-B1, I5/I6, I17.

## TV6 — Invalid certificate → no state change
`CertificateArrival(r)` → `EarlyStopVerify(r)`: some stepK FALSE → **no transition**; r stays ACTIVE_HASHING; records false_early_stop_rejected; E_verification charged. Invariants: I11, CR-B2.

## TV7 — Lease expiry after a partially accepted searched prefix
`LeaseExpiry` (af=p, s≤p<e): suffix=[p+1,e] → `RangeReassign([p+1,e], reason=lease_expiry)` → creates PENDING for to_miner → **T4/T3** to_miner→WAKING → `WakeComplete` **T5** →ACTIVE_HASHING. Prefix [s,p] stays accepted_searched; suffix custody=reassigned. Invariants: C4, I8a(accepted), I9, I1, D2 (WAKING).

## TV8 — Template refresh after full-domain exhaustion
`FullRangeExhaustNoSolution` (accepted_searched=domain; no unsearched) → ROUND_EXHAUSTED → `TemplateRefresh`: TEMPLATE_REFRESH → close old (preserve history) → build template → **TEMPLATE_REFRESH→TEMPLATE_COMMITMENT** → `TemplateCommit` (→ASSIGNMENT) → create new ORIGINAL assignments (previous_assignment_reference=null); each miner →WAKING → `WakeComplete` →ACTIVE_HASHING. Invariants: C5, C9, D2, D8, I12.

## TV9 — Zero active hash rate
`ActiveHashRateUpdate(t)`: H_active=0, q_adv=NA, **records no breach** → `SecurityFloorEvaluate`: `RECORD_ONCE` active-floor + honest-floor breaches; **no NA comparison**; →SECURITY_RECOVERY. Invariants: I17 (identity; NA at zero), C7 (single breach owner; NA never compared), I16.

## TV10 — Two valid solutions, different arrival times
`BlockAcceptancePoint(Sa, ACCEPTED_CANDIDATE)` at ta < `BlockAcceptancePoint(Sb, ACCEPTED_CANDIDATE)` at tb (queue order). ta fires → `AcceptanceTimestampBatch(ta)` (batch={Sa}) → `ValidateCandidate(Sa)` → `ValidBlockAccept(Sa)` → ROUND_ACCEPTED → `CloseRoundAssignments`. Later tb → `AcceptanceTimestampBatch(tb)` → `ValidBlockAccept(Sb)`: block already accepted → competing_valid(Sb). Invariants: C6 (queue-order earliest), I2/I3.

## TV11 — Two valid solutions, exactly equal arrival times
`BlockAcceptancePoint(Sa)` and `BlockAcceptancePoint(Sb)` both at ta → `AcceptanceTimestampBatch(ta)` gathers batch={Sa,Sb} → `ValidateCandidate(Sa)`,`ValidateCandidate(Sb)` (both valid) → winner=argmin(candidate_hash, then MinerID) → competing_valid(other) → `ValidBlockAccept(winner)` → `CloseRoundAssignments`. Round closes ONLY after arbitration. Invariants: C6 (exact-tie rule), determinism.

## TV12 — Completed range offered for reassignment → rejected
`RangeReassign([s,e], …)` with custody_status=completed, coverage_state=searched → preconditions `custody != completed` and `coverage != searched` FAIL → ASSERT fails; reassignment rejected; no new assignment. Invariants: CR-B5/C5, C4, I8a.

## TV13 — REGISTERED assignment passes through WAKING
`RangeAssign` (miner REGISTERED): create PENDING; **T3** REGISTERED→WAKING; `WakeComplete`: wake_latency, t_wake+E_transition, validate I1/RoundID/TemplateID, activate PENDING→CURRENT, **T5** WAKING→ACTIVE_HASHING. No direct REGISTERED→ACTIVE_HASHING. Invariants: D2, I1, I5/I6.

## TV14 — RESERVE activation creates a PENDING assignment, passes through WAKING, and charges wake energy
`ReserveActivate` (miner RESERVE): SELECT reserve_miner; SELECT candidate_range (unsearched/reassignable, `custody_status != completed`, `coverage_state != searched`); overlap guard (I10/I1); **E4:** `CREATE assignment(reserve_miner, candidate_range, TemplateID, RoundID, lease_start, lease_expiry) WITH status = PENDING`; `APPEND assignment to assignment_ledger`; `SET custody_status(candidate_range) <- original`; **T4** RESERVE→WAKING → `WakeComplete`: `[SIMULATION SAMPLING] wake_latency_model`; ACCUMULATE t_wake at P_wake + E_transition; validate I1/RoundID/TemplateID; on success activate PENDING→CURRENT, **T5** →ACTIVE_HASHING. On wake failure: `WakeComplete` records `reserve_wake_failure`, miner → OFFLINE, and `ReserveActivate` releases the bound range (`inactive_unsearched`, `custody_status <- abandoned`) and returns `activation_failure` — no CURRENT assignment recorded. Invariants: E4, D2, I6, I10/I1 (no overlap). PENDING→CURRENT occurs ONLY on a successful wake.

## TV15 — ROUND_ABORTED closes all open assignments and cancels pending events
`RoundAbort` → `CloseRoundAssignments(ROUND_ABORTED, stop_reason=ROUND_ABORTED)`: enumerate ALL open assignments (ACTIVE_HASHING/EXHAUSTED_PENDING/LOW_POWER_LISTEN/WAKING/OFFLINE); ACTIVE holders → `EnterLowPowerListen(ROUND_ABORTED)`; others recorded closed round-ended; **cancel pending wake/resume/certificate-arrival/BlockAcceptancePoint events for RoundID**; finalise durations/energy. Ranges NOT marked exhausted; nothing reassigned under closed TemplateID. Invariants: D7, I5/I6/I7, I14/I15/I16.

## TV16 — TemplateRefresh transitions through TEMPLATE_COMMITMENT before TemplateCommit
`TemplateRefresh`: ROUND_EXHAUSTED/HASHING → TEMPLATE_REFRESH → close old + preserve history + build template → **TEMPLATE_REFRESH→TEMPLATE_COMMITMENT** → `TemplateCommit` (precondition round_state=TEMPLATE_COMMITMENT satisfied) → ASSIGNMENT → new ORIGINAL assignments, previous_assignment_reference=null; miners →WAKING→`WakeComplete`→ACTIVE_HASHING. `TemplateCommit` is NEVER called from TEMPLATE_REFRESH. Invariants: D8, C5, D2, I12.

## TV17 — Same-timestamp acceptance batch validates both candidates before closing
Two `BlockAcceptancePoint(ACCEPTED_CANDIDATE)` at identical ta → `AcceptanceTimestampBatch(ta)`: gather both; `ValidateCandidate` runs on BOTH before any acceptance; discard invalid; winner by candidate_hash then MinerID; competing_valid(other); ONLY THEN `ValidBlockAccept(winner)` → ROUND_ACCEPTED → `CloseRoundAssignments`. No round closure before arbitration completes; no event inspects future timestamps. Invariants: D6, C6.

## Result
All 17 vectors execute against named procedures with no state-path, coverage, custody, energy,
or hash-rate contradiction. Every transition is caused by a named pseudocode procedure; none
assumes an unmodeled external action.
