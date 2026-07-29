# Stage 5B1C — Remote Freeze-Branch Verification & Final Pre-Execution Integrity Audit

**Verification stage — no scientific code, matrix, seed schedule, retention list,
dependency lock, thesis, preregistration, results, or scientific test was modified.**
Machine-readable result:
`results/thesis_revision_v43/stage_05b1c/manifests/verification_result.json`.

## Final verdict

# READY_FOR_STAGE_5B2

Every check below passed; no defect was found.

---

## 1. Remote freeze-branch verification

| Field | Value |
|-------|-------|
| Remote branch | `thesis-v43-stage5b2-freeze-1` |
| Resolved commit SHA | `c0ff48e462b90870540caf7461831c9ef795a77f` |
| Expected commit SHA | `c0ff48e462b90870540caf7461831c9ef795a77f` |
| Match | ✅ exact |
| Tree SHA | `edd2389cb06ff509739a2a1c7dc3e3ac2c9c7aea` |
| Commit parent | `65a16c876378d440487da51214a64d2922b28c4d` (Stage 5B1A) |
| Commit timestamp | 2026-07-29T15:58:27Z |
| Repository status | branch present remotely, points exactly to the expected commit |

## 2. Clean-checkout verification

```
git worktree add --detach <scratch>/freeze-verify c0ff48e462b90870540caf7461831c9ef795a77f
```

| Property | Result |
|----------|--------|
| HEAD SHA | `c0ff48e462b90870540caf7461831c9ef795a77f` |
| Detached / pinned | ✅ |
| Working tree clean (0 uncommitted) | ✅ |
| `InputsConfig.py` unmodified vs frozen tree | ✅ |
| Isolated from dev result directories | ✅ (fresh worktree at the frozen tree) |

## 3. Full checksum reconciliation (64-hex, exact)

| Artifact | Expected = Actual | Match |
|----------|-------------------|:---:|
| Matrix | `306d82834395a6bb159dbacf713eaf2290a7ada52c1e9c451c031d09014edce5` | ✅ |
| Seed schedule | `6122dbd0f455a1c4c9676ec6575f064c3a682b3c978705d6588af11489b13e10` | ✅ |
| Retention list | `2283f2ff69bcabf423267b2984ef4acfce852b217b39e1efe8061e583bc1702e` | ✅ |
| Dependency lock | `6e211ea7c031a3fab560843690e27e5a3c2aa2a8c363ab483369a2babc8157be` | ✅ |
| Thesis DOCX | `2c3afdc5739109d0ea12ada96c3115d626a2188c1acbaeaa4b6020974884cbda` | ✅ |
| Thesis PDF | `131412bb2ce17ed97b98dfbefc136c7b5b226b9fd7372e79a25e4b0dc057e9c4` | ✅ |

Seed-schedule and retention-list checksums were **recomputed** from the frozen code
(not read back from a file) and match.

## 4. Solution-position sampling audit — PASS

Frozen sampler (scenario_engine.py): `pos = np.unique(r_solpos.integers(0, S, size=k))`,
`k = r_solk.binomial(S, p)`.

| # | Requirement | Result |
|---|-------------|--------|
| 1 | 0 ≤ K ≤ S | ✅ (K ~ Binomial(S,p)) |
| 2 | positions unique | ✅ (`np.unique`) |
| 3 | uniform without replacement | ✅ output is a uniform unique subset |
| 4 | no sorted-oversample-then-truncate | ✅ (`size=k*2` and `[:k]` both absent — the fixed bug) |
| 5 | not with-replacement without collision resolution | ✅ `np.unique` guarantees a collision-free result |
| 6 | minimum not biased low | ✅ empirical min-of-2 mean **16.195 ≈ S/3 (16.667)**, not the old-bug S/5 (10.0) |
| 7 | same named stream reproduces positions | ✅ |
| 8 | count ~ Binomial(S,p) | ✅ mean k = 2.044 ≈ μ = 2; returned size == k at frozen scale |

**Small-domain checks** (K=0/1/S/near-S, multiple unique, reproducibility, uniform
subset, minimum distribution) all pass. **Implementation note (transparent):** the
sampler draws with replacement and deduplicates; on a collision the count would drop
below k. At the frozen production domain sizes (S ≥ 4.23×10¹⁶) collision probability
is ~10⁻¹⁷ per draw (empirically **0 collisions in 5000 draws**; ~10⁻¹³ expected
across the entire 1 890-run matrix), so the sampler is exact uniform-without-
replacement Binomial(S,p) with unbiased minimum for every frozen run. The real
defect (2× min-bias from `[:2k]` oversampling) is fixed and verified. No critical
defect; the freeze remains valid. (If Stage 5B2 were ever run at *small* domains, a
resample-to-k without-replacement sampler would be advisable — not applicable here.)

## 5. Matrix hash-taxonomy audit — PASS

| Property | Expected | Observed |
|----------|---------|----------|
| Physical run rows | 1 890 | **1 890** |
| `scientific_semantics_hash` groups | 63 | **63** |
| Group-size frequency | all 30 | **{30: 63}** |
| Distinct `run_execution_hash` | 1 890 | **1 890** |
| Duplicate run-execution hashes | 0 | **0** |
| Duplicate same-seed semantics | 0 | **0** |
| Seeds excluded from scientific-semantics | yes | ✅ |
| Seeds included in run-execution | yes | ✅ |
| B3/C1 → one physical run | yes | **870 dual rows, one scenario_id** |
| Presentation-only field splitting a run | none | ✅ none |
| Anomalous groups | none | **[]** |

## 6. B1 analytical audit — PASS

| Check | Result |
|-------|--------|
| Exact P_zero uses finite-domain candidate counts | ✅ M = unique_rate·T |
| log1p / arbitrary-precision (mpmath) | ✅ |
| Exact recomputation matches committed table (all N) | ✅ |
| Poisson labelled only as approximation (+ error) | ✅ |
| Arbitrary 0.25 tolerance removed | ✅ none in codebase |
| Exact P_zero within event-loop 99% CI (all N) | ✅ (committed report) |
| No systematic across-N discrepancy | ✅ |
| Zero-block metrics NA/null (not 0/∞) | ✅ |
| Zero-block runs kept in progress/liveness | ✅ (energy counted, block count reported) |

No new confirmatory dataset was generated; only deterministic analytical checks and
the existing validation were re-run.

## 7. Complete test-suite result (from the clean frozen checkout)

| Field | Value |
|-------|-------|
| Command | `python3 -m pytest tests/ -q` |
| Passed | **268** |
| Failed | 0 |
| Skipped | 0 |
| Runtime | 18.31 s |
| Python | 3.11.15 |
| Dependencies | numpy 2.4.6 · scipy 1.17.1 · mpmath 1.4.1 · pandas 3.0.5 · pytest 9.1.1 |

No test was modified during Stage 5B1C.

## 8. Thesis integrity

`docs/Raed-Rasheed-draft-42-00.docx` and `.pdf` are byte-identical to the expected
SHA-256 values (§3). Neither file was modified, regenerated, renamed, or re-saved.

## 9. Final verdict

**READY_FOR_STAGE_5B2** — the remote freeze branch points to the expected commit,
all six checksums reconcile exactly, the sampling / hash-taxonomy / B1 analytical
audits pass, the full suite is green from a clean pinned checkout, and the thesis is
byte-identical. No scientific artifact was modified in this stage.
