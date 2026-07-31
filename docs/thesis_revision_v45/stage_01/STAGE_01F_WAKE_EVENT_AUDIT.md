# Stage 1F — Wake-Event Audit (F5)

Verifies that all wake completion is event-scheduled and non-blocking, and that concurrent wakes
complete independently. Verified over `STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.10 and the five
activation callers.

## 1. The StartWake / WakeCompleteEvent split

| Procedure | Behaviour |
|-----------|-----------|
| `StartWake(MinerID, target_assignment, from_state)` | applies `from_state → WAKING` via `ApplyMinerStateTransition`; draws `wake_latency`; begins `P_wake`; SCHEDULEs `WakeCompleteEvent AT now + wake_latency`; **returns immediately** to the event loop |
| `WakeCompleteEvent(MinerID, target_assignment)` | fires at its OWN completion timestamp; on success validates the assignment, applies `WAKING → ACTIVE_HASHING` (T5, PENDING/PAUSED→CURRENT) via the hook, begins hashing; on wake-deadline expiry applies `WAKING → OFFLINE` (T12) and releases the range |

The former synchronous `WakeComplete` is REMOVED (§11 note); no procedure performs a blocking wake.

## 2. Properties

| # | Property | Result |
|--:|----------|--------|
| 1 | No blocking wake anywhere | **PASS** — `grep` shows zero `CALL WakeComplete(`; the only wake construct is `StartWake` (schedules) + `WakeCompleteEvent` (handler) |
| 2 | All five activation callers use StartWake | **PASS** — `RangeAssign`, `ReserveActivate`, `RangeReassign`, `TemplateRefresh`, `ResumeFromPause` each `CALL StartWake` (5 sites) and none call a synchronous wake |
| 3 | Wake residency accrues per miner at its own timestamps | **PASS** — `ApplyMinerStateTransition` closes/opens residency intervals at each transition's `event_time`; `P_wake·wake_latency` is charged for the WAKING interval bounded by `StartWake` (entry) and `WakeCompleteEvent` (exit) (I5/I6) |
| 4 | Concurrent wakes complete independently, not serially | **PASS** — N miners calling `StartWake` at `t0` schedule N independent `WakeCompleteEvent`s at `t0 + L_i`; each returns immediately, so no wake occupies the loop while another waits (TV33) |
| 5 | Activation into ACTIVE_HASHING routes through the hook (I17) | **PASS** — `WakeCompleteEvent` success calls `ApplyMinerStateTransition(WAKING → ACTIVE_HASHING)`, which recomputes `H_active`/I17 at that boundary (F6) |
| 6 | Wake failure yields no CURRENT assignment | **PASS** — the deadline-expiry branch applies `WAKING → OFFLINE` (T12), marks the range `inactive_unsearched`, sets `custody_status = abandoned`, and closes the PENDING assignment; no PENDING→CURRENT occurs (E4/F5) |
| 7 | No activation into a closed round | **PASS** — at round closure `CloseRoundAssignments` cancels the pending `WakeCompleteEvent` and applies `WAKING → OFFLINE` (T12); the event-priority table processes closure (2) before wake completion (12) (TV37, F8) |
| 8 | Resume is also event-scheduled | **PASS** — `ResumeFromPause` calls `StartWake(from_state = LOW_POWER_LISTEN)` (T30); the resumed PAUSED assignment is restored to CURRENT at its `WakeCompleteEvent` |

## 3. Ordering note

Because `TemplateRefresh` calls `StartWake` (non-blocking) for each eligible miner and then performs
`ASSIGNMENT → HASHING`, the round reaches `HASHING` at `now` while each miner reaches
`ACTIVE_HASHING` at its later `WakeCompleteEvent` (`now + L_i > now`). This preserves §3.2 (no miner
is `ACTIVE_HASHING` before the round is `HASHING`) under concurrency.

## Result

**WAKE-EVENT AUDIT: PASS.** Wake completion is fully event-scheduled and non-blocking; the five
activation paths use `StartWake`; concurrent wakes are independent; activation routes through the
central hook and never enters a closed round. (Exercised by TV33, TV37.)
