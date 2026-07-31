# Stage 1J — Security-Floor Applicability Audit (J6 round-state applicability before breach recording)

Documentation-only audit of correction **J6**: `SecurityFloorEvaluate` (§9) checks **round-state
applicability BEFORE evaluating any threshold or recording any breach event**. In an observation-only
round state (setup / `ROUND_EXHAUSTED` / `TEMPLATE_REFRESH`) the procedure now records ONLY a
`security_census_observation` and returns the matching observation-only result; it records **no** I16
`breach_event`. Thresholds are evaluated and I16 breaches recorded ONLY in `HASHING`,
`SOLUTION_PROPAGATION`, or `SECURITY_RECOVERY`. This is a structural audit of the specification text
(`STAGE_01_PROTOCOL_PSEUDOCODE.md` §9 `SecurityFloorEvaluate` / §9 `FinalizeEventTimeSecurityCensus`,
§0.7c/§0.7d; `STAGE_01_ROUND_STATE_MACHINE.md` §1 the ten round states, §2.4–§2.10;
`STAGE_01_INVARIANT_CATALOGUE.md` I16). It EXTENDS `STAGE_01I_TERMINAL_SECURITY_AUDIT.md` (I-05
terminal-first ordering, unchanged here). It describes **PoCol** with **the idle policy within PoCol**
enabled and claims **no property** (energy, security, fairness, incentive) beyond the ordering
structure defined here; no new consensus feature is introduced. The strings "PoCol-E",
"Energy-Aware PoCol", and "Enhanced PoCol" are prohibited. The accepted A1 baseline is
`8.420833333 kWh` and is UNCHANGED — any energy change is attributable ONLY to reduced active
power-time, never to this evaluation-ordering correction.

---

## 1. The corrected-away problem (breach events counted in observation-only states)

Under the Stage-1I ordering (`STAGE_01I_TERMINAL_SECURITY_AUDIT.md` §2), `SecurityFloorEvaluate`
evaluated thresholds and executed `RECORD_ONCE breach_event(…)` (I16) for **every non-terminal,
non-stale** state, and only the round **transition** was suppressed afterward. The Stage-1I table
records this explicitly: rows for `ROUND_INITIALISING`, `TEMPLATE_COMMITMENT`, `ASSIGNMENT`,
`ROUND_EXHAUSTED`, and `TEMPLATE_REFRESH` all show outcome `*_observation_only` with **"breach record
made? = yes (I16 `breach_event`)"**, and §4 C7 defines "observation-only means recorded-but-no-
transition". Consequence: an I16 `breach_event` was **counted during setup / refresh / exhausted
states** — round states in which no coverage search is in progress and a floor breach carries no
operational meaning — inflating the recorded breach series with observations that should never have
been breaches.

## 2. The correction (J6) — applicability BEFORE thresholds or breach recording

`SecurityFloorEvaluate` (§9) is invoked ONLY by the event-time epilogue
`FinalizeEventTimeSecurityCensus` (§9), run EXACTLY ONCE per QUIESCENT `event_time` (I-01/I-02, §0.7d
`ProcessEventTime`) on the FINAL settled census, carrying the census's OWN stored provenance
`(event_RoundID, event_TemplateID, event_state_version)` (J8). The body now executes its guards in
this exact order (§9):

```
    # I-05: TERMINAL-FIRST. Return BEFORE any threshold evaluation or recording for a terminal round.
    IF round_state in {ROUND_ACCEPTED, ROUND_ABORTED}:
      RETURN terminal_stale_noop                               # no observation, no breach, no transition
    # J8 STALE-CENSUS-CONTEXT GUARD. Census epoch no longer current -> observation only, no recovery.
    IF event_RoundID != RoundID_current
       OR event_TemplateID != TemplateID_committed
       OR event_state_version != state_version_current:
      RECORD security_census_observation(stale_census, event_RoundID, event_TemplateID, event_state_version,
                                         H_active(t), H_honest(t), q_adv(t))     # J8: observation only
      RETURN stale_census_observation                          # no recovery in the new context
    # J6 APPLICABILITY BEFORE BREACH RECORDING. Thresholds/I16 breaches ONLY in the 3 applicable states.
    IF round_state NOT in {HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY}:
      RECORD security_census_observation(round_state, H_active(t), H_honest(t), q_adv(t))   # J6: no breach
      RETURN (round_state = TEMPLATE_REFRESH ? refresh_observation_only  :
              round_state = ROUND_EXHAUSTED  ? exhausted_observation_only :
              setup_observation_only)          # ROUND_INITIALISING / TEMPLATE_COMMITMENT / ASSIGNMENT
    # ---- APPLICABLE states only (HASHING / SOLUTION_PROPAGATION / SECURITY_RECOVERY) ----
    breach <- FALSE
    ... RECORD_ONCE breach_event(active_floor | honest_floor | adversarial_share, t)   # I16
    ... IF breach AND round_state in {HASHING, SOLUTION_PROPAGATION}: -> SECURITY_RECOVERY (R10/R8)
    ... ELSE IF breach AND round_state = SECURITY_RECOVERY: RECORD_ONCE breach_persists(t)  # no transition
```

Ordering, restated: **(1) terminal-first** (`ROUND_ACCEPTED`/`ROUND_ABORTED` → `terminal_stale_noop`,
records nothing); **(2) J8 stale-context** (mismatched carried epoch → `security_census_observation` +
`stale_census_observation`, no breach); **(3) J6 applicability** (`round_state NOT in {HASHING,
SOLUTION_PROPAGATION, SECURITY_RECOVERY}` → `security_census_observation` ONLY + the matching
observation-only result, **no** active-floor / honest-floor / adversarial-share breach event); **(4)
applicable states ONLY** evaluate thresholds, `RECORD_ONCE breach_event(…)` (I16), then the I-05
recovery transitions. The applicability check is a **guarded early return placed ahead of the breach
block**, so no threshold is compared and no `breach_event` is recorded in an observation-only state.
The §9 NOTE states the same contract: "round-state applicability is checked BEFORE any threshold
evaluation, so setup/refresh/exhausted states record ONLY a `security_census_observation` (never a
breach event)".

## 3. Ten round states — outcome and whether an I16 breach event may be recorded

The J8 stale-context guard is **cross-cutting**: for any non-terminal state, if the carried census
epoch is stale the outcome is `stale_census_observation` (observation only, no breach) BEFORE the J6
check. The table below gives the outcome when the census is **fresh** (epoch current).

| # | `round_state` | applicability class | outcome (fresh census) | may record I16 `breach_event`? |
|---|---------------|---------------------|------------------------|--------------------------------|
| 1 | `ROUND_INITIALISING` | observation-only (setup) | `setup_observation_only` (census observation only) | **no** |
| 2 | `TEMPLATE_COMMITMENT` | observation-only (setup) | `setup_observation_only` (census observation only) | **no** |
| 3 | `ASSIGNMENT` | observation-only (setup) | `setup_observation_only` (census observation only) | **no** |
| 4 | `HASHING` | **applicable** | thresholds evaluated; `RECORD_ONCE breach_event` (I16); breach → `SECURITY_RECOVERY` (R10) | **yes** |
| 5 | `SECURITY_RECOVERY` | **applicable** | thresholds evaluated; `RECORD_ONCE breach_event` (I16); continuing breach → `breach_persists` (no self-transition, I-05) | **yes** |
| 6 | `SOLUTION_PROPAGATION` | **applicable** | thresholds evaluated; `RECORD_ONCE breach_event` (I16); breach → `SECURITY_RECOVERY` (R8, preserves live candidates G8) | **yes** |
| 7 | `ROUND_ACCEPTED` | terminal | `terminal_stale_noop` (returned FIRST, records nothing) | **no** |
| 8 | `ROUND_EXHAUSTED` | observation-only | `exhausted_observation_only` (census observation only) | **no** |
| 9 | `TEMPLATE_REFRESH` | observation-only | `refresh_observation_only` (census observation only) | **no** |
| 10 | `ROUND_ABORTED` | terminal | `terminal_stale_noop` (returned FIRST, records nothing) | **no** |

Only rows 4/5/6 — the three states in `{HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY}` — may
record an I16 `breach_event`. Recovery is **entered** only from `HASHING` (R10) or
`SOLUTION_PROPAGATION` (R8); a continuing breach in `SECURITY_RECOVERY` records `breach_persists`
with no self-transition and no `state_version` bump (I-05, unchanged from Stage 1I). Terminal rows
7/10 record nothing (terminal-first). Any non-terminal row returns `stale_census_observation` instead
when its carried epoch is stale (J8).

## 4. No breach event is recorded during setup / refresh / exhausted

For `ROUND_INITIALISING`, `TEMPLATE_COMMITMENT`, `ASSIGNMENT`, `ROUND_EXHAUSTED`, and
`TEMPLATE_REFRESH`, the J6 guard `IF round_state NOT in {HASHING, SOLUTION_PROPAGATION,
SECURITY_RECOVERY}` is **true**, so control takes the early return: it executes exactly
`RECORD security_census_observation(round_state, H_active(t), H_honest(t), q_adv(t))` and returns the
observation-only variant. The `breach <- FALSE` initialiser, the `H_active(t) == 0` branch, the three
`IF H_* < floor` comparisons, every `RECORD_ONCE breach_event(…)` (I16), and the recovery-transition
block are ALL below this early return and are never reached in these states.

Contrast with the prior ordering (§1): Stage-1I reached `RECORD_ONCE breach_event(…)` for these same
states and suppressed only the transition, so the recorded breach series included setup / refresh /
exhausted observations. Under J6 the recorded series contains, for these states, only
`security_census_observation` entries — I16 (breaches recorded, never silently repaired) is preserved
because in an applicable state every breach is still recorded, and an observation-only state now
produces no breach to record in the first place.

## 5. Worked example (TV77) — `H_active = 0` during `ASSIGNMENT`

Preconditions: at an `event_time` with `round_state = ASSIGNMENT` (a setup state), a miner-state
boundary yields `H_active(t) = 0` (hence `q_adv(t) = NA`, I17); the epilogue runs
`FinalizeEventTimeSecurityCensus → SecurityFloorEvaluate` once on the quiescent census.

Trace (§9): the terminal-first guard is passed (`ASSIGNMENT ∉ {ROUND_ACCEPTED, ROUND_ABORTED}`); the
J8 stale guard is passed (fresh census); the J6 applicability check fires because `ASSIGNMENT ∉
{HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY}`, so the procedure executes
`RECORD security_census_observation(ASSIGNMENT, H_active = 0, H_honest, q_adv = NA)` and returns
`setup_observation_only` — WITHOUT evaluating thresholds, WITHOUT comparing `NA`, and WITHOUT
recording any active-floor / honest-floor / adversarial-share `breach_event`.

Expected: one census observation recorded; **no** I16 breach event counted during setup; no recovery
transition. Matches **TV77** in `STAGE_01J_SEMANTIC_TEST_VECTORS.md` (Reqs J6, I16). Note the
difference from the applicable-state `H_active = 0` case (TV in `STAGE_01D_SEMANTIC_TEST_VECTORS.md`),
where `HASHING` with `H_active = 0` DOES record active-floor + honest-floor breaches and enters
`SECURITY_RECOVERY` — the same census value, a different recorded outcome, decided solely by the J6
applicability guard.

## 6. Acceptance-style PASS checklist

| # | Check | Result | Ground |
|---|-------|--------|--------|
| C1 | Applicability guard precedes ALL threshold evaluation and breach recording | PASS | §9 `SecurityFloorEvaluate`: J6 `IF round_state NOT in {…}` early return sits above `breach <- FALSE` and every `RECORD_ONCE breach_event` |
| C2 | Guard ordering is terminal-first → J8 stale → J6 applicability → thresholds/I16 → I-05 transitions | PASS | §9 statement order; §0.7c terminal-round guard |
| C3 | Observation-only states record ONLY `security_census_observation` (no breach) | PASS | §9 J6 branch `RECORD security_census_observation(round_state, …)` then `RETURN …_observation_only` |
| C4 | Exactly 3 states may record an I16 `breach_event`: `HASHING`, `SOLUTION_PROPAGATION`, `SECURITY_RECOVERY` | PASS | §9 applicable-states block reachable only when `round_state in {HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY}` |
| C5 | `ROUND_INITIALISING`/`TEMPLATE_COMMITMENT`/`ASSIGNMENT` → `setup_observation_only`, no breach | PASS | §9 J6 `setup_observation_only` default; table §3 rows 1–3 |
| C6 | `ROUND_EXHAUSTED` → `exhausted_observation_only`, `TEMPLATE_REFRESH` → `refresh_observation_only`, no breach | PASS | §9 J6 ternary; table §3 rows 8–9 |
| C7 | `ROUND_ACCEPTED`/`ROUND_ABORTED` → `terminal_stale_noop` before any recording | PASS | §9 terminal-first `IF`; table §3 rows 7/10; I-05 |
| C8 | I16 preserved: breaches still recorded in applicable states; observation-only produces no breach to record | PASS | §9 `RECORD_ONCE breach_event` in applicable block; I16 (`STAGE_01_INVARIANT_CATALOGUE.md`) |
| C9 | I17 — `q_adv = NA` never numerically compared; observation-only skips comparison entirely | PASS | §9 J6 early return before `H_active == 0` / `q_adv != NA` branches; I17 |
| C10 | No new consensus feature; A1 baseline `8.420833333 kWh` unchanged | PASS | Ordering audit only; idle policy within PoCol |

Exercised by **TV77** (J6 observation-not-breach in a setup state) in
`STAGE_01J_SEMANTIC_TEST_VECTORS.md`; the I-05 terminal-first / persistence structure is corroborated
by `STAGE_01I_TERMINAL_SECURITY_AUDIT.md` (TV67) and the single event-time epilogue by TV61–TV63.

---

## Result

**Result: SECURITY APPLICABILITY AUDIT (Stage 1J): PASS** — `SecurityFloorEvaluate` (§9) checks
round-state applicability BEFORE any threshold evaluation or breach recording: after the terminal-first
guard (`ROUND_ACCEPTED`/`ROUND_ABORTED` → `terminal_stale_noop`, I-05) and the J8 stale-context guard
(mismatched epoch → `stale_census_observation`), the J6 guard `IF round_state NOT in {HASHING,
SOLUTION_PROPAGATION, SECURITY_RECOVERY}` records ONLY a `security_census_observation` and returns the
matching observation-only result (`setup_observation_only` / `exhausted_observation_only` /
`refresh_observation_only`) with **no** I16 `breach_event`; thresholds are evaluated and I16 breaches
`RECORD_ONCE`-recorded ONLY in the three applicable states, correcting the Stage-1I ordering that
recorded breach events during setup / refresh / exhausted; I16 (breaches recorded), I17 (`q_adv = NA`
never compared), and the single event-time epilogue (`FinalizeEventTimeSecurityCensus`, I-01/I-02) are
all maintained — with no new consensus feature and the A1 baseline (`8.420833333 kWh`) unchanged.
