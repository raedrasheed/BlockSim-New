# STAGE 04 — Scientific Baseline Definitions (B0–B3, C1–C2)

Accurately named, fairly matched scenarios. Code:
`experiments/thesis_revision_v43/scenario_definitions.py`; schema
`config_schema.py`; dry-run evidence `STAGE_04_DRY_RUN_RESULTS.csv`; tests
`test_stage4_stale_and_scenarios.py` (15–23).

Candidate-header identity (duplicate **iff all fields equal**):
`(template_id, template_generation_id, parent_id, height, extranonce, nonce)`.

---

## Scenario table

| ID | Name | Template | Nonce allocation | Idle | Isolated mechanism |
|---|---|---|---|---|---|
| **B0** | Independent-template PoW **abstraction** | per-miner (distinct) | independent | no | ordinary PoW; equal numeric nonces under different templates are **not** duplicates |
| **B1** | Common-template **uncoordinated** PoW | one shared | all from 0 | no | duplicate candidate-header evaluation under one template |
| **B2** | Common-template randomized-start PoW | one shared | randomized start + wraparound | no | overlap reduction from randomized starts (no formal ranges) |
| **B3** | Common-template disjoint-range **continuous** PoW | one shared | disjoint ranges | no | nonce-range partitioning **without** idling |
| **C1** | PoCol continuous-performance | one shared | disjoint (PoCol round/template metadata) | no | PoCol abstraction under continuous operation |
| **C2** | PoCol post-range **idle** | one shared | disjoint | **yes** | genuine active→idle energy saving |

Naming rules honoured: B0 is the *independent-template PoW abstraction* (not
"exact Bitcoin"); B1 is *not* called "classical PoW".

## Fair-matching invariants (all scenarios)
Fixed aggregate hash rate `Σ Hᵢ = H_total`; identical efficiency, active power,
target interval, and duration; one shared configuration schema; deterministic
seeds. Only the mechanism under test differs.

## Dry-run findings (small scale, semantic validation)

- **B0** → duplicate evaluations = 0 (distinct templates).
- **B1** → duplicate evaluations > 0 (all miners re-hash the same headers).
- **B2** → duplicate rate < B1 (randomized starts reduce overlap).
- **B3 / C1** → overlap = 0 (disjoint ranges cover the domain once).

### Two honest, non-obvious findings

1. **Duplicate elimination does not, by itself, reduce total energy.** Over a
   fixed wall-clock round every miner hashes for the same duration regardless of
   overlap, so B1 and B3 consume the **same total energy**. Disjoint ranges
   change **coverage** (distinct headers searched → probability of finding a
   solution → energy *per accepted block*), not total power. Any claim that
   "eliminating duplicate hashing saves energy" must therefore be stated as
   *energy per block / throughput*, not total energy.

2. **C1 and B3 are numerically identical in the simulator.** Their only
   differences (immutable TemplateID commitment, pre-committed reward
   distribution, collaborative-reward semantics) are **specified but not
   implemented** (Path A). We state this explicitly rather than manufacture an
   artificial difference: in the executed abstraction, **C1 = B3**.

## C2 — where a genuine energy saving comes from

C2's saving is exactly `Σᵢ idle_timeᵢ · (P_activeᵢ − P_idleᵢ)`, where
`idle_timeᵢ = max(0, round_end − range_completionᵢ)` and
`range_completionᵢ = Sᵢ / Hᵢ`. Consequences (measured):

- **Symmetric homogeneous, μ ≥ 1 (S ≥ H·B): C2 = C1, zero saving.** Every
  miner's equal range completes no earlier than the round ends, so no miner ever
  idles. The "post-range idle policy" saves **nothing** here.
- **When ranges complete early (S < H·B, or heterogeneous rates with equal
  ranges): C2 saves.** Dry-run demo (range completes at half the round): idle
  power 0 % → 50 % saving; 10 % → 45 %; 20 % → 40 % — i.e. saving falls linearly
  with idle power, exactly the state-duration formula. **0 % idle power is the
  explicit theoretical lower bound, not a realistic main result.**

This decomposition is central to Stage 6: the thesis's energy claim must be
attributed to the idle transition under the conditions where it actually occurs,
not to nonce-range separation or duplicate elimination.
