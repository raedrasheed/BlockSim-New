# Stage 7 — Resource Preflight Gate (BINDING)

**This gate is a hard precondition on Stage-7 execution.** No confirmatory master seed may be
executed — not one, not a "warm-up", not a "smoke test" against a confirmatory seed — until a
real persistent host has been recorded in §2 below and every verification in §3 has passed on
that recorded host.

The gate exists because Stage 6 measured the cost of the frozen sweep and found that the only
execution host available to it **cannot** carry that sweep. Recording that fact, rather than
discovering it partway through Stage 7, is the point.

---

## 1. Separation of concerns

| statement | meaning |
|---|---|
| `STAGE_6_PREREGISTRATION_COMPLETE` | the pilot ran, the design is frozen, every scientific and validation gate passed |
| `STAGE_7_RESOURCE_PREFLIGHT_NOT_YET_PASSED` | no verified persistent execution host is on record |

These are **independent**. Stage 6 is pilot and preregistration; Stage 7 is frozen execution.
The absence of a provisioned host does not invalidate a preregistration — a preregistration is a
commitment made *before* execution, and it is complete when the commitment is complete.

Equally, a complete preregistration is **not** permission to execute. Stage-7 execution is
authorised only by a passed preflight recorded here.

---

## 2. The preflight record

Every field is mandatory. A field that cannot be filled from a **verified** observation of the
host makes the preflight FAIL. No field may be filled from an assumption, a quotation, a
marketing figure or an intention to provision.

| # | field | value | how verified |
|---:|---|---|---|
| 1 | host identifier | *(unfilled)* | |
| 2 | availability / lifetime guarantee | *(unfilled)* | |
| 3 | CPU cores | *(unfilled)* | |
| 4 | usable RAM | *(unfilled)* | |
| 5 | free disk | *(unfilled)* | |
| 6 | archive destination | *(unfilled)* | |
| 7 | network / durable-storage path | *(unfilled)* | |
| 8 | per-class worker limits | *(unfilled)* | |
| 9 | streaming-compression command | *(unfilled)* | |
| 10 | compression runtime / memory benchmark | *(unfilled)* | |
| 11 | heartbeat command | *(unfilled)* | |
| 12 | checkpoint policy | *(unfilled)* | |
| 13 | per-run timeout | *(unfilled)* | |
| 14 | same-seed infrastructure-rerun policy | *(unfilled)* | |

**Status: `STAGE_7_RESOURCE_PREFLIGHT_NOT_YET_PASSED`.** The table is unfilled because no
persistent host has been identified. Stage 6 does not fabricate one.

---

## 3. Verifications the preflight must pass

All three are numeric and must be evaluated against the **recorded** host, not against a
reference machine.

### V1 — memory

```
usable_RAM  >=  1.25 x SUM_c ( n_c x peak_rss_c )
```

over the planned concurrent worker set `{n_c}`, using the per-class `peak_rss_c` measured in the
Tier-2 pilot and recorded in `STAGE_06_RUNTIME_AND_ARCHIVE_PLAN.md` §2. Core count alone is
**not** an acceptable basis for declaring worker capacity.

### V2 — disk

Free disk plus temporary headroom must be sufficient for the **tested streaming compression
path** — the one recorded in field 9, benchmarked in field 10 — not for an untested one, and not
for a raw-first path unless the raw-first working set has itself been shown to fit.

### V3 — lifetime

```
host_lifetime_guarantee  >=  1.25 x projected_resource_aware_execution_duration
```

where the projected duration is computed per scenario cost class under the worker limits in
field 8, never from a single global average.

**If any of V1, V2 or V3 fails, or if any field in §2 is unfilled, no Stage-7 run may begin.**

---

## 4. The current environment is NOT APPROVED

| item | measured value |
|---|---|
| host | ephemeral session container (Stage-6 locked environment) |
| CPU cores | 4 |
| total RAM | 15.7 GB (12.56 GB usable at the declared 0.80 fraction) |
| free disk | 11.6 GB |
| lifetime guarantee | **none** — reclaimed after inactivity or at session end |

**`NOT APPROVED FOR STAGE-7 FROZEN EXECUTION`**

Reason: its guaranteed lifetime is shorter than the projected execution window. V3 fails
outright — the guarantee is not merely too short, it is absent. V1 also constrains it to a
single worst-case heavy worker, and V2 passes only because compress-on-write is mandatory in
this plan.

This environment remains fully approved for what it was used for: Stage-6 pilot execution on
pilot seeds, preregistration, validation and freeze. Nothing about this record retracts the
Stage-6 result.

---

## 5. What must happen before Stage 7 begins

1. Provision or identify a persistent host.
2. Fill every field in §2 from direct observation of that host.
3. Run the compression benchmark (`benchmark_compression.py`) **on that host** and record
   field 10 from its output — throughput, CPU, peak memory and the streaming verdict are
   host-specific.
4. Evaluate V1, V2 and V3 numerically and record the results.
5. Record the outcome as `STAGE_7_RESOURCE_PREFLIGHT_PASSED` together with the host record.
6. Only then execute the first confirmatory seed.

Until step 5 is recorded, the standing state is
**`STAGE_7_RESOURCE_PREFLIGHT_NOT_YET_PASSED`** and
**`STAGE_7_EXECUTION_REMAINS_UNAUTHORIZED`**.
