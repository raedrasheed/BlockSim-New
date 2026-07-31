# Stage 1L — Correction Report (final contract reconciliation)

**Branch.** `thesis-v45-pocol-stage1l-final-contract-reconciliation`
**Base.** `d9ff9680b987ae41490c4af2101500651831717b` (Stage 1K).
**Scope.** Documentation only — no executable source, configuration, DOCX, PDF, or experiment
changes. Protected DOCX drafts byte-identical (draft-42 `2c3afdc5…`, draft-44 `a31400bc…`); Stage
1A–1K lettered artifacts unmodified (A–K-lock).

**Naming rule (binding).** Algorithm is **PoCol**; mechanism is **the idle policy within PoCol**.
No property (energy, security, fairness, incentive) is claimed. The A1 baseline is unchanged
(`8.420833333 kWh`); any modeled energy change is attributable ONLY to reduced active power-time. No
new consensus feature — L1…L6 are a **final contract reconciliation** that removes latent
contradictions introduced across Stages 1H–1K (event-envelope threading, a duplicated
assignment-phase transition, a self-contradictory same-timestamp order, a status-blind lease expiry, a
two-procedure round-boundary rebase, and a residual explicit `delta_cycle` in scheduling).

## L1 — Thread the event envelope through every miner transition

`ProcessEventTime` materialises ONE `dispatch_envelope = (event_time, delta_cycle, event_seq)` per
dispatched event, from the event's OWN enqueued envelope, and records it in `EventQueueContext`
(new field `current_event_seq`, §0.7e). Every `StartWake` gained an explicit `dispatch_envelope` input
and threads all three fields into its WAKING `ApplyMinerStateTransition`; every `StartWake` caller
(`PrepareParticipantsForNewRound`, `RangeAssign`, `ReserveActivate`, `RangeReassign`, `ResumeFromPause`,
`TemplateRefresh`, `AdversarialParticipationChangeEvent`) threads it, and the unsupported
`driver_envelope = env` arguments are removed. Sim-driver entry points (`MinerRegister`,
`PrepareParticipantsForNewRound`, `ReserveActivate`) no longer manually stamp `next
EQ.event_creation_seq`: the seq is owned SOLELY by `ScheduleEvent`, and each entry point is itself
seated on the queue and dispatched, so its `dispatch_envelope` is the sanctioned source (§0.7f — the K4
manual-stamp alternative is withdrawn). The normative POSITIONAL SHORTHAND (§0.9) defines a positional
`ApplyMinerStateTransition(…, now, …)` to bind all three fields from `dispatch_envelope` (available
identically as the threaded parameter or the `EQ.current_*` fields), so NO call omits `event_time`,
`delta_cycle`, or `event_seq` semantically or syntactically. Updated: pseudocode
§0.7/§0.7e/§0.7f/§0.9/§0.10/§2a/§3/§4/§8a/§10/§13/§16a/§18/§19. Audit:
`STAGE_01L_EVENT_ENVELOPE_AUDIT.md`. TV91.

## L2 — A single ASSIGNMENT → HASHING path

`CompleteAssignmentPhase` (K2) is the SOLE executable `ASSIGNMENT → HASHING` (R4) owner: it asserts the
intended set is well-formed, performs the transition, and captures the K7 applicability-entry census.
Both `PrepareParticipantsForNewRound` and `TemplateRefresh` now route through it; the former in-line
`TRANSITION round_state -> HASHING` in `TemplateRefresh` is removed. The `SOLUTION_PROPAGATION →
HASHING` transition in `HandlePropagationFailure` is a DISTINCT round-SM re-entry (annotated not-R4) and
is correctly NOT routed through `CompleteAssignmentPhase`; its census changes are captured at resumed
miners' `ApplyMinerStateTransition` boundaries (J1). Every entry to HASHING via the assignment phase
therefore captures the census. Updated: pseudocode §2b/§2a/§19; §16b re-entry annotation. Audit:
`STAGE_01L_ASSIGNMENT_PHASE_UNIFICATION_AUDIT.md`. TV92.

## L3 — One canonical discovery-before-lease-expiry order

The §21 priority table orders solution discovery (item 7) before lease expiry (item 10). A
contradicting "Consequences" statement that said discovery "is processed AFTER the lease-expiry
decision" is REMOVED and replaced by the canonical rule: at a shared `event_time`, discovery is
processed BEFORE lease expiry. The order now agrees across §0.7 (microphase list), the §21 priority
table, and the frozen authoritative `STAGE_01G_EVENT_MICROPHASE_SPEC.md §4`. A boundary discovery
captures its immutable snapshot (E1) against the still-`CURRENT` head before the lease can expire; the
head then pauses and `LeaseExpiry` handles it via the L4 `CASE PAUSED`, never retracting the captured
discovery. The reverse order is forbidden (it would lose a boundary solution to the G9 stale guard).
Updated: pseudocode §21 (table annotations + rewritten consequences). Audit:
`STAGE_01L_EVENT_ORDER_AUDIT.md`. TV93.

## L4 — Status-aware lease expiry

`LeaseExpiry` now branches on the CANONICAL status (§0.8/J7) of the EXACT expiring version:
`SUPERSEDED`/`CLOSED` → stale no-op; `CURRENT` → renew (F7, never reassigned) or canonical CLOSE via
`EnterLowPowerListen` (K6) then reassign; `PAUSED` → CLOSE the paused head WITHOUT a wake (re-classify
the holder's parked reason to `ASSIGNMENT_REVOKED`, clear pause bookkeeping) then reassign; `PENDING` →
CLOSE the un-activated head then reassign. The common reassign tail asserts `status(assignment) =
CLOSED`, and `RangeReassign` now asserts `status(source) = CLOSED` — so a suffix is reassigned ONLY
after its source lineage head is CLOSED. `SUPERSEDED` remains renewal-only; I18a/I18b hold at every
observable point. Updated: pseudocode §12 (`LeaseExpiry`), §13 (`RangeReassign` precondition/assert).
Audit: `STAGE_01L_LEASE_STATUS_AUDIT.md`. TV94/TV95.

## L5 — A single idempotent round-boundary residency owner

The two K3 procedures `FinalizeRoundResidency` + `BeginRoundResidency` are SUPERSEDED by ONE procedure
`RebaseResidencyAtRoundBoundary` (§1a) that performs the old-round CLOSE and the new-round REOPEN
together, IDEMPOTENTLY via a deterministic `boundary_id = (prior_RoundID, new_RoundID)` (a repeat is a
no-op via the per-run `rebased_boundaries` set). `boundary_time = prior_state.round_terminal_time`,
recorded ONLY by `CloseRoundAssignments` (which performs NO rebase). `ApplyMinerStateTransition` remains
the sole owner of intervals for an ACTUAL state change; the boundary charges NO transition energy and
the idle interval is counted EXACTLY ONCE. Invariant **I19** and the energy-model I5 duration
reconciliation are updated. Updated: pseudocode §1a/§0.8/§1/§17a; catalogue I19; energy model §"Duration
reconciliation to the horizon (I5)". Audit: `STAGE_01L_RESIDENCY_BOUNDARY_AUDIT.md`. TV96.

## L6 — ScheduleEvent is the sole delta-cycle authority

§0.7e is strengthened: `ScheduleEvent` is the SOLE authority over `delta_cycle`; no `SCHEDULE`
expression, `ScheduleEvent` argument, or handler supplies, writes, or overrides one. Every
`delta_cycle` in the text is the value `ScheduleEvent` derived, or the `dispatch_envelope.delta_cycle`
`ProcessEventTime` reads back at dispatch. `StartWake` now schedules `WakeCompleteEvent` through
`ScheduleEvent` with ONLY `(target_event_time, target_microphase)` — positive latency → `now +
wake_latency`; zero latency → `now` at `WAKE_COMPLETE` — the former explicit `delta_cycle = 0` /
`delta_cycle+1` is removed, and `ScheduleEvent` alone derives the delta-cycle. Updated: pseudocode
§0.7e/§0.10. Audit: `STAGE_01L_SCHEDULER_CONFORMANCE_AUDIT.md`. TV97.

## Summary of changed / added artifacts

| Artifact | Change |
|----------|--------|
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` | §0.7 ProcessEventTime dispatch_envelope (L1); §0.7e `current_event_seq` + sole delta-cycle authority (L1/L6); §0.7f single sanctioned envelope source (L1); §0.9 positional-shorthand convention (L1); §0.10 StartWake envelope + ScheduleEvent WakeCompleteEvent (L1/L6); §1 RoundInitialise rebase call + `rebased_boundaries` (L5); §1a `RebaseResidencyAtRoundBoundary` (L5); §0.8 registries `rebased_boundaries` + K3/L5 comment (L5); §2a PrepareParticipantsForNewRound envelope (L1); §2b/§19 single ASSIGNMENT→HASHING (L2); §3 MinerRegister (L1); §4 RangeAssign (L1); §8a AdversarialParticipationChangeEvent (L1); §10 ReserveActivate (L1); §12 LeaseExpiry status-aware (L4); §13 RangeReassign status(source)=CLOSED (L4) + envelope (L1); §16a ResumeFromPause (L1); §16b SOLUTION_PROPAGATION→HASHING annotation (L2); §17a CloseRoundAssignments round_terminal_time (L5); §18 FullRangeExhaustNoSolution (L1); §21 discovery-before-lease-expiry order (L3) |
| `STAGE_01_INVARIANT_CATALOGUE.md` | I19 amended: single idempotent boundary owner (L5) |
| `STAGE_01_TERMINOLOGY.md` | Stage-1L addendum (L1–L6); K3 rebase entry annotated superseded |
| `STAGE_01_TRACEABILITY_MATRIX.csv` | R77 updated (L5 owner); rows R83–R88 (L1–L6) |
| `STAGE_01_ENERGY_MODEL_SPECIFICATION.md` | I5 cross-round boundary rebase paragraph (L5) |
| `STAGE_01L_*` (12 new deliverables) | this report + event-envelope / assignment-phase-unification / event-order / lease-status / residency-boundary / scheduler-conformance audits + procedure call graph + semantic test vectors + supersession register + cross-document audit + checksum manifest |

No executable source, configuration, DOCX, or PDF file is modified; no Stage 1A–1K lettered artifact is
modified. The specification conforms to L1–L6 while preserving B1–B9, C1–C10, D1–D9, E1–E10, F1–F9,
G1–G11, H1–H9, I-01…I-08, J1–J9, and K1–K8. Name remains PoCol; the idle policy within PoCol is
described as a mechanism only; A1 baseline unchanged.
