# Stage 1E — Procedure Call Graph

Extracted from `STAGE_01_PROTOCOL_PSEUDOCODE.md` (post-E1..E10). `→` is a direct `CALL`; `⇒` is a
scheduled discrete `event` (`SCHEDULE event`). This graph proves the Stage-1E reachability
properties. New Stage-1E procedures: `CreateSolutionEligibilitySnapshot`,
`HandlePropagationFailure`, `CloseTemplateAssignments`.

## Direct-call edges (CALL)

```
RoundInitialise                    (leaf)
TemplateCommit                     (leaf)
MinerRegister                      (leaf)
RangeAssign                        → WakeComplete
ActiveHashing                      → CreateSolutionEligibilitySnapshot, EarlyStopGenerate,
                                     ScheduleSolutionPropagation, ActualRangeCompletion,
                                     ReportedExhaustionClaim, ExhaustionAdjudicate, ProgressCommit
ActualRangeCompletion              (leaf)
ReportedExhaustionClaim            (leaf)
ExhaustionAdjudicate               (leaf)   # may CALL RangeReassign / RoundAbort in the REJECTED branch
EnterLowPowerListen                (leaf)
ActiveHashRateUpdate               (leaf)
SecurityFloorEvaluate              (leaf)
ReserveActivate                    → WakeComplete                       # E4: creates PENDING before waking
WakeComplete                       (leaf)
LeaseExpiry                        → EnterLowPowerListen, RangeReassign # E9: renewal is in-state (no call)
RangeReassign                      → WakeComplete
ProgressCommit                     (leaf)
CreateSolutionEligibilitySnapshot  (leaf)   # E1 (new)
EarlyStopGenerate                  (leaf)
SelfValidateFoundSolution          → ValidateCandidate                 # E2
EarlyStopVerify                    → ValidateCandidate, EnterLowPowerListen
ResumeFromPause                    → ActiveHashRateUpdate, ActiveHashing
ScheduleSolutionPropagation        → SelfValidateFoundSolution, EnterLowPowerListen
CertificateArrival                 → EarlyStopVerify
BlockAcceptancePoint               → AcceptanceTimestampBatch, HandlePropagationFailure   # E3/E6
ValidateCandidate                  (leaf)   # E1/E2 canonical predicate
AcceptanceTimestampBatch           → ValidateCandidate, ValidBlockAccept, HandlePropagationFailure  # E3
ValidBlockAccept                   → CloseRoundAssignments
HandlePropagationFailure           → SecurityFloorEvaluate             # E3 (new)
CloseRoundAssignments              → EnterLowPowerListen               # E7
CloseTemplateAssignments           → EnterLowPowerListen               # E8 (new)
FullRangeExhaustNoSolution         → TemplateRefresh, RoundAbort
TemplateRefresh                    → CloseTemplateAssignments, TemplateCommit, WakeComplete  # E8
RoundAbort                         → CloseRoundAssignments
```

## Scheduled-event edges (SCHEDULE event)

```
ScheduleSolutionPropagation ⇒ CertificateArrival, BlockAcceptancePoint   # carry (certificate, snapshot)
HandlePropagationFailure    ⇒ ResumeFromPause                            # per PATH-B paused miner (E3)
```

## Required-property proofs

1. **The discovery snapshot flows to every validation site (E1/E2).** `ActiveHashing →
   CreateSolutionEligibilitySnapshot` produces `snapshot`; `EarlyStopGenerate` binds it into the
   signed certificate; `ScheduleSolutionPropagation ⇒ CertificateArrival(…, certificate, snapshot)`
   and `⇒ BlockAcceptancePoint(…, certificate, snapshot, outcome)`. The three validators
   `SelfValidateFoundSolution`, `EarlyStopVerify`, and `AcceptanceTimestampBatch` all call the
   single `ValidateCandidate(RoundContext, certificate, snapshot)`. No validator requires the
   finder's assignment to be CURRENT at arrival.
2. **Every non-acceptance outcome resumes paused miners (E3).** `BlockAcceptancePoint`'s non-accept
   branch and `AcceptanceTimestampBatch`'s empty-valid branch both `→ HandlePropagationFailure`,
   which `⇒ ResumeFromPause` for each PATH-B paused miner. No other exit from the acceptance cluster
   leaves paused miners without a scheduled resume.
3. **Acceptance funnels through arbitration, once (E6).** `BlockAcceptancePoint(ACCEPTED_CANDIDATE)
   → AcceptanceTimestampBatch → {ValidateCandidate*, ValidBlockAccept → CloseRoundAssignments}`.
   `ValidBlockAccept` performs the single `SOLUTION_PROPAGATION → ROUND_ACCEPTED` transition; only
   `AcceptanceTimestampBatch` calls it.
4. **Every activation reaches WAKING (D2, preserved after E4/E5/E8).** `RangeAssign`,
   `ReserveActivate` (E4), `RangeReassign`, and `TemplateRefresh` create a PENDING assignment and
   reach `ACTIVE_HASHING` only through `WakeComplete` (T5). There is no `ACTIVE_HASHING →
   ACTIVE_HASHING` self-loop (T6 removed, E5); `ResumeFromPause` also passes through `WAKING`.
5. **Every round closure reaches CloseRoundAssignments (E7).** The only closure callers are
   `ValidBlockAccept` (ROUND_ACCEPTED) and `RoundAbort` (ROUND_ABORTED); both `→
   CloseRoundAssignments`, which has an explicit action for every holder state.
6. **Template refresh never bypasses TEMPLATE_COMMITMENT (E8).** `TemplateRefresh →
   CloseTemplateAssignments` (old-template closure), then `→ TemplateCommit` — invoked only after the
   round is in `TEMPLATE_COMMITMENT`; re-activation uses legal per-state edges into `WAKING`, and the
   procedure ends with an explicit `ASSIGNMENT → HASHING`.
7. **`TemplateCommit` is called only from `TEMPLATE_COMMITMENT`.** Its callers are `RoundInitialise`'s
   successor (round in `TEMPLATE_COMMITMENT`) and `TemplateRefresh`, which transitions
   `TEMPLATE_REFRESH → TEMPLATE_COMMITMENT` immediately before the call.
8. **Renewal is a leaf in-state operation (E9).** `LeaseExpiry`'s renewal branch calls nothing and
   changes no state; only the expiry-without-renewal branch `→ EnterLowPowerListen, RangeReassign`.

## Result

**PROCEDURE CALL GRAPH (Stage 1E): PASS** — all eight required reachability properties hold; the
three new procedures are reachable and correctly wired; no orphaned or dangling call remains.
