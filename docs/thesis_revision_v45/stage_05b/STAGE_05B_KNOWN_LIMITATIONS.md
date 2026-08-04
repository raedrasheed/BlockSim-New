# Stage 5B — Known Limitations

Stated plainly, so no reader can mistake a modelling choice for a proved property.

## 1. What Stage 5B does not establish

Stage 5B adds **no** claim of incentive compatibility, fairness, Sybil resistance,
selfish-mining resistance, coalition resistance, common-prefix security, chain-quality security
or Bitcoin/PoW-equivalent security. It models bounded adversarial behaviours and measures their
outcomes under the accepted PoCol core. It does not prove PoCol defeats any of them.

## 2. Reward ownership is an accounting rule, not a mechanism-design result

First-physical-evaluator ownership (S5B-1) fixes an accounting defect: a nonce position now
earns at most one work reward, and it goes to whoever really evaluated it first. This makes the
model internally consistent. It is **not** evidence that the resulting reward function is
incentive compatible, budget balanced, fair, or resistant to strategic manipulation. The reward
rates are model parameters, not tuned or optimal values.

## 3. The audit is modelled, not implemented

`audit_detection_probability` is a declared parameter that decides whether a progress or
exhaustion claim is caught. No real verification protocol is specified or implemented. A
detection probability of 0 or 1 is an experimental condition, not a statement about what a
deployed system could detect.

## 4. Splitting and virtual identities remain a sensitivity model

`SubAssignmentRecord` and `VirtualIdentityRecord` are accounting artefacts. The
virtual-subassignment accounting authority (option B of the directive) maps physical evaluations
onto subassignments without changing throughput; it is not a real per-subassignment scheduler
with its own capacity clock. Declared identities grant no physical capacity. **None of this is a
Sybil defence**, and the naive-vs-deduplicated comparison is a sensitivity measurement, not a
demonstration that deduplication is achievable in a real deployment.

## 5. Delayed-wake coverage spans runs, not a single execution

All four wake lifecycles are exercised by real queued events, but no single execution can
simultaneously present an exhausted primary (which wins Path-A candidate selection) and an
unused available reserve (which is required for Path B) for the same fault. S5B-04 therefore
aggregates three executed runs. Each lifecycle is genuinely exercised; the aggregation is stated
here so it is not read as one run covering everything.

## 6. `physical_evaluation_count` is inert when the Stage-5 model is disabled

`physical_evaluation_count` is a Stage-5 counter. With the adversarial model disabled — the
default — it remains 0 while the Stage-2B evaluation ledger is still populated. This is the
explicitly documented distinction permitted by S5B-8: `physical_evaluation_ledger_residual` is
reported as 0 for disabled runs, and the reconciliation invariant admits that case via
`behaviour_profile_count == 0`. With the model **enabled**, a zero physical count beside a
non-empty evaluation ledger is impossible, and the residual is 0 in every measured scenario with
range leases enabled and disabled.

## 7. Reported-rate allocation composed with the floor re-sizes only the primary span

When `security_floor` and `coordinator_uses_reported_hash_rate` are both enabled, the floor
carves the primary span and the reserve-domain slices first, and only the **primary** span is
re-sized from reported rates. Reserve-domain slice sizes are unaffected by reported rates. This
is a declared composition rule, not a claim that any other composition would be equivalent.

## 8. The security floor remains operational only

The floor is an operational active-capacity floor. It is not a security proof, not a bound on
adversarial share, and not a guarantee about chain properties. `q_adv` is reported as NA for any
interval in which the actual active hash rate is zero; an NA interval never enters the
time-weighted mean and is never compared against the threshold.

## 9. Energy accounting

The energy-saving mechanism remains **the idle policy within PoCol**. Nonce-domain partitioning
alone is never described as an energy-saving mechanism. The incremental delayed-wake energy is
a **cost** charged over the realised added waking interval; it is not a saving and is never
reported as one.

## 10. Fixed target

Dynamic difficulty remains excluded. No Stage-5 parameter changes the fixed SHA-256 target or
difficulty. Micro-scenarios use `difficulty = 1` (every nonce a solution) or `1 << 300`
(unreachable) purely to make round outcomes deterministic for evidence; neither is a claim about
realistic difficulty.

## 11. Scenario scale

Every measurement in `STAGE_05B_METRICS.json` comes from small deterministic micro-scenarios
(4 miners, 400-nonce domain, short horizons). They are **not** the confirmatory experiment
matrix, carry no statistical power, and support no inferential claim. Stage 6, preregistration,
the confirmatory matrix, statistical analysis and thesis integration are not begun.
