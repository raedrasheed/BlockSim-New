# Stage 1I — Correction Report (execution-contract lock)

**Branch.** `thesis-v45-pocol-stage1i-execution-contract-lock`
**Base.** `f5b1327d4d260257628bcc10d745b23d4610a34c` (Stage 1H).
**Scope.** Documentation only — no executable source, configuration, DOCX, PDF, or experiment
changes. Protected DOCX drafts byte-identical (draft-42 `2c3afdc5…`, draft-44 `a31400bc…`); Stage
1A–1H artifacts unmodified (A–H-lock).

**Naming rule (binding).** Algorithm is **PoCol**; mechanism is **the idle policy within PoCol**.
Forbidden name strings (`PoCol-E`, `Energy-Aware PoCol`, `Enhanced PoCol`) appear only in prohibition
clauses. No property (energy, security, fairness, incentive) is claimed. The A1 baseline is unchanged
(`8.420833333 kWh`); any modeled energy change is attributable ONLY to reduced active power-time. No new
consensus feature — I-01…I-08 are execution-contract, event-loop-causality, and accounting-consistency
corrections.

## I-01 — Event-time security epilogue

The per-`(event_time, delta_cycle)` security-decision model is replaced by a single event-time
epilogue keyed by `event_time` alone. `ApplyMinerStateTransition` recomputes the census, verifies I17,
records the intermediate census for audit, sets `security_census_dirty[event_time] <- true`, and
OVERWRITES `latest_security_census[event_time]` with the newest post-transition census — it never keys
the pending decision by the source `delta_cycle`. Exactly one `FinalizeEventTimeSecurityCensus(event_time)`
reads `latest_security_census[event_time]`, clears the flag, and calls `SecurityFloorEvaluate` once. No
intermediate delta-cycle census can independently trigger recovery, and no dirty flag can be stranded
between delta-cycles. Updated: pseudocode §0.8 (registries), §0.9 step (7), §9 (new
`FinalizeEventTimeSecurityCensus`), `HandlePropagationFailure`. Spec:
`STAGE_01I_EVENT_TIME_EPILOGUE_SPEC.md`. TV61/TV62.

## I-02 — Explicit quiescence and epilogue driver

A new event-loop procedure `ProcessEventTime(event_time t)` drains every ordinary and delta-cycle
event at `t` (in `(delta_cycle, microphase, stable_tie_key, seq)` order, including handler-generated
same-time events) until quiescence, THEN runs the security epilogue `FinalizeEventTimeSecurityCensus(t)`
exactly once (if `security_census_dirty[t]`), marks `t` in `finalised_event_times`, and advances
simulated wall-clock time. The epilogue is invoked structurally by the driver, NOT as a queued
microphase event, so it runs even when no later event exists. No ordinary event may be scheduled into a
finalised `event_time`; any participation-changing action from the security decision is scheduled at a
STRICTLY LATER `event_time`, so a recovery action cannot alter `H_active` after the final decision at
`t`. Updated: pseudocode §0.7 (security decision relocated), §0.7d (`ProcessEventTime`), §21 (security
decision removed from the same-timestamp queue). Spec: `STAGE_01I_EVENT_TIME_EPILOGUE_SPEC.md`. TV63.

## I-03 — Event-identity idempotence

Transition duplicate suppression keyed by `(MinerID, event_time, old_state, new_state)` is replaced by
suppression on an immutable `TransitionEventID = (event_time, delta_cycle, seq, MinerID, old_state,
new_state, reason, AssignmentID, assignment_version, CandidateID?, PropagationID?)`.
`ApplyMinerStateTransition` suppresses ONLY an exact-same-id replay (before opening any residency
interval or charging energy); a legitimate repeat of the same state edge at the same `event_time` in a
DIFFERENT `delta_cycle` has a distinct id and is applied. `TransitionEventID` is recorded in
`transition_audit`. Updated: pseudocode §0.8 (`transition_event_registry`), §0.9 step (0) + audit
record + NOTE. Audit: `STAGE_01I_TRANSITION_IDENTITY_AUDIT.md`. TV64/TV65.

## I-04 — Initialise all normative runtime registries

`RoundInitialise` explicitly initialises and RETURNS every normative registry; none is an implicit
global. PER-ROUND registries (`active_propagation_set`, `acceptance_batch_registry`,
`candidate_discovery_seq`, `block_accepted`, `state_version`, `residency_ledger`) reset each round;
PER-RUN event-loop bookkeeping (`security_census_dirty`, `latest_security_census`,
`transition_event_registry`, `finalised_event_times`, `current_delta_cycle`) is initialised once at run
start (`prior_state = null`) and preserved across rounds (§3.12) — a per-round reset would un-finalise
past `event_times` (I-02) or drop replay-suppression state (I-03). Updated: pseudocode §0.8 (scope
comments), §1 (`RoundInitialise` body + RETURNS + NOTE). Audit:
`STAGE_01I_RUNTIME_INITIALISATION_AUDIT.md`. TV66.

## I-05 — Terminal and recovery security behaviour

`SecurityFloorEvaluate` begins with `IF round_state in {ROUND_ACCEPTED, ROUND_ABORTED}: RETURN
terminal_stale_noop` BEFORE any breach recording or recovery logic. The ONLY permitted recovery
transitions are `HASHING → SECURITY_RECOVERY` and `SOLUTION_PROPAGATION → SECURITY_RECOVERY`. A
continuing breach while already in `SECURITY_RECOVERY` records `breach_persists` and keeps the state:
NO `SECURITY_RECOVERY → SECURITY_RECOVERY` self-transition and NO `state_version` bump (which would
spuriously stale every carried epoch). All other states are observation-only. Updated: pseudocode §9
(`SecurityFloorEvaluate` guard ordering + persistent-recovery branch), §0.7c. Audit:
`STAGE_01I_TERMINAL_SECURITY_AUDIT.md`. TV67.

## I-06 — State-specific low-power re-entry

Adversarial `LOW_POWER_LISTEN` re-entry is split by `entry_stop_reason`: `VALID_SOLUTION_VERIFIED`
resumes the own PAUSED head via `ResumeFromPause` (two-id match, never `RangeAssign`);
`RANGE_EXHAUSTED`/`ASSIGNMENT_REVOKED` create a fresh T10 assignment ONLY in a nonterminal,
non-refreshing, committed-eligible-template round whose policy permits a range (else deferral);
`ROUND_ACCEPTED`/`ROUND_ABORTED` create NO assignment or wake in the closed round (deferred to the next
round); a `TEMPLATE_REFRESH` round defers to the new-template assignment procedure. Updated: pseudocode
§8a (`AdversarialParticipationChangeEvent` `CASE LOW_POWER_LISTEN`). Audit:
`STAGE_01I_LOW_POWER_REENTRY_AUDIT.md`. TV68.

## I-07 — Valid custody enum

`custody_status` takes ONLY a value from the canonical, closed enum `{original, renewed, reassigned,
revoked, expired, abandoned, completed, superseded_by_template_refresh}`. An adversarial withdrawal sets
`custody_status = revoked` and `revocation_reason = adversarial_withdrawal` (two-field representation);
the invented value `revoked_adversarial_exit` is NOT used. Updated: pseudocode §0.8 (Assignment struct
`revocation_reason`), §8a (adversarial exit); invariant catalogue I8b; terminology (Stage-1I addendum).
Audit: `STAGE_01I_CUSTODY_ENUM_AUDIT.md`. TV69.

## I-08 — Complete normative references

All current un-suffixed normative files now reference `I1..I19` (including `I18a`/`I18b`); no residual
`I1..I17`-only range text remains. Updated: `STAGE_01_PROTOCOL_PSEUDOCODE.md`,
`STAGE_01_COMPLETION_REPORT.md`, `STAGE_01_OPEN_QUESTIONS.md`, `STAGE_01_THREAT_MODEL.md`,
`STAGE_01_TERMINOLOGY.md`, `STAGE_01_FAILURE_AND_ADVERSARIAL_PATHS.md`, `STAGE_01_PROTOCOL_SCOPE.md`
(genuine single-invariant `I17` references are unchanged). No `STAGE_01[A-H]_*` file is modified. TV70.

## Summary of changed / added artifacts

| Artifact | Change |
|----------|--------|
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` | §0.7/§0.7c/§0.7d (epilogue + `ProcessEventTime`, I-01/I-02); §0.8 registries (`security_census_dirty`, `latest_security_census`, `transition_event_registry`, `finalised_event_times`, `current_delta_cycle`; Assignment `revocation_reason`); §0.9 hook (TransitionEventID I-03; event-time flag I-01); §1 `RoundInitialise` (I-04); §8a `AdversarialParticipationChangeEvent` (I-06/I-07); §9 `FinalizeEventTimeSecurityCensus` (I-01) + `SecurityFloorEvaluate` (I-05); `HandlePropagationFailure` (I-01); §21 (security decision → epilogue); I1..I19 refs (I-08) |
| `STAGE_01_INVARIANT_CATALOGUE.md` | I8b canonical custody enum + `revocation_reason` (I-07) |
| `STAGE_01_TERMINOLOGY.md` | Stage-1I addendum; I1..I19 ref (I-08) |
| `STAGE_01_TRACEABILITY_MATRIX.csv` | Rows R58–R65 (I-01…I-08) |
| `STAGE_01_COMPLETION_REPORT.md`, `STAGE_01_OPEN_QUESTIONS.md`, `STAGE_01_THREAT_MODEL.md`, `STAGE_01_FAILURE_AND_ADVERSARIAL_PATHS.md`, `STAGE_01_PROTOCOL_SCOPE.md` | I1..I19 reference updates (I-08) |
| `STAGE_01I_*` (12 new deliverables) | this report + epilogue spec + transition-identity / runtime-init / terminal-security / low-power-reentry / custody-enum audits + procedure call graph + semantic test vectors + supersession register + cross-document audit + checksum manifest |

No executable source, configuration, DOCX, or PDF file is modified; no Stage 1A–1H artifact is
modified. The specification conforms to I-01…I-08 while preserving B1–B9, C1–C10, D1–D9, E1–E10, F1–F9,
G1–G11, and H1–H9.
