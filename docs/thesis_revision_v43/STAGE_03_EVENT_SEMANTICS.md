# STAGE 03 — Event Semantics and Classification

Defines the immutable event identity, the classification categories (A–H from
the Stage-3 brief), the validation rules, and the cancellation strategy. Code:
`Models/PoCol/round_state.py` (pure, tested), `Models/PoCol/Consensus.py`
(round state + scheduling), `Models/PoCol/BlockCommit.py` (validation on firing).

---

## 1. Event identity (required metadata)

Every scheduled PoCol mining event carries an immutable `EventIdentity`
(`round_state.EventIdentity`), attached to the `Event` and its candidate block:

| field | meaning |
|---|---|
| `event_id` | unique per scheduled event |
| `event_generation_id` | mining generation (== round in which it was scheduled) |
| `round_id` | round the finder searched |
| `parent_block_id` | the round's parent (block being extended) |
| `parent_height` | parent depth |
| `template_id` | canonical template id for the round |
| `template_generation_id` | increments on finite-domain exhaustion refresh |
| `miner_id` | the finder |
| `scheduled_at`, `fires_at` | schedule vs. execution time |
| `target_version` | difficulty/target version |
| `nonce_range_id` | the finder's disjoint nonce range |

Non-PoCol models pass no metadata (`Event.meta=None`), so they are unaffected.

## 2. Local (not global) round state

Classification uses the **miner's local tip**, not a global clock: a miner's
"current" round/generation/template are those of the round established by its
local tip block (`Consensus.round_meta[tip_id]`). Miners therefore legitimately
hold **different local rounds** during propagation delay (brief). This is the
idealized-agreement (Path A) representation: a centralized round coordinator is
assumed only for *template supply*; the round *state each miner acts on* is
local. (Documented assumption, not an implemented distributed agreement layer.)

## 3. Classification (`round_state.classify_event`)

Evaluated in order (first inconsistency wins):

| # | category | condition | outcome |
|---|---|---|---|
| H | `INVALID_EVENT` | already consumed/invalidated | reject |
| F | `OBSOLETE_GENERATION_EVENT` | event generation ≠ miner generation | reject |
| F | `OBSOLETE_DIFFICULTY_EVENT` | target version ≠ current | reject |
| E | `OBSOLETE_TEMPLATE_EVENT` | template generation ≠ current | reject |
| D | `OBSOLETE_PARENT_EVENT` | event parent ≠ miner tip | reject |
| C | `OBSOLETE_ROUND_EVENT` | event round ≠ miner's local round | reject |
| B | `LEGITIMATE_PROPAGATION_COMPETITOR` | structurally current **and** a sibling already advanced | counted as genuine stale |
| A | `VALID_CURRENT_EVENT` | structurally current, first for the parent | accepted; one round transition |
| G | `FINITE_DOMAIN_EXHAUSTION` | round found no solution | new template generation; **never** a block or stale |

`OBSOLETE_CATEGORIES = {C, D, E, F, difficulty, H}`. A rejected obsolete event
does **not**: create a block, increment stale, increment accepted, advance the
round, trigger a reward, change difficulty, or consume new energy. Energy already
consumed *before* the miner learned of the new block is retained (Stage 2).

## 4. Validation on firing (`BlockCommit.generate_block`)

1. read `EventIdentity`; if absent → `INVALID_EVENT`;
2. `label = classify_event(ev, current_state(miner))`;
3. dispatch:
   - obsolete/invalid → record category, mark consumed, return;
   - `LEGIT_COMPETITOR` → account energy, count as stale (off main chain), return;
   - `VALID_CURRENT` → account energy, accept, `mark_advanced(parent)`,
     `start_round(new block)` (exactly one transition), propagate.

`mark_consumed` and `mark_advanced` are **set operations → idempotent**; an event
is never processed twice.

## 5. Cancellation vs. lazy validation

We use **lazy validation at execution** (option B). Obsolete events may remain in
the heap but are rejected in O(1) on firing. Correctness never depends on
removing arbitrary heap elements. Because only *finders* (≈ `mu = p·S` per round,
not `N`) are ever scheduled, the queue peak is O(N) (a single propagation burst),
not O(N·blocks) — see `STAGE_03_SCHEDULER_REPORT.md`.

## 6. Why the Stage-1/2 "stale explosion" was an artifact

Previously every one of the `N` miners was scheduled a block event each round and
credited with a block whenever its (stale) parent still matched — even though its
disjoint range contained no solution. Those were **finite-domain non-solutions
mislabelled as stale blocks**. Correctly, only solution-holding finders can find
a block; non-finders exhaust or are preempted. The corrected genuine stale rate
is the rare case where two finders find within the propagation window
(`LEGITIMATE_PROPAGATION_COMPETITOR`).
