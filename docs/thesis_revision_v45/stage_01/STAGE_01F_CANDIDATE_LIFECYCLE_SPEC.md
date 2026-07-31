# Stage 1F — Candidate Lifecycle Specification (F1–F3)

Specifies the lifecycle of a `CandidatePropagationContext` (CPC): its immutable identity, its
fields, its status transitions, and the candidate-scoped pause/resume and active-set rules. Binds to
`STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.8 (data model), §16b–§16e (propagation/acceptance), and §21
(event priority).

## 1. Identity and context (F1)

Every discovered candidate solution gets, at `CreatePropagationContext`, an **immutable, globally
unique** `CandidateID` and `PropagationID`. Its `CandidatePropagationContext` holds at least:
`CandidateID`, `PropagationID`, `RoundID`, `TemplateID`, `certificate`, `SolutionEligibilitySnapshot`
(`snapshot`), `finder_MinerID`, `discovery_time`, `certificate_arrival_events`, `block_arrival_event`,
`acceptance_timestamp`, `status`, `failure_reason`.

Every certificate-arrival, block-arrival, validation, timeout, cancellation, and resume event carries
`CandidateID` and `PropagationID` in its envelope (§0.2). A context is **never** identified by
`RoundID` alone — multiple contexts coexist within one round.

## 2. Status lifecycle (F1)

```
                      CreatePropagationContext
   (discovery) ─────────────────► DISCOVERED
                                     │  (self-validate ok)
                                     ▼
                                SELF_VALIDATED
                                     │  (added to active_propagation_set; certificate/block events scheduled)
                                     ▼
                                 PROPAGATING
                                     │  (block-arrival event fires ACCEPTED_CANDIDATE → batch)
                                     ▼
                              PENDING_ACCEPTANCE
                    ┌────────────────┼─────────────────────────┐
      (batch winner)│      (non-accept / empty batch) │  (another candidate accepted)
                    ▼                ▼                          ▼
                 ACCEPTED          FAILED            COMPETING / STALE / CANCELLED
```

| Status | Set by | Meaning |
|--------|--------|---------|
| `DISCOVERED` | `CreatePropagationContext` | candidate just found; identity minted |
| `SELF_VALIDATED` | after `SelfValidateFoundSolution` ok | signed certificate self-validated (E2) |
| `PROPAGATING` | `ScheduleSolutionPropagation` (added to set) | certificate-arrival + block-arrival events scheduled; round is `SOLUTION_PROPAGATION` |
| `PENDING_ACCEPTANCE` | `ScheduleSolutionPropagation` (block event scheduled) / `BlockAcceptancePoint` | awaiting the modeled acceptance point |
| `FAILED` | `HandlePropagationFailure(CandidateID)` | REJECTED/BLOCK_UNAVAILABLE/PROPAGATION_TIMEOUT/NO_VALID_CANDIDATE; candidate-scoped |
| `ACCEPTED` | `ValidBlockAccept(winner)` | this candidate's block accepted; round closes once |
| `COMPETING` | `AcceptanceTimestampBatch` / `ValidBlockAccept` | valid same-timestamp loser |
| `STALE` / `CANCELLED` | `ValidBlockAccept` (other live contexts on acceptance) | superseded by the accepted block; its events cancelled |

A context is **live** while `status ∈ {DISCOVERED, SELF_VALIDATED, PROPAGATING, PENDING_ACCEPTANCE}`.
It is in `active_propagation_set` exactly while live.

## 3. Candidate-scoped pause and resume (F2)

When a miner verifies a certificate (`EarlyStopVerify` ok) or a finder self-validates
(`ScheduleSolutionPropagation`), it pauses via `EnterLowPowerListen(VALID_SOLUTION_VERIFIED, …)`,
which records on its assignment: `pause_cause_candidate_id`, `pause_cause_propagation_id`,
`paused_assignment_id`, `retained_actual_frontier`.

- `HandlePropagationFailure(CandidateID)` resumes ONLY miners whose
  `pause_cause_candidate_id = CandidateID`, and cancels ONLY that candidate's certificate-arrival /
  block-arrival events. It never touches another candidate's events or paused miners.
- If a paused miner has no matching failed pause cause, it is left unchanged.

**Multi-candidate disposition policy (explicit).** A miner verifies a certificate ONLY while
`ACTIVE_HASHING`. On `VERIFIED` it pauses (leaves `ACTIVE_HASHING`), so a later `CertificateArrival`
for a DIFFERENT candidate finds the miner not `ACTIVE_HASHING` and is IGNORED (`CertificateArrival`
guard). Therefore a miner has **at most one** pause cause at any time, and that pause cause is
unambiguous. This policy is exercised by TV28/TV29.

## 4. Active-propagation-set round-state rule (F3)

- The round enters `SOLUTION_PROPAGATION` when the FIRST context becomes live (empty→non-empty).
- The round remains `SOLUTION_PROPAGATION` while `size(active_propagation_set) > 0`.
- Failure of one candidate removes ONLY that candidate (`HandlePropagationFailure` REMOVEs `cpc`).
- `SOLUTION_PROPAGATION → HASHING` occurs ONLY when `propagation_quiescent` holds: no block accepted,
  set empty, no same-timestamp acceptance batch pending, no live candidate-specific acceptance event.
- On a security-floor breach the round moves to `SECURITY_RECOVERY` and PRESERVES the remaining live
  contexts (defined rule); on recovery it returns to `SOLUTION_PROPAGATION` if the set is still
  non-empty, else to `HASHING`.
- Acceptance of one candidate (`ValidBlockAccept`) sets it `ACCEPTED`, marks all other live contexts
  `COMPETING`/`STALE`/`CANCELLED`, cancels their events, clears the set, and closes the round
  **exactly once**.

## Result

The candidate lifecycle is fully candidate-scoped (F1/F2) and the round-state rule is driven by
`active_propagation_set` (F3): concurrent candidates are independent; one candidate's failure never
affects another; and the round stays in propagation while any candidate is live. Exercised by
TV28–TV30, TV38.
