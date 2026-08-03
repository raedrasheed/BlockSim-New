# Stage 5 — Known Limitations

This document states, without hedging, what the Stage-5 adversarial and incentive model cannot
support. It should be read before any Stage-5 figure is cited anywhere.

---

## 1. Claims Stage 5 does not make

Stage 5 **models** bounded behaviours and **measures** outcomes. It does **not** establish:

| Property | Status |
|---|---|
| Incentive compatibility | **Not established.** Behaviours are declared in configuration, never chosen in response to payoffs. No equilibrium concept is modeled. |
| Fairness | **Not established.** No fairness metric is defined, computed or asserted. |
| Sybil resistance | **Not established.** The S5-8 measurement shows what a deduplication rule removes from a *reward ledger*, nothing about identity acquisition. |
| Selfish-mining resistance | **Not established** — and measured *failing*: withholding denies liveness entirely (scenario G, 0 blocks vs 29). |
| Coalition resistance | **Not established.** Coalitions can be declared; no resistance property is derived. |
| Common-prefix security | **Not established.** No fork-choice or chain-growth analysis exists. |
| Chain-quality security | **Not established.** No chain-quality metric is computed. |
| Bitcoin- or PoW-equivalent security | **Not established.** No comparison to any deployed protocol's security model exists. |

Stage 5 does not show that PoCol *defeats* any modeled behaviour. Where an attack succeeds, the
model records that it succeeded.

## 2. The audit is an assumption, not a mechanism

`audit_detection_probability` is a **model parameter**. Setting it to 1.0 does not mean PoCol
can detect false claims; it means the scenario *assumes* detection. There is no cryptographic or
protocol-level verification behind it.

Every result conditioned on detection is conditioned on that assumption. In particular, scenario
E (all 90 false claims caught, zero coverage gap) is a property of the assumed parameter, not of
PoCol. Scenario F — the same behaviour with detection off — leaves **3,000 nonces unsearched and
charges no penalty**. An undetected liar pays nothing.

Whether such detection is achievable in a real deployment is **out of scope and unaddressed**.

## 3. Behaviours are declared, not chosen

No miner in this simulator responds to incentives. Behaviour sets are fixed in the configuration
before the run and are immutable for the round. Consequences:

- no best-response, equilibrium or deviation-profitability conclusion can be drawn;
- the ledger's net figures describe *what a declared behaviour earned*, never *what a rational
  agent would do*;
- adaptive, learning and reactive adversaries are entirely unmodeled.

## 4. Coverage of the adversarial space

Modeled: free riding, hash-rate misreporting, assignment splitting, progress withholding, false
exhaustion, solution withholding, delayed wake, out-of-range actions, idle-policy defection.

**Not** modeled: network-level attacks (eclipse, partition, delay), message forgery or
signature-level attacks, timing/side-channel attacks, collusion protocols between entities,
bribery, adaptive strategies, and any attack on the underlying SHA-256 primitive. Absence of a
behaviour from this list is not evidence that PoCol resists it — it means it was not modeled.

## 5. The micro-scenarios are not experiments

The twelve scenarios in `STAGE_05_ADVERSARIAL_INCENTIVE_METRICS.json` are single deterministic
runs at N = 4 miners over a 400-nonce domain and a short horizon. They exist to demonstrate that
the executable paths work.

They are **not** samples, carry **no** confidence intervals, and support **no** statistical
claim. The confirmatory experiment matrix has not been executed and is out of scope for
Stage 5. Any Stage-5 number cited elsewhere must be labelled a demonstration measurement.

## 6. Energy findings must not be inverted

The matched pair records the attacked arm using **less** energy than the honest baseline
(−0.000278 kWh). This is **not** a saving. Energy fell because withholding miners stop hashing
and drop to low power while the protocol produces **no blocks at all**. Spending less to deliver
nothing is a liveness failure.

The energy-saving mechanism in PoCol remains **the idle policy within PoCol**, evaluated under
the accepted matched-control identity experiment. Nonce-domain partitioning alone is **not** an
energy-saving mechanism. Delaying a wake costs energy (S5-16 measures wake energy strictly
increasing); it never saves it.

## 7. `q_adv` is composition, not a security threshold

`q_adv(t)` measures the adversarial share of **actual active hash rate**. It is a descriptive
statistic.

- Crossing `q_adv_threshold` implies **nothing** about safety. The threshold exists only to
  report a duration-above figure; it is not a security bound.
- When `H_active(t) = 0` the ratio is undefined and reported **NA**. NA intervals are excluded
  from the time-weighted mean and the above-threshold duration. Every measured scenario has a
  non-zero NA duration, so any external tool consuming these fields must handle `None` and must
  not coerce it to 0.0.
- The security floor remains the **operational active-capacity floor only**. `q_adv` is not part
  of it and does not extend it.

## 8. Accounting scope of the deduplication result

The naive-vs-deduplicated gap (4.00× in scenario L, 3.73× in scenario K) is an **accounting**
measurement over the reward ledger under one arbitrary parameterisation. It does not bound an
adversary's identity count, assignment influence, or consensus weight, and it is not a defence.
Both views are reported so the exposure remains visible.

The ratio is also **not** a general constant: it depends entirely on how much of the network's
work the declaring entity performs. Amplification applies only to the entity that declares the
identities or the split, so an entity doing a small share of the work produces a small aggregate
ratio even with a large per-entity factor — exactly why scenario K's aggregate (3.73×) sits well
below that entity's own 12× factor.

## 9. Parameterisation is arbitrary

Every rate, probability, delay, fraction and multiplier used in Stage 5 was chosen to exercise
code paths deterministically. None is calibrated against any deployment, and none is claimed
optimal. Different values would produce different figures and could reverse apparent orderings
between honest and adversarial entities.

## 10. Scope boundary

Stage 5 does not begin Stage 6, preregistration, large-scale experiment execution, statistical
analysis or thesis integration. It modifies no Stage-1 document, no protected DOCX/PDF, and no
prior-stage evidence. The accepted Stage-2B search core is byte-identical to the frozen
Stage-4C baseline.
