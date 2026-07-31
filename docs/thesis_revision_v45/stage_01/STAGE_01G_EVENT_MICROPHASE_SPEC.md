# Stage 1G — Event Microphase Specification (G5)

Normative specification for correction **G5** (timestamp microphase contract). This document is the
full contract referenced by `STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.7. It is documentation only; it
describes **PoCol** and claims no property beyond the structure defined here.

## 1. Motivation

At a single `event_time` many events may fire: full-block arrivals, certificate arrivals, discoveries,
lease expiries, closures, floor evaluations. Processing them in an arbitrary or data-structure-derived
order lets acceptance run before every same-timestamp block arrival has been seen, or lets a floor
evaluation reopen a round that a later-processed acceptance closed. G5 removes this by processing every
`event_time` in explicit **microphases**. The ordering guarantees two things: acceptance is causally
**downstream** of collecting ALL same-timestamp full-block arrivals at an acceptance point, and round
closure is **atomic** — it is the result of arbitration, not a separate event that races arbitration.

## 2. Microphase table (per `event_time`)

Microphases run in numeric order; every event at this timestamp is dispatched into exactly one phase.

| Phase | Runs | Why |
|-------|------|-----|
| **1** | Terminal abort / previously-committed closure: `RoundAbort` -> `CloseRoundAssignments(ROUND_ABORTED)`; an already-committed `ROUND_ACCEPTED` closure. | Settle the round first. A terminal disposition invalidates every downstream candidate, wake, and floor event at this timestamp. |
| **2** | Template invalidation/refresh: `TemplateRefresh` / `CloseTemplateAssignments`. | Discard the old search domain before any domain-dependent event, so arrivals bound to the discarded template find their candidate stale. |
| **3** | Collect ALL full-block arrivals at this timestamp. Each `BlockAcceptancePoint` ONLY registers into `acceptance_batch_registry[(timestamp, acceptance_point)]` (sets its context `PENDING_ACCEPTANCE`, records `acceptance_timestamp`) and returns. | It never accepts, arbitrates, or closes. Registration guarantees the batch is complete before arbitration begins. |
| **4** | Run `AcceptanceBatchFinalize` EXACTLY ONCE per `(timestamp, acceptance_point)`. | Single arbitration + closure point, causally downstream of phase 3. See below. |
| **5** | `SecurityFloorEvaluate` (SCHEDULED, terminal-guarded). | Returns `stale_noop` if the round is `ROUND_ACCEPTED`/`ROUND_ABORTED` or the `RoundID`/`TemplateID`/`state_version` is stale; it never reopens a terminal round (G10). Runs after any acceptance that closed the round this timestamp. |
| **6+** | Certificate arrivals; solution-discovery (`HashWorkEvent` hit); range completion; reported exhaustion; lease expiry; wake completion; resume; periodic monitoring. | Lower-priority structural and periodic events, processed after closures, refresh, acceptance, and floor evaluation have settled the round for this timestamp. |

**Phase 4 detail (`AcceptanceBatchFinalize`).** For the single `(timestamp, acceptance_point)`:

1. Validate every collected `ACCEPTED_CANDIDATE` arrival via `ValidateCandidate` against **each one's own
   discovery snapshot** (discovery-time eligibility, E1/E2/G1 — the assignment need not be `CURRENT` now).
2. Select the winner: smallest `candidate_hash`, then smallest `MinerID`.
3. `ValidBlockAccept` commits acceptance and closes the round **atomically** — sets `block_accepted`, marks
   every other live candidate `COMPETING`/`STALE`/`CANCELLED`, cancels their events, and performs a single
   transition to `ROUND_ACCEPTED`.
4. If no valid winner exists at this timestamp, fail each accepted-but-invalid candidate **candidate-scoped**
   (`NO_VALID_CANDIDATE`); each resumes only its own paused miners.
5. Then disposition the non-accept arrivals **candidate-scoped** — a no-op if the round has already closed
   in steps (2)–(3).

Round-acceptance closure is NOT an independent event preceding arbitration; it is the atomic result of
phase 4.

## 3. Intra-phase tie-break (G7)

Within a microphase, events of the same type break ties by

    (CandidateID, MinerID, AssignmentID, seq)

lexicographically. Acceptance arbitration additionally uses `candidate_hash`, then `MinerID`. Ties are
NEVER broken by hash-map / set iteration order (G7). `seq` is the strictly monotonic per-run creation
counter, assigned only after the deterministic key order is established, and is the final tie-break.

## 4. Solution-discovery vs same-time lease expiry (canonical rule)

**Single canonical rule: solution discovery is processed FIRST and captures its discovery snapshot BEFORE
the same-time lease expiry / renewal.** A discovery at `event_time` records its immutable
`SolutionEligibilitySnapshot` against the version that was `CURRENT` at that instant; a lease expiry or
renewal firing at the same `event_time` is ordered after it. By E1/I2/I18 the captured discovery stays
valid even if the assignment version is later superseded, paused, or renewed — the snapshot resolves to
the exact immutable version that was `CURRENT` at discovery, so acceptance remains verifiable afterward.

## 5. Required-race table (microphase-derived outcomes)

| Race (same `event_time`) | Microphase resolution | Outcome |
|--------------------------|-----------------------|---------|
| Certificate arrival vs round abort | Abort runs in phase 1, before certificate arrival (phase 6+). | Certificate finds its candidate `CANCELLED` / stale; no verification into an aborted round. |
| Wake completion vs round acceptance | Acceptance closes in phase 1/4; wake completion is phase 6+. | Wake finds the round closed; `WAKING -> OFFLINE` at closure (T12); no activation into a closed round. |
| Full-block arrival vs template refresh | Refresh runs in phase 2, before block collection (phase 3). | Block finds its candidate stale (bound to the discarded template); registration is ignored. |
| Two same-timestamp block arrivals | Both collected in phase 3; one `AcceptanceBatchFinalize` in phase 4. | One arbitration selects the winner; one atomic closure; the loser becomes `COMPETING`. |
| Security-floor breach vs candidate acceptance | Acceptance (phase 4) precedes floor evaluation (phase 5). | Floor `stale_noop`s on the now-closed round; no `SECURITY_RECOVERY` reopening. |
| Solution discovery vs lease expiry | Discovery first (§4). | Discovery captures its snapshot before the expiry/renewal; snapshot stays valid. |

## 6. Determinism properties (structural)

| Property | Structural basis | Status |
|----------|------------------|--------|
| A total order exists over same-timestamp events | Numbered microphases + `(CandidateID, MinerID, AssignmentID, seq)` tie-break | PASS |
| Independent of iteration order | Stable sorted keys, never data-structure iteration order (G7) | PASS |
| Reproducible across reruns | Deterministic identifiers and `seq` assignment (G7) | PASS |
| No acceptance before collection | Phase 3 collects ALL arrivals before phase 4 arbitrates | PASS |
| Single atomic closure | One `AcceptanceBatchFinalize` per `(timestamp, acceptance_point)`; `ValidBlockAccept` closes once (`block_accepted` guard) | PASS |

## 7. Result

**EVENT MICROPHASE SPEC (G5): deterministic and causally consistent.**

Exercised by TV43 and TV44 (and TV36 / TV37 historically). This contract supersedes the flat Stage-1F
priority table: `STAGE_01F_EVENT_PRIORITY_TABLE.md` remains a **frozen historical artifact** and is not
authoritative where it differs from the microphase contract defined here.
