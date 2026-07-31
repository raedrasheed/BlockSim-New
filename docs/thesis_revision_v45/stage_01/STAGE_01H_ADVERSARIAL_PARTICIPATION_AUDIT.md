# Stage 1H — Adversarial-Participation Audit (H6)

Audits correction **H6**: adversarial entry and exit take **state-specific** legal paths, so every
membership change routes through the central hook and no path fabricates a second live head or
leaves a live head behind. Binds to `STAGE_01_PROTOCOL_PSEUDOCODE.md` §8a
(`AdversarialParticipationChangeEvent`), §0.9 (`ApplyMinerStateTransition`), §4 (`RangeAssign`),
§0.11 (`CreatePendingAssignment`), §0.10 (`StartWake`/`WakeCompleteEvent`), §16a
(`ResumeFromPause`), §7 (`EnterLowPowerListen`), §5 (`HashWorkEvent` stale/cancel guard), §8
(`ActiveHashRateUpdate`); and `STAGE_01_MINER_STATE_MACHINE.md` §3 (T3/T4/T5/T10/T11/T17/T30). This
is a specification act on **PoCol** with the idle policy within PoCol enabled — not a claim of
implementation, enforcement, security, fairness, or any derived property. No new consensus feature
is introduced; the eight miner states and the T1–T30 (minus retired T6) edges are unchanged.

## 1. The corrected-away problem

A single **generic** re-entry (e.g. always calling `RangeAssign`) or a single **generic** exit is
unsound because it could:

- **(a)** mint a SECOND live head for a miner that already holds one — violating **I18b** (one live
  head per OPEN lineage). A still-PAUSED PATH-B miner already holds a live head; `RangeAssign` on it
  would open a second lineage head.
- **(b)** leave a live CURRENT head behind after a departure — violating **I18a/I18b** (a departed
  miner must leave zero live heads).
- **(c)** call `RangeAssign` from a state whose precondition it does not satisfy. `RangeAssign` (§4)
  requires `miner_state ∈ {REGISTERED, RESERVE}`; calling it from `OFFLINE` or `LOW_POWER_LISTEN` is
  an illegal transition (no such edge exists in §3).

H6 replaces the generic paths with a state-specific dispatch keyed on `miner_state(MinerID)` and, for
the idle case, on `entry_stop_reason(MinerID)` (I4).

## 2. Entry dispatch (`direction = enter`), state-specific

`AdversarialParticipationChangeEvent` reaches `ACTIVE_HASHING` **only** at a future
`WakeCompleteEvent` (T5, §0.10) — never a direct census add.

- **`REGISTERED` or `RESERVE`** — no live head exists. Calls `RangeAssign` (§4), which builds a fresh
  PENDING via `CreatePendingAssignment` (ORIGINAL, fresh lineage, §0.11) and issues the non-blocking
  `StartWake` — **T3** from `REGISTERED`, **T4** from `RESERVE`. The miner reaches `ACTIVE_HASHING`
  only at its own `WakeCompleteEvent` (**T5**). `RangeAssign`'s precondition is satisfied here, so the
  call is legal.
- **`OFFLINE`** — hook `OFFLINE → REGISTERED` FIRST (`ApplyMinerStateTransition`, reason
  `adversarial_rejoin`, **T17**), THEN `RangeAssign` (fresh PENDING + `StartWake`). The rejoin makes
  the subsequent `RangeAssign` precondition (`REGISTERED`) hold; there is never a direct census add and
  never an illegal `RangeAssign`-from-`OFFLINE` call.
- **`LOW_POWER_LISTEN` with `entry_stop_reason = VALID_SOLUTION_VERIFIED`** — the miner's OWN
  assignment is still **PAUSED**: a live head under I18b. Re-entry resumes THAT head via
  `ResumeFromPause` (§16a, **T30 → T5**) with `trigger = adversarial_reactivation`, reading the head's
  OWN recorded `pause_cause_candidate_id` / `pause_cause_propagation_id`. It **MUST NOT** call
  `RangeAssign` — that would mint a second live head and break I18b. `ResumeFromPause`'s precondition
  trigger set was extended from the candidate-failure set
  `{REJECTED, BLOCK_UNAVAILABLE, PROPAGATION_TIMEOUT, NO_VALID_CANDIDATE}` to also accept the single
  non-failure trigger `adversarial_reactivation`; because the caller reads the two ids **from the
  miner's own PAUSED head**, the two-id match (G11) is exact and no second live head is minted — this
  is precisely why H6 routes a PAUSED re-entry here rather than through `RangeAssign`.
- **`LOW_POWER_LISTEN` with `entry_stop_reason ∈ {RANGE_EXHAUSTED, ASSIGNMENT_REVOKED, ROUND_ACCEPTED,
  ROUND_ABORTED}`** — the prior assignment is CLOSED, so there is NO live head (I18b) and a fresh
  eligible assignment is legal. The legal re-entry edge from `LOW_POWER_LISTEN` is **T10** (new-
  assignment wake → `WAKING`), **NOT** `RangeAssign` (whose precondition is `REGISTERED`/`RESERVE`).
  It selects a fresh never-assigned range (I1), builds a fresh ORIGINAL PENDING (new lineage, I18b)
  via `CreatePendingAssignment`, and `StartWake` from `LOW_POWER_LISTEN` (**T10**). This mirrors
  `RangeAssign`'s body but with the correct legal source edge, avoiding the illegal
  `RangeAssign`-from-`LOW_POWER_LISTEN` call.
- **DEFAULT (`WAKING` / `ACTIVE_HASHING` / `EXHAUSTED_PENDING` / `DISQUALIFIED`)** — already
  participating or in a transient/terminal state → `RETURN no_change`. No transition, no census edit.

## 3. Exit dispatch (`direction = exit`)

Exit acts **ONLY** on `ACTIVE_HASHING`: a miner not in `H_active` contributes 0, so
`miner_state ≠ ACTIVE_HASHING` returns `no_census_change` (no fabricated departure edge). For an
`ACTIVE_HASHING` miner on CURRENT version `X` (the unique CURRENT, I18a):

1. PRESERVE the accepted searched prefix `[range_start(X), accepted_frontier(X)]`.
2. Expose ONLY the accepted unsearched suffix `[accepted_frontier(X)+1, range_end(X)]` as
   `inactive_unsearched / reassignable` (**C4**) — never the prefix.
3. RECORD the I9 withdrawal reason/provenance on `X` (`withdrawal_reason = adversarial_withdrawal`;
   `custody_status(range(X)) = revoked_adversarial_exit`).
4. CANCEL pending `HashWorkEvent` units for `(MinerID, AssignmentID(X), assignment_version(X))` — they
   would self-cancel by the §5 stale guard, but the exit cancels them so no unit is charged after the
   census leaves `H_active`.
5. `CLOSE/SUPERSEDE X` explicitly, so **NO** live CURRENT head remains (I18a/I18b).
6. `ApplyMinerStateTransition(ACTIVE_HASHING → OFFLINE, reason = adversarial_withdrawal, T11)` closes
   the `P_hash` residency and recomputes `H_active/H_honest/H_adversarial` (I17) at the boundary.

All six steps are inside the hook-routed exit; the census changes only at step 6 via the hook.

## 4. Compute-only census and hook-only membership

- `ActiveHashRateUpdate` (§8) is **compute-only** (G3): it READS the census and RECORDS
  `(H_active, H_honest, H_adversarial, q_adv)`; it has no `[SIMULATION SAMPLING]` step and MUST NOT
  add/remove any miner from `H_active` independently of `miner_state`. It never mutates the census.
- The adversarial **sampling** lives ONLY in the SCHEDULING of these events (the model draws each
  miner's enter/exit times and which miner changes); the STATE CHANGE is deterministic.
- Every membership change is applied by `ApplyMinerStateTransition` (§0.9, F6), so residency (single
  owner, H7), transition energy, and the I17 recompute each happen exactly once. Because the census-
  changing boundary is a hook transition, the hook sets
  `security_evaluation_required[(now, current_delta_cycle)]` (H3), and one
  `FinalizeTimestampSecurityCensus` evaluates the floor once for the settled census — the intermediate
  census is retained for audit only and never drives a round-state transition.

## 5. State → legal-path routing table

| from `miner_state` (+ `entry_stop_reason`) | dir | chosen legal path | transition id(s) | live-head outcome |
|--------------------------------------------|-----|-------------------|------------------|-------------------|
| `REGISTERED` | enter | `RangeAssign` → fresh ORIGINAL PENDING + `StartWake` | T3 → T5 | 1 head (PENDING→CURRENT at T5); I18b held |
| `RESERVE` | enter | `RangeAssign` → fresh ORIGINAL PENDING + `StartWake` | T4 → T5 | 1 head (PENDING→CURRENT at T5); I18b held |
| `OFFLINE` | enter | hook rejoin, THEN `RangeAssign` | T17, then T3 → T5 | 0 heads before, 1 head after; I18b held |
| `LOW_POWER_LISTEN` (`VALID_SOLUTION_VERIFIED`) | enter | `ResumeFromPause(adversarial_reactivation)`, own ids | T30 → T5 | reuses the SAME PAUSED head (no second head); I18b held |
| `LOW_POWER_LISTEN` (`RANGE_EXHAUSTED` / `ASSIGNMENT_REVOKED` / `ROUND_ACCEPTED` / `ROUND_ABORTED`) | enter | fresh ORIGINAL PENDING + `StartWake` from listen | T10 → T5 | prior CLOSED (0 heads) → 1 fresh head; I18b held |
| `WAKING` / `ACTIVE_HASHING` / `EXHAUSTED_PENDING` / `DISQUALIFIED` | enter | `no_change` | — | unchanged |
| `ACTIVE_HASHING` | exit | preserve prefix; suffix→C4; I9 record; cancel units; `CLOSE/SUPERSEDE X`; hook | T11 | CURRENT head closed → 0 live heads; I18a/I18b held |
| any state `≠ ACTIVE_HASHING` | exit | `no_census_change` | — | unchanged |

## 6. Proof-style argument

**No entry path mints a second live head.** The dispatch partitions on `miner_state`, and each branch
is only taken from a state whose live-head count is known:

- `REGISTERED` / `RESERVE` / `OFFLINE(→REGISTERED)` hold **zero** live heads (no assignment), so the
  fresh PENDING built by `CreatePendingAssignment` opens the lineage's first and only head (I18b).
- `LOW_POWER_LISTEN` with a CLOSED prior assignment holds **zero** live heads, so the T10 fresh
  ORIGINAL PENDING is again the only head.
- `LOW_POWER_LISTEN` with `VALID_SOLUTION_VERIFIED` holds **exactly one** PAUSED head; H6 routes it to
  `ResumeFromPause`, which resumes THAT head (matched on both pause-cause ids read from the head
  itself, G11) and mints **no** new lineage. It never calls `RangeAssign`.
- DEFAULT states apply no change.

Hence in every branch the post-entry live-head count is exactly one, and no `RangeAssign` is ever
called from a state outside its `{REGISTERED, RESERVE}` precondition — closing problems (a) and (c).

**No exit leaves a live head.** Exit fires only from `ACTIVE_HASHING`, where the lineage's unique head
is CURRENT (I18a). The exit explicitly `CLOSE/SUPERSEDE`s that version before the T11 hook call, so
the OPEN lineage transitions to CLOSED with zero live heads (I18b), and only the accepted unsearched
suffix (C4) survives as reassignable — closing problem (b). A departure from any other state changes
no census.

## 7. Acceptance-style PASS checklist

| # | Check | Result |
|--:|-------|--------|
| C1 | Entry from `REGISTERED` → `RangeAssign` (T3→T5), fresh ORIGINAL PENDING, no direct census add | **PASS** |
| C2 | Entry from `RESERVE` → `RangeAssign` (T4→T5), fresh ORIGINAL PENDING | **PASS** |
| C3 | Entry from `OFFLINE` → hook rejoin (T17) THEN `RangeAssign`, never a direct census add | **PASS** |
| C4 | Entry from paused `LOW_POWER_LISTEN` (`VALID_SOLUTION_VERIFIED`) → `ResumeFromPause` on OWN head (T30→T5), NOT `RangeAssign` | **PASS** |
| C5 | Entry from post-closure `LOW_POWER_LISTEN` → fresh ORIGINAL PENDING via T10, NOT `RangeAssign` | **PASS** |
| C6 | DEFAULT states (`WAKING`/`ACTIVE_HASHING`/`EXHAUSTED_PENDING`/`DISQUALIFIED`) → `no_change` | **PASS** |
| C7 | Exit acts only on `ACTIVE_HASHING`; else `no_census_change` | **PASS** |
| C8 | Exit preserves prefix, exposes only accepted unsearched suffix (C4), records I9, cancels units, `CLOSE/SUPERSEDE`s X, departs T11 | **PASS** |
| C9 | No illegal `RangeAssign` call (never from `OFFLINE`/`LOW_POWER_LISTEN`) | **PASS** |
| C10 | Every census change applied by `ApplyMinerStateTransition` (hook-only), settled once (H3) | **PASS** |
| C11 | `ActiveHashRateUpdate` compute-only; sampling only in event scheduling (G3) | **PASS** |
| C12 | I17 recomputed at each `ACTIVE_HASHING` boundary; I18a/I18b/I9/C4 preserved | **PASS** |
| C13 | A1 continuous full-participation baseline **8.420833333 kWh** unchanged; no new consensus feature | **PASS** |

Exercised by **TV55** (paused re-entry resumes its own head), **TV56** (post-closure re-entry opens a
fresh head via T10), and **TV57** (exit preserves coverage, leaves no live head).

## Result

**Result: ADVERSARIAL PARTICIPATION AUDIT (Stage 1H): PASS** — adversarial entry and exit take
state-specific legal paths (T3/T4 from `REGISTERED`/`RESERVE`; T17-then-`RangeAssign` from `OFFLINE`;
`ResumeFromPause` T30→T5 for a still-PAUSED idle head; T10 for a post-closure idle head; T11 for the
`ACTIVE_HASHING` exit), no path mints a second live head and no exit leaves a live CURRENT head
behind, no illegal `RangeAssign` is called outside its `{REGISTERED, RESERVE}` precondition, every
membership change routes through `ApplyMinerStateTransition` while `ActiveHashRateUpdate` stays
compute-only, and I17/I18a/I18b/I9/C4 hold with the A1 baseline 8.420833333 kWh unchanged.
