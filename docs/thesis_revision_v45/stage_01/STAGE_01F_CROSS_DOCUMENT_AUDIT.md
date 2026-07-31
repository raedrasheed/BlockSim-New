# Stage 1F — Cross-Document Audit (acceptance gates)

The fourteen Stage-1F acceptance gates, verified by procedure-call-graph, event-envelope, and corpus
analysis over `docs/thesis_revision_v45/stage_01/` (not string search alone), plus cross-document
consistency.

| # | Acceptance gate | Result |
|--:|-----------------|--------|
| 1 | Every candidate has a unique propagation context | **PASS** — `CreatePropagationContext` mints immutable unique `CandidateID`/`PropagationID`; each discovery adds its own CPC to `active_propagation_set` (F1). See `STAGE_01F_CANDIDATE_LIFECYCLE_SPEC.md`; TV28–TV30 |
| 2 | Failure handling is candidate-scoped | **PASS** — `HandlePropagationFailure(CandidateID)` fails only that context, removes only it from the set, cancels only its events, resumes only matching-pause-cause miners (F2). `STAGE_01F_CONCURRENCY_AUDIT.md` #3; TV28 |
| 3 | One candidate's failure cannot cancel/resume another candidate's state | **PASS** — the handler iterates only `pause_cause_candidate_id = CandidateID` miners and only `certificate_arrival_events(cpc)`/`block_arrival_event(cpc)` (F2); TV28/TV29 |
| 4 | SOLUTION_PROPAGATION remains active while any live candidate exists | **PASS** — round `= SOLUTION_PROPAGATION` iff `active_propagation_set` non-empty; return to HASHING only when `propagation_quiescent` (F3, §0.6); TV28/TV38 |
| 5 | Reserve assignment provenance distinguishes original and reassigned ranges | **PASS** — `ReserveActivate` selects ORIGINAL vs REASSIGNED; `CreatePendingAssignment` sets custody + I9 provenance accordingly (F4); TV31/TV32 |
| 6 | All wake completion is event-scheduled and non-blocking | **PASS** — `StartWake ⇒ WakeCompleteEvent`; zero synchronous `CALL WakeComplete(`; five callers use `StartWake` (F5). `STAGE_01F_WAKE_EVENT_AUDIT.md`; TV33 |
| 7 | Every miner transition uses one accounting/security hook | **PASS** — 0 `TRANSITION miner_state` in procedures; 12 `CALL ApplyMinerStateTransition` sites; it is the sole writer (F6). `STAGE_01F_STATE_TRANSITION_HOOK.md` |
| 8 | I17 is updated at every ACTIVE_HASHING boundary | **PASS** — `ApplyMinerStateTransition` recomputes `H_active=H_honest+H_adversarial` and sets `q_adv`/NA on every call; I17 catalogue note added (F6/I17); TV34 |
| 9 | Renewal creates immutable atomic assignment versions | **PASS** — `RenewAssignment` atomically supersedes old and publishes new CURRENT; no in-place identity mutation (F7). `STAGE_01F_ASSIGNMENT_VERSION_AUDIT.md`; TV35 |
| 10 | Exactly one CURRENT assignment version exists per lineage | **PASS** — invariant **I18** enforced by the atomic swap in `RenewAssignment` (asserted post-swap); TV35 |
| 11 | All same-timestamp event races have deterministic priorities | **PASS** — 14-rank inter-type table + `(CandidateID, MinerID, AssignmentID, seq)` tie-break; six required races resolved; iteration-order-independent (F8). `STAGE_01F_EVENT_PRIORITY_TABLE.md`; TV36/TV37/TV38 |
| 12 | Historical Stage-1A–1E artifacts are not modified | **PASS** — `git diff --name-only <base>` shows no `STAGE_01[A-E]_*` file; supersessions recorded in `STAGE_01F_HISTORICAL_ARTIFACT_REGISTER.md` (F9) |
| 13 | TV28–TV38 pass on paper | **PASS** — `STAGE_01F_SEMANTIC_TEST_VECTORS.md`; every vector names exact procedures + preconditions; no unmodeled external action |
| 14 | No executable source, configuration, DOCX, or PDF changes | **PASS** — `git diff` confined to `docs/thesis_revision_v45/stage_01/`; draft-42 `2c3afdc5…`, draft-44 `a31400bc…` byte-identical |

## Cross-document consistency

| Check | Result |
|-------|--------|
| Name is always **PoCol**; mechanism only "the idle policy within PoCol" | **PASS** — every forbidden-name occurrence is inside a prohibition clause; none used as a name |
| Single miner-state writer | **PASS** — `ApplyMinerStateTransition` is the only writer; no `TRANSITION miner_state` remains in any procedure |
| Single wake construct | **PASS** — `StartWake`/`WakeCompleteEvent`; no synchronous wake |
| Candidate ids thread through every propagation event | **PASS** — `CertificateArrival`, `BlockAcceptancePoint`, `ResumeFromPause`, cancellations carry `CandidateID`/`PropagationID` |
| Call graph has no dangling calls | **PASS** — 38 defined; 0 called-but-undefined (`STAGE_01F_PROCEDURE_CALL_GRAPH.md`) |
| Legal-transition edges only | **PASS** — the F6 legality precondition holds at all 12 sites; the illegal `WAKING→LOW_POWER_LISTEN` closure edge is corrected to `WAKING→OFFLINE` (T12) |
| Miner-SM ↔ pseudocode agreement | **PASS** — §1.7 conventions + T5/T12 notes match `StartWake`/`WakeCompleteEvent`/hook |
| Round-SM ↔ pseudocode agreement | **PASS** — §2.6 active-set rule and R6–R8 match `active_propagation_set`/`propagation_quiescent`/`ValidBlockAccept` |
| Invariant catalogue updated | **PASS** — I17 boundary note; new I18; title/summary I1..I18 |
| Traceability updated | **PASS** — rows R32–R38 |
| Sampling summary complete | **PASS** — the sole wake draw is now `StartWake`; no new sampling site; F-procedures deterministic |

## Git delta

Modified (5, all un-suffixed normative): `STAGE_01_PROTOCOL_PSEUDOCODE.md`,
`STAGE_01_MINER_STATE_MACHINE.md`, `STAGE_01_ROUND_STATE_MACHINE.md`,
`STAGE_01_INVARIANT_CATALOGUE.md`, `STAGE_01_TRACEABILITY_MATRIX.csv`.
Added (12): the `STAGE_01F_*` deliverables. No file outside `docs/thesis_revision_v45/stage_01/` is
touched; no `STAGE_01[A-E]_*` file is modified.

## Result

All fourteen acceptance gates pass and all cross-document consistency checks hold. The specification
conforms to F1–F9 while preserving B1–B9, C1–C10, D1–D9, and E1–E10. Name remains PoCol; no new
consensus feature; documentation only; protected drafts byte-identical; historical artifacts frozen.
