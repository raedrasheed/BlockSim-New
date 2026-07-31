# Stage 1C — Semantic Test Vectors (paper execution)

Documentation-level test vectors traced through the corrected pseudocode
(`STAGE_01_PROTOCOL_PSEUDOCODE.md`) and miner state machine. Each shows: initial states →
events → state transitions → coverage changes → custody changes → energy terms → hash-rate
effect → round outcome → invariants exercised. All are paper executions of the modeled
abstraction, not proofs.

Legend: coverage layers `actual` / `reported` / `accepted`; `af` = accepted_frontier; range
`[s,e]`. Only `ACTIVE_HASHING` contributes to `H_active`.

## TV1 — Honest full range exhaustion
- **Initial:** miner M `ACTIVE_HASHING`, assignment `[s,e]`, honest mode.
- **Events:** cursor reaches `e`, no hit; `RangeExhaust`.
- **Transitions:** adjudication ACCEPTED (honest ground-truth) → `ACTIVE_HASHING → EXHAUSTED_PENDING` (T7, `RANGE_EXHAUSTED`) → `EnterLowPowerListen(RANGE_EXHAUSTED)` → `EXHAUSTED_PENDING → LOW_POWER_LISTEN` (T8).
- **Coverage:** `accepted_searched = [s,e]`; `active_unsearched = ∅`.
- **Custody:** `completed`.
- **Energy:** `t_hash` for the full sweep; short `P_hash` `EXHAUSTED_PENDING` transient; then `P_listen`; one-shot `E_transition`/`E_coordination`.
- **Hash-rate:** M removed from `H_active` at T7.
- **Round:** contributes accepted coverage toward `ROUND_EXHAUSTED`.
- **Invariants:** I4, I8a (accepted), I5/I6, I2 (n/a: no solution).

## TV2 — False exhaustion, audited and rejected
- **Initial:** adversarial M `ACTIVE_HASHING`; `actual_frontier < e` but reports `reported_exhaustion=true`.
- **Events:** `RangeExhaust`; `[SIMULATION SAMPLING] audit_selected = true`; `audit_result = inconsistent`.
- **Transitions:** `claim_accepted_or_rejected = REJECTED` → **no** transition; M stays `ACTIVE_HASHING`.
- **Coverage:** unchanged — `accepted_searched` NOT advanced; range NOT `searched`.
- **Custody:** unchanged (NOT `completed`).
- **Energy:** `t_hash` continues.
- **Hash-rate:** M remains in `H_active`.
- **Round:** `false_exhaustion_detected` recorded (progress/audit model, **not** I11); adversarial response applied.
- **Invariants:** I8a (accepted only), C2 order, I16 (breach/record retained).

## TV3 — False exhaustion, unaudited under the explicitly modeled policy
- **Initial:** adversarial M; `reported_exhaustion=true`; audit not selected.
- **Events:** `RangeExhaust`; `audit_selected=false`; `claim_accepted_or_rejected = modeled_unaudited_acceptance_policy(...)`.
- **Transitions:** if policy = ACCEPTED → T7/T8 as TV1 but flagged **modeled acceptance** (not actual proof); if policy = REJECTED → as TV2.
- **Coverage/custody:** on modeled acceptance, `accepted_searched=[s,e]`, `completed` — recorded as *modeled acceptance*.
- **Round:** contributes to `ROUND_EXHAUSTED` only via **accepted** coverage; recorded as modeled, not proven.
- **Invariants:** I8a, C9 (defined adjudication outcome), C2.

## TV4 — Verified solution certificate → accepted full block
- **Initial:** finder F finds hit; recipients R1,R2 `ACTIVE_HASHING`.
- **Events:** `EarlyStopGenerate` → `ScheduleSolutionPropagation` (schedules `CertificateArrival(R1),(R2)` and `BlockAcceptancePoint`); F ceases via `EnterLowPowerListen(VALID_SOLUTION_VERIFIED)`, assignment PAUSED. `CertificateArrival` → `EarlyStopVerify` passes → R1,R2 `ACTIVE_HASHING → LOW_POWER_LISTEN` (T26, PAUSED). `BlockAcceptancePoint` → `ValidBlockAccept` (earliest arrival) → `ROUND_ACCEPTED`.
- **Coverage:** none marked `searched` (all PAUSED, retain `actual_frontier`/`accepted_frontier`).
- **Custody:** unchanged (no `completed`).
- **Energy:** F/R: `t_hash` up to pause; `E_verification` (recipients, on top of `t_hash`, not double-counted); block-propagation `E_coordination`.
- **Hash-rate:** F removed at pause; R1,R2 removed only after their verification passes.
- **Round:** `ROUND_ACCEPTED`; remaining assignments closed with `stop_reason=ROUND_ACCEPTED` (not exhausted).
- **Invariants:** I2, I3, I11, I4, I6 (E_verification separate), CR-B1 (PATH B never via `EXHAUSTED_PENDING`).

## TV5 — Verified certificate → rejected full block → resume
- **Initial:** as TV4 up to R1 PAUSED (`VALID_SOLUTION_VERIFIED`).
- **Events:** full block `BLOCK_REJECTED`/timeout → `ResumeFromPause(R1)`.
- **Transitions:** `LOW_POWER_LISTEN → WAKING → ACTIVE_HASHING` (T30→T5); resume from retained `actual_frontier`.
- **Coverage:** never falsely credited (was PAUSED, not `searched`); resumes exactly.
- **Custody:** unchanged.
- **Energy:** `t_listen` during pause; `t_wake` + `E_transition` on resume; `t_hash` continues.
- **Hash-rate:** R1 re-enters `H_active` on `ACTIVE_HASHING`.
- **Round:** continues (`HASHING`).
- **Invariants:** CR-B1 (resume exclusive to PATH B), I5/I6.

## TV6 — Invalid certificate → no state change
- **Initial:** R `ACTIVE_HASHING`; receives certificate failing a validation step (e.g. bad signature or nonce ∉ range).
- **Events:** `CertificateArrival` → `EarlyStopVerify` → one of step1..step6 FALSE.
- **Transitions:** **none** — R stays `ACTIVE_HASHING`, keeps hashing.
- **Coverage/custody/energy:** unchanged except `E_verification` for the check; `t_hash` continues.
- **Hash-rate:** R remains in `H_active`.
- **Round:** `false_early_stop_rejected` recorded.
- **Invariants:** **I11** (no stop without full validation), CR-B2.

## TV7 — Lease expiry after a partially accepted searched prefix
- **Initial:** M `ACTIVE_HASHING`, range `[s,e]`, `af = p` with `s ≤ p < e`; lease expires, no renewal.
- **Events:** `LeaseExpiry` → `suffix = [p+1, e]` reassignable → `RangeReassign(suffix, reason=lease_expiry)`.
- **Coverage:** prefix `[s,p]` stays `accepted_searched`; `[p+1,e]` → `inactive_unsearched` then reassigned as a new assignment (`active_unsearched`).
- **Custody:** suffix → `reassigned`; prefix unaffected.
- **Energy:** M's `t_hash` for `[s,p]` retained.
- **Round:** continues; coverage partition preserved (I8a).
- **Invariants:** **C4** (suffix only), I8a (accepted), I9 (provenance), I1 (disjoint).

## TV8 — Template refresh after full-domain exhaustion
- **Initial:** `ROUND_EXHAUSTED` (all accepted searched; TV1×N); policy = continue.
- **Events:** `TemplateRefresh` → close all old-`TemplateID` assignments; preserve history; new template + fresh `TemplateID`; create new **original** assignments (`previous_assignment_reference=null`).
- **Coverage:** new domain starts `active_unsearched`; old completed coverage preserved in history.
- **Custody:** new = `original`; old completed ranges NOT reassigned/rebound.
- **Energy:** new round accrual begins.
- **Round:** new search domain under fixed difficulty (I12).
- **Invariants:** **C5**, I12, I8b (custody), I8a.

## TV9 — Zero active hash rate
- **Initial:** all miners in `LOW_POWER_LISTEN`/`RESERVE`/`WAKING`/`OFFLINE`; none `ACTIVE_HASHING`.
- **Events:** `ActiveHashRateUpdate(t)` → `H_active=0`, `q_adv=NA` (compute only, no breach). `SecurityFloorEvaluate` → record active-floor + honest-floor breaches; **no** NA comparison; trigger `SECURITY_RECOVERY`.
- **Coverage/custody:** unchanged.
- **Hash-rate:** `H_active=H_honest=H_adversarial=0`; `q_adv=NA`.
- **Round:** `→ SECURITY_RECOVERY`; reserve activation may follow.
- **Invariants:** **I17** (identity; NA at zero), **C7** (single breach owner; NA never compared), I16 (recorded).

## TV10 — Two valid solutions, different arrival times
- **Events:** solutions Sa, Sb; `BlockAcceptancePoint(Sa)` fires before `BlockAcceptancePoint(Sb)` (queue order).
- **Transitions:** `ValidBlockAccept(Sa)` → accepted → `ROUND_ACCEPTED`; later `ValidBlockAccept(Sb)` → a block already accepted → `competing_valid(Sb)`.
- **Round:** Sa accepted; Sb stale/competing; remaining assignments closed `ROUND_ACCEPTED`.
- **Invariants:** **C6** (queue-order earliest; no global future set), I2/I3.

## TV11 — Two valid solutions, exactly equal arrival times
- **Events:** `BlockAcceptancePoint(Sa)` and `BlockAcceptancePoint(Sb)` at the EXACT same acceptance timestamp.
- **Transitions:** deterministic secondary tie-break — keep smaller `candidate_hash`, then smaller `MinerID`; the other → `competing_valid`.
- **Round:** one accepted, one competing.
- **Invariants:** **C6** (tie-break only on exact-equal timestamps), determinism.

## TV12 — Completed range offered for reassignment → rejected
- **Initial:** range `[s,e]` `coverage_state=searched`, `custody_status=completed`.
- **Events:** something calls `RangeReassign([s,e], reason=…)`.
- **Transitions:** precondition `custody_status != completed` FAILS and `coverage_state != searched` FAILS → **ASSERT fails; reassignment rejected**. No new assignment created.
- **Coverage/custody:** unchanged (`searched`/`completed`).
- **Round:** unaffected.
- **Invariants:** **C5/CR-B5** (completed never reassignable), C4 (suffix only), I8a.

## Result
All 12 vectors execute consistently against the corrected procedures with no state-path,
coverage, custody, energy, or hash-rate contradiction. The valid-solution path (PATH B) and
the exhaustion path (PATH A) never merge; accepted coverage governs I8a and `ROUND_EXHAUSTED`;
acceptance occurs only at the modeled acceptance point; completed ranges are never reassigned;
`q_adv=NA` is never compared; I17 holds exactly.
