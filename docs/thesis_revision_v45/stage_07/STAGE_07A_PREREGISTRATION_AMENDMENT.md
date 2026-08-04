# Stage 7A — Pre-execution preregistration amendment: logical rows vs physical executions

**Recorded before any confirmatory run executed.** No confirmatory master seed has been
executed at the time of this amendment, so nothing here is informed by any result.

Parent: `0725f068f73dda49c4264200d3591bcc86dd6033`

## 1. The precise frozen interpretation

The frozen design is unchanged. What changes is only how its execution is counted:

| quantity | value |
|---|---:|
| logical scenarios | **22** |
| confirmatory master seeds | **30** |
| logical scenario-seed rows | **660** |
| **unique physical executions** | **630** |
| **A05/B01 alias pairs** | **30** |

`A05` and `B01` have **byte-identical executable configurations**. Under a shared master seed
they denote one physical execution, because the accepted engine is deterministic given the
configuration and the derived child seeds. They differ only in `block_id`, `hypothesis_ids`,
`notes` and `paired_control_id` — that is, in their *roles*, not in what they compute.

Any earlier statement of "21 scenarios / 630 runs" is superseded. The correct reading is
**22 logical scenarios, 660 logical scenario-seed rows, 630 unique physical executions**. The
630 figure is not a reduced matrix; it is the count of distinct computations behind the
unchanged 660 rows.

## 2. Physical execution identity

```
physical_execution_id = "P-" + sha256( config_digest | master_seed | engine_commit )[:24]
```

Emitted by `build_physical_registry.py` into two artefacts on the durable path:

* `physical_execution_registry.csv` — 630 rows, each with its executor run, cost class and the
  logical run ids it serves;
* `logical_to_physical_alias.csv` — 660 rows, each marked `EXECUTED` or
  `MATERIALISED_FROM_SHARED_PHYSICAL_EXECUTION`.

## 3. Execution and materialisation rule

Each `physical_execution_id` is executed **exactly once**, by a deterministic executor run
(the lexicographically first member of its alias group). Both logical rows are then
materialised from **the same verified output and the same checksum**. Neither A05 nor B01 is
deleted, and the redundant configuration is never executed twice.

Every logical row carries:

* `physical_execution_id`
* `shared_physical_execution` — `true` for the 60 alias rows, `false` otherwise
* `alias_group_id` — `ALIAS-A05+B01` for the 30 shared groups
* `materialised_from_run_id` — which executor produced the observation

## 4. Binding instruction to the Stage-8 analysis

The inferential unit remains **one physical run under one master seed**. Therefore:

1. The shared observation **may** be used in each of the separate contrasts it belongs to —
   A05 within the idle-policy contrast against A03, B01 as the floor-disabled control — because
   those are different comparisons.
2. A05 and B01 **must never be pooled** as two independent physical observations.
3. They **must never be counted twice** in a single inferential sample, in a permutation null,
   in a bootstrap resample, or in any multiplicity family's effective sample size.
4. Provenance **must be retained** in every derived table: one physical execution serving two
   logical roles is a fact about the data and must remain visible in it.

A cluster bootstrap or sign-permutation over master seeds must resample **physical executions**,
not logical rows, wherever A05 and B01 both enter the same computation.

## 5. What is not changed

The engine, `search.py`, configuration semantics, hypotheses, primary and secondary outcomes,
scenario definitions, fault schedules, master seeds, pair definitions, multiplicity families,
equivalence and non-inferiority margins, hypothesis directions, the analysis method, the fixed
target and the fixed difficulty are all unchanged.

The algorithm remains **PoCol**. The energy-saving mechanism remains **the idle policy within
PoCol**. Nonce-domain partitioning alone is not an energy-saving mechanism.
