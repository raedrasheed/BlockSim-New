# STAGE 05A — Pilot Report (diagnostic only; NOT thesis evidence)

72 pilot runs (≤ 150 cap), 36 full event-loop + 36 direct-model, 3 fixed seeds
(20260201–03). Runner: `experiments/thesis_revision_v43/pilot.py`. Raw
(read-only): `results/thesis_revision_v43/stage_05a/{raw,manifests}`. Summary:
`manifests/_PILOT_SUMMARY.json`. Pilot results must not enter the thesis.

## Headline
- **72 runs, max wall time 3.05 s/run**, all well under the 240 s cap.
- **198 / 198 reconciliations pass** (A energy, B candidate, D events, E blocks,
  F time — each where applicable).
- Deterministic reproduction confirmed (same seed → identical outputs; test 38).

## Findings by hypothesis

| H | pilot evidence | direction |
|---|---|---|
| H1 duplicate coverage | B1 dup rate **0.99** (distinct=100/10000) vs B2 **0.31–0.35** (distinct≈6600) | B1 ≫ B2 ✓ |
| H2 energy equivalence | B0 and B3_C1 total energy **= 8.420833 kWh** at N=100 & 500, all seeds | equal ✓ |
| H3 C2 mechanism | energy reconciles to active+idle+coordination in every C2 run | decomposition holds ✓ |
| H4 homogeneous symmetry | C2 homogeneous equal-range: **idle_time = 0 → no saving**, idle ratio irrelevant | ✓ |
| H5 heterogeneity/allocation | idle emerges under heterogeneity, **but equal == weighted (see limitation)** | partial / blocked |
| H6 inactive | (not in pilot; scheduled for 5B) | — |
| H7 propagation delay | legit stale rate **0 (≤5 s) → 5.8 % (30 s) → 7.7 % (60 s)** | rises with delay ✓ |
| H8 μ | exhausted rounds **79 → 34 → 8** for μ = 0.5 → 1 → 2 | falls with μ ✓ |

## Reconciliation pass/fail (198 checks)
| id | identity | applied to | result |
|---|---|---|---|
| A energy | total = active+idle+coordination | direct + full-sim (invariant) | **PASS** |
| B candidate | total = distinct+duplicate | direct | **PASS** |
| D events | scheduled = valid+legit+obsolete(+cancel+beyond) | full-sim | **PASS** |
| E blocks | main_blocks = accepted | full-sim | **PASS** |
| F time | active+idle = eligible time | direct | **PASS** |

(C nonce-domain and full D/E/F for every scenario are exercised more completely
in 5B; the pilot covers the applicable identities per execution model.)

## Verified pilot purposes
- runtime ✓ (≤3.05 s); storage ✓ (summaries + diag, ~few MB); deterministic
  reproduction ✓; manifest completeness ✓; metric reconciliation ✓;
- **legitimate stales emerge under increased delay** ✓ (0→5.8%→7.7%);
- **C2 saving decomposes exactly into active/idle durations** ✓ (identity
  `saving = Σ idle_time·(P_active−P_idle)`; homogeneous idle_time=0 ⇒ 0 saving);
- **B3/C1 data are not duplicated** ✓ (one `pocol_continuous` dataset, labels
  "B3;C1").

## Limitations detected (this is a pilot purpose — "detect invalid/redundant configs")

1. **Equal-vs-weighted allocation is not yet separable in the direct model.**
   `simulate_round` sizes ranges ∝ hash-rate shares, so the "equal" and
   "weighted" C2 heterogeneous runs are **identical** (both 77.1 s / 311.6 s idle
   at N=100/500). The small idle observed is a **range-rounding artifact**, not
   the genuine equal-range-heterogeneous-rate effect. **Blocker for H5:** Stage 5B
   requires extending the scenario/simulator model to **decouple range size from
   hash rate** (equal ranges with heterogeneous rates → fast miners idle).
2. **B1/B2 have no full event-loop implementation.** They are executed here via
   the direct single-round coverage model (duplicate/coverage/energy only). A
   full event-loop implementation (coverage → exhaustion → interval over 10 000 s)
   is a **Stage 5B prerequisite** for their block/throughput/stale outcomes.
3. **Direct-model energies are toy-scale** (H = N in the pilot) — used for
   semantic/reconciliation checks only; the full-sim runs (B0/B3_C1) carry the
   realistic 8.4208 kWh magnitude.

## Provenance note
Pilot runs used the simulator at commit `9e8040b` (the Stage-4 code; Stage-5A
added only non-simulator tooling — `pilot.py`, `build_matrix.py`,
`scenario_definitions.py` is unchanged). This is recorded per run.
