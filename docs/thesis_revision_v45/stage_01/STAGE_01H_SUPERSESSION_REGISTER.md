# Stage 1H — Supersession Register (H9)

This register records, in ONE place, every Stage-1H statement that supersedes a prior-stage statement.
It exists so that **no historical Stage-1A..1G artifact is rewritten**: the prior files remain frozen
evidence, and the corrections live here and in the un-suffixed normative documents
(`STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_ROUND_STATE_MACHINE.md`,
`STAGE_01_INVARIANT_CATALOGUE.md`, `STAGE_01_TERMINOLOGY.md`, `STAGE_01_TRACEABILITY_MATRIX.csv`).

Name remains **PoCol**; mechanism is **the idle policy within PoCol**. No property is claimed; the A1
baseline (`8.420833333 kWh`) is unchanged; no new consensus feature is introduced.

## Supersession entries

| # | Prior statement (frozen source) | Superseded by (Stage 1H) | Nature |
|--:|----------------------------------|---------------------------|--------|
| 1 | Round-SM §2.6 "the round is `SOLUTION_PROPAGATION` **iff** `active_propagation_set` is non-empty" and "`active_propagation_set` holds every live `CandidatePropagationContext`" (historical Stage-1F phrasing, restated up to Stage 1G) | H1: the round-state and the propagation set are NOT identified; the set holds EXACTLY `{PROPAGATING, PENDING_ACCEPTANCE}` (G6); the round leaves `SOLUTION_PROPAGATION` only on `propagation_quiescent`; `SECURITY_RECOVERY` may coexist with a non-empty set (G8). `STAGE_01_ROUND_STATE_MACHINE.md` §2.6 | correction (round-model consolidation) |
| 2 | Round-SM §2.6 "Same-timestamp event priority (F8): events fire in the deterministic order of `STAGE_01F_EVENT_PRIORITY_TABLE.md`" (authoritative) | H1/H2: the authoritative same-`event_time` contract is `STAGE_01G_EVENT_MICROPHASE_SPEC.md`, extended by the H2 delta-cycle rule (§0.7-H2); the Stage-1F flat priority table is NOT authoritative | superseding model (the F table remains a frozen artifact) |
| 3 | Round-SM §2.7 "`ROUND_ACCEPTED` — Entry condition: From `SOLUTION_PROPAGATION` on a validated solution" (only source) | H1: `ROUND_ACCEPTED` is entered from `SOLUTION_PROPAGATION` **or `SECURITY_RECOVERY`** (R6/G8), as the atomic result of `AcceptanceBatchFinalize → ValidBlockAccept` (closure downstream of arbitration, G5) | correction (legal acceptance source) |
| 4 | Stage-1F/1G event envelope `{event_type, event_time, …, seq}` and total order `(event_time, seq)` / priority-table order | H2: envelope extended with `delta_cycle` and `microphase`; total order key `(event_time, delta_cycle, microphase, stable_tie_key, seq)`, `stable_tie_key = (CandidateID, MinerID, AssignmentID)`. `STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.2 | extension (no field removed) |
| 5 | Stage-1G `ApplyMinerStateTransition` step scheduling `SecurityFloorEvaluate` at the boundary, and `HandlePropagationFailure ⇒ SecurityFloorEvaluate` | H3: the hook records an audit-only intermediate census and sets `security_evaluation_required[(event_time, delta_cycle)]`; `HandlePropagationFailure` sets the same flag; exactly one `FinalizeTimestampSecurityCensus` (microphase 5) calls `SecurityFloorEvaluate` per settled timestamp | correction (single settled-census evaluation) |
| 6 | Stage-1G `SecurityFloorEvaluate` "always SCHEDULED (never inline)" reachable from the hook / propagation-failure | H3/H4: `SecurityFloorEvaluate` is invoked ONLY by `FinalizeTimestampSecurityCensus`, and may transition to `SECURITY_RECOVERY` ONLY from `{HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY}` (else observation-only). The G10 terminal/stale guard is retained | refinement (sole caller + legal source guard) |
| 7 | Stage-1F/1G `StartWake` scheduling `WakeCompleteEvent` at `now + wake_latency` (no delta-cycle) | H5: a zero-latency wake schedules `WakeCompleteEvent` at the SAME `event_time` in `delta_cycle + 1` at the `WAKE_COMPLETE` microphase (never backward); a positive latency schedules a future `event_time`. `STAGE_01_PROTOCOL_PSEUDOCODE.md` `StartWake` | refinement (causal zero-latency wake) |
| 8 | Stage-1G `AdversarialParticipationChangeEvent` generic entry via `RangeAssign` for any idle state and generic exit via T11 | H6: state-specific entry (`RangeAssign` T3/T4; hook T17 then `RangeAssign`; `ResumeFromPause` on the own PAUSED head; fresh `ORIGINAL` + `StartWake` T10 post-closure) and exit that closes the CURRENT head explicitly (no live head remains). `ResumeFromPause` gains the `adversarial_reactivation` trigger. `STAGE_01_PROTOCOL_PSEUDOCODE.md` §8a | correction (legal per-state paths; I18b preserved) |
| 9 | Stage-1G `HashWorkEvent` "accounts residency by elapsed event time" (§0.7b) | H7/I19: `HashWorkEvent` records hash-work METADATA only and adds ZERO duration; `t_ACTIVE_HASHING = t_hash` is owned SOLELY by the `residency_ledger` via `ApplyMinerStateTransition`, computed once at the boundary. New invariant **I19**. `STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.7b/§5/§0.8/§0.9; `STAGE_01_INVARIANT_CATALOGUE.md` | correction (no double-count residency) |
| 10 | Stage-1E..1G `EnterLowPowerListen` relying on a free `assignment` variable in its body/callers | H8: `EnterLowPowerListen` receives an explicit `assignment_ref` (a live head in `{CURRENT, PAUSED}`); all five callers pass the exact version. `STAGE_01_PROTOCOL_PSEUDOCODE.md` `EnterLowPowerListen` + callers | correction (explicit version binding) |
| 11 | Invariant catalogue I17 enforcement text "the periodic `ActiveHashRateUpdate` step supplies the adversarial-participation census draw" | G3/H6: adversarial changes are carried by `AdversarialParticipationChangeEvent` through the hook; `ActiveHashRateUpdate` is compute-only (no sampling, no census mutation); the single `FinalizeTimestampSecurityCensus` (H3) reads the settled census. `STAGE_01_INVARIANT_CATALOGUE.md` I17 | correction (compute-only census) |

## Frozen-artifact discipline (A–G lock)

- No `STAGE_01[A-G]_*` file is modified in Stage 1H (verified by `git diff --name-only <base>`; see
  `STAGE_01H_CROSS_DOCUMENT_AUDIT.md`). The Stage-1F `STAGE_01F_EVENT_PRIORITY_TABLE.md`, the
  Stage-1G `STAGE_01G_EVENT_MICROPHASE_SPEC.md`, and all prior audits/vectors/call-graphs remain
  byte-frozen; entries 1–11 above are the ONLY sanctioned way their now-superseded statements are
  amended.
- Historical invariants I2 (G1) and I18→I18a/I18b (G2) are NOT re-opened; Stage 1H adds I19 and
  reconciles cross-document references to `I1..I19` (H9) without altering the frozen definitions.
- The A1 accounting baseline (`8.420833333 kWh`) and the difficulty-fixed rule (I12) are unchanged; no
  energy, security, fairness, or incentive property is claimed.
