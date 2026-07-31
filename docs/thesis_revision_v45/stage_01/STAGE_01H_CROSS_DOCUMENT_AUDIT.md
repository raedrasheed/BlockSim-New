# Stage 1H — Cross-Document Audit (acceptance gates)

The thirteen Stage-1H acceptance gates, verified by procedure-call-graph, event-envelope, and corpus
analysis over `docs/thesis_revision_v45/stage_01/` (not string search alone), plus cross-document
consistency and protected/historical-artifact verification. Name remains **PoCol**; mechanism is **the
idle policy within PoCol**; no property is claimed; the A1 baseline (`8.420833333 kWh`) is unchanged.

| # | Acceptance gate | Result |
|--:|-----------------|--------|
| 1 | Consolidated round model — no round-state/propagation-set `iff` (H1) | **PASS** — round-SM §2.6 removes "`SOLUTION_PROPAGATION` iff the set is non-empty" and "holds every live context"; `active_propagation_set = {PROPAGATING, PENDING_ACCEPTANCE}` (G6); the round leaves `SOLUTION_PROPAGATION` only on `propagation_quiescent`; `SECURITY_RECOVERY` may coexist (G8). `STAGE_01H_ROUND_STATE_CONSISTENCY_AUDIT.md`; TV60 |
| 2 | Acceptance from `SOLUTION_PROPAGATION` OR `SECURITY_RECOVERY`; microphase spec authoritative (H1) | **PASS** — §2.7 ROUND_ACCEPTED entry lists both sources (R6/G8); closure is the atomic result of `AcceptanceBatchFinalize → ValidBlockAccept` (G5); §2.6 same-timestamp order cites `STAGE_01G_EVENT_MICROPHASE_SPEC.md` (extended by H2), and marks `STAGE_01F_EVENT_PRIORITY_TABLE.md` NOT authoritative. TV60 |
| 3 | Delta-cycle envelope; no backward travel within a timestamp (H2) | **PASS** — §0.2 envelope adds `delta_cycle`/`microphase`; total order `(event_time, delta_cycle, microphase, stable_tie_key, seq)`, `stable_tie_key = (CandidateID, MinerID, AssignmentID)`; §0.7-H2 forbids backward travel and completes cycle `k` before `k+1`. `STAGE_01H_DELTA_CYCLE_CONTRACT.md`; TV51 |
| 4 | Single settled-census security evaluation per timestamp (H3) | **PASS** — `ApplyMinerStateTransition` records an audit-only intermediate census and sets `security_evaluation_required[(event_time, delta_cycle)]`; one `FinalizeTimestampSecurityCensus` (microphase 5) is the SOLE caller of `SecurityFloorEvaluate`; `HandlePropagationFailure` sets the flag, does not schedule. `STAGE_01H_FINAL_CENSUS_AUDIT.md`; TV52 |
| 5 | Legal `SECURITY_RECOVERY` source states only (H4) | **PASS** — `SecurityFloorEvaluate` transitions to `SECURITY_RECOVERY` ONLY from `{HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY}`; otherwise observation-only (`refresh`/`exhausted`/`setup_observation_only`, `terminal_stale_noop`); breaches still recorded (I16). `STAGE_01H_FINAL_CENSUS_AUDIT.md`; TV53 |
| 6 | Zero-latency wake is causally forward (H5) | **PASS** — `StartWake` schedules `WakeCompleteEvent` at `event_time = now, delta_cycle = current_delta_cycle + 1, microphase = WAKE_COMPLETE` for `wake_latency = 0`; positive latency schedules a future `event_time`; WAKING accounting path preserved (I19). `STAGE_01H_DELTA_CYCLE_CONTRACT.md`; TV54 |
| 7 | State-specific adversarial entry/exit; no second live head; no illegal `RangeAssign` (H6) | **PASS** — §8a routes REGISTERED/RESERVE→`RangeAssign` (T3/T4); OFFLINE→hook T17 then `RangeAssign`; still-PAUSED LPL→`ResumeFromPause` (own head, T30); post-closure LPL→fresh `ORIGINAL`+`StartWake` (T10, not `RangeAssign`); exit only from ACTIVE_HASHING closes the CURRENT head (T11). `STAGE_01H_ADVERSARIAL_PARTICIPATION_AUDIT.md`; TV55/56/57 |
| 8 | Single-owner, no-double-count residency (H7/I19) | **PASS** — `residency_ledger` (owned by `ApplyMinerStateTransition`) is the SOLE owner of every `t_<state>` incl `t_ACTIVE_HASHING = t_hash`; `HashWorkEvent` records metadata only, adds ZERO duration (§0.7b/§5); new invariant I19 in the catalogue. `STAGE_01H_RESIDENCY_ACCOUNTING_AUDIT.md`; TV58 |
| 9 | Explicit `assignment_ref` at every `EnterLowPowerListen` call site (H8) | **PASS** — `EnterLowPowerListen` requires `assignment_ref` (belongs to miner AND `status ∈ {CURRENT, PAUSED}`); all five callers (`LeaseExpiry`, `EarlyStopVerify`, `ScheduleSolutionPropagation`, `CloseRoundAssignments`, `CloseTemplateAssignments`) pass the exact version. TV59 |
| 10 | Reference updates (`I1..I19`) + supersession register; A–G frozen (H9) | **PASS** — catalogue title/summary `I1..I19`; I17 enforcement text corrected (G3/H3/H6); terminology Stage-1H addendum; traceability R49–R57; supersessions in `STAGE_01H_SUPERSESSION_REGISTER.md`, not by rewriting prior evidence |
| 11 | TV51–TV60 pass on paper | **PASS** — `STAGE_01H_SEMANTIC_TEST_VECTORS.md`; every vector names exact procedures + preconditions; no unmodeled external action; A1 preserved by TV58 |
| 12 | Procedure call graph has no dangling calls | **PASS** — 42 defined; 0 called-but-undefined; `FinalizeTimestampSecurityCensus` sole caller of `SecurityFloorEvaluate`; `AdversarialParticipationChangeEvent` reaches only legal per-state edges. `STAGE_01H_PROCEDURE_CALL_GRAPH.md` |
| 13 | No executable source, configuration, DOCX, or PDF changes; no Stage-1A..1G artifact modified | **PASS** — `git diff` confined to `docs/thesis_revision_v45/stage_01/`; draft-42 `2c3afdc5…`, draft-44 `a31400bc…` byte-identical; `git diff --name-only <base>` shows no `STAGE_01[A-G]_*` file |

## Cross-document consistency

| Check | Result |
|-------|--------|
| Name always **PoCol**; mechanism only "the idle policy within PoCol" | **PASS** — every forbidden-name hit is a prohibition clause |
| Single miner-state writer / single residency owner | **PASS** — `ApplyMinerStateTransition` is the sole `miner_state` writer and sole `residency_ledger` owner (H7/I19); `HashWorkEvent` adds zero duration |
| One security evaluation per settled timestamp | **PASS** — `FinalizeTimestampSecurityCensus` (microphase 5) is the sole caller of `SecurityFloorEvaluate`; the hook and `HandlePropagationFailure` set the flag only (H3) |
| Delta-cycle ordering consistent | **PASS** — §0.2 envelope, §0.7-H2 rule, `StartWake` (H5), and the round-SM same-timestamp paragraph all reference the same total order key and microphase authority |
| Round-model consistent (SM ↔ pseudocode) | **PASS** — round-SM §2.5/§2.6/§2.7 + R6/R8/R13 agree with pseudocode §0.6 `propagation_quiescent`, §0.8 membership, `ValidBlockAccept` (accepts from SP/SR), `AcceptanceBatchFinalize` |
| Adversarial participation consistent | **PASS** — §8a legal per-state paths; `ResumeFromPause` trigger set extended with `adversarial_reactivation`; `ActiveHashRateUpdate` compute-only; I17 enforcement text corrected |
| Invariant catalogue updated | **PASS** — new I19 (H7); I17 enforcement text (G3/H3/H6); title/summary `I1..I19` |
| Terminology addendum | **PASS** — delta_cycle, single final census, legal recovery sources, zero-latency wake, adversarial entry/exit, residency single owner, explicit assignment_ref |
| Traceability updated | **PASS** — R49–R57 (H1–H9) |
| Call graph has no dangling calls | **PASS** — 42 defined; 0 called-but-undefined (`STAGE_01H_PROCEDURE_CALL_GRAPH.md`) |
| A1 discipline | **PASS** — baseline `8.420833333 kWh` unchanged; I19 guarantees residency time is not double-counted, so any energy change is attributable ONLY to reduced active power-time |

## Supersession notes

All Stage-1H supersessions of prior-stage statements are recorded in
`STAGE_01H_SUPERSESSION_REGISTER.md` (11 entries) — historical `STAGE_01[A-G]_*` files are NOT
modified.

## Git delta

Modified (5, all un-suffixed normative): `STAGE_01_PROTOCOL_PSEUDOCODE.md`,
`STAGE_01_ROUND_STATE_MACHINE.md`, `STAGE_01_INVARIANT_CATALOGUE.md`, `STAGE_01_TERMINOLOGY.md`,
`STAGE_01_TRACEABILITY_MATRIX.csv`. Added (11): the `STAGE_01H_*` deliverables. No file outside
`docs/thesis_revision_v45/stage_01/` is touched; no `STAGE_01[A-G]_*` file is modified.

## Result

All thirteen acceptance gates pass and all cross-document consistency checks hold. The specification
conforms to H1–H9 while preserving B1–B9, C1–C10, D1–D9, E1–E10, F1–F9, and G1–G11. Name remains
PoCol; no new consensus feature; documentation only; protected drafts byte-identical; Stage-1A–1G
artifacts frozen; A1 baseline unchanged.
