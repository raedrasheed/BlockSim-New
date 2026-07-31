# Stage 1G — Correction Report (pre-implementation lock)

**Branch.** `thesis-v45-pocol-stage1g-preimplementation-lock`
**Base.** `4991d0af76452e97b904f07c682c06dd7791b763` (Stage 1F).
**Scope.** Documentation only — no executable source, configuration, DOCX, PDF, or experiment
changes. Protected DOCX drafts byte-identical; Stage 1A–1F artifacts unmodified (F9/G-lock).

**Naming rule (binding).** Algorithm is **PoCol**; mechanism is **the idle policy within PoCol**.
Forbidden name strings appear only in prohibition clauses. No property is claimed; A1 baseline
unchanged; no new consensus feature — G1–G11 are causal-consistency and determinism corrections.

## G1 — I2 corrected to discovery-time eligibility

Acceptance now binds a solution to the IMMUTABLE assignment version that was VALID and `CURRENT` at
`discovery_time`, resolvable from the `SolutionEligibilitySnapshot`; the version need NOT be
`CURRENT` at certificate/block arrival (may be `PAUSED`/`SUPERSEDED`). Updated: invariant catalogue
I2; pseudocode §0.5g + `ValidateCandidate`; miner-SM §1.7/§2/§3.2; round-SM §2.6/§3.3/R5/R6/§4.1;
terminology addendum; traceability R39. Audit: `STAGE_01G_ACCEPTANCE_PREDICATE_AUDIT.md`. TV39.

## G2 — I18 replaced by consistent I18a/I18b; RENEWED removed from CreatePendingAssignment

`I18a` (`count(CURRENT) <= 1` per lineage; zero legal) and `I18b` (one live head in
`{PENDING, CURRENT, PAUSED}` per open lineage; zero after closure; atomic renewal at `renewal_time`)
replace the impossible "exactly one CURRENT at every instant". `CreatePendingAssignment` now handles
only ORIGINAL/REASSIGNED (fresh lineages); `RenewAssignment` is the sole renewal path and reuses the
source lineage. Updated: catalogue I18a/I18b; pseudocode §0.5/§0.8/`CreatePendingAssignment`;
miner-SM §1.7; traceability R38/R40. Audit: `STAGE_01G_LINEAGE_INVARIANT_AUDIT.md`. TV40.

## G3 — ActiveHashRateUpdate compute-only; AdversarialParticipationChangeEvent through the hook

`ActiveHashRateUpdate` is now READ-ONLY (no sampling, no census mutation). Each modeled adversarial
entry/exit is a scheduled `AdversarialParticipationChangeEvent` that changes state ONLY via
`ApplyMinerStateTransition` (residency/energy/H-recompute/I17/floor-schedule). Updated: pseudocode §8
+ new §8a; sampling summary item 2; traceability R41. Audit: `STAGE_01G_STATE_HOOK_AUDIT.md`. TV41.

## G4 — Status-aware wake failure

`WakeCompleteEvent` failure branches on the target status: PENDING (case A — preserve accepted
coverage, expose only the accepted unsearched suffix, correct provenance) vs PAUSED (case B — preserve
all three frontiers, reassign only `[accepted_frontier+1, range_end]`, explicit `resume_wake_failed`
disposition, clear candidate pause fields). Never `PAUSED → CLOSED` by the PENDING-only rule. Updated:
pseudocode §0.10; traceability R42. Audit: `STAGE_01G_HASH_EVENT_AUDIT.md` §wake. TV42.

## G5 — Timestamp microphase contract

Replaced the flat priority sequence with explicit microphases: PHASE 1 terminal closure; 2 template
refresh; 3 collect all block arrivals; 4 `AcceptanceBatchFinalize` (one atomic arbitration+closure);
5 terminal-guarded floor evaluation; 6+ certificate/discovery/…. `BlockAcceptancePoint` REGISTERS
only; round-acceptance closure is the atomic result of `AcceptanceBatchFinalize`. Updated: pseudocode
§0.7 + `BlockAcceptancePoint` + `AcceptanceBatchFinalize` (replacing `AcceptanceTimestampBatch`) +
§21; round-SM §2.6/R6. Spec: `STAGE_01G_EVENT_MICROPHASE_SPEC.md`. TV43/TV44.

## G6 — Reachable candidate lifecycle

`CreatePropagationContext` sets `DISCOVERED`; `ScheduleSolutionPropagation` advances
`SELF_VALIDATED → PROPAGATING`; `BlockAcceptancePoint` sets `PENDING_ACCEPTANCE`.
`active_propagation_set` holds ONLY `{PROPAGATING, PENDING_ACCEPTANCE}`. Removed the "iff" forbidding
SECURITY_RECOVERY coexistence. Updated: pseudocode §0.6/§0.8/`CreatePropagationContext`/
`ScheduleSolutionPropagation`; traceability R45. TV45 (ids), TV46 (recovery).

## G7 — Deterministic identifiers and iteration

`CandidateID = (RoundID, candidate_discovery_seq)`, `PropagationID = (CandidateID,
propagation_attempt_seq)`; every create/cancel/schedule loop iterates in stable sorted order (MinerID,
CandidateID, …); `seq` assigned after ordering; queue order independent of hash-map iteration. Updated:
pseudocode §0.2/§0.7a/`CreatePropagationContext`/`ScheduleSolutionPropagation`/`AcceptanceBatchFinalize`/
`HandlePropagationFailure`/`ValidBlockAccept`/`RoundAbort`/`CloseTemplateAssignments`; traceability
R46. Audit: `STAGE_01G_DETERMINISM_AUDIT.md`. TV45.

## G8 — Propagation during SECURITY_RECOVERY; round registries

`SECURITY_RECOVERY` coexists with a non-empty `active_propagation_set`; block arrivals/arbitration
remain processable; a valid candidate may close a recovery-state round (`ValidBlockAccept` allows
`{SOLUTION_PROPAGATION, SECURITY_RECOVERY}`). `RoundInitialise` initialises the registries;
`RoundAbort` (and closure/refresh) disposition every live context and clear them. Updated: pseudocode
§0.6/`RoundInitialise`/`ValidBlockAccept`/`RoundAbort`/`CloseRoundAssignments`/`CloseTemplateAssignments`;
round-SM §2.5/R6/R13; traceability R47. Audit: `STAGE_01G_CANDIDATE_CLEANUP_AUDIT.md`. TV46/TV47/TV50.

## G9 — Event-scheduled hashing

Replaced the blocking `ActiveHashing` WHILE loop with `StartHashing` / `HashWorkEvent` /
`ScheduleNextHashWork`. Each unit verifies the miner is still `ACTIVE_HASHING` and the exact version
`CURRENT`, evaluates one bounded unit, may emit a candidate/completion, schedules the next unit, and
returns. Pending units self-cancel after pause/exhaustion/revocation/offline/disqualification/refresh/
closure. Updated: pseudocode §5 (+§0.7b) + `WakeCompleteEvent` (calls `StartHashing`); sampling
summary item 1; traceability R43. Audit: `STAGE_01G_HASH_EVENT_AUDIT.md`. TV48.

## G10 — Terminal-round security guard

`SecurityFloorEvaluate` is always SCHEDULED (never inline) and carries `(RoundID, TemplateID,
state_version)`; it returns `stale_noop` for a terminal round or a stale epoch and never transitions a
terminal round to `SECURITY_RECOVERY`. `HandlePropagationFailure` schedules it. Updated: pseudocode §9
+ `HandlePropagationFailure` + §0.7c; traceability R41. TV44.

## G11 — Complete candidate resume envelopes

Every candidate resume event carries `CandidateID` AND `PropagationID`; `ResumeFromPause` verifies
BOTH; `HandlePropagationFailure` matches paused miners on both ids. Updated: pseudocode
`HandlePropagationFailure`/`ResumeFromPause`; traceability R48. TV49.

## G12 (F9-lock) — historical artifacts preserved

No `STAGE_01[A-F]_*` file is modified (verified by git delta). Supersession notes are recorded in
`STAGE_01G_CROSS_DOCUMENT_AUDIT.md` §supersession, not by rewriting prior evidence.

## Summary of changed / added artifacts

| Artifact | Change |
|----------|--------|
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` | §0 model (0.5–0.7c, 0.8); G1–G11 procedures; §5/§8/§8a/§9; acceptance cluster; §21 |
| `STAGE_01_MINER_STATE_MACHINE.md` | §1.7 conventions; I2/I18 references (G1/G2) |
| `STAGE_01_ROUND_STATE_MACHINE.md` | §2.5 recovery coexistence; §2.6; R6/R13; I2 references |
| `STAGE_01_INVARIANT_CATALOGUE.md` | I2 discovery-time (G1); I18a/I18b (G2) |
| `STAGE_01_TERMINOLOGY.md` | Stage-1G addendum |
| `STAGE_01_TRACEABILITY_MATRIX.csv` | R39–R48 (R38 amended) |
| `STAGE_01G_*` (12 new deliverables) | this report + 8 audits/specs + test vectors + call graph + cross-document audit + checksum manifest |

No executable source, configuration, DOCX, or PDF file is modified; no Stage 1A–1F artifact is modified.
