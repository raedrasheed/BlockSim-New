# Stage 1A — Specification Correction Report

Correction-only, documentation-only stage. Branch
`thesis-v45-pocol-stage1a-specification-corrections`, from Stage-1 commit
`d3aebb38b09094779942cae1c237cbac7ada108e`. No executable code, DOCX/PDF, experiments, or
protected-artifact changes. The algorithm name remains **PoCol**; the mechanism is only *the
idle policy within PoCol*.

This report is the **single source of truth** for the eight corrections. Every affected
document uses the verbatim canonical blocks below.

---

## CANONICAL CORRECTED RULES (verbatim — reused across all documents)

### CR1 — Early-stop certificate (definition)
An early-stop certificate is generated **ONLY** after a miner finds a valid candidate
solution satisfying the current target. It **MUST** contain exactly: `RoundID`, `TemplateID`,
`AssignmentID`, `MinerID`, `nonce`, `candidate_hash`, `target`, `signature/authentication`.
It **MUST NOT** be generated from: aggregated progress commitments; searched-domain coverage;
claimed exhaustion; sufficient coverage; or a progress frontier. Progress verification and
early-stop certification are **completely separate mechanisms**. A progress commitment says
"I claim to have searched up to this frontier." An early-stop certificate says "I found this
exact valid solution."

### CR2 — Verification-time state rule
A miner receiving an unverified early-stop certificate **remains in `ACTIVE_HASHING`**; it
continues hashing while verifying; it remains included in `H_active(t)`; verification energy
is recorded separately as `E_verification` (a clearly identified coordination/verification
energy increment), added on top of the `ACTIVE_HASHING` residency energy and **not
double-counted**; only after **all** certificate-validation steps pass may the miner leave
`ACTIVE_HASHING`; a failed certificate produces **no** hashing-state transition. **No
`VERIFYING` miner state is introduced.**

### CR3 — Canonical state-to-power mapping and energy equation
One residency power per state (no numeric values at Stage 1; ordering
`P_offline ≤ P_listen = P_reserve = P_registered ≤ P_hash`, with `P_wake` a transient):

| Miner state | Residency power | Contributes to `H_active(t)`? | Reward-eligible? |
|-------------|-----------------|:-----------------------------:|:----------------:|
| REGISTERED | `P_registered` (= `P_listen`) | No | No |
| RESERVE | `P_reserve` (= `P_listen`; low-power standby, **not** `P_offline`) | No | Availability only |
| ACTIVE_HASHING | `P_hash` | **Yes** | Yes |
| EXHAUSTED_PENDING | `P_hash` (short transient; no idle saving credited here) | No | Yes |
| LOW_POWER_LISTEN | `P_listen` | No | Yes (idle credit) |
| WAKING | `P_wake` | No | Yes |
| OFFLINE | `P_offline` | No | No |
| DISQUALIFIED | `P_offline` | No | No |

Normative energy equation:
`E_i = Σ_{s∈States} (P_{i,s} · t_{i,s}) + E_transition,i + E_coordination,i + E_verification,i`
over the eight miner states.
Duration invariant: `Σ_{s} t_{i,s} = T` (observation horizon) for every miner `i`; there is
**no** residual / `t_other` bucket. Energy invariant: `E_i` equals the sum of the eight
state-residency energies plus `E_transition,i + E_coordination,i + E_verification,i` exactly,
with no residual bucket. `E_verification,i` is a **separate event-energy term** (not folded
into `P_hash·t_hash`); `t_hash` still counts the full active duration and `E_verification` is
the incremental verification cost, so it is not double-counted.

### CR4 — Replacement of I8 (two orthogonal models)
**I8a (coverage-state partition):** for every assignment,
`searched + active_unsearched + inactive_unsearched = assigned_domain`, and the three
coverage categories are pairwise disjoint and collectively exhaustive.
**I8b (custody/provenance model):** each assignment carries a lineage/event status in
`{original, renewed, reassigned, revoked, expired, abandoned}`. These are custody/lineage
properties and **must not** appear as additive terms in the coverage-state equation. A
reassigned position still has an **independent coverage state**
(`searched` / `active_unsearched` / `inactive_unsearched`).
The old equation `searched + unsearched + inactive + reassigned = assigned` is **invalid**
and removed everywhere ("reassigned" is custody, not a coverage state).

### CR5 — Actual vs reported progress (two layers)
**Simulator ground truth:** `actual_frontier`, `actual_positions_evaluated`,
`actual_solution_positions`, `actual_exhaustion`.
**Protocol-level claim:** `reported_frontier`, `reported_exhaustion`, `audit_selected`,
`audit_result`, `claim_accepted_or_rejected`.
The simulator **may** know actual exhaustion exactly; the modeled progress-verification
abstraction does **not** prove actual exhaustion, and **no** progress commitment verifies that
no valid solution exists in the whole range. Honest simulations: `EXHAUSTED_PENDING`
eligibility **may** use actual cursor completion (ground truth). Adversarial simulations:
reported exhaustion is compared with ground truth and passed through the modeled
audit/detection abstraction. All findings are **modeled, not cryptographically proven**.

### CR6 — Competing valid solutions (network-arrival semantics)
The global-oracle rule "smallest `(TemplateID, nonce, MinerID)`" is **removed** as the primary
accepted-solution rule. Instead:
1. Each valid solution receives a reproducible propagation/arrival time.
2. Local acceptance uses the **earliest valid arrival**.
3. Other valid solutions are recorded as competing/stale proposals.
4. Only exact arrival-time ties use a deterministic secondary rule: smallest `candidate_hash`,
   then smallest `MinerID`.
No chain-wide fork-choice proof is claimed.

### CR7 — Stage map (implementation/test stages)
- Stage 2: core miner states and complete energy accounting.
- Stage 3: time-varying hash rate, security floor, reserve activation.
- Stage 4: range leases, reassignment, and modeled progress verification.
- Stage 5: adversarial and incentive model.
- Stage 6: pilot and preregistration.
- Stage 7: scientific freeze and execution.
- Stage 8: statistical analysis.
- Stage 9: thesis integration.
- Stage 10: render and finalisation.

### CR8 — Energy-reduction attribution
`Delta_E_total = Delta_E_range_idle + Delta_E_reserve + Delta_E_early_stop
                 − Delta_E_transition_and_wake − Delta_E_coordination_and_verification`
- `Delta_E_range_idle`: saving from miners exhausting their assigned ranges and entering
  `LOW_POWER_LISTEN`.
- `Delta_E_reserve`: saving from holding reserve miners outside active hashing (at
  `P_reserve`).
- `Delta_E_early_stop`: a propagation/termination optimisation (stopping once a valid solution
  arrives); **not unique to nonce-domain partitioning**.
- `Delta_E_transition_and_wake`, `Delta_E_coordination_and_verification`: **costs**.
Total saving must be net of wake, transition, coordination, and verification energy. These
effects are **not** attributed generically to nonce partitioning.

---

## Defect → correction → resulting canonical rule

| # | Defect | Affected files | Correction | Resulting canonical rule |
|--:|--------|----------------|------------|--------------------------|
| 1 | Early-stop certificate could be generated from aggregate progress commitments | EARLY_STOP_CERTIFICATE, PROTOCOL_PSEUDOCODE, PROGRESS_VERIFICATION_ABSTRACTION, IDLE_POLICY | Early-stop only from a found valid solution; remove progress-derived generation | CR1 |
| 2 | Contradiction: miner "doesn't stop before verification" yet "removed from active hashing during verification" | MINER_STATE_MACHINE, EARLY_STOP_CERTIFICATE, ENERGY_MODEL, ROUND_STATE_MACHINE, PROTOCOL_PSEUDOCODE | Miner stays `ACTIVE_HASHING` while verifying; `E_verification` separate; leaves only after all steps pass | CR2 |
| 3 | Ambiguous grouped energy model (RESERVE = `P_offline` vs `P_listen`; `t_other` without power) | ENERGY_MODEL, MINER_STATE_MACHINE, RESERVE_POLICY, SECURITY_FLOOR, PROTOCOL_SCOPE, IDLE_POLICY | One residency power per state; state-complete equation; `Σ t = T`; no residual | CR3 |
| 4 | I8 wrongly added custody status "reassigned" as a coverage term | INVARIANT_CATALOGUE, RANGE_LEASE_AND_REASSIGNMENT, RANGE_ASSIGNMENT, PROTOCOL_PSEUDOCODE, FAILURE_AND_ADVERSARIAL_PATHS, OPEN_QUESTIONS, TRACEABILITY_MATRIX, TERMINOLOGY | Split into I8a (coverage partition) and I8b (custody model), orthogonal | CR4 |
| 5 | Progress commitment implied proof that no solution exists in the range | PROGRESS_VERIFICATION_ABSTRACTION, IDLE_POLICY, PROTOCOL_PSEUDOCODE, THREAT_MODEL | Separate ground-truth vs reported layers; modeled audit, not proof | CR5 |
| 6 | Global-oracle "smallest (TemplateID, nonce, MinerID)" as primary accepted-solution rule | EARLY_STOP_CERTIFICATE, ROUND_STATE_MACHINE, PROTOCOL_PSEUDOCODE, OPEN_QUESTIONS, THREAT_MODEL, FAILURE_AND_ADVERSARIAL_PATHS | Network-arrival semantics; earliest valid arrival; ties by `candidate_hash` then `MinerID` | CR6 |
| 7 | Implementation/test-stage mappings inconsistent with Stage-0 governance | TRACEABILITY_MATRIX, INVARIANT_CATALOGUE | Re-map to the approved stage plan | CR7 |
| 8 | Energy savings attributed generically to nonce partitioning | ENERGY_MODEL, IDLE_POLICY | Decompose into range-idle / reserve / early-stop minus costs | CR8 |

## Stage-2 status

Stage 2 remains **BLOCKED pending this re-audit**. After the corrections and the
cross-document consistency audit (`STAGE_01A_CROSS_DOCUMENT_CONSISTENCY_AUDIT.md`) pass, the
specification is internally consistent and Stage 2 (core miner states + complete energy
accounting) can be implemented deterministically — subject to explicit approval of this
correction stage.
