# Stage 1N — Correction Report (run-lifecycle & recovery closure)

**Branch.** `thesis-v45-pocol-stage1n-run-lifecycle-recovery-closure`
**Base.** `83638de4f72b6ef540dcc11af9fed9b83fc97752` (Stage 1M).
**Scope.** Documentation only — no executable source, configuration, DOCX, PDF, or experiment changes.
Protected DOCX drafts byte-identical (draft-42 `2c3afdc5…`, draft-44 `a31400bc…`); Stage 1A–1M lettered
artifacts unmodified (A–M-lock).

**Naming rule (binding).** Algorithm is **PoCol**; mechanism is **the idle policy within PoCol**. No
property (energy, security, fairness, incentive) is claimed. The A1 baseline is unchanged
(`8.420833333 kWh`); any modeled energy change is attributable ONLY to reduced active power-time. No new
consensus feature — N1…N4 separate the run lifecycle from a single round, make the existing round-SM
R13/R14 recovery contract executable, and complete the driver-event seating map.

## N1 — Separate round abort from simulation end

`RoundAbort` (§20) now terminates exactly ONE round: it dispositions candidate contexts, closes assignments
via `CloseRoundAssignments` (which records `round_terminal_time` at the abort `event_time`), transitions to
`ROUND_ABORTED`, and returns control so `RoundInitialise` may start another round when simulated time
remains. The former `SettleResidencyBoundary(mode = FINAL_RUN_END)` and the `ASSERT durations reconcile to
horizon T` are REMOVED — an early abort at `t < T` never closes residency at the horizon. A new run-level
procedure `FinalizeSimulationRun` (§20a) is the SINGLE run-level terminal action: run EXACTLY ONCE at the
fixed horizon `T` (guarded by `run_finalised`) for `ROUND_ACCEPTED`/`ROUND_ABORTED`/nonterminal final rounds
alike, it drains all events up to the final `event_time`, closes a nonterminal round through the declared
horizon-end disposition, performs the ONE `SettleResidencyBoundary(mode = FINAL_RUN_END, boundary_id =
(RunID, RUN_END))` (no reopen), and only THEN runs the I5/I6/I7 reconciliation. `SettleResidencyBoundary`'s
`FINAL_RUN_END` mode is now invoked ONLY by `FinalizeSimulationRun`. Updated: pseudocode
§20/§20a/§1a/§0.8/§1; catalogue I19; energy model §3; round SM §2.10/§3.14. Audit:
`STAGE_01N_RUN_FINALISATION_AUDIT.md`. TV104/TV105/TV106.

## N2 — Executable security-recovery completion path (R13/R14)

The round-state-machine R13 (FloorRestored) and R14 (FloorUnrecoverable) contracts are now EXECUTABLE
through the single named procedure `CompleteSecurityRecovery` (§10a). It is seated on the queue by the
epilogue's floor-restored decision (§9: when `SecurityFloorEvaluate` finds no breach while `round_state =
SECURITY_RECOVERY`, it seats one `CompleteSecurityRecovery` at a STRICTLY LATER `event_time`, microphase
`RECOVERY_COMPLETE`, carrying the settled floor result + the decision epoch, I-02) — the epilogue performs
no inline transition. `CompleteSecurityRecovery` guards a stale decision, then branches: **A** live
propagation contexts remain → `SECURITY_RECOVERY → SOLUTION_PROPAGATION` via `TransitionRoundState`
(contexts + events preserved, G8); **B** no context, no assignment change → `SECURITY_RECOVERY → HASHING`
via `TransitionRoundState`; **C** redistribution needed → `SECURITY_RECOVERY → ASSIGNMENT`, build the valid
disjoint set (no new template), then `CompleteAssignmentPhase → HASHING`; **D** floor unrecoverable →
`RoundAbort(reason = floor_unrecoverable)` (round only, N1). Branches A/B/C reach a floor-applicable state
through `TransitionRoundState`/`CompleteAssignmentPhase`, so the applicability-entry census is ALWAYS
captured (M2). Every "R13 described but non-executable" claim is removed. Updated: pseudocode
§10a/§9/§2a-bis/§16d; round SM R13/R14/§3.10. Audit: `STAGE_01N_SECURITY_RECOVERY_EXIT_AUDIT.md`.
TV107/TV108/TV109.

## N3 — Complete the driver-event microphase map

`§0.7g-driver` declares, for every sim-driver entry point seated on the queue, its event type, target
microphase, stable tie key, required envelope fields, and its right (or not) to create same-time
delta-cycle events. It covers `RoundInitialise` (`ROUND_SETUP`), `TemplateCommit` (`TEMPLATE_COMMIT`),
`PrepareParticipantsForNewRound` (`ASSIGNMENT_SETUP`), `MinerRegister` (`REGISTRATION`), `ReserveActivate`
(`RECOVERY_ACTIVATE`), `FullRangeExhaustNoSolution` (`RANGE_EXHAUST_ADJUDICATE`), `CompleteSecurityRecovery`
(`RECOVERY_COMPLETE`), `RoundAbort` (`TERMINAL_ABORT`, §21 item 1), and `FinalizeSimulationRun`
(`RUN_FINALISE`, a run-level terminal). No driver entry point receives a `dispatch_envelope` without such a
normative `ScheduleEvent` seating rule; `RoundAbort` retains terminal-abort priority and
`FinalizeSimulationRun` is a run-level action processed after every ordinary round event. Updated: pseudocode
§0.7g-driver/§21. Audit: `STAGE_01N_DRIVER_EVENT_MAPPING_AUDIT.md`. TV110.

## N4 — Align normative text and audits

The un-suffixed normative documents are corrected so no claim survives that (a) `RoundAbort` is the generic
final-run flush, (b) no executable `SECURITY_RECOVERY` exit exists, or (c) all driver entry points already
have a complete microphase mapping. Updated: `STAGE_01_PROTOCOL_PSEUDOCODE.md`,
`STAGE_01_ROUND_STATE_MACHINE.md` (§2.10/§3.10/§3.14, R13/R14 rows), `STAGE_01_ENERGY_MODEL_SPECIFICATION.md`
(§3 boundary-settle paragraph), `STAGE_01_INVARIANT_CATALOGUE.md` (I19), `STAGE_01_TERMINOLOGY.md` (Stage-1N
addendum), `STAGE_01_TRACEABILITY_MATRIX.csv` (R92 updated; R95–R99 added). Historical Stage-1A–1M artifacts
are NOT modified; supersessions are recorded in `STAGE_01N_SUPERSESSION_REGISTER.md`.

## Summary of changed / added artifacts

| Artifact | Change |
|----------|--------|
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` | §20 `RoundAbort` round-only (FINAL_RUN_END + horizon reconciliation removed) (N1); §20a `FinalizeSimulationRun` (N1); §1a `SettleResidencyBoundary` FINAL_RUN_END only via FinalizeSimulationRun + `(RunID, RUN_END)` (N1); §0.8 `run_finalised`/`RunID` (N1); §1 RoundInitialise init/preserve (N1); §9 SecurityFloorEvaluate floor-restored seating (N2); §10a `CompleteSecurityRecovery` (N2); §2a-bis note (recovery exits executable) (N2); §16d note (N2); §0.7g-driver seating table (N3); §21 RECOVERY_COMPLETE + RUN_FINALISE (N3) |
| `STAGE_01_ROUND_STATE_MACHINE.md` | §2.10 (RoundAbort round-only + FinalizeSimulationRun); §3.10 (recovery exit executable); §3.14 (run-level finalisation); R13/R14 rows annotated executable (N1/N2) |
| `STAGE_01_ENERGY_MODEL_SPECIFICATION.md` | §3 I5 boundary-settle paragraph: FINAL_RUN_END owned by FinalizeSimulationRun; RoundAbort no run-end settle (N1) |
| `STAGE_01_INVARIANT_CATALOGUE.md` | I19: FINAL_RUN_END owner reassigned to FinalizeSimulationRun; RoundAbort none (N1) |
| `STAGE_01_TERMINOLOGY.md` | Stage-1N addendum (N1–N4) |
| `STAGE_01_TRACEABILITY_MATRIX.csv` | R92 updated (FinalizeSimulationRun); R95–R99 (N1–N4 + TV104–TV110) |
| `STAGE_01N_*` (9 new deliverables) | this report + run-finalisation / security-recovery-exit / driver-event-mapping audits + procedure call graph + semantic test vectors + supersession register + cross-document audit + checksum manifest |

No executable source, configuration, DOCX, or PDF file is modified; no Stage 1A–1M lettered artifact is
modified. The specification conforms to N1–N4 while preserving B1–B9, C1–C10, D1–D9, E1–E10, F1–F9, G1–G11,
H1–H9, I-01…I-08, J1–J9, K1–K8, L1–L6, and M1–M6. Name remains PoCol; the idle policy within PoCol is
described as a mechanism only; A1 baseline unchanged.
