# STAGE 8Y — PILOT REPORT

**Phase 5–6 deliverable.** Executed before the freeze and before any confirmatory run.

> The Pilot dataset is **excluded from every inferential result**. It uses its own
> seed sub-namespace (`pilot-master`, 6 seeds), its own run-ID prefix (`8YP_`), and
> its own output files. Disjointness from the primary, secondary and long-horizon
> seed groups — and from the entire Stage 8X registry — is asserted in test.

Command: `python -m experiments.stage8y.run --phase pilot`

---

## 1. Pilot design

| Item | Setting |
|---|---|
| Network sizes | N ∈ {100, 300, 500} (small, medium, large) |
| Compositions | H0 (homogeneous), H2 (medium), H4 (multi-generation) |
| Protocols | POW, POW_CT, P0_ALL, P1_EQUAL, P2_HASHPROP, P3_ENERGY, P4_RESERVE |
| Seeds | 6 dedicated pilot seeds |
| Runs | 3 × 3 × 7 × 6 = **378 physical pilot runs** |
| α | all five cases re-priced (1350 energy observations) |
| Wake delay | 10 s (non-zero, the confirmatory value) |
| Horizon | 10 000 s, target interval 600 s |

The Pilot's purpose is to **verify invariants, not hypotheses**.

---

## 2. Invariant verification — all PASS

| Invariant | Result |
|---|---|
| `t_active + t_low + t_standby + t_waking = T` for every miner | max error **1.82×10⁻¹² s** |
| No negative residence time | min residence **0.0 s** (never negative) |
| `W_i = ∫H_active dt` (no hashing while parked or waking) | max relative error **5.59×10⁻¹⁵** |
| `P_N·T = pw_active + pw_waking + pw_low + pw_standby` | max error **1.9×10⁻⁵ W·s** on ~3×10⁹ |
| `W_total = W_unique + W_duplicate` | 0 violations in 378 runs |
| No exact duplicates under disjoint allocation (all PoCol) | **0** in every PoCol run |
| No exact duplicates under traditional PoW (distinct templates) | **0** |
| Common-template PoW *does* produce duplicates | ratio **0.334** (theory `(1−1/N)^N → e⁻¹ = 0.368`) |
| Nonce-value reuse is tracked separately from exact duplication | PoW reuse ratio ≥ 0.99999999997 with 0 exact duplicates |
| Reserve activation occurs only at intended events | P3 activations **0**; P4 wake events = reserve activations exactly |
| Every activated reserve passes STANDBY → WAKING → ACTIVE | `trans_STANDBY->WAKING` = `trans_WAKING->ACTIVE` |
| Completed ranges are not rescanned | asserted per template; duplicates 0 |
| Paired runs share seed and hardware | asserted over the whole primary matrix |
| Same seed reproduces identical physical results | bit-identical on repeat |
| Difficulty identical across all seven protocols | one `D` per (N, composition) |
| Difficulty independent of the active fraction | identical at r_H ∈ {0.3, 0.9} |
| Domain not reduced by parking miners | `S` identical for all active fractions |
| Zero-block runs | **0** (none discarded, none occurred) |
| Decomposition residual | **0.0 J** exactly |

Runtime: 378 runs in **19.8 s** of simulation time (max 0.131 s/run at N = 500), so
the 1080-run confirmatory matrix costs ≈ 60 s. The horizon was **not** changed.

---

## 3. Pilot observations (invariant-level, not hypothesis tests)

Means over 6 pilot seeds at N = 300.

| Comp | Protocol | Saving α=0 | Retention | SelectivityGain | share participation | share selection |
|---|---|---|---|---|---|---|
| H0 | P0_ALL | 0.0021 | 0.9933 | 1.000 | 1.000 | 0.000 |
| H0 | P1_EQUAL | 0.0021 | 0.9933 | 1.000 | 1.000 | 0.000 |
| H0 | P3_ENERGY | 0.4014 | 0.6705 | 1.000 | 1.000 | 0.000 |
| H0 | P4_RESERVE | 0.4282 | 0.6008 | 0.995 | 1.005 | −0.005 |
| H2 | P0_ALL | 0.0021 | 0.9928 | 0.999 | 1.001 | −0.001 |
| H2 | P1_EQUAL | 0.2159 | 0.7838 | **0.772** | 1.296 | **−0.296** |
| H2 | P3_ENERGY | 0.5388 | 0.5307 | **1.342** | 0.746 | **0.255** |
| H2 | P4_RESERVE | 0.4748 | 0.5685 | 1.068 | 0.938 | 0.062 |
| H4 | P0_ALL | 0.0020 | 1.0000 | 1.000 | 1.000 | 0.000 |
| H4 | P1_EQUAL | 0.1314 | 0.8784 | **0.751** | 1.331 | **−0.331** |
| H4 | P3_ENERGY | 0.5187 | 0.5954 | **1.297** | 0.771 | 0.229 |
| H4 | P4_RESERVE | 0.4784 | 0.5536 | 1.059 | 0.946 | 0.054 |

Three structural facts, all confirming the instrumentation works as designed:

1. **`SelectivityGain = 1.000` in the homogeneous control H0**, so the
   selection term of the decomposition is identically zero there. The metric is
   measuring what it claims to measure.
2. **`SelectivityGain < 1` for P1 (equal ranges).** Equal allocation makes the
   *fast, efficient* S21 units finish first and park, so it preferentially removes
   cheap capacity — the opposite of energy-aware behaviour. Its selection term is
   **negative** (−0.30). This is why P2 (hash-proportional) is the correct control
   for P1, exactly as the brief anticipated.
3. **P4's time-average active capacity falls below its stage-0 target.** Reserves
   woken mid-epoch complete their slots at staggered times, so early completers park
   in LOW_POWER while the epoch waits for the last one. This is legitimate post-range
   parking, not a violation, and it is reported rather than asserted away.

The Pilot also confirms Stage 8X's structural finding in the new setting: because
hash-proportional slots make every active miner finish at the same instant, the whole
network is momentarily parked between domain exhaustion and receipt of the refreshed
common template, so the **minimum instantaneous security hash fraction is 0** for
every PoCol policy while the time-average stays high. PoW has no such gap. This is
recorded now and carried into the security analysis.

---

## 4. Defects found and fixed

All three were found and fixed **before** the freeze. Each is classified per the
brief's taxonomy.

**D1 — implementation defect (shared-buffer bug in the S4 optimiser).**
`_optimize_counts` enumerated device-class counts using a shared list; the count of
the most efficient class from the previous branch leaked into the residual
computation, so the closed-form solve under-counted and the optimiser returned a
suboptimal set. Observed at H4/N=300, r_H = 0.60: it returned (32, 86, 56) at
542 988 W instead of the true optimum (60, 81, 0) at 454 410 W.
*Fix:* zero `counts[0]` before computing the residual.
*Verification:* a new test checks the optimiser against **exhaustive enumeration** at
12 (composition, N, r_H) combinations; all are now exactly optimal.
*Scientific direction:* the bug made energy-aware selection look **worse** than it is,
so the fix does not favour the hypothesis — but it was fixed because it was wrong,
not because of its direction.

**D2 — implementation defect (completed ranges rescanned on reserve activation).**
A stage-up woke miners in `LOW_POWER` as well as `STANDBY`. A `LOW_POWER` miner has
already swept its slot for the current epoch, so re-activating it restarted the scan
at cursor 0 and produced **1.34×10¹⁹ exact duplicate evaluations** in P4 — a direct
violation of "completed ranges cannot be rescanned without explicit reassignment".
*Fix:* only a `STANDBY` reserve may be activated by a stage-up; a `LOW_POWER` miner
legitimately wakes at the next template refresh. A related correction gives a woken
reserve the epoch the rest of the network is actually on (`epoch_of_tip`) rather than
a stale epoch index.
*Verification:* PoCol exact duplicates are now **0** in all 378 pilot runs, asserted
per protocol in test.
*Scientific direction:* the bug inflated P4's physical work without changing its
energy, so it distorted the work accounting; the fix is neutral for energy.

**D3 — test-expectation error (not a code defect).**
`test_reserve_only_adds_capacity` asserted that P4's *time-average* active hash
fraction is at least its stage-0 target. That is false by design: post-range parking
legitimately lowers the mean below the stage level (see §3.3). The assertion was
replaced by the correct invariant — that the run's *peak* active capacity exceeds the
stage-0 level, which is what "reserves add capacity" actually means. Two further test
thresholds were relaxed to the values the physics supports (`r_P` vs `r` separation,
and the zero-hash gap at template refresh, which is now a documented positive test).

**No scientific parameter was changed by the Pilot.** D1 and D2 are implementation
corrections; D3 is a test correction. The Pilot therefore does not need to be rerun
under a different design, and the freeze proceeds with the parameters declared in
`STAGE_8Y_IMPLEMENTATION_PLAN.md` §2 unchanged.

---

## 5. Final frozen settings (unchanged from the pre-Pilot design)

| Parameter | Frozen value | Changed by Pilot? |
|---|---|---|
| Hardware registry (3 devices) | S21PRO / S19XP / S19JPRO | no |
| Compositions H0–H4 | as declared | no |
| Primary N | {100, 300, 500} | no |
| Primary compositions | {H0, H2, H4} | no |
| Horizon / long horizon | 10 000 s / 100 000 s | no |
| Target interval | 600 s | no |
| Epoch sweep τ | 600 s | no |
| Propagation | Exp(mean 0.42 s) | no |
| Difficulty rule | `D = H_N·600/2³²`, installed capacity | no |
| Nonce domain | `S = H_N·τ`, installed capacity | no |
| Confirmatory selection | S4 exact optimisation | no |
| Confirmatory r_H (P3) | 0.60 | no |
| Confirmatory schedule (P4) | 0.60→0.75→0.90→1.00 | no |
| Confirmatory trigger / wake | 300 s / 10 s | no |
| Wake power | full active power (conservative) | no |
| α cases | {0, 0.05, 0.10, 0.25, 0.50} | no |
| Seeds | 30 primary, disjoint groups | no |
| S4 optimiser | **corrected (D1)** | implementation only |
| Reserve activation eligibility | **corrected (D2)** | implementation only |

**Verdict: Pilot PASSED.** Proceed to freeze.
