# STAGE 04 — Round and Template Terminology

Consistent definitions for the simulator (thesis wording is **not** changed yet).

## Definitions

| term | meaning | identifier |
|---|---|---|
| **chain height** | index of the accepted block in the canonical chain | `parent_height (+1)` |
| **consensus round** | the search for the block at height h+1 on a fixed parent | `round_id` |
| **template generation** | a canonical template instance for the current round; a new one is minted on finite-domain exhaustion | `template_generation_id` (+ `template_id`) |
| **mining generation** | the miner's local generation, used to invalidate events after a restart/round change | `event_generation_id` (== round_id here) |
| **nonce-allocation epoch** | one assignment of disjoint ranges over the domain; coincides with a template generation | (per `template_generation_id`) |
| **parent generation** | the round metadata established by a block for its children | `round_meta[parent_id]` |
| **target/difficulty version** | the active target/`p` version | `target_version` |

## State-transition table (what increments)

| event | chain height | round_id | template_generation_id | mining generation | target_version | invalidates prior events? |
|---|---|---|---|---|---|---|
| **accepted block** | +1 | new round on the new block | reset to 0 (new round) | new | — | yes (parent/round/generation change) |
| **template exhaustion** | unchanged | unchanged | **+1** (new epoch, same parent) | unchanged | — | yes, prior template-generation events → OBSOLETE_TEMPLATE |
| **parent update (reorg/receive)** | may change | adopts new tip's round | adopts new tip's | adopts new tip's | — | yes (OBSOLETE_PARENT) |
| **difficulty update** | unchanged | unchanged | unchanged | unchanged | **+1** | yes (OBSOLETE_DIFFICULTY) |
| **miner restart** | unchanged | unchanged | unchanged | unchanged | — | re-opens local mining (energy only) |
| **local chain reorg** | changes | adopts winning chain's | adopts | adopts | — | yes (OBSOLETE_PARENT) |
| **simulation cutoff** | frozen | frozen | frozen | frozen | frozen | open ACTIVE intervals flushed (energy) |

## Resolved interpretation of exhaustion

Among the three options in the brief, the simulator uses **(B/C combined):
finite-domain exhaustion starts a new *template generation* / *nonce-allocation
epoch* within the same consensus round on the same chain height/parent — it does
NOT start a new consensus round.**

Rationale: exhaustion produces **no block**, so the chain height and parent are
unchanged; a "consensus round" is defined by (parent, height) and therefore
cannot advance without an accepted block. What genuinely changes on exhaustion is
the *search assignment* — a fresh canonical template and a new disjoint-range
allocation over the domain — which is precisely a new template generation /
nonce-allocation epoch. Events from the exhausted generation are rejected as
`OBSOLETE_TEMPLATE`. This keeps "round" tied to chain progress and "template
generation" tied to search refresh, avoiding the Stage-1/2 conflation.
