# Stage 9 — Obsolete / Overstated Claim Audit

Full-document sweep of draft-44 for the directive's mandated terms. Each surviving claim
is classified SUPPORTED / SUPPORTED_WITH_BOUND / SUPERSEDED / DELETE / REWRITE /
NEEDS_CITATION / UNRESOLVED. draft-44 was already conservatively corrected in Stage 7B, so
most energy/PoW claims are pre-bounded; the sweep confirms this and pins the few residual
edits.

## 1. Term sweep results (source: merged document.xml plain text)

| Term | Hits | Finding |
|---|---|---|
| `superior` | 8 | All already bounded or negated. [895] "does not imply PoCol is universally superior"; [1692] "cannot categorically state that PoCol is superior to PoS or PBFT". No action beyond keeping the negation. |
| `equivalent` | 4 | Literature-table majority-control usage ([540]) and general prose; none claim PoW-equivalent PoCol performance/security. No change. |
| `maintains performance` / `maintain … perform` | 0 material | No "maintains PoW performance" claim present. |
| `Bitcoin` | 39 | All in literature/background/energy-context (real deployed PoW). None attributes a Stage-8U/8S matched-control result to Bitcoin. Stage-9 insertions must preserve this: matched control is never Bitcoin. |
| `Ethereum` | present | Literature/background only. No change. |
| `PoW` | many | §7.3 throughput narrative uses the legacy BlockSim PoW abstraction — see CM11/CM12. Elsewhere bounded. |
| `throughput` | 58 | [1592]/[1595] §7.3.1 legacy throughput-superiority narrative — SUPERSEDED by Stage-8U matched control; REWRITE/bound. Other uses descriptive. |
| `energy reduction` | 14 | Consistently tied to idle/low-power states or reduced participation (already bounded). Stage-9 adds Stage-8S 55.05% and Stage-8U 44.95% with explicit comparators. |
| `efficient` / `efficiency` | 27 | Mostly "energy-efficient consensus" topic framing. No unsupported "highly efficient" superiority claim. |
| `duplicate` / `redundan` | 62 | Duplicate-elimination framing, supported by Stage-6A H1 and Stage-8U P02 = 0. SUPPORTED. |
| `security` / `security floor` | 149 | Design-level analysis (Ch5 §5.11) and literature. No formal security/Sybil/incentive PROOF is claimed. Stage-9 adds explicit "no formal chain-security / incentive-compatibility proof" bound. |
| `nonce partition` / partitioning | few | [33]/[1608] already state "partitioning alone does not reduce energy". SUPPORTED. |
| `8.420833333` | 11 | Stage-6A A1 energy invariant. SUPPORTED (retained macro-scale finding). |
| `40.408`, `33.078`, `7.90`, `PoCol-E` | 0 | Not present in draft-44 (already removed in earlier corrections). No action. |
| `67.7`, `19.3` | reference nums only | Not present as result claims; Stage-9 ADDS 67.70% (Stage-8U block ratio) and ~19.3% (energy per block) with W01 comparator. |
| `90%`, `55%`, `44.95%`, `90.39`, `55.05` | 0 | Not yet in draft-44; Stage-9 INSERTS with exact comparators per numeric provenance. |
| `A1` | present | Stage-6A result label; retained. |
| `Proof of Collaboration` / `Proof-of-Collaboration` | many | Correct algorithm name throughout. No new name introduced. |

## 2. Residual edits required (the short list)

| ID | Location | Issue | Action |
|---|---|---|---|
| OC1 | §7.3.1 [1592] | "PoCol performs equally as well as PoW … better at higher counts" (legacy BlockSim PoW abstraction) | REWRITE (red): label legacy abstraction; state the matched same-template PoW control (Stage-8U) shows PoCol produces 67.70% of W01's blocks at 5.219× median round duration |
| OC2 | §7.3.1 [1595] | "improved throughput performance … increasing quantity of useful work" | REWRITE (red): reframe as work-efficiency (1,173.2 vs 208.7 accepted blocks per million evaluations), not raw throughput superiority |
| OC3 | §7.2 [1563] | evaluation restricted to miner counts 100–500 (Stage-6A) | RETAIN as Stage-6A macro layer; ADD Stage-8S/8U reduced-scale (20-miner) evaluation as a distinct, newer confirmatory layer |
| OC4 | §1.3 [342] RQ2 | "reduce block-production energy relative to classical PoW across 100–500" | REWRITE to RQ1–RQ5 (directive), removing implied energy-vs-PoW proof |
| OC5 | Abstract/§8 | no quantified low-power-state reduction stated | INSERT Stage-8S 55.05% and Stage-8U 44.95% with comparators |

## 3. Nothing to delete outright

No fabricated number, unsupported superiority claim, or PoW-equivalence claim survives in
draft-44 that requires deletion; the earlier Stage-7B correction already removed the
obsolete PoW-versus-PoCol energy/carbon table (placeholder retained at para [1542]). All
Stage-9 changes are bounded rewrites and additive integration of the frozen Stage-8S/8U
evidence.
