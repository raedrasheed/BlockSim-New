# Stage 1E — Propagation-Failure Audit (E3/E6)

Verifies that EVERY non-acceptance propagation outcome resumes every PATH-B paused miner through the
single `HandlePropagationFailure` handler, and that entry to / exit from `SOLUTION_PROPAGATION` is
event-ordered and correct. Verified by procedure-call-graph analysis over
`STAGE_01_PROTOCOL_PSEUDOCODE.md`.

## 1. The four non-acceptance outcomes and their single handler

`HandlePropagationFailure(RoundContext, certificate, snapshot, failure_reason)` accepts exactly
`failure_reason ∈ {REJECTED, BLOCK_UNAVAILABLE, PROPAGATION_TIMEOUT, NO_VALID_CANDIDATE}`.

| Source | Outcome routed to handler |
|--------|---------------------------|
| `BlockAcceptancePoint` non-accept branch | `REJECTED`, `BLOCK_UNAVAILABLE`, `PROPAGATION_TIMEOUT` |
| `AcceptanceTimestampBatch` empty valid set | `NO_VALID_CANDIDATE` |

**Property P1 — no non-acceptance outcome bypasses the handler.** `BlockAcceptancePoint`'s only two
branches are `ACCEPTED_CANDIDATE → AcceptanceTimestampBatch` and `else → HandlePropagationFailure`.
`AcceptanceTimestampBatch`'s only exits are `ValidBlockAccept(winner)` (valid set non-empty) and
`HandlePropagationFailure(NO_VALID_CANDIDATE)` (valid set empty). No other exit exists. **PASS.**

## 2. Handler effects

`HandlePropagationFailure`:
1. records `propagation_failure(RoundID, TemplateID, certificate, failure_reason)`;
2. `SecurityFloorEvaluate`: if breach ⇒ `SECURITY_RECOVERY`; else if `round_state =
   SOLUTION_PROPAGATION` ⇒ `SOLUTION_PROPAGATION → HASHING` (E6, R7), else ensure HASHING;
3. cancels pending `CertificateArrival`/`BlockAcceptancePoint` events carrying this certificate;
4. `FOR EACH` miner `M` with a PAUSED assignment AND `entry_stop_reason(M) = VALID_SOLUTION_VERIFIED`
   ⇒ `SCHEDULE ResumeFromPause(M, trigger = failure_reason)`;
5. never accepts a block and never closes the round.

**Property P2 — no paused miner is stranded.** Step 4 enumerates EVERY PATH-B paused miner (the
finder and any recipient that verified the certificate). `ResumeFromPause` restores the assignment to
CURRENT from its retained `actual_frontier`, charges wake + transition energy (I5/I6), transitions
`LOW_POWER_LISTEN → WAKING → ACTIVE_HASHING` (T30 → T5), and calls `ActiveHashRateUpdate` to
recompute `H_active/H_honest/H_adversarial/q_adv` (I17). **PASS.** (Exercised by TV21.)

**Property P3 — round returns to a hashing-capable state.** After the handler, `round_state ∈
{HASHING, SECURITY_RECOVERY}`; in both, `ActiveHashing` is permitted (E6), so resumed miners can
continue searching. **PASS.**

**Property P4 — obsolete events cannot fire.** Step 3 cancels the failed certificate's
`CertificateArrival`/`BlockAcceptancePoint` events, so no stale acceptance can occur for a
certificate that already failed. **PASS.**

**Property P5 — a PATH-A exhausted range is never resumed.** `ResumeFromPause` applies ONLY to
`entry_stop_reason = VALID_SOLUTION_VERIFIED`; a `RANGE_EXHAUSTED` (searched/completed) range is not
enumerated by step 4 and its `NOTE` forbids resume. **PASS.**

## 3. SOLUTION_PROPAGATION entry/exit (E6)

| # | Property | Result |
|--:|----------|--------|
| 1 | Entry at the FIRST found solution, not after acceptance | **PASS** — `ScheduleSolutionPropagation` performs `HASHING → SOLUTION_PROPAGATION` (R5); `ValidBlockAccept` performs no entry transition |
| 2 | Unpaused miners keep hashing during SOLUTION_PROPAGATION | **PASS** — `ActiveHashing` admits `round_state ∈ {HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY}` |
| 3 | Further candidates may be scheduled | **PASS** — a second `ScheduleSolutionPropagation` no-ops the entry (already SOLUTION_PROPAGATION) and schedules another arrival/acceptance pair |
| 4 | Rejection/timeout ⇒ SOLUTION_PROPAGATION → HASHING or SECURITY_RECOVERY | **PASS** — `HandlePropagationFailure` step 2 (R7/R8) |
| 5 | Accepted arbitration ⇒ single SOLUTION_PROPAGATION → ROUND_ACCEPTED | **PASS** — `ValidBlockAccept` transitions once (R6); no double `HASHING → SOLUTION_PROPAGATION` |
| 6 | No acceptance at solution-discovery | **PASS** — `ActiveHashing`/`ScheduleSolutionPropagation` never call `ValidBlockAccept`/`AcceptanceTimestampBatch` |

## 4. Event ordering (carried from D5/D6)

Earliest full-block arrival wins by discrete-event queue order; EXACT-timestamp ties are batched and
arbitrated by `AcceptanceTimestampBatch` (`candidate_hash`, then `MinerID`); no event inspects
unknown future timestamps; no round closure precedes arbitration. Unchanged by Stage 1E except that
the empty-batch case now routes to `HandlePropagationFailure` (E3). **PASS.**

## Result

**PROPAGATION-FAILURE AUDIT: PASS.** Every non-acceptance outcome — including an empty valid batch —
funnels through the single `HandlePropagationFailure`, which resumes every PATH-B paused miner,
cancels obsolete candidate events, and returns the round to a hashing-capable state; and
`SOLUTION_PROPAGATION` is a real round state entered at propagation start with continued hashing
(E3/E6).
