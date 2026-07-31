# Stage 1N — Supersession Register (run-lifecycle & recovery closure)

This register records, in ONE place, every Stage-1N statement that supersedes a prior-stage statement, so
that **no historical Stage-1A..1M lettered artifact is rewritten**: the prior files remain frozen evidence,
and the corrections live here and in the un-suffixed normative documents.

Name remains **PoCol**; mechanism is **the idle policy within PoCol**. No property is claimed; the A1
baseline (`8.420833333 kWh`) is unchanged; no new consensus feature is introduced (R13/R14 are existing
round-state-machine contracts made executable; run finalisation is an accounting boundary, not a feature).

## Supersession entries

| # | Prior statement (frozen source) | Superseded by (Stage 1N) | Nature |
|--:|----------------------------------|---------------------------|--------|
| 1 | Stage-1M `RoundAbort` performed `SettleResidencyBoundary(mode = FINAL_RUN_END, boundary_id = (RoundID_current, RUN_END))` and asserted durations reconcile to the horizon `T` — treating every round abort as the run's final flush | N1: `RoundAbort` terminates ONE round only — it dispositions candidates, closes assignments (recording `round_terminal_time` at the abort `event_time`), transitions to `ROUND_ABORTED`, and returns control; it performs NO run-end settle and NO horizon reconciliation. An early abort at `t < T` is followed by `RoundInitialise`. `STAGE_01_PROTOCOL_PSEUDOCODE.md` §20 | correction (round abort ≠ run end) |
| 2 | Stage-1M had no run-level finaliser; the run-end settle + I5/I6/I7 reconciliation lived inside `RoundAbort` | N1: `FinalizeSimulationRun` (§20a) is the SINGLE run-level terminal action, run EXACTLY ONCE at the horizon `T` for `ROUND_ACCEPTED`/`ROUND_ABORTED`/nonterminal final rounds alike; it drains to `T`, horizon-closes a nonterminal round, performs the ONE `SettleResidencyBoundary(FINAL_RUN_END, (RunID, RUN_END))`, then reconciles I5/I6/I7; guarded by `run_finalised`. `STAGE_01_PROTOCOL_PSEUDOCODE.md` §20a/§0.8/§1 | addition (single generic run finaliser) |
| 3 | Stage-1M `TransitionRoundState` note: "There is no executable `SECURITY_RECOVERY -> HASHING` restore transition in this pseudocode (round SM R13)"; round SM R13/R14 described but not executable | N2: `CompleteSecurityRecovery` (§10a) makes R13/R14 EXECUTABLE — branch A → `SOLUTION_PROPAGATION` (contexts+events preserved), B → `HASHING`, C → `ASSIGNMENT → CompleteAssignmentPhase → HASHING` (no new template), D → `RoundAbort(floor_unrecoverable)`; branches A/B/C capture the applicability census via `TransitionRoundState`/`CompleteAssignmentPhase`. Seated by the epilogue's floor-restored decision (§9, strictly-later `event_time`, I-02). `STAGE_01_PROTOCOL_PSEUDOCODE.md` §10a/§9/§2a-bis | correction (executable R13/R14) |
| 4 | Stage-1M `§0.7g` gave a microphase mapping for queued MINER events only; sim-driver entry points had no complete declared seating (event type / microphase / tie key / envelope fields / same-time delta-cycle right) | N3: `§0.7g-driver` declares the full seating rule for every sim-driver entry point (`RoundInitialise`, `TemplateCommit`, `PrepareParticipantsForNewRound`, `MinerRegister`, `ReserveActivate`, `FullRangeExhaustNoSolution`, `CompleteSecurityRecovery`, `RoundAbort`, `FinalizeSimulationRun`); `RoundAbort` keeps `TERMINAL_ABORT` (§21 item 1); `FinalizeSimulationRun` is `RUN_FINALISE`, a run-level terminal. `STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.7g-driver/§21 | correction (complete driver mapping) |
| 5 | Stage-1M I19 / energy-model I5 attributed the `FINAL_RUN_END` settle to `RoundInitialise` / `RoundAbort` | N1: the `FINAL_RUN_END` settle is owned SOLELY by `FinalizeSimulationRun`; `RoundInitialise` owns only `REBASE_TO_NEXT_ROUND`; `RoundAbort` owns neither. I19 (catalogue) and the energy-model I5 boundary-settle paragraph updated. `STAGE_01_INVARIANT_CATALOGUE.md` I19; `STAGE_01_ENERGY_MODEL_SPECIFICATION.md` §3 | correction (run-end owner) |
| 6 | Stage-1M round SM §2.10/§3.10 described the recovery exit and abort without an executable owner and without distinguishing round abort from run end | N1/N2: round SM §2.10 (RoundAbort round-scope only + FinalizeSimulationRun run-level), §3.10 (recovery exit EXECUTABLE via `CompleteSecurityRecovery`), §3.14 (run-level finalisation), R13/R14 rows annotated executable. `STAGE_01_ROUND_STATE_MACHINE.md` §2.10/§3.10/§3.14/R13/R14 | correction (round SM alignment) |

## Frozen-artifact discipline (A–M lock)

- No `STAGE_01[A-M]_*` file is modified in Stage 1N (verified by `git diff --name-only <base>`; see
  `STAGE_01N_CROSS_DOCUMENT_AUDIT.md`). All prior correction reports, audits, specs, call graphs, and test
  vectors remain byte-frozen; entries 1–6 above are the ONLY sanctioned way their now-superseded statements
  are amended.
- The L1–L6 and M1–M6 models are PRESERVED: N1 uses the M4 `SettleResidencyBoundary` (adding the run-end
  owner `FinalizeSimulationRun`); N2 reuses the M2 `TransitionRoundState` census helper and the L2
  `CompleteAssignmentPhase`; N3 extends the M5 `§0.7g` mapping.
- Historical invariants (I1..I19) are NOT re-opened; Stage 1N clarifies the I19 `FINAL_RUN_END` owner (N1)
  without altering the frozen invariant IDs.
- The A1 accounting baseline (`8.420833333 kWh`) and the difficulty-fixed rule (I12) are unchanged; no
  energy, security, fairness, or incentive property is claimed.
