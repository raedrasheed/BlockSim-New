# Stage 1L — Assignment-Phase Unification Audit (L2)

Audits correction **L2**: there is exactly ONE executable `ASSIGNMENT -> HASHING` path. The R4
transition is performed by the single named owner `CompleteAssignmentPhase` (§2b), and BOTH driver
routes into `HASHING` via the assignment phase — `PrepareParticipantsForNewRound` (§2a) and
`TemplateRefresh` (§19) — reach it through that one procedure. `TemplateRefresh` no longer performs
its own in-line R4: its former `TRANSITION round_state -> HASHING # E8` is REMOVED and replaced by
`CALL CompleteAssignmentPhase(RoundContext)`. The `SOLUTION_PROPAGATION -> HASHING` edge inside
`HandlePropagationFailure` (§16d-bis) is a DISTINCT round-state-machine re-entry, explicitly annotated
NOT R4 and correctly NOT routed through `CompleteAssignmentPhase`. Binds to
`STAGE_01_PROTOCOL_PSEUDOCODE.md` §2b (`PROCEDURE CompleteAssignmentPhase`, the sole R4 body), §2a
(`PROCEDURE PrepareParticipantsForNewRound`, the `CALL CompleteAssignmentPhase(RoundContext)` after
the miner loop), §19 (`PROCEDURE TemplateRefresh`, the `ASSERT round_state = ASSIGNMENT` then
`CALL CompleteAssignmentPhase(RoundContext)`), §16d-bis (`PROCEDURE HandlePropagationFailure`, the
`SOLUTION_PROPAGATION -> HASHING` re-entry gated on `propagation_quiescent`), §9
(`PROCEDURE CaptureSecurityCensusOnApplicabilityEntry`, the K7 applicability-entry census), and §5
(`PROCEDURE HashWorkEvent`, the no-op guard while `round_state = ASSIGNMENT`); to
`STAGE_01_ROUND_STATE_MACHINE.md` R4 (`ASSIGNMENT -> HASHING`); and to
`STAGE_01_INVARIANT_CATALOGUE.md` I1/I3/I18b (disjointness / round-template binding / one-live-head),
G10 (`state_version`), and J1 (coherent census writers). This is a specification act on **PoCol** with
the idle policy within PoCol enabled — not a claim of implementation, enforcement, scheduling,
security, fairness, or any derived property. No new consensus feature is introduced; the eight miner
states and the round-state machine are unchanged, and the A1 baseline (8.420833333 kWh) is untouched.

## 1. The corrected-away problem

After K2 made assignment-phase completion an executable named step (§2b `CompleteAssignmentPhase`),
one driver route into `HASHING` still by-passed it. `TemplateRefresh` (§19), rebuilding the template
after exhaustion or systemic disagreement, ran its OWN in-line `TRANSITION round_state -> HASHING`
(annotated `# E8`) after re-assigning miners — a SECOND executable `ASSIGNMENT -> HASHING` edge that
did NOT run the §2b well-formedness `ASSERT`s and did NOT capture the K7 applicability-entry security
census. Two owners of the same R4 edge meant the census floor could be evaluated on one route
(`PrepareParticipantsForNewRound`) but not the other (`TemplateRefresh`), and the well-formedness
guard was not uniformly applied. L2 removes that second owner.

## 2. The correction

L2 makes `CompleteAssignmentPhase` (§2b) the SINGLE executable `ASSIGNMENT -> HASHING` (R4) owner and
routes every assignment-phase entry to `HASHING` through it:

- **§19 `TemplateRefresh`** — its former in-line `TRANSITION round_state -> HASHING # E8` is REMOVED.
  After building the new domain, waking eligible miners, and asserting difficulty is unchanged (I12),
  it now `ASSERT round_state = ASSIGNMENT` and `CALL CompleteAssignmentPhase(RoundContext)`
  (`# L2: SOLE ASSIGNMENT -> HASHING owner (R4 + K7)`).
- **§2a `PrepareParticipantsForNewRound`** — unchanged from K2: after the miner loop builds the
  intended set it `CALL CompleteAssignmentPhase(RoundContext)` (`# K2: ASSIGNMENT -> HASHING`).
- **§2b `CompleteAssignmentPhase`** — holds the SOLE executable `TRANSITION round_state -> HASHING`
  (R4; bumps `state_version`, G10), preceded by the well-formedness `ASSERT`s (I1/I3/I18b) and
  followed by `CaptureSecurityCensusOnApplicabilityEntry(entered_state = HASHING, at = now)` (K7).

Because both assignment-phase owners funnel through §2b, EVERY entry to `HASHING` via the assignment
phase runs the same `ASSERT` block and captures the same K7 census — so the floor is captured for the
epilogue even at `H_active = 0` with no successful `WakeCompleteEvent` (§9 `H_active(at)` may be 0 at
applicability entry).

The `SOLUTION_PROPAGATION -> HASHING` edge inside §16d-bis `HandlePropagationFailure` is untouched and
is a DIFFERENT round-state-machine edge: a re-entry to `HASHING` after propagation quiescence, gated
on `IF round_state = SOLUTION_PROPAGATION AND propagation_quiescent(RoundContext)`, explicitly
annotated `# SOLUTION_PROPAGATION -> HASHING re-entry (NOT R4)`. It is correctly NOT routed through
`CompleteAssignmentPhase` (whose precondition is `round_state = ASSIGNMENT` with a freshly-bound
`PENDING` set); any census change from resumed miners is captured at their own
`ApplyMinerStateTransition` boundaries (J1), not by an assignment-phase completion.

## 3. Every `-> HASHING` site, classified

The only executable `TRANSITION round_state -> HASHING` statements in
`STAGE_01_PROTOCOL_PSEUDOCODE.md` are two (§2b line 930, §16d-bis line 2096); two further sites reach
`HASHING` by CALLing the §2b owner; the former §19 in-line transition is removed; and §5
`HashWorkEvent` performs no transition and no-ops while `ASSIGNMENT`.

| Site (procedure, §) | Form | Edge | R4? | Routed via `CompleteAssignmentPhase`? | Classification |
|---|---|---|---|---|---|
| §2b `CompleteAssignmentPhase` | `TRANSITION round_state -> HASHING` (`# R4; bumps state_version`) | `ASSIGNMENT -> HASHING` | **Yes** | is the owner | The SOLE executable R4; asserts well-formedness (I1/I3/I18b), bumps `state_version` (G10), then K7 census capture |
| §2a `PrepareParticipantsForNewRound` | `CALL CompleteAssignmentPhase(RoundContext)` (`# K2`) | `ASSIGNMENT -> HASHING` | Yes (delegated) | **Yes** | Assignment-phase entry #1 — new-round participant preparation; performs no in-line R4 |
| §19 `TemplateRefresh` | `ASSERT round_state = ASSIGNMENT` + `CALL CompleteAssignmentPhase(RoundContext)` (`# L2`) | `ASSIGNMENT -> HASHING` | Yes (delegated) | **Yes** | Assignment-phase entry #2 — post-refresh; the former in-line `TRANSITION round_state -> HASHING # E8` is REMOVED |
| §16d-bis `HandlePropagationFailure` | `TRANSITION round_state -> HASHING` (`# SOLUTION_PROPAGATION -> HASHING re-entry (NOT R4)`) | `SOLUTION_PROPAGATION -> HASHING` | **No** | **No** (correctly) | Distinct round-SM re-entry after `propagation_quiescent`; census captured at resumed miners' `ApplyMinerStateTransition` boundaries (J1) |
| §5 `HashWorkEvent` | no transition; guard `round_state not in {HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY}` | — | — | — | Consumer-side no-op: a unit dispatched while `round_state = ASSIGNMENT` `RETURN`s `hash_work_noop`; hashing cannot precede R4 |

There is no third executable `ASSIGNMENT -> HASHING` and no second assignment-phase completion: the
`SOLUTION_PROPAGATION -> HASHING` edge is not an assignment-phase completion, and §19 no longer holds
a private R4.

## 4. Acceptance-style PASS checklist

| # | Check | Result |
|--:|-------|--------|
| C1 | There is exactly ONE executable `ASSIGNMENT -> HASHING` path — `CompleteAssignmentPhase` (§2b) holds the SOLE `TRANSITION round_state -> HASHING` for R4 | **PASS** |
| C2 | BOTH assignment-phase owners route through it: §2a `PrepareParticipantsForNewRound` and §19 `TemplateRefresh` each `CALL CompleteAssignmentPhase(RoundContext)` | **PASS** |
| C3 | `TemplateRefresh` no longer performs its own `ASSIGNMENT -> HASHING`: the former in-line `TRANSITION round_state -> HASHING # E8` is REMOVED, replaced by the `CALL` | **PASS** |
| C4 | Every `HASHING` entry via the assignment phase captures the K7 census — §2b calls `CaptureSecurityCensusOnApplicabilityEntry(HASHING, now)` (§9), so the floor is captured even at `H_active = 0` with no successful wake | **PASS** |
| C5 | The `SOLUTION_PROPAGATION -> HASHING` re-entry (§16d-bis `HandlePropagationFailure`) is a DISTINCT edge, explicitly annotated NOT R4, gated on `propagation_quiescent`, and NOT routed through `CompleteAssignmentPhase` — not a second assignment-phase completion | **PASS** |
| C6 | Census changes from resumed miners after propagation failure are captured at their `ApplyMinerStateTransition` boundaries (J1), not by an assignment-phase completion | **PASS** |
| C7 | §5 `HashWorkEvent` performs no `-> HASHING` transition and no-ops while `round_state = ASSIGNMENT`; hashing begins only after R4 and each miner's own `WakeCompleteEvent` | **PASS** |
| C8 | §2b/§2a/§19/§16d-bis, R4, I1/I3/I18b/G10/J1, and §9 all AGREE; A1 continuous full-participation baseline **8.420833333 kWh** unchanged; any energy change is attributable ONLY to reduced active power-time; no new consensus feature | **PASS** |

## Result

**Result: ASSIGNMENT-PHASE UNIFICATION AUDIT (Stage 1L): PASS** — `CompleteAssignmentPhase` (§2b) is
the SINGLE executable `ASSIGNMENT -> HASHING` (R4) owner, holding the only `TRANSITION round_state ->
HASHING` for that edge (bumping `state_version` per G10 after the I1/I3/I18b well-formedness `ASSERT`s
and before the K7 `CaptureSecurityCensusOnApplicabilityEntry(HASHING, now)`, §9); both assignment-phase
routes — §2a `PrepareParticipantsForNewRound` and §19 `TemplateRefresh` — reach `HASHING` by CALLing
it, with `TemplateRefresh`'s former in-line `TRANSITION round_state -> HASHING # E8` REMOVED, so every
entry to `HASHING` via the assignment phase captures the applicability-entry census even at
`H_active = 0` with no successful wake; the `SOLUTION_PROPAGATION -> HASHING` re-entry in §16d-bis
`HandlePropagationFailure` is a distinct round-state-machine edge, explicitly annotated NOT R4, gated
on `propagation_quiescent`, correctly NOT routed through `CompleteAssignmentPhase`, and not a second
assignment-phase completion (its census changes are captured at resumed miners'
`ApplyMinerStateTransition` boundaries per J1); §5 `HashWorkEvent` no-ops while `round_state =
ASSIGNMENT` — with §2b/§2a/§19/§16d-bis, R4, I1/I3/I18b/G10/J1, and §9 all agreeing, the A1 baseline
8.420833333 kWh unchanged (any energy change attributable only to reduced active power-time), and no
new consensus feature.
