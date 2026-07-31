# Stage 1D — State-Invariant Audit

Verifies that the corrected procedures uphold I1–I17, with emphasis on the invariants the
Stage-1D fixes touch.

| Invariant | Statement (abridged) | Upheld by (post-D) |
|-----------|----------------------|--------------------|
| I1 | No two valid active assignments overlap | `RangeAssign`/`RangeReassign`/`ReserveActivate`/`WakeComplete` overlap guards; `TemplateRefresh` new-domain partitioning |
| I2 | Accepted solution ∈ signer's valid current assignment | `ValidateCandidate`, `SelfValidateFoundSolution`, `EarlyStopVerify` (nonce ∈ range) |
| I3 | Accepted solution matches current RoundID+TemplateID | same three procedures |
| I4 | `LOW_POWER_LISTEN` entry only via the five recorded `stop_reason` triggers | `EnterLowPowerListen` (five dispositions); `EXHAUSTED_PENDING` only via `ExhaustionAdjudicate` ACCEPTED |
| I5 | Durations ≥ 0, reconcile to horizon T | `WakeComplete`/`ResumeFromPause` charge wake+transition; `CloseRoundAssignments` finalises to closure time |
| I6 | Per-miner state energies sum to per-miner energy | all activation via `WAKING` charges `P_wake·t_wake`+`E_transition`; `E_verification` separate |
| I7 | Per-miner energies sum to network energy | `CloseRoundAssignments`/`RoundAbort` finalise the energy ledger |
| I8a | `accepted_searched + active_unsearched + inactive_unsearched = assigned_domain` | only `ExhaustionAdjudicate` (ACCEPTED) promotes reported→accepted; `ProgressCommit` writes reported only; `RangeReassign` reassigns accepted unsearched suffix only |
| I8b | Custody set orthogonal to coverage | `{original, renewed, reassigned, revoked, expired, abandoned, completed}` |
| I9 | Every reassignment has complete provenance | `RangeReassign` provenance record |
| I10 | Reserve activation creates no overlap | `ReserveActivate`/`WakeComplete` overlap guard |
| I11 | Solution-certificate validation only | `SelfValidateFoundSolution`, `EarlyStopVerify`, `ValidateCandidate`; **no** exhaustion/progress dependency; does **not** gate T7 |
| I12 | Difficulty fixed | asserted in `RoundInitialise`, `TemplateCommit`, `TemplateRefresh` |
| I13 | Shared physical executions not double-counted | provenance `prior_pc` de-dup |
| I14 | Zero-block outcomes retained | `FullRangeExhaustNoSolution`, `RoundAbort` |
| I15 | Undefined block-normalised metrics remain NA | same |
| I16 | Security-floor breaches recorded, not repaired | `SecurityFloorEvaluate` (sole owner; `RECORD_ONCE`) |
| I17 | `H_active = H_honest + H_adversarial`; `q_adv` NA at zero | `ActiveHashRateUpdate` (compute-only); `SecurityFloorEvaluate` (NA never compared) |

## Emphasis: Stage-1D-touched invariants

- **I4 (D1/D2/D3/D7):** the only route into `EXHAUSTED_PENDING` is `ExhaustionAdjudicate` ACCEPTED
  (PATH A); `LOW_POWER_LISTEN` is entered only via `EnterLowPowerListen` with one of five reasons,
  each wired to a caller (`ExhaustionAdjudicate`→RANGE_EXHAUSTED; `ScheduleSolutionPropagation`/
  `EarlyStopVerify`→VALID_SOLUTION_VERIFIED; revocation→ASSIGNMENT_REVOKED; `CloseRoundAssignments`
  →ROUND_ACCEPTED/ROUND_ABORTED).
- **I11 (D1/D9):** decoupled from exhaustion everywhere (pseudocode, MINER_SM §1.5/prohibited
  transitions, INVARIANT_CATALOGUE); false exhaustion is a progress/audit finding.
- **I5/I6 (D2):** because all activation and resume pass through `WAKING`, no wake/transition
  energy is ever skipped; a zero wake-latency experimental value still traverses the accounting
  path.
- **I17 (C7 retained):** `ActiveHashRateUpdate` computes only; `q_adv=NA` never compared.

## Result
**STATE-INVARIANT AUDIT: PASS** — I1–I17 hold across the corrected procedures.
