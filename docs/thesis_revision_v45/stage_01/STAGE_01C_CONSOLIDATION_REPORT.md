# Stage 1C — Specification Consolidation Report

Consolidation-only, documentation-only stage. Branch
`thesis-v45-pocol-stage1c-specification-consolidation`, from Stage-1B commit
`f2057d40a9b83ba7f880f2696b9db408f3a2e387`. No executable code, configuration, DOCX/PDF,
experiments, or protected-artifact changes. **No new protocol features** — every normative
procedure is made to conform exactly to the already-accepted B1–B9 rules. Name remains
**PoCol**; mechanism remains *the idle policy within PoCol*.

This report is the single source of truth for C1–C10. The pseudocode and miner state-machine
side effects are the primary targets.

---

## C1 — `EnterLowPowerListen` has five reason-specific dispositions
Replace the generic procedure. It supports exactly `RANGE_EXHAUSTED`, `ASSIGNMENT_REVOKED`,
`VALID_SOLUTION_VERIFIED`, `ROUND_ACCEPTED`, `ROUND_ABORTED`, each with the canonical
disposition:
- **RANGE_EXHAUSTED:** source must be `EXHAUSTED_PENDING`; accepted exhaustion accounting must
  exist; `coverage_state=searched`, `custody_status=completed`; close the assignment; do NOT
  release or reassign any part of the completed range.
- **ASSIGNMENT_REVOKED:** source may be `ACTIVE_HASHING`; preserve the accepted searched
  prefix; only the accepted unsearched suffix becomes `inactive_unsearched`/reassignable;
  close/supersede the assignment.
- **VALID_SOLUTION_VERIFIED:** source must be `ACTIVE_HASHING`; certificate must pass I11;
  PAUSE the assignment; retain `actual_frontier` and `accepted_frontier`; do NOT change
  coverage to `searched`; do NOT release the assignment.
- **ROUND_ACCEPTED / ROUND_ABORTED:** close the assignment because the round ended; do NOT
  mark the range exhausted; do NOT reassign under the closed `TemplateID`.
Delete every generic "RELEASE any held range back to pool / mark inactive/reassignable" from
`EnterLowPowerListen`.

## C2 — `RangeExhaust` adjudicates before marking searched/completed
Order: (1) preserve ground truth `actual_frontier`, `actual_positions_evaluated`,
`actual_exhaustion`, `actual_solution_positions`; (2) record protocol claim
`reported_frontier`, `reported_exhaustion`; (3) adjudicate — honest path may accept exact
ground-truth completion, adversarial path passes the modeled audit/detection abstraction;
(4) only when `claim_accepted_or_rejected = ACCEPTED`: `accepted_frontier=range_end`,
`accepted_exhaustion=true`, `coverage_state=searched`, `custody_status=completed`, transition
`ACTIVE_HASHING → EXHAUSTED_PENDING`; (5) when rejected: do not mark searched/completed, do
not enter `EXHAUSTED_PENDING`, preserve actual coverage, apply the adversarial/failure
response. A final reported `ProgressCommit` is a claim, not automatically accepted coverage.

## C3 — Three separate coverage layers
`actual_frontier`/`actual_searched`; `reported_frontier`/`reported_searched`;
`accepted_frontier`/`accepted_searched`. `ProgressCommit` may update `reported_*` **only** and
MUST NOT update the normative I8a measure. **I8a uses accepted coverage only:**
`accepted_searched + active_unsearched + inactive_unsearched = assigned_domain`. Honest-mode
runs may set accepted = ground truth by explicit model rule; adversarial-mode runs promote
reported → accepted only after the modeled adjudication rule.

## C4 — Reassign only the accepted unsearched suffix
For `LeaseExpiry`, `Abandonment`, `Revocation`, `Departure`, `Conflict`, `SecurityRecovery`:
`suffix_start = accepted_frontier + 1`; `reassignable_suffix = [suffix_start, range_end]`. If
no accepted positions exist, the suffix may be the whole range. If `accepted_frontier =
range_end`, the range is completed and no suffix exists. Never mark a searched prefix or a
completed range reassignable. `RangeReassign` receives the exact unsearched suffix, not the
original full range.

## C5 — `TemplateRefresh` creates original assignments
Close all assignments under the old `TemplateID`; preserve their historical
coverage/provenance; create a new immutable template and fresh `TemplateID`; create new
**ORIGINAL** assignments over the new candidate-identity domain with
`previous_assignment_reference = null`; do NOT call `RangeReassign` for old ranges; do NOT
rebind old assignments; keep difficulty fixed. A new `TemplateID` is a new search domain, not
a reassignment-lineage event.

## C6 — Event-ordered solution propagation
`ActiveHashing` MUST NOT call `ValidBlockAccept` immediately on a hit. Sequence: (1) find
valid candidate; (2) construct early-stop certificate; (3) schedule certificate-arrival events
per recipient using modeled propagation delays; (4) schedule full-block propagation/arrival
events; (5) finder ceases hashing under the solution-found/verified rule, block-propagation
energy accounted; (6) each recipient stays `ACTIVE_HASHING` until its certificate-arrival event
fully validates; (7) on success the recipient enters `LOW_POWER_LISTEN`,
`stop_reason=VALID_SOLUTION_VERIFIED`, assignment PAUSED; (8) block acceptance occurs only at
the **modeled acceptance point** after the full block arrives and validates; (9) the
discrete-event queue itself establishes earliest arrival; (10) only exactly-equal acceptance
timestamps break by `candidate_hash` then `MinerID`; (11) competing proposals become
stale/competing records; (12) on rejection/timeout paused miners wake and resume; (13) on
acceptance round closure closes remaining assignments without labeling them exhausted. The
**modeled acceptance point** is a designated coordinator/validator or a clearly identified
canonical local view. Do NOT use a global set of future solutions; do NOT close
`ROUND_ACCEPTED` at solution-discovery time.

## C7 — Centralised security-floor evaluation
`ActiveHashRateUpdate` computes only `H_honest`, `H_adversarial`, `H_active`, and `q_adv` or
`NA`. `SecurityFloorEvaluate` alone records breaches and triggers recovery:
`if H_active == 0: q_adv = NA; record active-floor breach; record honest-floor breach; do not
compare NA with maximum_adversarial_share; trigger SECURITY_RECOVERY; else evaluate active,
honest, and q_adv thresholds`. Prevent duplicate breach records for the same event and
threshold. Retain exact I17: `H_active = H_honest + H_adversarial`.

## C8 — Clean miner state-machine side effects
Remove from the range-exhaustion path every instruction that releases a completed range "for
reclamation." **T7:** accepted exhaustion only; mark coverage `searched`; mark custody
`completed`; `ACTIVE_HASHING → EXHAUSTED_PENDING`. **T8:** confirmation/finalisation only;
`EXHAUSTED_PENDING → LOW_POWER_LISTEN`; do not release or reassign the completed range. **T9
redeployment:** permitted only after the prior completed assignment is fully adjudicated and
closed; assigns an unrelated available unsearched suffix or new assignment; not a reassignment
of the completed range. Remove any wording that calls a false exhaustion claim an "unverified
early-stop" or invokes I11 for it: false exhaustion belongs to the progress/audit model; false
solution certificates belong to I11.

## C9 — Full-domain exhaustion uses accepted coverage
`FullRangeExhaustNoSolution` may enter `ROUND_EXHAUSTED` only when the I8a ledger shows the
entire assigned domain as **accepted** searched coverage. Reported coverage alone is
insufficient. For adversarial runs every accepted coverage claim must have a defined
adjudication outcome; an unaudited claim may be accepted only if the modeled policy explicitly
defines that result, recorded as modeled acceptance (not actual proof). Do NOT transition to
`ROUND_EXHAUSTED` while any `active_unsearched` or `inactive_unsearched` coverage remains.

## C10 — Canonical reward-eligibility wording
Because incentive semantics are deferred to Stage 5, every reward-eligibility field/state
description uses one canonical wording: **"reward eligibility: NOT SPECIFIED AT STAGE 1"**,
except that a valid solution may be recorded as having a solver identity. Do not assign idle
credit, availability reward, work reward, or other reward eligibility inconsistently across
documents.

---

## Defect → correction summary

| ID | Defect (post-1B) | Correction |
|----|------------------|-----------|
| C1 | `EnterLowPowerListen` generic; released held ranges | Five reason-specific dispositions; no generic release |
| C2 | `RangeExhaust` set `searched` before adjudication | Adjudicate first; mark searched/completed only on ACCEPTED |
| C3 | `ProgressCommit` updated the I8a searched measure directly | Three coverage layers; I8a uses accepted coverage only |
| C4 | Lease/reassign returned whole range | Reassign only `[accepted_frontier+1, range_end]` |
| C5 | `TemplateRefresh` rebound old assignments | Close old; create new original assignments; `previous_assignment_reference=null` |
| C6 | `ActiveHashing` accepted the block at discovery | Event-scheduled certificate/block propagation; acceptance at the modeled acceptance point |
| C7 | `ActiveHashRateUpdate` recorded breaches; `q_adv=NA` compared | Compute-only update; `SecurityFloorEvaluate` owns breaches; NA never compared |
| C8 | T7/T8 released completed range; false exhaustion invoked I11 | No release of completed ranges; false exhaustion → audit model, not I11 |
| C9 | `ROUND_EXHAUSTED` on reported coverage | Requires accepted full-domain coverage; no unsearched remaining |
| C10 | Inconsistent reward-eligibility wording | "NOT SPECIFIED AT STAGE 1" (solver identity only) |

## Stage-2 status
Stage 2 remains **BLOCKED pending final re-audit**. Once every acceptance gate passes and all
semantic test vectors hold on paper (`STAGE_01C_SEMANTIC_TEST_VECTORS.md`), the specification
and its executable pseudocode conform to B1–B9 and C1–C10 and Stage 2 can be implemented
deterministically, subject to explicit approval.
