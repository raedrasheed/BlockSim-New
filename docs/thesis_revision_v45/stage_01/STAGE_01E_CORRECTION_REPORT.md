# Stage 1E — Correction Report (pre-implementation contract)

**Branch.** `thesis-v45-pocol-stage1e-preimplementation-contract`
**Base.** `29a312ac0ab4bf6c64d56d48f5e7248f52530b21` (Stage 1D).
**Scope.** Documentation only — no executable source, configuration, DOCX, PDF, or experiment
changes. Protected DOCX drafts are byte-identical (see `STAGE_01E_CROSS_DOCUMENT_AUDIT.md`).

**Naming rule (binding).** The algorithm is **PoCol**; the mechanism is **the idle policy within
PoCol**. The strings "PoCol-E", "Energy-Aware PoCol", "Enhanced PoCol" are prohibited and do not
appear. No property (energy, security, fairness, incentive) is claimed — Stage 1 specifies
structure only. The accepted baseline (A1: partitioning alone does not reduce fixed-horizon
energy) is unchanged; any energy reduction is attributable ONLY to reduced active power-time via
the idle policy.

This report enumerates the ten corrections E1–E10 and, for each, the exact defect, the fix, and
the affected artifact(s).

---

## E1 — Solution-eligibility snapshot (validate against discovery state, not the later PAUSED state)

**Defect (1D).** A finder's certificate/block were implicitly validated against the finder's
assignment as it stood at certificate/block arrival. After the finder PAUSES (PATH B), its
assignment is PAUSED, so a late validation could spuriously reject a genuinely-discovered solution.

**Fix.** Added `CreateSolutionEligibilitySnapshot`, producing an IMMUTABLE snapshot at discovery
time containing exactly `{RoundID, TemplateID, AssignmentID, assignment_version, MinerID, nonce,
discovery_time, range_start, range_end, assignment_status_at_discovery=CURRENT, candidate_hash,
target}`. `EarlyStopGenerate` binds the certificate to the snapshot (`snapshot_ref`) and signs over
all fields including it. `ValidateCandidate` validates against the SNAPSHOT and does NOT require the
finder's assignment to be CURRENT at arrival; it requires the snapshot was CURRENT at discovery, the
assignment was not revoked before `discovery_time`, `range_start ≤ nonce ≤ range_end`, and the bound
RoundID/TemplateID/target/signature hold.
**Artifacts.** `STAGE_01_PROTOCOL_PSEUDOCODE.md` (§15/§16). Audited in
`STAGE_01E_ASSIGNMENT_VALIDITY_AUDIT.md`; exercised by TV18, TV19.

## E2 — Self-validate the certificate, not an unsigned candidate

**Defect (1D).** `SelfValidateFoundSolution` could be read as validating an unsigned
`candidate_solution` (which has no `signature/authentication` field).

**Fix.** `SelfValidateFoundSolution(RoundContext, certificate, snapshot)` receives the SIGNED
certificate and calls the SAME `ValidateCandidate` predicate used by recipients and by acceptance;
the predicate's final conjunct checks the certificate signature/authentication. The canonical
sequence is: candidate → `EarlyStopGenerate` (signed cert) → `SelfValidateFoundSolution(cert,
snapshot)` → propagation → finder `EnterLowPowerListen(VALID_SOLUTION_VERIFIED)`.
**Artifacts.** `STAGE_01_PROTOCOL_PSEUDOCODE.md`. Exercised by TV20.

## E3 — One propagation-failure handler

**Defect (1D).** Resume logic was inlined only in `BlockAcceptancePoint`'s non-accept branch; an
empty valid batch in `AcceptanceTimestampBatch` returned `no_valid_candidate` without resuming
paused miners — they could be stranded.

**Fix.** Added `HandlePropagationFailure(RoundContext, certificate, snapshot, failure_reason ∈
{REJECTED, BLOCK_UNAVAILABLE, PROPAGATION_TIMEOUT, NO_VALID_CANDIDATE})`. It returns the round to
HASHING (or SECURITY_RECOVERY on a floor breach), cancels obsolete candidate-specific events,
enumerates every PATH-B paused miner (`entry_stop_reason = VALID_SOLUTION_VERIFIED`), and schedules
`ResumeFromPause` (which restores CURRENT from `actual_frontier` and recomputes hash rates).
`BlockAcceptancePoint` calls it for every non-accepted outcome; `AcceptanceTimestampBatch` calls it
when its valid set is empty.
**Artifacts.** `STAGE_01_PROTOCOL_PSEUDOCODE.md` (§16d/§16d-bis/§16e). Audited in
`STAGE_01E_PROPAGATION_FAILURE_AUDIT.md`; exercised by TV21.

## E4 — Reserve activation creates a PENDING assignment

**Defect (1D).** `ReserveActivate` transitioned RESERVE → WAKING and called `WakeComplete` without
first creating and ledgering a PENDING assignment, so `WakeComplete`'s "activate PENDING → CURRENT"
had nothing to activate.

**Fix.** `ReserveActivate` now (1) selects the exact unsearched range, (2) `CREATE … WITH status =
PENDING`, (3) appends to the ledger and binds it, (4) RESERVE → WAKING (T4), (5) `WakeComplete`,
(6) activates PENDING → CURRENT ONLY on a successful wake, (7) on wake failure records
`reserve_wake_failure`, moves the miner OFFLINE, releases the range, and returns
`activation_failure` with no CURRENT assignment recorded.
**Artifacts.** `STAGE_01_PROTOCOL_PSEUDOCODE.md` (§10); TV14 updated in
`STAGE_01D_SEMANTIC_TEST_VECTORS.md`; exercised by TV22.

## E5 — Remove/narrow T6

**Defect (1D).** T6 (`ACTIVE_HASHING → ACTIVE_HASHING`) allowed a changed-range reassignment
"shortcut" that bypassed WAKING and conflated a changed-range replacement with a lease renewal.

**Fix.** T6 is RETIRED. Every NEW range assignment passes through WAKING. A same-holder lease
renewal is a non-state-changing in-state administrative operation: the range is unchanged,
`AssignmentID`/`assignment_version`/provenance are updated, status stays CURRENT, and no wake cycle
is charged. A changed-range replacement is never called a renewal.
**Artifacts.** `STAGE_01_MINER_STATE_MACHINE.md` (§2.3, transition table T6 row, §3.1 prohibited,
§3.2), `STAGE_01B_STATE_PATH_AUDIT.md` (T6 row marked removed),
`STAGE_01_PROTOCOL_PSEUDOCODE.md` (`LeaseExpiry`). Exercised by TV23, TV27.

## E6 — SOLUTION_PROPAGATION is a real round state entered at propagation start

**Defect (1D).** Entry to SOLUTION_PROPAGATION was ambiguous / effectively after acceptance;
acceptance performed a double `HASHING → SOLUTION_PROPAGATION → ROUND_ACCEPTED`.

**Fix.** One canonical model: `ScheduleSolutionPropagation` performs `HASHING →
SOLUTION_PROPAGATION` at the FIRST valid found-solution. `ActiveHashing` is permitted in `{HASHING,
SOLUTION_PROPAGATION, SECURITY_RECOVERY}`, so unpaused miners keep hashing and further candidates
may be scheduled. Rejection/timeout returns `SOLUTION_PROPAGATION → HASHING` (or SECURITY_RECOVERY);
accepted arbitration performs the SINGLE `SOLUTION_PROPAGATION → ROUND_ACCEPTED` transition.
**Artifacts.** `STAGE_01_PROTOCOL_PSEUDOCODE.md` (`ActiveHashing`, `ScheduleSolutionPropagation`,
`ValidBlockAccept`), `STAGE_01_ROUND_STATE_MACHINE.md` (§2.6). Exercised by TV24.

## E7 — Deterministic round-closure state map

**Defect (1D).** `CloseRoundAssignments` used a generic "update state consistently" and could
overwrite `RANGE_EXHAUSTED`/`VALID_SOLUTION_VERIFIED` when the round later closed.

**Fix.** Rewritten with an EXPLICIT action for every holder state (ACTIVE_HASHING,
EXHAUSTED_PENDING, LOW_POWER_LISTEN, WAKING, REGISTERED, RESERVE, OFFLINE, DISQUALIFIED), recording a
`round_closure_disposition` SEPARATE from `entry_stop_reason`. Only an ACTIVE_HASHING holder (which
had no prior stop reason) receives the disposition as its entry reason. `RoundAbort` and
accepted-block closure use the same table.
**Artifacts.** `STAGE_01_PROTOCOL_PSEUDOCODE.md` (§17a). Tabulated in
`STAGE_01E_ROUND_CLOSURE_TABLE.md`; exercised by TV25.

## E8 — State-aware template refresh

**Defect (1D).** `TemplateRefresh` transitioned arbitrary miners directly to WAKING and a round-SM
statement allowed TEMPLATE_REFRESH to bypass TEMPLATE_COMMITMENT.

**Fix.** Added `CloseTemplateAssignments` (closes old-template assignments via legal per-state edges,
preserves history). `TemplateRefresh`: `→ TEMPLATE_REFRESH → CloseTemplateAssignments → build →
TEMPLATE_COMMITMENT → TemplateCommit (→ ASSIGNMENT)`; selects only eligible miners in
{REGISTERED, RESERVE, LOW_POWER_LISTEN}, creates fresh ORIGINAL PENDING, uses the legal per-source
transition into WAKING (T3/T4/T10) then WakeComplete; OFFLINE/DISQUALIFIED receive no assignment;
finally executes ASSIGNMENT → HASHING explicitly. Removed the round-SM "directly to ASSIGNMENT"
bypass statements.
**Artifacts.** `STAGE_01_PROTOCOL_PSEUDOCODE.md` (§19), `STAGE_01_ROUND_STATE_MACHINE.md`
(§2.9, §3.11). Audited in `STAGE_01E_TEMPLATE_REFRESH_AUDIT.md`; exercised by TV26.

## E9 — Correct lease renewal

**Defect (1D).** `LeaseExpiry` invalidated the assignment BEFORE deciding renewal.

**Fix.** `LeaseExpiry` decides renewal FIRST. Renewal preserves the same range and holder, mints a
fresh `AssignmentID`/`assignment_version` (or updates the lease), keeps status CURRENT, retains
accepted progress and provenance, and requires no WAKING. Expiry WITHOUT renewal invalidates the old
assignment and reassigns ONLY the accepted unsearched suffix.
**Artifacts.** `STAGE_01_PROTOCOL_PSEUDOCODE.md` (§12), `STAGE_01_MINER_STATE_MACHINE.md` (§2.3
timeout/side-effects). Exercised by TV27.

## E10 — Blocking test vectors

**Fix.** Added TV18–TV27 in `STAGE_01E_SEMANTIC_TEST_VECTORS.md`; every vector names the exact
procedure(s) and exact preconditions and assumes no unmodeled external action. TV14 updated for E4.

---

## Summary of changed artifacts

| Artifact | Change |
|----------|--------|
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` | E1,E2,E3,E4,E5(LeaseExpiry),E6,E7,E8,E9; sampling summary |
| `STAGE_01_MINER_STATE_MACHINE.md` | E5 (T6 retired; lease renewal in-state) |
| `STAGE_01_ROUND_STATE_MACHINE.md` | E6 (§2.6), E8 (§2.9,§3.11 no commitment bypass) |
| `STAGE_01_TRACEABILITY_MATRIX.csv` | R27–R31 added |
| `STAGE_01B_STATE_PATH_AUDIT.md` | T6 row marked removed (E5) |
| `STAGE_01D_SEMANTIC_TEST_VECTORS.md` | TV14 updated (E4) |
| `STAGE_01E_*` (9 new deliverables) | this report + audits + closure table + call graph + vectors + cross-doc audit + checksum manifest |

No executable source, configuration, DOCX, or PDF file is modified.
