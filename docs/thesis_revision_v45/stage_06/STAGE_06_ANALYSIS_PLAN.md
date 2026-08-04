# Stage 6 — Frozen Analysis Plan (executed in Stage 8)

Frozen in Stage 6, before any confirmatory seed is executed. No element of this plan may be
changed after the Stage-6 commit — in particular no margin, no outcome priority and no
hypothesis direction (see `STAGE_06_EXCLUSION_RETENTION_POLICY.md`, rule R16).

---

## 1. Inferential unit

**One physical run under one master seed.**

Not a round, not a miner, not a block, not a transaction, and never repeated rows drawn from a
single execution. Round-level and miner-level tables may be archived as secondary data, but they
are **not inferentially independent** and never enter a confirmatory test as units.

With 21 confirmatory scenarios and 30 confirmatory master seeds, Stage 7 produces **630
physical runs**, i.e. 30 independent units per condition.

---

## 2. Estimands

For each preregistered contrast, with treatment `T`, matched control `C`, and master seed `s`:

| quantity | definition |
|---|---|
| **primary estimand** | `mean_s [ Y_T(s) − Y_C(s) ]` — the mean paired difference |
| median paired difference | `median_s [ Y_T(s) − Y_C(s) ]` |
| paired relative difference | `mean_s [ (Y_C(s) − Y_T(s)) / Y_C(s) ] × 100` |
| interval | 95 % paired cluster-bootstrap CI over master seeds |

Both arms of a pair are executed under the **same** master seed, hence the same template seed
and the same adversarial seed, so the difference is within-seed and the pairing is exact.

---

## 3. Methods

| element | frozen value |
|---|---|
| paired test | paired **sign-permutation** at the master-seed level |
| permutations | **10 000** when exact enumeration is unavailable (exact enumeration is used when `2^30` is not required, i.e. never in practice at n = 30 — so 10 000 is the operative value) |
| interval | **cluster bootstrap over master seeds** |
| bootstrap resamples | **10 000** |
| analysis seed | **13165134141831138817** (`SHA256("PoCol-v45-stage8-analysis-0")[:8]`, frozen in `STAGE_06_SEED_REGISTRY.csv`) |
| significance level | 0.05 |

The analysis seed drives every resampling procedure, so the whole analysis is reproducible from
the registry alone.

---

## 4. Multiplicity

Holm correction is applied **within** each family. The families are **never** combined into one
omnibus family.

| family | members |
|---|---|
| **Family 1** | IP-H3; IP-H4; the three IP-H6 adjacent contrasts (0.00→0.10, 0.10→0.25, 0.25→1.00) |
| **Family 2** | IP-H7; IP-H8 |
| **Family 3** | IP-H10a; IP-H10b; IP-H10c; IP-H10d |

Holm is additionally applied **within IP-H6** across its three adjacent contrasts, as specified.

**No p-values at all** are produced for IP-H1, IP-H2, IP-H5 and IP-H9. These are deterministic
validation gates evaluated against exact numeric tolerances:

| gate | tolerance |
|---|---|
| IP-H1 A1 reproduction | ≤ 1e-9 kWh |
| IP-H2 energy identity | ≤ 1e-8 J |
| IP-H2 residency partition | ≤ 1e-9 s |
| IP-H5 equal-power residual | ≤ 1e-9 kWh, every master seed |
| IP-H9 integrity counts | exactly 0 |

---

## 5. Reporting rules

1. **Effect sizes and confidence intervals are reported regardless of significance**, for every
   preregistered contrast, including those that fail.
2. **`p ≥ 0.05` is never interpreted as evidence of equivalence.** Absence of a detected effect
   is reported as absence of a detected effect.
3. **Equivalence and non-inferiority are assessed only against the exact preregistered margins**:
   * IP-H3 equivalence: the *complete* 95 % CI must lie inside ±0.10 % of A1, i.e.
     ±0.0084208333 kWh;
   * IP-H4 minimum relative reduction: **≥ 5 %** — a preregistered minimum, **not** estimated
     from the pilot;
   * IP-H8 non-inferiority: accepted-blocks-per-horizon ratio ≥ 0.95; median-round-duration
     ratio ≤ 1.05; absolute zero-block-rate increase ≤ 0.05.
4. Robust-estimator sensitivity analyses (e.g. median-based, trimmed) are permitted but are
   **labelled secondary** and never replace the preregistered primary estimand.
5. **`q_adv` is NA when `H_active = 0`.** An NA `q_adv` is never imputed and never numerically
   compared.

---

## 6. Conditional claim structure

**An energy success may be claimed only when IP-H7 and IP-H8 both pass.** A significant IP-H4
result accompanied by a failed operational floor (IP-H7) or a failed service non-inferiority
(IP-H8) is reported as *an energy difference that does not support an energy claim*.

Any energy statement is further bounded by:

* it is **conditional** on heterogeneous hash rates and on this configuration — never an
  unconditional PoCol energy-reduction claim;
* the mechanism is **the idle policy within PoCol**; nonce-domain partitioning alone is never
  described as an energy-saving mechanism;
* the comparator is the **matched idle-policy-off control**, never an absolute PoW baseline.

---

## 7. Incentive and adversarial quantities

Incentive quantities are **secondary exploratory** in Stage 7 and are **never** primary
confirmatory endpoints. IP-H10a–d report **bounded experimental effects of modeled behaviours**;
they are **not** evidence of attack resistance, incentive compatibility, fairness, Sybil
resistance, selfish-mining resistance, coalition resistance, common-prefix security or
chain-quality security.

---

## 8. Analysis inputs

The analysis consumes exactly one row per physical run, in the confirmatory output schema
defined in `STAGE_06_STAGE7_EXECUTION_PLAN.md` §5. Runs with `run_status != "COMPLETED"` are
retained as failed runs and are excluded from estimation **only** by the failure rules in
`STAGE_06_EXCLUSION_RETENTION_POLICY.md` — never by any outcome-based criterion.
