# Stage 1F — Global Event-Priority Table (F8)

The deterministic order in which same-timestamp events are processed by the single discrete-event
loop (`STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.1, §21). This document is normative for F8. The order is
reproducible across reruns and **independent of any data-structure iteration order**.

## 1. Inter-type priority (highest first)

When two or more events carry the EXACT same `event_time`, they fire in this fixed order. The
rationale column states WHY a higher-priority event must precede lower ones so that no event ever
acts on a round/miner/candidate/assignment a higher-priority same-timestamp event has invalidated.

| Prio | Event type | Procedure | Rationale for its rank |
|-----:|-----------|-----------|------------------------|
| 1 | Round abort closure | `RoundAbort → CloseRoundAssignments(ROUND_ABORTED)` | A terminal-abort must settle the round before anything else acts on it; nothing may run against an aborting round. |
| 2 | Round acceptance closure | `ValidBlockAccept → ROUND_ACCEPTED → CloseRoundAssignments` | Once a block is accepted the round is closing; later same-timestamp events must see it closed (prevents activation/acceptance into a closed round). |
| 3 | Same-timestamp acceptance arbitration | `AcceptanceTimestampBatch` | Must gather and arbitrate ALL exact-timestamp ACCEPTED candidates before any single acceptance closes the round (D6). |
| 4 | Template invalidation / refresh | `TemplateRefresh` / `CloseTemplateAssignments` | A template change discards the search domain; it must precede domain-dependent events (discovery, exhaustion) at the same instant. |
| 5 | Security-floor evaluation / breach | `SecurityFloorEvaluate` | A breach can force `SECURITY_RECOVERY`; it is resolved before non-closure propagation/mining events act at the same instant. |
| 6 | Full-block arrival (acceptance point) | `BlockAcceptancePoint` | Acceptance/failure of a candidate outranks new certificate arrivals and new discoveries at the same instant. |
| 7 | Certificate arrival (recipient) | `CertificateArrival → EarlyStopVerify` | A recipient pause is processed after block-level outcomes but before new discoveries. |
| 8 | Solution discovery | `ActiveHashing` hit → `ScheduleSolutionPropagation` | A new candidate is created after existing candidates' block/certificate events resolve at the same instant. |
| 9 | Range completion / exhaustion adjudication | `ActualRangeCompletion` / `ExhaustionAdjudicate` | PATH-A completion is processed after solution events; it changes coverage, not acceptance. |
| 10 | Reported exhaustion | `ReportedExhaustionClaim` | A reported claim (progress layer) ranks below actual completion. |
| 11 | Lease expiry | `LeaseExpiry` | Lease decisions act after discovery/exhaustion so a same-instant discovery is evaluated against the pre-expiry version (E1/I18). |
| 12 | Wake completion | `WakeCompleteEvent` | Activation into `ACTIVE_HASHING` is processed after any same-timestamp closure/refresh, so a miner never wakes into a closed/refreshed round. |
| 13 | Resume from pause | `ResumeFromPause` (→ `StartWake`) | Resume is scheduled by a candidate failure; it ranks just below a fresh wake completion. |
| 14 | Periodic monitoring | `ActiveHashRateUpdate` / heartbeat | The lowest-priority periodic census/among-boundary sampler; it never overrides a structural event at the same instant. |

## 2. Intra-type tie-break

Two events of the SAME type at the SAME timestamp are ordered lexicographically by

    (CandidateID, MinerID, AssignmentID, seq)

where any absent key sorts as the empty/least value and `seq` is the strictly monotonic
event-envelope creation counter (§0.2). Acceptance arbitration additionally applies the value
tie-break `candidate_hash` then `MinerID` (D6) among validated candidates. No comparison ever reads
hash-map / set iteration order, so the total order is identical on every rerun.

## 3. Per-pair resolution of the required races (F8)

| Race (same timestamp) | Winner (processed first) | Resulting behaviour |
|-----------------------|--------------------------|---------------------|
| **Solution discovery vs lease expiry** | discovery (8) before lease expiry (11) | The discovery captures its `SolutionEligibilitySnapshot` against the version CURRENT at `t`; the subsequent lease expiry/renewal does not retroactively invalidate it (E1/I18). Deterministic. |
| **Certificate arrival vs round abort** | round abort (1) before certificate arrival (7) | `CloseRoundAssignments(ROUND_ABORTED)` runs first; `CertificateArrival` then finds its candidate no longer live (`status ∉ {PROPAGATING, PENDING_ACCEPTANCE}`) and returns `ignored_stale_candidate`. No pause into an aborted round. |
| **Wake completion vs round acceptance** | round acceptance (2) before wake completion (12) | `CloseRoundAssignments(ROUND_ACCEPTED)` cancels the pending `WakeCompleteEvent` and moves the WAKING miner to `OFFLINE` (T12); the wake slot is a no-op. No activation into a closed round (TV37). |
| **Full-block arrival vs template refresh** | template refresh (4) before full-block arrival (6) | `CloseTemplateAssignments` discards the old-template candidates; the block arrival then finds its candidate stale and returns `ignored_stale_candidate`. |
| **Valid solution vs range exhaustion (same timestamp, same/different miner)** | solution discovery (8) before range completion (9) | The valid solution's context is created first; PATH-A completion (coverage) is processed after. Acceptance of the solution (via its later block arrival) and exhaustion accounting never conflict because acceptance (2/3/6) outranks exhaustion (9). A miner is on exactly one path (CR-B1). |
| **Security-floor breach vs candidate acceptance** | acceptance closure (2) / arbitration (3) before floor evaluation (5) **only when acceptance is at the same instant**; otherwise floor evaluation (5) precedes block arrival (6) | If a block is accepted at `t`, the round closes at priority 2 and the same-`t` floor evaluation acts on the closed round (no recovery of a closed round). If NO acceptance occurs at `t`, floor evaluation (5) precedes block arrival (6), so a breach can move the round to `SECURITY_RECOVERY` before a non-accepting block-arrival is handled; `HandlePropagationFailure` then preserves live contexts (F3). |

## 4. Determinism properties

| # | Property | Result |
|--:|----------|--------|
| 1 | A total order exists on any same-timestamp event set | **PASS** — inter-type rank (1–14) then the `(CandidateID, MinerID, AssignmentID, seq)` lexicographic tie-break; `seq` is unique, so the order is total |
| 2 | Order is independent of data-structure iteration | **PASS** — every key is an intrinsic event field; no set/map traversal order is consulted |
| 3 | Order is identical across reruns | **PASS** — all keys are deterministic; `seq` is assigned in deterministic creation order |
| 4 | No event acts on state a higher-priority same-timestamp event invalidated | **PASS** — closures (1–2) and refresh (4) precede arrivals/discovery/wake; stale-candidate and cancelled-wake guards absorb the rest |
| 5 | Acceptance never precedes its arbitration | **PASS** — arbitration (3) is above block arrival (6) and `ValidBlockAccept` is reached only through `AcceptanceTimestampBatch` |

## Result

**EVENT-PRIORITY CONTRACT (F8): deterministic and complete** for the enumerated event types and all
six required races; reproducible across reruns; independent of iteration order. (Exercised by TV36,
TV37, TV38.)
