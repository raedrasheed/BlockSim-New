# Stage 5C — Known Limitations

Stated plainly, so no reader can mistake a modelling choice for a proved property.

## 1. What Stage 5C does not establish

Stage 5C adds **no** claim of incentive compatibility, fairness, Sybil resistance,
selfish-mining resistance, coalition resistance, common-prefix security, chain-quality security
or Bitcoin/PoW-equivalent security. It corrects how the model *accounts* for what it executed.
It does not prove PoCol defeats any behaviour.

## 2. Record-derived amplification is a sensitivity model, not a defence

`entity_record_accounting` measures how much a **naive** accounting scheme could be inflated by
an entity's real subassignment and identity records. Deriving those factors from executed records
rather than requested configuration makes the measurement honest; it does not make the protocol
resistant to anything.

Specifically: counting one real miner plus three `VirtualIdentityRecord`s as four represented
identities is a statement about a hypothetical naive reward scheme, **not** a claim that PoCol
detects, prevents or is robust to identity multiplication. The deduplicated view is the model's
own accounting; nothing here shows it is implementable against a real adversary.

## 3. Virtual identities remain accounting artefacts

`VirtualIdentityRecord`s grant no physical capacity, hold no assignment and hold no lease
(`virtual_identity_physical_capacity_granted` stays 0.0 in every scenario). They exist so identity
count can be reported separately from real miner count. **This is not a Sybil defence.**

## 4. The split factor is one lineage's record count

`actual_split_units` is the number of `SubAssignmentRecord`s in the entity's **widest** range
lineage — the largest split actually executed. An entity splitting different lineages by
different amounts is summarised by its widest, which is a deliberate upper-bound choice for a
sensitivity measurement, not a derived optimum.

## 5. `physical_evaluation_count` is a report, not a protocol quantity

Counting committed physical evaluations happens whether or not the Stage-5 model is enabled,
because it describes work the search core really did. It creates no adversarial action, claim,
reward or penalty, and it changes no protocol decision. A disabled run is still a Stage-4C run in
every respect that affects behaviour; only the *reporting* is now complete.

The residual `abs(counter − evaluation_ledger_nonce_total)` is a genuine cross-check between two
independently maintained quantities — an accumulator advanced at each commit, and the immutable
ledger summed after the fact. It is 0 in every measured scenario, which is a result, not a
definition.

## 6. Replay purity is about repeated invocation, not about time

S5C-3 guarantees that invoking `maybe_false_exhaustion` again with the **same** immutable action
identity changes nothing and returns the same object. It does not claim anything about a miner
that legitimately reaches a *different* frontier later in the round: that is a different action
identity and is evaluated on its merits.

## 7. The audit remains modelled, not implemented

`audit_detection_probability` is a declared parameter deciding whether a claim is caught. No real
verification protocol is specified or implemented. A detection probability of 0 or 1 is an
experimental condition, not a statement about what a deployed system could detect.

## 8. The security floor remains operational only

The floor is an operational active-capacity floor. It is not a security proof, not a bound on
adversarial share, and not a guarantee about chain properties. `q_adv` is reported as NA for any
interval in which the actual active hash rate is zero.

## 9. Energy accounting

The energy-saving mechanism remains **the idle policy within PoCol**. Nonce-domain partitioning
alone is never described as an energy-saving mechanism. The incremental delayed-wake energy
retained from Stage 5B is a **cost**, charged over the realised added waking interval; it is
never reported as a saving.

## 10. Fixed target

Dynamic difficulty remains excluded. No Stage-5 parameter changes the fixed SHA-256 target or
difficulty. Micro-scenarios use `1 << 300` (unreachable) purely to make round outcomes
deterministic for evidence; that is not a claim about realistic difficulty.

## 11. Scenario scale

Every measurement in `STAGE_05C_METRICS.json` comes from small deterministic micro-scenarios
(4 miners, 400-nonce domain — 12 in the split-overflow scenario — short horizons). They are
**not** the confirmatory experiment matrix, carry no statistical power, and support no
inferential claim. Stage 6, preregistration, the confirmatory matrix, statistical analysis and
thesis integration are not begun.
