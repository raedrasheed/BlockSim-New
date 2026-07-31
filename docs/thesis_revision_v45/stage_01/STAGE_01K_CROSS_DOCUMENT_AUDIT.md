# Stage 1K — Cross-Document Audit (acceptance gates)

The thirteen Stage-1K acceptance gates, verified by procedure-call-graph, event-envelope, and corpus
analysis over `docs/thesis_revision_v45/stage_01/` (not string search alone), plus cross-document
consistency and protected/historical-artifact verification. Name remains **PoCol**; mechanism is **the
idle policy within PoCol**; no property is claimed; the A1 baseline (`8.420833333 kWh`) is unchanged.

| # | Acceptance gate | Result |
|--:|-----------------|--------|
| 1 | VALID_SOLUTION_VERIFIED miners have an executable next-round path | **PASS** — §2a `PrepareParticipantsForNewRound` `CASE LOW_POWER_LISTEN` handles `VALID_SOLUTION_VERIFIED` explicitly (archive → confirm CLOSED → fresh `ORIGINAL` under new ids → T10); no fall-through. `STAGE_01K_NEXT_ROUND_PARTICIPATION_AUDIT.md`; TV81/TV82 |
| 2 | PrepareParticipantsForNewRound performs ASSIGNMENT → HASHING through a named procedure | **PASS** — §2a calls §2b `CompleteAssignmentPhase`, which `TRANSITION round_state -> HASHING` (R4) after asserting the intended set; R4 is no longer prose-only. `STAGE_01K_ASSIGNMENT_PHASE_AUDIT.md`; TV83 |
| 3 | HashWorkEvent cannot be stranded behind ASSIGNMENT | **PASS** — §5 guard: `ASSIGNMENT` is not a hashing-capable state, so a `HashWorkEvent` dispatched while `round_state = ASSIGNMENT` returns `hash_work_noop`; hashing begins only after `CompleteAssignmentPhase`. `STAGE_01K_ASSIGNMENT_PHASE_AUDIT.md`; TV84 |
| 4 | State-residency intervals remain continuous across round boundaries | **PASS** — §1a `FinalizeRoundResidency`/`BeginRoundResidency` close the old-round interval and reopen the same state at the identical `boundary_time` (no transition energy); idle interval counted once (I19 amended). `STAGE_01K_CROSS_ROUND_RESIDENCY_AUDIT.md`; TV85 |
| 5 | All driver-originated state transitions have complete event envelopes | **PASS** — §0.7f `DriverEventEnvelope`; `MinerRegister`/`PrepareParticipantsForNewRound` construct `env` and pass `(event_time, delta_cycle, event_seq)`; §0.9 forbids ambient seq. `STAGE_01K_DRIVER_EVENT_ENVELOPE_AUDIT.md`; TV86 |
| 6 | Rejected transitions are absent from the applied-transition registry | **PASS** — §0.9 adds the `TransitionEventID` to `applied_transition_registry` ONLY inside the atomic apply (step 5); stale/illegal transitions are recorded in `transition_rejection_log`, never the applied registry. `STAGE_01K_TRANSITION_REGISTRY_AUDIT.md`; TV87/TV88 |
| 7 | Lease expiry uses only declared assignment states | **PASS** — §12 `LeaseExpiry` performs no `INVALIDATE`; it CLOSES the CURRENT version canonically via `EnterLowPowerListen` (`CLOSED`/`expired`/`termination_reason = lease_expiry`, a declared field). `STAGE_01K_LEASE_TERMINATION_AUDIT.md`; TV89 |
| 8 | I18a/I18b hold throughout lease termination | **PASS** — one live CURRENT head before the atomic CLOSE, zero after (a CLOSED lineage); accepted prefix preserved, only the accepted unsearched suffix reassigned. `STAGE_01K_LEASE_TERMINATION_AUDIT.md`; TV89 |
| 9 | Security evaluation occurs on entry to HASHING even without a miner-state boundary | **PASS** — §9 `CaptureSecurityCensusOnApplicabilityEntry` writes a coherent dirty+latest on entry to `HASHING` (via `CompleteAssignmentPhase`) even when `H_active = 0` and no wake succeeds; the epilogue decides once. `STAGE_01K_SECURITY_APPLICABILITY_AUDIT.md`; TV90 |
| 10 | ScheduleEvent has a complete current-dispatch context | **PASS** — §0.7e `EventQueueContext` holds the queue/current_*/event_creation_seq/finalised_event_times; `ScheduleEvent` derives `delta_cycle` (no `target_delta_cycle` input); the caller cannot bypass the forward rule. `STAGE_01K_SCHEDULER_CONTEXT_AUDIT.md` |
| 11 | TV81 through TV90 pass on paper | **PASS** — `STAGE_01K_SEMANTIC_TEST_VECTORS.md`; every vector names exact procedures + preconditions; no unmodeled external action; A1 preserved |
| 12 | No executable source, configuration, DOCX, or PDF changes | **PASS** — `git diff` confined to `docs/thesis_revision_v45/stage_01/`; draft-42 `2c3afdc5…`, draft-44 `a31400bc…` byte-identical |
| 13 | No Stage-1A..1J historical artifact is modified | **PASS** — `git diff --name-only <base>` shows no `STAGE_01[A-J]_*` file; supersessions recorded in `STAGE_01K_SUPERSESSION_REGISTER.md`, not by rewriting prior evidence |

## Cross-document consistency

| Check | Result |
|-------|--------|
| Name always **PoCol**; mechanism only "the idle policy within PoCol" | **PASS** — every forbidden-name hit is a prohibition clause |
| Executable round handoff (pseudocode ↔ round-SM) | **PASS** — `PrepareParticipantsForNewRound → CompleteAssignmentPhase` performs R4; hashing gated on `HASHING` |
| Two coherent census writers | **PASS** — `ApplyMinerStateTransition` (J1) and `CaptureSecurityCensusOnApplicabilityEntry` (K7) both write dirty+latest together; coherence invariant holds |
| Register-only-applied transitions | **PASS** — id in `applied_transition_registry` only on atomic apply; rejections in `transition_rejection_log` (K5) |
| Cross-round residency | **PASS** — §1a rebase; I19 amended; `ApplyMinerStateTransition` still sole owner for state changes |
| Canonical terminal status | **PASS** — `SUPERSEDED` renewal-only; lease expiry CLOSED/expired/lease_expiry (K6/J7); I18b zero live heads |
| Scheduler context | **PASS** — single `EventQueueContext`; `ScheduleEvent` derives `delta_cycle`; driver envelopes complete (K8/K4) |
| Invariant catalogue updated | **PASS** — I19 amended for cross-round continuity (K3); Assignment `termination_reason` (K6) |
| Terminology addendum | **PASS** — Stage-1K addendum covers K1–K8 |
| Traceability updated | **PASS** — R75–R82 (K1–K8) |
| Call graph has no dangling calls | **PASS** — 49 defined; 0 called-but-undefined (`STAGE_01K_PROCEDURE_CALL_GRAPH.md`) |
| A1 discipline | **PASS** — baseline `8.420833333 kWh` unchanged; cross-round rebase counts the idle interval once (I19), so accounting is unaffected |

## Supersession notes

All Stage-1K supersessions of prior-stage statements are recorded in
`STAGE_01K_SUPERSESSION_REGISTER.md` (8 entries) — historical `STAGE_01[A-J]_*` files are NOT modified.

## Git delta

Modified (4, all un-suffixed normative): `STAGE_01_PROTOCOL_PSEUDOCODE.md`,
`STAGE_01_INVARIANT_CATALOGUE.md`, `STAGE_01_TERMINOLOGY.md`, `STAGE_01_TRACEABILITY_MATRIX.csv`. Added
(14): the `STAGE_01K_*` deliverables. No file outside `docs/thesis_revision_v45/stage_01/` is touched; no
`STAGE_01[A-J]_*` file is modified.

## Result

All thirteen acceptance gates pass and all cross-document consistency checks hold. The specification
conforms to K1–K8 while preserving B1–B9, C1–C10, D1–D9, E1–E10, F1–F9, G1–G11, H1–H9, I-01…I-08, and
J1–J9. Name remains PoCol; no new consensus feature; documentation only; protected drafts byte-identical;
Stage-1A–1J artifacts frozen; A1 baseline unchanged.
