# Stage 1C — Event-Order Audit

Verifies C6 (event-ordered solution propagation and the modeled acceptance point) across the
pseudocode and the round/early-stop documents.

## Event sequence (C6 steps 1–13)

| Step | Requirement | Where | Status |
|-----:|-------------|-------|--------|
| 1 | A valid candidate is found | `ActiveHashing` (hit branch) | PASS |
| 2 | Construct early-stop certificate | `EarlyStopGenerate` | PASS |
| 3 | Schedule per-recipient certificate-arrival events (modeled delays) | `ScheduleSolutionPropagation` | PASS |
| 4 | Schedule full-block propagation/arrival events | `ScheduleSolutionPropagation` → `BlockAcceptancePoint` | PASS |
| 5 | Finder ceases hashing; block-propagation energy accounted | `ScheduleSolutionPropagation` (`EnterLowPowerListen(VALID_SOLUTION_VERIFIED)`) | PASS |
| 6 | Recipient stays `ACTIVE_HASHING` until its certificate-arrival event validates | `CertificateArrival` → `EarlyStopVerify` | PASS |
| 7 | On success recipient → `LOW_POWER_LISTEN`, `VALID_SOLUTION_VERIFIED`, PAUSED | `EarlyStopVerify` | PASS |
| 8 | Block acceptance only at the modeled acceptance point after full block arrives+validates | `BlockAcceptancePoint` → `ValidBlockAccept` | PASS |
| 9 | The discrete-event queue establishes earliest arrival | `ValidBlockAccept` (first accept wins; later → competing) | PASS |
| 10 | Only exactly-equal acceptance timestamps break by `candidate_hash` then `MinerID` | `ValidBlockAccept` | PASS |
| 11 | Competing proposals become stale/competing records | `ValidBlockAccept` (`competing_valid`) | PASS |
| 12 | On rejection/timeout, paused miners wake and resume | `ResumeFromPause` | PASS |
| 13 | On acceptance, round closure closes remaining assignments without labeling them exhausted | `ValidBlockAccept` closure loop (`stop_reason = ROUND_ACCEPTED`) | PASS |

## Modeled acceptance point
Defined explicitly as **either** a designated coordinator/validator **or** a clearly
identified canonical local view (`RoundContext.acceptance_point_policy`) — `BlockAcceptancePoint`
and PROTOCOL_SCOPE §A.6 / ROUND_STATE_MACHINE §2.6.

## Prohibited patterns absent
- `ActiveHashing` does **not** call `ValidBlockAccept` on a hit (it calls
  `ScheduleSolutionPropagation`) — PASS.
- `ROUND_ACCEPTED` is **not** set at solution-discovery time (only in `ValidBlockAccept`, invoked
  from `BlockAcceptancePoint`) — PASS.
- No **global set of future solutions** is scanned to choose the earliest; ordering is the
  discrete-event queue — PASS.
- No new randomness: modeled propagation delays are deterministic/reproducible — PASS.

## Result
**EVENT-ORDER AUDIT: PASS** — solution propagation is event-scheduled; acceptance occurs only
at the modeled acceptance point; earliest arrival is the queue order; no chain-wide fork-choice
proof is claimed.
