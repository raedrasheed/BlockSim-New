# Stage 9 — Chapter Integration Plan

How the frozen Stage-8S/8U evidence is integrated into the existing draft-44 structure.
Integrate into existing chapters; do not create duplicate chapters. Every inserted or
modified run, caption, table, equation, reference and number is red (RGB FF0000) in the
redline copy. Unchanged text keeps its colour. The authoritative `draft-44-00.docx` is
never edited in place.

## Existing thesis structure (para indices in the merged document.xml)

| Component | Body para | Stage-9 treatment |
|---|---|---|
| English Abstract | 31–35 | REWRITE (red): add Stage-8S/8U bounded findings + trade-off framing |
| Arabic Abstract الملخص | 37–40 | REWRITE (red): exact scientific mirror, RTL preserved |
| Ch1 Introduction | 328–374 | UPDATE: problem/motivation/RQ1–RQ5/objectives/contributions/scope/limitations/organisation |
| Ch2 Technical Background | 375–415 | No change (still supported) |
| Ch3 Literature Review | 416–1082 | LIGHT UPDATE: distinguish deployed PoW / legacy BlockSim PoW / economic PoW models / matched same-template PoW control; reference audit for any modified citation |
| Ch4 System Model | 1083–1187 | No substantive change; metrics section cross-referenced from results |
| Ch5 PoCol Design | 1188–1485 | UPDATE §5.6.6: add useful-work-aware target, coarse reassignment, single-handoff policy as evaluated operating-policy refinements; distinguish core mechanism / experimental refinements / historical variants / final evaluated policy |
| Ch6 Implementation & Setup | 1486–1555 | UPDATE §6.4/§6.7/§6.9: document Stage-8S and Stage-8U experiments separately (scenarios, scale, comparators, inferential design); explain W00/W01 and why legacy BlockSim PoW was not used for the matched comparison |
| Ch7 Results & Evaluation | 1556–1716 | MAJOR UPDATE: retain Stage-6A §7.3/§7.4; bound the legacy throughput-superiority claim; INSERT Stage-8S and Stage-8U results subsections with two result boxes, Tables 7.2–7.8, Figures 7.10–7.19; extend discussion §7.6 with the trade-off |
| Ch8 Conclusion & Future Work | 1717–1741 | UPDATE: summary, RQ1–RQ5 answer matrix (Table 8.1), contributions, conclusion, future work |
| References | 1742+ | ADD only verified citations; reference audit |

## Central thesis claim (applied throughout)

PoCol provides coordinated, disjoint nonce-domain evaluation under a common immutable
template, eliminating exact-input duplication in the honest evaluated configuration and
enabling substantial reductions in **calculated** energy through low-power-state
residency. The evidence demonstrates a measurable **energy/work-efficiency versus
service/latency trade-off**: lower physical work and energy against longer
solution-discovery latency and lower accepted-block production — not unconditional
superiority.

## Chapter 1 — the five research questions (replace the current RQ1–RQ3)

* **RQ1** — Does coordinated disjoint nonce evaluation eliminate exact-input duplication
  under one common immutable template?
* **RQ2** — How much calculated energy reduction is associated with low-power-state
  residency within PoCol?
* **RQ3** — How much block production is retained relative to a no-floor PoCol control?
* **RQ4** — How does PoCol compare with a matched same-template PoW control in energy,
  physical work, block production and round latency?
* **RQ5** — What operational limits arise from floor management, reserve activation,
  reassignment and static contiguous range ownership?

Each is phrased as an open question, never as already proven. Objectives O1–O3 and
contributions C1–C5 are updated to align (C4 names the Stage-8S within-PoCol and Stage-8U
matched-PoW experiments; the empirical contribution is the quantified trade-off).

## Chapter 7 — results organisation (four subsections, inserted after the retained Stage-6A material)

* **A. Work and integrity properties** — duplicate elimination (Stage-6A H1 + Stage-8U
  P02 = 0 duplicates), physical-evaluation efficiency (Table 7.6), integrity gates
  (60/60). 
* **B. Best within-PoCol energy/throughput result (Stage-8S)** — Result Box 1 (90.39%
  retention vs no-floor PoCol control; 55.05% calculated energy reduction vs within-run
  power-null), Table 7.3, energy decomposition Table 7.5, with the immediate bounding
  statements and the unsatisfied joint rule.
* **C. Matched PoW versus PoCol comparison (Stage-8U)** — Result Box 2 (44.95% less total
  energy, ~19.3% less energy per accepted block, ~87.9% fewer physical evaluations, zero
  duplicates vs W01; 67.70% of blocks; 5.219× median round duration), Table 7.4, Figures
  7.10–7.18, with the not-licensed verdict.
* **D. Policy evolution and operational limitations** — Table 7.8 + Figure 7.19; static
  vs useful floor (Figure 7.16), churn (Figure 7.17); all failed limits kept visible.

### Result Box 1 (verbatim, red)
> PoCol retained 90.39% of the accepted-block output of the no-floor PoCol control while
> producing a mean calculated low-power-state energy reduction of 55.05%.
> _Block production is relative to the no-floor PoCol control. Energy reduction is
> relative to the within-run power-null reference. The joint Stage-8S operational rule
> was not fully satisfied._

### Result Box 2 (verbatim, red)
> Relative to the active-capacity-matched same-template PoW control, PoCol used 44.95%
> less total energy and approximately 19.3% less energy per accepted block, with
> approximately 87.9% fewer physical evaluations and zero exact-input duplicates.
> _PoCol produced 67.7% of the control's accepted blocks and had a 5.219-times larger
> median round duration. The joint Stage-8U claim was not licensed._

## Two PoW layers must be kept distinct everywhere

1. **Legacy BlockSim PoW abstraction** — exponential mining-time model, no matched
   templates; source of the draft-44 §7.3 throughput figures. Retained only as the
   original comparative-throughput context, explicitly labelled legacy.
2. **Matched same-template PoW control (Stage-8U W00/W01)** — same template, target,
   difficulty, domain, horizon, seeds, rates and powers; the authoritative energy/work
   comparator. W01 (active-capacity-matched) is the primary service/energy comparator.

## Redline mechanics

* Tracked changes: `<w:ins>` / `<w:del>` with `w:author="Stage9 Integration"`, red run
  colour `<w:color w:val="FF0000"/>` on inserted runs.
* Preserve styles, headings, equations, page size/margins, section breaks, Arabic RTL,
  citations, bibliography, TOC structure, cross-references, existing figure numbering.
* Figures inserted as PNG (300 dpi) with SVG retained in the source tree; captions and
  "Author's simulation results" source line in red.
