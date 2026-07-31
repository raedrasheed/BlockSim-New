# Stage 1G — Acceptance-Predicate Audit (G1)

Documentation-only audit of correction **G1**: invariant **I2** corrected to
**discovery-time eligibility** for PoCol. This deliverable confirms that the acceptance
predicate binds each accepted solution to its discovery-time assignment version and that
no procedure imposes "CURRENT at acceptance" semantics. No property is experimentally
supported at Stage 1; this is a structural audit of the specification.

## 1. Corrected I2 (discovery-time eligibility)

An accepted solution `s` binds to an **IMMUTABLE** assignment version `A` such that:

- **(i)** `A` was **VALID** and **CURRENT** for `signer(s)` at the solution's `discovery_time`;
- **(ii)** `A` was **not revoked** before `discovery_time`;
- **(iii)** `A` **belonged to `signer(s)`** at `discovery_time`;
- **(iv)** `A` **contained the submitted nonce** (`nonce(s) ∈ range(A)`);
- **(v)** `A` was **bound to the candidate's `(RoundID, TemplateID)`**;
- **(vi)** `A` **remains resolvable** from the `SolutionEligibilitySnapshot`.

`A` **need NOT remain CURRENT** at certificate or block arrival — it may by then be
`PAUSED` or `SUPERSEDED`. **No "CURRENT at acceptance" semantics appear anywhere** in the
specification.

## 2. Discovery-time conjuncts vs `ValidateCandidate`

`ValidateCandidate` is the single canonical predicate. It validates the **SIGNED
certificate** against the **immutable `snapshot`**, resolving the snapshot's
`(AssignmentID, assignment_version)` to the exact immutable version — never against the
finder's later (possibly `PAUSED`) assignment state.

| I2 conjunct | `ValidateCandidate` check |
|---|---|
| (i) VALID + CURRENT at discovery | `snapshot.assignment_status_at_discovery = CURRENT`; snapshot's `(AssignmentID, assignment_version)` resolved to the immutable version |
| (ii) not revoked before discovery | `assignment(AssignmentID, assignment_version)` was NOT revoked before `snapshot.discovery_time` |
| (iii) belonged to signer at discovery | certificate binds snapshot on `MinerID`; signature/authentication valid for `certificate.MinerID` over the signed fields |
| (iv) contained the submitted nonce | `snapshot.range_start <= certificate.nonce <= snapshot.range_end` |
| (v) bound to candidate's RoundID/TemplateID | `certificate.RoundID = RoundID_current AND certificate.TemplateID = TemplateID_committed`; `candidate_hash` is the modeled digest of `TemplateID`+nonce and satisfies `target` under fixed `D` |
| (vi) resolvable from snapshot | certificate binds snapshot (same RoundID/TemplateID/AssignmentID/assignment_version/nonce/candidate_hash/target); predicate evaluated against the snapshot, not later state |

There is **no** conjunct requiring the assignment to be `CURRENT` at certificate or block
arrival.

## 3. Call sites use the SAME predicate

| Call site | Role | Predicate invoked | Requires CURRENT-at-acceptance? |
|---|---|---|---|
| `SelfValidateFoundSolution` | finder self-validation before it may stop | `ValidateCandidate(certificate, snapshot)` | No |
| `EarlyStopVerify` | recipient verification while still `ACTIVE_HASHING` | `ValidateCandidate(certificate, snapshot)` | No |
| `AcceptanceBatchFinalize` | acceptance / arbitration | `ValidateCandidate(a.certificate, a.snapshot)` per accepted candidate | No |

All three resolve the snapshot to its immutable version and validate **discovery-time**
eligibility. None consults the finder's current assignment status.

## 4. Properties

| # | Property | Result | Why |
|---|---|---|---|
| P1 | A solution discovered under version `v1` stays acceptable after `v1` becomes `PAUSED` or `SUPERSEDED` | PASS | E1 snapshot is immutable; `ValidateCandidate` resolves `(AssignmentID, assignment_version)` to that exact immutable version (I18b), independent of `v1`'s later status |
| P2 | No procedure uses acceptance-time `CURRENT` | PASS | The only status check is `snapshot.assignment_status_at_discovery = CURRENT`; no procedure checks assignment status at certificate/block arrival |
| P3 | An out-of-range or never-eligible solution is still rejected | PASS | Conjuncts (iv) nonce-in-range, (i) CURRENT-at-discovery, target satisfaction and signature checks reject out-of-range / never-eligible / forged certificates |
| P4 | I2 references updated consistently | PASS | Discovery-time wording aligned across invariant catalogue (I2), miner state machine, round state machine, terminology, and traceability |

No property claim beyond structural consistency is made; each is a specification target
with a planned verification stage.

## 5. Result

**ACCEPTANCE-PREDICATE AUDIT (G1): PASS**

The corrected I2 is discovery-time eligibility; `ValidateCandidate` is the single canonical
predicate at all three call sites and never requires "CURRENT at acceptance". This audit is
exercised by **TV39**.
