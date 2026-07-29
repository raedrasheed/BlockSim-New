# Stage 5B1F — Template & Parent Provenance and Partial/Exhausted Classification

Engine: `scenario_engine.py`
Tests: `test_stage5b1f_provenance.py` (28–32)

## 1. Parent provenance (Section 9)

Each generation captures the parent **before** processing:

```
parent_before = last_accepted_block_id     # captured at generation start
template.parent_block_id = parent_before
# ... process generation ...
if accepted:  last_accepted_block_id = accepted_block_id
```

Guarantees (all tested):
- an accepted block is **never its own parent** (test 28);
- the first accepted block's parent is `genesis`, and every later block points to the
  **previous accepted block** (test 29);
- an exhausted generation (refresh, no block) **retains the same parent** — height does
  not advance (test 30);
- a refresh without a block sets `refresh_required` and does **not** advance height
  (test 32).

The earlier code set `last_block_id = block_id` *before* writing the template record,
so a block could appear as its own parent; capturing `parent_before` fixes this.

## 2. Partial vs exhausted (Section 10)

Separate boolean fields are emitted per template generation:

| Field | Meaning |
|-------|---------|
| `completed` | the generation finished within the horizon |
| `exhausted` | active domain fully searched, no active solution (and completed) |
| `partial` | the simulation horizon interrupted the generation |
| `accepted` | an active solution produced a block |
| `refresh_required` | the template refreshes (no block accepted) |

A generation is **never** both `partial` and `exhausted` (test 31): `exhausted` is set
only when the active searchable domain was fully completed with no active solution;
`partial` is set only when the horizon interrupts the generation. The old code set
`exhausted = (status != FOUND)`, which mislabelled partial generations as exhausted.
