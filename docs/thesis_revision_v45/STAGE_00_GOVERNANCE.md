# Stage 0 — Governance Charter (thesis-v45 PoCol idle-policy development line)

This document governs a new, stage-gated scientific development line that adds and evaluates
**the idle policy within PoCol**. It is authoritative for Stages 0–10 of this line.

## 0.1 Authoritative starting point

- **Base commit:** `6cb4c9b89f265af95857fdda4417d03ad336edfa`
  (Stage 7B — `thesis-v43-stage7-thesis-integration-2`).
- **Development branch (this stage):** `thesis-v45-pocol-stage0-governance`.
- **Base scientific data lineage:** `thesis-v43-stage6-analysis-2` (`b7b61d20…`).

## 0.2 Naming rule (binding)

- The algorithm name **remains `PoCol`** at all times and in all artifacts.
- **Forbidden names:** `PoCol-E`, `Energy-Aware PoCol`, `Enhanced PoCol`, or any other
  replacement/derivative algorithm name.
- The low-power mechanism is described **only** as *"the idle policy within PoCol"* or
  *"PoCol with the idle policy enabled."*
- The idle policy is an **operating policy inside PoCol**, not a new algorithm.

## 0.3 Accepted scientific baseline (must not be contradicted)

- **Nonce-domain partitioning alone does not reduce total fixed-horizon energy.** Total
  fixed-horizon energy is an accounting invariant (A1 = 8.420833333 kWh under the frozen
  reference setting; max relative deviation 3.6e-16).
- Any new energy reduction must be attributed to an **explicit reduction in active
  power–time** through (a) the idle policy, (b) reserve operation, or (c) reduced
  participation — never to partitioning itself.
- Energy reduction is **successful only if security and service remain within preregistered
  limits**.

## 0.4 Global scientific rules (binding for every stage)

1. PoCol continuous full-participation operation remains the **control**.
2. The idle policy is an operating policy inside PoCol, not a new algorithm.
3. Do not claim that partitioning inherently reduces energy.
4. Do not claim energy improvement until the full frozen experiment and analysis are
   complete.
5. Energy reduction is successful only if security and service remain within preregistered
   limits.
6. Do not dynamically change difficulty in the core confirmatory experiment.
7. Any difficulty-control experiment must be separate and exploratory.
8. Model active hash rate as a **time-varying** quantity.
9. Model adversarial share as a **time-varying** quantity.
10. Retain zero-block runs.
11. Preserve undefined block-normalised metrics as **NA**.
12. Never double-count shared physical executions.
13. Use physical runs / master seeds as the **inferential units**.
14. Call simulated progress verification a **modeled abstraction**, not a complete
    cryptographic proof.
15. Record every assumption, limitation, and unsupported security property.

## 0.5 Stage gates and stop tokens

Each stage produces controlled commits, then **STOPS**. The next stage begins **only after
explicit written approval**. No stage may be started, merged, or combined without approval.

| Stage | Scope | Stop token |
|------:|-------|------------|
| 0 | Governance (this stage) — docs + verification only | `STAGE_0_GOVERNANCE_COMPLETE_READY_FOR_PROTOCOL_SPECIFICATION` |
| 1 | Formal idle-policy specification (no code) | `STAGE_1_PROTOCOL_SPECIFICATION_COMPLETE_READY_FOR_CORE_IMPLEMENTATION` |
| 2 | Core state + multi-state energy implementation | `STAGE_2_IDLE_STATE_IMPLEMENTATION_COMPLETE_READY_FOR_SECURITY_FLOOR` |
| 3 | Security floor + reserve activation | `STAGE_3_SECURITY_BOUNDED_IDLE_POLICY_COMPLETE_READY_FOR_REASSIGNMENT` |
| 4 | Range leases, reassignment, progress model | `STAGE_4_REASSIGNMENT_AND_PROGRESS_MODEL_COMPLETE_READY_FOR_ADVERSARIAL_TESTING` |
| 5 | Adversarial + incentive model | `STAGE_5_ADVERSARIAL_MODEL_COMPLETE_READY_FOR_PREREGISTRATION` |
| 6 | Pilot + preregistration (IP-H1…IP-H10) | `STAGE_6_PREREGISTRATION_COMPLETE_READY_FOR_SCIENTIFIC_FREEZE` |
| 7 | Scientific freeze + frozen execution | `STAGE_7_FROZEN_EXECUTION_COMPLETE_READY_FOR_ANALYSIS` |
| 8 | Statistical analysis (energy survives full accounting?) | `STAGE_8_ANALYSIS_COMPLETE_READY_FOR_THESIS_INSERTION` |
| 9 | Thesis integration → `draft-45-00.docx` (red edits) | `STAGE_9_THESIS_INTEGRATION_COMPLETE_READY_FOR_EXTERNAL_RENDER_VALIDATION` |
| 10 | External render + finalisation | `STAGE_10_FINAL_SUBMISSION_COPY_COMPLETE` / `STAGE_10_FINALISATION_BLOCKED` |

## 0.6 Stage-0 constraints (this stage)

- **No simulator edits.** No file under the scientific engine is created, modified, or
  deleted in Stage 0.
- **No thesis edits.** No `.docx` is created, modified, or deleted in Stages 0–8.
- Stage 0 produces **only** governance/verification documents under
  `docs/thesis_revision_v45/`.
- All protected hashes and branches are verified (see `STAGE_00_PROTECTED_ARTIFACTS.md`).

## 0.7 Confirmatory vs. exploratory separation

- The **core confirmatory experiment** holds difficulty fixed (rule 6). The idle policy's
  energy effect is measured against the continuous full-participation control at matched
  aggregate hash rate and power.
- Any **difficulty-control** study is a **separate, exploratory** track (rule 7) and its
  results may never be presented as confirmatory.

## 0.8 Approval discipline

The agent must stop at each stage's stop token and wait. The agent must not:
- proceed to the next stage without explicit approval;
- modify any protected artifact (§0.9);
- edit the simulator in Stage 0 or the thesis in Stages 0–8.

## 0.9 Protected artifacts (summary; full register in `STAGE_00_PROTECTED_ARTIFACTS.md`)

Immutable in this development line: `draft-42/43/44` DOCX; all freeze, results, data,
analysis, and both Stage-7 integration branches; all previous scientific outputs. This line
adds new commits on `thesis-v45-*` branches only and never rewrites protected history.
