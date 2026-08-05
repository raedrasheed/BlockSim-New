# Stage 8S — Implementation Report: the useful-work-aware idle and reserve-control policy within PoCol

**Branch:** `thesis-v45-pocol-stage8s-useful-floor-coarse-reassignment` from
`12baeae0cbba54234723d6ec79e4216e4948c689` (exact remote HEAD of
`thesis-v45-pocol-stage8r-controller-refinement`; clean worktree; 213 tests green;
Stage-8R manifest verified — frozen dataset and analysis unchanged). The algorithm name
remains **PoCol**.

## 1. Controller modes

| mode | behaviour |
|---|---|
| `LEGACY_REACTIVE` (default) | reproduces the frozen Stage-8M record bit-exactly (S8S-TEST-01) |
| `STAGE8R_PREDICTIVE_STATIC_FLOOR` | reproduces frozen Stage-8R R02 for the same seed exactly (rounds, blocks, seats, batches, below-floor; energy to 1 ULP of the pair-summation order — S8S-TEST-02) |
| `USEFUL_FLOOR_ONLY` | Stage-8R features + the useful-work-aware decision target (S8S-2) + reserve admission control (S8S-5) |
| `USEFUL_FLOOR_COARSE_REASSIGNMENT` | the above + work-conserving deterministic coarse suffix repartition, receiver-first (S8S-3/4) |

The two new modes cannot affect default execution; no mode touches target/difficulty
(S8S-TEST-22). All Stage-8R features are retained (episodes, 0.78/0.80/0.82 hysteresis,
one live batch, cooldown, observable-only prediction, physical H_effective, H_pipeline,
minimum-cardinality selection, replay idempotence, closure cleanup).

## 2. S8S-1/S8S-2 — the two floors

`H_static_floor = 0.80 × H0` stays computed, reported and historically comparable in every
run (never redefined; S8S-TEST-04). The NEW primary quantity is
`H_useful_target(t) = min(0.80 × H0, H_useful_available(t))` where `H_useful_available`
counts ONLY (1) ACTIVE_HASHING miners with a non-empty accepted range and (2) already-awake
eligible receivers bounded by the spare whole batches active donors could cede (WAKING
miners, reserves, stale assignments and any future-solution information are excluded; live
wake requests stay in H_pipeline only). Two definitional clarifications, declared here
before the freeze: the **decision** reference counts receivers only in the coarse mode
(the only mode whose mechanism can deliver work to them), while the **reported**
useful-floor metrics always count receivers (a mode-independent counterfactual, so
S01/S02/S03 are comparable); both floors' metrics are computed independently
(S8S-TEST-21).

## 3. S8S-3/S8S-4 — work-conserving coarse repartition (receiver-first)

The Stage-8R failure (1 198 trigger decisions, ZERO seated reassignments — the trigger
fired before any receiver existed) is corrected by ordering: eligible already-awake
receivers are selected FIRST; only then is the donor with the LARGEST accepted unsearched
suffix chosen. The suffix is partitioned by the accepted integer apportionment rule into
`part_count = min(1 + receivers, ceil(remaining/batch))` contiguous near-equal chunks
(deterministically reduced so no non-final chunk is below one batch); donor keeps the
first chunk; one chunk per receiver; one repartition per donor lineage per breach episode;
pairwise-disjoint chunks whose union is exactly the accepted remaining suffix
(S8S-TEST-08/09/10/12). The apply is **atomic**: receivers seat first, the donor shrinks
last under a fresh assignment version, and any seat failure unwinds everything.

Two design decisions the data forced, declared before the freeze:
* **Receivers start immediately** (LOW_POWER_LISTEN → ACTIVE_HASHING, no wake transient):
  they are already awake, which is what distinguishes them from reserves — and with the
  1.0 s wake latency the arithmetic of this scale (suffixes ≤ 80 nonces) makes ANY
  latency-paying split strictly counterproductive.
* **A deterministic benefit gate**: a repartition applies only when the post-split makespan
  strictly beats the donor finishing alone (all inputs observable: chunk sizes and actual
  rates). No speculative churn.

## 4. S8S-5 — reserve admission control

A reserve wake requires atomically bindable useful work: the accepted seating transaction
claims an UNCLAIMED, non-empty reserve slice and binds it to the wake request in one
all-or-none commit (S8S-TEST-14). When eligible reserves exist but no bindable work
remains, the wake is rejected and recorded (`activation_rejected_no_useful_work`,
`reserve_wakes_rejected_no_useful_work`); H_effective is untouched and nothing counts as
capacity restoration. Reserve wake is subordinate to reassignment: a reserve batch is
never seated in the same decision as a coarse repartition (S8S-TEST-13).

## 5. Files

`refinement.py` (modes, `h_useful_available`, `CoarseRequest`, counters), `context.py`
(coarse registries + useful trackers), `simulator.py` (useful-mode decision reference,
`_useful_predictive_check`, atomic `_maybe_coarse_repartition`, admission control, closure
terminalisation), `adapter.py` (static+useful floor block, coarse metrics, admission
metrics), tests `tests/thesis_revision_v45/stage_08s/` (S8S-TEST-01..22), Phase-0
diagnostic `experiments/thesis_revision_v45/stage_08s/diagnose_8s_baseline.py`.

Historical evidence untouched: Stage-6M/7M/8M/8R manifests all verify. The frozen gates
`test_s6m_08` (Stage-5D byte identity) and R-TEST-01-style equivalences carry the
behavioural protection; the full accepted + Stage-8R suites pass unchanged.
