# Stage 6 — Pilot Plan

The pilot exists to establish **feasibility**, nothing else. It is executed with **pilot master
seeds only**, drawn from a registry provably disjoint from the confirmatory registry.

Harness: `experiments/thesis_revision_v45/stage_06/run_pilot.py`
Plan: `experiments/thesis_revision_v45/stage_06/pilot/pilot_matrix.csv`
Results: `experiments/thesis_revision_v45/stage_06/pilot/pilot_results.json`
Log: `experiments/thesis_revision_v45/stage_06/pilot/pilot_run_log.txt`

---

## 1. Permitted and forbidden uses

**The pilot may be used only for:** runtime estimation; memory estimation; event-count
estimation; detecting configuration errors; detecting execution failures; checking zero-block
and NA feasibility; validating that expected fields exist; validating that all integrity gates
are computable.

**The pilot must never be used to:** select a favourable hypothesis direction; select factor
levels because they produced larger savings; remove scenarios because their effects were small;
estimate or report confirmatory p-values; make thesis claims; choose an attack because it looked
most damaging; replace confirmatory runs; change the target or the difficulty.

The harness enforces this by construction: it records no condition-specific energy saving, no
effect estimate, no p-value, no confidence interval and no ranking of conditions by effect. The
only energy quantities it retains are the deterministic IP-H1/IP-H2/IP-H5 accounting residuals,
which are integrity gates with fixed numeric tolerances, not effects.

---

## 2. Tier 1 — reduced-scale semantic pilot

| parameter | value |
|---|---|
| `num_miners` | 12 |
| `horizon_T` | 200 s |
| `nonce_domain_size` | 400 |
| `batch_size` | 25 |
| scenarios | **all 21** frozen confirmatory scenario types |
| pilot seeds per scenario | **2** (seed indices 0 and 1) |
| total runs | **42** |

Tier 1 is a **configuration validator**, not a scaled-down experiment. Its purposes:

* configuration validation — every frozen row constructs and executes;
* field availability — every preregistered outcome is present in the accepted schema;
* zero-block and NA feasibility;
* integrity-gate availability — all nine IP-H9 gates are computable on every row;
* event-lifecycle validation — leases, reassignments (Path A and Path B), reserve activations
  and adversarial behaviours actually occur where the matrix says they do;
* failure detection.

---

## 3. Tier 2 — full-scale runtime pilot

| parameter | value |
|---|---|
| `num_miners` | 141 |
| `horizon_T` | 10000 s |
| `nonce_domain_size` | 4000 |
| `difficulty` | 1000 |
| `batch_size` | 50 |
| scenarios | **4** representative configurations |
| pilot seeds | **1 each** (seed indices 4, 5, 6, 7 — disjoint from Tier-1 usage) |
| total runs | **4** |

| scenario | why it is representative |
|---|---|
| **A03** | heterogeneous control (idle policy off) — the IP-H4/IP-H6 control arm |
| **A05** | heterogeneous idle policy at the reference ratio — the IP-H4 treatment arm |
| **B02** | security floor with minimum-cardinality reserve activation — the heaviest Stage-3 path |
| **C04** | genuine Path-B reassignment via Stage-3 reserve wake — the heaviest Stage-4 path |

Purposes: wall-clock runtime; peak memory; output size; event count; expected archive size; and
the Stage-7 chunking and parallelisation plan.

---

## 4. What the pilot report may and may not contain

**May contain only:** runtime; peak memory; output bytes; event count; round count; zero-block
count; NA count by field; exception count; integrity-gate failures; configuration feasibility;
whether the run completed.

**Must not contain:** condition-specific mean energy savings; inferential effect estimates;
p-values; confidence intervals; any ranking of conditions by energy effect; claims about which
hypothesis passed; recommendations based on effect direction.

---

## 5. Stop condition

If a pilot scenario cannot execute because the accepted engine lacks a required configuration
path, Stage 6 **stops**. The engine is not edited. The stage returns
`STAGE_6_PREREGISTRATION_BLOCKED` naming the exact scenario, the stack trace, the missing
capability and the minimum correction.

---

## 6. Calibration is permitted; tuning is not

Adjusting a configuration so that a declared scenario **executes the behaviour it is named
for** is configuration validation, explicitly within the pilot's remit ("detecting
configuration errors"). Adjusting a configuration because it produced a **larger or more
favourable outcome** is forbidden.

Every calibration performed in this stage is recorded in `STAGE_06_DECISION_LOG.md` with the
measurement that motivated it, so the distinction is auditable rather than asserted. No
calibration in this stage consulted an energy value, a service value, an effect size or a
direction of difference.
