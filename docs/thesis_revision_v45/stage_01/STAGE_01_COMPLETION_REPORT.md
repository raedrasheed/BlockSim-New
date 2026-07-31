# Stage 1 — Completion Report (Formal specification of the idle policy within PoCol)

Specification-only stage. Branch `thesis-v45-pocol-stage1-protocol-specification`, created from
the accepted Stage-0 commit `e154df21fb62bc49839d9359711028baf7295f1d`. **No executable
simulator code, no DOCX/PDF, no experiments, no protected-artifact changes.**

## Naming and baseline discipline

The algorithm name is **PoCol** throughout; the mechanism is described only as *"the idle
policy within PoCol."* The forbidden variants (PoCol-E / Energy-Aware PoCol / Enhanced PoCol)
appear **only inside prohibition statements**, never as usage. The accepted baseline is
preserved: nonce-domain partitioning alone does not reduce total fixed-horizon energy (A1 =
8.420833333 kWh at 141 TH/s, 21.5 J/TH, 3031.5 W, 10,000 s); any future energy reduction is
attributed to reduced active power-time (idle policy / reserve / reduced participation). No
mechanism is claimed to be implemented, validated, secure, fair, or incentive-compatible.

## Deliverables (all documentation, under `docs/thesis_revision_v45/stage_01/`)

| # | File | Covers spec section |
|--:|------|---------------------|
| 1 | STAGE_01_PROTOCOL_SCOPE.md | §3 scope (include/exclude/out-of-scope) |
| 2 | STAGE_01_TERMINOLOGY.md | §3 terminology table |
| 3 | STAGE_01_MINER_STATE_MACHINE.md | §4 (8 states, 13 facets each, transitions T1–T25) |
| 4 | STAGE_01_ROUND_STATE_MACHINE.md | §5 (10 round states, transitions R1–R21) |
| 5 | STAGE_01_TEMPLATE_SPECIFICATION.md | §6 template + §17 difficulty/target rule |
| 6 | STAGE_01_RANGE_ASSIGNMENT_SPECIFICATION.md | §7 assignment (linear/circular, alpha, apportionment) |
| 7 | STAGE_01_IDLE_POLICY_SPECIFICATION.md | §8 exact exhaustion + idle entry |
| 8 | STAGE_01_ENERGY_MODEL_SPECIFICATION.md | §9 multi-state energy model |
| 9 | STAGE_01_SECURITY_FLOOR_SPECIFICATION.md | §10 time-varying rates + §11 security floor |
| 10 | STAGE_01_RESERVE_POLICY_SPECIFICATION.md | §12 reserve policy |
| 11 | STAGE_01_RANGE_LEASE_AND_REASSIGNMENT.md | §13 leases + reassignment |
| 12 | STAGE_01_PROGRESS_VERIFICATION_ABSTRACTION.md | §14 modeled progress abstraction |
| 13 | STAGE_01_EARLY_STOP_CERTIFICATE.md | §15 early-stop certificate + 7-step validation |
| 14 | STAGE_01_REWARD_PENALTY_INTERFACE.md | §16 reward/penalty interface |
| 15 | STAGE_01_FAILURE_AND_ADVERSARIAL_PATHS.md | §18 failure table (19 paths) |
| 16 | STAGE_01_INVARIANT_CATALOGUE.md | §19 invariants I1–I19 (incl. I18a/I18b) |
| 17 | STAGE_01_PROTOCOL_PSEUDOCODE.md | §20 pseudocode (20 procedures, non-executable) |
| 18 | STAGE_01_THREAT_MODEL.md | §21 threat model + 5-way classification |
| 19 | STAGE_01_OPEN_QUESTIONS.md | §22 open-question register |
| 20 | STAGE_01_TRACEABILITY_MATRIX.csv | §23 traceability (22 requirements) |
| 21 | STAGE_01_COMPLETION_REPORT.md | this report |
| 22 | STAGE_01_CHECKSUM_MANIFEST.sha256 | §24 checksums |

## Quality gates (§25) — all pass

| Gate | Result |
|------|--------|
| No executable source file changed | ✅ (git delta only under `stage_01/`) |
| No simulator configuration changed | ✅ |
| No DOCX or PDF changed | ✅ (draft-42 `2c3afdc5…`, draft-44 `a31400bc…` unchanged) |
| No protected branch moved | ✅ |
| All deliverables are documentation | ✅ |
| Every state transition has a guard and action | ✅ (miner T1–T25, round R1–R21) |
| Every round termination path defined | ✅ (ROUND_ACCEPTED / ROUND_EXHAUSTED / TEMPLATE_REFRESH / ROUND_ABORTED) |
| Every energy term has units | ✅ (W, s, kWh via /3,600,000) |
| Every security-floor variable defined | ✅ (6 parameters) |
| Every reassignment preserves provenance | ✅ (`previous_assignment_reference`, `assignment_version`; I9) |
| Every accepted solution requires range membership | ✅ (I2, early-stop validation step 4) |
| Difficulty remains fixed | ✅ (I12; §17) |
| No implemented/validated/secure/fair/incentive-compatible claim | ✅ (all such terms are negations) |
| No replacement name for PoCol | ✅ (forbidden names only in prohibitions) |
| All unresolved issues recorded | ✅ (16 open questions) |
| No Stage-2 implementation begins | ✅ |

## Completeness against §27 COMPLETE criteria

- Protocol semantics complete enough to implement deterministically: **yes** — every miner and
  round transition has a guard + action; the pseudocode covers all 20 procedures; the three
  simulation-sampling points are isolated from deterministic logic.
- All state and round transitions defined: **yes**.
- Energy and security accounting specified: **yes** — the six-term energy model with units and
  the parameterised security floor over time-varying `H_active(t)`, `H_honest(t)`,
  `H_adversarial(t)`, `q_adv(t)`.
- All invariants testable: **yes** — I1–I19 (including I18a/I18b) each carry a planned Stage-2/3/4/5 test.
- No Stage-2-blocking open question remains: **yes** — the open-question register fixes a
  minimal, conservative default for every semantics-affecting question (Q1–Q12); Q13–Q16 are
  non-blocking.
- Every requirement traceable: **yes** — the 22-row traceability matrix maps requirement →
  state/event → invariant → threat → implementation stage → test stage → thesis section.
- Only documentation files added: **yes**.

## Open items carried forward (non-blocking)

Numeric parameter values (idle-power ratio, security-floor thresholds, alpha, reserve
fraction, wake latency) are deliberately unset at Stage 1 and will be fixed at pilot /
preregistration (Stage 6). The completeness of range-search and incentive/Sybil properties
remain modeled-only and are recorded as open research problems and out-of-scope items, not as
supported results.

## Verdict

All §27 COMPLETE criteria are satisfied and the branch is committed and pushed.

**STAGE_1_PROTOCOL_SPECIFICATION_COMPLETE_READY_FOR_CORE_IMPLEMENTATION**
