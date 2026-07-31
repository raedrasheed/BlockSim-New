# Stage 1M — Supersession Register (minimal executable closure)

This register records, in ONE place, every Stage-1M statement that supersedes a prior-stage statement, so
that **no historical Stage-1A..1L lettered artifact is rewritten**: the prior files remain frozen evidence,
and the corrections live here and in the un-suffixed normative documents.

Name remains **PoCol**; mechanism is **the idle policy within PoCol**. No property is claimed; the A1
baseline (`8.420833333 kWh`) is unchanged; no new consensus feature is introduced.

## Supersession entries

| # | Prior statement (frozen source) | Superseded by (Stage 1M) | Nature |
|--:|----------------------------------|---------------------------|--------|
| 1 | Stage-1L §0.9 POSITIONAL SHORTHAND: a positional `ApplyMinerStateTransition(…, now, reason=…)` implicitly bound the three envelope fields from `EQ.current_event_time/current_delta_cycle/current_event_seq` without procedure-level threading | M1: the shorthand is REMOVED. Every procedure that directly or indirectly calls the hook carries an explicit `dispatch_envelope` and threads it; every hook call spells out `event_time`/`delta_cycle`/`event_seq`; no positional `now` form and no `EQ.current_*` read remain. `STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.9 (+ all hook-reaching procedures) | correction (explicit threading) |
| 2 | Stage-1L `HandlePropagationFailure` `SOLUTION_PROPAGATION → HASHING` re-entry annotated as NOT capturing a census ("any census change from resumed miners is captured at their ApplyMinerStateTransition boundaries") | M2: the re-entry routes through the new `TransitionRoundState` helper, which captures a coherent applicability-entry census on entry to HASHING even with no paused miner, positive-latency resumes, or unchanged `H_active`. Every floor-applicable entry captures a census (helper), except the epilogue's `→ SECURITY_RECOVERY` (documented). `STAGE_01_PROTOCOL_PSEUDOCODE.md` §2a-bis/§16d | correction (census on every floor-applicable entry) |
| 3 | Stage-1L `LeaseExpiry` `CASE PENDING` closed the head and relied on a later `WakeCompleteEvent` self-cancelling "via the G9 stale guard"; `WakeCompleteEvent` had no explicit stale-target guard | M3: `CASE PENDING` is EXECUTABLE — cancel the exact `WakeCompleteEvent`, resolve a `WAKING` holder `WAKING → OFFLINE` (`lease_expired_while_waking`), close, preserve accepted coverage, reassign only after CLOSED; `CASE PAUSED` cancels candidate-specific resume/wake events; `WakeCompleteEvent` BEGINS with an explicit stale-target guard returning `stale_wake_noop` (independent of the HashWorkEvent G9 guard). `STAGE_01_PROTOCOL_PSEUDOCODE.md` §12/§0.10 | correction (executable wake handling) |
| 4 | Stage-1L `CloseRoundAssignments` executed `finalise state durations and energy to the EXACT closure time` (a residency finalisation competing with the boundary owner); `RoundAbort` executed `finalise energy_ledger`; the boundary owner was `RebaseResidencyAtRoundBoundary` (round-boundary only) | M4: `CloseRoundAssignments` performs NO residency finalisation (the in-line line is removed) and records `round_terminal_time` only; the single owner is `SettleResidencyBoundary` with `REBASE_TO_NEXT_ROUND` and `FINAL_RUN_END` modes (idempotent via `boundary_id`); `RoundAbort` settles via `FINAL_RUN_END` before its I5/I6/I7 checks. I19 + energy model updated. `STAGE_01_PROTOCOL_PSEUDOCODE.md` §1a/§17a/§20; catalogue I19; energy model I5 | correction (single boundary owner in executable text) |
| 5 | Stage-1L bare `SCHEDULE event HashWorkEvent(…) AT …`, `SCHEDULE event CertificateArrival/BlockAcceptancePoint(…) AT …`, and `SCHEDULE event ResumeFromPause(…)` omitted an explicit target microphase; `TemplateRefresh` iterated `FOR EACH miner m in eligible` (unsorted) | M5: a canonical event-type → microphase mapping is added (§0.7g); every enqueue is a `ScheduleEvent` call supplying an explicit `target_microphase`; `TemplateRefresh` and the two closure loops are stably sorted before seq assignment. `STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.7g/§5/§16b/§16d/§17a/§19 | correction (microphase-complete, deterministic enqueue) |
| 6 | Stage-1L `TV96` names `RebaseResidencyAtRoundBoundary` as the cross-round residency owner and does not cover the run-end case | M4/M6: `TV102` (Stage-1M) restates the residency-owner behavior against the actual pseudocode — `SettleResidencyBoundary` (REBASE/FINAL_RUN_END), `CloseRoundAssignments` records `round_terminal_time` only. The frozen `STAGE_01L_SEMANTIC_TEST_VECTORS.md` (TV96) is NOT modified; TV102 supersedes it on paper. `STAGE_01M_SEMANTIC_TEST_VECTORS.md` | supersession (test-vector naming) |

## Frozen-artifact discipline (A–L lock)

- No `STAGE_01[A-L]_*` file is modified in Stage 1M (verified by `git diff --name-only <base>`; see
  `STAGE_01M_CROSS_DOCUMENT_AUDIT.md`). All prior correction reports, audits, specs, call graphs, and test
  vectors remain byte-frozen; entries 1–6 above are the ONLY sanctioned way their now-superseded statements
  are amended. In particular `STAGE_01G_EVENT_MICROPHASE_SPEC.md` (the frozen same-timestamp authority) is
  CONSISTENT with the M5 mapping and is not rewritten.
- The L1–L6 model is PRESERVED and made executable: M1 replaces the L1 shorthand with explicit threading;
  M2 completes the L2 single-owner story so every floor-applicable HASHING entry captures a census; M3 makes
  the L4 status-aware `LeaseExpiry` `CASE PENDING` executable and adds the `WakeCompleteEvent` guard; M4
  generalises the L5 `RebaseResidencyAtRoundBoundary` to `SettleResidencyBoundary` and removes the competing
  finalisation; M5 completes the L6 scheduler contract with an explicit microphase per enqueue.
- Historical invariants (I1..I19, incl. I18a/I18b) are NOT re-opened; Stage 1M amends I19 for the unified
  single boundary owner (M4) without altering the frozen invariant IDs.
- The A1 accounting baseline (`8.420833333 kWh`) and the difficulty-fixed rule (I12) are unchanged; no
  energy, security, fairness, or incentive property is claimed.
