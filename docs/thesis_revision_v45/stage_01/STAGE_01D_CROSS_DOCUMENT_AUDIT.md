# Stage 1D — Cross-Document Audit (acceptance gates)

The ten Stage-1D acceptance gates, verified by procedure-call-graph analysis and corpus
checks (not string search alone).

| # | Acceptance gate | Result |
|--:|-----------------|--------|
| 1 | I11 has no exhaustion/progress dependency anywhere | **PASS** — I11 scoped to solution-certificate validation (INVARIANT_CATALOGUE I11, MINER_SM §1.5/prohibited transitions, pseudocode); all remaining I11↔exhaustion strings are negations/fix descriptions |
| 2 | `RangeAssign` never bypasses `WAKING` | **PASS** — `RangeAssign` transitions holder → `WAKING` and returns `CALL WakeComplete`; no direct `→ ACTIVE_HASHING`; same for `ReserveActivate`/`RangeReassign`/`TemplateRefresh`/`ResumeFromPause` (D2) |
| 3 | False exhaustion is callable without violating an actual-completion precondition | **PASS** — `ReportedExhaustionClaim` has `PRECONDITIONS: none` (callable with `actual_frontier < range_end`); `ExhaustionAdjudicate` rejects it via the modeled audit (D3) |
| 4 | The finder self-validates before stopping | **PASS** — `ScheduleSolutionPropagation` gates on `SelfValidateFoundSolution` (I11 fields) before `EnterLowPowerListen(VALID_SOLUTION_VERIFIED)` (D4) |
| 5 | Full-block rejection and timeout explicitly resume paused miners | **PASS** — `BlockAcceptancePoint(REJECTED/BLOCK_UNAVAILABLE/PROPAGATION_TIMEOUT)` ⇒ `ResumeFromPause` per paused miner; `ResumeFromPause` restores CURRENT + recomputes hash rates (D5) |
| 6 | Exact-timestamp candidates are batched before acceptance | **PASS** — `BlockAcceptancePoint(ACCEPTED_CANDIDATE)` → `AcceptanceTimestampBatch` validates all, arbitrates (candidate_hash, then MinerID), then `ValidBlockAccept` (D6) |
| 7 | `RoundAbort` closes assignments and miner paths | **PASS** — `RoundAbort` → `CloseRoundAssignments(ROUND_ABORTED)`; enumerates all open assignments, wires `EnterLowPowerListen(ROUND_ABORTED)`, cancels pending events (D7) |
| 8 | `TemplateCommit` is never called from `TEMPLATE_REFRESH` | **PASS** — `TemplateRefresh` transitions `TEMPLATE_REFRESH → TEMPLATE_COMMITMENT` before `CALL TemplateCommit`; ROUND_SM R17/R18 aligned (D8) |
| 9 | All 17 semantic test vectors follow named procedures exactly | **PASS** — `STAGE_01D_SEMANTIC_TEST_VECTORS.md` (TV1–TV17); no vector assumes an unmodeled external action |
| 10 | No executable code, configuration, DOCX, or PDF changes | **PASS** — git delta confined to `docs/thesis_revision_v45/stage_01/`; draft-42 `2c3afdc5…`, draft-44 `a31400bc…` byte-identical |

## Procedure-call-graph reachability (see `STAGE_01D_PROCEDURE_CALL_GRAPH.md`)
- every state transition has a callable procedure — **PASS**
- every rejection/timeout path reaches `ResumeFromPause` — **PASS**
- every round closure reaches `CloseRoundAssignments` — **PASS**
- every activation reaches `WAKING` — **PASS**
- `TemplateCommit` is called only from `TEMPLATE_COMMITMENT` — **PASS**

## Residual fixes applied during this audit
- MINER_SM §1.5 convention, failure-behaviour text, and the prohibited-transition summary
  decoupled from I11 (D1/D9).
- ROUND_SM R18 no longer bypasses `TEMPLATE_COMMITMENT` (D8/C5).
- Sampling summary references `ExhaustionAdjudicate` (was `RangeExhaust`).

## Result
All ten acceptance gates pass and all five call-graph reachability properties hold. The
executable specification conforms to B1–B9, C1–C10, and D1–D9. Name remains PoCol; no new
protocol features; documentation only.
