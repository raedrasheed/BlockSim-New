# Stage 1E — Cross-Document Audit (acceptance gates)

The eleven Stage-1E acceptance gates, verified by procedure-call-graph analysis and corpus checks
over `docs/thesis_revision_v45/stage_01/` (not string search alone), plus cross-document consistency.

| # | Acceptance gate | Result |
|--:|-----------------|--------|
| 1 | A paused assignment does not invalidate its already-discovered solution | **PASS** — `ValidateCandidate` validates against the immutable discovery `snapshot`, not the finder's later PAUSED assignment (E1); `CreateSolutionEligibilitySnapshot` + `EarlyStopGenerate` bind it. See `STAGE_01E_ASSIGNMENT_VALIDITY_AUDIT.md` S1–S4; TV18/TV19 |
| 2 | Self-validation uses an authenticated object | **PASS** — `SelfValidateFoundSolution(certificate, snapshot) → ValidateCandidate` checks the certificate signature; the unsigned `candidate_solution` cannot satisfy it (E2); TV20 |
| 3 | Every failed acceptance path resumes paused miners | **PASS** — `BlockAcceptancePoint` (non-accept) and `AcceptanceTimestampBatch` (empty valid set) both `→ HandlePropagationFailure ⇒ ResumeFromPause` for each PATH-B paused miner (E3). See `STAGE_01E_PROPAGATION_FAILURE_AUDIT.md` P1–P5; TV21 |
| 4 | `ReserveActivate` creates a real PENDING assignment | **PASS** — creates + ledgers PENDING, binds, RESERVE→WAKING, `WakeComplete`; PENDING→CURRENT only on success; wake failure records none (E4); TV22 |
| 5 | No changed-range T6 shortcut remains | **PASS** — T6 retired in `STAGE_01_MINER_STATE_MACHINE.md` (table row, §2.3, §3.1 prohibited, §3.2); `STAGE_01B_STATE_PATH_AUDIT.md` T6 row marked removed; a different range is acquired only through `WAKING` (E5); TV23 |
| 6 | `SOLUTION_PROPAGATION` is entered at propagation start | **PASS** — `ScheduleSolutionPropagation` performs `HASHING → SOLUTION_PROPAGATION` at the first found solution; `ActiveHashing` runs in `{HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY}`; `ValidBlockAccept` does a single `SOLUTION_PROPAGATION → ROUND_ACCEPTED` (E6); round-SM §2.6; TV24 |
| 7 | Every closure state has a deterministic action | **PASS** — `CloseRoundAssignments` has an explicit action for all eight holder states; `entry_stop_reason` ≠ `round_closure_disposition`; no "update state consistently" (E7). See `STAGE_01E_ROUND_CLOSURE_TABLE.md`; TV25 |
| 8 | `TemplateRefresh` uses only legal miner transitions | **PASS** — `CloseTemplateAssignments` routes old holders via T27/T8/T12; re-activation uses T3/T4/T10; OFFLINE/DISQUALIFIED excluded (E8). See `STAGE_01E_TEMPLATE_REFRESH_AUDIT.md`; TV26 |
| 9 | `ASSIGNMENT` reaches `HASHING` explicitly | **PASS** — `TemplateRefresh` ends with `ASSERT round_state = ASSIGNMENT` then `TRANSITION → HASHING` (R4) (E8); TV26 |
| 10 | Lease renewal preserves a valid CURRENT assignment | **PASS** — `LeaseExpiry` decides renewal BEFORE invalidating; renewal keeps range/holder/CURRENT, retains progress + provenance, no WAKING; expiry-without-renewal reassigns only the accepted unsearched suffix (E9); TV27 |
| 11 | No executable source, configuration, DOCX, or PDF changes | **PASS** — `git diff` vs base is confined to `docs/thesis_revision_v45/stage_01/`; draft-42 `2c3afdc5…`, draft-44 `a31400bc…` byte-identical (see manifest) |

## Cross-document consistency

| Check | Result |
|-------|--------|
| Algorithm name is always **PoCol**; mechanism only "the idle policy within PoCol" | **PASS** — every `PoCol-E`/`Energy-Aware PoCol`/`Enhanced PoCol` occurrence is inside a prohibition clause; none used as a name |
| No dangling `T6` reference implies it is still legal | **PASS** — all `T6` mentions in miner SM and `STAGE_01B_STATE_PATH_AUDIT.md` describe it as removed/retired |
| Snapshot/certificate parameter threading is consistent | **PASS** — every `ValidateCandidate` call passes `(certificate, snapshot)`; every `EarlyStopVerify` call passes `(certificate, snapshot, verifying_MinerID)`; `BlockAcceptancePoint`/`CertificateArrival` carry `snapshot`; no `winner_solution`/`candidate_solution` leaks into the acceptance cluster |
| `entry_stop_reason` naming unified | **PASS** — the per-miner field is `entry_stop_reason` in `ExhaustionAdjudicate`, `EnterLowPowerListen`, `ResumeFromPause`, `HandlePropagationFailure`, `CloseRoundAssignments`; the input parameter name `stop_reason` is unchanged where it is a parameter |
| Round-SM ↔ pseudocode transitions agree | **PASS** — R5 (HASHING→SOLUTION_PROPAGATION), R6 (→ROUND_ACCEPTED single step), R7/R8 (→HASHING/SECURITY_RECOVERY), R4 (ASSIGNMENT→HASHING), R17/R18 (refresh via TEMPLATE_COMMITMENT) match the pseudocode |
| Miner-SM legality of every transition emitted by pseudocode | **PASS** — activation T3/T4/T9/T10→T5; PATH A T7→T8; PATH B T26; revocation T27; closure T28/T29; resume T30→T5; no illegal edge introduced by E1..E10 |
| Traceability updated | **PASS** — `STAGE_01_TRACEABILITY_MATRIX.csv` rows R27–R31 added for E1/E2, E3, E6, E7, E8/E9 |
| Sampling summary complete | **PASS** — the four `[SIMULATION SAMPLING]` sites unchanged; Stage-1E procedures add no new draw |

## Git delta

Modified (6): `STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_MINER_STATE_MACHINE.md`,
`STAGE_01_ROUND_STATE_MACHINE.md`, `STAGE_01_TRACEABILITY_MATRIX.csv`,
`STAGE_01B_STATE_PATH_AUDIT.md`, `STAGE_01D_SEMANTIC_TEST_VECTORS.md`.
Added (9): the `STAGE_01E_*` deliverables (this file, correction report, assignment-validity audit,
propagation-failure audit, round-closure table, template-refresh audit, procedure call graph,
semantic test vectors, checksum manifest).
No file outside `docs/thesis_revision_v45/stage_01/` is touched.

## Result

All eleven acceptance gates pass and all cross-document consistency checks hold. The executable
specification conforms to E1–E10 while preserving B1–B9, C1–C10, and D1–D9. Name remains PoCol; no
new protocol features; documentation only; protected drafts byte-identical.
