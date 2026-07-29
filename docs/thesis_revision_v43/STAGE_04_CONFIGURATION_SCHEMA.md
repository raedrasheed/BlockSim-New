# STAGE 04 — Common Configuration Schema

One validated schema drives every scenario B0–B3 / C1–C2. Code:
`experiments/thesis_revision_v43/config_schema.py` (`ExperimentConfig`,
`validate`). Tests: `test_stage4_duplicates_and_config.py` (32–39),
`test_stage4_stale_and_scenarios.py` (23).

## Fields

`scenario_id, seed, miner_count, simulation_duration_s, network_hash_rate_hps,
miner_hash_rate_distribution, hash_rate_shares, efficiency_j_per_th,
idle_power_ratio, coordination_energy_model, coordination_energy_kwh,
target_block_interval_s, nonce_domain_size, allocation_policy,
search_order_policy, randomized_start_policy, template_policy,
template_refresh_policy, propagation_delay_model, propagation_delay_mean_s,
topology, transaction_arrival_model, block_capacity, inactive_miner_fraction,
logging_level, code_commit`, plus derived `configuration_hash()`,
`per_miner_hash_rate_hps()`, `expected_solutions_mu()`.

## Validation rules (`validate` raises `ConfigError`)

1. `Σ per_miner_hash_rate_hps == network_hash_rate_hps` (within 1e-9).
2. **B0** must use `template_policy="independent"` and `allocation="independent"`
   — a common TemplateID / shared serialized-header duplicate ID is rejected.
3. **B1/B2/B3/C1/C2** require `template_policy="common"`.
4. **B3/C1/C2** require a `disjoint_*` allocation; `disjoint_*` is rejected for
   any other scenario.
5. **B2** requires `randomized_start_policy != "none"`.
6. **C2** must define `idle_power_ratio ∈ [0,1]` (0.0 = explicit lower bound);
   every continuous scenario must **not** set a nonzero idle ratio.
7. `coordination_energy_model="excluded_zero"` ⇒ `coordination_energy_kwh == 0`
   (coordination energy is never invented).
8. `inactive_miner_fraction ∈ [0,1)`; durations, hash rate, efficiency, domain
   size all `> 0`.

## Units (shared by all scenarios)

`*_hps` (H/s), `*_j_per_th` (J/TH), `*_power_w` (W), `*_time_s` (s),
`*_energy_kwh` (kWh); `1 TH/s = 1e12 H/s`, `1 kWh = 3.6e6 J`. Every scenario's
result carries `active_energy_kwh`, `idle_energy_kwh`,
`coordination_energy_kwh`, `total_energy_kwh` (test 39).

## Reproducibility

`configuration_hash()` is a SHA-256 over the fully-resolved config (including
normalized shares); identical configs hash identically, any change differs
(test 37). Seeds make both `simulate_round` and the full harness bit-reproducible
(test 38).
