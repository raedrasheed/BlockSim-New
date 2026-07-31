# Stage 1E — Template-Refresh Audit (E8)

Verifies the state-aware template refresh: old-template closure via `CloseTemplateAssignments`,
correct round-state sequencing through `TEMPLATE_COMMITMENT` (never bypassed), eligible-only
re-activation via LEGAL per-state transitions, exclusion of OFFLINE/DISQUALIFIED, and the explicit
`ASSIGNMENT → HASHING` step. Verified over `STAGE_01_PROTOCOL_PSEUDOCODE.md` (§19) and
`STAGE_01_ROUND_STATE_MACHINE.md` (§2.9, §3.11, R17/R18).

## 1. Required sequence (E8)

| Step | Requirement | Realised by |
|-----:|-------------|-------------|
| 1 | Close old-template assignments via explicit `CloseTemplateAssignments` | `TemplateRefresh` calls `CloseTemplateAssignments(old_TemplateID = TemplateID_current)` |
| 2 | Preserve old history | `CloseTemplateAssignments` PRESERVEs `coverage_state`/`custody_status`/provenance; sets `custody_status <- superseded_by_template_refresh` (lineage marker) |
| 3 | `TEMPLATE_REFRESH → TEMPLATE_COMMITMENT` | explicit transition before `TemplateCommit` |
| 4 | `TemplateCommit → ASSIGNMENT` | `TemplateCommit` requires `TEMPLATE_COMMITMENT`, transitions to `ASSIGNMENT` |
| 5 | Select only eligible REGISTERED / RESERVE / permitted low-power miners | `eligible = {m : state ∈ {REGISTERED, RESERVE, LOW_POWER_LISTEN}}` |
| 6 | Create fresh ORIGINAL PENDING assignments | `CREATE … status = PENDING`; `custody_status <- original`; `previous_assignment_reference <- null` |
| 7 | Use the legal miner-state transition for each eligible source | `REGISTERED→WAKING` (T3), `RESERVE→WAKING` (T4), `LOW_POWER_LISTEN→WAKING` (T10) |
| 8 | `WakeComplete` activates them | `WakeComplete` validates I1/RoundID/new_TemplateID, `PENDING→CURRENT`, T5 |
| 9 | After the assignment set is valid: `ASSIGNMENT → HASHING` | `ASSERT round_state = ASSIGNMENT` then `TRANSITION → HASHING` (R4) |

## 2. Old-template holder routing (CloseTemplateAssignments)

Every old holder leaves the old template through a LEGAL miner-state edge (no fabricated transition):

| Old holder state | Legal edge | Resulting state |
|------------------|-----------|-----------------|
| `ACTIVE_HASHING` | T27 (`ASSIGNMENT_REVOKED`, template changed) | `LOW_POWER_LISTEN` |
| `EXHAUSTED_PENDING` | T8 (exhaustion drop) | `LOW_POWER_LISTEN` (RANGE_EXHAUSTED preserved) |
| `LOW_POWER_LISTEN` | — (assignment closed; state unchanged) | `LOW_POWER_LISTEN` |
| `WAKING` | T12 (bound assignment on discarded template fails validation) | `OFFLINE` |
| `REGISTERED`/`RESERVE`/`OFFLINE`/`DISQUALIFIED` | — (no CURRENT old assignment) | unchanged |

## 3. Acceptance gates

| # | Gate | Result |
|--:|------|--------|
| 1 | `TEMPLATE_COMMITMENT` is never bypassed | **PASS** — `TemplateRefresh` always `→ TEMPLATE_COMMITMENT → TemplateCommit`; round-SM §2.9 exit is "to `TEMPLATE_COMMITMENT` only" and §3.11 states refresh never bypasses it; R17→R18 aligned; the former "directly to ASSIGNMENT" statement is removed |
| 2 | Only legal miner transitions are used | **PASS** — activation uses T3/T4/T10 per source state; closure uses T27/T8/T12; no `*→ACTIVE_HASHING` direct edge and no removed-T6 self-loop |
| 3 | OFFLINE/DISQUALIFIED receive no assignment | **PASS** — `eligible` excludes them (and mid-wake WAKING) |
| 4 | New assignments are ORIGINAL, not reassignment lineage | **PASS** — `custody_status <- original`, `previous_assignment_reference <- null` (C5); no completed old range is reassigned |
| 5 | Old history preserved | **PASS** — `CloseTemplateAssignments` PRESERVEs coverage/custody/provenance |
| 6 | `ASSIGNMENT → HASHING` is explicit | **PASS** — asserted and transitioned at the end of `TemplateRefresh` (R4) |
| 7 | Difficulty unchanged | **PASS** — `ASSERT difficulty unchanged` (I12) |
| 8 | I1 disjointness on the new domain | **PASS** — `WakeComplete` validates I1 for each fresh range at T5 |

## Result

**TEMPLATE-REFRESH AUDIT (E8): PASS.** Template refresh closes old-template assignments through an
explicit procedure preserving history, always commits the new template through `TEMPLATE_COMMITMENT`,
re-activates only eligible miners via their legal per-state transitions (excluding
OFFLINE/DISQUALIFIED), and reaches `HASHING` explicitly. (Exercised by TV26.)
