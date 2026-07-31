# Stage 1G — Cross-Document Audit (acceptance gates)

The sixteen Stage-1G acceptance gates, verified by procedure-call-graph, event-envelope, and corpus
analysis over `docs/thesis_revision_v45/stage_01/` (not string search alone), plus cross-document
consistency and protected/historical-artifact verification.

| # | Acceptance gate | Result |
|--:|-----------------|--------|
| 1 | I2 uses discovery-time assignment eligibility | **PASS** — `ValidateCandidate` validates the signed certificate against the immutable discovery `snapshot` (was VALID+CURRENT at `discovery_time`, not revoked before it, nonce in range, RoundID/TemplateID/target/sig), never CURRENT-at-acceptance; I2 rewritten in the catalogue, miner-SM, round-SM, terminology (G1). `STAGE_01G_ACCEPTANCE_PREDICATE_AUDIT.md`; TV39 |
| 2 | I18 no longer requires CURRENT during PENDING/PAUSED/CLOSED | **PASS** — I18 replaced by I18a (`count(CURRENT) <= 1`, zero legal) and I18b (one live head in `{PENDING, CURRENT, PAUSED}` per open lineage; zero after closure) (G2). `STAGE_01G_LINEAGE_INVARIANT_AUDIT.md`; TV40 |
| 3 | `ActiveHashRateUpdate` cannot alter participation outside the state hook | **PASS** — it is compute-only (no sampling, no census mutation); each adversarial entry/exit is an `AdversarialParticipationChangeEvent` routed through `ApplyMinerStateTransition` (G3). `STAGE_01G_STATE_HOOK_AUDIT.md`; TV41 |
| 4 | PAUSED resume failure preserves accepted coverage | **PASS** — `WakeCompleteEvent` PAUSED branch preserves all three frontiers, reassigns only the accepted unsearched suffix, uses `resume_wake_failed` (not the PENDING-only rule), clears candidate pause fields (G4). `STAGE_01G_HASH_EVENT_AUDIT.md`; TV42 |
| 5 | All same-time block arrivals are collected before arbitration | **PASS** — `BlockAcceptancePoint` register-only (microphase 3); `AcceptanceBatchFinalize` runs once per (timestamp, acceptance point) in microphase 4 (G5). `STAGE_01G_EVENT_MICROPHASE_SPEC.md`; TV43 |
| 6 | Acceptance closure is causally downstream of arbitration | **PASS** — round closure is the atomic result of `AcceptanceBatchFinalize → ValidBlockAccept`; no block-arrival closes directly; `block_accepted` guard ⇒ single closure (G5). TV43 |
| 7 | Discovery-vs-lease ordering identical in every document | **PASS** — "solution discovery is processed first and captures its discovery snapshot before same-time lease expiry/renewal" stated in pseudocode §0.7/§21, `STAGE_01G_EVENT_MICROPHASE_SPEC.md`, and (historically) preserved; single canonical rule (G5) |
| 8 | DISCOVERED is reachable | **PASS** — `CreatePropagationContext` sets `status = DISCOVERED`; `ScheduleSolutionPropagation` advances `SELF_VALIDATED → PROPAGATING`; `BlockAcceptancePoint` sets `PENDING_ACCEPTANCE` (G6). `active_propagation_set = {PROPAGATING, PENDING_ACCEPTANCE}` |
| 9 | IDs and scheduling iteration are deterministic | **PASS** — `CandidateID=(RoundID, seq)`, `PropagationID=(CandidateID, seq)`; every create/cancel/schedule loop sorts by intrinsic keys; `seq` after ordering; iteration-order-independent (G7). `STAGE_01G_DETERMINISM_AUDIT.md`; TV45 |
| 10 | SECURITY_RECOVERY coexists consistently with live candidates | **PASS** — the round-state and `active_propagation_set` are not identified; `ValidBlockAccept` allows `{SOLUTION_PROPAGATION, SECURITY_RECOVERY}`; round-SM §2.5/R6/R13 (G8). `STAGE_01G_CANDIDATE_CLEANUP_AUDIT.md`; TV46 |
| 11 | Hashing is event-scheduled and non-blocking | **PASS** — `StartHashing`/`HashWorkEvent`/`ScheduleNextHashWork`; the blocking `ActiveHashing` loop is removed; pending units self-cancel (G9). `STAGE_01G_HASH_EVENT_AUDIT.md`; TV48 |
| 12 | Terminal rounds cannot transition back to SECURITY_RECOVERY | **PASS** — `SecurityFloorEvaluate` is scheduled and carries `(RoundID, TemplateID, state_version)`; returns `stale_noop` for a terminal/stale round (G10). TV44 |
| 13 | Every candidate resume carries CandidateID and PropagationID | **PASS** — `HandlePropagationFailure` matches paused miners on BOTH ids and schedules `ResumeFromPause(…, CandidateID, PropagationID)`; `ResumeFromPause` verifies both (G11). TV49 |
| 14 | TV39–TV50 pass on paper | **PASS** — `STAGE_01G_SEMANTIC_TEST_VECTORS.md`; every vector names exact procedures + preconditions; no unmodeled external action |
| 15 | No executable source, configuration, DOCX, or PDF changes | **PASS** — `git diff` confined to `docs/thesis_revision_v45/stage_01/`; draft-42 `2c3afdc5…`, draft-44 `a31400bc…` byte-identical |
| 16 | No Stage-1A–1F historical artifact is modified | **PASS** — `git diff --name-only <base>` shows no `STAGE_01[A-F]_*` file; supersessions recorded below, not by rewriting prior evidence |

## Cross-document consistency

| Check | Result |
|-------|--------|
| Name always **PoCol**; mechanism only "the idle policy within PoCol" | **PASS** — every forbidden-name hit is a prohibition clause |
| Single miner-state writer | **PASS** — 0 `TRANSITION miner_state` in procedures; `ApplyMinerStateTransition` sole writer |
| No blocking hash loop / no synchronous wake | **PASS** — no `ActiveHashing` WHILE / no `step_budget` / no synchronous `WakeComplete`; `HashWorkEvent`/`StartWake` only |
| Acceptance cluster consistent | **PASS** — `BlockAcceptancePoint` register-only → `AcceptanceBatchFinalize` (single per timestamp) → `ValidBlockAccept` (single closure, allows SECURITY_RECOVERY) |
| Call graph has no dangling calls | **PASS** — 41 defined; 0 called-but-undefined (`STAGE_01G_PROCEDURE_CALL_GRAPH.md`) |
| Invariant catalogue updated | **PASS** — I2 discovery-time; I18a/I18b; title/summary reflect both |
| Terminology addendum | **PASS** — discovery-time eligibility, lineage heads, candidate lifecycle, microphases, hook/hashing/census |
| Round-SM ↔ pseudocode agreement | **PASS** — §2.5 recovery coexistence, R6 (accept from SP/SR), R13 (return to SP if candidates remain) match `ValidBlockAccept`/`propagation_quiescent` |
| Traceability updated | **PASS** — R39–R48 (R38 amended) |
| Sampling summary complete | **PASS** — adversarial draw relocated to `AdversarialParticipationChangeEvent` scheduling; hash draw in `HashWorkEvent`; wake draw in `StartWake`; no new site |

## Supersession notes (recorded here; historical files NOT modified — F9-lock)

| Historical statement | Superseded by (Stage 1G) | Nature |
|----------------------|--------------------------|--------|
| Stage-1F I18 "exactly one CURRENT per lineage at every instant" (`STAGE_01F_*` audits/vectors) | I18a/I18b in `STAGE_01_INVARIANT_CATALOGUE.md` | correction; historical Stage-1F files remain frozen |
| Stage-1F flat event-priority table (`STAGE_01F_EVENT_PRIORITY_TABLE.md`) | `STAGE_01G_EVENT_MICROPHASE_SPEC.md` (§0.7 microphases) | superseding model; the F table remains a frozen artifact |
| Stage-1F `ActiveHashing` blocking loop / `AcceptanceTimestampBatch` | `HashWorkEvent` chain (G9) / `AcceptanceBatchFinalize` (G5) | replacement in the normative pseudocode; Stage-1F call graph/vectors remain frozen |
| Stage-1F I2 "signer's valid current assignment" phrasing in `STAGE_01F_*` | I2 discovery-time eligibility (G1) | correction; historical Stage-1F files remain frozen |

## Git delta

Modified (6, all un-suffixed normative): `STAGE_01_PROTOCOL_PSEUDOCODE.md`,
`STAGE_01_MINER_STATE_MACHINE.md`, `STAGE_01_ROUND_STATE_MACHINE.md`,
`STAGE_01_INVARIANT_CATALOGUE.md`, `STAGE_01_TERMINOLOGY.md`, `STAGE_01_TRACEABILITY_MATRIX.csv`.
Added (12): the `STAGE_01G_*` deliverables. No file outside `docs/thesis_revision_v45/stage_01/` is
touched; no `STAGE_01[A-F]_*` file is modified.

## Result

All sixteen acceptance gates pass and all cross-document consistency checks hold. The specification
conforms to G1–G11 while preserving B1–B9, C1–C10, D1–D9, E1–E10, and F1–F9. Name remains PoCol; no
new consensus feature; documentation only; protected drafts byte-identical; Stage-1A–1F artifacts
frozen.
