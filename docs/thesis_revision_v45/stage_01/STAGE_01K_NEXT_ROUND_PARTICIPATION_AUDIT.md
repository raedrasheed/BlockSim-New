# Stage 1K — Next-Round Participation Audit (K1)

Audits correction **K1**: EVERY miner parked in `LOW_POWER_LISTEN` after an accepted or aborted round
is given a **named, executable** next-round route back to `ACTIVE_HASHING` by
`PrepareParticipantsForNewRound` (§2a) for **every** `entry_stop_reason` it may carry — including
`VALID_SOLUTION_VERIFIED`, which was previously corrected away into a `DEFAULT/CONTINUE`. The
procedure runs in the `ASSIGNMENT` phase, binds fresh `ORIGINAL`/`REASSIGNED` `PENDING` assignments to
the **NEW** `RoundID`/`TemplateID`, wakes each eligible miner through its legal per-state edge, and
hands off to `CompleteAssignmentPhase` (§2b) for `ASSIGNMENT → HASHING` — **never** reopening a
`PAUSED`/`CLOSED` old-round head. Binds to `STAGE_01_PROTOCOL_PSEUDOCODE.md` §2a
(`PrepareParticipantsForNewRound`, `CASE LOW_POWER_LISTEN` and its `entry_stop_reason` `SWITCH`), §2b
(`CompleteAssignmentPhase`), §1 (`RoundInitialise`), §2 (`TemplateCommit`), §0.11
(`CreatePendingAssignment`), §0.10 (`StartWake`/`WakeCompleteEvent`), §17a (`CloseRoundAssignments`),
§7 (`EnterLowPowerListen`), §16 (`EarlyStopVerify`, PATH B); and `STAGE_01_MINER_STATE_MACHINE.md` §3
(**T3** `REGISTERED → WAKING`, **T4** `RESERVE → WAKING`, **T10** `LOW_POWER_LISTEN → WAKING`, **T5**
`WAKING → ACTIVE_HASHING`). This is a specification act on **PoCol** with **the idle policy within
PoCol** enabled — not a claim of implementation, enforcement, security, fairness, or any derived
property. No new consensus feature is introduced; the eight miner states and the T1–T30 (minus retired
T6) edges are unchanged, and the A1 continuous full-participation baseline **8.420833333 kWh** is
unchanged.

## 1. The corrected-away problem

`CloseRoundAssignments` (§17a) records a `round_closure_disposition` that is **separate** from a
miner's `entry_stop_reason` (I4) and explicitly **never overwrites** an existing
`VALID_SOLUTION_VERIFIED` reason: a PATH-B holder already parked in `LOW_POWER_LISTEN` keeps
`entry_stop_reason = VALID_SOLUTION_VERIFIED` through closure (§17a `CASE LOW_POWER_LISTEN`,
`ASSERT entry_stop_reason(h) ∈ {RANGE_EXHAUSTED, VALID_SOLUTION_VERIFIED, ASSIGNMENT_REVOKED}`), while
its paused head is `CLOSED` (J7). The reason is **preserved for historical attribution** — a verified
finder/recipient stays labelled as such.

Consequently a verified finder or certificate-verifying recipient crosses the round boundary in
`LOW_POWER_LISTEN` still carrying `entry_stop_reason = VALID_SOLUTION_VERIFIED`. In the earlier form,
`PrepareParticipantsForNewRound`'s `CASE LOW_POWER_LISTEN` `SWITCH` handled `ROUND_ACCEPTED`/
`ROUND_ABORTED` and `RANGE_EXHAUSTED`/`ASSIGNMENT_REVOKED` explicitly, but `VALID_SOLUTION_VERIFIED`
fell into a `DEFAULT`/`CONTINUE`. That head was already `CLOSED`, so **T30** (resume of a `PAUSED`
head) was inapplicable and no branch emitted a **T10** offer: a verified finder/recipient parked after
an accepted round had **no named, executable path** back to `ACTIVE_HASHING` and silently dropped out
of the next round. K1 supplies that path.

## 2. The correction — canonical `entry_stop_reason` disposition (K1)

`PrepareParticipantsForNewRound` (§2a) runs with `PRECONDITIONS: round_state = ASSIGNMENT` once
`RoundInitialise` (§1) and `TemplateCommit` (§2) have produced a fresh `RoundID` and a committed
eligible `TemplateID`; it enumerates eligible miners in **stable `MinerID` order** (G7) under an
explicit `DriverEventEnvelope` (K4). Its `CASE LOW_POWER_LISTEN` now makes **every** legal
`entry_stop_reason` an explicit disposition — **none falls through**.

**Canonical rule for `VALID_SOLUTION_VERIFIED` (grouped with `ROUND_ACCEPTED`/`ROUND_ABORTED`):**
(1) `ARCHIVE previous_round_entry_stop_reason(m) ← entry_stop_reason(m)` (I4) — the preserved
attribution is moved to audit history; (2) `ASSERT` no live head remains for `m`'s prior-round
lineage — its version is `CLOSED` (I18b/J7), **never** reopen a `PAUSED`/`CLOSED` version; (3)
`CreatePendingAssignment(ORIGINAL)` (§0.11) — a **fresh** `ORIGINAL` `PENDING` on a **new** lineage
bound to the **NEW** `RoundID`/`TemplateID` over a range `SELECT`ed from the unassigned nonce domain
under the new template (I1), set `lease`; (4) `StartWake(from_state = LOW_POWER_LISTEN)` — **T10**; the
miner reaches `ACTIVE_HASHING` only at its own `WakeCompleteEvent` (**T5**).

`RANGE_EXHAUSTED`/`ASSIGNMENT_REVOKED` apply the **new-round assignment policy explicitly**: if it
offers `m` a range, archive the reason and bind a fresh `ORIGINAL` under the new template + **T10**;
otherwise `RECORD next_round_disposition(m) ← parked_no_range_offered` (an explicit, recorded parked
disposition — not a fall-through). `OFFLINE`/`DISQUALIFIED` receive **no** assignment
(`RECORD next_round_disposition(m) ← deferred_no_assignment`). After the loop,
`CompleteAssignmentPhase` (§2b) performs the executable `ASSIGNMENT → HASHING` (R4).

## 3. Per-`entry_stop_reason` disposition table

`miner_state = LOW_POWER_LISTEN` unless noted. All five legal reasons plus the `OFFLINE`/`DISQUALIFIED`
states are covered; the "fall-through?" column is **No** for every row.

| # | `entry_stop_reason` (or state) | §2a disposition | edge | assignment origin / new ids | old head | fall-through? |
|--:|--------------------------------|-----------------|:----:|-----------------------------|----------|:-------------:|
| 1 | `VALID_SOLUTION_VERIFIED` | archive prev reason; `ASSERT` head CLOSED (I18b/J7); `CreatePendingAssignment(ORIGINAL)` under NEW ids; `StartWake` | **T10 → T5** | **ORIGINAL**, fresh lineage, NEW `RoundID`/`TemplateID` | stays CLOSED — **no reopen** | **No** (K1 explicit) |
| 2 | `ROUND_ACCEPTED` | (as #1) | **T10 → T5** | **ORIGINAL**, NEW ids | stays CLOSED — no reopen | **No** |
| 3 | `ROUND_ABORTED` | (as #1) | **T10 → T5** | **ORIGINAL**, NEW ids | stays CLOSED — no reopen | **No** |
| 4 | `RANGE_EXHAUSTED` / `ASSIGNMENT_REVOKED`, **policy offers a range** | archive reason; `SELECT` policy-offered range (NEW `TemplateID`, I1); `CreatePendingAssignment(ORIGINAL)`; `StartWake` | **T10 → T5** | **ORIGINAL** under new template | already CLOSED — no reopen | **No** |
| 5 | `RANGE_EXHAUSTED` / `ASSIGNMENT_REVOKED`, **no range offered** | `RECORD next_round_disposition(m) ← parked_no_range_offered` | *(none)* | no head created; explicit parked disposition | already CLOSED — no reopen | **No** (recorded parked) |
| 6 | state `OFFLINE` | `RECORD next_round_disposition(m) ← deferred_no_assignment`; rejoin only via a **separate** completed `OFFLINE → REGISTERED` (**T17**) on a later pass (then row for `REGISTERED`) | **T17** first (elsewhere) | no assignment here | n/a | **No** (explicit defer) |
| 7 | state `DISQUALIFIED` | `RECORD next_round_disposition(m) ← deferred_no_assignment` | *(none)* | terminal/absorbing; never assigned | n/a | **No** (explicit defer) |

Sibling `CASE`s of the same `SWITCH`: `REGISTERED` → fresh `ORIGINAL` **T3 → T5**; `RESERVE` → fresh
`ORIGINAL` or a correctly-provenanced `REASSIGNED` suffix (I9) **T4 → T5**;
`ACTIVE_HASHING`/`WAKING`/`EXHAUSTED_PENDING` cannot occur at a fresh round's `ASSIGNMENT`
(`DEFAULT: CONTINUE`, unreachable). Only the range-binding wake edges **T3**/**T4**/**T10** into
`WAKING` are used, each completing at **T5**; no illegal direct `LOW_POWER_LISTEN → ACTIVE_HASHING`
edge is taken, so wake energy is charged (miner SM §3.1).

## 4. Proof — no reason falls through, no closed head reopened

**(P1) Total case coverage.** The `LOW_POWER_LISTEN` inner `SWITCH` matches on `entry_stop_reason(m)`,
whose domain is exactly `{VALID_SOLUTION_VERIFIED, ROUND_ACCEPTED, ROUND_ABORTED, RANGE_EXHAUSTED,
ASSIGNMENT_REVOKED}` (§7 `EnterLowPowerListen` `PRECONDITIONS`; §17a `CASE LOW_POWER_LISTEN` `ASSERT`).
Branch A (`VALID_SOLUTION_VERIFIED ∨ ROUND_ACCEPTED ∨ ROUND_ABORTED`) covers three; branch B
(`RANGE_EXHAUSTED ∨ ASSIGNMENT_REVOKED`) covers the other two, and its own `IF/ELSE` is total (range
offered → T10; else recorded parked). The union is the whole domain with **no residual `DEFAULT`**, so
no `entry_stop_reason` reaches a `CONTINUE`. `VALID_SOLUTION_VERIFIED` in particular is handled by
branch A, exactly the reason the correction targets.

**(P2) No closed head reopened.** Every disposition that creates a head calls
`CreatePendingAssignment` with `assignment_origin = ORIGINAL` (or `REASSIGNED` for the `RESERVE`
sibling), which opens a **fresh lineage** at `assignment_version = 1` (§0.11); it never mutates,
resumes, or re-`CURRENT`s a prior version. Before creating it, branch A `ASSERT`s the prior-round
lineage has **no live head** — it is `CLOSED` (I18b: a CLOSED lineage has zero live heads; J7: closure
is `CLOSED`, not `SUPERSEDED`). No branch invokes **T30**; a `PAUSED`/`CLOSED` head is therefore never
reopened across the boundary. A new `TemplateID` is minted per round, so a fresh assignment can never
bind the old, closed template.

**(P3) Right window, valid set.** The procedure runs strictly after `TemplateCommit` (R3) and strictly
before `ASSIGNMENT → HASHING`: it builds the intended set (all `PENDING`, waking) and only then calls
`CompleteAssignmentPhase` (§2b), whose `ASSERT`s reject any assignment bound to an old
`RoundID`/`TemplateID` and require pairwise disjointness (I1) and one live head per lineage (I18b)
before `TRANSITION round_state → HASHING` (R4). Every next-round head is thus new-id-bound and valid at
R4. ∎

## 5. Worked example — TV81 (finder)

**Setup.** In round `r`, finder `F` paused with `entry_stop_reason = VALID_SOLUTION_VERIFIED` (PATH B);
`r` was `ROUND_ACCEPTED` and `F`'s paused head was `CLOSED` at closure, its reason **preserved** as
`VALID_SOLUTION_VERIFIED` for attribution (§17a). Round `r+1` runs `RoundInitialise` (fresh `RoundID`)
and `TemplateCommit` (new `TemplateID`), reaching `round_state = ASSIGNMENT`.

**Trace (row 1).** `PrepareParticipantsForNewRound` iterates in stable `MinerID` order; for `F` it
takes `CASE LOW_POWER_LISTEN` / `VALID_SOLUTION_VERIFIED ∨ ROUND_ACCEPTED ∨ ROUND_ABORTED`:
`ARCHIVE previous_round_entry_stop_reason(F) ← VALID_SOLUTION_VERIFIED`; `ASSERT` no live head remains
(CLOSED, I18b/J7); `SELECT`s a fresh never-assigned range under the NEW `TemplateID`;
`CreatePendingAssignment(ORIGINAL)` (new lineage `a`, bound to the NEW `RoundID`/`TemplateID`); sets
`lease_start`/`lease_expiry`; `StartWake(from_state = LOW_POWER_LISTEN, driver_envelope = env)` —
**T10**. `VALID_SOLUTION_VERIFIED` does **not** fall into a `DEFAULT/CONTINUE`. At `F`'s own
`WakeCompleteEvent`, `a` activates `PENDING → CURRENT` and `F` enters `ACTIVE_HASHING` — **T5** — before
`ASSIGNMENT → HASHING` (R4, via §2b).

**Outcome.** `F` participates in `r+1` via a fresh new-template `ORIGINAL` assignment (T10 → T5); no
`PAUSED`/`CLOSED` head is reopened; I1/I18b/J7 hold. Reqs: **K1**, J7, I18b.

## 6. Worked example — TV82 (finder + several recipients all return)

**Setup.** In round `r`, finder `F` and certificate-verifying recipients `R1..Rk` all paused with
`entry_stop_reason = VALID_SOLUTION_VERIFIED` (PATH B, §16 `EarlyStopVerify`) on the accepted
certificate; `r` was accepted and **all** their heads were `CLOSED` at closure (each reason preserved).

**Trace + outcome (row 1, per miner).** In `r+1`'s `ASSIGNMENT`, `PrepareParticipantsForNewRound`
processes `F, R1..Rk` in stable `MinerID` order; each independently takes the branch-A
`VALID_SOLUTION_VERIFIED` disposition — archive → `ASSERT` head CLOSED (I18b/J7) → fresh `ORIGINAL`
under the new ids → `StartWake` **T10**, completing at its **own** `WakeCompleteEvent` (**T5**, F5:
concurrent wakes independent). The whole cohort returns via distinct fresh **T10** assignments; no old
assignment is reopened for any of them; no per-miner fall-through. Reqs: **K1**, J7, I18b.

## 7. Acceptance-style PASS checklist

| # | Check | Result |
|--:|-------|--------|
| C1 | `VALID_SOLUTION_VERIFIED` has an **explicit** disposition (branch A) — never a `DEFAULT/CONTINUE` | **PASS** |
| C2 | `VALID_SOLUTION_VERIFIED`/`ROUND_ACCEPTED`/`ROUND_ABORTED` → archive prev reason; `ASSERT` head CLOSED; fresh `ORIGINAL` under NEW ids; `StartWake` **T10 → T5** | **PASS** |
| C3 | `RANGE_EXHAUSTED`/`ASSIGNMENT_REVOKED` → new-round policy applied explicitly: fresh `ORIGINAL` + **T10** if a range is offered, else recorded `parked_no_range_offered` | **PASS** |
| C4 | `OFFLINE` → nothing unless a **separate** completed `OFFLINE → REGISTERED` (**T17**); `DISQUALIFIED` terminal — nothing; both recorded `deferred_no_assignment` | **PASS** |
| C5 | All five `entry_stop_reason`s covered; the `SWITCH` has **no residual `DEFAULT`** for `LOW_POWER_LISTEN` (P1) | **PASS** |
| C6 | No `PAUSED`/`CLOSED` old head reopened/resumed/re-`CURRENT`ed (J7); no **T30** used; fresh heads are new lineages (I18b) (P2) | **PASS** |
| C7 | `CloseRoundAssignments` (§17a) preserves `VALID_SOLUTION_VERIFIED` for attribution; §2a archives it at the next round (I4) | **PASS** |
| C8 | Every new assignment binds the **NEW** `RoundID`/`TemplateID` (never the old, closed one) | **PASS** |
| C9 | Only legal edges: **T3**/**T4**/**T10** into `WAKING`, each completing at **T5**; no direct `LOW_POWER_LISTEN → ACTIVE_HASHING` | **PASS** |
| C10 | Runs after `TemplateCommit` (R3) and before `ASSIGNMENT → HASHING` (R4, via §2b); set valid (I1/I3/I18b) at R4 (P3) | **PASS** |
| C11 | Stable `MinerID` order (G7); driver actions carry a `DriverEventEnvelope` (K4); scheduled via `ScheduleEvent` (J9) | **PASS** |
| C12 | A1 baseline **8.420833333 kWh** unchanged; no new consensus feature; algorithm remains **PoCol** with **the idle policy within PoCol** | **PASS** |

Exercised by **TV81** (a `VALID_SOLUTION_VERIFIED` finder re-assigned via T10, no reopen) and **TV82**
(the finder and several verifying recipients all return via fresh T10 assignments).

## 8. Prohibition clause

The algorithm is named **PoCol** and the mechanism is **the idle policy within PoCol**, exclusively.
No renamed or "enhanced" variant is introduced or implied by K1; the labels *PoCol-E*,
*Energy-Aware PoCol*, and *Enhanced PoCol* are **prohibited** and denote nothing here. K1 adds no
consensus feature, state, or edge — it makes an already-present next-round disposition total over
`entry_stop_reason`. No property (energy, security, fairness, incentive-compatibility) is claimed.

## Result

**Result: NEXT-ROUND PARTICIPATION AUDIT (Stage 1K): PASS** — `PrepareParticipantsForNewRound` (§2a)
makes the `LOW_POWER_LISTEN` next-round disposition **total** over `entry_stop_reason`: the
`VALID_SOLUTION_VERIFIED` case that formerly fell into a `DEFAULT/CONTINUE` — leaving a verified
finder/recipient (whose reason `CloseRoundAssignments` §17a preserves for attribution) with no
executable route back — is now the canonical branch shared with `ROUND_ACCEPTED`/`ROUND_ABORTED`
(archive the prior reason; `ASSERT` the old head is `CLOSED`, never reopening a `PAUSED`/`CLOSED`
version, J7/I18b; bind a fresh `ORIGINAL` `PENDING` to the **NEW** `RoundID`/`TemplateID`; `StartWake`
via **T10**), while `RANGE_EXHAUSTED`/`ASSIGNMENT_REVOKED` apply the new-round policy explicitly (fresh
`ORIGINAL` via **T10** if a range is offered, else recorded parked) and `OFFLINE` (rejoin only via a
completed **T17**) / `DISQUALIFIED` (terminal) receive nothing; every case is explicit with no residual
`DEFAULT` (P1) and no closed head reopened (P2), each miner reaching `ACTIVE_HASHING` at its own
`WakeCompleteEvent` (**T5**) before `ASSIGNMENT → HASHING` (R4, via §2b) — verified by **TV81**/**TV82**,
with the A1 baseline 8.420833333 kWh unchanged and no new consensus feature introduced.
