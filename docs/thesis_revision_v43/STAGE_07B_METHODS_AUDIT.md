# Stage 7B — Methods Audit (Chapter 6) (§4)

Verifies that the methods narrative in `Raed-Rasheed-draft-44-00.docx` describes the **frozen
experiment actually executed** (Stage 4–6A), replacing the obsolete ad-hoc PoW-vs-PoCol
design in place (red).

## Replaced design paragraph (§6.4)

The obsolete sentence *"The experiment was designed to compare the performance of two
consensus protocols …"* (a 10-log ad-hoc comparison) was **replaced in place** with a red
paragraph specifying the executed frozen matrix. The following required methods elements are
present as active (red) text:

| Element | Present | Wording basis |
|---------|:---:|---------------|
| 10,000 s fixed horizon | ✅ | "10,000-second horizon" |
| 141 TH/s aggregate hash rate | ✅ | "aggregate hash rate 141 TH/s" |
| 21.5 J/TH efficiency | ✅ | "efficiency 21.5 J/TH" |
| Aggregate power 3031.5 W | ✅ | (Ch7 §7.4.1: "→ 3031.5 W") |
| Integer per-miner apportionment | ✅ | "Integer per-miner hash-rate apportionment" |
| 63 scientific-semantics groups | ✅ | "63 scientific-semantics groups" |
| 30 frozen master seeds | ✅ | "30 frozen master seeds" |
| 1,890 physical executions | ✅ | "1,890 physical executions" |
| Unique run-execution hashes | ✅ | "unique run-execution hash" |
| Statistical unit = one physical run; seed-matched | ✅ | "the statistical unit is one physical run … seed-matched" |
| B3/C1 shared execution (one dataset) | ✅ | "B3 and C1 share one physical execution … never counted as independent samples" |
| Exact candidate accounting | ✅ | "exact candidate accounting" |
| Exact B2 circular-domain exhaustion | ✅ | "exact B2 circular-domain exhaustion" |
| Active/idle/offline power states | ✅ | "explicit active/idle/offline power states" |
| Inactive-domain semantics | ✅ | "inactive-domain semantics" |
| Zero-block/NA policy | ✅ | "strict zero-block/NA policy" |
| H1: 30 independent seed clusters / 150 pairs | ✅ | "30 independent master-seed clusters (150 physical seed-matched pairs across five miner counts)" |
| Bootstrap + permutation (10,000 replicates) | ✅ | "paired seed-matched bootstrap and permutation tests (10,000 replicates each)" |
| Holm multiplicity control | ✅ | "Holm multiplicity control" |
| H7 secondary single-height diagnostic | ✅ | "the propagation-delay stale quantity is a secondary single-height diagnostic" |

## Consistency with results chapter

The methods figures are numerically consistent with the Chapter 7 A1 statement
(141 TH/s × 21.5 J/TH × 10,000 s = 3031.5 W → 8.420833333 kWh) and with the corrected
Tables 7.1–7.3 and Figures 7.4–7.10.

## Verdict

**METHODS AUDIT: PASS** — Chapter 6's design narrative describes the executed frozen
experiment; all required methods elements are present as active red text; no obsolete 10-log
ad-hoc PoW-vs-PoCol design survives.
