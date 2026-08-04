# Stage 6 — Runtime and Archive Plan

Grounded in the **3 completed** Tier-2 full-scale records, the **1 right-censored** record, and a measured compression benchmark. Stage 7 must re-check these figures against its own first chunk before committing to the full sweep.

> **Projected per scenario cost class, never from one global average.** The three classes below differ by more than an order of magnitude in runtime and by more than three orders of magnitude in output size; averaging them would misstate both the compute requirement and the archive requirement.

---

## 1. Scenario cost classes

The class of a scenario follows from its own frozen matrix row — it is derived, not assigned by hand:

```
SECURITY_FLOOR   security_floor_policy != DISABLED
REASSIGNMENT     security_floor_policy == DISABLED and fault_schedule != NONE
LIGHTWEIGHT      neither
```

| class | scenarios | count | Stage-7 runs | measured by | why it costs what it does |
|---|---|---:|---:|---|---|
| **LIGHTWEIGHT** | A01, A02, A03, A04, A05, A06, B01, C01, C06 | 9 | 270 | A03, A05 | no floor evaluation and no reconciliation tables |
| **SECURITY_FLOOR** | B02, B03, B04 | 3 | 90 | **not measured** | `EvaluateSecurityFloor` walks the run-lifetime `reserve_records` map on every capacity change — O(rounds^2) |
| **REASSIGNMENT** | C02, C03, C04, C05, D00, D01, D02, D03, D04, D04C | 10 | 300 | C04 | revoked leases populate `entity_reconciliation` and `ownership_reconciliation`, which dominate the serialised output |

Total: 22 confirmatory scenarios x 30 seeds = **660** Stage-7 physical runs.

### 1.1 Unbenchmarked scenarios and their declared scheduling status

Only 4 of 22 scenarios were executed at full scale. Every other scenario inherits its class figures as a **lower bound**, never as an upper bound, and is scheduled at the worst measured class. `C06` is called out explicitly because it is the case where the gap is largest:

| scenario | class | `runtime_bound_status` | `timeout_class` | `memory_class` |
|---|---|---|---|---|
| `C06` | LIGHTWEIGHT | **`LOWER_BOUND_ONLY`** | **`SLOWEST_MEASURED_CLASS`** | **`SLOWEST_MEASURED_CLASS`** |
| every other unbenchmarked scenario (17) | its own | `LOWER_BOUND_ONLY` | `SLOWEST_MEASURED_CLASS` | `SLOWEST_MEASURED_CLASS` |
| the 4 measured scenarios | its own | `MEASURED` | its own class | its own class |

`C06` is the declared unreachable-target integrity condition: every round exhausts the whole nonce domain without finding a block, so its per-round hashing work is the maximum the model admits. It classifies as LIGHTWEIGHT only because its *policy fields* are lightweight, and it was not one of the four Tier-2 runs. Treating its runtime as bounded above by the LIGHTWEIGHT figure would be an unmeasured assumption, so it is not made.

## 1.2 Tier-2 completion status under the governance amendment

| category | count |
|---|---:|
| Tier-2 completed runs | **3** |
| Tier-2 right-censored runs | **1** |
| Tier-2 failed runs | **0** |

**Tier-2 feasibility evidence sufficient for preregistration freeze; final security-floor runtime and resource sizing deferred to the mandatory Stage-7 resource preflight.**

Governance reason, recorded exactly: the remaining B02 run required approximately 9-10 additional wall-clock hours and Stage 6 was closed under an explicit user-authorised time constraint — **not** because of any effect direction or magnitude. No effect was observed from the partial run and none is inferred.

### B02 — `RIGHT_CENSORED_TERMINATED_BEFORE_COMPLETION_AT_STAGE6_FREEZE`

| quantity | value | interpretation |
|---|---:|---|
| elapsed wall | 22,459 s | **LOWER_BOUND** |
| CPU seconds | 21,757 s | **LOWER_BOUND** |
| CPU / wall | 0.969 | measured |
| VmHWM | 2,550 MB | **LOWER_BOUND** |
| simulated time | 5,797 of 10,000 s (58.0 %) | **LOWER_BOUND** |
| output bytes | NEVER_WRITTEN | no output was written |
| config SHA-256 | `4fda6ee86d4c97d0b19531ce2de998b7...` | preserved |
| master seed | `13251983728229268948` | preserved, **not** redrawn |

*The closeout directive anticipated a STILL-RUNNING process and specified the status RIGHT_CENSORED_RUNNING_AT_STAGE6_FREEZE. That is not what happened: PID 12496 terminated at approximately 13:19 UTC, about 75 minutes BEFORE the closeout instruction was issued, without writing a completion line to its log and without writing a checkpoint. Recording it as 'running' would be false, so the status records termination. Every censoring interpretation below applies unchanged, and more strongly.*

**Termination cause: `UNDETERMINED_INFRASTRUCTURE`.** no completion line in the execution log; no checkpoint written; VmHWM 2,549 MB against 15.7 GB total with 14.6 GB free at the time of discovery, so an out-of-memory kill is not supported by the evidence; no OOM record in dmesg; the external sampler stopped at sample 191 when /proc/12496 disappeared. Consistent with harness-level reaping of the background process group, but NOT positively established.

Rerun policy: preregistered same-seed infrastructure rerun: the identical (scenario_id, master_seed) pair and identical frozen configuration are retried on the Stage-7 host. NO replacement seed is drawn and the seed registry is not extended.

Scientific use: NONE — no treatment effect, no energy quantity, no integrity-gate result and no hypothesis outcome is inferred from this partial run.

The class projections below therefore **cannot be closed for the SECURITY_FLOOR class**, whose only representative is censored. Every SECURITY_FLOOR figure that would depend on it is reported as `LOWER_BOUND` or omitted, never as a completed measurement. The Tier-1 figures do not substitute: the confirmatory scale is roughly twelve times the population and fifty times the horizon.

### Lower-bound resource sizing for the SECURITY_FLOOR class

| quantity | value | basis |
|---|---:|---|
| runtime `LOWER_BOUND` | 6.24 h | observed before censoring |
| runtime `ESTIMATED` (quadratic fit) | ~18.6 h | **ESTIMATED**, not measured |
| peak memory `LOWER_BOUND` | 2,550 MB | observed before censoring |
| peak memory `ESTIMATED` for sizing | ~4,398 MB | **ESTIMATED**, linear in simulated fraction |
| output bytes | unknown | never written |

Stage 7 must not size the SECURITY_FLOOR class from these numbers without first passing the resource preflight, which requires either the completed B02 run or an equivalent full-scale security-floor preflight on the real host.

