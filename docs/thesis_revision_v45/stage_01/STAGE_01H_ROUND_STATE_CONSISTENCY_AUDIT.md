# Stage 1H — Round-State Consistency Audit (H1)

Documentation-only audit of correction **H1**: the round state machine of **PoCol** is
consolidated into a single, internally-consistent model in which the round-state and the
propagation set are **NOT identified**. This deliverable verifies that each previously
contradictory statement has been corrected away in the CURRENT
`STAGE_01_ROUND_STATE_MACHINE.md` text and that every surviving statement agrees with
`STAGE_01_PROTOCOL_PSEUDOCODE.md`. It audits wording and control structure only; it claims
**no** security, fairness, or incentive property, adds **no new consensus feature**, and
concerns the idle policy within PoCol. No property is experimentally supported at Stage 1.

---

## 1. Corrected-away contradictions (each confirmed gone)

**H1.1 — No round-state ⇔ propagation-set "iff".** The old §2.6 wording ("the round is
`SOLUTION_PROPAGATION` iff the set is non-empty") is removed. The current §2.6 "Active
propagation set (F3, refined G6; NOT identified with the round-state, G8/H1)" paragraph states
explicitly: *"There is NO `iff` tying the round-state to the set (H1): a non-empty set does not
force `SOLUTION_PROPAGATION` (the same live candidates are preserved while the round is in
`SECURITY_RECOVERY`, G8), and the round leaves `SOLUTION_PROPAGATION` only when
`propagation_quiescent` holds (set empty AND no pending acceptance batch AND no live candidate
acceptance event AND `block_accepted` false)."* This matches pseudocode §0.6, whose closing
sentence reads *"The round-state and the propagation set are NOT identified"* and which names
`propagation_quiescent` as the ONLY condition returning the round to `HASHING`. **Confirmed: the
round-state and the propagation set are NOT identified.**

**H1.2 — `active_propagation_set` holds EXACTLY {`PROPAGATING`, `PENDING_ACCEPTANCE`} (G6).**
§2.6 now states the set holds *"EXACTLY the propagation-active contexts — those with `status ∈
{PROPAGATING, PENDING_ACCEPTANCE}` (G6). `DISCOVERED` and `SELF_VALIDATED` contexts exist but are
NOT yet in the set; `FAILED`/`ACCEPTED`/`COMPETING`/`STALE`/`CANCELLED` contexts have LEFT it. It
is therefore NOT 'every live context'."* This is the exact membership rule of pseudocode §0.8
(`# active_propagation_set membership (G6) = { cpc : status(cpc) in {PROPAGATING,
PENDING_ACCEPTANCE} }`) and §0.6. The nine-value `CANDIDATE_STATUS` enum of §0.8 makes every
status reachable; `ScheduleSolutionPropagation` (§16b) walks `DISCOVERED → SELF_VALIDATED →
PROPAGATING` and only `ADD cpc to active_propagation_set` at `PROPAGATING`. **Confirmed: round-SM
matches the pseudocode membership rule.**

**H1.3 — Acceptance may occur from `SOLUTION_PROPAGATION` OR `SECURITY_RECOVERY` (R6; G8).** §2.7
`ROUND_ACCEPTED` entry now reads *"From `SOLUTION_PROPAGATION` **or `SECURITY_RECOVERY`** (G8/H1)
on a validated accepted candidate — the atomic result of `AcceptanceBatchFinalize →
ValidBlockAccept` (R6). A block arrival never closes the round directly; acceptance is causally
downstream of arbitration (G5)."* The R6 `current_round_state` column lists
`SOLUTION_PROPAGATION` **or `SECURITY_RECOVERY`** (G8). This matches `ValidBlockAccept` (§17),
whose precondition is `round_state in {SOLUTION_PROPAGATION, SECURITY_RECOVERY}` and which
performs a **single** `TRANSITION round_state → ROUND_ACCEPTED`; and `AcceptanceBatchFinalize`
(§16e), the single arbitration+closure point that invokes `ValidBlockAccept` after microphase 3
collected all same-timestamp arrivals. `BlockAcceptancePoint` (§16d) only REGISTERS and returns.
**Confirmed: acceptance is the atomic downstream result of arbitration, from SP or SR.**

**H1.4 — Same-timestamp authority is the microphase spec, not the frozen F table.** §2.6
"Same-timestamp event order" now cites *"(authoritative: `STAGE_01G_EVENT_MICROPHASE_SPEC.md`,
extended by the H2 delta-cycle rule)"* and states *"The frozen Stage-1F
`STAGE_01F_EVENT_PRIORITY_TABLE.md` is **NOT** authoritative (superseded by the microphase model,
G5/H1)."* This matches pseudocode §0.7 (identical authority statement) and §0.7-H2 (delta-cycle
forward-scheduling rule). The microphase spec §7 corroborates: the F priority table "remains a
**frozen historical artifact** and is not authoritative." **Confirmed: F table is not
authoritative.**

**H1.5 — Surviving transitions are mutually consistent** (see §3).

## 2. Ten round states — one-line consistency check

| Round state | Consistency check vs consolidated model / pseudocode |
|---|---|
| `ROUND_INITIALISING` | Non-propagation; `RoundInitialise` (§1) sets `active_propagation_set ← empty`; entered at genesis or R20/R21. No set coupling. Consistent. |
| `TEMPLATE_COMMITMENT` | Pre-hashing; no propagation-active contexts; entered via R2 or refresh R17. Consistent. |
| `ASSIGNMENT` | Pre-hashing; no set coupling; a legal R13 target when recovery ends quiescent (re-partition). Consistent. |
| `HASHING` | Hashing-capable (E6/G8); set empty here — the first propagation-active context performs `HASHING → SOLUTION_PROPAGATION` (R5, `ScheduleSolutionPropagation`); re-entered from SP only when `propagation_quiescent` (R7). Consistent. |
| `SECURITY_RECOVERY` | MAY coexist with a non-empty `active_propagation_set` (§2.5 G8); entered from `HASHING` (R10) or `SOLUTION_PROPAGATION` (R8, live contexts preserved); may accept (R6) or exit to `SOLUTION_PROPAGATION`/`ASSIGNMENT` (R13) or `ROUND_ABORTED` (R14). Not identified with the set. Consistent. |
| `SOLUTION_PROPAGATION` | Set non-empty (≥1 `PROPAGATING`/`PENDING_ACCEPTANCE`); leaves ONLY on `propagation_quiescent` (R7), coincident floor breach (R8), or acceptance (R6). No iff — a non-empty set does not force SP (preserved through SR). Consistent. |
| `ROUND_ACCEPTED` | Terminal-accept; entered from SP **or SR** (R6) as the atomic result of `AcceptanceBatchFinalize → ValidBlockAccept`; a block arrival never closes directly (G5). Consistent. |
| `ROUND_EXHAUSTED` | Non-propagation; entered from `HASHING` (R9) on accepted whole-domain exhaustion; no set coupling. Consistent. |
| `TEMPLATE_REFRESH` | Non-propagation; from `ROUND_EXHAUSTED` (R15) or `HASHING` (R11); ALWAYS returns to `TEMPLATE_COMMITMENT` (R17), never bypassing it. Consistent. |
| `ROUND_ABORTED` | Terminal-abort; from `SECURITY_RECOVERY` (R14), `HASHING` (R12), `ROUND_EXHAUSTED` (R16), `TEMPLATE_REFRESH` (R19). Consistent. |

## 3. Relevant transitions — consolidated model

| R# | Source(s) → target | Guard summary | Pseudocode anchor |
|---|---|---|---|
| **R5** | `HASHING` → `SOLUTION_PROPAGATION` | First propagation-active context (`was_empty AND round_state = HASHING`) at the first valid found solution | `ScheduleSolutionPropagation` §16b |
| **R6** | `SOLUTION_PROPAGATION` **or `SECURITY_RECOVERY`** → `ROUND_ACCEPTED` | Winner of the atomic `AcceptanceBatchFinalize` after all same-timestamp arrivals collected; `I2`(discovery-time, G1)∧`I3`; `block_accepted` false | `AcceptanceBatchFinalize` §16e → `ValidBlockAccept` §17 |
| **R7** | `SOLUTION_PROPAGATION` → `HASHING` | `propagation_quiescent` holds (set empty ∧ no pending batch ∧ no live acceptance event ∧ not accepted) | `HandlePropagationFailure` §16d-bis; `propagation_quiescent` §0.6 |
| **R8** | `SOLUTION_PROPAGATION` → `SECURITY_RECOVERY` | Candidate failed AND `H_honest(t)` below floor; **PRESERVES** remaining live contexts | `HandlePropagationFailure` §16d-bis (round stays in recovery, G8) |
| **R10** | `HASHING` → `SECURITY_RECOVERY` | `SecurityFloorEvaluate` reports breach / invariant-risk | §0.7c terminal-guarded `SecurityFloorEvaluate` |
| **R13** | `SECURITY_RECOVERY` → `ASSIGNMENT`(→`HASHING` at R4) **or `SOLUTION_PROPAGATION`** | Floor restored; re-partition when `propagation_quiescent`, else resume propagation if set still non-empty (G8) | `propagation_quiescent` §0.6; §0.7-H2 settled-census (microphase 5) |
| **R14** | `SECURITY_RECOVERY` → `ROUND_ABORTED` | Floor unrecoverable (insufficient reserves) | Terminal-abort; `SecurityFloorEvaluate` G10 |

**Mutual consistency.** R5 is the sole entry into `SOLUTION_PROPAGATION` and fires exactly when
the set transitions empty→non-empty in `HASHING`; so `HASHING` always carries an empty set,
consistent with R7 returning there only on `propagation_quiescent`. R8 diverts a floor breach
during propagation into `SECURITY_RECOVERY` **without** clearing the set — the same live
candidates the "iff" would have forced into `SOLUTION_PROPAGATION` now sit in `SECURITY_RECOVERY`,
which is exactly why the iff had to go (H1.1). R13 is the inverse: on floor restoration the round
returns to `SOLUTION_PROPAGATION` if the preserved set is non-empty, else re-`ASSIGNMENT`→`HASHING`
when quiescent. R6 accepts from **either** propagation state, matching `ValidBlockAccept`'s
`round_state in {SOLUTION_PROPAGATION, SECURITY_RECOVERY}` precondition and its single closure.
R10/R14 bound the recovery state's non-propagation entry and abort exit. Every guard is expressed
over `propagation_quiescent` (§0.6) or the floor census, never over "round-state = SP ⇔ set
non-empty". The transitions are therefore mutually consistent and consistent with the pseudocode.

## 4. Acceptance-style PASS checklist

| # | Check | Result | Ground |
|---|---|---|---|
| C1 | No round-state ⇔ set "iff"; round-state and set NOT identified | PASS | §2.6 "Active propagation set" (NO `iff`, H1); §2.5 G8; pseudocode §0.6 |
| C2 | `active_propagation_set` = EXACTLY {`PROPAGATING`, `PENDING_ACCEPTANCE`} | PASS | §2.6 (G6); pseudocode §0.8 membership rule; §0.6 |
| C3 | Acceptance from `SOLUTION_PROPAGATION` OR `SECURITY_RECOVERY` (R6) | PASS | §2.7 entry; R6 source column; `ValidBlockAccept` §17 precondition |
| C4 | Microphase spec authoritative; F priority table NOT | PASS | §2.6 "Same-timestamp event order"; pseudocode §0.7; microphase spec §7 |
| C5 | Round-SM agrees with pseudocode (states, transitions, guards) | PASS | §2/§4 vs §0.6/§0.7/§0.8/§16b/§16d/§16e/§17 |
| C6 | Single atomic closure (`AcceptanceBatchFinalize → ValidBlockAccept`; block arrival never closes directly) | PASS | §16d register-only; §16e once per (ts, point); §17 `block_accepted` guard; §2.7 (G5) |
| C7 | R5/R6/R7/R8/R10/R13/R14 mutually consistent | PASS | §3 cross-check |
| C8 | No new consensus feature introduced | PASS | Wording/structure audit only; idle policy within PoCol |
| C9 | A1 baseline unchanged | PASS | 8.420833333 kWh; no round-SM change touches the baseline |

---

## Result

**ROUND-STATE CONSISTENCY AUDIT (Stage 1H): PASS** — the consolidated PoCol round model removes
the round-state ⇔ propagation-set "iff" (§2.6, §0.6): the round-state and the
`active_propagation_set` are NOT identified, the set holds EXACTLY the `{PROPAGATING,
PENDING_ACCEPTANCE}` contexts (G6, §0.8), acceptance may occur from `SOLUTION_PROPAGATION` OR
`SECURITY_RECOVERY` as the single atomic result of `AcceptanceBatchFinalize → ValidBlockAccept`
(R6/G8, §17), and the authoritative same-timestamp contract is
`STAGE_01G_EVENT_MICROPHASE_SPEC.md` extended by the H2 delta-cycle rule while the frozen
`STAGE_01F_EVENT_PRIORITY_TABLE.md` is not; transitions R5/R6/R7/R8/R10/R13/R14 are mutually
consistent and consistent with the pseudocode `propagation_quiescent` predicate and
`ValidBlockAccept`, with no new consensus feature and the A1 baseline (8.420833333 kWh) unchanged.
