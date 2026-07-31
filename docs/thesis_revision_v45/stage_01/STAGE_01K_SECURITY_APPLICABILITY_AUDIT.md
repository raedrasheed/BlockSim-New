# Stage 1K — Security-Floor Applicability Audit (K7 security-census evaluation on applicability entry)

Documentation-only audit of correction **K7**: the security floor is now evaluated when the round
**ENTERS a floor-applicable state**, not only when a miner-state boundary happens to set the census.
`CaptureSecurityCensusOnApplicabilityEntry` (§9) computes the `ACTIVE_HASHING` census on entry to
`HASHING` (via `CompleteAssignmentPhase`, K2, §2b) and to `SOLUTION_PROPAGATION` (via
`ScheduleSolutionPropagation`, §16b) and writes `security_census_dirty[at]` **and**
`latest_security_census[at]` (with full provenance) **together atomically** (J1). It is the **second
coherent writer** of that pair; the first is `ApplyMinerStateTransition` (§0.9, F6). This is a structural
audit of the specification text (`STAGE_01_PROTOCOL_PSEUDOCODE.md` §9
`CaptureSecurityCensusOnApplicabilityEntry` / §9 `FinalizeEventTimeSecurityCensus` +
`SecurityFloorEvaluate`, §2b `CompleteAssignmentPhase`, §16b `ScheduleSolutionPropagation`, §0.8
registries J1/K7 two-writer note; `STAGE_01_INVARIANT_CATALOGUE.md` I16/I17). It EXTENDS
`STAGE_01J_SECURITY_APPLICABILITY_AUDIT.md` (J6 applicability-before-breach, unchanged here) and
`STAGE_01J_SECURITY_CENSUS_COHERENCE_AUDIT.md` (J1 atomic dirty/latest, J8 provenance — the "sole
writer" of Stage 1J becomes the FIRST of two coherent writers under K7). It describes **PoCol** with
**the idle policy within PoCol** enabled and claims **no property** (energy, security, fairness,
incentive) beyond the evaluation-triggering structure defined here; no new consensus feature is
introduced. The strings "PoCol-E", "Energy-Aware PoCol", and "Enhanced PoCol" are prohibited. The
accepted A1 baseline is `8.420833333 kWh` and is UNCHANGED — any energy change is attributable ONLY to
reduced active power-time, never to this census-triggering correction.

---

## 1. The corrected-away problem (a floor-applicable state entered with no boundary → no floor decision)

Before K7, `security_census_dirty[t]` / `latest_security_census[t]` were set by exactly **one** writer,
`ApplyMinerStateTransition` (§0.9), and only on a miner-state boundary that changed the `ACTIVE_HASHING`
census. The event-time epilogue `FinalizeEventTimeSecurityCensus(t)` (§9) evaluates the floor **only when
`security_census_dirty[t]` is true**. So a round could ENTER a floor-applicable state at an `event_time`
where **no miner-state boundary occurred**, leaving the dirty flag unset and the epilogue returning
`no_census_change` — **no floor decision fired at the entry**.

The load-bearing case is `ASSIGNMENT → HASHING` with `H_active = 0` because **no `WakeCompleteEvent` has
yet succeeded** (§2b; §0.10). That transition is a `TRANSITION round_state` step (R4), **not** a
`CALL ApplyMinerStateTransition` — it moves no miner, so it wrote no census and set no dirty flag. A round
could then sit in `HASHING` (floor-applicable, J6) with zero active hash rate yet record **no** I16 breach
and take **no** recovery decision, because nothing at that `event_time` had marked the census dirty.

## 2. The correction (K7) — `CaptureSecurityCensusOnApplicabilityEntry`, the second coherent writer

`CaptureSecurityCensusOnApplicabilityEntry(RoundContext, entered_state, at)` (§9) computes the census
from the post-entry `ACTIVE_HASHING` set and writes the coherence pair itself:

```
    SET H_honest(at)      <- SUM over honest miners in ACTIVE_HASHING of modeled hash rate
    SET H_adversarial(at) <- SUM over adversarial miners in ACTIVE_HASHING of modeled hash rate
    SET H_active(at)      <- H_honest(at) + H_adversarial(at)          # I17 (may be 0 at applicability entry)
    IF H_active(at) = 0: SET q_adv(at) <- NA  ELSE q_adv(at) <- H_adversarial(at)/H_active(at)
    ATOMICALLY:                                                        # J1: dirty + latest together
      SET latest_security_census[at] <- census_record(RoundID_at_census, TemplateID_at_census,
            state_version_at_census, census_seq = applicability_entry(entered_state, at),
            H_active, H_honest, H_adversarial, q_adv)                  # J8 full provenance
      SET security_census_dirty[at]  <- true
```

**The two coherent writers of `security_census_dirty` / `latest_security_census` (§0.8 J1/K7 note):**

| # | Writer | Boundary kind | Fires when |
|---|--------|---------------|------------|
| 1 | `ApplyMinerStateTransition` (§0.9, F6) | miner-state boundary | a transition changes the `ACTIVE_HASHING` census (step (5f)) |
| 2 | `CaptureSecurityCensusOnApplicabilityEntry` (§9, K7) | round-state applicability-entry boundary | the round ENTERS a floor-applicable state, even with **no** miner-state boundary at `at` |

Both writers write the **two maps together in one atomic step**, so the J1 invariant
`security_census_dirty[t] = true ⇒ latest_security_census[t] exists` holds for either writer. **Entry
points wired** (the only two call sites):

| Entry point | Site (§) | Call |
|-------------|----------|------|
| `CompleteAssignmentPhase` | §2b (K2) | after `TRANSITION round_state -> HASHING` (R4): `CALL CaptureSecurityCensusOnApplicabilityEntry(HASHING, at = now)` |
| `ScheduleSolutionPropagation` | §16b | on the FIRST propagation-active context, after `TRANSITION round_state -> SOLUTION_PROPAGATION`: `CALL CaptureSecurityCensusOnApplicabilityEntry(SOLUTION_PROPAGATION, at = now)` |

The event-time epilogue `FinalizeEventTimeSecurityCensus(at)` (§9, I-01/I-02) then finds
`security_census_dirty[at] = true`, reads `latest_security_census[at]` (with its stored J8 provenance),
and invokes `SecurityFloorEvaluate` **once** — so the floor is decided on entry to the applicable state
even when no wake succeeded and no miner boundary occurred.

## 3. Which entered state captures, where it is wired, and why

| `entered_state` | capture on entry? | where wired | why |
|-----------------|-------------------|-------------|-----|
| `HASHING` | **yes** | `CompleteAssignmentPhase` §2b (K2) | `ASSIGNMENT → HASHING` (R4) moves no miner; without capture, entry with `H_active = 0` (no successful wake) would set no dirty flag and skip the floor decision |
| `SOLUTION_PROPAGATION` | **yes** | `ScheduleSolutionPropagation` §16b | `HASHING → SOLUTION_PROPAGATION` on the first propagation-active context is a `TRANSITION round_state` (E6), not a miner boundary; capture makes the epilogue decide the floor at that entry |
| `SECURITY_RECOVERY` | **no** (see §5) | — | entry is itself the RESULT of a `SecurityFloorEvaluate` on an already-coherent census at the SAME `event_time`; re-capturing would re-dirty a finalising `event_time` |
| `ASSIGNMENT` / `ROUND_INITIALISING` / `TEMPLATE_COMMITMENT` / `ROUND_EXHAUSTED` / `TEMPLATE_REFRESH` / terminal | **never invoked** | — | non-applicable (J6); `CaptureSecurityCensusOnApplicabilityEntry` is NEVER called there, so it creates no census and no breach in a non-applicable state |

## 4. J1 coherence preserved, and no breach created in a non-applicable state (J6)

**J1 coherence.** Adding a second writer does not weaken J1: `CaptureSecurityCensusOnApplicabilityEntry`
sets `security_census_dirty[at]` **inside the same `ATOMICALLY` block** that writes
`latest_security_census[at]`, exactly as `ApplyMinerStateTransition` does (§0.9 step (5f)). Neither map is
ever written without the other, so the epilogue's `ASSERT latest_security_census[event_time] EXISTS`
(§9 `FinalizeEventTimeSecurityCensus`) is grounded for either writer. Newest-wins overwrite is
order-preserving: if a miner boundary and an applicability entry occur at the same `at`, whichever writes
last leaves a coherent `(dirty, latest)` pair carrying its own provenance, and the epilogue reads one
settled census once (I-01).

**J6 — no breach in a non-applicable state.** `CaptureSecurityCensusOnApplicabilityEntry` is invoked ONLY
for `entered_state ∈ {HASHING, SOLUTION_PROPAGATION}` (SECURITY_RECOVERY excepted, §5); it **NEVER runs
while the round is `ASSIGNMENT`** or any setup / refresh / exhausted state, so it never dirties a census in
a non-applicable state. Capture fires **after** the `TRANSITION round_state -> HASHING`/`-> SOLUTION_PROPAGATION`
completes, so `round_state` is already the applicable state when the epilogue evaluates — any breach is
attributed to the applicable state, never to `ASSIGNMENT`. And even a stray dirty flag in a setup state is
harmless: `SecurityFloorEvaluate`'s J6 guard `IF round_state NOT in {HASHING, SOLUTION_PROPAGATION,
SECURITY_RECOVERY}` records ONLY a `security_census_observation`, never an I16 `breach_event`
(`STAGE_01J_SECURITY_APPLICABILITY_AUDIT.md`).

## 5. `SECURITY_RECOVERY` needs no separate capture

Entry to `SECURITY_RECOVERY` is reached ONLY from inside `SecurityFloorEvaluate`
(`TRANSITION round_state -> SECURITY_RECOVERY` on a breach in `HASHING`/`SOLUTION_PROPAGATION`, §9), which
is itself invoked by the epilogue `FinalizeEventTimeSecurityCensus(at)` on an **already-coherent** census
that the epilogue has just read and whose dirty flag it has just cleared. That entry is therefore the
RESULT of a floor decision on a coherent census at `at`, not a fresh applicability boundary needing its
own census. A `CaptureSecurityCensusOnApplicabilityEntry(SECURITY_RECOVERY, at)` here would
`SET security_census_dirty[at] <- true` **while the epilogue for `at` is mid-run and about to finalise it**
— re-dirtying an `event_time` whose epilogue has already consumed its census. The §9 NOTE states this
verbatim: SECURITY_RECOVERY "needs NO separate capture … calling this there would re-dirty an event_time
whose epilogue is mid-run — forbidden". The enum still admits `SECURITY_RECOVERY` as a floor-applicable
value for `SecurityFloorEvaluate`'s own guard, but no call site captures on entry to it.

## 6. Worked example (TV90) — `HASHING` entry, `H_active = 0`, no successful wake, one floor decision

Preconditions: in round `r+1`, `PrepareParticipantsForNewRound` has waked miners but **no
`WakeCompleteEvent` has yet succeeded**, so `H_active = 0` at the `ASSIGNMENT → HASHING` moment; **no
miner-state boundary** occurs at that `event_time = now` (§2b; §0.10).

Trace (§2b → §9): `CompleteAssignmentPhase` asserts every `PENDING` is bound to `(RoundID, TemplateID)`
and satisfies I1/I3/I18b, executes `TRANSITION round_state -> HASHING` (R4, bumps `state_version`), then
`CALL CaptureSecurityCensusOnApplicabilityEntry(HASHING, at = now)`. Capture computes
`H_active = H_honest = H_adversarial = 0` (I17), sets `q_adv = NA` (I17), and writes
`latest_security_census[now]` **and** `security_census_dirty[now] <- true` together atomically (J1/K7).
`ProcessEventTime(now)` drains to quiescence, then the epilogue `FinalizeEventTimeSecurityCensus(now)`
finds the flag set, reads the census with its provenance, clears the flag, and calls
`SecurityFloorEvaluate` — now in `HASHING` (applicable, J6) with `H_active = 0` — which
`RECORD_ONCE breach_event(active_floor, now)` and `breach_event(honest_floor, now)` (I16; `NA` never
numerically compared, I17) and decides the floor **once**.

Expected: exactly **one** floor decision on entry to `HASHING` even though no wake succeeded and no miner
boundary occurred; **no** breach was recorded while the round was still `ASSIGNMENT`. Matches **TV90**
(Reqs K7, J6, I16, I17) in `STAGE_01K_SEMANTIC_TEST_VECTORS.md`. Contrast TV77 (`ASSIGNMENT` with
`H_active = 0`): the same census value records only a `security_census_observation` — the deciding
difference is that K7 capture makes the epilogue evaluate the floor **in `HASHING`**, the applicable state.

## 7. Acceptance-style PASS checklist

| # | Check | Result | Ground |
|---|-------|--------|--------|
| C1 | Two coherent writers of `security_census_dirty`/`latest_security_census`; both write the pair atomically | PASS | §0.8 J1/K7 note; §0.9 step (5f); §9 `CaptureSecurityCensusOnApplicabilityEntry` `ATOMICALLY` block |
| C2 | Capture wired on entry to `HASHING` via `CompleteAssignmentPhase` (K2) | PASS | §2b `CALL CaptureSecurityCensusOnApplicabilityEntry(HASHING, at = now)` after `TRANSITION -> HASHING` |
| C3 | Capture wired on entry to `SOLUTION_PROPAGATION` via `ScheduleSolutionPropagation` | PASS | §16b `CALL CaptureSecurityCensusOnApplicabilityEntry(SOLUTION_PROPAGATION, at = now)` on first propagation-active context |
| C4 | J1 invariant `dirty[t] ⇒ latest[t] exists` holds for the applicability-entry writer | PASS | §9 capture writes both in one `ATOMICALLY` block; epilogue `ASSERT latest[t] EXISTS` (§9) grounded |
| C5 | Capture NEVER runs while round is `ASSIGNMENT` / setup — no breach created in a non-applicable state (J6) | PASS | §9 NOTE ("NEVER runs while … ASSIGNMENT"); only `entered_state ∈ {HASHING, SOLUTION_PROPAGATION}` call sites; §9 J6 guard |
| C6 | Entry to `SECURITY_RECOVERY` takes NO separate capture (already-coherent census; no re-dirty of a finalising `event_time`) | PASS | §9 NOTE; entry occurs inside `SecurityFloorEvaluate` under the epilogue |
| C7 | Epilogue decides the floor ONCE per quiescent `event_time` from the captured census with stored provenance | PASS | §9 `FinalizeEventTimeSecurityCensus` (I-01/I-02, J8); §0.7d `ProcessEventTime` |
| C8 | `HASHING` entry with `H_active = 0` and no successful wake yields exactly one floor decision (I16 breach, I17 `q_adv = NA` uncompared) | PASS | TV90; §9 `SecurityFloorEvaluate` `H_active == 0` branch |
| C9 | I17 exact decomposition recomputed at capture; `q_adv = NA` at zero active rate | PASS | §9 capture `H_active = H_honest + H_adversarial`; `IF H_active = 0: q_adv <- NA` |
| C10 | No new consensus feature; A1 baseline `8.420833333 kWh` unchanged | PASS | Census-triggering audit only; the idle policy within PoCol |

Exercised by **TV90** (K7 applicability-entry census, one floor decision on `HASHING` entry with
`H_active = 0`) in `STAGE_01K_SEMANTIC_TEST_VECTORS.md`; the J1 atomic-coherence structure is corroborated
by `STAGE_01J_SECURITY_CENSUS_COHERENCE_AUDIT.md` and the J6 applicability guard by
`STAGE_01J_SECURITY_APPLICABILITY_AUDIT.md` (TV77).

---

## Result

**Result: SECURITY APPLICABILITY AUDIT (Stage 1K): PASS** — `CaptureSecurityCensusOnApplicabilityEntry`
(§9) makes the security floor evaluable on ENTRY to a floor-applicable round state: wired into
`CompleteAssignmentPhase` (K2, §2b) for `HASHING` and `ScheduleSolutionPropagation` (§16b) for
`SOLUTION_PROPAGATION`, it computes the `ACTIVE_HASHING` census and writes `security_census_dirty[at]`
and `latest_security_census[at]` (with full J8 provenance) TOGETHER atomically as the SECOND coherent
writer alongside `ApplyMinerStateTransition` (J1 preserved); it NEVER runs while the round is `ASSIGNMENT`
so no breach is created in a non-applicable state (J6 preserved), and entry to `SECURITY_RECOVERY` needs
no separate capture because that entry is the RESULT of a `SecurityFloorEvaluate` on an already-coherent
census (re-capturing would re-dirty a finalising `event_time`); the event-time epilogue
`FinalizeEventTimeSecurityCensus` (I-01/I-02) consequently decides the floor ONCE on entry to `HASHING`
even with `H_active = 0` and no successful wake (TV90), correcting the pre-K7 gap in which a floor-applicable
state entered without a miner-state boundary set no census and fired no floor decision — with I16
(breaches recorded), I17 (`q_adv = NA` never compared) maintained, no new consensus feature, and the A1
baseline (`8.420833333 kWh`) unchanged.
