# Stage 1K — Assignment-Phase Audit (K2)

Audits correction **K2**: assignment-phase completion is an EXECUTABLE named step, not explanatory
prose. The `ASSIGNMENT -> HASHING` transition (R4) is performed by the named procedure
`CompleteAssignmentPhase`, which first ASSERTs the intended assignment set is well-formed and then
transitions the round; a `HashWorkEvent` dispatched while the round is still `ASSIGNMENT` is a no-op.
Binds to `STAGE_01_PROTOCOL_PSEUDOCODE.md` §2b `Assignment-phase completion (K2)`
(`PROCEDURE CompleteAssignmentPhase`, full body), §2a `Next-round participant preparation (J5)`
(`PROCEDURE PrepareParticipantsForNewRound`, the `CALL CompleteAssignmentPhase(RoundContext)` after
the miner loop), and §5 `Active hashing (event-scheduled, G9)` (`PROCEDURE HashWorkEvent`, the guard
`round_state not in {HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY}` and its K2 no-op NOTE); to
`STAGE_01_ROUND_STATE_MACHINE.md` R3 (`TEMPLATE_COMMITMENT -> ASSIGNMENT`) / R4
(`ASSIGNMENT -> HASHING`, `AssignmentSetValid`); to `STAGE_01_INVARIANT_CATALOGUE.md` I1/I3/I18b
(disjointness / round-template binding / one-live-head) and G10 (`state_version`); and to
`STAGE_01K_SEMANTIC_TEST_VECTORS.md` TV83/TV84. This is a specification act on **PoCol** with the idle
policy within PoCol enabled — not a claim of implementation, enforcement, scheduling, security,
fairness, or any derived property. No new consensus feature is introduced; the eight miner states and
the round-state machine are unchanged, and the A1 baseline (8.420833333 kWh) is untouched.

## 1. The corrected-away problem

R4 (`ASSIGNMENT -> HASHING`) existed only as an explanatory row in the round-state machine — narrative
prose describing that "hashing may begin" after the assignment set is valid, with NO executable step
that actually performed the transition. Two failure modes followed. First, a round could remain in
`ASSIGNMENT` with a complete, waking assignment set yet never advance, because nothing was specified to
drive R4; hashing was **stranded behind `ASSIGNMENT`**. Second, the well-formedness conditions R4
names as its guard (`AssignmentSetValid`: disjoint per I1, bound to `RoundID`+`TemplateID` per I3) were
never checked at a definite point, so entry to `HASHING` was not gated on the set being sound.

## 2. The correction

K2 makes assignment-phase completion an EXECUTABLE named procedure (§2b `CompleteAssignmentPhase`):

- It ASSERTs the intended set is **well-formed** before entering `HASHING`: every `PENDING` assignment
  is bound to the current `(RoundID, TemplateID)` (I3), ranges are pairwise disjoint (I1), each
  lineage has exactly one live head (I18b), and NO assignment references an old `RoundID`/`TemplateID`.
- It performs the SOLE executable **`TRANSITION round_state -> HASHING`** (R4), which bumps
  `state_version` (G10) — never a prose-only R4.
- It then CALLs `CaptureSecurityCensusOnApplicabilityEntry(entered_state = HASHING, at = now)` (K7),
  so the applicability-entry census is captured on entry even if no `WakeCompleteEvent` later succeeds.
- §2a `PrepareParticipantsForNewRound` CALLs it once, after the miner loop has built the intended set:
  `CALL CompleteAssignmentPhase(RoundContext)   # K2: ASSIGNMENT -> HASHING`.

Hashing therefore begins ONLY after this transition, and then only at each miner's own
`WakeCompleteEvent`.

## 3. Mechanism (§2b `CompleteAssignmentPhase`, verbatim)

Preconditions and effects, quoted from `STAGE_01_PROTOCOL_PSEUDOCODE.md` §2b:

```
PRECONDITIONS: round_state = ASSIGNMENT; a committed RoundID and TemplateID exist; the intended
               assignment set has been established; every PENDING assignment satisfies I1/I3/I18b;
               NO assignment is bound to an old RoundID or TemplateID
EFFECTS:
    ASSERT for every PENDING assignment a: bound to (RoundID_current, TemplateID_committed)   # I3
           AND disjoint per I1 AND its lineage has exactly one live head (I18b)
    ASSERT no assignment references an old RoundID/TemplateID
    TRANSITION round_state -> HASHING                            # R4; bumps state_version (G10)
    CALL CaptureSecurityCensusOnApplicabilityEntry(RoundContext, entered_state = HASHING, at = now)
```

The transition is the SOLE executable `ASSIGNMENT -> HASHING` step. §2b's NOTE binds it to §5: a
`HashWorkEvent` is never scheduled into a round that remains `ASSIGNMENT`, and one dispatched while
`round_state != HASHING` is a no-op.

## 4. Precondition ASSERTs and what each guards

| ASSERT / precondition (§2b) | Invariant | What it guards against |
|---|---|---|
| `round_state = ASSIGNMENT` on entry | R3→R4 ordering | Entering `HASHING` from any state other than the completed `ASSIGNMENT` phase |
| a committed `RoundID` and `TemplateID` exist | I3 | Completing the phase before `TemplateCommit` (R3) has frozen the template |
| every `PENDING` bound to `(RoundID_current, TemplateID_committed)` | I3 | A stray assignment bound to the wrong (or no) round/template entering `HASHING` |
| ranges pairwise disjoint | I1 | Two live assignments overlapping on the nonce domain at hashing start |
| each lineage has exactly one live head | I18b | A headless or double-headed lineage (e.g. a phantom SUPERSEDED-without-successor, J7) |
| NO assignment references an old `RoundID`/`TemplateID` | I3 | A prior-round/stale-template assignment being carried live into the new round's `HASHING` |
| `TRANSITION round_state -> HASHING` bumps `state_version` | G10 | An un-versioned state change; stale readers observing an ambiguous phase across R4 |

## 5. The `HashWorkEvent` guard (§5, verbatim)

`HashWorkEvent`'s stale/cancelled-work guard rejects any unit dispatched outside a hashing-capable
state, quoted from §5:

```
IF miner_state(MinerID) != ACTIVE_HASHING
   OR status(assignment) != CURRENT
   OR RoundID != RoundID_current OR TemplateID != TemplateID_committed
   OR round_state not in {HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY}:   # E6/G8 hashing-capable states
  RETURN hash_work_noop
```

`ASSIGNMENT` is NOT in `{HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY}`, so any `HashWorkEvent`
dispatched while `round_state = ASSIGNMENT` (before `CompleteAssignmentPhase` performed R4) `RETURN`s
`hash_work_noop`. Hashing begins only AFTER the explicit `ASSIGNMENT -> HASHING` transition (K2) and
each miner's own `WakeCompleteEvent`.

## 6. Worked examples

### TV83 — transition before any hash work

**Preconditions.** Round `r+1` is in `ASSIGNMENT`; `PrepareParticipantsForNewRound` has built the
intended assignment set (all `PENDING`, waking).

**Trace.** After the miner loop, §2a CALLs `CompleteAssignmentPhase`. It ASSERTs every `PENDING` is
bound to `(RoundID_current, TemplateID_committed)` and satisfies I1/I3/I18b, then
`TRANSITION round_state -> HASHING` (R4; bumps `state_version`, G10) and
`CaptureSecurityCensusOnApplicabilityEntry(HASHING)` (K7). Only then does hashing begin, at each
miner's own `WakeCompleteEvent`.

**Expected.** `ASSIGNMENT -> HASHING` is an executable named-procedure step; the round is in `HASHING`
before any `HashWorkEvent` executes. Matches TV83 (Reqs **K2**, K7).

### TV84 — `HashWorkEvent` no-op in `ASSIGNMENT`, executes after completion

**Preconditions.** A `HashWorkEvent` is dispatched while `round_state = ASSIGNMENT` (before
`CompleteAssignmentPhase`); later, after `ASSIGNMENT -> HASHING`, a new `HashWorkEvent` is dispatched.

**Trace.** The first unit hits the guard `round_state not in {HASHING, SOLUTION_PROPAGATION,
SECURITY_RECOVERY}` (`ASSIGNMENT` is not hashing-capable) → `RETURN hash_work_noop` (K2). After
`CompleteAssignmentPhase` puts the round in `HASHING`, the later unit — miner `ACTIVE_HASHING`, version
`CURRENT`, `(RoundID, TemplateID)` current — passes the guard and executes normally.

**Expected.** Hashing cannot be stranded behind `ASSIGNMENT`; the pre-transition unit is a no-op, the
post-transition unit runs. Matches TV84 (Reqs **K2**).

## 7. Acceptance-style PASS checklist

| # | Check | Result |
|--:|-------|--------|
| C1 | `ASSIGNMENT -> HASHING` (R4) is an EXECUTABLE named step — `PROCEDURE CompleteAssignmentPhase` (§2b), not prose-only | **PASS** |
| C2 | It ASSERTs well-formedness before transition: every `PENDING` bound to `(RoundID_current, TemplateID_committed)` (I3), disjoint (I1), one live head (I18b), no old-`RoundID`/`TemplateID` reference | **PASS** |
| C3 | The `TRANSITION round_state -> HASHING` is the SOLE executable R4 and bumps `state_version` (G10) | **PASS** |
| C4 | On entry to `HASHING` it CALLs `CaptureSecurityCensusOnApplicabilityEntry(HASHING, now)` (K7) | **PASS** |
| C5 | §2a `PrepareParticipantsForNewRound` CALLs `CompleteAssignmentPhase` once, after building the set | **PASS** |
| C6 | `ASSIGNMENT` is not a hashing-capable state; a `HashWorkEvent` dispatched in `ASSIGNMENT` `RETURN`s `hash_work_noop` (§5 guard); hashing begins only after R4 and each miner's `WakeCompleteEvent` | **PASS** |
| C7 | §2b, §2a, §5, R3/R4, I1/I3/I18b/G10, and TV83/TV84 all AGREE | **PASS** |
| C8 | A1 continuous full-participation baseline **8.420833333 kWh** unchanged; no new consensus feature | **PASS** |

Exercised by **TV83** (transition performed before any hash work) and **TV84** (`HashWorkEvent` no-op
in `ASSIGNMENT`, executes after completion).

## Result

**Result: ASSIGNMENT PHASE AUDIT (Stage 1K): PASS** — assignment-phase completion is an EXECUTABLE
named procedure (§2b `CompleteAssignmentPhase`), CALLed once by §2a `PrepareParticipantsForNewRound`
after the intended set is built; it ASSERTs the set is well-formed (every `PENDING` bound to the
current `RoundID`/`TemplateID` per I3, disjoint per I1, one live head per I18b, no assignment bound to
an old `RoundID`/`TemplateID`), performs the SOLE executable `TRANSITION round_state -> HASHING` (R4,
bumping `state_version` per G10), and captures the applicability-entry security census (K7); a
`HashWorkEvent` dispatched while `round_state = ASSIGNMENT` is a no-op (`hash_work_noop`, §5 guard) so
hashing can never be stranded behind `ASSIGNMENT` and begins only after R4 and each miner's own
`WakeCompleteEvent` — with §2b/§2a/§5, R3/R4, I1/I3/I18b/G10, and TV83/TV84 all agreeing, the A1
baseline 8.420833333 kWh unchanged, and no new consensus feature.
