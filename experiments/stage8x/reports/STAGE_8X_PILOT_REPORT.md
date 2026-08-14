# STAGE 8X — PILOT REPORT

**Phase 4–5 deliverable.** Executed *before* the freeze and *before* any primary run.

> The Pilot dataset is **excluded from every inferential result**. It uses its own
> seed sub-namespace (`pilot-master`), its own run-ID prefix (`8XP_`), and its own
> output files. `tests/test_stage8x.py::test_seed_registry_is_fresh_and_partitioned`
> asserts that the Pilot and primary seed sets are disjoint.

Command: `python -m experiments.stage8x.run --phase pilot`

---

## 1. Tested settings

| Item | Setting |
|---|---|
| Network sizes | N ∈ {100, 300, 500} |
| Protocols | X-PW, X-PC, X-PW-MT (secondary comparator) |
| Pilot seeds | 5 dedicated seeds (`pilot-master`) |
| Runs | 3 × 3 × 5 = **45 physical pilot runs** |
| Horizon | T = 10 000 s |
| Target interval | I_target = 600 s |
| Hardware | S21 Pro: 234 TH/s, 3510 W, 15 J/TH per miner |
| Difficulty | D_N = H_N · 600 / 2³² (single D_N per N, shared by both protocols) |
| Epoch domain | S_N = H_N · τ_epoch with τ_epoch = 600 s; L = h·600 = 1.404×10¹⁷ per miner |
| Propagation | Exp(mean 0.42 s) broadcast to all peers |

---

## 2. Pilot results

Means over the 5 pilot seeds.

| Protocol | N | blocks | mean interval (s) | W_total (evals) | dup ratio | F_low | epoch exhaustions | mean low (s) | max low (s) | miners entering low | stale | wall (s) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| X-PC | 100 | 18.2 | 502.4 | 2.3350e+20 | 0.0000 | 2.127e-03 | 9.6 | 2.21 | 5.02 | 100% | 0 | 0.018 |
| X-PC | 300 | 15.8 | 582.7 | 7.0026e+20 | 0.0000 | 2.482e-03 | 9.8 | 2.54 | 5.98 | 100% | 0 | 0.050 |
| X-PC | 500 | 16.8 | 568.3 | 1.1672e+21 | 0.0000 | 2.353e-03 | 9.2 | 2.54 | 6.05 | 100% | 0 | 0.091 |
| X-PW | 100 | 18.2 | 501.3 | 2.3400e+20 | 0.0000 | 0 | 0 | — | — | 0% | 0 | 0.014 |
| X-PW | 300 | 15.8 | 581.3 | 7.0200e+20 | 0.0000 | 0 | 0 | — | — | 0% | 0 | 0.041 |
| X-PW | 500 | 17.2 | 536.6 | 1.1700e+21 | 0.0000 | 0 | 0 | — | — | 0% | 0 | 0.068 |
| X-PW-MT | 100 | 10.8 | 930.3 | 2.3400e+20 | 0.3275 | 0 | 0 | — | — | 0% | 0 | 0.014 |
| X-PW-MT | 300 | 11.4 | 950.7 | 7.0200e+20 | 0.3273 | 0 | 0 | — | — | 0% | 0 | 0.042 |
| X-PW-MT | 500 | 10.8 | 952.6 | 1.1700e+21 | 0.3312 | 0 | 0 | — | — | 0% | 0 | 0.073 |

Pooled block-interval calibration (all pilot N and seeds):

| Protocol | pooled mean interval | blocks |
|---|---|---|
| X-PW | **585.9 s** | 256 |
| X-PC | 590.6 s | 254 |
| X-PW-MT | 909.1 s | 165 |

---

## 3. Calibration checks (the ten Pilot objectives)

**(1) Difficulty / target.** `D_N = H_N·600/2³²` gives
D₁₀₀ = 3.2687×10⁹, D₃₀₀ = 9.8060×10⁹, D₅₀₀ = 1.6343×10¹⁰, i.e. exactly
proportional to H_N. `target/2²⁵⁶ = q_N` holds to 1e-9 relative
(`test_target_probability_mapping`). A single D_N is handed to both protocols
(`test_pow_and_pocol_share_the_same_difficulty_and_target`).

**(2) Expected PoW block interval near 600 s.** Pooled X-PW mean = **585.9 s** over
256 blocks. For an exponential process the standard error of the mean interval is
600/√256 = 37.5 s, so the observation sits 0.37 SE below the nominal value —
no evidence of miscalibration. **No parameter was changed on the basis of this
number.**

**(3) Nonce-domain size / representation.** The domain is *derived*, not tuned:
S_N = H_N·τ_epoch with τ_epoch = I_target = 600 s, giving exactly one block's
expected work per epoch and a per-miner range L = h·600 = 1.404×10¹⁷ candidates,
identical at every N. The Stage 8S/8U diagnostic domain of 1600 is **not** reused.

**(4) Exhaustion behaviour.** Three categories are separated:
* *legitimate protocol range completion* — a miner finishes its own assigned range.
  Observed 960 / 2940 / 4655 completions per run at N = 100 / 300 / 500, i.e. one
  per miner per epoch, exactly as designed;
* *global nonce-domain exhaustion* — every honest range swept with no solution, so
  the common template is refreshed. Observed share of epochs ending this way:
  **0.345 / 0.383 / 0.354** at N = 100 / 300 / 500, against the closed-form
  prediction e⁻¹ = **0.368**. The mechanism behaves exactly as the theory says;
* *simulator artifact from an undersized domain* — counter
  `domain_artifact_exhaustions`, **0 after the fix in §4**.

**(5) Event-scheduler correctness.** Deterministic `(time, seq)` ordering; stale
events are invalidated by a per-miner work token. Zero stale blocks were observed,
which is expected with a 0.42 s propagation mean against a 600 s interval
(fork probability per block ≈ 0.07 %) — not a defect.

**(6) Low-power transitions.** Every ACTIVE→LOW_POWER transition is matched by a
LOW_POWER→ACTIVE transition (960/960, 2940/2940, 4655/4655). 100 % of miners enter
low power at least once. Mean episode 2.2–2.5 s, maximum 5.0–6.1 s.

**(7) State-time conservation.** max over all runs and miners of
|t_active + t_low − T| = **1.82×10⁻¹² s** (float rounding only).

**(8) Energy accounting.** X-PW is ACTIVE for the entire horizon, so
E = N·3510·T exactly (`test_pow_is_active_for_the_whole_horizon`). Energy comes
only from `simulator/energy.py::account`, i.e. state × power × time.

**(9) Runtime and memory.** 45 pilot runs in **2.06 s** total; slowest single run
0.099 s (N = 500). The 300-run primary matrix is therefore ~15 s. T = 10 000 s is
comfortably feasible and was **not** changed.

**(10)–(12) Instrumentation, duplicate counting, reproducibility.**
`W_total = h · t_active` holds to 1.2×10⁻¹⁵ relative. `W_total = W_unique +
W_duplicate` holds exactly. X-PC duplicates = 0 across every pilot run; X-PW
duplicates = 0 (distinct templates); X-PW-MT duplicates = 0.327–0.331, against the
closed-form expectation 1 − (1 − 1/N)^N → 1 − e⁻¹ = 0.368 for full epochs (the
observed value is slightly lower because rounds interrupt epochs before they
complete). Re-running any configuration with the same seed reproduces bit-identical
physical results.

---

## 4. Problems encountered and fixes

**P1 — Candidate indices exceeded the 4-byte-extranonce serialisation width.**
The diagnostic counter `domain_artifact_exhaustions` fired 22 477 times at N = 300
and 49 815 times at N = 500. Cause: a PoCol epoch domain is
S_N = N × 1.404×10¹⁷ candidates, which exceeds 2⁶⁴ = 1.845×10¹⁹ for N ≥ 132, so the
absolute candidate index of a high-id miner could not be serialised as
(4-byte extranonce ‖ 4-byte nonce).
*Fix:* widened the extranonce field to 8 bytes (`hashing.EXTRANONCE_BITS = 64`),
giving a per-template candidate space of 2⁹⁶ ≈ 7.9×10²⁸. Stratum `extranonce2` is
commonly 4–8 bytes and the coinbase can carry more, so this is realistic. It is a
**serialisation-width choice, not a scientific parameter**: it changes no
probability, no rate, no difficulty and no energy quantity, and the numeric results
before and after the fix are identical. After the fix the counter is **0** in every
run.

**P2 — Work over-counting in the interval ledger (found by the identity check).**
`W_total` exceeded `h·t_active` by 0.3 %. Cause: after a solution the scanned
segment was logged once explicitly and then re-derived a second time from elapsed
time during re-assignment. *Fix:* `_record_scan` now advances the scan clock as well
as the cursor watermark. Post-fix error 1.2×10⁻¹⁵. This is precisely the defect that
the `W_total = h·t_active` identity exists to catch.

No other problem was found. **No scientific parameter was altered by the Pilot.**

---

## 5. Structural finding recorded before the freeze

The Pilot confirms the Phase-1 audit finding **A5** quantitatively, and it matters
for interpretation:

* Homogeneous S21-Pro miners holding **equal disjoint ranges complete those ranges
  simultaneously**. The network therefore exhausts the epoch domain at the same
  instant the individual miner does, so a PoCol miner's low-power residency is
  bounded by the time needed to *agree on and receive the refreshed common
  template*, not by any surplus of idle capacity.
* Measured consequence: F_low ≈ 2.1–2.5 × 10⁻³, i.e. mean low-power episodes of
  ~2.2–2.5 s occurring ~9–10 times per 10 000 s run.
* Therefore a **small** primary energy effect is expected, and a null or near-null
  result (brief Outcome C/E) is a live possibility. This expectation is recorded
  here, before the freeze, so that it cannot be presented afterwards as a finding
  that was anticipated only in hindsight.

The Pilot also confirms that the declared secondary comparator is not decorative:
X-PW-MT loses ~35 % of its block production to duplicate work (909 s vs 586 s mean
interval), which is the only place in Stage 8X where disjoint allocation has a
first-order effect.

---

## 6. Final frozen settings (unchanged from the pre-Pilot design)

| Parameter | Frozen value | Changed by the Pilot? |
|---|---|---|
| Per-miner hash rate | 234 TH/s | no |
| Per-miner active power | 3510 W | no |
| Efficiency | 15 J/TH | no |
| α cases | 0, 0.10, 0.25, 0.50 | no |
| Network sizes | 100, 200, 300, 400, 500 | no |
| Horizon T | 10 000 s | no |
| Target interval | 600 s | no |
| Difficulty rule | D_N = H_N·600/2³² | no |
| Epoch sweep τ | 600 s | no |
| Nonce domain | S_N = H_N·τ ; L = h·τ | no |
| Propagation | Exp(mean 0.42 s) | no |
| Seeds | 30 fresh primary seeds | no |
| Extranonce serialisation width | 4 B → **8 B** | yes — non-scientific (P1) |
| Work-ledger clock advance | corrected (P2) | yes — defect fix |

**Objective justification.** Both changes are validity/numerical-feasibility fixes
required by failing diagnostics (an unrepresentable index and a violated accounting
identity). Neither was selected by looking at whether it favours PoCol or PoW;
both are neutral with respect to the comparison, and P2 in fact removed a spurious
0.3 % inflation that applied to *both* protocols. No parameter was tuned toward any
outcome.

**Verdict: Pilot PASSED.** Proceed to freeze.
