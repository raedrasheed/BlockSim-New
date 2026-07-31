# Stage 1I — Low-Power Re-Entry Audit (I-06)

Audits correction **I-06**: an adversarial re-entry from `LOW_POWER_LISTEN` is dispatched
**state-specifically by `entry_stop_reason` (I4) AND the CURRENT round's liveness**, so no fresh
assignment or wake is ever created against a closed or discarded-template `RoundContext`, and the
paused-solution path never mints a second live head. Binds to `STAGE_01_PROTOCOL_PSEUDOCODE.md`
§8a (`AdversarialParticipationChangeEvent`, `CASE LOW_POWER_LISTEN` and its inner
`SWITCH entry_stop_reason(MinerID)`), §16a (`ResumeFromPause`), §0.11 (`CreatePendingAssignment`),
§0.10 (`StartWake`/`WakeCompleteEvent`), §7 (`EnterLowPowerListen`), §17a
(`CloseRoundAssignments`), §19 (`TemplateRefresh`), §4 (`RangeAssign` — for the precondition it
does NOT satisfy here); and `STAGE_01_MINER_STATE_MACHINE.md` §3 (T10 / T30 / T5 / T26–T29). This
is a specification act on **PoCol** with **the idle policy within PoCol** enabled — not a claim of
implementation, enforcement, security, fairness, or any derived property. No new consensus feature
is introduced; the eight miner states and the T1–T30 (minus retired T6) edges are unchanged, and
the A1 continuous full-participation baseline **8.420833333 kWh** is unchanged.

## 1. The corrected-away problem

The Stage-1H `CASE LOW_POWER_LISTEN` branch lumped four `entry_stop_reason` values
`{RANGE_EXHAUSTED, ASSIGNMENT_REVOKED, ROUND_ACCEPTED, ROUND_ABORTED}` into a **single** "fresh
ORIGINAL PENDING + `StartWake` (T10)" branch. That single branch is unsound because:

- **(a)** it would `CreatePendingAssignment` and `StartWake` even when the CURRENT round is
  terminal — `ROUND_ACCEPTED` or `ROUND_ABORTED` — creating an assignment and a wake **inside a
  closed `RoundContext`** whose head `EnterLowPowerListen` (§7) already CLOSED via T28/T29;
- **(b)** it would activate against a **discarded template** when the round is mid-`TEMPLATE_REFRESH`
  (§19), binding a range under a template that is about to be superseded by a new `TemplateID`;
- **(c)** even in a live round it did not gate on a committed eligible `TemplateID` or on the
  assignment policy, so it could force a range where none is offered.

I-06 replaces the single branch with a dispatch keyed first on `entry_stop_reason(MinerID)` and
then, for the fresh-range reasons, on `round_state` liveness.

## 2. The correction — state-specific re-entry (I-06)

The inner `SWITCH entry_stop_reason(MinerID)` in §8a `CASE LOW_POWER_LISTEN` splits into:

- **`VALID_SOLUTION_VERIFIED` (PATH-B pause).** The miner's OWN assignment is still **PAUSED** — a
  live head under I18b. Re-entry resumes THAT head via `ResumeFromPause` (§16a) with
  `trigger = adversarial_reactivation`, reading the head's OWN recorded
  `pause_cause_candidate_id` / `pause_cause_propagation_id` from `paused_assignment(MinerID)` so the
  two-id match (**G11**) is exact — **T30 → T5**. It **NEVER** calls `RangeAssign` and mints **no**
  second live head (I18b). A terminal round would already have CLOSED this head in
  `CloseRoundAssignments` (§17a), so reaching this case implies the round is still **live** and the
  head is genuinely PAUSED.
- **`RANGE_EXHAUSTED` or `ASSIGNMENT_REVOKED`.** The prior assignment is CLOSED (zero live heads), so
  a fresh assignment is legal — but **only** when all three liveness guards hold:
  1. `round_state ∉ {ROUND_ACCEPTED, ROUND_ABORTED}` — else `RETURN deferred_round_terminal`;
  2. `round_state ≠ TEMPLATE_REFRESH` — else `RETURN deferred_to_new_template`;
  3. a committed **eligible** `TemplateID` exists for `RoundContext` **AND**
     `assignment_policy_permits_fresh_range(RoundContext)` — else `RETURN no_eligible_range_now`.
  When all hold, it `SELECT`s a fresh never-assigned range (I1), builds a fresh **ORIGINAL** PENDING
  (new lineage, I18b) via `CreatePendingAssignment` (§0.11), and `StartWake` from `LOW_POWER_LISTEN`
  — **T10** (§0.10), **NOT** `RangeAssign` (§4, whose precondition is `REGISTERED`/`RESERVE`, T3/T4).
  Otherwise it returns a deferral token and creates **no** assignment and **no** wake.
- **`ROUND_ACCEPTED` or `ROUND_ABORTED`.** The miner idled because the **round ended**. It creates
  **NO** assignment in the closed `RoundContext` and does **NOT** `StartWake` for the closed round —
  `RETURN deferred_round_terminal`. Participation is DEFERRED to the next
  `RoundInitialise` / `TemplateCommit` / `ASSIGNMENT` phase, which re-offers ranges legally under a
  fresh `RoundID`/`TemplateID`.
- **`TEMPLATE_REFRESH` round-state (guard 2 above).** A `RANGE_EXHAUSTED`/`ASSIGNMENT_REVOKED`
  re-entry is DEFERRED (`deferred_to_new_template`) to the new-template assignment procedure:
  `TemplateRefresh` (§19) commits the new `TemplateID` and only then re-offers ranges (T10 **under
  the NEW template**). No activation is ever performed against the discarded template.

## 3. Decision table — (`entry_stop_reason`, round liveness) → action → transition / token

| # | `entry_stop_reason` | `round_state` / liveness | chosen action | transition id(s) / deferral token | live-head / round-safety outcome |
|--:|---------------------|--------------------------|---------------|-----------------------------------|----------------------------------|
| 1 | `VALID_SOLUTION_VERIFIED` | round live (head still PAUSED; a terminal round would have CLOSED it in §17a) | `ResumeFromPause(adversarial_reactivation)` on OWN head, two-id match (G11) | **T30 → T5** | reuses the SAME PAUSED head; **no** second live head (I18b) |
| 2 | `RANGE_EXHAUSTED` / `ASSIGNMENT_REVOKED` | live, non-refresh, committed eligible `TemplateID`, policy permits fresh range | fresh never-assigned range (I1) → `CreatePendingAssignment` (ORIGINAL) → `StartWake` from `LOW_POWER_LISTEN` | **T10 → T5** (NOT `RangeAssign`) | prior CLOSED (0 heads) → 1 fresh ORIGINAL head; I18b held |
| 3 | `RANGE_EXHAUSTED` / `ASSIGNMENT_REVOKED` | `ROUND_ACCEPTED` or `ROUND_ABORTED` (terminal) | no assignment, no wake | `deferred_round_terminal` | no head created in a closed `RoundContext` |
| 4 | `RANGE_EXHAUSTED` / `ASSIGNMENT_REVOKED` | `TEMPLATE_REFRESH` (mid-refresh) | defer to new-template assignment; `TemplateRefresh` re-offers ranges under the new `TemplateID` | `deferred_to_new_template` (later **T10** under the NEW template) | no activation against the discarded template |
| 5 | `RANGE_EXHAUSTED` / `ASSIGNMENT_REVOKED` | live & non-refresh, but no eligible `TemplateID` or policy offers no range | no assignment, no wake | `no_eligible_range_now` | no head; re-entry is deferred, not forced |
| 6 | `ROUND_ACCEPTED` or `ROUND_ABORTED` | (round ended by definition) | no assignment in the closed round, no wake | `deferred_round_terminal` | deferred to next `RoundInitialise`/`TemplateCommit`/`ASSIGNMENT` |

## 4. Proof — no head against a closed/discarded template; no second live head

**No assignment or wake is ever created against a closed `RoundContext`.** The only branches that
call `CreatePendingAssignment` + `StartWake` are rows 1 and 2. Row 2 is reached ONLY after guard 1
`round_state ∉ {ROUND_ACCEPTED, ROUND_ABORTED}` has passed, so it cannot fire in a terminal round;
rows 3 and 6 return `deferred_round_terminal` without any constructor or wake. Row 1
(`ResumeFromPause`) is only reachable when the head is still PAUSED, which — because
`CloseRoundAssignments` (§17a) CLOSES every head at `ROUND_ACCEPTED`/`ROUND_ABORTED` — implies the
round is live. Hence no `T10` and no `T30` wake targets a closed round. ∎

**No assignment or wake is ever created against a discarded template.** Row 2 is reached ONLY after
guard 2 `round_state ≠ TEMPLATE_REFRESH` passes; a mid-refresh re-entry takes row 4
(`deferred_to_new_template`). Activation resumes only through `TemplateRefresh` (§19), which commits
the new `TemplateID` first and then re-offers ranges via T10 under that new template. So no `T10`
binds a range under a to-be-discarded template. ∎

**The `VALID_SOLUTION_VERIFIED` path never mints a second live head (I18b).** A PAUSED PATH-B head
is the lineage's **one** live head (I18b). Row 1 routes to `ResumeFromPause`, whose precondition
requires `entry_stop_reason = VALID_SOLUTION_VERIFIED` and matches BOTH
`pause_cause_candidate_id` and `pause_cause_propagation_id` against `paused_assignment(MinerID)`
(G11); the caller reads those ids FROM the miner's own PAUSED head, so the match is exact and the
resume restores THAT head (PAUSED → CURRENT at T5) rather than opening a new lineage. `RangeAssign`
is never called on it. Therefore the post-entry live-head count is exactly one, and I18a/I18b hold. ∎

## 5. Acceptance-style PASS checklist

| # | Check | Result |
|--:|-------|--------|
| C1 | `VALID_SOLUTION_VERIFIED` → `ResumeFromPause(adversarial_reactivation)` on OWN head (T30→T5), NOT `RangeAssign` | **PASS** |
| C2 | Two-id pause-cause match (G11) preserved: ids read from `paused_assignment(MinerID)` | **PASS** |
| C3 | `VALID_SOLUTION_VERIFIED` mints no second live head; I18a/I18b held | **PASS** |
| C4 | `RANGE_EXHAUSTED`/`ASSIGNMENT_REVOKED` fresh re-entry uses **T10** (not `RangeAssign`), ORIGINAL PENDING, fresh lineage | **PASS** |
| C5 | Fresh re-entry gated on non-terminal `round_state` (`deferred_round_terminal` otherwise) | **PASS** |
| C6 | Fresh re-entry gated on non-`TEMPLATE_REFRESH` (`deferred_to_new_template` otherwise) | **PASS** |
| C7 | Fresh re-entry gated on committed eligible `TemplateID` + `assignment_policy_permits_fresh_range` (`no_eligible_range_now` otherwise) | **PASS** |
| C8 | `ROUND_ACCEPTED`/`ROUND_ABORTED` → `deferred_round_terminal`; no assignment/wake in the closed round | **PASS** |
| C9 | Deferred participation resumes only under a fresh `RoundID`/`TemplateID` (next `RoundInitialise`/`TemplateCommit`/`ASSIGNMENT`) or via `TemplateRefresh`'s T10 under the new template | **PASS** |
| C10 | No `CreatePendingAssignment`/`StartWake` ever targets a closed or discarded-template `RoundContext` | **PASS** |
| C11 | No illegal `RangeAssign` from `LOW_POWER_LISTEN` (its precondition is `REGISTERED`/`RESERVE`) | **PASS** |
| C12 | A1 baseline **8.420833333 kWh** unchanged; no new consensus feature; algorithm remains **PoCol** with **the idle policy within PoCol** | **PASS** |

Exercised by **TV68** (an adversarial-enter event for a `ROUND_ACCEPTED`-idle miner returns
`deferred_round_terminal` — no assignment/wake in the closed round; re-participates only under a
fresh `RoundID`/`TemplateID`).

## Result

**Result: LOW-POWER RE-ENTRY AUDIT (Stage 1I): PASS** — the §8a `CASE LOW_POWER_LISTEN` re-entry is
split by `entry_stop_reason` and round liveness: `VALID_SOLUTION_VERIFIED` resumes the miner's OWN
still-PAUSED head via `ResumeFromPause` (T30→T5) with its recorded two-id pause cause (G11) and never
`RangeAssign` (no second live head, I18b); `RANGE_EXHAUSTED`/`ASSIGNMENT_REVOKED` bind a fresh
ORIGINAL PENDING and `StartWake` via **T10** only in a non-terminal, non-`TEMPLATE_REFRESH`,
committed-eligible-template round whose policy permits a range, else return
`deferred_round_terminal` / `deferred_to_new_template` / `no_eligible_range_now`;
`ROUND_ACCEPTED`/`ROUND_ABORTED` defer to the next round; and a `TEMPLATE_REFRESH` round defers to
`TemplateRefresh`'s T10 under the new `TemplateID` — so no assignment or wake is ever created against
a closed or discarded-template `RoundContext`, with I18a/I18b/G11/I4 held and the A1 baseline
8.420833333 kWh unchanged.
