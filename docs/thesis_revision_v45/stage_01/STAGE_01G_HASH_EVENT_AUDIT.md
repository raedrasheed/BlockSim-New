# Stage 1G — Hash-Event & Wake-Failure Audit (G9, G4)

A structural audit of two Stage-1G corrections in the **PoCol** protocol pseudocode
(`STAGE_01_PROTOCOL_PSEUDOCODE.md`): **G9** replaces blocking-loop hashing with
event-scheduled `HashWorkEvent`s, and **G4** makes the `WakeCompleteEvent` failure branch
status-aware so a PAUSED resume failure is not dispositioned by the PENDING-only rule. This
document is documentation only; it audits wording and control structure, and claims no
security, fairness, or incentive property.

---

## Part A — Event-scheduled hashing (G9)

### A.1 Procedure descriptions

- **`StartHashing`** (§5) — begins event-scheduled hashing. It does **not** loop: it calls
  `ScheduleNextHashWork` for the first unit (`from_cursor` = next unsearched nonce in the
  assignment range) and returns `hashing_started`.
- **`ScheduleNextHashWork`** (§5) — schedules exactly **ONE** bounded `HashWorkEvent`,
  carrying the identity keys `MinerID, AssignmentID(assignment), assignment_version,
  RoundID, TemplateID, from_cursor`, at `now + modeled_hash_step_time`, and returns.
- **`HashWorkEvent`** (§5) — evaluates one bounded unit at its own event timestamp:
  1. **Stale/cancelled-work guard.** Resolves `assignment <- version(AssignmentID,
     assignment_version)` and returns `hash_work_noop` unless the miner is still
     `ACTIVE_HASHING` **AND** the exact `status(assignment) = CURRENT` **AND** `RoundID` /
     `TemplateID` match the current round/committed template **AND** `round_state ∈
     {HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY}`.
  2. Asserts `cursor ∈ range` and **accounts residency** by accumulating `t_hash` over the
     elapsed event time since the last hash boundary (I5/I6).
  3. Draws **one** `[SIMULATION SAMPLING]` target-hit `Bernoulli(target_hit_probability(D))`.
  4. **On hit** → build the candidate solution, take the immutable discovery **snapshot**,
     generate the signed **certificate**, then `ScheduleSolutionPropagation` — the finder
     **pauses**, so **no next unit** is scheduled for it.
  5. **On cursor beyond range** → `ActualRangeCompletion`, then `ReportedExhaustionClaim`,
     then `ExhaustionAdjudicate`.
  6. **Otherwise** → `ScheduleNextHashWork(from_cursor = cursor)` and return to the loop.

### A.2 Properties

| # | Property | Result | Why (structure) |
|---|----------|--------|-----------------|
| A1 | No blocking `WHILE` loop remains | PASS | §5 defines only `StartHashing` / `HashWorkEvent` / `ScheduleNextHashWork`; grep of §5 shows no `ActiveHashing` loop, no `WHILE`, and no `step_budget` — hashing is a chain of discrete events. |
| A2 | A certificate arrival scheduled between two hash units is processed in queue order (TV48) | PASS | Each unit schedules the next at `now + modeled_hash_step_time` and returns; an intervening event fires by `event_time`/microphase order, not blocked by any loop. |
| A3 | Pending units self-cancel as a no-op | PASS | The step-(1) guard returns `hash_work_noop` on non-`ACTIVE_HASHING`, non-`CURRENT` version, changed `RoundID`/`TemplateID`, or a `round_state` outside the hashing-capable set — covering pause / exhaustion / revocation / offline / disqualification / template refresh / round closure. |
| A4 | `WakeCompleteEvent` success calls `StartHashing`, not a blocking loop | PASS | The success branch (§0.10) is `RETURN CALL StartHashing(...)`, which only schedules the first unit and returns. |
| A5 | Multiple miners hash through independent events | PASS | Each miner's units are independently scheduled events; `WakeCompleteEvent` makes no nested blocking hashing call — only the non-blocking `StartHashing` handoff. |
| A6 | Only `ACTIVE_HASHING` contributes to the active hash rate | PASS | The guard requires `miner_state = ACTIVE_HASHING`; residency/`H_active` recompute is owned by `ApplyMinerStateTransition` (I17), and §8 credits only `ACTIVE_HASHING`. |
| A7 | The single sampling draw is the per-unit target-hit | PASS | `HashWorkEvent` contains exactly one `[SIMULATION SAMPLING]` step, the `Bernoulli` target-hit draw; all other steps are deterministic. |

---

## Part B — Status-aware wake failure (G4)

### B.1 `WakeCompleteEvent` failure branch (§0.10)

On `wake_within_deadline` failure the handler records `wake_failure`, moves the miner
**`WAKING -> OFFLINE`** (T12) via `ApplyMinerStateTransition`, then `SWITCH`es on
`status(target_assignment)`:

- **CASE PENDING** (failed activation of a fresh/reassigned assignment):
  - preserve the accepted searched prefix `[range_start, accepted_frontier]`;
  - `reassignable` = **none** if `accepted_frontier = range_end`; else the **whole range**
    if no accepted positions exist; else the suffix `[accepted_frontier + 1, range_end]`;
  - mark any `reassignable` as `inactive_unsearched / reassignable`; set
    `custody_status <- abandoned`;
  - `CLOSE` the assignment `PENDING -> CLOSED` (**no CURRENT recorded**;
    ORIGINAL/REASSIGNED provenance kept); record wake-failure energy/provenance.

- **CASE PAUSED** (failed resume of a PATH-B assignment):
  - **PRESERVE all three frontiers** `actual_frontier, reported_frontier,
    accepted_frontier`;
  - `reassignable` = **whole range** if no accepted positions exist, else the **SUFFIX
    only** `[accepted_frontier + 1, range_end]`; mark it `inactive_unsearched /
    reassignable`; set `custody_status <- abandoned`;
  - `CLOSE/ABANDON` the assignment `PAUSED -> CLOSED` with
    `disposition = resume_wake_failed` (**not** the PENDING-only rule);
  - `CLEAR` `pause_cause_candidate_id`, `pause_cause_propagation_id`, and
    `retained_actual_frontier`; record resume-failure energy/provenance.

### B.2 Properties

| # | Property | Result | Why (structure) |
|---|----------|--------|-----------------|
| B1 | PENDING and PAUSED failure paths differ | PASS | Two distinct `SWITCH` cases: PENDING may set `reassignable <- whole range`, closes `PENDING -> CLOSED` with no CURRENT; PAUSED preserves three frontiers and closes with `disposition = resume_wake_failed`. |
| B2 | PAUSED resume failure preserves accepted coverage and reassigns only the accepted unsearched suffix | PASS | PAUSED case preserves all three frontiers and, when accepted positions exist, sets `reassignable <- [accepted_frontier + 1, range_end]` (SUFFIX only) — never whole-range under the PENDING-only rule. |
| B3 | Candidate pause fields cleared on resume failure | PASS | The PAUSED case ends with `CLEAR pause_cause_candidate_id / pause_cause_propagation_id / retained_actual_frontier` (G4/G11). |
| B4 | Never `PAUSED -> CLOSED` via a PENDING-only rule | PASS | The PAUSED closure is explicitly `disposition = resume_wake_failed`; the whole-range-inactive PENDING rule is confined to the PENDING case. |
| B5 | Miner reaches OFFLINE via the hook (I17 recomputed at the boundary) | PASS | Both cases follow `ApplyMinerStateTransition(WAKING, OFFLINE, ...)` (T12), the sole writer of `miner_state` that recomputes `H_active/H_honest/H_adversarial` (I17) at the boundary. |

---

## Result

**HASH-EVENT & WAKE-FAILURE AUDIT (G9, G4): PASS.** Hashing is a chain of discrete
`HashWorkEvent`s with a stale/cancelled-work guard and a single per-unit sampling draw, and
no blocking loop remains (exercised by TV48); the `WakeCompleteEvent` failure branch is
status-aware, preserving accepted coverage and clearing candidate pause fields on a PAUSED
resume failure rather than applying the PENDING-only rule (exercised by TV42).
