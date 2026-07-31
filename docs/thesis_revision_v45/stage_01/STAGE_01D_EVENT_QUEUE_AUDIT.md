# Stage 1D — Event-Queue Audit

Verifies the discrete-event ordering of solution propagation, acceptance, and resume (C6, D5,
D6) against the corrected pseudocode.

## Scheduled events

| Event | Scheduled by | Handler | Ordering basis |
|-------|--------------|---------|----------------|
| `CertificateArrival(r)` | `ScheduleSolutionPropagation` | `CertificateArrival` → `EarlyStopVerify` | per-recipient modeled delay (deterministic, reproducible) |
| `BlockAcceptancePoint(outcome)` | `ScheduleSolutionPropagation` | `BlockAcceptancePoint` | full-block modeled delay to the acceptance point |
| `ResumeFromPause(M)` | `BlockAcceptancePoint` (REJECTED/UNAVAIL/TIMEOUT) | `ResumeFromPause` | scheduled on non-acceptance |

## Ordering properties

| # | Property | Result |
|--:|----------|--------|
| 1 | Acceptance never occurs at solution discovery | **PASS** — `ActiveHashing` calls `ScheduleSolutionPropagation`, never `ValidBlockAccept`/`AcceptanceTimestampBatch` |
| 2 | Earliest arrival is the discrete-event queue order | **PASS** — a strictly-earlier `BlockAcceptancePoint` fires first; `ValidBlockAccept` records "already accepted" for later arrivals → competing |
| 3 | Exact-timestamp ties are batched before acceptance | **PASS** — `BlockAcceptancePoint(ACCEPTED_CANDIDATE)` → `AcceptanceTimestampBatch(now)` gathers all same-timestamp candidates, validates all, arbitrates, then accepts |
| 4 | No event inspects unknown future timestamps | **PASS** — arbitration is scoped to the current timestamp batch; no global future-solution set is scanned |
| 5 | No round closure before same-timestamp arbitration | **PASS** — `AcceptanceTimestampBatch` calls `ValidBlockAccept` (→ `CloseRoundAssignments`) only after arbitration completes |
| 6 | Rejection/timeout schedules resume for every paused miner | **PASS** — `BlockAcceptancePoint` non-accept branch ⇒ `ResumeFromPause` per PAUSED `VALID_SOLUTION_VERIFIED` miner |
| 7 | Resume restores CURRENT and recomputes hash rates | **PASS** — `ResumeFromPause` restores assignment CURRENT from `actual_frontier` and calls `ActiveHashRateUpdate` |
| 8 | Round closure cancels pending events | **PASS** — `CloseRoundAssignments` cancels pending wake/resume/certificate-arrival/`BlockAcceptancePoint` events for the closed RoundID |
| 9 | Randomness confined to labelled draws | **PASS** — propagation delays are deterministic/reproducible; the only `[SIMULATION SAMPLING]` steps are target-hit, adversarial active-census, wake latency, and audit selection |

## Result
**EVENT-QUEUE AUDIT: PASS** — propagation, acceptance (with same-timestamp arbitration), and
rejection-driven resume are event-scheduled and correctly ordered; no acceptance-at-discovery,
no future-timestamp inspection, and no closure before arbitration.
