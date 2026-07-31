# Stage 1B — Hash-Rate Identity Audit

Verifies CR-B6: exact, deterministic hash-rate decomposition and the new invariant I17.

## Canonical decomposition

- `H_honest(t)` = sum of hash rates of honest miners in `ACTIVE_HASHING`.
- `H_adversarial(t)` = sum of hash rates of adversarial miners in `ACTIVE_HASHING`.
- `H_active(t) = H_honest(t) + H_adversarial(t)`.
- Only `ACTIVE_HASHING` contributes; `EXHAUSTED_PENDING` (though at `P_hash`), `RESERVE`,
  `LOW_POWER_LISTEN`, `WAKING`, `OFFLINE`, `DISQUALIFIED` contribute nothing.

## Checks

| # | Check | Result |
|--:|-------|--------|
| 1 | Exact identity `H_active(t) = H_honest(t) + H_adversarial(t)` stated as invariant I17 | PASS — INVARIANT_CATALOGUE (I17), SECURITY_FLOOR §1.1, TERMINOLOGY, TRACEABILITY (R10/R11) |
| 2 | Three quantities computed **deterministically** from the active-state census after states are determined | PASS — SECURITY_FLOOR §1.1, pseudocode `ActiveHashRateUpdate`, INVARIANT_CATALOGUE I17 |
| 3 | `H_adversarial` NOT sampled independently after `H_active` is computed (the `[SIMULATION SAMPLING]` step decides which adversarial miners are in `ACTIVE_HASHING`, then all three are derived deterministically) | PASS — pseudocode `ActiveHashRateUpdate`; SECURITY_FLOOR §1.1 |
| 4 | `q_adv(t)` is undefined/NA when `H_active(t) = 0`, with a recorded security-floor breach (not treated as zero) | PASS — SECURITY_FLOOR §1.1, INVARIANT_CATALOGUE I17, TERMINOLOGY, TRACEABILITY, OPEN_QUESTIONS Q9 |
| 5 | I17 carries the standard invariant fields and a planned test stage (Stage 3) | PASS — INVARIANT_CATALOGUE I17 row + summary table |

## Ordering rationale

The adversarial-behavior model may sample or decide **which** adversarial miners continue
hashing (a state decision), but the hash-rate totals are a pure function of the resulting
active-state census. This removes the Stage-1A defect in which `H_adversarial` could be
sampled after `H_active` had already been fixed, which could break the additive identity.

## Result

**HASH-RATE IDENTITY AUDIT: PASS.**
