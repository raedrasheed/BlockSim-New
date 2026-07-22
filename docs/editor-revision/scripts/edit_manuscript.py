#!/usr/bin/env python3
"""Editor-mediated revision of the BlockSim energy/carbon manuscript.

Produces the CLEAN red manuscript: every inserted/corrected/replacement text run
is coloured RGB(255,0,0)=#FF0000; unchanged text stays black; deleted text is
removed. Figures 1-3 (misleading, crypto-labelled) are removed; Figures 4-7 are
renumbered to 1-4; the carbon figure is regenerated with generic labels; a new
consolidated parameter table and a randomness/CI subsection are added.
"""
import copy
from docx import Document
from docx.shared import RGBColor, Pt
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

SRC = "manuscript.docx"
OUT = "Manuscript_Final_Editor_Revision_Red.docx"
RED = RGBColor(0xFF, 0x00, 0x00)

d = Document(SRC)
paras = d.paragraphs

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
def wq(t): return qn("w:" + t)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def set_run_red(run):
    run.font.color.rgb = RED

def clear_text_runs(p):
    """Remove only runs that carry text (w:t); keep drawing/anchor runs."""
    for r in list(p.runs):
        if r._r.find(wq("t")) is not None:
            r._r.getparent().remove(r._r)

def rewrite_red(p, text):
    """Replace all textual content of a paragraph with a single red run,
    preserving the paragraph style and any anchored drawings."""
    clear_text_runs(p)
    run = p.add_run(text)
    set_run_red(run)
    return run

def delete_paragraph(p):
    p._p.getparent().remove(p._p)

def _copy_rpr(src_run, dst_run):
    src_rpr = src_run._r.find(wq("rPr"))
    if src_rpr is not None:
        # remove existing color, we'll set our own if needed
        new = copy.deepcopy(src_rpr)
        old = dst_run._r.find(wq("rPr"))
        if old is not None:
            dst_run._r.remove(old)
        dst_run._r.insert(0, new)

def surgical_replace(p, old, new, red=True):
    """Find `old` inside one run of p and split it into before/new/after runs,
    colouring the `new` middle run red. Preserves original run formatting."""
    for r in list(p.runs):
        if r.text and old in r.text:
            before, after = r.text.split(old, 1)
            src = r
            # set 'before' on the original run
            r.text = before
            # create middle (new) run
            mid = p.add_run(new)
            _copy_rpr(src, mid)
            if red:
                set_run_red(mid)
            # create after run
            aft = p.add_run(after)
            _copy_rpr(src, aft)
            # move mid and aft to just after src in XML order
            src._r.addnext(aft._r)
            src._r.addnext(mid._r)
            return True
    return False

# ---------------------------------------------------------------------------
# capture paragraph references by index (before structural deletes)
# ---------------------------------------------------------------------------
P = {i: paras[i] for i in range(len(paras))}

# ===========================================================================
# 1. KEYWORDS  (para 16):  "PoW. PoW"  ->  "PoW, PoS"
# ===========================================================================
kw = P[16]
runs = kw.runs
# run[12]='.'  -> ','(red) ; run[14]='PoW' -> 'PoS'(red)
runs[12].text = ","
set_run_red(runs[12])
runs[14].text = "PoS"
set_run_red(runs[14])

# ===========================================================================
# 2. EXPERIMENTAL SETUP  §B (para 93) : remove fixed-power Model1/Model2 framing
# ===========================================================================
rewrite_red(P[93],
    "The primary evaluation uses the economically driven Proof-of-Work model "
    "(Section D) with a ten-minute (600 s) target block interval, together with "
    "the validator-count Proof-of-Stake model (Section E). Transaction workloads "
    "are modelled as a Poisson process, a common assumption in blockchain "
    "performance studies [4], [17]. To assess scaling behaviour, the miner "
    "population is varied over {50, 100, 500, 1000} and the validator population "
    "over {100, 500, 1000, 5000} while the simulation horizon is held fixed at "
    "24 hours; additional sensitivity sweeps vary the coin price, block reward, "
    "and electricity price for PoW and the hardware class and uptime for PoS. All "
    "parameter values are consolidated in Table 1.")

# ===========================================================================
# 3. EXPERIMENTAL SETUP  §C (para 96) : remove fixed-power / 2500 W-per-miner
# ===========================================================================
rewrite_red(P[96],
    "Energy consumption is computed at runtime from the consensus-aware models: "
    "Proof-of-Work energy from the economic model (Eqs. 5-7), driven by the block "
    "reward, coin price, electricity price, hardware efficiency, and the "
    "electricity-spend ratio κ, and Proof-of-Stake energy from the "
    "validator-count model (Eq. 8). Carbon emissions are computed with the "
    "configurable emission factor γ, varied across low, average, and high "
    "grid scenarios (see Results) rather than held fixed, following established "
    "blockchain carbon-footprint analyses [3]. Concretely, carbon is derived via "
    "the standard emission-factor formulation (electricity use × emission "
    "factor), consistent with common GHG accounting practice.")

# ===========================================================================
# 4. RESULTS opening (para 101) : remove miner-count-scaling narrative
#     (image2/image3 anchored here are removed later in the drawing pass)
# ===========================================================================
rewrite_red(P[101],
    "The simulation results demonstrate that integrating energy and "
    "carbon-footprint modelling into BlockSim enables meaningful sustainability "
    "analysis while preserving the simulator's original performance-evaluation "
    "capabilities. The consensus-aware models make the distinct energy drivers of "
    "each family explicit: Proof-of-Work energy is governed by mining economics, "
    "whereas Proof-of-Stake energy is governed by validator count and hardware "
    "power, as detailed below.")

# para 102 : "magnitude difference between the two PoW scenarios..." -> delete
delete_paragraph(P[102])

# ===========================================================================
# 5. RESULTS §A Energy : remove fixed-power totals, lead with economic model
# ===========================================================================
# para 104 intro ("...cumulative totals extracted from EnergyLog were:") -> delete
delete_paragraph(P[104])
# para 105 baseline 3.93->83.84  -> delete
delete_paragraph(P[105])
# para 106 high-throughput 346.70->6934.13 -> delete
delete_paragraph(P[106])

# para 107 : rewrite as economic PoW lead (keeps anchored Figure-4->1 image)
rewrite_red(P[107],
    "Under the economically driven Proof-of-Work model (Section D), total network "
    "energy is governed by mining economics rather than by the number of miners. "
    "Holding the economic inputs fixed over a 24-hour horizon, the PoW network "
    "total is approximately 467.5 GWh and is essentially invariant across "
    "50-1000 miners (95% CI ± 17.1 GWh), while the mean per-miner energy "
    "falls approximately as 1/N.")

# para 108 : rewrite economic PoW continuation, drop Ethereum-labelled sentence,
#            reference renumbered Figure 1
rewrite_red(P[108],
    "Network energy scales linearly with coin price, rising from 155.8 GWh at "
    "20,000 USD/coin to 779.1 GWh at 100,000 USD/coin, and inversely with "
    "electricity price, confirming the economic argument of Section D. Increasing "
    "the number of participating miners therefore redistributes a fixed, "
    "economically bounded energy budget rather than increasing it, correcting the "
    "common misconception that Proof-of-Work energy grows with the raw miner "
    "count. These absolute magnitudes are scenario-based model outputs for the "
    "chosen economic assumptions, not real-world measurements of any specific "
    "cryptocurrency. Figure 1 summarizes the sensitivity of PoW network energy to "
    "the number of miners: the network total is invariant to miner count, while "
    "the mean per-miner energy falls approximately as 1/N.")

# para 109 : PoS -> renumber Figure 5 to Figure 2 (surgical)
assert surgical_replace(P[109], "Figure 5", "Figure 2")

# para 110 : communication -> renumber Figure 6 to Figure 3 (surgical)
assert surgical_replace(P[110], "Figure 6", "Figure 3")

# para 111 : duplicated step-density (Bitcoin/Ethereum) -> delete
delete_paragraph(P[111])
# para 112 : step-density (generic, discusses deleted event-based Fig 1) -> delete
delete_paragraph(P[112])
# para 113 : "Figure 1. shows the event-based cumulative energy ..." -> delete
delete_paragraph(P[113])

# para 114 : "Each of Figures 2-3 compares ..." -> clear text, KEEP anchored
#            image6 (renumbered Figure 3) drawing
clear_text_runs(P[114])

# para 115 : reframe closing energy paragraph to the economic regime
rewrite_red(P[115],
    "Overall, these results reinforce that, in the economically driven regime, "
    "aggregate Proof-of-Work energy is bounded by mining economics - responding "
    "to coin price, block reward, and electricity price rather than to the raw "
    "number of miners - while per-miner energy falls as 1/N. Skewed hashpower "
    "distributions (not shown) redistribute this bounded budget toward dominant "
    "miners without increasing the network total [8].")

# ===========================================================================
# 6. RESULTS §B Carbon : remove fixed-power carbon totals, lead with gamma
# ===========================================================================
# para 117 : carbon lead
rewrite_red(P[117],
    "Because emissions are computed directly from electricity use via the "
    "emission-factor relation C = E·γ (Eq. 9), the carbon results "
    "inherit the energy behaviour: Proof-of-Work emissions are governed by mining "
    "economics and Proof-of-Stake emissions by validator count. For a given "
    "energy level, the dominant driver of carbon is the grid emission factor.")
# para 118 baseline carbon 1.75->37.31 -> delete
delete_paragraph(P[118])
# para 119 high-throughput carbon 154.28->3085.69 -> delete
delete_paragraph(P[119])
# para 120 "carbon curves preserve ... constant grid factor" -> delete
delete_paragraph(P[120])
# para 121 gamma sensitivity : renumber Figure 7 -> Figure 4 (surgical)
assert surgical_replace(P[121], "Figure 7", "Figure 4")

# ===========================================================================
# 7. DISCUSSION (para 129) : wall off naive fixed-power vs economic model
# ===========================================================================
rewrite_red(P[129],
    "A key methodological observation is that Proof-of-Work energy and CO₂ "
    "outcomes depend critically on how mining power is modelled. A naïve "
    "fixed-power baseline that assigns a constant wattage to every miner makes "
    "total network power scale directly with miner count; this is the intuitive "
    "but misleading picture that motivated the economic model, because it "
    "conflates a growing mining industry (more miners ⇒ more total watts) "
    "with the economically constrained reality in which rational miners "
    "collectively spend only up to the fiat value of the block reward. The "
    "economic Proof-of-Work model adopted here instead makes total network energy "
    "invariant to miner count and driven by coin price, reward, and electricity "
    "price (Section D; Figure 1). We therefore report PoW energy through the "
    "economic model and treat the fixed-power, per-miner picture only as a "
    "conceptual contrast, not as a network-level estimate.")

# ===========================================================================
# 8. THREATS TO VALIDITY (para 134) : reconcile with gamma sensitivity
# ===========================================================================
rewrite_red(P[134],
    "Although the analysis evaluates three discrete emission-factor scenarios "
    "(low, average, and high grids), these values do not capture the full "
    "temporal and geographical variability of electricity-grid carbon intensity, "
    "nor do they represent real-time or marginal grid emissions. The resulting "
    "carbon estimates should therefore be interpreted as scenario-based "
    "comparisons rather than location-specific operational measurements.")

# ===========================================================================
# 9. REFERENCES : fix duplicated / stray citation markers
# ===========================================================================
# para 195 : reference 21 has a manually-typed "[21] " prefix (Word auto-numbers)
r0 = P[195].runs[0]
assert r0.text.startswith("[21] ")
r0.text = r0.text[len("[21] "):]
# para 185 : reference 15 has a stray "] " prefix
r0b = P[185].runs[0]
assert r0b.text == "] "
r0b.text = ""

# ===========================================================================
# save intermediate; drawings, captions, table & subsection inserted in step 2
# ===========================================================================
d.save(OUT)
print("stage-1 text edits saved to", OUT)
