# Stage 1D — Executable-Specification Fix Report

Documentation-only fix from Stage-1C commit `18d334329d543460a4ecdc85df3dfddaa53fa648`. No
executable code, configuration, DOCX/PDF, experiments, protected-artifact changes, or new
protocol features. Name remains **PoCol**; mechanism remains *the idle policy within PoCol*.
Every correction makes a normative procedure conform to the accepted B1–B9 / C1–C10 rules.

| ID | Defect (post-1C) | Correction |
|----|------------------|-----------|
| D1 | Residual I11↔exhaustion coupling (MINER_SM §1.5, failure text, prohibited transition) | I11 applies ONLY to solution-certificate validation; range exhaustion governed by I4/I8a/adjudication; false exhaustion is a progress/audit violation, not I11 |
| D2 | `RangeAssign` transitioned REGISTERED/RESERVE directly to `ACTIVE_HASHING` | All activation (initial, reserve, reassignment, template-refresh, resume) creates a PENDING assignment and passes through `WAKING` → `WakeComplete` → `ACTIVE_HASHING`; `WakeComplete` no longer recurses into `RangeAssign` |
| D3 | `RangeExhaust` precondition made false-exhaustion untestable | Split into `ActualRangeCompletion` (ground truth), `ReportedExhaustionClaim` (callable with actual_frontier<range_end), `ExhaustionAdjudicate` (only ACCEPTED sets accepted/searched/completed + EXHAUSTED_PENDING); TV1/TV2/TV3 updated |
| D4 | Finder stopped without self-validation | `ScheduleSolutionPropagation` calls `SelfValidateFoundSolution` (I11 fields) before the finder may stop; E_verification charged |
| D5 | Rejection/timeout/resume not wired | `BlockAcceptancePoint` handles ACCEPTED_CANDIDATE / REJECTED / BLOCK_UNAVAILABLE / PROPAGATION_TIMEOUT; non-accept schedules `ResumeFromPause` for every PAUSED VALID_SOLUTION_VERIFIED miner; `ResumeFromPause` restores CURRENT and recomputes hash rates; TV5 updated |
| D6 | First same-timestamp event accepted immediately | `AcceptanceTimestampBatch` gathers exact-timestamp candidates, `ValidateCandidate` all, picks smallest candidate_hash then MinerID, records others competing, then accepts; TV10/TV11 updated |
| D7 | Round closure inlined; ROUND_ABORTED disposition unwired | `CloseRoundAssignments(disposition, stop_reason)` enumerates ALL open assignments, cancels pending events, finalises energy; called by `ValidBlockAccept` (ROUND_ACCEPTED) and `RoundAbort` (ROUND_ABORTED) |
| D8 | `TemplateRefresh` called `TemplateCommit` from `TEMPLATE_REFRESH` | Sequence TEMPLATE_REFRESH → TEMPLATE_COMMITMENT → `TemplateCommit` (→ ASSIGNMENT) → fresh ORIGINAL assignments via WAKING; ROUND_SM R18 no longer bypasses commitment |
| D9 | Terminology residuals (target-checks = progress; I11 gates T7) | Intro distinguishes target verification (one solution, I11) from progress verification (claimed range progress, I4/I8a); MINER_SM convention/summary corrected |

## Canonical separations (binding)

- **Solution-certificate path** → governed by **I11** (`EarlyStopVerify`, `SelfValidateFoundSolution`,
  `ValidateCandidate`).
- **Range-exhaustion path** → governed by **I4, I8a, and the actual/reported/accepted adjudication
  model** (`ActualRangeCompletion` / `ReportedExhaustionClaim` / `ExhaustionAdjudicate`).
- **Activation** → always via `WAKING` (`WakeComplete`).
- **Round closure** → always via `CloseRoundAssignments`.
- **Same-timestamp acceptance** → always via `AcceptanceTimestampBatch` before any closure.

## New procedures added (all pseudocode)

`ActualRangeCompletion`, `ReportedExhaustionClaim`, `ExhaustionAdjudicate`,
`SelfValidateFoundSolution`, `ValidateCandidate`, `AcceptanceTimestampBatch`,
`CloseRoundAssignments`. (`RangeExhaust` removed; `BlockAcceptancePoint`, `ValidBlockAccept`,
`WakeComplete`, `RangeAssign`, `RangeReassign`, `TemplateRefresh`, `RoundAbort`,
`ResumeFromPause`, `ScheduleSolutionPropagation` amended.)

## Deliverables
Updated: STAGE_01_PROTOCOL_PSEUDOCODE, STAGE_01_MINER_STATE_MACHINE, STAGE_01_ROUND_STATE_MACHINE,
STAGE_01_INVARIANT_CATALOGUE (verified), STAGE_01C_SEMANTIC_TEST_VECTORS (superseded/aligned),
STAGE_01_TRACEABILITY_MATRIX. Added: STAGE_01D_{CORRECTION_REPORT, PROCEDURE_CALL_GRAPH,
EVENT_QUEUE_AUDIT, STATE_INVARIANT_AUDIT, SEMANTIC_TEST_VECTORS (17), CROSS_DOCUMENT_AUDIT,
CHECKSUM_MANIFEST.sha256}.

## Stage-2 status
Stage 2 remains **BLOCKED pending final acceptance review**. Once the acceptance gates and the
procedure-call graph verify, the executable specification is deterministically implementable.
