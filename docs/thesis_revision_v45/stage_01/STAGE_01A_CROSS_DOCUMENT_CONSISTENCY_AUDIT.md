# Stage 1A — Cross-Document Consistency Audit

Mechanical + manual audit after applying the eight corrections (CR1–CR8). All checks below
were run by string search across `docs/thesis_revision_v45/stage_01/` and confirmed by
reading the flagged contexts.

| # | Check | Result |
|--:|-------|--------|
| 1 | Every early-stop certificate contains an exact valid solution (8 fields) | **PASS** — CR1 definition present in EARLY_STOP_CERTIFICATE, PROTOCOL_PSEUDOCODE (`EarlyStopGenerate`), TERMINOLOGY |
| 2 | No early-stop certificate is generated from progress coverage | **PASS** — progress-derived generation removed from pseudocode §15; residual mentions are negations ("distinct from", "not generated from") |
| 3 | No unverified certificate removes a miner from `H_active(t)` | **PASS** — CR2 rule in MINER_STATE_MACHINE §1.5, EARLY_STOP_CERTIFICATE §4.1, ROUND_STATE_MACHINE §2.6, PROTOCOL_PSEUDOCODE `EarlyStopVerify`; verifier stays `ACTIVE_HASHING` |
| 4 | Every miner state has exactly one residency-power mapping | **PASS** — canonical CR3 table; REGISTERED=`P_registered`, RESERVE=`P_reserve`, ACTIVE_HASHING/EXHAUSTED_PENDING=`P_hash`, LOW_POWER_LISTEN=`P_listen`, WAKING=`P_wake`, OFFLINE/DISQUALIFIED=`P_offline` |
| 5 | No duration term lacks a power term (`t_other` removed) | **PASS** — `t_other` appears only in the "no `t_other` bucket" negation; `Σ_s t_{i,s} = T` |
| 6 | No power-time interval counted twice | **PASS** — `E_verification` is a separate event term added on top of `ACTIVE_HASHING` residency, not folded into `P_hash·t_hash`; energy invariant states no residual bucket |
| 7 | I8 no longer contains "reassigned" as an additive coverage category | **PASS** — I8→I8a (coverage: searched + active_unsearched + inactive_unsearched = assigned_domain) + I8b (custody, orthogonal) in INVARIANT_CATALOGUE, RANGE_LEASE_AND_REASSIGNMENT, RANGE_ASSIGNMENT, FAILURE, OPEN_QUESTIONS, PROTOCOL_PSEUDOCODE, TEMPLATE_SPECIFICATION, TRACEABILITY_MATRIX; old equation absent |
| 8 | Actual progress and reported progress are separate fields | **PASS** — CR5 ground-truth (`actual_*`) vs protocol-claim (`reported_*`, `audit_*`, `claim_accepted_or_rejected`) in PROGRESS_VERIFICATION_ABSTRACTION, IDLE_POLICY, PROTOCOL_PSEUDOCODE, THREAT_MODEL, TERMINOLOGY |
| 9 | No full-range exhaustion called cryptographically proven | **PASS** — all "cryptographic proof" mentions are negations/"would require"/out-of-scope; "modeled progress-verification abstraction" used throughout |
| 10 | All competing-solution rules are identical (network-arrival) | **PASS** — earliest valid arrival; exact-tie break `candidate_hash` then `MinerID`; in EARLY_STOP_CERTIFICATE, ROUND_STATE_MACHINE, PROTOCOL_PSEUDOCODE, OPEN_QUESTIONS, THREAT_MODEL, FAILURE; global-oracle rule removed (only as rejected option) |
| 11 | All stage mappings match approved Stage-0 governance | **PASS** — CR7 stage map applied in INVARIANT_CATALOGUE (per-invariant test stage) and TRACEABILITY_MATRIX (Stage 2 states+energy; Stage 3 time-varying/floor/reserve; Stage 4 leases/reassignment/progress; Stage 5 adversarial/incentive) |
| 12 | PoCol remains the algorithm name | **PASS** — no forbidden variant used as a name; the strings appear only inside prohibition statements |
| 13 | No executable source, configuration, DOCX, or PDF change | **PASS** — git delta confined to `docs/thesis_revision_v45/stage_01/`; draft-42 `2c3afdc5…` and draft-44 `a31400bc…` byte-identical; no protected branch moved |

## Residual fixes applied during this audit

- `STAGE_01_TEMPLATE_SPECIFICATION.md` (not owned by any correction agent) still cited the old
  I8 additive equation; updated to I8a/I8b (CR4).
- `STAGE_01_TERMINOLOGY.md` still defined the early-stop certificate as "a modeled summary of
  sufficient covered progress" and grouped it under the progress-verification abstraction;
  rewritten to the CR1 found-solution definition, and the early-stop certificate is now stated
  as a **separate** mechanism from progress verification.

## Conclusion

All 13 cross-document consistency checks pass. The specification is internally consistent
across every document and the pseudocode. No cross-document semantic contradiction remains.
