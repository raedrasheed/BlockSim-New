# Stage 1B — Final Semantic Correction Report

Correction-only, documentation-only stage. Branch
`thesis-v45-pocol-stage1b-final-semantic-corrections`, from Stage-1A commit
`9b9edc2633a00ab3cd3c1b5a11401cd8b3cba655`. No executable code, configuration, DOCX/PDF,
experiments, or protected-artifact changes. Algorithm name remains **PoCol**; mechanism is
only *the idle policy within PoCol*.

This report is the **single source of truth** for corrections B1–B9. Every affected document
uses the verbatim canonical rules below. The semantic backbone is the **two-path separation**
in B1.

---

## CANONICAL CORRECTED RULES (verbatim)

### Transition-reason enumeration (mandatory `stop_reason`)
`RANGE_EXHAUSTED`, `ASSIGNMENT_REVOKED`, `VALID_SOLUTION_VERIFIED`, `ROUND_ACCEPTED`,
`ROUND_ABORTED`. Every entry into `LOW_POWER_LISTEN` records exactly one `stop_reason`.

### CR-B1 — Two completely separate paths
**PATH A — local range exhaustion** (own assigned range fully searched, no valid solution
found):
`ACTIVE_HASHING → EXHAUSTED_PENDING → LOW_POWER_LISTEN`, `stop_reason = RANGE_EXHAUSTED`.
On this path the range is closed: `coverage_state = searched`, `custody_status = completed`.

**PATH B — verified valid-solution stop** (miner verifies a valid early-stop certificate for
the current round):
`ACTIVE_HASHING → LOW_POWER_LISTEN` **directly**, `stop_reason = VALID_SOLUTION_VERIFIED`.
**PATH B MUST NOT pass through `EXHAUSTED_PENDING`.** During verification the miner **stays in
`ACTIVE_HASHING`**; only after all validation steps pass may it enter `LOW_POWER_LISTEN`. On
this path the assignment is **PAUSED**, not searched or exhausted: the retained
`actual_frontier` is preserved and **no unsearched positions are credited as searched**.

**Resume after a paused (PATH B) stop**, if the full block is later rejected, unavailable, or
times out:
`LOW_POWER_LISTEN → WAKING → ACTIVE_HASHING`, resuming from the retained `actual_frontier`,
with wake and transition energy fully accounted.

**Round closure.** If the full block is accepted, all remaining assignments close because the
**round ended** (`stop_reason = ROUND_ACCEPTED`), **not** because their ranges were exhausted.
`ROUND_ABORTED` closes assignments with `stop_reason = ROUND_ABORTED`. Neither marks ranges
exhausted.

**Assignment revocation.** `ACTIVE_HASHING → LOW_POWER_LISTEN` directly,
`stop_reason = ASSIGNMENT_REVOKED`; only the unsearched suffix is returned for reassignment.
Not via `EXHAUSTED_PENDING`.

### CR-B2 — Amended I4
A miner may enter `LOW_POWER_LISTEN` only after **one** of: (1) accepted range-exhaustion
accounting (via `EXHAUSTED_PENDING`); (2) explicit assignment revocation; (3) a fully verified
valid-solution early-stop certificate; (4) round closure. Every entry records the
`stop_reason`. **No unverified certificate may cause the transition.** `EXHAUSTED_PENDING`
remains exclusive to the range-exhaustion path (PATH A).

### CR-B3 — Amended I11 (solution-certificate invariant only)
A miner may stop hashing because of an early-stop certificate **only after** validating: the
current `RoundID`, current `TemplateID`, current `AssignmentID`, `MinerID`, `nonce`
membership, recomputed `candidate_hash`, `target` satisfaction, and
authentication/signature. A failed or partially verified certificate causes **no**
hashing-state transition. I11 has **no** dependency on progress commitments, coverage
frontiers, range exhaustion, searched-domain coverage, or proof of no solution in a range.
Range exhaustion is governed by **I4, I8a, and the actual-vs-reported progress model**, not by
I11.

### CR-B4 — No "target-verified exhaustion"
Remove every occurrence or semantic equivalent of "target verification confirms no valid
solution in the whole range", "verified target-checked exhaustion", "cryptographically
verified exhaustion", "I11 proves exhaustion". Canonical exhaustion semantics:
- **Honest simulation path:** `actual_frontier = range_end`,
  `actual_positions_evaluated = range_size`, `actual_exhaustion = true`, and no valid solution
  was encountered during the actual evaluated sequence.
- **Adversarial simulation path:** `reported_exhaustion` is compared with simulator ground
  truth through the modeled audit/detection abstraction. When the protocol claim is accepted,
  use the phrase **"accepted reported exhaustion under the modeled audit abstraction"**.
Never call that claim a cryptographic proof or verified actual exhaustion.

### CR-B5 — Completed ranges are not reassignable
A fully exhausted range under the same `RoundID` and `TemplateID` is complete:
`coverage_state = searched`, `custody_status = completed`. Do not release it to the
reassignable pool, mark it `inactive_unsearched`, reassign it under the same `TemplateID`, or
use exhaustion as a reassignment reason. **Custody set** (I8b) becomes
`{original, renewed, reassigned, revoked, expired, abandoned, completed}`. **Permitted
reassignment reasons** are exactly: `lease_expiry`, `abandonment`, `revocation`, `departure`,
`conflict`, `security_recovery`. Only an **unsearched suffix** may be reassigned. A template
refresh creates a **new** candidate-identity domain and **new original** assignments under the
new `TemplateID`; it is not a reassignment of the completed old range. Remove the contradictory
phrase "EXHAUSTED_PENDING without completing the range" (`EXHAUSTED_PENDING` is reachable only
after completion / accepted exhaustion accounting).

### CR-B6 — Exact hash-rate decomposition (new I17)
`H_honest(t)` = sum of hash rates of honest miners in `ACTIVE_HASHING`;
`H_adversarial(t)` = sum of hash rates of adversarial miners in `ACTIVE_HASHING`;
`H_active(t) = H_honest(t) + H_adversarial(t)`. The adversarial-behavior model may sample or
decide **which adversarial miners** continue hashing, but **after** miner states are
determined all three quantities are computed **deterministically** from the active-state
census. Do **not** sample `H_adversarial` independently after `H_active` has been computed.
**I17 (new):** for every event-update time, `H_active(t) = H_honest(t) + H_adversarial(t)`
exactly. When `H_active(t) = 0`, `q_adv(t)` is **undefined/NA** and a security-floor breach is
recorded — **not** treated as zero.

### CR-B7 — Narrowed early-stop wording
The early-stop certificate is **the only solution-triggered mechanism that authorises miners
to stop hashing before full-block propagation completes.** Miners may also cease hashing
because of: own-range exhaustion; assignment revocation; round acceptance; round abort; or
offline/disqualification transitions.

### CR-B8 — Matched-control description
The control and idle-policy scenario match on: installed/registered aggregate hash-rate
capacity at the start; miner hardware and efficiency; fixed difficulty; target; fixed
observation horizon; and workload/template rules where applicable. **They do not execute the
same total work.** Under the idle policy: `H_active(t)` may decrease; realised hash
evaluations may decrease; accepted-block count and block interval may change; security
exposure may change. A fixed-capacity, fixed-horizon **energy** comparison is **not** by
itself a service-equivalent or security-equivalent comparison. Service and security
non-inferiority are evaluated only after the frozen experiments.

### CR-B9 — Network-arrival and early-stop ordering
1. A candidate solution is found.
2. Its certificate propagates with modeled per-recipient arrival times.
3. Each recipient continues hashing while validating.
4. After successful validation, that recipient enters `LOW_POWER_LISTEN` with
   `stop_reason = VALID_SOLUTION_VERIFIED` (assignment PAUSED).
5. Full block propagation/validation continues.
6. If the full block is accepted, the round closes.
7. If the full block is rejected or times out, stopped miners wake and resume their paused
   assignments (`LOW_POWER_LISTEN → WAKING → ACTIVE_HASHING`).
No recipient is labeled `EXHAUSTED` merely because a valid solution was received. No
chain-wide fork-choice proof is claimed.

---

## Defect → correction summary

| ID | Defect (post-1A) | Correction |
|----|------------------|-----------|
| B1 | Valid-solution stop merged with exhaustion path through `EXHAUSTED_PENDING` | Two separate paths; PATH B goes directly to `LOW_POWER_LISTEN`, assignment PAUSED, resumable |
| B2 | I4 did not treat verified-solution stop as a distinct legal trigger | I4 lists four triggers, each with a `stop_reason`; `EXHAUSTED_PENDING` exclusive to exhaustion |
| B3 | I11 coupled to progress/coverage/exhaustion | I11 = solution-certificate validation only |
| B4 | "target-verified exhaustion" implied a proof of no solution | Honest = actual cursor; adversarial = accepted reported exhaustion under modeled audit |
| B5 | Completed/exhausted ranges could be reassigned; exhaustion was a reassignment reason | `custody_status = completed`; exhaustion removed from reassignment reasons; only unsearched suffix reassignable |
| B6 | `H_adversarial` sampled independently of `H_active` | Deterministic census; new I17 identity; `q_adv` NA at zero active hash rate |
| B7 | Early-stop called the only trigger to stop early | Narrowed to the only **solution-triggered** mechanism before full-block propagation |
| B8 | Matched control implied equal realised work | Match on capacity/hardware/difficulty/target/horizon; not equal work; not service/security equivalent |
| B9 | Early-stop/arrival ordering under-specified | Seven-step ordering; recipients pause (not exhaust); resume on block rejection |

## Stage-2 status

Stage 2 remains **BLOCKED pending this re-audit**. After the corrections and the semantic
state-path audit (`STAGE_01B_STATE_PATH_AUDIT.md`) pass, the two paths never merge, I4/I11/I17
are consistent, completed ranges are non-reassignable, and the hash-rate identity holds — at
which point Stage 2 can be implemented deterministically, subject to explicit approval.
