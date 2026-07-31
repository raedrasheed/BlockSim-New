# Stage 1J — Cross-Document Audit (acceptance gates)

The fourteen Stage-1J acceptance gates, verified by procedure-call-graph, event-envelope, and corpus
analysis over `docs/thesis_revision_v45/stage_01/` (not string search alone), plus cross-document
consistency and protected/historical-artifact verification. Name remains **PoCol**; mechanism is **the
idle policy within PoCol**; no property is claimed; the A1 baseline (`8.420833333 kWh`) is unchanged.

| # | Acceptance gate | Result |
|--:|-----------------|--------|
| 1 | `dirty = true` always implies a latest census exists | **PASS** — `ApplyMinerStateTransition` writes `security_census_dirty[t]` and `latest_security_census[t]` TOGETHER atomically (§0.9 step (8)); `FinalizeEventTimeSecurityCensus` ASSERTs `latest[t] exists` before reading (§9). `STAGE_01J_SECURITY_CENSUS_COHERENCE_AUDIT.md`; TV71 |
| 2 | Candidate failure cannot create a false dirty census | **PASS** — `HandlePropagationFailure` sets NO dirty flag (the defensive `SET security_census_dirty[now]` is REMOVED, §16); only later re-activation boundaries update the census via the hook. `STAGE_01J_SECURITY_CENSUS_COHERENCE_AUDIT.md`; TV72 |
| 3 | Exact transition replay is suppressed before old-state validation | **PASS** — §0.9 step (1) replay guard (by `TransitionEventID`) returns `duplicate_suppressed` before step (2)'s `old_state = miner_state` check; no energy/residency charged. `STAGE_01J_TRANSITION_REPLAY_AUDIT.md`; TV73 |
| 4 | Candidate-triggered TransitionEventIDs include CandidateID and PropagationID | **PASS** — §0.9 INPUTS take explicit `candidate_id` + `propagation_id`; the `TransitionEventID` tuple carries both; `EnterLowPowerListen` passes both (no `candidate_ref`). `STAGE_01J_EVENT_ENVELOPE_AUDIT.md`; TV75 |
| 5 | `event_creation_seq` has one explicit owner and initialisation path | **PASS** — §0.8 declares it owned SOLELY by `ScheduleEvent`; §1 `RoundInitialise` sets it to 0 at run start and preserves it across rounds; no ambient seq. `STAGE_01J_EVENT_ENVELOPE_AUDIT.md`; TV79 |
| 6 | Miners parked by ROUND_ACCEPTED/ROUND_ABORTED have an executable new-round assignment path | **PASS** — §2a `PrepareParticipantsForNewRound` binds a fresh `ORIGINAL` PENDING under the new `RoundID`/`TemplateID` via T10 and wakes, before `ASSIGNMENT → HASHING`; no reopen of a CLOSED assignment. `STAGE_01J_NEXT_ROUND_PARTICIPATION_AUDIT.md`; TV76 |
| 7 | Setup/refresh/exhausted states do not generate security breach events | **PASS** — §9 `SecurityFloorEvaluate` checks applicability BEFORE thresholds; non-applicable states record only `security_census_observation`; I16 breaches only in `HASHING`/`SOLUTION_PROPAGATION`/`SECURITY_RECOVERY`. `STAGE_01J_SECURITY_APPLICABILITY_AUDIT.md`; TV77 |
| 8 | SUPERSEDED is used only for renewal | **PASS** — §0.8 status note + catalogue I18b: `SUPERSEDED` only for atomic same-range renewal (`RenewAssignment`); all terminations set `CLOSED`. `STAGE_01J_ASSIGNMENT_TERMINAL_STATUS_AUDIT.md`; TV78 |
| 9 | Revocation/withdrawal lineages close with zero live heads | **PASS** — the adversarial exit sets `status = CLOSED` + `custody_status = revoked` + `revocation_reason` (§8a); `EnterLowPowerListen` revocation sets `CLOSED`; a CLOSED lineage has zero live heads (I18b). `STAGE_01J_ASSIGNMENT_TERMINAL_STATUS_AUDIT.md`; TV78 |
| 10 | Latest census carries its original round/template/state provenance | **PASS** — §0.8 `latest_security_census` is a `census_record(RoundID_at_census, TemplateID_at_census, state_version_at_census, census_seq, …)`; §9 epilogue passes the stored provenance; a stale-context census → `stale_census_observation`. `STAGE_01J_SECURITY_CENSUS_COHERENCE_AUDIT.md`; TV80 |
| 11 | All event scheduling passes through one deterministic scheduler contract | **PASS** — §0.7e `ScheduleEvent` is the sole enqueue interface (rejects finalised times, owns `event_creation_seq`, delta-cycle forward rule, deterministic total-order insert); every `SCHEDULE` is shorthand for it. `STAGE_01J_EVENT_ENVELOPE_AUDIT.md` |
| 12 | TV71 through TV80 pass on paper | **PASS** — `STAGE_01J_SEMANTIC_TEST_VECTORS.md`; every vector names exact procedures + preconditions; no unmodeled external action; A1 preserved |
| 13 | No executable source, configuration, DOCX, or PDF changes | **PASS** — `git diff` confined to `docs/thesis_revision_v45/stage_01/`; draft-42 `2c3afdc5…`, draft-44 `a31400bc…` byte-identical |
| 14 | No Stage-1A..1I historical artifact is modified | **PASS** — `git diff --name-only <base>` shows no `STAGE_01[A-I]_*` file; supersessions recorded in `STAGE_01J_SUPERSESSION_REGISTER.md`, not by rewriting prior evidence |

## Cross-document consistency

| Check | Result |
|-------|--------|
| Name always **PoCol**; mechanism only "the idle policy within PoCol" | **PASS** — every forbidden-name hit is a prohibition clause |
| Single security-census writer + coherence + provenance | **PASS** — `ApplyMinerStateTransition` sole writer (atomic dirty+latest, J1); provenance stored + passed (J8); `HandlePropagationFailure` sets no dirty |
| Single miner-state writer + replay-before-precondition | **PASS** — §0.9 sole `miner_state` writer; replay guard precedes old-state check (J2); full envelope incl both candidate ids (J3) |
| One event-seq owner + central scheduler | **PASS** — `event_creation_seq` owned by `ScheduleEvent` (J4/J9); every `SCHEDULE` routes through it |
| Next-round participation consistent (pseudocode ↔ round-SM) | **PASS** — §2a `PrepareParticipantsForNewRound` runs in ASSIGNMENT before R4 (`ASSIGNMENT → HASHING`); binds to new ids via T3/T4/T10 |
| Floor applicability consistent | **PASS** — §9 records breaches only in HASHING/SOLUTION_PROPAGATION/SECURITY_RECOVERY; observation-only elsewhere (J6) |
| Terminal status consistent (schema ↔ §7 ↔ §8a ↔ I18b ↔ terminology) | **PASS** — SUPERSEDED renewal-only; CLOSED for terminations; zero live heads (J7) |
| Invariant catalogue updated | **PASS** — I18b J7 note (SUPERSEDED renewal-only / CLOSED zero live heads); title `I1..I19` |
| Terminology addendum | **PASS** — Stage-1J addendum covers J1–J9 |
| Traceability updated | **PASS** — R66–R74 (J1–J9) |
| Call graph has no dangling calls | **PASS** — 45 defined; 0 called-but-undefined (`STAGE_01J_PROCEDURE_CALL_GRAPH.md`) |
| A1 discipline | **PASS** — baseline `8.420833333 kWh` unchanged; replay suppression charges no second boundary (I19), so accounting is unaffected |

## Supersession notes

All Stage-1J supersessions of prior-stage statements are recorded in
`STAGE_01J_SUPERSESSION_REGISTER.md` (9 entries) — historical `STAGE_01[A-I]_*` files are NOT modified.

## Git delta

Modified (5, all un-suffixed normative): `STAGE_01_PROTOCOL_PSEUDOCODE.md`,
`STAGE_01_INVARIANT_CATALOGUE.md`, `STAGE_01_TERMINOLOGY.md`, `STAGE_01_TRACEABILITY_MATRIX.csv`. Added
(12): the `STAGE_01J_*` deliverables. No file outside `docs/thesis_revision_v45/stage_01/` is touched; no
`STAGE_01[A-I]_*` file is modified.

## Result

All fourteen acceptance gates pass and all cross-document consistency checks hold. The specification
conforms to J1–J9 while preserving B1–B9, C1–C10, D1–D9, E1–E10, F1–F9, G1–G11, H1–H9, and I-01…I-08.
Name remains PoCol; no new consensus feature; documentation only; protected drafts byte-identical;
Stage-1A–1I artifacts frozen; A1 baseline unchanged.
