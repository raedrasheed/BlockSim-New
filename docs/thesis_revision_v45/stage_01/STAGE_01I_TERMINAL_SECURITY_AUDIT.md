# Stage 1I — Terminal Security Audit (I-05)

Documentation-only audit of correction **I-05**: `SecurityFloorEvaluate` is reordered so that a
**terminal round is handled FIRST** — before any breach recording or recovery logic — the legal
recovery-source set is **narrowed** to two states, and a continuing breach already in
`SECURITY_RECOVERY` is recorded as **persistence with no self-transition and no `state_version`
bump**. It is a structural audit of the specification text
(`STAGE_01_PROTOCOL_PSEUDOCODE.md` §9, §0.7c/§0.7d; `STAGE_01_ROUND_STATE_MACHINE.md` §2.5,
R6/R8/R10/R13/R14); no protocol property (energy, security, fairness) is claimed or evaluated
here. The mechanism under review is **the idle policy within PoCol**; no new consensus feature is
introduced, and no property is experimentally supported at Stage 1. The A1 baseline
(`8.420833333 kWh`) is unchanged — any energy change is attributable ONLY to reduced active
power-time, never to this evaluation-ordering correction.

---

## 1. Mechanism (I-05) — guard ordering inside `SecurityFloorEvaluate`

`SecurityFloorEvaluate` (§9) is invoked ONLY by the event-time epilogue
`FinalizeEventTimeSecurityCensus` (§9), which runs EXACTLY ONCE per QUIESCENT `event_time`
(I-01/I-02, §0.7d) on the FINAL settled census and carries the round epoch
`(event_RoundID = RoundID, event_TemplateID = TemplateID, event_state_version = state_version)`.
The body executes its guards in this exact order:

```
    # I-05: TERMINAL-FIRST. Return BEFORE any breach recording or recovery logic for a terminal round.
    IF round_state in {ROUND_ACCEPTED, ROUND_ABORTED}:
      RETURN terminal_stale_noop                               # no breach recorded, no transition
    # G10: STALE GUARD on the carried epoch (a superseded RoundID/TemplateID/state_version).
    IF event_RoundID != RoundID_current
       OR event_TemplateID != TemplateID_committed
       OR event_state_version != state_version_current:
      RETURN terminal_stale_noop                               # no breach recorded, no transition
    breach <- FALSE
    ... RECORD_ONCE breach_event(active_floor|honest_floor|adversarial_share, t)   # I16 breach recording
    # I-05: the ONLY permitted recovery transitions are HASHING -> SECURITY_RECOVERY and
    #       SOLUTION_PROPAGATION -> SECURITY_RECOVERY. All other states are observation-only or no-op.
    IF breach AND round_state in {HASHING, SOLUTION_PROPAGATION}:
      TRANSITION round_state -> SECURITY_RECOVERY              # bumps state_version (G10)
      RETURN breach
    ELSE IF breach AND round_state = SECURITY_RECOVERY:
      RECORD_ONCE breach_persists(t)                          # I16 persistence record; NO transition
      RETURN breach_persists
    ELSE IF breach:
      RETURN (refresh_observation_only | exhausted_observation_only | setup_observation_only)
    RETURN no_breach
```

Ordering, restated: **(1) terminal-first** (`ROUND_ACCEPTED`/`ROUND_ABORTED` → `terminal_stale_noop`,
records nothing), **(2) stale-epoch guard** (`RoundID`/`TemplateID`/`state_version` mismatch →
`terminal_stale_noop`), **(3) breach recording** (`RECORD_ONCE breach_event(…)`, I16), **(4) the
transition branch** (enter recovery / record persistence / observation-only / `no_breach`). The
§0.7c "Terminal-round security guard (G10/I-05)" states the same contract: `terminal_stale_noop`
is returned "when the round is already `ROUND_ACCEPTED`/`ROUND_ABORTED` (checked FIRST, before any
breach recording, I-05) or the evaluation belongs to a stale `RoundID`/`TemplateID`/`state_version`."

**Contrast with the prior H4 ordering (`STAGE_01H_FINAL_CENSUS_AUDIT.md` §3).** Under H4,
`SecurityFloorEvaluate` "records every breach with `RECORD_ONCE breach_event(…)` (I16) BEFORE the
H4 source guard", and terminal handling was a **branch AFTER breach recording** that relied on the
G10 stale guard to short-circuit "the common case". I-05 promotes the terminal check to the FIRST
guard so a terminal round records **nothing** even when its epoch is not yet stale. I-05 also
**narrows** the legal recovery-source set: H4 listed `{HASHING, SOLUTION_PROPAGATION,
SECURITY_RECOVERY}` (row 6: `SECURITY_RECOVERY → SECURITY_RECOVERY` self, "re-records, bumps
`state_version`"); I-05 removes `SECURITY_RECOVERY` from the transition set, leaving only
`{HASHING, SOLUTION_PROPAGATION}`, and reroutes a continuing recovery breach to `breach_persists`.

## 2. Ten round states — `SecurityFloorEvaluate` outcome on breach

`RECORD_ONCE breach_event(…)` (I16) fires for every non-terminal, non-stale state; only the
terminal-first / stale guard returns BEFORE recording, so terminal rounds deliberately record
NOTHING (they returned first).

| # | `round_state` at evaluation | class | outcome on breach | round transition | breach record made? |
|---|-----------------------------|-------|-------------------|------------------|---------------------|
| 1 | `ROUND_INITIALISING` | setup | `setup_observation_only` | none | yes (I16 `breach_event`) |
| 2 | `TEMPLATE_COMMITMENT` | setup | `setup_observation_only` | none | yes (I16 `breach_event`) |
| 3 | `ASSIGNMENT` | setup | `setup_observation_only` | none | yes (I16 `breach_event`) |
| 4 | `HASHING` | legal source | `breach` → `TRANSITION → SECURITY_RECOVERY` (R10) | yes; bumps `state_version` | yes (I16 `breach_event`) |
| 5 | `SECURITY_RECOVERY` | persistent | `breach_persists` (`RECORD_ONCE breach_persists(t)`) | **none — no self-transition** | yes (`breach_event` + `breach_persists`) |
| 6 | `SOLUTION_PROPAGATION` | legal source | `breach` → `TRANSITION → SECURITY_RECOVERY` (R8, preserves live candidates G8) | yes; bumps `state_version` | yes (I16 `breach_event`) |
| 7 | `ROUND_ACCEPTED` | terminal | `terminal_stale_noop` (handled FIRST) | none | **no — returned before recording** |
| 8 | `ROUND_EXHAUSTED` | observation | `exhausted_observation_only` | none | yes (I16 `breach_event`) |
| 9 | `TEMPLATE_REFRESH` | observation | `refresh_observation_only` | none | yes (I16 `breach_event`) |
| 10 | `ROUND_ABORTED` | terminal | `terminal_stale_noop` (handled FIRST) | none | **no — returned before recording** |

Row 4 = R10 (`HASHING → SECURITY_RECOVERY`); row 6 = R8 (`SOLUTION_PROPAGATION → SECURITY_RECOVERY`,
which PRESERVES remaining live candidate contexts, G8). These are the **only** two entries into
`SECURITY_RECOVERY` this procedure performs. The recovery **exits** R13 (`FloorRestored →
ASSIGNMENT`/`SOLUTION_PROPAGATION`) and R14 (`FloorUnrecoverable → ROUND_ABORTED`) are driven
elsewhere (floor-restoration / abort logic), NOT by `SecurityFloorEvaluate`; row 5 never fires them.

## 3. Persistent recovery cannot churn `state_version` and cannot self-transition

The `ELSE IF breach AND round_state = SECURITY_RECOVERY` branch contains no
`TRANSITION round_state -> S` statement — it executes only `RECORD_ONCE breach_persists(t)` and
`RETURN breach_persists`, never assigning `round_state`. Two consequences follow directly:

- **No self-transition.** Because `round_state` is never re-assigned, no
  `SECURITY_RECOVERY → SECURITY_RECOVERY` edge is emitted; the round simply stays in
  `SECURITY_RECOVERY`. (Under H4 this edge existed as row 6; I-05 removes it.)
- **No `state_version` bump.** `RoundInitialise` (§1, G10 NOTE) fixes that "every
  `TRANSITION round_state -> S` in this document also bumps `state_version`". Since this branch
  runs no `TRANSITION`, `state_version` is left unchanged.

**Why this matters.** `SecurityFloorEvaluate` carries `event_state_version` and the stale guard
(step 2) rejects any evaluation whose `event_state_version != state_version_current`. A spurious
bump "merely to represent persistence" would **stale every carried epoch** — every
`latest_security_census[event_time]` / pending epilogue keyed to the round epoch (§0.8, §0.9 I-01)
would mismatch the new `state_version` and be discarded — and would **churn the round epoch** on
every re-evaluation while the breach continues. Persistence is therefore a **record only**
(`breach_persists`, I16), not a state edge (I-05 NOTE §9; TV67).

## 4. Consistency preserved (G8 / I-01 / I16 / I17)

- **G8 — live candidates preserved.** Entering `SECURITY_RECOVERY` from R8/R10 does NOT cancel
  live candidate contexts; `SECURITY_RECOVERY` MAY coexist with a non-empty `active_propagation_set`
  (§2.5), block arrivals and `AcceptanceBatchFinalize` remain processable, and a preserved candidate
  may still close the round `SECURITY_RECOVERY → ROUND_ACCEPTED` (R6, §2.5/§2.7).
- **I-01 — single event-time epilogue.** The decision is taken exactly once by
  `FinalizeEventTimeSecurityCensus(event_time)` after the `event_time` is quiescent (§0.7d,
  `ProcessEventTime`); no intermediate delta-cycle census can independently trigger recovery.
- **I16 — breaches always recorded.** `RECORD_ONCE breach_event(…)` precedes the transition branch
  for every non-terminal, non-stale state (rows 1–6, 8, 9); observation-only means
  recorded-but-no-transition; only the terminal-first/stale guard returns before recording.
- **I17 — `q_adv = NA` never numerically compared.** At `H_active(t) == 0` the procedure records
  the active- and honest-floor breaches and does NOT compare `NA` with `q_adv_threshold`
  (`IF q_adv(t) != NA AND …`); `H_active = H_honest + H_adversarial` is exact at every
  `ACTIVE_HASHING` boundary (§0.9, I17).

## 5. Acceptance-style PASS checklist

| # | Check | Result | Ground |
|---|-------|--------|--------|
| C1 | Terminal-first guard precedes ALL breach recording | PASS | §9 `SecurityFloorEvaluate` (terminal `IF` is first statement); §0.7c "checked FIRST, before any breach recording, I-05" |
| C2 | Stale-epoch guard follows terminal-first, then breach recording | PASS | §9 guard order: terminal → `RoundID`/`TemplateID`/`state_version` → `breach_event` |
| C3 | Only 2 legal recovery sources: `HASHING`, `SOLUTION_PROPAGATION` | PASS | §9 `IF breach AND round_state in {HASHING, SOLUTION_PROPAGATION}`; narrows H4 set (§STAGE_01H_FINAL_CENSUS_AUDIT §3) |
| C4 | Persistent breach in `SECURITY_RECOVERY` = `breach_persists`, no self-transition, no `state_version` bump | PASS | §9 persistent branch (no `TRANSITION`); §9 NOTE; TV67 |
| C5 | Other states observation-only (setup / exhausted / refresh) | PASS | §9 `refresh_observation_only`/`exhausted_observation_only`/`setup_observation_only`; table §2 |
| C6 | Terminal rounds record NOTHING (returned first) | PASS | §9 terminal-first `RETURN terminal_stale_noop`; table §2 rows 7/10 |
| C7 | I16 — breaches recorded for every non-terminal, non-stale state | PASS | §9 `RECORD_ONCE breach_event(…)` before transition branch |
| C8 | I17 — `q_adv = NA` never numerically compared | PASS | §9 `H_active == 0` branch; `IF q_adv(t) != NA AND …` |
| C9 | G8 — entering `SECURITY_RECOVERY` preserves live candidates | PASS | §2.5 coexistence (G8); R8 preserves set; R6 recovery-state acceptance |
| C10 | No new consensus feature; A1 baseline unchanged | PASS | Ordering audit only; idle policy within PoCol; `8.420833333 kWh` untouched |

Exercised by **TV67** (I-05 persistent-recovery: no self-transition, no `state_version` bump) in
`STAGE_01I_SEMANTIC_TEST_VECTORS.md`; TV61–TV63 corroborate the single event-time epilogue (I-01/I-02).

---

## Result

**Result: TERMINAL SECURITY AUDIT (Stage 1I): PASS** — `SecurityFloorEvaluate` (§9) checks
`round_state in {ROUND_ACCEPTED, ROUND_ABORTED}` FIRST and returns `terminal_stale_noop` before any
breach recording (§0.7c, I-05), then applies the stale-epoch guard, then records breaches
(`RECORD_ONCE breach_event`, I16); the ONLY permitted recovery transitions are
`HASHING → SECURITY_RECOVERY` (R10) and `SOLUTION_PROPAGATION → SECURITY_RECOVERY` (R8), narrowing
the Stage-1H legal-source set that also listed `SECURITY_RECOVERY`; a continuing breach already in
`SECURITY_RECOVERY` records `breach_persists` with NO self-transition and NO `state_version` bump
(so no carried epoch is spuriously staled, TV67); setup / `ROUND_EXHAUSTED` / `TEMPLATE_REFRESH`
are observation-only and terminal rounds record nothing; the single event-time epilogue
(`FinalizeEventTimeSecurityCensus`, I-01/I-02), I16/I17, and G8 candidate preservation are all
maintained — with no new consensus feature and the A1 baseline (`8.420833333 kWh`) unchanged.
