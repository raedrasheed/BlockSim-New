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
- **Invariants** `I1..I16` are defined in `STAGE_01_INVARIANT_CATALOGUE.md`.
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
| 1 | Miner disappears while hashing | Progress-commitment / lease heartbeat timeout while in `ACTIVE_HASHING`; no commitment within the expected interval | Mark miner `OFFLINE`; treat its lease as expired; flag range remainder as unsearched (I8); range reassignment with provenance (I9); enter `SECURITY_RECOVERY` if floor at risk | Its `t_hash,i` truncated at departure; remaining active power-time for the range shifts to the reassignee; totals reconcile via I5–I7; no double credit (I13) | Temporary coverage loss over its range until reassignment; measured against active-hash-rate floor | `miner_departure_hashing`; range flagged `reassigned` | continue (abort if floor unrecoverable) |
| 2 | Miner disappears while listening | Listen-state liveness timeout in `LOW_POWER_LISTEN`; missing keep-alive | Mark miner `OFFLINE`; it holds no active range, so no active-work reassignment; promote `RESERVE` only if floor at risk | `t_listen,i` truncated; negligible active power-time change; small coordination term | None directly — listening never contributed to active honest hash rate; floor unaffected by its exit | `miner_departure_listening` | continue |
| 3 | Reserve fails to wake | `WAKING` deadline exceeded without transition to `ACTIVE_HASHING`; wake-latency budget overrun | Abort this promotion; move miner to `OFFLINE`/`DISQUALIFIED` per policy; promote an alternate `RESERVE` with overlap guard (I10); if none and floor breached, stay in `SECURITY_RECOVERY` | `P_wake,i · t_wake,i` spent without productive hashing (sunk); logged under `E_transition,i`/`E_coordination,i` | Intended floor top-up not realised; floor may remain breached | `reserve_wake_failure` | continue (abort if floor unrecoverable and no reserve) |
| 4 | Miner hashes outside its range | Submitted solution/progress nonce not in signer's valid current assignment (violates I2); assignment-membership check | Reject the out-of-range work; do NOT accept the solution; flag miner, `DISQUALIFIED` per policy; round acceptance unaffected | Offending miner's active power-time is uncredited toward coverage; charged to its `E_i`, not to legitimate coverage | Attempted coverage manipulation / double-search; rejection preserves acceptance integrity; breach recorded | `out_of_range_work`; assignment-violation flag | continue |
| 5 | Miner claims false exhaustion | Progress commitment inconsistent with claimed exhaustion under the modeled progress-verification abstraction; range accounting mismatch (I8) | Do not accept the claim as complete; retain range remainder as unsearched; flag miner; reassign remainder to preserve coverage (I9) | If believed it would have idled coverage prematurely; retaining the remainder preserves/reassigns the needed active power-time | Attempt to shrink the searched domain; caught by accounting; recorded | `false_exhaustion_claim` | continue |
| 6 | Miner withholds progress | Missing progress commitment within interval while `ACTIVE_HASHING` or holding a lease | Treat progress beyond last commitment as unverified/unsearched; reclaim lease on expiry; reassign (I8/I9) | Its active power-time may be uncredited toward coverage; reassignment may re-pay for the remainder (paid, never double-counted — I13) | Cannot fabricate covered progress; conservative treatment keeps coverage sound; recorded | `progress_withheld` | continue |
| 7 | Miner withholds a solution | Not directly detectable at Stage 1 (no proof-of-possession); inferred only via round timeout, eventual exhaustion, or another miner's solution | Round proceeds as if unsolved; normal disposition on later solution or exhaustion; withholder gains no acceptance; classified `SPECIFIED_FOR_LATER_TEST` in the threat model | Honest miners keep spending active power-time longer than an ideal early stop; realised ΔE reduced; accounted normally | Liveness/fairness concern; unresolved at Stage 1; recorded only when observable | `solution_withheld` (when observable) / undetected otherwise | continue (until solution or exhaustion) |
| 8 | Conflicting valid solutions | More than one solution satisfying the target for the committed `TemplateID`/`RoundID` arrives (I3), each in its signer's range (I2) | Apply the deterministic tie-break (see Open Questions default: smallest `(TemplateID, nonce, MinerID)`); accept one block; record the others as `competing_valid`; proceed `SOLUTION_PROPAGATION` → `ROUND_ACCEPTED` | Minor extra propagation/coordination energy; active hashing stops on acceptance | Fork-choice/selection concern flagged; selection deterministic in spec, soundness out of scope | `conflicting_valid_solutions`; accepted + competing recorded | continue → accepted |
| 9 | False early-stop certificate | Early-stop verification fails against target verification (I11); certificate contents inconsistent with retained progress commitments | Reject the certificate; do NOT terminate hashing (I11 forbids termination without target verification); flag issuer | Prevents premature idling; active power-time preserved | Attempt to halt honest hashing; blocked by I11; recorded | `false_early_stop_rejected` | continue |
| 10 | Delayed certificate | Certificate timestamp/round-phase check shows a valid early-stop or solution certificate arriving after its deadline or after disposition | If the round is still open and the certificate valid, honour it; if the round is already dispositioned, record but do NOT retroactively apply; never roll back an accepted block | Possible extra active power-time spent during the delay | Timing/latency concern; no acceptance-integrity loss; recorded | `delayed_certificate` | continue (inconclusive if it arrives post-disposition — no retroactive effect) |
| 11 | Template disagreement | `TemplateID` mismatch between submitted work and the committed template (I3); commitment cross-check in `TEMPLATE_COMMITMENT` | Reject work referencing a non-current `TemplateID`; if disagreement is systemic, run `TEMPLATE_REFRESH` to re-commit one template and rebind assignments to the new `TemplateID` | Work on the wrong template is wasted active power-time (uncredited); refresh incurs coordination energy | Template-grinding / split-work concern; contained by `TemplateID` binding; recorded | `template_disagreement` | refresh (continue if isolated and simply rejected) |
| 12 | Coordinator failure | Coordinator liveness timeout; assignment/commitment services missing | Round coordination cannot progress; enter `SECURITY_RECOVERY`; recover via standby coordination or re-initialise, else `ROUND_ABORTED`; never accept a block lacking a valid commitment | Miners may idle in `LOW_POWER_LISTEN` pending recovery → active power-time paused; wake energy on resume | Availability concern; adversarial-coordinator soundness out of scope (see threat model); recorded | `coordinator_failure` | continue after recovery (abort if unrecoverable) |
| 13 | Range-assignment conflict | Overlap detected between two assignments (violates I1); `ASSIGNMENT`-phase validation | Reject/rescind the conflicting assignment before activation; retain at most one valid assignment; issue corrected disjoint ranges via reassignment (I9) | Prevents duplicate active power-time on the same range (supports I13); minor coordination cost | Prevents overlap ambiguity and double counting; recorded | `assignment_conflict` | continue |
| 14 | Lease expiry | Lease clock reaches `lease_expiry` while the range is unsearched or not renewed | Reclaim the lease; return the range to the pool; renew to the same miner or reassign with full provenance (I8/I9); holder must stop treating it as a valid assignment | Normal operating event enabling coverage without continuous full participation; reassignment coordination cost | None if provenance complete; stale-lease mining would be out-of-range (I2) and rejected; recorded | `lease_expiry` | continue |
| 15 | All ranges exhausted without a solution | Assignment accounting shows the entire nonce domain searched (I8) with no accepted block | Move round to `ROUND_EXHAUSTED`; then `TEMPLATE_REFRESH` (new `TemplateID`) to continue mining, or `ROUND_ABORTED` per policy | Full-horizon active power-time spent; zero-block outcome retained (I14); block-normalised metrics recorded `NA` (I15) | None — legitimate exhaustion; recorded | `full_exhaustion_no_solution` (zero-block, retained) | refresh (abort per policy) |
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

- **False early-stop vs. delayed certificate (rows 9, 10).** These are deliberately
  separated. A *false* certificate fails verification and is blocked by **I11** — hashing is
  never terminated without target verification. A *delayed* certificate may be perfectly
  valid; its only issue is timing. Neither may retroactively reverse a completed disposition,
  which is why a post-disposition delayed certificate is recorded `inconclusive`.

- **Exhaustion legitimacy (rows 5, 6, 15).** Rows 5 and 6 are adversarial/incomplete
  exhaustion evidence handled conservatively (remainder retained as unsearched). Row 15 is a
  *legitimate* full exhaustion reconciled by **I8** across the whole domain, producing a
  retained zero-block outcome (**I14**) with `NA` block-normalised metrics (**I15**).

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
