# Stage 8S — Limitations (binding; final refinement cycle)

1. **The structural-policy claim is NOT licensed.** H-S1 (+10.6 blocks, Holm) and H-S4
   (55.1 % retained accounting benefit) passed; H-S2 failed on the useful-floor duration
   (28.7 s > 15 s) and H-S3 failed on every churn count. Only the conditional statement in
   the analysis report may be used.
2. **This was the FINAL controller-refinement cycle.** Per the frozen directive there is
   no re-tuning, no Stage 8T, and no change of seeds, margins, target or difficulty. The
   result stands as-is for thesis integration.
3. **Scale conditionality.** All confirmatory inference is at the frozen 20-miner /
   300 s / 1600-nonce core with 12 fresh paired seeds. The 0.9039 throughput ratio and
   every other number are claims about this configuration only.
4. **The static 0.80 × H0 floor remains structurally unattainable** (~272 s below it in
   every floor arm; pool 1 000 H vs 3 200 H). It is retained as a SECONDARY historical
   metric and was not the H-S2 gate; nothing here reinterprets the Stage-8M/8R failures.
5. **The useful-floor metric is a counterfactual.** It counts idle-receiver seconds under
   the coarse mechanism's own eligibility definition; a different work-delivery mechanism
   would induce a different useful floor. It is never a security metric.
6. **S02 collapsed into S01.** Without a delivery mechanism the useful target cannot
   change decisions; the component arm is descriptive evidence of that, not a defect.
7. **Instant receiver starts are a declared modelling assumption**: already-awake
   LOW_POWER_LISTEN miners begin reassigned chunks without a wake transient. Reserves
   always pay the accepted 1.0 s wake. A deployment where awake listeners also pay a
   ramp-up would weaken S03's gains.
8. **Churn scales with recovered rounds.** More completed rounds mean more reserve-batch
   cycles; the frozen churn limits do not normalise for throughput, and the frozen rule
   forbids redefining them post hoc. Future work: churn metrics normalised per accepted
   block, receiver pools larger than the spare-batch bound, multi-donor repartition, and a
   reserve pool sized to the floor.
9. **Accounting counterfactual, not hardware.** E_power_null is the exact within-run
   price substitution with declared wattages; no unconditional PoCol energy-reduction
   claim is made. Leases/adversarial/incentive mechanisms remain executably validated but
   confirmatorily untested; no broad security or incentive claim is made.
