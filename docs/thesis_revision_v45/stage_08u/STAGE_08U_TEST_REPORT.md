# Stage 8U — Test Report (COMMIT 1)

**Suites executed locally (no CI created or waited for):**

* `tests/thesis_revision_v45/stage2/` + `stage_08r/` + `stage_08s/`: **235 passed** —
  every previously accepted test retained, unmodified, after the Stage-8U engine
  additions (the additive mode is inert unless selected).
* `tests/thesis_revision_v45/stage_08u/test_stage8u_controller.py`: **22 passed**
  (U-TEST-01..22).

Executed seeds: the fresh Stage-8U PILOT seed `SHA256("PoCol-v45-stage8u-pilot-0")`
(first 8 bytes, big-endian), plus — in U-TEST-01 only, as directed — the frozen
historical Stage-6M/8R/8S seeds solely to REPRODUCE their frozen records.  No
confirmatory Stage-8U seed exists yet (derived and frozen at COMMIT 2).

| test | requirement | evidence |
|---|---|---|
| U-TEST-01 | every historical controller reproduces its frozen record | LEGACY_REACTIVE == frozen M03 JSON (blocks, energy bit-exact, below-floor); STAGE8R_PREDICTIVE_STATIC_FLOOR == frozen R02 CSV row; USEFUL_FLOOR_COARSE_REASSIGNMENT == frozen S03 CSV row (rounds 212, blocks 177, energy to 1 ULP, coarse count 305, below-useful to 1e-9); 8U counters zero there |
| U-TEST-02 | PoW/PoCol share target, difficulty, horizon, template seed, hash primitive | `MP.make_template is SEARCH.make_template`; template stream `tpl-round-k` identical for k=1..3; fixed target equality; horizon/batch/domain equality |
| U-TEST-03 | PoW overlap measurable | duplicates > 0 in W00 and W01; per-round and aggregate total == unique + duplicate; unique ≤ domain |
| U-TEST-04 | PoW post-round evaluations zero | recorded field == 0; per-round per-miner causal bound n ≤ rate × window |
| U-TEST-05 | PoW energy/residency reconcile | identity residual ≤ 1e-8 J (observed 1.5e-11), residency residual exactly 0; closed-form totals match to 1e-12 relative |
| U-TEST-06 | ≤ 1 handoff epoch per round | 96 epochs across 96 distinct rounds; registry bijection |
| U-TEST-07 | second attempt = replay no-op | 1 564 duplicate-prevented replays, zero phantom epochs |
| U-TEST-08 | receiver selection deterministic | fastest wins; tie → smaller MinerID; live reassignment excludes |
| U-TEST-09 | donor selection deterministic | largest suffix wins; deterministic MinerID tie-break; < 2 batches never selected |
| U-TEST-10 | chunks contiguous/disjoint/union exact | donor+receiver chunks partition the original suffix exactly; both ≥ 1 batch; donor never evaluated inside the ceded chunk (ledger cross-check) |
| U-TEST-11 | rate-proportional sizing | independent reimplementation of the apportionment+clamp reproduces every committed chunk size |
| U-TEST-12 | predicted makespan strictly improves | committed: after < before; cancelled: after ≥ before; zero FAILED |
| U-TEST-13 | no rewind | physical_frontier_rewind_count == 0 |
| U-TEST-14 | duplicates zero (honest PoCol) | duplicate_nonce_count == 0; per-round ledger intervals pairwise disjoint |
| U-TEST-15 | ≤ 1 reserve wake per round | per-round request count ≤ 1; every request registered in the U4 lifecycle set; seated counter equals request count |
| U-TEST-16 | reserve rejected when awake receiver available | unit fixture: reason `awake_receiver_available`, counter incremented |
| U-TEST-17 | reserve rejected when useful window too short | 0.8 s window ≤ 1.0 s wake + 0.25 s batch → rejected; long window admits; missing slice → `no_bound_useful_work` |
| U-TEST-18 | closure leaves zero live records | all epochs terminal with terminal_time; episodes/batches/requests terminal; live-receiver and per-round fallback registries empty; zero post-round records |
| U-TEST-19 | target/difficulty fixed everywhere | every controller mode (incl. the new one) and both PoW controls: difficulty 1000, identical fixed target, domain 1600 |
| U-TEST-20 | energy-price invariance | doubling all power values: identical blocks/rounds/epochs/evaluations, energy exactly ×2 (PoCol and PoW) |
| U-TEST-21 | all comparison fields present | 17 PoCol-side fields + 22 PoW-side fields incl. `consensus_label == "matched same-template PoW control"`; first-valid-solution schema exact |
| U-TEST-22 | byte-identical tables + deterministic figure metadata | serialisation byte-equal across re-runs with equal checksums; FIG01..FIG18 specs frozen; metadata order-independent with no timestamp/environment fields |

One test-authoring defect was found and fixed during this commit's development: the
first version of U-TEST-22 asserted a hand-typed float literal that differs from its
`repr` round-trip by 1 ULP; the assertion now uses `repr()` itself.  No engine change
was involved.
