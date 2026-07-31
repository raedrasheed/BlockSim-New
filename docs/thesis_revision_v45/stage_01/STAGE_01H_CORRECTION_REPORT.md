# Stage 1H — Correction Report (timestamp-causality lock)

**Branch.** `thesis-v45-pocol-stage1h-timestamp-causality-lock`
**Base.** `513d0184278b1ab6049bfef2b15770eea2ff0ebb` (Stage 1G).
**Scope.** Documentation only — no executable source, configuration, DOCX, PDF, or experiment
changes. Protected DOCX drafts byte-identical (draft-42 `2c3afdc5…`, draft-44 `a31400bc…`); Stage
1A–1G artifacts unmodified (F9/G-lock, extended to an A–G-lock this stage).

**Naming rule (binding).** Algorithm is **PoCol**; mechanism is **the idle policy within PoCol**.
Forbidden name strings (`PoCol-E`, `Energy-Aware PoCol`, `Enhanced PoCol`) appear only in prohibition
clauses. No property (energy, security, fairness, incentive) is claimed. The A1 baseline is unchanged
(`8.420833333 kWh`; 141 TH/s, 21.5 J/TH, 3031.5 W); any modeled energy change is attributable ONLY to
reduced active power-time. No new consensus feature — H1–H9 are timestamp-causality, census-timing,
and accounting-consistency corrections.

## H1 — Consolidated round model; no round-state/propagation-set identification

The round-state machine is made internally consistent and consistent with the pseudocode: the old
"`SOLUTION_PROPAGATION` **iff** the set is non-empty" rule and "`active_propagation_set` holds every
live context" phrasing are removed. `active_propagation_set` holds EXACTLY
`{PROPAGATING, PENDING_ACCEPTANCE}` (G6); `DISCOVERED`/`SELF_VALIDATED` are not yet in it. The
round-state and the propagation set are NOT identified: the set may be non-empty while the round is in
`SECURITY_RECOVERY` (G8). Acceptance may occur from `SOLUTION_PROPAGATION` OR `SECURITY_RECOVERY` (R6),
as the atomic result of `AcceptanceBatchFinalize → ValidBlockAccept` (closure downstream of
arbitration, G5). The authoritative same-`event_time` contract is `STAGE_01G_EVENT_MICROPHASE_SPEC.md`
(extended by H2); the frozen `STAGE_01F_EVENT_PRIORITY_TABLE.md` is NOT authoritative. Updated:
round-SM §2.6 (active-propagation-set paragraph, same-timestamp-order paragraph), §2.7 (ROUND_ACCEPTED
entry). Audit: `STAGE_01H_ROUND_STATE_CONSISTENCY_AUDIT.md`. TV60.

## H2 — Delta-cycle same-timestamp scheduling (no backward travel)

The event envelope is extended with `delta_cycle` and `microphase`; the total order key is
`(event_time, delta_cycle, microphase, stable_tie_key, seq)` with
`stable_tie_key = (CandidateID, MinerID, AssignmentID)`. A handler in microphase `m` of
`(event_time = t, delta_cycle = k)` schedules a same-`event_time` event into cycle `k` if its target
microphase is later than `m`, else into cycle `k+1`; the loop finishes all microphases of cycle `k`
before any event of cycle `k+1`; no event travels backward into a completed cycle. Updated: pseudocode
§0.2 (envelope), §0.7 (microphase authority), §0.7-H2 (delta-cycle rule). Contract:
`STAGE_01H_DELTA_CYCLE_CONTRACT.md`. TV51.

## H3 — Single settled-census security evaluation per timestamp

`ApplyMinerStateTransition` no longer schedules a per-transition floor decision. It records
`intermediate_census_for_audit(event_time, current_delta_cycle, …)` (audit only) and, when the
transition changed the `ACTIVE_HASHING` census, sets
`security_evaluation_required[(event_time, current_delta_cycle)]`. Exactly one
`FinalizeTimestampSecurityCensus` runs in microphase 5 per settled `(event_time, delta_cycle)`: it
reads the FINAL settled census, clears the flag, and calls `SecurityFloorEvaluate` at most once
carrying `(RoundID, TemplateID, state_version)`. `FinalizeTimestampSecurityCensus` is the SOLE caller
of `SecurityFloorEvaluate`; `HandlePropagationFailure` now sets the flag instead of scheduling.
Updated: pseudocode §0.8 (registries), §0.9 step (7), §9 (new `FinalizeTimestampSecurityCensus`,
`SecurityFloorEvaluate` precondition), `HandlePropagationFailure`. Audit:
`STAGE_01H_FINAL_CENSUS_AUDIT.md`. TV52.

## H4 — Legal SECURITY_RECOVERY source states

`SecurityFloorEvaluate` may TRANSITION to `SECURITY_RECOVERY` ONLY from
`{HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY}`. On a breach from any other state it records the
census as observation-only and performs NO transition (`refresh_observation_only` /
`exhausted_observation_only` / `setup_observation_only` / `terminal_stale_noop`); breaches are still
recorded (I16), never silently repaired. Updated: pseudocode `SecurityFloorEvaluate` (H4 branch);
round-SM §2.5 consistency. Audit: `STAGE_01H_FINAL_CENSUS_AUDIT.md`. TV53.

## H5 — Zero-latency wake is causally forward

`StartWake` schedules `WakeCompleteEvent` at a future `event_time` for a positive latency; for a
zero-latency wake (a permitted experimental value) it schedules at the SAME `event_time` in
`delta_cycle + 1` at the `WAKE_COMPLETE` microphase, so a resume initiated after the wake microphase
never travels backward into a completed phase. The `WAKING` residency and its
`P_wake · t_wake + E_transition` accounting path always exist (owned by the residency ledger, I19).
Updated: pseudocode `StartWake` (H5 branch), §0.7-H2. Contract: `STAGE_01H_DELTA_CYCLE_CONTRACT.md`.
TV54.

## H6 — State-specific adversarial entry/exit

`AdversarialParticipationChangeEvent` takes legal per-state paths. ENTRY: `REGISTERED`/`RESERVE` →
`RangeAssign` (fresh `PENDING` + `StartWake`, T3/T4); `OFFLINE` → hook `OFFLINE→REGISTERED` (T17) then
`RangeAssign`; still-`PAUSED` `LOW_POWER_LISTEN` → `ResumeFromPause(trigger = adversarial_reactivation)`
on its OWN head (matched ids, never `RangeAssign`, so no second live head, I18b); post-closure
`LOW_POWER_LISTEN` → fresh `ORIGINAL` `PENDING` + `StartWake` from `LOW_POWER_LISTEN` (T10, the legal
edge — not `RangeAssign`, whose precondition is `REGISTERED`/`RESERVE`). EXIT acts ONLY on
`ACTIVE_HASHING`: preserve accepted coverage, expose only the accepted unsearched suffix (C4), record
the I9 reason/provenance, cancel the version's pending `HashWorkEvent`s, close the `CURRENT` head
explicitly (no live head remains, I18a), depart via T11 — all through the hook. `ResumeFromPause`'s
precondition was extended to accept the single non-failure trigger `adversarial_reactivation`. Updated:
pseudocode §8a, `ResumeFromPause` precondition/NOTE. Audit:
`STAGE_01H_ADVERSARIAL_PARTICIPATION_AUDIT.md`. TV55/TV56/TV57.

## H7 — Single-owner, no-double-count residency (invariant I19)

`residency_ledger`, owned SOLELY by `ApplyMinerStateTransition`, is the single owner of every
per-miner `t_<state>`, including `t_ACTIVE_HASHING = t_hash`; it opens/closes each interval at the
state boundary and accrues `P_<state> · Δt` once. `HashWorkEvent` records hash-work METADATA only and
adds ZERO duration, so an `ACTIVE_HASHING` occupancy is counted once (at the boundary), never per hash
unit. New invariant **I19** formalises single-owner, no-double-count residency. Updated: pseudocode
§0.8 (`residency_ledger`), §0.9 NOTE, §0.7b, `HashWorkEvent`; invariant catalogue (new I19,
cross-reference row, title `I1..I19`). Audit: `STAGE_01H_RESIDENCY_ACCOUNTING_AUDIT.md`. TV58.

## H8 — Explicit `assignment_ref`

`EnterLowPowerListen` receives the EXACT immutable assignment version being paused/exhausted/revoked/
closed as `assignment_ref` (precondition: belongs to the miner AND `status ∈ {CURRENT, PAUSED}`); there
is no undeclared free `assignment`. All five call sites pass the precise version: `LeaseExpiry`,
`EarlyStopVerify`, `ScheduleSolutionPropagation`, `CloseRoundAssignments`, `CloseTemplateAssignments`.
A `SUPERSEDED`/`CLOSED` historical version can never be paused or closed by accident (I18a/I18b).
Updated: pseudocode `EnterLowPowerListen` (INPUTS/PRECONDITIONS/body/NOTE) and its five callers. TV59.

## H9 — Reference updates and supersession register

Cross-document references to invariants (`I1..I18b`, plus the new `I19`) are reconciled: the invariant
catalogue title/summary become `I1..I19`; the I17 enforcement text is corrected to the G3/H6 model
(`AdversarialParticipationChangeEvent` carries adversarial changes through the hook;
`ActiveHashRateUpdate` is compute-only) and the H3 single settled-census evaluation; terminology gains
a Stage-1H addendum; traceability gains rows R49–R57. No `STAGE_01[A-G]_*` file is modified;
supersessions are recorded in `STAGE_01H_SUPERSESSION_REGISTER.md` and
`STAGE_01H_CROSS_DOCUMENT_AUDIT.md`, not by rewriting prior evidence.

## Summary of changed / added artifacts

| Artifact | Change |
|----------|--------|
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` | §0.2 envelope (delta_cycle/microphase); §0.7/§0.7-H2 microphase authority + delta-cycle rule; §0.8 registries (`security_evaluation_required`, `residency_ledger`); §0.9 hook step (7) + NOTE (H3/H7); `StartWake` (H5); `HashWorkEvent` (H7); §8a `AdversarialParticipationChangeEvent` (H6); `ResumeFromPause` (H6 trigger); §9 `FinalizeTimestampSecurityCensus` (H3) + `SecurityFloorEvaluate` (H3/H4); `HandlePropagationFailure` (H3); `EnterLowPowerListen` + 5 callers (H8) |
| `STAGE_01_ROUND_STATE_MACHINE.md` | §2.6 active-propagation-set + same-timestamp-order paragraphs (H1); §2.7 ROUND_ACCEPTED entry (H1) |
| `STAGE_01_INVARIANT_CATALOGUE.md` | New I19 (H7); I17 enforcement text corrected (G3/H3/H6); title/summary `I1..I19` |
| `STAGE_01_TERMINOLOGY.md` | Stage-1H addendum (delta_cycle, final census, legal recovery sources, zero-latency wake, adversarial entry/exit, residency single owner, explicit assignment_ref) |
| `STAGE_01_TRACEABILITY_MATRIX.csv` | Rows R49–R57 (H1–H9) |
| `STAGE_01H_*` (11 new deliverables) | this report + delta-cycle contract + final-census audit + residency audit + adversarial audit + round-state audit + procedure call graph + semantic test vectors + supersession register + cross-document audit + checksum manifest |

No executable source, configuration, DOCX, or PDF file is modified; no Stage 1A–1G artifact is
modified. The specification conforms to H1–H9 while preserving B1–B9, C1–C10, D1–D9, E1–E10, F1–F9, and
G1–G11.
