# Stage 1P — Correction Report (horizon-sentinel & recovery-decision lock)

**Branch.** `thesis-v45-pocol-stage1p-horizon-sentinel-recovery-decision-lock`
**Base.** `00aae789694b30a8341d2dda18887e9a0d98d996` (Stage 1O).
**Scope.** Documentation only — no executable source, configuration, DOCX, PDF, or experiment changes.
Protected DOCX drafts byte-identical (draft-42 `2c3afdc5…`, draft-44 `a31400bc…`); Stage 1A–1O lettered
artifacts unmodified (A–O-lock).

**Naming rule (binding).** Algorithm is **PoCol**; mechanism is **the idle policy within PoCol**. No property
(energy, security, fairness, incentive) is claimed. The A1 baseline is unchanged (`8.420833333 kWh`); any
modeled energy change is attributable ONLY to reduced active power-time. No new consensus feature — P1…P5
close the horizon-time processing step, give the horizon-close hook a defined identity, move the recovery
outcome to the post-quiescence epilogue, make completion seating atomic with scheduler success, and version
recovery decisions.

## P1 — Force exactly one horizon-time processing step

`RunEventLoopToHorizon` (§0.7d-run) now processes every `event_time` **strictly less than** `T` via
`ProcessEventTime`, then makes ONE synthetic horizon invocation `ProcessEventTime(T, is_horizon = true,
allow_empty_horizon = true)` guarded by `T not in finalised_event_times`. `ProcessEventTime` (§0.7d) gained
`allow_empty_horizon` and permits an EMPTY drain at `T`, so the horizon sequence runs EXACTLY once even when
the queue holds no event at `T`: the drain (possibly empty) → `CloseRoundAtHorizon` if nonterminal → the `T`
epilogue (a `terminal_stale_noop` that finalises the `T` census created by horizon closure) → `T` added to
`finalised_event_times`. `FinalizeSimulationRun` (§20a) ASSERTS `round_state ∈ {ROUND_ACCEPTED,
ROUND_ABORTED}`, so a nonterminal round can never reach it without horizon closure. Updated: pseudocode
§0.7d/§0.7d-run/§20a; round SM §3.14. Audit: `STAGE_01P_HORIZON_SENTINEL_AUDIT.md`. TV119/TV120.

## P2 — Deterministic run-hook envelope

The undefined `horizon_close_delta_cycle` / `horizon_close_event_seq` are REMOVED. A new per-run `STRUCTURE
RunHookContext` (§0.7e) owns run-hook identity: `run_hook_seq` (separate from the ordinary `event_creation_seq`)
and `applied_run_hook_ids`. `HorizonHookID = (RunID, run_horizon_T, HORIZON_CLOSE)`; the reserved
`RUN_HOOK_CYCLE` delta-cycle is never produced by `ScheduleEvent`, so a run-hook envelope cannot collide with
an ordinary event envelope. `CloseRoundAtHorizon` (§20b) mints ONE envelope `{event_time = T, delta_cycle =
RUN_HOOK_CYCLE, event_seq = run_hook_seq, hook_id = HorizonHookID}`, threads it into `CloseRoundAssignments`
(so every horizon-close miner transition is uniquely identifiable by `(MinerID, assignment_version, run-hook
envelope)`), and is idempotent via `applied_run_hook_ids` — a replay returns `horizon_close_duplicate_noop`
with NO second transition energy and NO second residency boundary (exactly one horizon close per run).
`RunHookContext` is initialised at run start and preserved across rounds (§1). Updated: pseudocode
§0.7e/§0.8/§1/§0.7d/§20b; catalogue I19. Audit: `STAGE_01P_RUN_HOOK_ENVELOPE_AUDIT.md`. TV125.

## P3 — The recovery deadline is a fact, not a pre-epilogue outcome

`RecoveryDeadlineEvent` (§9a) NO LONGER selects `UNRECOVERABLE` or seats a completion. After its stale guard,
it sets `recovery_deadline_reached[episode] <- true` (a FACT) and calls the new
`CaptureSecurityCensusOnRecoveryDeadline` (§9a) — the THIRD coherent writer of
`security_census_dirty`/`latest_security_census` — which writes a coherent census for the deadline timestamp.
A same-timestamp `WakeCompleteEvent` that restores the floor OVERWRITES that census via
`ApplyMinerStateTransition`, so the event-time epilogue reads the FINAL census. The epilogue
(`SecurityFloorEvaluate`, §9) SELECTS the outcome from the FINAL census: a persistent breach WITH the deadline
reached → `UNRECOVERABLE`; a restored floor → `RESTORED`. The deadline never assumes that remaining in
`SECURITY_RECOVERY` means the floor is still breached. Updated: pseudocode §9/§9a; round SM §2.5/§3.10/R14.
Audit: `STAGE_01P_RECOVERY_DEADLINE_DECISION_AUDIT.md`. TV121/TV122.

## P4 — Make completion seating atomic with scheduler success

All completion seating now goes through ONE seater, `SeatRecoveryCompletion` (§9), called by the epilogue. It
sets `recovery_completion_pending[episode] <- true` ONLY AFTER `ScheduleEvent` returns `scheduled`; on
rejection it leaves the flag false, records the exact scheduling disposition, and returns
`recovery_completion_not_seated` (never `recovery_completion_seated`). A decision at `t = T` records
`run_ending_no_recovery_action`, seats nothing, and leaves no false pending flag; `CloseRoundAtHorizon` closes
the round. Combined with the O2 rule (`ScheduleEvent` rejects `target_event_time > T`), no completion is
attempted after or beyond `T`. Updated: pseudocode §9. Audit:
`STAGE_01P_RECOVERY_COMPLETION_ATOMICITY_AUDIT.md`. TV123/TV124.

## P5 — Decision versioning for recovery completion

§0.8 adds `recovery_decision_seq`, `RecoveryDecisionID = (RecoveryEpisodeID, recovery_decision_seq)`, and
`latest_recovery_decision[episode] = { decision_id, outcome }`. `SeatRecoveryCompletion` mints a fresh
`RecoveryDecisionID` per decision and, on scheduler success, records it as the latest; a DIFFERENT outcome
supersedes a pending one, the SAME standing outcome is not re-seated. `CompleteSecurityRecovery` (§10a) carries
its `RecoveryDecisionID` and applies its outcome ONLY if the episode is current AND its decision equals
`latest_recovery_decision[episode].decision_id`; otherwise it returns `recovery_decision_stale_noop`. This
prevents an old `RESTORED`/`UNRECOVERABLE` outcome from being applied after a newer final-census decision
exists; at most one outcome is APPLIED per episode (`recovery_outcome_finalised`, O4). Updated: pseudocode
§0.8/§9/§10a/§0.7g-driver. Audit: `STAGE_01P_RECOVERY_DECISION_VERSION_AUDIT.md`. TV126.

## Summary of changed / added artifacts

| Artifact | Change |
|----------|--------|
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` | §0.7d `ProcessEventTime` (`allow_empty_horizon`, RunHookContext input) + `RunEventLoopToHorizon` (horizon sentinel) (P1/P2); §0.7d-run prose (P1); §0.7e `RunHookContext`/`RUN_HOOK_CYCLE`/`HORIZON_CLOSE` (P2); §0.8 episode registries `recovery_deadline_reached`/`recovery_decision_seq`/`latest_recovery_decision` (P3/P5); §1 RoundInitialise resets + `RunHookContext` init (P2/P3/P5); §9 SecurityFloorEvaluate recovery branches + `SeatRecoveryCompletion` (P3/P4/P5); §9a `RecoveryDeadlineEvent` (records fact) + `CaptureSecurityCensusOnRecoveryDeadline` (P3); §10a `CompleteSecurityRecovery` (RecoveryDecisionID guard) (P5); §20b `CloseRoundAtHorizon` (deterministic run-hook envelope) (P2); §0.7g/§0.7g-driver/§21 recovery + run-hook notes (P2/P3/P5) |
| `STAGE_01_ROUND_STATE_MACHINE.md` | §2.5 exit conditions (deadline records a fact; epilogue decides); §3.10 (P3 deadline + epilogue decision, P5 versioning); §3.14 (P1 horizon sentinel); R14 row (epilogue decides UNRECOVERABLE from final census) |
| `STAGE_01_INVARIANT_CATALOGUE.md` | I19 enforcement point: `CloseRoundAtHorizon` run-hook envelope idempotence (P2 — no double transition energy/boundary; P1 horizon sentinel) |
| `STAGE_01_TERMINOLOGY.md` | Stage-1P addendum (P1–P5) |
| `STAGE_01_TRACEABILITY_MATRIX.csv` | R106–R111 (P1–P5 + TV119–TV126) |
| `STAGE_01P_*` (11 new deliverables) | this report + horizon-sentinel / run-hook-envelope / recovery-deadline-decision / recovery-completion-atomicity / recovery-decision-version audits + procedure call graph + semantic test vectors + supersession register + cross-document audit + checksum manifest |

No executable source, configuration, DOCX, or PDF file is modified; no Stage 1A–1O lettered artifact is
modified. The specification conforms to P1–P5 while preserving B1–B9, C1–C10, D1–D9, E1–E10, F1–F9, G1–G11,
H1–H9, I-01…I-08, J1–J9, K1–K8, L1–L6, M1–M6, N1–N4, and O1–O5. Name remains PoCol; the idle policy within
PoCol is described as a mechanism only; A1 baseline unchanged. The prohibited rebranded-algorithm-name
variants are not used anywhere in this document.
