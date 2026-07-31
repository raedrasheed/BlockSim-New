# Stage 1B — Semantic State-Path Audit

A semantic (not string-only) audit of the corrected miner state machine. It enumerates every
legal transition into and out of the four hashing-related states and proves the
valid-solution stop path (PATH B) and the range-exhaustion path (PATH A) never merge.
Transition IDs refer to `STAGE_01_MINER_STATE_MACHINE.md` §3 (T1–T30).

## Transition-reason enumeration

Every entry into `LOW_POWER_LISTEN` records exactly one `stop_reason` ∈
`{RANGE_EXHAUSTED, ASSIGNMENT_REVOKED, VALID_SOLUTION_VERIFIED, ROUND_ACCEPTED, ROUND_ABORTED}`
(invariant I4, amended).

## `ACTIVE_HASHING`

| Direction | Transition | Other endpoint | Reason / note |
|-----------|-----------|----------------|---------------|
| In | T5 | `WAKING` | RampComplete or PATH-B resume (start/continue `t_hash`) |
| — | ~~T6~~ | *(removed — E5)* | The `ACTIVE_HASHING → ACTIVE_HASHING` changed-range self-loop is **removed** (Stage 1E, E5). Acquiring a different range now closes the assignment and activates the new holder through `WAKING`; same-range lease renewal is a non-state-changing in-state operation, not a transition. |
| Out | **T7** | `EXHAUSTED_PENDING` | **PATH A**, `RANGE_EXHAUSTED` |
| Out | **T26** | `LOW_POWER_LISTEN` | **PATH B**, `VALID_SOLUTION_VERIFIED` (direct; assignment PAUSED) |
| Out | T27 | `LOW_POWER_LISTEN` | `ASSIGNMENT_REVOKED` (direct) |
| Out | T28 | `LOW_POWER_LISTEN` | `ROUND_ACCEPTED` (round ended) |
| Out | T29 | `LOW_POWER_LISTEN` | `ROUND_ABORTED` (round ended) |
| Out | T11 | `OFFLINE` | departure / heartbeat loss |
| Out | T18 | `DISQUALIFIED` | protocol violation (I2/I3/I11) |

## `EXHAUSTED_PENDING` (PATH A only)

| Direction | Transition | Other endpoint | Reason / note |
|-----------|-----------|----------------|---------------|
| In | **T7** | `ACTIVE_HASHING` | **ONLY incoming**; `RANGE_EXHAUSTED` (PATH A) |
| Out | T8 | `LOW_POWER_LISTEN` | ExhaustionConfirmed; range closed `coverage_state=searched`, `custody_status=completed` |
| Out | T9 | `WAKING` | RedeployOffer of an **available unsearched suffix** (permitted reason; the miner's own completed range is NOT reassigned) |
| Out | T13 | `OFFLINE` | departure / confirm-deadline expiry |
| Out | T19 | `DISQUALIFIED` | fabricated-exhaustion violation |

**Only incoming transition is T7 (`RANGE_EXHAUSTED`).** No valid-solution, revocation, or
round-closure transition enters `EXHAUSTED_PENDING`.

## `LOW_POWER_LISTEN`

| Direction | Transition | Other endpoint | Reason / note |
|-----------|-----------|----------------|---------------|
| In | T8 | `EXHAUSTED_PENDING` | PATH A, `RANGE_EXHAUSTED` |
| In | T26 | `ACTIVE_HASHING` | PATH B, `VALID_SOLUTION_VERIFIED` (PAUSED) |
| In | T27 | `ACTIVE_HASHING` | `ASSIGNMENT_REVOKED` |
| In | T28 | `ACTIVE_HASHING` | `ROUND_ACCEPTED` |
| In | T29 | `ACTIVE_HASHING` | `ROUND_ABORTED` |
| Out | T10 | `WAKING` | WakeRequest (new-round assignment / template refresh / security recovery) |
| Out | **T30** | `WAKING` | **ResumePausedAssignment** (PATH-B paused assignment; block rejected/unavailable/timed out) |
| Out | T14 | `OFFLINE` | departure / heartbeat loss |
| Out | T20 | `DISQUALIFIED` | protocol violation |

`LOW_POWER_LISTEN` is the legitimate shared sink of both paths, disambiguated by `stop_reason`;
only PATH-B (paused, `VALID_SOLUTION_VERIFIED`) assignments are eligible for T30 resume.

## `WAKING`

| Direction | Transition | Other endpoint | Reason / note |
|-----------|-----------|----------------|---------------|
| In | T3 | `REGISTERED` | AssignmentOffer |
| In | T4 | `RESERVE` | ReserveActivation |
| In | T9 | `EXHAUSTED_PENDING` | RedeployOffer (available unsearched suffix) |
| In | T10 | `LOW_POWER_LISTEN` | WakeRequest (new assignment) |
| In | T30 | `LOW_POWER_LISTEN` | ResumePausedAssignment (retained `actual_frontier`) |
| Out | T5 | `ACTIVE_HASHING` | RampComplete / resume; wake+transition energy accounted (`P_wake`, `E_transition`) |
| Out | T12 | `OFFLINE` | departure / wake-deadline / validation abort |
| Out | T21 | `DISQUALIFIED` | protocol violation |

## Path-separation proof

- **PATH A (range exhaustion):** `ACTIVE_HASHING --T7--> EXHAUSTED_PENDING --T8--> LOW_POWER_LISTEN`,
  `stop_reason = RANGE_EXHAUSTED`. The range is **closed** (`coverage_state = searched`,
  `custody_status = completed`) and is never reassigned nor resumed.
- **PATH B (verified valid-solution stop):** `ACTIVE_HASHING --T26--> LOW_POWER_LISTEN`
  **directly**, `stop_reason = VALID_SOLUTION_VERIFIED`. The assignment is **PAUSED** (retains
  `actual_frontier`; no unsearched position credited as searched) and is resumable via
  `--T30--> WAKING --T5--> ACTIVE_HASHING`.
- **Non-merge:** The only incoming edge of `EXHAUSTED_PENDING` is T7 (`RANGE_EXHAUSTED`); PATH B
  (T26) bypasses `EXHAUSTED_PENDING` entirely. No PATH-B trajectory ever enters
  `EXHAUSTED_PENDING`, and no PATH-A range is ever paused/resumed. The two paths share only the
  source `ACTIVE_HASHING` and the sink `LOW_POWER_LISTEN`, and are disambiguated at the sink by
  `stop_reason`. **The valid-solution path and the exhaustion path never merge.**
- **Resume exclusivity:** T30 is guarded on a paused (PATH-B, `VALID_SOLUTION_VERIFIED`)
  assignment; a completed (PATH-A) range cannot satisfy the T30 guard, so exhausted ranges
  cannot be resumed.

## Result

**STATE-PATH AUDIT: PASS.** `EXHAUSTED_PENDING` is reachable only via range exhaustion (T7);
the verified valid-solution stop is a distinct direct edge (T26); the two paths never merge;
every `LOW_POWER_LISTEN` entry records a `stop_reason`; PATH-B pauses are resumable and PATH-A
completions are not.
