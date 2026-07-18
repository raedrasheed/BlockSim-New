# PoCol Main-Simulator Extension — Equal Nonce Shares + Power-Down After Work

**Branch:** `claude/pocol-equal-nonce-idle-mainsim`
**Flags:** `PoCol_IdleAfterRange` (opt-in, **default OFF**) ·
`PoCol_RestartPolicy` = `"slot"` (default) | `"immediate"`
**Data:** `results/mainsim_idle_after_range/raw_runs.csv` (PoCol, N ∈ {100…500}, 30 seeds, fresh process per run)

## What the extension does (as requested / حسب الطلب)

1. **تقسيم نطاق النونس بالتساوي:** the nonce domain is split into mutually
   disjoint shares proportional to hash rate — **equal shares for equal miners**
   (this partitioning already existed in the corrected model).
2. **كل معدّن يعمل على جزئه فقط:** each miner searches only its own share.
3. **التوقف بعد انتهاء العمل:** when the round closes, **every miner powers down
   to 0 W (IDLE)** until the next slot boundary (`Binterval` grid). Mining
   resumes at the boundary with a fresh template.
4. **توزيع عادل:** equal shares ⇒ equal ACTIVE time ⇒ **exactly equal per-miner
   energy** (verified: max−min = 0 in every run).

Energy accounting is wall-clock state integration: ACTIVE charged to the close
time, the idle window integrated at 0 W, re-armed ACTIVE at the boundary.
**The saving emerges only from genuinely shorter ACTIVE time — never from
dividing energy by N** (test: `energy == E_continuous × active_fraction` exactly).

## Results (30 seeds, mean)

| N | flag | Energy (kWh) | saving | % time ACTIVE | blocks | accepted interval (s) |
|---:|:--|---:|---:|---:|---:|---:|
| 100 | OFF | 8.4208 | – | 100.0 | 18.5 | 533 |
| 100 | **ON** | **5.0269** | **40.3 %** | 59.7 | 11.3 | 875 |
| 200 | OFF | 8.4208 | – | 100.0 | 17.9 | 544 |
| 200 | **ON** | **5.2034** | **38.2 %** | 61.8 | 11.1 | 922 |
| 300 | OFF | 8.4208 | – | 100.0 | 15.5 | 658 |
| 300 | **ON** | **5.5955** | **33.6 %** | 66.4 | 10.0 | 987 |
| 400 | OFF | 8.4208 | – | 100.0 | 16.9 | 581 |
| 400 | **ON** | **5.2993** | **37.1 %** | 62.9 | 10.9 | 892 |
| 500 | OFF | 8.4208 | – | 100.0 | 16.8 | 592 |
| 500 | **ON** | **5.4167** | **35.7 %** | 64.3 | 10.2 | 998 |

Per-miner energy is **exactly equal** across miners in every ON run.

## Immediate-restart policy (بدون انتظار الدورة الزمنية — كما في PoW)

`PoCol_RestartPolicy = "immediate"`: the next round begins **at the round-close
time** — no slot-boundary wait. Each miner still works only its own disjoint
range. With ranges proportional to hash rate, no miner finishes its share before
the round closes, so **no idle time physically occurs** and the block schedule
matches the standard model bit-for-bit.

Results (30 seeds, mean; PoW shown for reference):

| N | variant | Energy (kWh) | blocks | interval (s) | throughput (tx/s) | % ACTIVE |
|---:|:--|---:|---:|---:|---:|---:|
| 100 | PoW | 8.4208 | 17.9 | 548 | 3.300 | 100.0 |
| 100 | PoCol **immediate** | **8.4208** | **18.5** | **533** | **3.399** | 100.0 |
| 100 | PoCol slot | 5.0269 | 11.3 | 875 | 2.092 | 59.7 |
| 200 | PoW | 8.4208 | 17.4 | 571 | 3.202 | 100.0 |
| 200 | PoCol **immediate** | **8.4208** | **17.9** | **544** | **3.302** | 100.0 |
| 200 | PoCol slot | 5.2034 | 11.1 | 922 | 2.052 | 61.8 |
| 300 | PoW | 8.4208 | 15.1 | 670 | 2.784 | 100.0 |
| 300 | PoCol **immediate** | **8.4208** | **15.5** | **658** | **2.851** | 100.0 |
| 300 | PoCol slot | 5.5955 | 10.0 | 987 | 1.852 | 66.4 |
| 400 | PoW | 8.4208 | 16.7 | 599 | 3.074 | 100.0 |
| 400 | PoCol **immediate** | **8.4208** | **16.9** | **581** | **3.111** | 100.0 |
| 400 | PoCol slot | 5.2993 | 10.9 | 892 | 2.011 | 62.9 |
| 500 | PoW | 8.4208 | 17.2 | 567 | 3.164 | 100.0 |
| 500 | PoCol **immediate** | **8.4208** | **16.8** | **592** | **3.102** | 100.0 |
| 500 | PoCol slot | 5.4167 | 10.2 | 998 | 1.880 | 64.3 |

**The trade-off is now explicit and unavoidable:**

- **immediate** (كما طلب: بدون انتظار): blocks come **~40–47 % faster** than slot
  mode and match PoW's production rate — but miners are ACTIVE 100 % of the time,
  so energy returns to **exactly 8.4208 kWh = PoW**. The saving disappears.
- **slot**: saves ~34–40 % energy — but blocks are ~60–70 % slower.
- You can have fast blocks or idle-time savings, **not both**: the energy saving
  *is* the waiting time. This is the central principle
  (`docs/CONTINUOUS_DISTRIBUTED_EFFORT_METHODOLOGY.md §2`) confirmed inside the
  main simulator: **nonce distribution alone does not reduce energy** —
  `E = P × active_time`, and immediate restart keeps `active_time = simTime`.

## Honest interpretation (اقرأ هذا قبل الاقتباس)

- **The ~34–40 % saving is NOT the (1−1/N) worst-case figure.** It is the idle
  fraction of the slot cycle: miners wait, powered down, between block discovery
  and the next slot boundary. It does not grow with N.
- **There is a real throughput cost:** the accepted block interval lengthens from
  ~530–660 s to ~870–1000 s (fewer blocks in the same horizon). The saving buys
  idle time, not free energy — energy *per accepted block* changes much less.
- **The saving requires miners to actually power down** (`0 W` idle here — the
  idealized `q = 0`). Real hardware idles above 0 W; see the sensitivity sweep in
  `results/continuous_distributed_effort/` (`reduction = (1−q)(1−1/N)` family).
- **Finding 1 is preserved:** flag OFF reproduces 8.4208 kWh bit-for-bit at every
  N; `results/corrected/` and `results/nonce_partition_worst_case/` are untouched.
- **A PoW network could adopt the same slot-idle policy** and obtain a similar
  idle-fraction saving; this extension does not, by itself, demonstrate a
  PoCol-specific advantage over independent-header mining (see the B ≈ C1
  equivalence in `docs/CONTINUOUS_DISTRIBUTED_EFFORT_RESULTS.md`).

## Reproduce

```bash
python experiments/run_scenario_idle.py PoCol 100 1 off        # standard
python experiments/run_scenario_idle.py PoCol 100 1 slot       # idle until next slot
python experiments/run_scenario_idle.py PoCol 100 1 immediate  # no waiting (like PoW)
python -m pytest tests/test_idle_after_range.py -v
```
