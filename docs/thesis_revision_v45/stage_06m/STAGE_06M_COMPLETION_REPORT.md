# Stage 6M — Completion Report (Resource-Minimal Confirmatory Preregistration)

**Branch:** `thesis-v45-pocol-stage6m-minimal-resource-preregistration`
**Base commit:** `0725f068f73dda49c4264200d3591bcc86dd6033`
**Status:** `STAGE_6M_PREREGISTRATION_COMPLETE` — frozen BEFORE any confirmatory seed executes.

This report records what Stage 6M produced, what it verified, and what it deliberately did
**not** do. Everything below was checked by an executable gate; nothing is asserted from
intention.

---

## 1. What Stage 6M is

Stage 6M is the **resource-minimal confirmatory redesign** authorized after the Stage-7
resource preflight measured that the previous frozen design (660 logical rows, 630 physical
executions, 30 aliases) projects to an execution window (~124 days on the only available
host) that no available host can carry. The supersession is recorded in
`STAGE_06M_SUPERSESSION_NOTICE.md`:

* the previous design required 660 logical rows / 630 physical executions;
* **zero confirmatory seeds of the previous design were ever executed**;
* the redesign was caused solely by measured compute infeasibility;
* no effect size, direction, or preliminary outcome informed any redesign choice;
* the previous preregistration is superseded **before data collection**, which is the
  methodologically clean point to do it.

The redesigned experiment is the smallest scientifically coherent test of the central energy
claim of the PoCol idle policy within its operational security/service limits.

---

## 2. The frozen design (summary; normative text in STAGE_06M_PREREGISTRATION.md)

* **Frozen minimal core:** 20 miners, horizon 300 s, nonce domain 1600, difficulty 1000,
  batch 25, base hash rate 100.0, reserve fraction 0.20, powers (W): hash 21.5,
  listen 2.15, reserve 2.15, wake 10.75, offline 0.0. Range leases, reassignment,
  adversarial and incentive models DISABLED; dynamic difficulty FORBIDDEN.
* **Analytic continuous control:** `A1_core_kwh = 20 × 21.5 × 300 / 3 600 000 =
  0.035833333333333335 kWh` (verified exact by test S6M-01).
* **Scenarios (3):** `M01_HET_IDLE` (heterogeneous, idle policy), `M02_HOM_IDLE`
  (homogeneous, idle policy), `M03_HET_IDLE_FLOOR` (= M01 + accepted operational floor:
  minimum active hash rate 0.80 × initial active-primary rate = 3200.0, MINIMUM_CARDINALITY
  reserve selection, ON_CAPACITY_CHANGE trigger, wake latency 1.0 s, tolerance 0.0,
  CONTINUE_DEGRADED).
* **Seeds:** the FIRST 10 existing confirmatory seeds (index 0–9;
  7266343386191483739 … 11943450448932995834). No replacements, no post-hoc additions.
  3 × 10 = **30 physical confirmatory runs**.
* **Primary contrast:** within-run power-null counterfactual computed from the SAME
  residency ledger (`E_power_null = P_hash·(t_hash+t_listen+t_reserve+t_wake) +
  P_offline·t_offline`). No separate power-control simulation exists.
* **Exploratory scale checks (non-inferential):** `X01_SCALE_HET_IDLE` and
  `X02_SCALE_HET_IDLE_FLOOR` (141 miners, nonce domain 4000, batch 50), one PILOT seed
  each; they carry `hypotheses = NONE` and may never enter confirmatory evidence.
* **Hypotheses:** H-M1 (energy reduction vs within-run power null; ≥5 % mean relative
  reduction AND bootstrap 95 % lower bound > 0 AND exact sign-permutation p < 0.05),
  H-M2 (mechanism sensitivity, descriptive only), H-M3 (floor cost within preregistered
  service limits). The thesis energy claim is licensed only if H-M1 passes AND H-M3 is
  within limits.

---

## 3. Executable verification record

Every gate below ran on this branch, in this order, before the freeze commit.

### 3.1 Accepted engine test suite — PASS

`python3 -m pytest tests/thesis_revision_v45/stage2/ -q` → **195 passed**.
Test S6M-08 additionally re-verified the SHA-256 of every accepted engine source file
against the Stage-5D accepted digests: the engine is byte-identical to the accepted
baseline. `search.py` untouched. No thesis DOCX/PDF touched. No CI workflow added.

### 3.2 Stage-6M validation tests — PASS (9/9)

`python3 -m pytest tests/thesis_revision_v45/stage_06m/ -q` → **9 passed**.

| test | what it proves |
|---|---|
| S6M-01 | frozen core config exact, `A1_core_kwh` exact, leases/adversarial/incentive genuinely disabled |
| S6M-02 | treatment isolation: M01↔M02 differ ONLY in `heterogeneous_hash_rates`; M01↔M03 ONLY in `security_floor` (the explicit `floor_unattainable_policy = CONTINUE_DEGRADED` equals the engine default) |
| S6M-03 | selected seeds are exactly the FIRST 10 existing confirmatory seeds and are disjoint from all pilot seeds |
| S6M-04 | **the required invariance proof**: changing only `P_listen`/`P_reserve`/`P_wake` leaves the nonce evaluation ledger, round identities/terminal times, residency, event log, accepted rounds, disposition and coverage byte-identical, and changes ONLY the energy accounting; the within-run `E_power_null` equals the actual energy of a run priced at `P_hash` everywhere, and (with zero offline residency) equals `A1_core_kwh` |
| S6M-05 | the three CSV artifacts regenerate byte-identically from `generate_6m.py` |
| S6M-06 | the structural pilot passed all gates and its output contains NO energy-effect quantity |
| S6M-07 | matrix counts (3 confirmatory / 2 exploratory), all mechanism columns DISABLED, dynamic difficulty FORBIDDEN, exploratory rows carry no hypothesis; 10 confirmatory seeds registered |
| S6M-08 | accepted engine byte-identical; historical Stage-6/Stage-7 records present and unmodified at this base commit |
| S6M-09 | the supersession notice states every required fact |

### 3.3 Deterministic regeneration — PASS

`python3 experiments/thesis_revision_v45/stage_06m/generate_6m.py --check` →
`OK: 3 artifact(s) byte-identical to regeneration`.

### 3.4 Structural pilot — PASS (6/6 runs, all gates)

`run_structural_pilot_6m.py` ran M01/M02/M03 on the 2 PILOT seed indexes (0, 1), which are
disjoint from the 10 confirmatory seeds. **Structure and runtime only** — the output
contains no per-run energy total, no power-null counterfactual, and no difference or ratio
of them (enforced by test S6M-06 as a forbidden-token scan).

| scenario | pilot idx | status | rounds | wall (s) | peak RSS (MB) | gates |
|---|---|---|---:|---:|---:|---|
| M01_HET_IDLE | 0 | COMPLETED | 227 | 1.16 | 54.2 | PASS |
| M01_HET_IDLE | 1 | COMPLETED | 228 | 1.23 | 60.5 | PASS |
| M02_HOM_IDLE | 0 | COMPLETED | 204 | 0.99 | 63.2 | PASS |
| M02_HOM_IDLE | 1 | COMPLETED | 201 | 1.02 | 63.2 | PASS |
| M03_HET_IDLE_FLOOR | 0 | COMPLETED | 193 | 1.65 | 74.0 | PASS |
| M03_HET_IDLE_FLOOR | 1 | COMPLETED | 189 | 1.66 | 75.7 | PASS |

Gates per run: completes; ≥100 rounds; non-empty evaluation ledger;
`duplicate_nonce_count == 0`; `post_round_evaluation_record_count == 0`; residency
reconciliation; wall ≤ 10 min; peak RSS ≤ 4 GB; and for M03 additionally: security-floor
observations recorded; ≥1 reserve activation seated; no nonterminal activation request
remains.

**Feasibility consequence:** the worst pilot run costs 1.66 s and < 76 MB. The full Stage-7M
load (30 confirmatory + 2 exploratory runs) projects to minutes, not days, with enormous
margin against the Stage-7M preflight ceilings (4 h wall, 8 GB RSS).

---

## 4. Deliverables in this freeze

| file | role |
|---|---|
| `STAGE_06M_SUPERSESSION_NOTICE.md` | why and how the previous preregistration is superseded |
| `STAGE_06M_PREREGISTRATION.md` | the frozen design (normative) |
| `STAGE_06M_MINIMAL_MATRIX.csv` | 3 confirmatory + 2 exploratory rows (generated) |
| `STAGE_06M_SEED_REGISTRY.csv` | the 10 confirmatory + pilot seed assignments (generated) |
| `STAGE_06M_OUTCOME_DICTIONARY.csv` | 26 preregistered outcomes incl. integrity gates (generated) |
| `STAGE_06M_ANALYSIS_PLAN.md` | exact H-M1/H-M2/H-M3 procedures, analysis seed, decision rules |
| `STAGE_06M_LIMITATIONS.md` | honest scope limits of the minimal design |
| `STAGE_06M_PILOT_REPORT.md` | structural pilot narrative (no energy effects) |
| `STAGE_06M_COMPLETION_REPORT.md` | this report |
| `STAGE_06M_CHECKSUM_MANIFEST.sha256` | SHA-256 over every Stage-6M doc/experiment/test file (generated LAST) |

Experiment code: `experiments/thesis_revision_v45/stage_06m/`
(`scenarios_6m.py`, `generate_6m.py`, `run_structural_pilot_6m.py`, pilot output).
Validation tests: `tests/thesis_revision_v45/stage_06m/test_stage6m.py`.

---

## 5. What Stage 6M did NOT do

* **No confirmatory master seed was executed.** The only executions were the 6 structural
  pilot runs on PILOT seeds and the pilot-seed invariance fixture inside test S6M-04.
* **No energy effect was computed, inspected or recorded for any pilot run.** The design was
  frozen blind to effect direction.
* No modification to the accepted simulation engine, `search.py`, any thesis DOCX/PDF, or
  any historical Stage-6/Stage-7 artifact. No CI workflow was created. Stage 9 not begun.

---

## 6. Standing state after this commit

```
STAGE_6M_PREREGISTRATION_COMPLETE
STAGE_7M_EXECUTION_NOT_YET_STARTED
```

Stage 7M (branch `thesis-v45-pocol-stage7m-minimal-execution`) may begin only from this
freeze commit, must pass its own dry-run resource preflight (projected wall ≤ 4 h, peak
RSS ≤ 8 GB, free disk ≥ 2 GB, zero pre-existing output, 32 unique run identifiers), and
executes exactly 30 confirmatory + 2 exploratory runs with ≤ 2 concurrent workers.
