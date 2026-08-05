# Stage 8U — Analysis Report (frozen preregistered analysis)

**Verdict: the single-handoff useful-work policy within PoCol is NOT LICENSED.**
H-U1 PASS, **H-U2 FAIL**, H-U3 PASS, **H-U5 FAIL**; all deterministic integrity gates
pass in all 60 runs.  The joint rule (H-U1 ∧ H-U2 ∧ H-U3 ∧ H-U5 ∧ integrity) therefore
fails.  Per the directive this is the final refinement cycle: nothing is retuned, no
Stage 8V is created, and the result stands as recorded.

Input: the frozen 60-row `STAGE_08U_RUN_DATASET.csv` only (5 scenarios × 12 fresh paired
confirmatory seeds).  Estimators exactly as preregistered: the run is the unit of
analysis; all 4096 exact sign assignments (two-sided); 10 000 paired bootstrap resamples
with percentile 95% CIs from the frozen analysis root 17618529829928476883; Holm at
α = 0.05 over exactly the four declared contrasts.  Rounds, miners, events, hashes and
chunks are never treated as independent observations.

## 1. Scenario means (12 confirmatory seeds each)

| scenario | energy (kWh) | blocks | closed rounds | median dur (s) | p95 dur (s) | total evals | unique evals | duplicate evals | blocks/M evals | kWh/block |
|---|---|---|---|---|---|---|---|---|---|---|
| W00 matched PoW, population-matched | 0.035833 | 249.42 | 311.25 | 0.1847 | 4.000 | 1 447 489 | 219 374 | 1 228 115 | 172.4 | 1.4475e-4 |
| W01 matched PoW, active-capacity-matched | 0.029383 | 241.75 | 301.25 | 0.2249 | 4.000 | 1 158 562 | 216 190 | 942 371 | 208.7 | 1.2272e-4 |
| P00 PoCol, floor disabled | 0.016548 | 178.00 | 223.42 | 1.1804 | 2.000 | 152 980 | 152 980 | 0 | 1166.1 | 9.312e-5 |
| P01 PoCol, Stage-8S coarse | 0.016129 | 164.50 | 206.00 | 1.1726 | 2.333 | 140 645 | 140 645 | 0 | 1172.2 | 9.832e-5 |
| **P02 PoCol, single handoff** | **0.016175** | **163.67** | **226.50** | **1.1735** | **1.800** | **139 712** | **139 712** | **0** | **1173.2** | **9.898e-5** |

## 2. Preregistered gates

### H-U1 — churn reduction (P02 vs P01): **PASS**

| criterion | value | required | pass |
|---|---|---|---|
| mean reassignments per closed round | 0.4535 | ≤ 1.0 | yes |
| mean activation requests seated | 0.00 (vs P01 646.67) | < P01 | yes |
| mean incomplete activation requests | 0.00 (vs P01 425.00) | < P01 | yes |

Both Holm contrasts are rejected at the smallest attainable exact p (0.000488 = 2/4096):
activation requests −646.67 per run (95% CI [−654.67, −637.67]) and incomplete requests
−425.00 (CI [−441.00, −407.67]).  The single-handoff policy eliminates reserve-wake churn
**entirely** — not merely reduces it.  Stage-8S's central failure mode is removed.

The mechanism is visible in the U4 admission counters: across the 12 P02 runs the
controller rejected on average 3 619.75 wake candidates per run for a too-short useful
window and 1 544.92 because an already-awake receiver could take the work, and seated
zero.  This is the honest structural reading: at the frozen reduced scale a reserve wake
can essentially never pay for itself, because a full 100-nonce primary range takes at
most 1.0 s to search (100 nonces ÷ 100 H) while the wake latency alone is 1.0 s and one
batch adds 0.25 s.  The U4 utility test is doing exactly what it was specified to do, and
what it reveals is that the reserve-wake mechanism is unproductive at this scale — a
finding about the configuration, not a defect of the check.

### H-U2 — service preservation vs W01 (matched PoW, active-capacity-matched): **FAIL**

| criterion | value | required | pass |
|---|---|---|---|
| mean accepted-block ratio P02 / W01 | 0.6770 | ≥ 0.90 | **no** |
| mean median-round-duration ratio P02 / W01 | 5.2190 | ≤ 1.10 | **no** |

Paired difference in accepted blocks: −78.08 per run (CI [−88.58, −68.17], exact
p = 0.000488, Holm-rejected — the difference is real and against P02).

The cause is structural and is exactly the asymmetry the preregistration anticipated when
it refused to make the population-matched control the primary gate — but it turns out to
bind against the capacity-matched control too.  Under the matched same-template PoW
control every mining node searches the **whole** 1600-nonce domain from its own offset,
so any node can find any solution and the expected time to the first valid solution is
short (median round 0.2249 s).  Under PoCol each of the 16 active primaries owns a
disjoint 100-nonce slice, so the round cannot close until the *specific* miner whose
slice contains a solution reaches it (median round 1.1735 s).  Partitioned search trades
per-round latency for work efficiency; the block-count and latency gates as written
measure only the first half of that trade.

### H-U3 — energy reduction vs W01: **PASS**

| criterion | value | required | pass |
|---|---|---|---|
| mean paired relative total-energy reduction | 0.4495 | ≥ 0.20 | yes |
| bootstrap 95% CI lower bound | 0.4487 | > 0 | yes |

Paired energy difference −0.013208 kWh per run (CI [−0.013229, −0.013185],
p = 0.000488, Holm-rejected).  The reduction is large, tight and consistent across every
one of the 12 seeds (FIG13).

### H-U4 — population-matched sensitivity (P02 vs W00): descriptive only, no gate

| quantity | P02 | W00 | paired difference | 95% CI | exact p |
|---|---|---|---|---|---|
| total energy (kWh) | 0.016175 | 0.035833 | −0.019658 | [−0.019679, −0.019635] | 0.000488 |
| relative energy reduction | — | — | 0.5486 | [0.5480, 0.5492] | — |
| accepted blocks | 163.67 | 249.42 | −85.75 | [−95.50, −76.92] | 0.000488 |
| median round duration (s) | 1.1735 | 0.1847 | +0.9888 | [+0.9805, +0.9979] | 0.000488 |
| total physical evaluations | 139 712 | 1 447 489 | −1 307 776 | [−1 310 450, −1 304 980] | 0.000488 |
| unique physical evaluations | 139 712 | 219 374 | −79 661 | [−85 574, −74 012] | 0.000488 |
| duplicate physical evaluations | 0 | 1 228 115 | −1 228 115 | [−1 234 820, −1 220 840] | 0.000488 |
| energy per accepted block (kWh) | 9.898e-5 | 1.4475e-4 | −4.577e-5 | [−5.087e-5, −4.045e-5] | 0.000488 |

These are sensitivity results and carry no licensing weight.  They point the same way as
the W01 comparison: PoCol buys a large energy reduction and a much higher work-efficiency
(1173 vs 172 accepted blocks per million committed evaluations, and cheaper energy per
accepted block) at the cost of fewer blocks and longer rounds inside the horizon.

### H-U5 — operational useful-work limit for P02: **FAIL**

| criterion | value | required | pass |
|---|---|---|---|
| mean duration below the useful floor | 23.130 s | ≤ 15 s | **no** |
| nonterminal handoff epochs (max over runs) | 0 | 0 | yes |
| nonterminal activation requests | 0 | 0 | yes |
| nonterminal leases | 0 | 0 | yes |
| nonterminal reassignment requests | 0 | 0 | yes |
| duplicate nonce count | 0 | 0 | yes |
| post-round evaluation records | 0 | 0 | yes |
| physical-frontier rewinds | 0 | 0 | yes |

Every structural-integrity component passes exactly.  The single numeric limit fails:
23.13 s against a 15 s budget.  On these same fresh seeds the Stage-8S coarse baseline
P01 sits at 27.70 s, so the single-handoff policy is a genuine 4.57 s improvement
(≈ 16.5% relative) — real progress in the same direction as Stage-8S's 42.25 → 28.71 s,
and still short of the preregistered limit.

## 3. Holm family (α = 0.05, exactly the four declared contrasts)

| contrast | exact two-sided p | Holm threshold | reject null |
|---|---|---|---|
| P02 vs P01, activation requests seated | 0.000488 | 0.01250 | yes |
| P02 vs P01, incomplete activation requests | 0.000488 | 0.01667 | yes |
| P02 vs W01, accepted blocks | 0.000488 | 0.02500 | yes |
| P02 vs W01, total energy | 0.000488 | 0.05000 | yes |

All four differences are statistically unambiguous at the resolution the exact
permutation test can express (2/4096 is its floor for n = 12).  Two favour P02 (churn,
energy) and one is decisively against it (blocks).

## 4. Handoff mechanism behaviour (P02, means over 12 runs)

102.67 handoff epochs opened per run, all 102.67 committed, 79.08 completed before round
closure, **0 cancelled and 0 failed**; 1 801.25 second attempts per run were correctly
absorbed as exact replay no-ops (`duplicate_handoff_prevented_count`).  Zero reserve
wakes were seated.  Committed handoffs run at 0.4535 per closed round — comfortably
inside the ≤ 1.0 bound and less than a third of P01's 1.676 reassignments per round.

Floor metrics stay independent as required by U5: P02 sits 268.66 s below the historical
static 3200 H floor (deficit area 821 495 hash·s) and 23.13 s below the useful-work
target (deficit area 23 024 hash·s).  The static floor was never lowered or redefined;
the static family remains unattainable for structural reasons established in Stage 8R
(the four-reserve pool contributes at most 1000 H against a 3200 H floor).

## 5. Why the joint rule fails, stated plainly

The policy did what it was designed to do — it removed reserve-wake churn completely,
kept a large and tight energy advantage, held reassignment churn under one per round, and
kept every structural invariant exact — but two preregistered limits were not met.  The
useful-floor duration missed by 8.13 s.  The service gate against the matched
capacity-matched PoW control missed by a wide margin, and the reason is a property of
partitioned search rather than of the handoff policy: disjoint-range assignment
necessarily serialises a round behind the single miner owning the winning nonce, whereas
uncoordinated full-domain PoW search closes rounds sooner by spending roughly nine times
the physical work (1.16 M evaluations of which 942 K are duplicates, versus 140 K with
zero duplicates).

No parameter was changed after the preregistration freeze, and none is changed now.
