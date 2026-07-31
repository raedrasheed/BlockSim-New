# Stage 1H — Final-Census Security Audit (H3 + H4)

This audit confirms corrections **H3** and **H4** in the **PoCol** Stage-1 pseudocode: a single
security evaluation runs per settled timestamp on the FINAL census, and `SECURITY_RECOVERY` is
entered ONLY from a legal source round-state. It is a structural audit of the specification text
(`STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_ROUND_STATE_MACHINE.md`); no protocol property
(energy, security, fairness) is claimed or evaluated here. The mechanism under review is **the idle
policy within PoCol**; no new consensus feature is introduced. The A1 baseline
(`8.420833333 kWh`) is unchanged — any energy change is attributable ONLY to reduced active
power-time, not to this evaluation-timing correction.

## 1. Mechanism (H3) — one settled-census evaluation per timestamp

**Corrected-away condition.** Previously, multiple same-timestamp miner-state transitions could each
independently schedule a `SecurityFloorEvaluate`, so the FIRST transition's INTERMEDIATE census
could drive the round into `SECURITY_RECOVERY` before the census settled. That per-transition
scheduling is removed.

**Registry fields (§0.8 `STRUCTURE RoundContext registries`).**

- `security_evaluation_required` — per `(event_time, delta_cycle)` boolean flag, set by
  `ApplyMinerStateTransition` when a miner-state boundary changed the `ACTIVE_HASHING` census (H3);
  cleared by `FinalizeTimestampSecurityCensus`. "NO per-transition floor decision is scheduled."
- `residency_ledger` — sole owner of each `t_<state>` (unchanged; referenced for A1 continuity, H7).
- `intermediate_census_for_audit(event_time, delta_cycle, …)` — recorded per transition for AUDIT
  ONLY; never drives a round-state transition.

**Hook contract (§0.9 `PROCEDURE ApplyMinerStateTransition`, step (7)).** At each call the hook
recomputes `H_honest`/`H_adversarial`/`H_active`/`q_adv` from the post-transition `ACTIVE_HASHING`
set (step (6), I17), then `RECORD intermediate_census_for_audit(event_time, current_delta_cycle, …)`
(audit only). Step (7): it does **NOT** schedule an independent floor decision for THIS transition;
instead, `IF this transition changed the ACTIVE_HASHING census: SET
security_evaluation_required[(event_time, current_delta_cycle)] <- true`. The closing NOTE:
"it never … schedules a per-transition floor decision (H3): it only sets
security_evaluation_required for the settled-census evaluation."

**Microphase-5 timing (§0.7 PHASE 5; §0.7-H2 delta-cycle rule).** At each `event_time` the loop
processes microphases in order; PHASE 5 is "the SINGLE settled-census security evaluation
(`FinalizeTimestampSecurityCensus` → `SecurityFloorEvaluate`, H3, terminal/source-guarded,
G10/H4)". Same-`event_time` events created inside a handler are placed in the current or next
`delta_cycle` (§0.7-H2), never backward into a completed microphase, so all state changes of a
settled `(event_time, delta_cycle)` finish before its PHASE 5 runs.

**Finalizer (§9 `PROCEDURE FinalizeTimestampSecurityCensus`).** Runs "EXACTLY ONCE per
`(event_time, delta_cycle)`, AFTER every state-changing event of that `(event_time, delta_cycle)`
has settled (H3)". It: returns `no_census_change` when the flag is unset; else reads the FINAL
settled census (the last recomputation by `ApplyMinerStateTransition` at this
`(event_time, delta_cycle)`); `CLEAR security_evaluation_required[(event_time, delta_cycle)]`; and
calls `SecurityFloorEvaluate` **at most once**, carrying `event_RoundID = RoundID`,
`event_TemplateID = TemplateID`, `event_state_version = state_version`. Intermediate census values
"are retained for audit but never drive a round-state transition."

## 2. Sole-caller chain

- `FinalizeTimestampSecurityCensus` NOTE (§9): "H3: the ONLY caller of `SecurityFloorEvaluate`."
- `SecurityFloorEvaluate` PRECONDITIONS (§9): "invoked ONLY by `FinalizeTimestampSecurityCensus` on
  a settled census (H3); never inline (G10)."
- `HandlePropagationFailure` step (3): "do NOT schedule an independent floor decision here … `SET
  security_evaluation_required[(now, current_delta_cycle)] <- true`" — it now SETS THE FLAG rather
  than scheduling `SecurityFloorEvaluate` directly; the single `FinalizeTimestampSecurityCensus` for
  that settled timestamp performs the one decision.
- `EnterLowPowerListen`, `AdversarialParticipationChangeEvent`, and every other census-changing path
  reach the floor only through the hook's flag → `FinalizeTimestampSecurityCensus` (§0.7 PHASE 5).

No procedure other than `FinalizeTimestampSecurityCensus` invokes `SecurityFloorEvaluate`.

## 3. Legal SECURITY_RECOVERY source states (H4)

`SecurityFloorEvaluate` (§9) records every breach with `RECORD_ONCE breach_event(…)` (I16) BEFORE
the H4 source guard, then transitions to `SECURITY_RECOVERY` ONLY when
`round_state in {HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY}`. From any other state it returns
an observation-only result and performs NO transition. Observation-only means **recorded-but-no-
transition**, never silently repaired (I16). The terminal/stale guard (G10) runs first: if
`event_RoundID`/`event_TemplateID`/`event_state_version` are stale, it returns `terminal_stale_noop`
"before any breach logic" — a stale evaluation belongs to another epoch and records nothing.

| # | `round_state` at evaluation | class | outcome on breach | round transition |
|---|-----------------------------|-------|-------------------|------------------|
| 1 | `ROUND_INITIALISING` | setup | `setup_observation_only` | none |
| 2 | `TEMPLATE_COMMITMENT` | setup | `setup_observation_only` | none |
| 3 | `ASSIGNMENT` | setup | `setup_observation_only` | none |
| 4 | `HASHING` | legal source | `breach` → `TRANSITION → SECURITY_RECOVERY` (R10) | yes; bumps `state_version` |
| 5 | `SOLUTION_PROPAGATION` | legal source | `breach` → `TRANSITION → SECURITY_RECOVERY` (R8, preserves live candidates G8) | yes; bumps `state_version` |
| 6 | `SECURITY_RECOVERY` | legal source | `breach` → `TRANSITION → SECURITY_RECOVERY` (self) | yes; re-records, bumps `state_version` |
| 7 | `ROUND_ACCEPTED` | terminal | `terminal_stale_noop` | none |
| 8 | `ROUND_EXHAUSTED` | — | `exhausted_observation_only` | none |
| 9 | `TEMPLATE_REFRESH` | — | `refresh_observation_only` | none |
| 10 | `ROUND_ABORTED` | terminal | `terminal_stale_noop` | none |

Rows 7 and 10 also hit `terminal_stale_noop` at the G10 guard when `state_version` has already been
bumped by the terminal closure (the common case); the breach-branch return value agrees. Breaches
that pass the guard are RECORD_ONCE'd (I16) in every row 1–10 before the source guard is consulted;
only a genuinely stale/terminal evaluation short-circuits before breach logic.

## 4. Consistency with G8 (round-state not identified with the propagation set)

`SECURITY_RECOVERY` MAY coexist with a non-empty `active_propagation_set` (§2.5, G8). Entering it does
NOT cancel live candidate contexts; block arrivals and `AcceptanceBatchFinalize` remain processable.
A valid candidate preserved through recovery can still close the round
`SECURITY_RECOVERY → ROUND_ACCEPTED` (R6, §2.5/§2.7). Recovery exits are R13 (floor restored → `ASSIGNMENT`,
or `SOLUTION_PROPAGATION` if candidates remain) and R14 (floor unrecoverable → `ROUND_ABORTED`). The
round-state and the propagation set are NOT identified (H1/G8); there is no `iff` forcing
`SOLUTION_PROPAGATION` while candidates are live.

## 5. Acceptance checklist

- **PASS — one evaluation per settled timestamp.** `FinalizeTimestampSecurityCensus` runs "EXACTLY
  ONCE per `(event_time, delta_cycle)`" in PHASE 5 (§9, §0.7).
- **PASS — no per-transition floor decision.** `ApplyMinerStateTransition` step (7) only sets
  `security_evaluation_required`; its NOTE forbids scheduling a per-transition floor decision (§0.9).
- **PASS — `FinalizeTimestampSecurityCensus` is the sole caller.** Its NOTE ("the ONLY caller") and
  `SecurityFloorEvaluate`'s PRECONDITIONS ("invoked ONLY by `FinalizeTimestampSecurityCensus` …
  never inline") agree (§9).
- **PASS — intermediate census is audit-only.** `intermediate_census_for_audit(…)` is recorded per
  transition (§0.9 step (6)) and "never drive[s] a round-state transition"; the finalizer reads the
  FINAL settled census (§9).
- **PASS — legal SR sources only.** Transition to `SECURITY_RECOVERY` occurs only from
  `{HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY}`; all other states → observation-only /
  `terminal_stale_noop` (§9; table §3).
- **PASS — breaches always recorded (I16).** `RECORD_ONCE breach_event(…)` precedes the H4 source
  guard; observation-only = recorded-but-no-transition (§9; I16 §I16).
- **PASS — terminal/stale guard (G10).** Stale `RoundID`/`TemplateID`/`state_version` →
  `terminal_stale_noop` before any breach logic (§9, §0.7c).
- **PASS — `HandlePropagationFailure` sets the flag.** Step (3) sets
  `security_evaluation_required[(now, current_delta_cycle)]` instead of scheduling
  `SecurityFloorEvaluate` (§ `HandlePropagationFailure`).
- **PASS — A1 unchanged.** The `8.420833333 kWh` baseline is untouched; residency_ledger ownership of
  `t_<state>` is unaffected by this evaluation-timing correction.

Exercised by **TV52** (H3 single final census) and **TV53** (H4 legal recovery source) in
`STAGE_01H_SEMANTIC_TEST_VECTORS.md`; TV60 corroborates the G8 recovery-state acceptance path.

## 6. Result

**Result: FINAL-CENSUS AUDIT (Stage 1H): PASS** — exactly one `FinalizeTimestampSecurityCensus` →
`SecurityFloorEvaluate` runs per settled `(event_time, delta_cycle)` on the final settled census;
`ApplyMinerStateTransition` and `HandlePropagationFailure` only set `security_evaluation_required`
(no per-transition floor decision); `FinalizeTimestampSecurityCensus` is the sole caller; intermediate
census values are audit-only; `SECURITY_RECOVERY` is entered only from
`{HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY}` with all other states observation-only; breaches
are always recorded (I16); the terminal/stale guard (G10) short-circuits stale epochs; and the A1
baseline (`8.420833333 kWh`) is unchanged.
