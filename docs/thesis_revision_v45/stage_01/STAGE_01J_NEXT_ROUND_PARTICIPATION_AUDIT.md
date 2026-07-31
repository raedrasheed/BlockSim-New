# Stage 1J — Next-Round Participation Audit (J5)

Audits correction **J5**: after the first accepted (or aborted) round, miners parked in
`LOW_POWER_LISTEN` are given a **named, executable** route back to `ACTIVE_HASHING` in the next
round by `PrepareParticipantsForNewRound`, which runs in the `ASSIGNMENT` phase, binds fresh
`ORIGINAL`/`REASSIGNED` `PENDING` assignments to the **NEW** `RoundID`/`TemplateID`, and wakes each
eligible miner through its legal per-state edge — **never** reopening a CLOSED old-round assignment.
Binds to `STAGE_01_PROTOCOL_PSEUDOCODE.md` §2a (`PrepareParticipantsForNewRound`), §1
(`RoundInitialise`), §2 (`TemplateCommit`), §0.11 (`CreatePendingAssignment`), §0.10
(`StartWake`/`WakeCompleteEvent`), §17a (`CloseRoundAssignments` — the closure that CLOSED the old
head), §7 (`EnterLowPowerListen`), §8a (`AdversarialParticipationChangeEvent`, `CASE
LOW_POWER_LISTEN` — the mid-round contrast); `STAGE_01_MINER_STATE_MACHINE.md` §3 (T3 / T4 / T10 /
T5 / T17); and `STAGE_01_ROUND_STATE_MACHINE.md` §4 (R3 `TEMPLATE_COMMITMENT → ASSIGNMENT`, R4
`ASSIGNMENT → HASHING`). This is a specification act on **PoCol** with **the idle policy within
PoCol** enabled — not a claim of implementation, enforcement, security, fairness, or any derived
property. No new consensus feature is introduced; the eight miner states and the T1–T30 (minus
retired T6) edges are unchanged, and the A1 continuous full-participation baseline
**8.420833333 kWh** is unchanged.

## 1. The corrected-away problem

At round closure, `CloseRoundAssignments` (§17a) CLOSES every open assignment under the closing
`RoundID`/`TemplateID` (J7: `CLOSED`, not `SUPERSEDED`) and leaves each holder that had been hashing
in `LOW_POWER_LISTEN` with `entry_stop_reason ∈ {ROUND_ACCEPTED, ROUND_ABORTED}` (via T28/T29
through `EnterLowPowerListen`, §7). The next round then runs `RoundInitialise` (§1, fresh `RoundID`)
and `TemplateCommit` (§2, new `TemplateID`).

Nothing re-offered those parked miners a range. `LOW_POWER_LISTEN`'s only outgoing hashing edges are
**T10** (wake on a new-assignment offer) and **T30** (resume of a PAUSED PATH-B head); a
`ROUND_ACCEPTED`/`ROUND_ABORTED` head is CLOSED, so T30 is inapplicable, and no procedure emitted a
T10 offer for the next round. The mid-round §8a `CASE LOW_POWER_LISTEN` path explicitly
`RETURN deferred_round_terminal` for these reasons — it defers, on purpose, to a next-round path. So
after the first accepted round a parked miner had **no named, executable path** to `ACTIVE_HASHING`
and could not participate. J5 supplies exactly that path.

## 2. The correction — `PrepareParticipantsForNewRound` (J5)

`PrepareParticipantsForNewRound` (§2a) runs with `PRECONDITIONS: round_state = ASSIGNMENT` after
`RoundInitialise` and `TemplateCommit` have produced a fresh `RoundID` and a committed eligible
`TemplateID`. It enumerates eligible miners in **stable `MinerID` order** (G7) and gives each a legal
per-state path, binding every new assignment to the **NEW** identifiers via `CreatePendingAssignment`
(§0.11) and waking through the non-blocking `StartWake` (§0.10). Each miner then reaches
`ACTIVE_HASHING` only at its OWN `WakeCompleteEvent` (**T5**). The intended assignment set is thereby
established **before** `ASSIGNMENT → HASHING` (**R4**). It NEVER reopens a CLOSED old-round
assignment (J7); a fresh head is a new lineage (I18b).

## 3. Per-state decision table — (`miner_state`, `entry_stop_reason`) → action → transition → origin / round-safety

| # | `miner_state` (+ `entry_stop_reason`) | action in §2a | transition id | assignment origin / round-safety outcome |
|--:|---------------------------------------|---------------|:-------------:|------------------------------------------|
| 1 | `REGISTERED` | select unassigned range (I1); `CreatePendingAssignment(ORIGINAL)`; set lease; `StartWake(from=REGISTERED)` | **T3 → T5** | **ORIGINAL**, fresh lineage bound to NEW `RoundID`/`TemplateID`; I18b held |
| 2 | `RESERVE` (policy places accepted-unsearched suffix S) | `CreatePendingAssignment(REASSIGNED, source_of(S))` (I9 provenance); set lease; `StartWake(from=RESERVE)` | **T4 → T5** | **REASSIGNED** suffix, new lineage linked by `previous_assignment_reference` (I9); NOT labelled ORIGINAL |
| 3 | `RESERVE` (no suffix placed) | select unassigned range (I1); `CreatePendingAssignment(ORIGINAL)`; set lease; `StartWake(from=RESERVE)` | **T4 → T5** | **ORIGINAL**, fresh lineage bound to NEW ids; I18b held |
| 4 | `LOW_POWER_LISTEN` + `ROUND_ACCEPTED` | archive prev `entry_stop_reason`; select unassigned range (NEW `TemplateID`, I1); `CreatePendingAssignment(ORIGINAL)`; set lease; `StartWake(from=LOW_POWER_LISTEN)` | **T10 → T5** | **ORIGINAL** bound to NEW ids; old head stays CLOSED (J7) — **no reopen** |
| 5 | `LOW_POWER_LISTEN` + `ROUND_ABORTED` | (as #4) | **T10 → T5** | **ORIGINAL** bound to NEW ids; old head stays CLOSED (J7) — **no reopen** |
| 6 | `LOW_POWER_LISTEN` + `RANGE_EXHAUSTED` / `ASSIGNMENT_REVOKED`, policy offers a range | select policy-offered range (NEW `TemplateID`, I1); `CreatePendingAssignment(ORIGINAL)`; set lease; `StartWake(from=LOW_POWER_LISTEN)` | **T10 → T5** | **ORIGINAL** under new template; prior head already CLOSED — no reopen |
| 7 | `LOW_POWER_LISTEN` + `RANGE_EXHAUSTED` / `ASSIGNMENT_REVOKED`, no range offered | `CONTINUE` (stay parked) | *(none)* | no head created; participation deferred, not forced |
| 8 | `LOW_POWER_LISTEN` + `VALID_SOLUTION_VERIFIED` (DEFAULT) | `CONTINUE` — cannot survive a round boundary (prior closure CLOSED the paused head, J7); if seen, treat under new-round policy, never reopen | *(none)* | no PAUSED head reopened across the boundary |
| 9 | `OFFLINE` | `CONTINUE` — no assignment unless a **separate** legal rejoin (`OFFLINE → REGISTERED`, **T17**) has COMPLETED first; only then is it a `REGISTERED` participant on a later pass (row 1) | **T17** first (elsewhere) | no assignment here; rejoin is a distinct completed edge |
| 10 | `DISQUALIFIED` | `CONTINUE` — terminal/absorbing | *(none)* | terminal; never assigned |
| 11 | `ACTIVE_HASHING` / `WAKING` / `EXHAUSTED_PENDING` (DEFAULT) | `CONTINUE` — should not occur at a fresh round's `ASSIGNMENT` | *(none)* | no action |

Legal edges used are exactly the range-binding wake edges into `WAKING` — **T3** (`REGISTERED`),
**T4** (`RESERVE`), **T10** (`LOW_POWER_LISTEN` new assignment) — each completing at **T5**
(`WAKING → ACTIVE_HASHING`). No illegal direct `LOW_POWER_LISTEN → ACTIVE_HASHING` edge is used;
resumption of hashing passes through `WAKING` so wake energy is charged (miner SM §3.1).

## 4. Timing and new-id binding

**Right phase.** `PrepareParticipantsForNewRound`'s precondition is `round_state = ASSIGNMENT` with a
fresh `RoundID` and a committed eligible `TemplateID`. That state is reached only after
`RoundInitialise` (§1) → `TemplateCommit` (§2, which performs `TRANSITION round_state → ASSIGNMENT`,
**R3**). The procedure closes by stating the intended assignment set is established (all `PENDING`,
waking) and ONLY THEN does the round proceed `ASSIGNMENT → HASHING` (**R4**). So it runs strictly
**after** `TemplateCommit` and strictly **before** R4 — during the window R4 requires: every intended
active assignment distributed and valid (pairwise disjoint per I1, bound to the current
`RoundID`+`TemplateID` per I3).

**New identifiers only.** Every `CreatePendingAssignment` call carries the current-round
`RoundID`/`TemplateID` (§0.11 sets `RoundID, TemplateID` on the fresh version), and for the
`LOW_POWER_LISTEN` reasons the range is explicitly `SELECT`ed from the unassigned portion of the
nonce domain under the **NEW** `TemplateID`. The old head remains CLOSED from `CloseRoundAssignments`
(§17a); nothing rebinds, resumes, or re-`CURRENT`s it. A new `TemplateID` is minted per round
(round SM §3.12), so a fresh assignment can never bind the old, closed template.

## 5. Worked example (TV76)

**Setup.** Miner `m` is in `LOW_POWER_LISTEN` with `entry_stop_reason = ROUND_ACCEPTED`; its
old-round assignment `X_old` is CLOSED (J7). A new round runs `RoundInitialise` (fresh `RoundID`) and
`TemplateCommit` (new `TemplateID`), reaching `round_state = ASSIGNMENT`.

**Trace (row 4).** `PrepareParticipantsForNewRound` iterates in stable `MinerID` order; for `m` it
takes `CASE LOW_POWER_LISTEN / ROUND_ACCEPTED`: `ARCHIVE previous_round_entry_stop_reason(m)`,
`SELECT`s a fresh never-assigned range under the NEW `TemplateID`,
`CreatePendingAssignment(ORIGINAL)` (new lineage `a`, bound to the NEW `RoundID`/`TemplateID`), sets
`lease_start`/`lease_expiry`, and `StartWake(from_state = LOW_POWER_LISTEN)` — **T10**. `X_old` is
**not** reopened. At `m`'s own `WakeCompleteEvent`, `a` activates `PENDING → CURRENT` and `m` enters
`ACTIVE_HASHING` — **T5** — all before `ASSIGNMENT → HASHING` (R4).

**Outcome.** `m` participates in the next round via a fresh new-template ORIGINAL assignment (T10 →
T5); no CLOSED old assignment is reopened; I1/I18b hold. Reqs: **J5**, J7, I1, I18b.

## 6. Acceptance-style PASS checklist

| # | Check | Result |
|--:|-------|--------|
| C1 | `REGISTERED` → fresh **ORIGINAL** PENDING + `StartWake` via **T3 → T5** | **PASS** |
| C2 | `RESERVE` → fresh **ORIGINAL** OR correctly-provenanced **REASSIGNED** PENDING (I9) + `StartWake` via **T4 → T5** | **PASS** |
| C3 | `LOW_POWER_LISTEN` + `ROUND_ACCEPTED`/`ROUND_ABORTED` → archive prev reason; fresh ORIGINAL bound to NEW ids; `StartWake` via **T10 → T5** | **PASS** |
| C4 | `LOW_POWER_LISTEN` + `RANGE_EXHAUSTED`/`ASSIGNMENT_REVOKED` → new-round policy applied explicitly: fresh ORIGINAL + **T10** if a range is offered, else stay parked | **PASS** |
| C5 | `VALID_SOLUTION_VERIFIED` cannot survive the round boundary (paused head CLOSED, J7); `CONTINUE`, never reopen | **PASS** |
| C6 | `OFFLINE` gets nothing unless `OFFLINE → REGISTERED` (**T17**) COMPLETED first; `DISQUALIFIED` terminal — gets nothing | **PASS** |
| C7 | Every new assignment binds the **NEW** `RoundID`/`TemplateID` (never the old, closed one) | **PASS** |
| C8 | No CLOSED old-round assignment is reopened/resumed/re-`CURRENT`ed (J7); fresh heads are new lineages (I18b) | **PASS** |
| C9 | Only legal edges used: **T3**/**T4**/**T10** into `WAKING`, each completing at **T5**; no direct `LOW_POWER_LISTEN → ACTIVE_HASHING` | **PASS** |
| C10 | Miners iterated in stable `MinerID` order (G7); each `CreatePendingAssignment`/`StartWake` scheduled via `ScheduleEvent` (J9) | **PASS** |
| C11 | Runs after `TemplateCommit` (R3) and **before** `ASSIGNMENT → HASHING` (R4); assignment set valid (I1/I3) at R4 | **PASS** |
| C12 | A1 baseline **8.420833333 kWh** unchanged; no new consensus feature; algorithm remains **PoCol** with **the idle policy within PoCol** | **PASS** |

Exercised by **TV76** (a `ROUND_ACCEPTED`-parked `LOW_POWER_LISTEN` miner is re-assigned under the
new template via T10, no reopen of the CLOSED old-round assignment).

## Result

**Result: NEXT-ROUND PARTICIPATION AUDIT (Stage 1J): PASS** — `PrepareParticipantsForNewRound` (§2a)
supplies the previously missing named, executable next-round path: it runs in the `ASSIGNMENT` phase
after `RoundInitialise` (§1) and `TemplateCommit` (§2, R3) once a fresh `RoundID` and committed
eligible `TemplateID` exist, enumerates eligible miners in stable `MinerID` order (G7), and binds a
legal per-state assignment — `REGISTERED` fresh ORIGINAL via **T3**, `RESERVE` fresh ORIGINAL or
correctly-provenanced REASSIGNED via **T4**, `LOW_POWER_LISTEN`/`ROUND_ACCEPTED`/`ROUND_ABORTED` a
fresh ORIGINAL under the NEW `RoundID`/`TemplateID` via **T10** (prior head stays CLOSED, J7),
`LOW_POWER_LISTEN`/`RANGE_EXHAUSTED`/`ASSIGNMENT_REVOKED` a fresh ORIGINAL via **T10** only when the
new-round policy offers a range (else stays parked) — while `VALID_SOLUTION_VERIFIED` cannot cross the
boundary and `OFFLINE` (rejoin only via completed **T17**) / `DISQUALIFIED` (terminal) receive
nothing; each miner reaches `ACTIVE_HASHING` at its own `WakeCompleteEvent` (**T5**) with the
intended assignment set established before `ASSIGNMENT → HASHING` (**R4**), never reopening a CLOSED
old-round assignment (J7/I18b), with the A1 baseline 8.420833333 kWh unchanged and no new consensus
feature introduced.
