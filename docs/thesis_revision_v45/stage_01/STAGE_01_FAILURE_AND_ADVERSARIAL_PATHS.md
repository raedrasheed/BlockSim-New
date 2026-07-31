# Stage 1 — PoCol Failure and Adversarial Paths

**Document status:** Stage-1 specification-only. This document enumerates the failure and
adversarial paths of **PoCol** with **the idle policy within PoCol** enabled. It DEFINES how
each path is detected and dispositioned in the specified protocol. It does NOT claim that any
detection or response is implemented, validated, secure, fair, or incentive-compatible. At
Stage 1 no property in this document is experimentally supported.

Naming is binding: the algorithm is always **PoCol**; the low-power mechanism is always
**the idle policy within PoCol** (an operating policy inside PoCol, not a variant or fork).

---

## 1. Reading the failure table

Every path below is described against the canonical identifiers:

- **Miner states (8):** `REGISTERED`, `RESERVE`, `ACTIVE_HASHING`, `EXHAUSTED_PENDING`,
  `LOW_POWER_LISTEN`, `WAKING`, `OFFLINE`, `DISQUALIFIED`.
- **Round states (10):** `ROUND_INITIALISING`, `TEMPLATE_COMMITMENT`, `ASSIGNMENT`,
  `HASHING`, `SECURITY_RECOVERY`, `SOLUTION_PROPAGATION`, `ROUND_ACCEPTED`,
  `ROUND_EXHAUSTED`, `TEMPLATE_REFRESH`, `ROUND_ABORTED`.
- **Invariants** `I1..I19` are defined in `STAGE_01_INVARIANT_CATALOGUE.md`.
- **Adversarial share:** `q_adv(t) = H_adversarial(t) / (H_honest(t) + H_adversarial(t))`.
- **Progress evidence** is only a **modeled progress-verification abstraction**; it is NOT a
  cryptographic proof of range exhaustion.
- **Baseline A1:** continuous full-participation energy over the fixed 10,000 s horizon is
  8.420833333 kWh (141 TH/s, 21.5 J/TH, 3031.5 W). Partitioning ALONE changes no energy;
  every energy effect below is expressed as a change in **active power-time**
  (`Σ_i P_hash,i · t_hash,i`) plus the smaller listening / wake / transition / coordination
  terms of the energy model.

**`round_disposition` legend (exactly one per path):**

- **continue** — round remains in `HASHING`/`SECURITY_RECOVERY`; disposition unchanged.
- **refresh** — round moves through `TEMPLATE_REFRESH` to a new `TemplateID`.
- **abort** — round moves to `ROUND_ABORTED`.
- **inconclusive** — disposition cannot be determined until an external condition resolves
  (e.g. partition heal, late certificate); recorded as such, not forced.

Where a response depends on recoverability, the primary disposition is given first with the
escalation in parentheses.

---

## 2. Failure and adversarial path table

| # | scenario | detection | protocol_response | energy_effect | security_effect | recorded_outcome | round_disposition |
|---|---|---|---|---|---|---|---|
| 1 | Miner disappears while hashing | Progress-commitment / lease heartbeat timeout while in `ACTIVE_HASHING`; no commitment within the expected interval | Mark miner `OFFLINE`; treat its lease as expired; flag range remainder as `inactive_unsearched` (coverage; I8a); range reassignment with provenance (I9) and custody `reassigned` (I8b); enter `SECURITY_RECOVERY` if floor at risk | Its `t_hash,i` truncated at departure; remaining active power-time for the range shifts to the reassignee; totals reconcile via I5–I7; no double credit (I13) | Temporary coverage loss over its range until reassignment; measured against active-hash-rate floor | `miner_departure_hashing`; custody flagged `reassigned` (I8b) | continue (abort if floor unrecoverable) |
| 2 | Miner disappears while listening | Listen-state liveness timeout in `LOW_POWER_LISTEN`; missing keep-alive | Mark miner `OFFLINE`; it holds no active range, so no active-work reassignment; promote `RESERVE` only if floor at risk | `t_listen,i` truncated; negligible active power-time change; small coordination term | None directly — listening never contributed to active honest hash rate; floor unaffected by its exit | `miner_departure_listening` | continue |
| 3 | Reserve fails to wake | `WAKING` deadline exceeded without transition to `ACTIVE_HASHING`; wake-latency budget overrun | Abort this promotion; move miner to `OFFLINE`/`DISQUALIFIED` per policy; promote an alternate `RESERVE` with overlap guard (I10); if none and floor breached, stay in `SECURITY_RECOVERY` | `P_wake,i · t_wake,i` spent without productive hashing (sunk); logged under `E_transition,i`/`E_coordination,i` | Intended floor top-up not realised; floor may remain breached | `reserve_wake_failure` | continue (abort if floor unrecoverable and no reserve) |
| 4 | Miner hashes outside its range | Submitted solution/progress nonce not in signer's valid current assignment (violates I2); assignment-membership check | Reject the out-of-range work; do NOT accept the solution; flag miner, `DISQUALIFIED` per policy; round acceptance unaffected | Offending miner's active power-time is uncredited toward coverage; charged to its `E_i`, not to legitimate coverage | Attempted coverage manipulation / double-search; rejection preserves acceptance integrity; breach recorded | `out_of_range_work`; assignment-violation flag | continue |
| 5 | Miner claims false exhaustion | `reported_exhaustion` compared with simulator ground truth (`actual_frontier`/`actual_exhaustion`) through the modeled audit/detection abstraction; coverage-state mismatch (I8a). This is a modeled audit, never a target-verified or cryptographic proof of no solution in the range | Do not accept the claim as complete; the range is NOT closed (`custody_status` stays open, never `completed` on a rejected claim); retain range remainder as unsearched (I8a); flag miner; reassign only the unsearched suffix to preserve coverage, with custody `reassigned` (I8b) and provenance (I9) | If believed it would have idled coverage prematurely; retaining the remainder preserves/reassigns the needed active power-time | Attempt to shrink the searched domain; caught by the modeled audit against ground truth; recorded | `false_exhaustion_claim` | continue |
| 6 | Miner withholds progress | Missing progress commitment within interval while `ACTIVE_HASHING` or holding a lease | Treat progress beyond last commitment as unverified/unsearched; reclaim lease on expiry; reassign, updating coverage (I8a) with custody `reassigned` (I8b) and provenance (I9) | Its active power-time may be uncredited toward coverage; reassignment may re-pay for the remainder (paid, never double-counted — I13) | Cannot fabricate covered progress; conservative treatment keeps coverage sound; recorded | `progress_withheld` | continue |
| 7 | Miner withholds a solution | Not directly detectable at Stage 1 (no proof-of-possession); inferred only via round timeout, eventual exhaustion, or another miner's solution | Round proceeds as if unsolved; normal disposition on later solution or exhaustion; withholder gains no acceptance; classified `SPECIFIED_FOR_LATER_TEST` in the threat model | Honest miners keep spending active power-time longer than an ideal early stop; realised ΔE reduced; accounted normally | Liveness/fairness concern; unresolved at Stage 1; recorded only when observable | `solution_withheld` (when observable) / undetected otherwise | continue (until solution or exhaustion) |
| 8 | Conflicting valid solutions | More than one solution satisfying the target for the committed `TemplateID`/`RoundID` arrives (I3), each in its signer's range (I2) | Use event-ordered network-arrival semantics (C6): each valid solution's certificate/block propagation is event-scheduled with modeled per-recipient delays, so the **discrete-event queue** establishes a reproducible arrival order; each recipient **continues hashing while validating** and, only after validation passes, pauses via **PATH B** (`ACTIVE_HASHING → LOW_POWER_LISTEN` directly, `stop_reason = VALID_SOLUTION_VERIFIED`), assignment **PAUSED** (retained `actual_frontier` preserved, range NOT marked exhausted, no `EXHAUSTED_PENDING`); local acceptance at the **modeled acceptance point** takes the **earliest valid arrival** established by the discrete-event queue; only exactly-equal acceptance timestamps break deterministically by smallest `candidate_hash`, then smallest `MinerID`; accept one block; record the others as `competing`/`stale`; on acceptance remaining assignments close because the round ended (`stop_reason = ROUND_ACCEPTED`, not exhausted); proceed `SOLUTION_PROPAGATION` → `ROUND_ACCEPTED`. If the full block is later rejected, unavailable, or times out, paused miners wake and resume from their retained `actual_frontier` (`LOW_POWER_LISTEN → WAKING → ACTIVE_HASHING`) | Minor extra propagation/coordination energy; paused active power-time on the validated stop; wake and transition energy on resume if the block is rejected | Fork-choice/selection concern flagged; selection deterministic in spec, no chain-wide fork-choice proof claimed | `conflicting_valid_solutions`; accepted + competing/stale recorded; paused recipients `stop_reason = VALID_SOLUTION_VERIFIED` | continue → accepted |
| 9 | False early-stop certificate | Early-stop certificate fails I11 validation: current `RoundID`/`TemplateID`/`AssignmentID`/`MinerID`, `nonce` membership, recomputed `candidate_hash`, `target` satisfaction, or authentication/signature does not verify. I11 validation has NO dependency on progress commitments, coverage frontiers, or range exhaustion | Reject the certificate; the miner **stays in `ACTIVE_HASHING`** and does NOT transition (a failed or partially verified certificate causes no hashing-state transition; no `stop_reason` is recorded); flag issuer | Prevents premature idling; active power-time preserved | Attempt to halt honest hashing; blocked by I11; recorded | `false_early_stop_rejected` | continue |
| 10 | Delayed certificate | Certificate timestamp/round-phase check shows a valid early-stop or solution certificate arriving after its deadline or after disposition | If the round is still open and the certificate valid, honour it — the recipient pauses via **PATH B** (`stop_reason = VALID_SOLUTION_VERIFIED`, assignment PAUSED, retained `actual_frontier` preserved, range not exhausted); if the round is already dispositioned, record but do NOT retroactively apply; never roll back an accepted block | Possible extra active power-time spent during the delay | Timing/latency concern; no acceptance-integrity loss; recorded | `delayed_certificate` | continue (inconclusive if it arrives post-disposition — no retroactive effect) |
| 11 | Template disagreement | `TemplateID` mismatch between submitted work and the committed template (I3); commitment cross-check in `TEMPLATE_COMMITMENT` | Reject work referencing a non-current `TemplateID`; if disagreement is systemic, run `TEMPLATE_REFRESH` to re-commit one template and rebind assignments to the new `TemplateID` | Work on the wrong template is wasted active power-time (uncredited); refresh incurs coordination energy | Template-grinding / split-work concern; contained by `TemplateID` binding; recorded | `template_disagreement` | refresh (continue if isolated and simply rejected) |
| 12 | Coordinator failure | Coordinator liveness timeout; assignment/commitment services missing | Round coordination cannot progress; enter `SECURITY_RECOVERY`; recover via standby coordination or re-initialise, else `ROUND_ABORTED`; never accept a block lacking a valid commitment | Miners may idle in `LOW_POWER_LISTEN` pending recovery → active power-time paused; wake energy on resume | Availability concern; adversarial-coordinator soundness out of scope (see threat model); recorded | `coordinator_failure` | continue after recovery (abort if unrecoverable) |
| 13 | Range-assignment conflict | Overlap detected between two assignments (violates I1); `ASSIGNMENT`-phase validation | Reject/rescind the conflicting assignment before activation; retain at most one valid assignment; issue corrected disjoint ranges via reassignment (I9) | Prevents duplicate active power-time on the same range (supports I13); minor coordination cost | Prevents overlap ambiguity and double counting; recorded | `assignment_conflict` | continue |
| 14 | Lease expiry | Lease clock reaches `lease_expiry` while the range is unsearched or not renewed | Reclaim the lease; return the range to the pool; renew to the same miner (custody `renewed`, I8b) or reassign (custody `reassigned`, I8b) with full provenance (I9), reconciling coverage (I8a); holder must stop treating it as a valid assignment | Normal operating event enabling coverage without continuous full participation; reassignment coordination cost | None if provenance complete; stale-lease mining would be out-of-range (I2) and rejected; recorded | `lease_expiry` | continue |
| 15 | All ranges exhausted without a solution | Coverage-state accounting shows the entire nonce domain as **accepted** `searched` coverage (I8a) — reported coverage alone is insufficient — with no `active_unsearched`/`inactive_unsearched` remaining and no accepted block; each miner reached its own range end via **PATH A**, where exhaustion is adjudicated (accepted) **before** `coverage_state = searched` (C2) (`ACTIVE_HASHING → EXHAUSTED_PENDING → LOW_POWER_LISTEN`, `stop_reason = RANGE_EXHAUSTED`, `coverage_state = searched`, `custody_status = completed`) | Move round to `ROUND_EXHAUSTED` only once accepted full-domain coverage holds with no unsearched remaining (C9); completed ranges are **not** reassigned (exhaustion is not a reassignment reason); then `TEMPLATE_REFRESH` mints a **new** `TemplateID` with **new original** assignments (a new candidate-identity domain, not a reassignment of the completed old ranges) to continue mining, or `ROUND_ABORTED` per policy | Full-horizon active power-time spent; zero-block outcome retained (I14); block-normalised metrics recorded `NA` (I15) | None — legitimate exhaustion; recorded | `full_exhaustion_no_solution` (zero-block, retained); PATH A `stop_reason = RANGE_EXHAUSTED` | refresh (abort per policy) |
| 16 | Active hash rate below floor | Active-hash-rate update shows aggregate `ACTIVE_HASHING` rate below the modeled floor; security-floor evaluation | Enter `SECURITY_RECOVERY`; promote `RESERVE` and/or recall `LOW_POWER_LISTEN` via `WAKING` to restore the rate; record the breach — do NOT silently repair it in reported data (I16) | Recovery raises active power-time (wake + hash energy); realised ΔE reduced during recovery | Floor breach = modeled security-margin risk; recorded | `active_floor_breach` (recorded, I16) | continue (abort if unrecoverable) |
| 17 | Honest hash rate below floor | Modeled honest active rate `H_honest(t)` below the honest floor (distinct from total active rate); floor evaluation | Enter `SECURITY_RECOVERY`; restore honest participation (reserves/wake); if implied `q_adv(t)` exceeds threshold, escalate; record breach (I16) | Recovery active power-time increase | Honest-majority margin risk; recorded, not silently repaired | `honest_floor_breach` (recorded, I16) | continue (abort if unrecoverable) |
| 18 | Adversarial share above threshold | `q_adv(t) = H_adversarial(t)/(H_honest(t)+H_adversarial(t))` exceeds the modeled threshold | Enter `SECURITY_RECOVERY`; raise honest active rate (reserves/wake) to lower `q_adv(t)`; record breach (I16); acceptance still requires target verification (I11) | Honest active power-time increased to restore margin | Elevated adversarial fraction = modeled security risk; soundness out of scope; recorded | `adversarial_share_breach` (recorded, I16) | continue (abort if unrecoverable) |
| 19 | Network partition | Connectivity/quorum loss between coordinator and miners; commitment/propagation reachability failure | Partitioned side cannot form valid commitments or acceptances without quorum; enter `SECURITY_RECOVERY` or `ROUND_ABORTED`; on heal, reconcile against the single committed `TemplateID`/`RoundID`; never double-accept | Partitioned miners may idle in `LOW_POWER_LISTEN` → paused active power-time; wake energy on heal | Partition/availability plus possible conflicting progress; conflict resolution out of scope; recorded | `network_partition` | inconclusive (until heal) → continue / refresh / abort on reconciliation |

---

## 3. Coupled-invariant and disposition rationale (subtle paths)

- **Withheld solution (row 7).** Stage 1 does NOT assume a proof-of-possession; withholding
  is therefore not directly detectable. The specification does not claim to detect or punish
  it. Its only modeled effect is an *upward* pressure on honest active power-time (a smaller
  ΔE than an ideal early stop), which is accounted normally under the energy model.

- **Two-path separation and valid-solution stop (rows 8, 10).** A verified valid solution
  never marks a recipient's range exhausted. Recipients continue hashing while validating and,
  only after all validation steps pass, take **PATH B** (`ACTIVE_HASHING → LOW_POWER_LISTEN`
  directly, `stop_reason = VALID_SOLUTION_VERIFIED`), which **PAUSES** the assignment: the
  retained `actual_frontier` is preserved and no unsearched positions are credited as searched.
  PATH B never passes through `EXHAUSTED_PENDING`. If the full block is accepted, remaining
  assignments close because the round ended (`stop_reason = ROUND_ACCEPTED`), not because their
  ranges were exhausted. If the full block is rejected, unavailable, or times out, paused miners
  wake and resume from the retained `actual_frontier`
  (`LOW_POWER_LISTEN → WAKING → ACTIVE_HASHING`), with wake and transition energy fully
  accounted. `EXHAUSTED_PENDING` is reachable only via **PATH A** range exhaustion.

- **False early-stop vs. delayed certificate (rows 9, 10).** These are deliberately
  separated. A *false* certificate fails **I11** validation (current `RoundID`, `TemplateID`,
  `AssignmentID`, `MinerID`, `nonce` membership, recomputed `candidate_hash`, `target`
  satisfaction, authentication/signature) and causes **no** hashing-state transition — the
  miner stays in `ACTIVE_HASHING`; I11 validation has no dependency on progress commitments,
  coverage frontiers, or range exhaustion. A *delayed* certificate may be perfectly valid; its
  only issue is timing, and if honoured while the round is still open the recipient pauses via
  **PATH B** (`stop_reason = VALID_SOLUTION_VERIFIED`, assignment PAUSED). Neither may
  retroactively reverse a completed disposition, which is why a post-disposition delayed
  certificate is recorded `inconclusive`.

- **Exhaustion legitimacy (rows 5, 6, 15).** Rows 5 and 6 are adversarial/incomplete
  exhaustion evidence handled conservatively: `reported_exhaustion` is compared with simulator
  ground truth through the modeled progress/audit abstraction (never a target-verified or
  cryptographic proof of no solution), and only the unsearched suffix is retained/reassigned —
  the range is never closed as `completed` on a rejected claim. False-exhaustion detection
  belongs to this progress/audit abstraction and **not** to I11 — I11 governs only false
  *solution* certificates (row 9), and has no dependency on progress commitments, coverage
  frontiers, or range exhaustion. Exhaustion is adjudicated (accepted) **before**
  `coverage_state = searched`/`completed` is recorded (C2). Row 15 is a *legitimate* full
  exhaustion via **PATH A** (`stop_reason = RANGE_EXHAUSTED`, `coverage_state = searched`,
  `custody_status = completed`), reconciled by the **I8a** coverage-state partition across the
  whole domain; the round enters `ROUND_EXHAUSTED` only when the I8a ledger shows the entire
  assigned domain as **accepted** searched coverage with no `active_unsearched`/
  `inactive_unsearched` remaining (C9), producing a retained zero-block outcome (**I14**) with
  `NA` block-normalised metrics (**I15**). A `completed` range is not reassignable and
  exhaustion is never a reassignment reason; continuation is via a new `TemplateID` under
  `TEMPLATE_REFRESH`, not reassignment.

- **Floor family (rows 16, 17, 18).** Three distinct floors/thresholds are monitored: total
  active hash rate, honest active hash rate `H_honest(t)`, and adversarial share `q_adv(t)`.
  All three share the same disposition pattern — `SECURITY_RECOVERY` with reserve/wake
  restoration — and all three are subject to **I16**: the breach is recorded in the reported
  data and never silently repaired. Recovery actions are logged separately from the breach.

- **Overlap-preventing paths (rows 4, 13; reserve row 3).** Rows 4 and 13, together with
  reserve activation, are the operational front line for **I1**, **I2**, **I10**, and
  **I13**: no two valid active assignments overlap, every accepted solution lies in the
  signer's valid current assignment, reserve promotion never introduces overlap, and no
  shared physical execution is counted twice.

- **Coordinator and partition (rows 12, 19).** Both are availability paths whose *security*
  soundness (adversarial coordinator, partition-induced conflicting histories) is out of
  scope at Stage 1 and is classified accordingly in `STAGE_01_THREAT_MODEL.md`. Their idle
  cost is captured as paused active power-time plus wake energy on recovery.

No detection, response, or disposition above is asserted to be validated at Stage 1. This
document specifies the intended handling only.
