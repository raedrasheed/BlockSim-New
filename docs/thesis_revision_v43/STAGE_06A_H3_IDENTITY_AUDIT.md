# Stage 6A — H3 Preregistered Idle-Saving Identity Audit

Direct verification of the preregistered H3 identity (Stage 6A §4), replacing the earlier
indirect check. Machine-readable per-run records:
`results/thesis_revision_v43/stage_06a/diagnostics/h3_idle_saving_identity.csv`.

## 1. The preregistered identity

For each applicable C2 run *i*:

```
saving_i = Σ_j  idle_time_ij · (P_active_j − P_idle_j) / 3,600,000        [kWh]
```

computed from the **frozen** parameters and authoritative per-miner records:

- `P_active_j = hash_rate_hps_j · efficiency_j_per_th / 1e12`  (W); efficiency = 21.5 J/TH,
  network hash rate 141 TH/s → Σ_j P_active_j = 3031.5 W.
- `P_idle_j = idle_power_ratio · P_active_j`  (W).
- `idle_time_ij` = per-miner `idle_time_s` from `per_miner-C2.jsonl.gz`.

Compared against the observed saving `observed_i = anchor − total_energy_kwh_i`, accounting
explicitly for `coordination_energy_kwh` (0 for all C2 runs):

```
residual_i = saving_i − (observed_i + coordination_energy_i)      (expected 0)
```

## 2. Result

| Quantity | Value |
|----------|-------|
| C2 runs checked | **570** (all C2) |
| Runs with idle triggered (saving > 0) | 120 |
| Absolute tolerance | 1e-9 kWh |
| **Max absolute residual** | **7.1e-15 kWh** |
| Max relative residual, runs with saving > 1e-3 kWh (n=60) | **1.6e-15** |
| Max relative residual, all runs (incl. near-zero-saving) | 0.073 (small-denominator artifact only) |
| **Failed runs (|residual| > 1e-9 kWh)** | **0** |
| Per-run fields recorded | run_id, miner_count, seed, idle_power_ratio, idle_power_saving_kwh, observed_saving_kwh, coordination_energy_kwh, residual_kwh, relative_residual, pass |

The identity reconciles to **machine precision** for every C2 run. The large *relative*
residual over the full set is a small-denominator artifact: many runs have observed saving
≈ 0 (homogeneous-equal, or hash-rate-weighted runs whose modeled idle is near zero), so a
machine-epsilon absolute residual divided by a near-zero denominator inflates the ratio.
Restricted to the 60 runs with a substantive saving (> 1e-3 kWh), the relative residual is
≤ 1.6e-15. The pass criterion is the absolute tolerance; **all 570 runs pass**.

## 3. Disposition

The preregistered idle-saving identity is **verified directly**; H3 is classified
**SUPPORTED**. The saving is idle-driven (0 under homogeneous-equal, positive only under
heterogeneity-induced early completion, up to ≈ 5.87 kWh), and is attributable to reduced
**active power-time**, never to nonce-domain partitioning. Had the identity failed to
reconcile, the sub-claim would have been classified `NOT_TESTABLE_AS_PREREGISTERED`; it did
not.
