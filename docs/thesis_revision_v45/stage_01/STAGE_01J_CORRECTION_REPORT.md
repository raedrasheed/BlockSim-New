# Stage 1J — Correction Report (implementation-handoff lock)

**Branch.** `thesis-v45-pocol-stage1j-implementation-handoff-lock`
**Base.** `ae5255c5b1a30f8b20f4724ee7d40c6f5768f01b` (Stage 1I).
**Scope.** Documentation only — no executable source, configuration, DOCX, PDF, or experiment
changes. Protected DOCX drafts byte-identical (draft-42 `2c3afdc5…`, draft-44 `a31400bc…`); Stage
1A–1I artifacts unmodified (A–I-lock).

**Naming rule (binding).** Algorithm is **PoCol**; mechanism is **the idle policy within PoCol**.
Forbidden name strings (`PoCol-E`, `Energy-Aware PoCol`, `Enhanced PoCol`) appear only in prohibition
clauses. No property (energy, security, fairness, incentive) is claimed. The A1 baseline is unchanged
(`8.420833333 kWh`); any modeled energy change is attributable ONLY to reduced active power-time. No new
consensus feature — J1…J9 are implementation-handoff (coherence, ordering, ownership, participation)
corrections.

## J1 — Dirty/latest security-census coherence

`ApplyMinerStateTransition` is the SOLE writer of `security_census_dirty[event_time]` and
`latest_security_census[event_time]`, written TOGETHER in one atomic step (§0.9 step (8)); neither is
set without the other. The defensive `SET security_census_dirty[now] <- true` in
`HandlePropagationFailure` is REMOVED — candidate failure changes no `ACTIVE_HASHING` census; only the
later re-activation boundaries do, through the hook. New invariant: `security_census_dirty[t] = true ⇒
latest_security_census[t] exists`, asserted by `FinalizeEventTimeSecurityCensus` before reading. Updated:
pseudocode §0.8/§0.9/§16. Audit: `STAGE_01J_SECURITY_CENSUS_COHERENCE_AUDIT.md`. TV71/TV72.

## J2 — Replay guard before the state precondition

`ApplyMinerStateTransition` is reordered: (0) build `TransitionEventID`; (1) if it is in
`transition_event_registry`, return `duplicate_suppressed` WITHOUT reading `old_state` and WITHOUT
charging energy; (2) for a non-replay only, require `old_state = miner_state(MinerID)` (else
`illegal_stale_source`); (3) validate legality; (4+) apply atomically. An exact replay necessarily
arrives after the first event changed `miner_state`, so replay suppression must precede the old-state
precondition. Updated: pseudocode §0.9 (PRECONDITIONS + steps). Audit:
`STAGE_01J_TRANSITION_REPLAY_AUDIT.md`. TV73.

## J3 — Complete transition event envelope

`ApplyMinerStateTransition` receives/resolves the full envelope (`event_time`, `delta_cycle`,
`event_seq`, `MinerID`, `old_state`, `new_state`, `reason`, `AssignmentID`, `assignment_version`,
`candidate_id`, `propagation_id`). The ambiguous single `candidate_ref` is replaced by explicit
`candidate_id` AND `propagation_id`; every candidate-triggered caller (`EnterLowPowerListen`) passes
both. The `TransitionEventID` carries both ids, so two propagation attempts of one `CandidateID` are
distinct transitions. Updated: pseudocode §0.9 (INPUTS + id), `EnterLowPowerListen` and all hook
callers. Audit: `STAGE_01J_EVENT_ENVELOPE_AUDIT.md`. TV75.

## J4 — Explicit event-sequence ownership

One per-run monotonic `event_creation_seq`, owned SOLELY by the scheduler `ScheduleEvent`, assigned
atomically after deterministic ordering; it is the `seq` in every event envelope and every
`TransitionEventID`. Initialised once at run start (`RoundInitialise` `prior_state = null`) and
preserved across rounds (I-04); no ambient undeclared seq. Updated: pseudocode §0.2/§0.8/§1. Audit:
`STAGE_01J_EVENT_ENVELOPE_AUDIT.md`. TV79.

## J5 — Executable next-round participant path

New procedure `PrepareParticipantsForNewRound` runs in the `ASSIGNMENT` phase (after `RoundInitialise`
and `TemplateCommit`, once a fresh `RoundID`/`TemplateID` exist), enumerates eligible miners in stable
`MinerID` order, and gives each a legal per-state path: REGISTERED→T3, RESERVE→T4,
`LOW_POWER_LISTEN`(`ROUND_ACCEPTED`/`ROUND_ABORTED`)→archive + fresh `ORIGINAL` under the NEW ids via
T10, `LOW_POWER_LISTEN`(`RANGE_EXHAUSTED`/`ASSIGNMENT_REVOKED`)→new-round policy, `OFFLINE`/`DISQUALIFIED`→none.
It establishes the intended assignment set BEFORE `ASSIGNMENT → HASHING` (R4) and never reopens a CLOSED
old-round assignment. Updated: pseudocode §2a. Audit: `STAGE_01J_NEXT_ROUND_PARTICIPATION_AUDIT.md`.
TV76.

## J6 — Security-floor applicability before breach recording

`SecurityFloorEvaluate` checks round-state applicability BEFORE evaluating thresholds: terminal rounds
return `terminal_stale_noop` first; a stale-context census returns `stale_census_observation`;
setup/refresh/exhausted states record ONLY a `security_census_observation` (no I16 breach event); ONLY
`HASHING`/`SOLUTION_PROPAGATION`/`SECURITY_RECOVERY` evaluate thresholds and record I16 breaches, then
the I-05 recovery transitions. Updated: pseudocode §9. Audit:
`STAGE_01J_SECURITY_APPLICABILITY_AUDIT.md`. TV77.

## J7 — Canonical assignment terminal status

`SUPERSEDED` is used ONLY for atomic same-range renewal (`RenewAssignment`); `CLOSED` is the terminal
status for every non-renewal end-of-life (revocation, adversarial withdrawal, abandonment, wake failure,
cancellation, round closure, template closure). The ambiguous `CLOSE/SUPERSEDE` is removed. Adversarial
withdrawal: `status = CLOSED`, `custody_status = revoked`, `revocation_reason = adversarial_withdrawal`;
the lineage then has zero live heads (I18b). Updated: pseudocode §0.8 (status note)/§7/§8a; catalogue
I18b. Audit: `STAGE_01J_ASSIGNMENT_TERMINAL_STATUS_AUDIT.md`. TV78.

## J8 — Security-census provenance

`latest_security_census[event_time]` is a `census_record` carrying its production epoch
(`RoundID_at_census`, `TemplateID_at_census`, `state_version_at_census`, `census_seq`) plus the census
values. `FinalizeEventTimeSecurityCensus` passes the STORED provenance to `SecurityFloorEvaluate` (never
the current epoch); a stale-context census records `stale_census_observation` and triggers no recovery
in a new round/template. Updated: pseudocode §0.8/§9. Audit:
`STAGE_01J_SECURITY_CENSUS_COHERENCE_AUDIT.md`. TV80.

## J9 — Central scheduler guard

New procedure `ScheduleEvent` is the SOLE event-enqueue interface: it rejects a finalised `event_time`,
assigns `event_creation_seq`, applies the delta-cycle forward rule, attaches `RoundID`/`TemplateID` and
the candidate envelope fields, and inserts by the deterministic total-order key. Every `SCHEDULE`
expression is shorthand for a `ScheduleEvent` call. Updated: pseudocode §0.2/§0.7e. Audit:
`STAGE_01J_EVENT_ENVELOPE_AUDIT.md`.

## Summary of changed / added artifacts

| Artifact | Change |
|----------|--------|
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` | §0.2 envelope (seq owner); §0.7e `ScheduleEvent` (J9); §0.8 registries (J1 coherence, J4 `event_creation_seq`, J8 `census_record` provenance; Assignment J7 status note); §0.9 `ApplyMinerStateTransition` (J1/J2/J3/J8); §1 `RoundInitialise` (J4); §2a `PrepareParticipantsForNewRound` (J5); §7 `EnterLowPowerListen` (J3/J7); §8a adversarial exit (J7); §9 `FinalizeEventTimeSecurityCensus`+`SecurityFloorEvaluate` (J1/J6/J8); §16 `HandlePropagationFailure` (J1) |
| `STAGE_01_INVARIANT_CATALOGUE.md` | I18b J7 note (SUPERSEDED renewal-only / CLOSED zero live heads) |
| `STAGE_01_TERMINOLOGY.md` | Stage-1J addendum (J1–J9) |
| `STAGE_01_TRACEABILITY_MATRIX.csv` | Rows R66–R74 (J1–J9) |
| `STAGE_01J_*` (12 new deliverables) | this report + coherence / replay / envelope / next-round / applicability / terminal-status audits + procedure call graph + semantic test vectors + supersession register + cross-document audit + checksum manifest |

No executable source, configuration, DOCX, or PDF file is modified; no Stage 1A–1I artifact is
modified. The specification conforms to J1–J9 while preserving B1–B9, C1–C10, D1–D9, E1–E10, F1–F9,
G1–G11, H1–H9, and I-01…I-08.
