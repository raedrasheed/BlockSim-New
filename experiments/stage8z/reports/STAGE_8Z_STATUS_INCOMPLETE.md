# STAGE 8Z — STATUS: INCOMPLETE, HALTED AT PHASE 5

**This is not a completed experiment. No Stage 8Z result may be cited.**

Execution was deliberately halted before the Pilot was signed off, before the freeze,
and before any confirmatory run, because a core physical-work invariant is violated in
two of the six policies. The brief (§33) lists that invariant first among the Pilot
checks and (§7, §56) requires defects to be documented rather than run past.

---

## 1. What is complete and believed correct

| Item | Status |
|---|---|
| Protected-artifact baseline (377 files incl. Stage 8X and Stage 8Y) | recorded, `b2a68047…`, **verified unchanged** |
| Legacy / Stage 8X / Stage 8Y suites before and after | 11 / 74 / 116 all pass |
| Stage 8Y diagnosis (Phase 2) | complete — see §2 below |
| `STAGE_8Z_SCIENTIFIC_DESIGN.md` (Phase 3) | complete, including the preregistered analytic ceiling |
| Seed registry: 4 disjoint groups, disjoint from 8X/8Y | complete, `26c9dd1d…` |
| Frozen-candidate configuration, policies Z0–Z5, matrices | complete, `config_hash 1e74378296da6cef` |
| `rangeledger.py` — verifiable reassignment ledger | complete |
| `powerstate8z.py` — six-state residency + hash-floor deficit | complete |
| `engine.py` — Z0, Z1, Z2, Z3 | working and internally consistent |
| `engine.py` — Z4, Z5 | **defective, see §3** |
| Unit/integration test suite | **not written** |
| Pilot sign-off, exploratory sweep, freeze, confirmatory, secondary, long horizon, analysis, figures, tables, remaining reports | **not done** |

## 2. Phase-2 diagnosis of Stage 8Y (complete, and reproduced in code)

Stage 8Y's saving comes from reduced participation, and block retention tracks the
*realized* mean active hash fraction almost exactly. Stage 8Z's Z1 policy reproduces
the Stage 8Y P3 operating point to three decimal places on independent code:

| Quantity | Stage 8Y P3 (H2, N=300) | Stage 8Z Z1 (H2, N=300) |
|---|---|---|
| mean active hash fraction | 0.5985 | **0.5985** |
| mean active power fraction | 0.4614 | **0.4613** |
| saving at α = 0 | 53.87 % | **53.9 %** |

Z2 (hash floor 0.90) lands exactly on the independently derived analytic ceiling:
realized mean H_active 0.8995 / mean power 0.8488 → saving **15.1 %** against a
predicted ceiling of **14.9 %** for H2. The mechanism and the bound are therefore both
confirmed by working code.

**Preregistered consequence (recorded before any confirmatory run):** because
`BlockRetention ≈ mean H_active` and the registry's efficiency spread is only 1.967×,
the maximum saving at 95 % retention is 4.7 / 7.5 / 6.5 % (H0/H2/H4) and at 90 %
retention is 10.0 / 14.9 / 13.0 %. **Outcomes A, B, C and D of the brief are therefore
analytically unreachable with this hardware registry.** This is derived from the frozen
registry, not from results, and is stated in `STAGE_8Z_SCIENTIFIC_DESIGN.md` §2.

## 3. The blocking defect

**Work-accounting identity violated in Z4 and Z5.**

The invariant `W_total = ∫ H_active(t) dt` — recorded physical evaluations must equal
the integral of active hash rate — holds to ~2×10⁻¹⁵ (machine precision) for Z0, Z1,
Z2 and Z3, but is violated by **7.8×10⁻⁴ to 1.5×10⁻³ relative** for Z4 and Z5, i.e.
0.08–0.15 % of all hashing is mis-attributed.

Observed at N = 300, three pilot seeds, all three compositions. Zero exact duplicates
and zero range-ledger violations are reported in the same runs, so the defect is an
*accounting* mismatch between the scan ledger and the power ledger, not a duplication
or ownership fault.

The defect is confined to the interaction between predictive reserve activation
(`WAKING → ACTIVE_REASSIGNED`) and the repartition wave. Three contributing bugs in
that path were already found and fixed during development —

* **B1** epoch completion was gated on the residual pool emptying, so no-reassignment
  policies stalled permanently after one sweep (`is_exhausted` now tests owned work only);
* **B2** repartition cascaded once per miner completion (O(N²) per epoch, 10⁵–10⁶ spurious
  transfer events, 15–50 s per run); it now fires only on a completed wave or a reserve join;
* **B3** a joining reserve was scheduled twice under one token, double-counting its
  evaluations;

— but a residual leak remains and has not been isolated. Its magnitude (0.1 %) is small
but it is of the same order as several of the effects Stage 8Z is meant to measure
(e.g. the 3.8 pp realized-capacity gap that motivates the whole experiment), so results
produced with it would not be defensible.

## 4. Why execution was halted rather than continued

Running the 3240-run confirmatory matrix, the 780 secondary runs and the 450
long-horizon runs on an engine with an unexplained violation of its primary physical
identity would produce numbers that could not be defended, and would violate the
brief's own Pilot gate. No confirmatory run was executed, nothing was frozen, and no
result is reported.

## 5. What remains

1. Isolate and fix the Z4/Z5 accounting leak; restore `W = ∫H_active dt` to machine
   precision for all six policies.
2. Write the Stage 8Z test suite (the ten reassignment invariants of brief §14 already
   have machine-checkable support in `rangeledger.verify()`).
3. Pilot → sign-off → exploratory sweep on the dedicated exploratory seeds → apply the
   declared selection rules → freeze → confirmatory → secondary → long horizon.
4. Analysis, decomposition, same-work analysis, Pareto comparison against Stage 8Y,
   28 figures, 26 tables and the remaining 14 reports.

## 6. Repository protection (verified)

Stage 8Z wrote only under `experiments/stage8z/`. The 377-file protected baseline —
covering `Models/`, `results/`, `docs/`, `tests/`, **all of `experiments/stage8x/` and
all of `experiments/stage8y/`**, the legacy scripts, the root simulator modules and
every thesis `.docx`/`.pdf`/`.xlsx` — is byte-identical before and after
(`b2a68047ff56710239f8fd1fa2c5de961d46f6e8c379db3e279a31921ffce28d`). The legacy (11),
Stage 8X (74) and Stage 8Y (116) suites all pass unchanged.
