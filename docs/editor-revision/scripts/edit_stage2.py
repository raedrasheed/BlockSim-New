#!/usr/bin/env python3
"""Stage 2: figure removal, caption renumbering, parameter table, randomness
subsection. Operates on the stage-1 output in place."""
import copy
from docx import Document
from docx.shared import RGBColor, Pt
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

FILE = "Manuscript_Final_Editor_Revision_Red.docx"
RED = RGBColor(0xFF, 0x00, 0x00)
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

d = Document(FILE)
root = d.element
def wq(t): return qn("w:" + t)

# ---------------------------------------------------------------------------
# A. Remove old Figures 1-3 : image drawings rId8/9/10 + caption AlternateContents
# ---------------------------------------------------------------------------
DEL_EMBEDS = {"rId8", "rId9", "rId10"}
DEL_CAP_PREFIX = ("Figure 1:", "Figure 2:", "Figure 3:")

removed_imgs, removed_caps = [], []

# remove caption AlternateContents
for ac in list(root.iter("{http://schemas.openxmlformats.org/markup-compatibility/2006}AlternateContent")):
    cap = "".join(t.text or "" for t in ac.iter(wq("t")))
    if cap.startswith(DEL_CAP_PREFIX):
        run = ac.getparent()          # the w:r
        run.getparent().remove(run)   # remove whole run
        removed_caps.append(cap[:30])

# remove image drawings (the run holding the w:drawing with the target blip)
for dr in list(root.iter(wq("drawing"))):
    blip = dr.find(".//" + qn("a:blip"))
    emb = blip.get(R + "embed") if blip is not None else None
    if emb in DEL_EMBEDS:
        run = dr.getparent()          # w:r
        run.getparent().remove(run)
        removed_imgs.append(emb)

print("removed caption boxes:", removed_caps)
print("removed image runs   :", removed_imgs)

# ---------------------------------------------------------------------------
# B. Renumber kept captions 4->1, 5->2, 6->3, 7->4 ; colour the number red
# ---------------------------------------------------------------------------
CAP_MAP = {"Figure 4.": "Figure 1.", "Figure 5.": "Figure 2.",
           "Figure 6.": "Figure 3.", "Figure 7.": "Figure 4."}

def redden_run(r_el):
    rpr = r_el.find(wq("rPr"))
    if rpr is None:
        rpr = OxmlElement("w:rPr"); r_el.insert(0, rpr)
    for c in rpr.findall(wq("color")):
        rpr.remove(c)
    col = OxmlElement("w:color"); col.set(qn("w:val"), "FF0000"); rpr.append(col)

caps_done = []
for ac in list(root.iter("{http://schemas.openxmlformats.org/markup-compatibility/2006}AlternateContent")):
    full = "".join(t.text or "" for t in ac.iter(wq("t")))
    for old, new in CAP_MAP.items():
        if full.startswith(old):
            # each w:t holds the whole caption; split its run into red number + black rest
            for wt in list(ac.iter(wq("t"))):
                if wt.text and wt.text.startswith(old):
                    rest = wt.text[len(old):]
                    r_el = wt.getparent()            # w:r
                    # set this run to the red number
                    wt.text = new
                    redden_run(r_el)
                    # create a sibling run (black) with the remaining text
                    new_r = copy.deepcopy(r_el)
                    # remove color from the copy
                    rpr = new_r.find(wq("rPr"))
                    if rpr is not None:
                        for c in rpr.findall(wq("color")):
                            rpr.remove(c)
                    new_r.find(wq("t")).text = rest
                    new_r.find(wq("t")).set(qn("xml:space"), "preserve")
                    r_el.addnext(new_r)
            caps_done.append(f"{old}->{new}")
            break
print("captions renumbered:", caps_done)

# ---------------------------------------------------------------------------
# C. Insert consolidated parameter table (Table 1) after Exp-Setup intro
# ---------------------------------------------------------------------------
def find_para(prefix):
    for p in d.paragraphs:
        if p.text.strip().startswith(prefix):
            return p
    raise RuntimeError("not found: " + prefix)

intro = find_para("To evaluate the effectiveness of the proposed energy and carbon")

HEADER = ["Parameter", "Symbol", "Value / range", "Unit",
          "Model / scenario", "Type", "Source / justification"]
ROWS = [
 ["Block subsidy", "B_t", "3.125 (swept 1.5625 / 3.125 / 6.25)", "coin/block", "PoW economic", "Input (swept)", "Post-2024-halving anchor (assumption)"],
 ["Avg. transaction fees", "F_t", "0.30 (±40% across seeds)", "coin/block", "PoW economic", "Stochastic", "Scenario assumption"],
 ["Coin price", "P_t", "60,000 (swept 20,000 / 60,000 / 100,000; ±5% across seeds)", "USD/coin", "PoW economic", "Input (swept)/stochastic", "Scenario assumption"],
 ["Electricity price", "C_elec", "0.05 (swept 0.03 / 0.05 / 0.10)", "USD/kWh", "PoW economic", "Input (swept)", "Industrial-mining assumption"],
 ["Electricity-spend ratio", "κ", "0.80", "-", "PoW economic", "Deterministic input", "Assumption, κ ∈ [0,1]"],
 ["Mining efficiency", "-", "21.5", "J/TH", "PoW economic (technical bound)", "Deterministic input", "ASIC-class anchor (assumption)"],
 ["Block interval (PoW)", "-", "600", "s", "PoW economic", "Deterministic input", "~10-min target (assumption)"],
 ["Miner count", "N", "50; 100; 500; 1000", "miners", "PoW economic", "Swept", "Small-to-moderate networks [6]"],
 ["Per-miner power (fixed-power contrast baseline)", "P_miner", "2500 (illustrative)", "W", "Naïve fixed-power baseline", "Deterministic input", "Contrast only; not used for network-level estimates"],
 ["Validator power", "P_v", "10 / 100 / 500 (low / standard / high; ±10% across seeds)", "W", "PoS validator", "Input (swept)/stochastic", "Hardware-class assumptions"],
 ["Validator uptime", "u_v", "0.99 (swept 0.90 / 0.99 / 1.00; ±1% across seeds)", "-", "PoS validator", "Input/stochastic", "Assumption"],
 ["Validator count", "V", "100; 500; 1000; 5000", "validators", "PoS validator", "Swept", "-"],
 ["Validator gossip message rate", "-", "5", "msg/validator/s", "PoS validator", "Deterministic input", "Attestation/gossip assumption"],
 ["Peer degree", "-", "4; 8; 16", "peers", "Communication", "Swept", "Connectivity assumption"],
 ["Block size", "-", "0.5; 1; 2", "MB", "Communication", "Swept", "-"],
 ["Transaction rate", "-", "1; 10; 100", "tx/s", "Communication", "Swept", "-"],
 ["Transaction size", "-", "512", "bytes", "Communication", "Deterministic input", "Assumption"],
 ["TX energy per message", "e_tx", "0.10", "J/msg", "Communication", "Deterministic input", "Radio/NIC order-of-magnitude [11]"],
 ["RX energy per message", "e_rx", "0.05", "J/msg", "Communication", "Deterministic input", "Radio/NIC order-of-magnitude [11]"],
 ["TX energy per byte", "-", "2×10⁻⁶", "J/byte", "Communication", "Deterministic input", "[11]"],
 ["RX energy per byte", "-", "1×10⁻⁶", "J/byte", "Communication", "Deterministic input", "[11]"],
 ["Nodes (comm. overlay)", "-", "500", "nodes", "Communication", "Deterministic input", "-"],
 ["Grid emission factor", "γ", "0.05 / 0.475 / 0.82 (low / average / high)", "kgCO₂e/kWh", "Carbon", "Swept", "IEA/IPCC ranges [13], [14]"],
 ["Transactions per block (normalization)", "-", "2000", "tx/block", "Carbon", "Deterministic input", "Throughput assumption"],
 ["Simulation horizon", "T", "86,400 (24 h)", "s", "All models", "Deterministic input", "Common horizon (normalizes energy totals)"],
 ["Random seeds", "-", "30 (20260101-20260130; base + i, i = 0..29)", "-", "All stochastic runs", "-", "Reproducible seeding"],
 ["Confidence interval", "-", "95% (Student-t across seeds)", "-", "All stochastic runs", "-", "Across-seed CI of the mean"],
]

tbl = d.add_table(rows=1 + len(ROWS), cols=len(HEADER))
try:
    tbl.style = d.styles["Table Grid"]
except KeyError:
    pass

def set_cell(cell, text, bold=False):
    cell.text = ""
    p = cell.paragraphs[0]
    run = p.add_run(text)
    run.font.color.rgb = RED           # whole table is NEW -> red
    run.font.size = Pt(8)
    if bold:
        run.font.bold = True

for j, h in enumerate(HEADER):
    set_cell(tbl.rows[0].cells[j], h, bold=True)
for i, row in enumerate(ROWS, start=1):
    for j, val in enumerate(row):
        set_cell(tbl.rows[i].cells[j], val)

# lead sentence + caption (red, new)
lead = d.add_paragraph()
lead.style = d.styles["RSR"]
lr = lead.add_run("Table 1 consolidates every parameter required to reproduce "
                  "the experiments, distinguishing economic-PoW, fixed-power "
                  "baseline, PoS, communication, and carbon parameters, and "
                  "marking each as a deterministic input, a swept level, or a "
                  "stochastic (seed-varying) quantity.")
lr.font.color.rgb = RED

cap = d.add_paragraph()
cap.style = d.styles["RSR"]
cr = cap.add_run("Table 1. Consolidated experimental parameters (all values "
                 "verified against the released code, CSV outputs, and equations).")
cr.font.color.rgb = RED
cr.font.bold = True

spacer = d.add_paragraph()

# move lead, table, caption, spacer to right after the intro paragraph
intro._p.addnext(lead._p)
lead._p.addnext(tbl._tbl)
tbl._tbl.addnext(cap._p)
cap._p.addnext(spacer._p)

# ---------------------------------------------------------------------------
# D. Insert 'E. Randomness, Replications, and CI Construction' subsection
#    after the §D evaluation-metrics paragraph
# ---------------------------------------------------------------------------
metrics = find_para("The subsequent metrics are gathered for each simulation")

head = d.add_paragraph()
head.style = d.styles["Heading 2"]
hr = head.add_run("E. Randomness, Replications, and Confidence-Interval Construction")
hr.font.color.rgb = RED

body = d.add_paragraph()
body.style = d.styles["RSR"]
br = body.add_run(
    "The consensus-aware energy equations (Sections D and E) are deterministic "
    "in their inputs: for fixed power and horizon a configuration reproduces the "
    "closed-form E = P·T exactly (maximum relative error 0.00 across the "
    "fixed-power sanity check). The reported 30-seed confidence intervals "
    "therefore do not arise from the closed-form expressions themselves, but from "
    "scenario-level stochasticity in the inputs a protocol designer cannot fix "
    "exactly. For Proof-of-Work, each seed draws the number of blocks realized in "
    "the horizon from a Poisson distribution around the horizon divided by the "
    "target block interval, and applies independent Gaussian jitter to the coin "
    "price (standard deviation 5%) and to the average transaction fees (standard "
    "deviation 40%); hashpower shares are drawn from a Dirichlet(1,…,1) "
    "distribution, which affects the per-miner allocation. For Proof-of-Stake, "
    "each seed applies Gaussian jitter to per-validator power (standard deviation "
    "10%) and uptime (standard deviation 1%). Each of the 30 seeds "
    "(20260101-20260130, generated deterministically as base + i, i = 0..29) "
    "drives one independent realization, and the reported intervals are "
    "Student-t 95% confidence intervals of the mean across seeds. Purely "
    "deterministic quantities - such as the fixed-power check E = P·T - reproduce "
    "identically across seeds and are reported as exact values without confidence "
    "intervals.")
br.font.color.rgb = RED

metrics._p.addnext(head._p)
head._p.addnext(body._p)

d.save(FILE)
print("stage-2 saved:", FILE)
print("paras now:", len(d.paragraphs), "tables now:", len(d.tables))
