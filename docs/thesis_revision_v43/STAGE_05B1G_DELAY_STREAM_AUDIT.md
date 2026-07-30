# Stage 5B1G — Propagation-Delay Stream Identity Audit (Section 4)

Engine: `scenario_engine.py` (`_delivery_delay`, `_resolve_stale_race`,
`_record_stale_race`)
Tests: `tests/thesis_revision_v43/stage5b1g/test_stage5b1g_delay_streams.py` (11–17)
Records: `results/thesis_revision_v43/stage_05b1g/stale_race_and_delivery_delay_records_sample.json`

## 1. Defect removed

The former engine drew propagation delays from a single winner-scoped generator
(`rng(cfg.seed*1_000_003 + winner, "propagation_delay")`) and **zipped an anonymous
delay list onto the order-dependent competitor list**, with a first (unused) delay
draw at status determination and a second recomputation at block acceptance. That made
delays depend on competitor ordering and on how many recipients existed, and resolved
the race twice.

Both patterns are removed. The stale race is resolved **exactly once per accepted
height**, and every propagation delay is derived per delivery from the full delivery
identity.

## 2. Per-delivery deterministic stream

```
delivery_stream_key = f"{master_seed}|{template_generation_id}|{parent_block_id}"
                      f"|{winner_miner_id}|{recipient_miner_id}|propagation_delay"
seed  = int.from_bytes(sha256(delivery_stream_key)[:8], "big")
delay = Fraction(round(default_rng(seed).exponential(mean), 9))          # mean>0
delay = 0                                                                # mean<=0
```

`delivery_stream_key` is stored on every delivery-delay record.

## 3. Verified properties

| Property | How guaranteed | Test |
|----------|----------------|------|
| Reproducible | key → seed → single draw | 11 |
| Independent per recipient | recipient id in the key | 12 |
| Not a function of competitor-list order | delay keyed on identity, not position | 13 |
| Adding a recipient does not shift existing delays | each recipient has its own stream | 14 |
| Same winner in a different generation does not reuse the delay | gen id + parent in the key | 15 |
| Zero configured mean ⇒ exact zero delay ⇒ zero stales | explicit `mean <= 0` branch | 16 |
| Recorded delay reconstructs from the identity alone | key recomputation | 17 |

Order-independence is checked exhaustively over **all 24 permutations** of a
four-competitor discovery list: the set of stale producers and the per-recipient delay
map are invariant (test 13). Validation additionally re-derives every recorded
delivery delay from its stored identity and confirms an exact match
(`delay_stream` reconciliation family, `validate_5b1g.py`).

## 4. Consequence for the race

Because each recipient's delay is independent of ordering and of the recipient set,
`_resolve_stale_race` admits **one stale per miner** and as many distinct stale
producers as beat their own receipt — deterministically, regardless of the order in
which discoveries are presented.
