# Stage 1C — Pseudocode Conformance Audit

Procedure-by-procedure comparison of `STAGE_01_PROTOCOL_PSEUDOCODE.md` against the accepted
B1–B9 rules and the C1–C10 consolidation rules. This is a semantic comparison of the actual
procedures, not a string search.

| Procedure | Rule(s) | Conformance |
|-----------|---------|-------------|
| `ActiveHashing` | B1, C6 | On a hit, builds the found solution, calls `EarlyStopGenerate`, then `ScheduleSolutionPropagation` — **does not** call `ValidBlockAccept`; no acceptance at discovery. **PASS** |
| `RangeExhaust` | B4, C2, C3, C8 | Order: preserve ground truth → record reported claim → adjudicate (honest ground-truth or modeled audit) → set `accepted_frontier/coverage=searched/custody=completed` and transition to `EXHAUSTED_PENDING` **only** on ACCEPTED; on REJECTED no transition, coverage preserved, false-exhaustion recorded via the audit model (not I11). **PASS** |
| `EnterLowPowerListen` | B1, B2, C1 | Five reason-specific dispositions (`RANGE_EXHAUSTED`, `ASSIGNMENT_REVOKED`, `VALID_SOLUTION_VERIFIED`, `ROUND_ACCEPTED`/`ROUND_ABORTED`); no generic "release held range"; PATH-B pauses (no coverage change), PATH-A closes completed (no release/reassign), revoke frees only the accepted unsearched suffix. **PASS** |
| `ActiveHashRateUpdate` | B6, C7 | Samples only which adversarial miners are active, derives `H_honest/H_adversarial/H_active` deterministically, sets `q_adv` or `NA`; records **no** breach and triggers **no** recovery. **PASS** |
| `SecurityFloorEvaluate` | B6, C7 | Sole owner of breach recording/recovery; `H_active==0` → active+honest floor breaches, `q_adv=NA` never compared; `RECORD_ONCE` suppresses duplicates; I17 retained. **PASS** |
| `LeaseExpiry` | C4 | Renew, else reassign only `[accepted_frontier+1, range_end]`; whole range only if no accepted positions; nothing to reassign if `accepted_frontier=range_end`. **PASS** |
| `RangeReassign` | B5, C4 | Receives the exact accepted unsearched suffix; asserts not-completed, not-searched, no accepted prefix included; permitted reasons only (no exhaustion); I8a uses accepted coverage. **PASS** |
| `ProgressCommit` | C3 | Updates `reported_searched` only; explicitly **must not** update the I8a accepted measure; distinguishes `actual_*` / `reported_*`. **PASS** |
| `EarlyStopGenerate` | B7, CR1 | Generates only from a found valid solution; exact 8 fields; not from coverage/frontier/exhaustion. **PASS** |
| `EarlyStopVerify` | B1, B2, C6 | Verifier stays `ACTIVE_HASHING`, `E_verification` separate; on all-steps-pass → PAUSE and `ACTIVE_HASHING → LOW_POWER_LISTEN` directly (`VALID_SOLUTION_VERIFIED`), never via `EXHAUSTED_PENDING`; failure → no transition (I11). **PASS** |
| `ScheduleSolutionPropagation` (new) | C6 | Schedules per-recipient `CertificateArrival` + `BlockAcceptancePoint` via modeled delays; finder pauses; no acceptance here; no global future set. **PASS** |
| `CertificateArrival` (new) | C6 | Recipient stays `ACTIVE_HASHING` until its arrival event validates; success → pause; failure → no change. **PASS** |
| `BlockAcceptancePoint` (new) | C6 | Modeled acceptance point (coordinator/validator or canonical local view); the only caller of `ValidBlockAccept`. **PASS** |
| `ValidBlockAccept` | B9, C6 | Invoked only from `BlockAcceptancePoint`; earliest arrival = discrete-event queue order; exact-timestamp ties → `candidate_hash` then `MinerID`; later arrivals → competing/stale; on accept, `ROUND_ACCEPTED` closes remaining/paused assignments without marking exhausted. **PASS** |
| `FullRangeExhaustNoSolution` | C9 | `ROUND_EXHAUSTED` only when accepted_searched = whole domain **and** no `active_unsearched`/`inactive_unsearched` remain; adversarial claims need a defined adjudication outcome; modeled acceptance, not proof. **PASS** |
| `TemplateRefresh` | C5 | Closes old-`TemplateID` assignments, preserves history, mints fresh `TemplateID`, creates new **original** assignments with `previous_assignment_reference=null`; no `RangeReassign` of old ranges; difficulty fixed. **PASS** |
| `RoundAbort` | I5/I6/I7/I14/I15/I16 | Retains breaches, reconciles energy/durations, retains zero-block/NA. **PASS** |

## Sampling discipline
The only `[SIMULATION SAMPLING]` steps remain: (1) target-hit in `ActiveHashing`; (2) which
adversarial miners are active in `ActiveHashRateUpdate` (states only); (3) wake latency in
`WakeComplete`/`ResumeFromPause`; (4) audit selection in `RangeExhaust`/
`FullRangeExhaustNoSolution`. Modeled propagation delays are deterministic/reproducible (not
sampling). No new randomness was introduced by C6.

## Result
**PSEUDOCODE CONFORMANCE: PASS** — every procedure conforms to B1–B9 and C1–C10.
