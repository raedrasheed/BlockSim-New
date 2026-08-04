# Stage 8R — Limitations (binding on every downstream use)

1. **Reduced-resource design, 20-miner scale, 12 fresh paired seeds.** All confirmatory
   inference is at the frozen Stage-6M core scale (20 miners, 300 s horizon, domain 1600,
   difficulty 1000). Nothing extends to other scales or difficulty regimes.
2. **The revised-policy claim is NOT licensed.** H-R4 failed (blocks ratio 0.852 < 0.90;
   below-floor 274 s ≫ 15 s). The only permitted statement is conditional: the revised
   controller improves throughput and decision-churn against the legacy controller
   (H-R1/H-R2 supported under Holm) while retaining the low-power-state accounting benefit
   (H-R5), but it does not reach operational acceptance at this configuration.
3. **The floor is structurally unattainable at this population.** The 4-reserve pool
   (1 000 H total) cannot restore a 3 200 H floor once ≥ 2–3 primaries exhaust. The H-R4
   failure measures a population/pool constraint, not merely a controller property; no
   controller policy within this frozen population could pass the 15 s limit. Changing the
   reserve fraction or pool rates would be a NEW experiment, not a reinterpretation.
4. **H-R3 is refuted in its declared family outcome.** Activation *requests* rose (312.8 →
   593.7) even though batch decisions and unattainable-decision churn collapsed; the
   preregistered churn hypothesis (fewer requests) is reported as failed. The batch-level
   improvement is a supporting observation only.
5. **Within-run accounting counterfactual.** E_power_null is the exact price-substitution
   counterfactual on the same event path with declared wattages — a low-power-state
   accounting result, never a hardware measurement and never an unconditional protocol
   energy claim.
6. **H_pipeline is a forecast.** It is not current capacity, not a security metric, and
   was never substituted for the physical H_effective in any integrity check. WAKING
   miners contribute zero to H_effective throughout.
7. **Predictions are engineering estimates.** The fixed 100 H prediction error and the
   190 late wakes per run are reported; no security property is derived from any forecast.
8. **R03 is exploratory only.** Its floor improvements (below-floor −52 s vs R01) carry no
   confirmatory weight and may not determine any verdict; the 25-nonce chunk was frozen
   and untuned.
9. **Historical results stand.** The Stage-8M conclusion (large low-power-state energy
   difference; service/capacity limits exceeded; joint claim NOT licensed) is preserved
   unchanged; Stage-8R neither overwrites nor reinterprets it. Leases/adversarial/
   incentive mechanisms remain executably validated but confirmatorily untested here; no
   broad security or incentive claim is made.
