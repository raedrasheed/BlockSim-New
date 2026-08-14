# STAGE 8Y — LIMITATIONS

These qualify **every** quantitative statement in `STAGE_8Y_RESULTS_REPORT.md`.
Read this before quoting any number.

---

## 1. Simulation is not physical ASIC experimentation

No physical device was measured. Stage 8Y is a discrete-event model with an
analytically exact hashing abstraction. Nothing here establishes that any Antminer
behaves as modelled.

## 2. Nominal specifications may differ from field behaviour

Bitmain publishes these as *typical* values: hash rate ±3 %, power on wall and
efficiency on wall ±5 % at 25 ℃. Stage 8Y uses nominal figures with **no stochastic
device variation**. A ±5 % power tolerance is of the same order as some of the effects
measured here. Additionally, the S21 Pro and S19 XP numeric tables could not be
retrieved from this sandbox (`support.bitmain.com` returns HTTP 403); their official
URLs are recorded and they are flagged `url_located_content_not_retrievable`. Only the
S19j Pro 104T figures were quoted from official page content. **The two unverified
device rows must be confirmed against the official pages before publication.**

## 3. α values are sensitivity assumptions, not vendor modes

No manufacturer publishes an idle, standby or low-power operating state for any
registry device, so **no device-specific parked figure was invented**. All parked
power is `P_low = α·P_active` with α ∈ {0, 0.05, 0.10, 0.25, 0.50}. Verbatim: *these
values are model-based sensitivity assumptions and are not manufacturer-certified
Antminer low-power operating modes.* α = 0 is an idealized theoretical lower bound,
not a physically validated state. `LOW_POWER` and `STANDBY` are priced identically
because no data distinguishes them.

## 4. The wake model is model-based

No manufacturer wake-power curve exists. Stage 8Y takes the conservative option — a
waking miner draws full active power and performs no hashing — and sweeps
`t_wake ∈ {0,1,5,10,30} s`. Real transitions may involve ramp-up to full hash rate,
firmware delays and thermal re-stabilisation that are not modelled at all.

## 5. Temperature and thermal inertia are not modelled

There is no thermal state, no warm-up, no throttling and no ambient dependence.
Repeated park/wake cycling of real hardware has thermal consequences that this model
cannot represent.

## 6. DVFS and firmware effects are not modelled

There is no dynamic voltage/frequency scaling, no per-board tuning, no
underclocking/overclocking curve. In practice a miner might reduce power *without*
stopping, which is a different mechanism from the binary park modelled here — and
possibly a more attractive one.

## 7. Pool-level scheduling overhead is not modelled

The coordinator that computes the active set, distributes disjoint ranges and issues
refreshed templates is assumed free of computation, bandwidth and latency cost beyond
the modelled template propagation. A real deployment would pay for it.

## 8. Network propagation remains abstract

Gossip delay is `Exp(mean 0.42 s)` broadcast to all peers, with no topology, no
bandwidth limit, no verification cost and no partition behaviour. Stale blocks were
consequently rare in every configuration.

## 9. Energy-aware selection has fairness implications

Selection is by efficiency, which correlates perfectly with hardware generation.
Under P3 in composition H4, **all 150 S19j Pro units are permanently excluded**:
participation share 0.000, reward share 0.000, selection frequency 0.000, with a Gini
coefficient of 0.53 over active time and 159 of 300 miners never active at all. This
is not a side note; it is a direct consequence of the mechanism that produces the
energy saving.

## 10. Repeatedly selecting high-efficiency miners concentrates rewards

Reward share follows participation: under P3/H4 the S21 Pro and S19 XP classes take
100 % of block rewards. A deployed system would need rotation, compensation or a
fairness constraint, none of which is modelled or evaluated here. P4 partially
mitigates this (Gini 0.107, no permanently excluded miner) at the cost of a lower
saving.

## 11. Reserve miners experience reduced participation opportunity

Under the frozen P4 schedule a reserve is idle until the round is already 300 s old,
so its expected revenue is structurally lower than an always-active miner's. The
economic acceptability of that arrangement is not evaluated.

## 12–14. Security implications of reduced active hash rate

Under the confirmatory P3 setting the **time-average active hash fraction is ~0.60**,
so at any moment roughly 40 % of installed capacity is parked and the instantaneous
cost of out-hashing the live network is correspondingly lower. Worse, because
hash-proportional slots make every active miner finish simultaneously, the **minimum
instantaneous active hash fraction is 0.0** for every PoCol policy during the gap
between domain exhaustion and receipt of the refreshed common template; traditional
PoW never leaves 1.0. Parked capacity is *available* to an honest network but it is
not *hashing*, and a parked fleet is also a fleet an attacker could rent.

**Block-retention parity does not mean security is unchanged**, and no such claim is
made anywhere in this experiment. The energy–security trade-off is reported as a
separate axis, not folded into the energy result.

## 15. Static ASIC populations do not represent network churn

The population is fixed for the horizon. Real networks see continuous entry, exit,
hardware replacement and hash-rate migration, none of which is modelled.

## 16. An optimised hardware mixture is not evidence about real networks

H0–H4 are constructed compositions. H4's shares were fixed on a turnover argument
before execution and were not tuned toward the threshold, but no claim is made that
any real network has this mixture. The composition sweep is reported in full so the
dependence of the result on the mixture is visible.

## 17. A > 50 % result under idealized α is not physical evidence

> 50 % saving was reached only at α = 0 (6 configurations) and α = 0.05 (3
configurations), and never at α ≥ 0.10. The α = 0 case is an idealized lower bound.
The α = 0.05 case assumes a parked ASIC draws 5 % of active power — 176 W for an S21
Pro — which is an assumption, not a measurement. **Neither constitutes hardware
evidence.**

## 18. Most of the saving comes from reducing hash participation

The mandatory decomposition is explicit: at α = 0.10, **74.7 % (H2) and 77.2 % (H4)**
of the P3 saving is attributable to reduced hash participation and only **25.3 % /
22.8 %** to preferential selection of efficient ASICs; at H0 the selection share is
exactly 0.000. Stated plainly: *most of the measured energy reduction is PoCol doing
less hashing, not PoCol hashing more cleverly.*

## 19. The experiment does not establish economic profitability

There is no coin price, block reward, fee market, hardware capital cost, electricity
price or miner entry/exit. Nothing here says whether any of this would pay.

## 20. The experiment does not prove mainnet deployability

Coordinator trust, template agreement, verification of disjointness, resistance to
miners that ignore their assignment, and the incentive compatibility of parking are
all outside the model.

## 21. Additional limitations identified during execution

* **Latency degrades far beyond the preregistered bound.** The median-interval ratio
  is 1.79 (P3) and 1.85 (P4) against a 1.10 criterion. Any energy saving here is
  bought with a large latency penalty.
* **The winner-oracle abstraction is exact in law, not in bytes.** Acceptance is an
  i.i.d. Bernoulli(q) field over candidate indices, validated against real double
  SHA-256 at a tractable target in the Stage 8X suite. It does not exercise SHA-256
  at operational scale.
* **P3's active set is selected once and held for the horizon.** No rotation is
  modelled, which maximises both the measured saving and the measured unfairness.
* **The horizon is short relative to the block interval** (≈ 17 blocks per 10 000 s
  run), so per-run block counts are coarse; this is why the long-horizon set at
  100 000 s exists, and it confirms the short-horizon savings to within 0.4 pp for P3.
* **Stage 8Y's PoCol block rate depends on the epoch/template-refresh design.** A
  PoCol implementation that pipelined the next epoch's allocation would change both
  the parked time and the block rate, and is not evaluated.
