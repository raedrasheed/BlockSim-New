# Stage 1AH — Cross-Document Audit (26 acceptance gates)

This audit certifies, against the FINAL Stage-1AH normative tree, that the eight topical audits agree, that the five
modified `STAGE_01_*` documents are mutually consistent, and that every acceptance gate holds. It re-evaluates the tree
only after every normative edit (AH1–AH9), every companion-document update, every semantic vector (TV299–TV312), and every
fold-back were complete. The algorithm is **PoCol**; the mechanism is the idle policy within PoCol; the A1 baseline
(`8.420833333 kWh`) is preserved. This supersedes the Stage-1AG cross-document audit's gate marks for the contracts AH
corrects (`STAGE_01AH_SUPERSESSION_REGISTER.md`).

## 1. Topical-audit roll-up

| Topical audit | Correction | Verdict |
|---------------|-----------|---------|
| `STAGE_01AH_DRIVER_SCHEDULING_CONTEXT_AUDIT.md` | AH1 | PASS (after fold-back of a stale `post_epilogue_context` StartWake NOTE) |
| `STAGE_01AH_BOOTSTRAP_TIME_IDEMPOTENCE_AUDIT.md` | AH2 / AH3 | PASS |
| `STAGE_01AH_DRIVER_REQUEST_LIFECYCLE_AUDIT.md` | AH4 | PASS |
| `STAGE_01AH_BOOTSTRAP_CHAIN_RESULT_AUDIT.md` | AH6 / AH5 | PASS |
| `STAGE_01AH_ACCEPTANCE_GENERATION_LIFECYCLE_AUDIT.md` | AH7 | PASS |
| `STAGE_01AH_EVENT_ORDERING_ROOT_AUDIT.md` | AH8 | PASS (after fold-back of a surviving 4-field rule in the round-state companion) |
| `STAGE_01AH_RUNCONTEXT_TERMINAL_PUBLICATION_AUDIT.md` | AH2 / AH9 | PASS (after fold-back of the `CloseRoundAtHorizon` terminal-before-closure reorder) |
| `STAGE_01AH_PROCEDURE_SIGNATURE_CALL_AUDIT.md` | signatures/RETURNS/call sites | PASS |

All eight topical audits report PASS (every item verified against the final tree with exact line anchors). THREE genuine
defects were found by the audits and FOLDED BACK into the final normative tree, after which the affected audits verify
PASS: (a) the StartWake `NOTE` stale `post_epilogue_context` reference → now `scheduling_origin = POST_EPILOGUE(pctx)`;
(b) a surviving positive `(CandidateID, MinerID, AssignmentID, seq)` rule in `STAGE_01_ROUND_STATE_MACHINE.md`'s
"Same-timestamp event order" bullet → now the descriptor-derived `stable_tie_key`; (c) `CloseRoundAtHorizon` transitioned
to `ROUND_ABORTED` AFTER `CloseRoundAssignments` → the transition now precedes closure (matching `RoundAbort` /
`ValidBlockAccept`), so the terminal-round publication owner's terminal ASSERT holds on every path.

## 2. Acceptance gates

| # | Gate | Evidence | Verdict |
|---|------|----------|---------|
| 1 | `SchedulingOrigin` union defined (ORDINARY_DISPATCH/DRIVER/POST_EPILOGUE) + `DriverSchedulingContext` | `DRIVER_SCHEDULING_CONTEXT_AUDIT` (§0.7e); TV299 | PASS |
| 2 | `ScheduleEvent` takes `scheduling_origin` EXPLICITLY; derives delta_cycle from the origin frame, never ambient `EQ.current_*` | `DRIVER_SCHEDULING_CONTEXT_AUDIT`; TV299 | PASS |
| 3 | DRIVER seat derives dc=0, requires target ≥ source, else `rejected_driver_target_before_source` | `DRIVER_SCHEDULING_CONTEXT_AUDIT`; TV300 | PASS |
| 4 | `rejected_invalid_scheduling_origin` added; EVERY `CALL ScheduleEvent` names its origin (no `post_epilogue_context =` residue) | `DRIVER_SCHEDULING_CONTEXT_AUDIT` (18 sites) + `PROCEDURE_SIGNATURE_CALL_AUDIT`; TV299 | PASS |
| 5 | Fixed `round_bootstrap_time` REMOVED; each round targets its own `BootstrapRequest.target_time` (first=run_start_time; rotation=next_representable(prior terminal), strictly later, ≤ T) | `BOOTSTRAP_TIME_IDEMPOTENCE_AUDIT`; TV301 | PASS |
| 6 | ONE named terminal-round publication owner `PublishTerminalRoundAndSeatNext` with the required order (terminal time → publish → new BootstrapRequest → seat → inspect) | `RUNCONTEXT_TERMINAL_PUBLICATION_AUDIT`; TV302 | PASS |
| 7 | Horizon/RUN_HOOK close publishes terminal state but seats no next round; a bootstrap is NEVER seated while the predecessor is nonterminal (all three paths terminal-before-closure) | `RUNCONTEXT_TERMINAL_PUBLICATION_AUDIT` (after fold-back); TV302 | PASS |
| 8 | Stable `BootstrapRequestID` / `DriverRequestID` replay key checked BEFORE any sequence is minted | `BOOTSTRAP_TIME_IDEMPOTENCE_AUDIT`; TV303, TV304 | PASS |
| 9 | A replay returns the existing seat (same EventRef); no second event; no fresh seq minted on replay | `BOOTSTRAP_TIME_IDEMPOTENCE_AUDIT`; TV303, TV304 | PASS |
| 10 | Sim-driver requests are explicit `driver_request` records (5-status) with a named producer `AdmitDriverRequest`; each seat result inspected + terminalised | `DRIVER_REQUEST_LIFECYCLE_AUDIT`; TV306 | PASS |
| 11 | The event loop admits + seats pending driver requests BEFORE selecting the next earliest event_time (Option A); structural proof present | `DRIVER_REQUEST_LIFECYCLE_AUDIT`; TV305 | PASS |
| 12 | First-round admission not skipped — genesis registry imported (Option A) + initial-registration barrier | `BOOTSTRAP_CHAIN_RESULT_AUDIT`; TV307 | PASS |
| 13 | `PrepareParticipantsForNewRound` never runs before the declared initial miner set is complete (barrier gate) | `BOOTSTRAP_CHAIN_RESULT_AUDIT`; TV307 | PASS |
| 14 | Every bootstrap-chain seat result inspected → declared disposition; no caller returns success after a required successor failed to seat | `BOOTSTRAP_CHAIN_RESULT_AUDIT`; TV308 | PASS |
| 15 | A failed first bootstrap takes a declared no-round run path; no null RoundContext dereferenced | `BOOTSTRAP_CHAIN_RESULT_AUDIT`; TV309 | PASS |
| 16 | `acceptance_batch_registry` generation-keyed `(ts, point, batch_generation)` in the core model; one finalize per that triple | `ACCEPTANCE_GENERATION_LIFECYCLE_AUDIT`; TV310 | PASS |
| 17 | `ACCEPTANCE_BATCH_UNFINALISABLE` + single candidate-failure owner (FAILED AND removed from `active_propagation_set`) on a finalize-seat failure | `ACCEPTANCE_GENERATION_LIFECYCLE_AUDIT`; TV310 | PASS |
| 18 | Closure paths cancel `acceptance_batch_finalize_seat[key].EventRef` (never the whole record) | `ACCEPTANCE_GENERATION_LIFECYCLE_AUDIT`; TV311 | PASS |
| 19 | The ONLY authoritative queue tie key is `descriptor(event_type).stable_tie_key(immutable_payload)`; every surviving positive generic tuple removed | `EVENT_ORDERING_ROOT_AUDIT` (after fold-back); TV312 | PASS |
| 20 | Acceptance VALUE selection (`candidate_hash` then `MinerID`) kept DISTINCT as winner arbitration, not a queue key | `EVENT_ORDERING_ROOT_AUDIT`; TV312 | PASS |
| 21 | `EventRef` / `dispatch_envelope` / `immutable_payload` / `queued_event_record` / `stable_tie_key` distinct; domain identity fields are payload, NOT dispatch_envelope fields | `RUNCONTEXT_TERMINAL_PUBLICATION_AUDIT` (§0.2) | PASS |
| 22 | Every driver/bootstrap field DECLARED in `STRUCTURE RunContext`; the stale "ProcessEventTime obtains RunContext through RoundContext.RunContext" note REMOVED | `RUNCONTEXT_TERMINAL_PUBLICATION_AUDIT` | PASS |
| 23 | TV299–TV312 pass on paper (14 vectors; each names only defined procedures/results) | `STAGE_01AH_SEMANTIC_TEST_VECTORS.md` | PASS |
| 24 | All 8 Stage-1AH topical audits describe the FINAL tree; call graph closes 0 dangling over 108 callables | §1 + `STAGE_01AH_PROCEDURE_CALL_GRAPH.md` + `PROCEDURE_SIGNATURE_CALL_AUDIT` | PASS |
| 25 | No executable source/config/DOCX/PDF change; no Stage-1A…1AG artifact modified; protected drafts byte-identical; no forbidden identifier; A1 present; PoCol naming | §3 below | PASS |
| 26 | AH10 supersession recorded (`STAGE_01AH_SUPERSESSION_REGISTER.md`); Stage 2 not begun | §3 below | PASS |

## 3. Scope & integrity verification

- **Protected drafts byte-identical** (unchanged):
  - `docs/Raed-Rasheed-draft-42-00.docx` = `2c3afdc5739109d0ea12ada96c3115d626a2188c1acbaeaa4b6020974884cbda`
  - `docs/Raed-Rasheed-draft-42-00.pdf` = `131412bb2ce17ed97b98dfbefc136c7b5b226b9fd7372e79a25e4b0dc057e9c4`
  - `docs/Raed-Rasheed-draft-44-00.docx` = `a31400bce212585df8197ee3d63e4eb887b5f5d0f2f8a65b916b2489dbc12340`
- **No forbidden identifier.** A scan for model/vendor identifiers across every modified `STAGE_01_*` document and every
  `STAGE_01AH_*` deliverable returns no match.
- **A1 baseline** `8.420833333 kWh` present and unchanged (energy model spec, unmodified); **PoCol** naming and "the idle
  policy within PoCol" mechanism unchanged.
- **Call graph** closes with 0 dangling references over 108 defined callables (`STAGE_01AH_PROCEDURE_CALL_GRAPH.md`).
- **Delta confined** to the five modified normative documents (`STAGE_01_PROTOCOL_PSEUDOCODE.md`,
  `STAGE_01_ROUND_STATE_MACHINE.md`, `STAGE_01_INVARIANT_CATALOGUE.md`, `STAGE_01_TERMINOLOGY.md`,
  `STAGE_01_TRACEABILITY_MATRIX.csv`) and the fourteen new `STAGE_01AH_*` deliverables. No executable source,
  configuration, DOCX, or PDF was modified; no Stage-1A…1AG lettered artifact was modified; no experiment was run; Stage 2
  is not begun.

## 4. Overall verdict

**PASS — all 26 acceptance gates hold against the final Stage-1AH normative tree.** The driver-scheduling,
round-rotation, and acceptance-lifecycle contract (AH1–AH9) is realised faithfully; all eight topical audits PASS (three
after a folded-back single-line correction); the call graph closes with 0 dangling references over 108 callables; the
companion documents are mutually consistent; the protected drafts are byte-identical; and the A1 baseline and PoCol naming
are preserved.
