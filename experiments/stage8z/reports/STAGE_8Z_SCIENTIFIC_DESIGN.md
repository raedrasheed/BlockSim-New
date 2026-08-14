# STAGE 8Z — SCIENTIFIC DESIGN

**Phase 2–3 deliverable.** Written before implementation and before any Stage 8Z run.

---

## 1. Diagnosis of Stage 8Y (Phase 2)

Stage 8Y reached a maximum **53.87 %** energy saving (P3 energy-aware, H2, N = 300,
α = 0) but **no** configuration combined > 50 % saving with ≥ 90 % block retention;
the best retention among all > 50 % points was **68.8 %**. Its own decomposition
attributed **74.7 % (H2) / 77.2 % (H4)** of the saving to *reduced hash
participation* and only **25.3 % / 22.8 %** to preferential selection of efficient
ASICs, with the selection share exactly **0.000** in the homogeneous control.

Reading Stage 8Y's raw outputs, the mechanism is unambiguous:

| Stage 8Y point | saving | retention | mean H_active | nominal r_H |
|---|---|---|---|---|
| P3 / H2 / N=300 / α=0 | 0.5387 | 0.6442 | 0.5985 | 0.60 |
| P3 / H4 / N=300 / α=0 | 0.5186 | 0.6877 | 0.6000 | 0.60 |
| P4 / H2 / N=300 / α=0 | 0.4748 | 0.5765 | **0.5621** | 0.60 |
| P0 / H0 / N=300 / α=0 | 0.0024 | 1.0000 | 0.9976 | 1.00 |

Two facts drive everything Stage 8Z does:

**(D1) Block retention tracks the *realized* mean active hash fraction.** Under a
matched target, blocks arrive as a Poisson process of rate `H_active(t)·q`, so
`BlockRetention ≈ (1/T)∫H_active dt / H_N`. No amount of work orchestration changes
this: reassigning *which* candidates are scanned does not change *how many* are
scanned per second.

**(D2) Stage 8Y left realized capacity on the table.** P3's realized 0.5985 sits
essentially at its nominal 0.60, but **P4's realized 0.5621 falls 3.8 pp below its
nominal 0.60** because reserves woken mid-epoch finish at staggered times while early
finishers park in LOW_POWER. That gap is recoverable, and recovering it is a genuine
orchestration problem.

Stage 8Z therefore attacks the frontier from the *retention* side: instead of asking
"how few miners can we run", it asks "given a guaranteed hash floor, what is the
cheapest set that realizes it, and can orchestration make the realized floor equal the
nominal one".

## 2. Preregistered analytic ceiling

Because of (D1) the reachable region is bounded by hardware, not by cleverness. For a
realized hash floor `F_H`, the minimum active power fraction is the solution of
`min Σ P_i s.t. Σ h_i ≥ F_H·H_N`, and the maximum saving at α = 0 is `1 − r_P`.
Computed from the **frozen Stage 8Y registry** (not from any simulation), at N = 300:

| Realized floor | H0 ceiling | H2 ceiling | H4 ceiling |
|---|---|---|---|
| 0.70 | 29.7 % | **45.4 %** | 39.7 % |
| 0.80 | 20.0 % | 30.2 % | 26.4 % |
| 0.85 | 15.0 % | 22.7 % | 19.9 % |
| **0.90** | 10.0 % | **14.9 %** | 13.0 % |
| **0.95** | 4.7 % | **7.5 %** | 6.5 % |
| 1.00 | 0.0 % | 0.0 % | 0.0 % |

At α = 0.10 multiply by 0.9. The bound is structural: the registry's efficiency spread
is 15.0 → 29.5 J/TH (factor 1.967), so the selectivity ratio `r_P/r_H` cannot fall
below `η_min/η_N` = 0.771 (H2) or 0.674 (H4).

**Consequences recorded before execution:**

* **Outcome A** (> 50 % ∧ ≥ 95 %) is **analytically impossible** — the ceiling at 95 %
  retention is 7.5 %.
* **Outcome B** (> 50 % ∧ ≥ 90 %) is **analytically impossible** — ceiling 14.9 %.
* **Outcome C** (≥ 30 % ∧ ≥ 95 %) is **analytically impossible**.
* **Outcome D** (≥ 40 % ∧ ≥ 90 %) is **analytically impossible**.
* Outcomes **E** and **F** are the live ones.

This is stated now so that it cannot later be presented as a discovery, and so that
the experiment is not mistaken for a search for a result the hardware forbids.

## 3. What Stage 8Z can therefore actually establish

Given §2, the scientifically meaningful questions are:

**Q1 — Does orchestration realize the ceiling?** Does the *realized* mean active hash
fraction equal the *nominal* floor, and does the realized saving equal the analytic
ceiling? Stage 8Y's P4 missed by 3.8 pp; Stage 8Z's dynamic reassignment and
predictive reserve are designed to close that gap. This is a falsifiable, quantitative
prediction.

**Q2 — Does Stage 8Z fill the high-retention frontier region that Stage 8Y never
reached?** Stage 8Y produced no point above 68.8 % retention with any meaningful
saving. A hash-floor policy should populate the 85–100 % retention band. Frontier
*extension* is a real improvement even without frontier *domination*.

**Q3 — Does dynamic reassignment provide genuine energy benefit?** Under
hash-proportional slots every active miner completes simultaneously, so there is no
residual to move and reassignment should be **inert**. It should matter only where
completion is staggered — i.e. after reserve activation. Stage 8Z tests this directly
rather than assuming reassignment helps.

**Q4 — Does same-work efficiency improve?** `SameWorkSaving = 1 − E_PoCol /
E_PoW,samework` isolates efficiency from participation. It is bounded by `1 − η_A/η_N`
and is the only metric in the family that is *not* contaminated by doing less work.

**Q5 — What do the floor, the fairness constraint and the reserve cost?**

## 4. Policy hierarchy (nested, for attribution)

| ID | Policy | Adds |
|---|---|---|
| Z0 | Traditional PoW | — (principal comparator) |
| Z1 | Stage-8Y energy-aware baseline (r_H = 0.60, no floor) | reproduces the 8Y P3 point |
| Z2 | Hash-floor energy-aware | minimum active hash-capacity constraint |
| Z3 | Z2 + dynamic work reassignment | residual-range transfer with a range ledger |
| Z4 | Z3 + adaptive reserve | predictive activation + hash-capacity step-up |
| Z5 | Z4 + fair rotation | participation floor / fairness credit |

Each level differs from the previous by exactly one mechanism, so the marginal effect
of each mechanism is identified by differencing adjacent levels on matched seeds.

## 5. Hash-floor semantics (declared)

Stage 8Z uses an **operational floor**: `H_active(t) ≥ F_H·H_N` at all mining times
*except* explicitly measured transition windows (waking, template transition,
post-acceptance cancellation). Every excursion is recorded, and the mandatory metric

```
HashFloorDeficit  D_H = ∫₀ᵀ max(0, F_H·H_N − H_active(t)) dt      [hash·s]
```

is reported normalised by `F_H·H_N·T`. A policy may not claim to hold a 90 % floor if
it spends materially below it, and the realized `min H_active` and time-below-threshold
are reported alongside.

## 6. Dynamic reassignment (the principal new mechanism)

The nonce domain `S = H_N·τ` (τ = 600 s, installed capacity) is partitioned into one
disjoint slot per **installed** miner. Under Z2 the parked miners' slots are simply
never scanned. Under Z3+ an active miner that completes its own slot may **claim** an
unclaimed residual slot instead of parking, under a range ledger that enforces:

1. no candidate index is owned by two miners simultaneously;
2. no already-scanned segment is ever reassigned;
3. no completed segment is rescanned;
4. every transfer has a unique event id and an immutable ownership history;
5. source ownership ends strictly before target ownership begins;
6. the physical-work identity `W = ∫H_active dt` remains exact;
7. transfer changes neither target, difficulty, nor the global domain `S`;
8. no exact-input duplicate hashes are introduced.

Reassignment priority (frozen from exploratory data, never from confirmatory):
R0 none, R1 fastest-first, R2 efficiency-first, R3 **marginal-energy-first**
(`min_j P_j·L_remaining/h_j`), which is the a-priori preferred rule.

## 7. Adaptive reserve trigger

Instead of a fixed timer, activation is predictive. With the target fixed, the
probability of finding a block within the remaining deadline window is

```
P_success(Δt) = 1 − exp(−H_active·q·Δt)
```

and the reserve steps up when `P_success(Δt) < θ` (or another preregistered risk
condition). Step-up is in **hash-capacity** terms (`F_H: 0.80 → 0.90 → 0.95 → 1.00`),
not miner counts, and the added miners are those minimising incremental power for the
required incremental hash capacity. θ is swept in exploratory analysis and one value
is frozen before the confirmatory runs.

## 8. Fairness rotation

Z5 adds a rolling-window participation floor `p_min` (F2) as the principal scheme,
with F0 (none), F1 (soft credit) and F3 (hardware-class floor) as exploratory
alternatives. Stage 8Y's P3 permanently excluded **all 150 S19j Pro units** at H4
(Gini 0.53, 159/300 miners never active); Z5 exists to quantify what removing that
exclusion costs in energy.

## 9. Exploratory / confirmatory separation

This is the principal methodological upgrade over Stage 8Y. Four **disjoint** seed
groups: pilot, exploratory, confirmatory, long-horizon. The exploratory phase sweeps
floors, reassignment rules, reserve thresholds and fairness schemes on *exploratory
seeds only*. Selection rules are declared in advance:

* **Reassignment rule** → the rule with the highest mean realized `H_active` at fixed
  floor; ties to R3.
* **Reserve threshold θ** → the value minimising `HashFloorDeficit` subject to not
  increasing mean active power fraction by more than 2 pp.
* **Fairness scheme / p_min** → the largest `p_min` whose exploratory energy penalty
  is ≤ 3 pp of saving.
* **Confirmatory floors** → `{0.85, 0.90, 0.95, 1.00}` (declared now, not selected).

Confirmatory runs then use **fresh seeds never used for tuning**.

## 10. Matched conditions

Difficulty `D = H_N·600/2³²` from full installed hardware, one per (N, composition),
handed unchanged to Z0–Z5 — no recalibration for reduced active sets, reserve
activation, reassignment or selection. Nonce domain `S = H_N·τ` from installed
capacity; reassignment changes ownership only. Propagation `Exp(mean 0.42 s)`.
Horizon 10 000 s, long horizon 100 000 s, target interval 600 s.
α ∈ {0, 0.05, 0.10, 0.25, 0.50} — model assumptions, never vendor modes; primary
interpretation at α = 0.10. Wake ∈ {0,1,5,10,30} s, waking draws full active power and
does no hashing.
