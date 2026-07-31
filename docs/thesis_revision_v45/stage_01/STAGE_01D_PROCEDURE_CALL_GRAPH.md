# Stage 1D — Procedure Call Graph

Extracted from `STAGE_01_PROTOCOL_PSEUDOCODE.md`. `→` is a direct `CALL`; `⇒` is a scheduled
discrete `event` (`SCHEDULE event`). This graph proves the required reachability properties.

## Direct-call edges (CALL)

```
RoundInitialise            (leaf)
TemplateCommit             (leaf)
MinerRegister              (leaf)
RangeAssign                → WakeComplete
ActiveHashing              → EarlyStopGenerate, ScheduleSolutionPropagation,
                             ActualRangeCompletion, ReportedExhaustionClaim,
                             ExhaustionAdjudicate, ProgressCommit
ActualRangeCompletion      (leaf)
ReportedExhaustionClaim    (leaf)
ExhaustionAdjudicate       (leaf)          # may CALL RangeReassign / RoundAbort in the REJECTED branch
EnterLowPowerListen        (leaf)
ActiveHashRateUpdate       (leaf)
SecurityFloorEvaluate      (leaf)
ReserveActivate            → WakeComplete
WakeComplete               (leaf)
LeaseExpiry                → RangeReassign
RangeReassign              → WakeComplete
ProgressCommit             (leaf)
EarlyStopGenerate          (leaf)
EarlyStopVerify            (leaf)
SelfValidateFoundSolution  (leaf)
ScheduleSolutionPropagation→ SelfValidateFoundSolution, EnterLowPowerListen
CertificateArrival         → EarlyStopVerify
BlockAcceptancePoint       → AcceptanceTimestampBatch, SecurityFloorEvaluate
ValidateCandidate          (leaf)
AcceptanceTimestampBatch   → ValidateCandidate, ValidBlockAccept
ValidBlockAccept           → CloseRoundAssignments
CloseRoundAssignments      → EnterLowPowerListen
ResumeFromPause            → ActiveHashRateUpdate, ActiveHashing
FullRangeExhaustNoSolution → TemplateRefresh, RoundAbort
TemplateRefresh            → TemplateCommit, WakeComplete
RoundAbort                 → CloseRoundAssignments
```

## Scheduled-event edges (SCHEDULE event)

```
ScheduleSolutionPropagation ⇒ CertificateArrival, BlockAcceptancePoint
BlockAcceptancePoint        ⇒ ResumeFromPause          # REJECTED / BLOCK_UNAVAILABLE / PROPAGATION_TIMEOUT
```

## Required-property proofs

1. **Every state transition has a callable procedure.** Each miner transition T1–T30 and each
   round transition is effected inside a named procedure: registration (`MinerRegister`);
   activation `→ WAKING → ACTIVE_HASHING` (`RangeAssign`/`ReserveActivate`/`RangeReassign`/
   `TemplateRefresh` → `WakeComplete`); PATH-A exhaustion (`ExhaustionAdjudicate` → `EnterLowPowerListen`);
   PATH-B stop (`EarlyStopVerify`/`ScheduleSolutionPropagation` → `EnterLowPowerListen`); resume
   (`ResumeFromPause`); closure (`CloseRoundAssignments`); disqualify/offline (guarded in the
   owning procedures). No transition is caused by an unmodeled external action.
2. **Every rejection/timeout path reaches `ResumeFromPause`.** `BlockAcceptancePoint(outcome ∈
   {REJECTED, BLOCK_UNAVAILABLE, PROPAGATION_TIMEOUT})` ⇒ `ResumeFromPause` for each PAUSED
   `VALID_SOLUTION_VERIFIED` miner (D5).
3. **Every round closure reaches `CloseRoundAssignments`.** The only closure callers are
   `ValidBlockAccept` (ROUND_ACCEPTED) and `RoundAbort` (ROUND_ABORTED); both `→
   CloseRoundAssignments` (D7). No other procedure sets `ROUND_ACCEPTED`/`ROUND_ABORTED`.
4. **Every activation reaches `WAKING`.** `RangeAssign`, `ReserveActivate`, `RangeReassign`, and
   `TemplateRefresh` all create a PENDING assignment, transition the holder to `WAKING`, and `→
   WakeComplete` (which performs `WAKING → ACTIVE_HASHING`). `ResumeFromPause` also passes
   through `WAKING`. There is no direct `REGISTERED/RESERVE → ACTIVE_HASHING` edge (D2).
5. **`TemplateCommit` is called only from `TEMPLATE_COMMITMENT`.** Its two callers are
   `RoundInitialise`→ (round enters `TEMPLATE_COMMITMENT`) and `TemplateRefresh`, which
   transitions `TEMPLATE_REFRESH → TEMPLATE_COMMITMENT` immediately before the `CALL
   TemplateCommit` (D8). No caller invokes it from `TEMPLATE_REFRESH`.
6. **Acceptance funnels through arbitration.** `BlockAcceptancePoint(ACCEPTED_CANDIDATE) →
   AcceptanceTimestampBatch → {ValidateCandidate*, ValidBlockAccept → CloseRoundAssignments}`.
   No procedure other than `AcceptanceTimestampBatch` calls `ValidBlockAccept`; no round closure
   precedes arbitration (D6).
7. **Finder self-validation precedes stopping.** `ScheduleSolutionPropagation → SelfValidateFoundSolution`
   gates the finder's `EnterLowPowerListen(VALID_SOLUTION_VERIFIED)` (D4).

## Result
**PROCEDURE CALL GRAPH: PASS** — all seven required reachability properties hold.
