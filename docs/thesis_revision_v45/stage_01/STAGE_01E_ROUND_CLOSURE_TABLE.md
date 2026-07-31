# Stage 1E — Round-Closure State Table (E7)

The deterministic per-holder-state action table for `CloseRoundAssignments`
(`STAGE_01_PROTOCOL_PSEUDOCODE.md` §17a). `RoundAbort` (`disposition = ROUND_ABORTED`) and
accepted-block closure via `ValidBlockAccept` (`disposition = ROUND_ACCEPTED`) use the SAME table.

`round_closure_disposition` (how the ROUND ended) is recorded on the assignment SEPARATELY from
`entry_stop_reason` (why the miner earlier LEFT `ACTIVE_HASHING`). Closure NEVER overwrites an
existing `RANGE_EXHAUSTED` or `VALID_SOLUTION_VERIFIED` entry reason. There is no "update state
consistently" wording — every holder state has an explicit five-column action.

`disposition ∈ {ROUND_ACCEPTED, ROUND_ABORTED}`; below, "disposition" denotes whichever the closer
passed.

| Holder state at closure | Resulting miner state | Assignment status | Event cancellation | Energy boundary | Coverage / custody effect |
|-------------------------|-----------------------|-------------------|--------------------|-----------------|---------------------------|
| `ACTIVE_HASHING` | `LOW_POWER_LISTEN` (via `EnterLowPowerListen(disposition)`; T28/T29) | CLOSED (round-ended) | its pending wake/resume/cert/BlockAcceptancePoint events cancelled at end of pass | end `P_hash`, begin `P_listen`; one-shot `E_coordination` | range NOT marked exhausted/searched; `entry_stop_reason <- disposition` (had none); coverage preserved |
| `EXHAUSTED_PENDING` | `LOW_POWER_LISTEN` (T8 completion) | CLOSED (round-ended) | pending confirm/redeploy events cancelled | end `P_hash` transient, begin `P_listen`; one-shot `E_coordination` | completed range stays `coverage_state=searched`, `custody_status=completed`; `entry_stop_reason=RANGE_EXHAUSTED` PRESERVED |
| `LOW_POWER_LISTEN` | `LOW_POWER_LISTEN` (unchanged) | CLOSED (round-ended) | pending resume/wake events for this holder cancelled | continue `P_listen` to closure time | PATH-B PAUSED assignment closed, NOT resumed; `entry_stop_reason` (VALID_SOLUTION_VERIFIED / RANGE_EXHAUSTED / ASSIGNMENT_REVOKED) PRESERVED |
| `WAKING` | `LOW_POWER_LISTEN` | CLOSED (bound PENDING un-activated) | its pending `WakeComplete` cancelled | end `P_wake`, begin `P_listen`; wake energy already accrued is retained (I5/I6) | bound range released (not activated); no `entry_stop_reason` forced onto the range |
| `REGISTERED` | `REGISTERED` (unchanged) | CLOSED if a bound PENDING exists, else none | any bound-PENDING wake cancelled | continue `P_registered` (= `P_listen`) | holds no CURRENT range under this round; no coverage change |
| `RESERVE` | `RESERVE` (unchanged) | CLOSED if a bound PENDING exists, else none | any bound-PENDING activation cancelled | continue `P_reserve` (= `P_listen`) | holds no CURRENT range; no coverage change |
| `OFFLINE` | `OFFLINE` (unchanged) | CLOSED (record only) | none held | continue `P_offline` | not participating; no coverage change |
| `DISQUALIFIED` | `DISQUALIFIED` (unchanged, absorbing) | CLOSED (record only) | none held | continue `P_offline` | not participating; no coverage change |

After the per-assignment pass, `CloseRoundAssignments` cancels ALL pending
wake/resume/certificate-arrival/BlockAcceptancePoint events for the closed `RoundID`, records
`round_closure(RoundID, TemplateID, disposition)`, and finalises state durations and energy to the
EXACT closure time (I5, I6, I7).

## Determinism and invariant checks

| # | Property | Result |
|--:|----------|--------|
| 1 | Every one of the eight holder states has an explicit action | **PASS** — all eight rows above; no default/"consistently" branch |
| 2 | `entry_stop_reason` never overwritten by closure | **PASS** — only the ACTIVE_HASHING holder (which had none) gets `disposition` as its entry reason; all others PRESERVE it and record only `round_closure_disposition` |
| 3 | RoundAbort and accepted-block closure use the same table | **PASS** — both call `CloseRoundAssignments`; the only difference is the `disposition` argument |
| 4 | No range marked exhausted by closure | **PASS** — no row sets `coverage_state=searched` except the already-searched EXHAUSTED_PENDING/completed range, whose status pre-existed |
| 5 | Durations/energy reconcile to horizon T | **PASS** — final "finalise … to the EXACT closure time" (I5/I6/I7) |
| 6 | Pending events cannot fire after closure | **PASS** — all pending round events cancelled |

**ROUND-CLOSURE TABLE (E7): PASS** — deterministic for every miner state; `entry_stop_reason` and
`round_closure_disposition` are separate; the two closers share one table. (Exercised by TV25.)
