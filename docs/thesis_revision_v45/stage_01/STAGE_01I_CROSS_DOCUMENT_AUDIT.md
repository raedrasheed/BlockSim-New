# Stage 1I — Cross-Document Audit (acceptance gates)

The fourteen Stage-1I acceptance gates, verified by procedure-call-graph, event-envelope, and corpus
analysis over `docs/thesis_revision_v45/stage_01/` (not string search alone), plus cross-document
consistency and protected/historical-artifact verification. Name remains **PoCol**; mechanism is **the
idle policy within PoCol**; no property is claimed; the A1 baseline (`8.420833333 kWh`) is unchanged.

| # | Acceptance gate | Result |
|--:|-----------------|--------|
| 1 | No security dirty flag can be stranded between delta-cycles | **PASS** — `security_census_dirty` and `latest_security_census` are keyed by `event_time` ALONE (§0.8); `ApplyMinerStateTransition` sets/overwrites them regardless of `delta_cycle` (§0.9 step (7)). `STAGE_01I_EVENT_TIME_EPILOGUE_SPEC.md`; TV61 |
| 2 | Exactly one floor decision uses the final quiescent census per event_time | **PASS** — `FinalizeEventTimeSecurityCensus(event_time)` reads `latest_security_census[event_time]` (newest wins) and calls `SecurityFloorEvaluate` once; `ProcessEventTime` runs it after quiescence (§0.7d/§9). TV62 |
| 3 | Explicit event-loop epilogue guarantees finalisation even when no later event exists | **PASS** — `ProcessEventTime` invokes the epilogue STRUCTURALLY after draining `t`, not as a queued event; §0.7d + §21 remove the security decision from the same-timestamp queue. `STAGE_01I_EVENT_TIME_EPILOGUE_SPEC.md`; TV63 |
| 4 | Idempotence is keyed by TransitionEventID, not only state and timestamp | **PASS** — §0.9 step (0) builds `TransitionEventID = (event_time, delta_cycle, seq, MinerID, old_state, new_state, reason, AssignmentID, assignment_version, CandidateID?, PropagationID?)` and checks `transition_event_registry`; recorded in `transition_audit`. `STAGE_01I_TRANSITION_IDENTITY_AUDIT.md`; TV65 |
| 5 | Legitimate repeated edges in different delta-cycles are not suppressed | **PASS** — only an exact-id replay is suppressed; a same-edge occurrence in another `delta_cycle` has a distinct id (different `delta_cycle`/`seq`) and applies. `STAGE_01I_TRANSITION_IDENTITY_AUDIT.md`; TV64 |
| 6 | Every runtime registry is explicitly initialised | **PASS** — `RoundInitialise` initialises and RETURNS all per-round and per-run registries; per-run bookkeeping preserved across rounds; none an implicit global (§0.8/§1). `STAGE_01I_RUNTIME_INITIALISATION_AUDIT.md`; TV66 |
| 7 | Terminal rounds return before breach recording or recovery | **PASS** — `SecurityFloorEvaluate` begins `IF round_state in {ROUND_ACCEPTED, ROUND_ABORTED}: RETURN terminal_stale_noop` before any breach/recovery logic (§9/§0.7c). `STAGE_01I_TERMINAL_SECURITY_AUDIT.md`; TV67 |
| 8 | Persistent recovery does not perform a self-transition | **PASS** — a continuing breach in `SECURITY_RECOVERY` records `breach_persists`, keeps the state, performs NO `SECURITY_RECOVERY → SECURITY_RECOVERY`, and does NOT bump `state_version` (§9). `STAGE_01I_TERMINAL_SECURITY_AUDIT.md`; TV67 |
| 9 | ROUND_ACCEPTED/ROUND_ABORTED idle miners cannot receive assignments in the closed round | **PASS** — §8a `CASE LOW_POWER_LISTEN`/`CASE ROUND_ACCEPTED OR ROUND_ABORTED` returns `deferred_round_terminal`; no `CreatePendingAssignment`/`StartWake` in the closed `RoundContext`. `STAGE_01I_LOW_POWER_REENTRY_AUDIT.md`; TV68 |
| 10 | Custody values conform to the canonical enum | **PASS** — §0.8 Assignment declares the closed enum + `revocation_reason`; §8a sets `custody_status = revoked` + `revocation_reason = adversarial_withdrawal`; I8b restates the closed enum; `revoked_adversarial_exit` appears only in prohibition comments. `STAGE_01I_CUSTODY_ENUM_AUDIT.md`; TV69 |
| 11 | Current normative files reference I1..I19 consistently | **PASS** — all un-suffixed normative files reference `I1..I19` (incl. `I18a`/`I18b`); no residual `I1..I17`-only range text; genuine single-invariant `I17` references unchanged (I-08). TV70 |
| 12 | TV61 through TV70 pass on paper | **PASS** — `STAGE_01I_SEMANTIC_TEST_VECTORS.md`; every vector names exact procedures + preconditions; no unmodeled external action; A1 preserved |
| 13 | No executable source, configuration, DOCX, or PDF changes | **PASS** — `git diff` confined to `docs/thesis_revision_v45/stage_01/`; draft-42 `2c3afdc5…`, draft-44 `a31400bc…` byte-identical |
| 14 | No Stage-1A..1H historical artifact is modified | **PASS** — `git diff --name-only <base>` shows no `STAGE_01[A-H]_*` file; supersessions recorded in `STAGE_01I_SUPERSESSION_REGISTER.md`, not by rewriting prior evidence |

## Cross-document consistency

| Check | Result |
|-------|--------|
| Name always **PoCol**; mechanism only "the idle policy within PoCol" | **PASS** — every forbidden-name hit is a prohibition clause |
| Single security-decision path | **PASS** — `ProcessEventTime → FinalizeEventTimeSecurityCensus → SecurityFloorEvaluate`; the hook and `HandlePropagationFailure` only set `security_census_dirty` (I-01) |
| Single miner-state writer / residency owner / idempotence | **PASS** — `ApplyMinerStateTransition` sole writer + `residency_ledger` owner + `TransitionEventID` gate |
| Event-time epilogue consistent (pseudocode ↔ §21 ↔ terminology) | **PASS** — §0.7/§0.7d, §21 (security decision removed from the queue), and the Stage-1I terminology addendum agree |
| Registry initialisation consistent | **PASS** — §0.8 scope comments and §1 `RoundInitialise` list the same per-round/per-run registries |
| Terminal/recovery security consistent (pseudocode ↔ round-SM) | **PASS** — §9 `SecurityFloorEvaluate` and round-SM §2.5/R8/R10/R13 agree; only `HASHING`/`SOLUTION_PROPAGATION` → `SECURITY_RECOVERY` |
| Custody enum consistent (schema ↔ §8a ↔ I8b ↔ terminology ↔ TV69) | **PASS** — canonical closed enum + `revocation_reason` everywhere; no invented value |
| Invariant catalogue updated | **PASS** — I8b canonical custody enum + `revocation_reason`; catalogue title `I1..I19` |
| Traceability updated | **PASS** — R58–R65 (I-01…I-08) |
| Call graph has no dangling calls | **PASS** — 43 defined; 0 called-but-undefined (`STAGE_01I_PROCEDURE_CALL_GRAPH.md`) |
| A1 discipline | **PASS** — baseline `8.420833333 kWh` unchanged; TransitionEventID idempotence charges no second boundary (I19 preserved), so accounting is unaffected |

## Supersession notes

All Stage-1I supersessions of prior-stage statements are recorded in
`STAGE_01I_SUPERSESSION_REGISTER.md` (8 entries) — historical `STAGE_01[A-H]_*` files are NOT modified.

## Git delta

Modified (9, all un-suffixed normative): `STAGE_01_PROTOCOL_PSEUDOCODE.md`,
`STAGE_01_INVARIANT_CATALOGUE.md`, `STAGE_01_TERMINOLOGY.md`, `STAGE_01_TRACEABILITY_MATRIX.csv`,
`STAGE_01_COMPLETION_REPORT.md`, `STAGE_01_OPEN_QUESTIONS.md`, `STAGE_01_THREAT_MODEL.md`,
`STAGE_01_FAILURE_AND_ADVERSARIAL_PATHS.md`, `STAGE_01_PROTOCOL_SCOPE.md`. Added (12): the `STAGE_01I_*`
deliverables. No file outside `docs/thesis_revision_v45/stage_01/` is touched; no `STAGE_01[A-H]_*` file
is modified.

## Result

All fourteen acceptance gates pass and all cross-document consistency checks hold. The specification
conforms to I-01…I-08 while preserving B1–B9, C1–C10, D1–D9, E1–E10, F1–F9, G1–G11, and H1–H9. Name
remains PoCol; no new consensus feature; documentation only; protected drafts byte-identical;
Stage-1A–1H artifacts frozen; A1 baseline unchanged.
