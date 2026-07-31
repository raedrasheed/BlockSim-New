# Stage 1F — Concurrency Audit (F1–F3, F8)

Audits the concurrency correctness of the corrected specification: candidate isolation, scoped
failure/resume, active-set round-state, and race determinism. Verified by procedure-call-graph and
event-envelope analysis over `STAGE_01_PROTOCOL_PSEUDOCODE.md` (§0, §16b–§16e, §21), not string
search alone.

## Concurrency properties

| # | Property | Result |
|--:|----------|--------|
| 1 | Every candidate has a unique propagation context | **PASS** — `CreatePropagationContext` mints immutable unique `CandidateID`/`PropagationID`; each discovery gets its own CPC added to `active_propagation_set` (F1) |
| 2 | Every propagation event is candidate-scoped | **PASS** — `CertificateArrival`, `BlockAcceptancePoint`, `ResumeFromPause`, and all cancellations carry `CandidateID`/`PropagationID` (§0.2); no event is keyed by `RoundID` alone |
| 3 | Failure handling is candidate-scoped | **PASS** — `HandlePropagationFailure(CandidateID)` fails only `cpc`, removes only it from the set, cancels only its events, resumes only miners with matching `pause_cause_candidate_id` (F2) |
| 4 | One candidate's failure cannot cancel/resume another candidate's state | **PASS** — the failure handler iterates only `pause_cause_candidate_id = CandidateID` miners and only `certificate_arrival_events(cpc)` / `block_arrival_event(cpc)`; a miner paused by another live candidate is left unchanged (TV28/TV29) |
| 5 | A miner has at most one pause cause | **PASS** — `EarlyStopVerify` runs only when `ACTIVE_HASHING`; a paused miner ignores further `CertificateArrival`s, so `pause_cause_candidate_id` is unambiguous (multi-candidate policy) |
| 6 | SOLUTION_PROPAGATION persists while any live candidate exists | **PASS** — round `= SOLUTION_PROPAGATION` iff `active_propagation_set` non-empty (or batch/acceptance event live); `HandlePropagationFailure` returns to HASHING only when `propagation_quiescent` (F3, TV28/TV38) |
| 7 | Acceptance closes the round exactly once | **PASS** — `ValidBlockAccept` guards "already accepted?", marks other live contexts COMPETING/STALE/CANCELLED, cancels their events, clears the set, and transitions once to ROUND_ACCEPTED (TV30) |
| 8 | Same-timestamp races are deterministic | **PASS** — inter-type priority table + `(CandidateID, MinerID, AssignmentID, seq)` tie-break; independent of iteration order (F8; `STAGE_01F_EVENT_PRIORITY_TABLE.md`; TV36/TV37) |
| 9 | No acceptance/activation into a closed round | **PASS** — closures (priority 1–2) precede block arrival (6) and wake completion (12); stale-candidate guards and the WAKING→OFFLINE closure edge absorb the rest (TV37) |
| 10 | No paused miner is stranded | **PASS** — every non-acceptance outcome routes to `HandlePropagationFailure`, which schedules `ResumeFromPause` for each matching paused miner; accepted rounds close paused miners via `CloseRoundAssignments` (F2/F3) |

## Candidate-isolation call-graph facts

- `active_propagation_set` is written only by `ScheduleSolutionPropagation` (add), `HandlePropagationFailure`
  (remove one), and `ValidBlockAccept` (clear on acceptance). No other writer exists.
- `pause_cause_candidate_id` is written only by `EnterLowPowerListen` (VALID_SOLUTION_VERIFIED case)
  and cleared only by `ResumeFromPause`. No other writer.
- Cross-candidate cancellation occurs in exactly one place: `ValidBlockAccept` (acceptance). Failure
  cancellation is single-candidate only.

## Result

**CONCURRENCY AUDIT: PASS.** Candidates are isolated (F1), failure/resume is candidate-scoped (F2),
the round-state follows the active set with a single closure (F3), and all same-timestamp races are
deterministic and iteration-order-independent (F8).
