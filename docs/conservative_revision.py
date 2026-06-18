"""Conservative red-line revision of the ORIGINAL manuscript DOCX.

Loads the original document and applies *targeted* edits only:
  * phrase-level corrections (run-level, preserving each run's formatting),
  * inserted red paragraphs / subsections for reviewer-requested content,
  * a few added figures (numbered 7-9, preserving original Figures 1-6).

ALL newly added or changed text is coloured RED (C00000). Unchanged original
text and formatting are left intact.

Output: docs/Extending_BlockSim_..._REVISED_redline.docx
"""

import csv
import os
from copy import deepcopy

import docx
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = "/tmp/orig.docx"
OUT = os.path.join(ROOT, "docs",
                   "Extending_BlockSim_Energy_Carbon_REVISED_redline.docx")
FIG = os.path.join(ROOT, "results", "figures")

RED = "C00000"
BASE_FONT = "Times New Roman"
BASE_SIZE = Pt(11)

doc = docx.Document(SRC)
paras = doc.paragraphs

report = []


def load(name):
    with open(os.path.join(ROOT, "results", "data", name)) as f:
        return list(csv.DictReader(f))


# numbers for added results text
pm = {int(r["miner_count"]): r for r in load("pow_miner_scaling_summary.csv")}
pp = {(r["sweep"], r["level"]): r for r in load("pow_price_sensitivity_summary.csv")}
ps = {(r["hw_class"], int(r["validator_count"])): r for r in load("pos_validator_scaling_summary.csv")
      if r["hw_class"] in ("low_power_node", "standard_server", "high_power_server")}
cb = {(r["family"], r["gamma_scenario"]): r for r in load("carbon_gamma_sensitivity_summary.csv")}
cm = {(int(r["peer_degree"]), int(r["tx_rate_hz"]), float(r["block_size_mb"])): r
      for r in load("communication_energy_summary.csv")}
repro = {r["parameter"]: r["value"] for r in load("reproducibility_summary.csv")}


def gwh(k):
    return float(k) / 1e6


# ---------------------------------------------------------------- helpers
def find_para(substr, start=0):
    for i in range(start, len(doc.paragraphs)):
        if substr in doc.paragraphs[i].text:
            return i
    return -1


def _mk_run_elem(template_run, text, red):
    """Create a w:r element cloned from template_run, with given text and color."""
    new_r = deepcopy(template_run._element)
    for child in list(new_r):
        if child.tag == qn("w:t") or child.tag == qn("w:br"):
            new_r.remove(child)
    rpr = new_r.find(qn("w:rPr"))
    if red:
        if rpr is None:
            rpr = OxmlElement("w:rPr"); new_r.insert(0, rpr)
        for c in rpr.findall(qn("w:color")):
            rpr.remove(c)
        color = OxmlElement("w:color"); color.set(qn("w:val"), RED); rpr.append(color)
    t = OxmlElement("w:t"); t.set(qn("xml:space"), "preserve"); t.text = text
    new_r.append(t)
    return new_r


def replace_phrase(substr, old, new, label):
    """Run-level replace of `old` with red `new` inside the paragraph found by substr."""
    i = find_para(substr)
    if i < 0:
        report.append(f"[MISS anchor] {label}: '{substr[:40]}'")
        return False
    para = doc.paragraphs[i]
    for run in list(para.runs):
        if old in run.text:
            before, after = run.text.split(old, 1)
            anchor = run._element
            # insert after-run first, then red-new, so final order is before|new|after
            if after:
                anchor.addnext(_mk_run_elem(run, after, red=False))
            anchor.addnext(_mk_run_elem(run, new, red=True))
            run.text = before
            report.append(f"[OK replace] {label}")
            return True
    # phrase spans runs -> rebuild paragraph text (loses inner sub/superscript but rare)
    full = para.text
    if old in full:
        b, a = full.split(old, 1)
        for r in list(para.runs):
            r._element.getparent().remove(r._element)
        for txt, red in ((b, False), (new, True), (a, False)):
            if txt:
                rr = para.add_run(txt); rr.font.name = BASE_FONT; rr.font.size = BASE_SIZE
                if red:
                    rr.font.color.rgb = RGBColor.from_string(RED)
        report.append(f"[OK replace*spanned] {label}")
        return True
    report.append(f"[MISS phrase] {label}: '{old[:40]}'")
    return False


def insert_after(anchor_substr, text, style=None, red=True, align=None,
                 bold=False, italic=False, size=None, label="", occurrence=1):
    """Insert a new paragraph after the paragraph matching anchor_substr."""
    i, seen = -1, 0
    for j in range(len(doc.paragraphs)):
        if anchor_substr in doc.paragraphs[j].text:
            seen += 1
            if seen == occurrence:
                i = j; break
    if i < 0:
        report.append(f"[MISS anchor-insert] {label}: '{anchor_substr[:40]}'")
        return None
    anchor = doc.paragraphs[i]
    new_p = OxmlElement("w:p")
    anchor._p.addnext(new_p)
    np = Paragraph(new_p, anchor._parent)
    if style:
        try:
            np.style = doc.styles[style]
        except KeyError:
            pass
    if align == "c":
        np.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if text:
        r = np.add_run(text)
        r.font.name = BASE_FONT
        r.font.size = size or BASE_SIZE
        r.bold = bold
        r.italic = italic
        if red:
            r.font.color.rgb = RGBColor.from_string(RED)
    report.append(f"[OK insert] {label}")
    return np


def insert_chain(anchor_substr, items, label=""):
    """Insert several paragraphs in order after an anchor. items = list of dicts."""
    last_anchor = anchor_substr
    created = []
    for k, it in enumerate(items):
        # after the first insert, anchor on the previously created paragraph's text
        anc = last_anchor if k == 0 else created[-1].text[:40]
        p = insert_after(anc, it["text"], style=it.get("style"),
                         red=it.get("red", True), align=it.get("align"),
                         bold=it.get("bold", False), italic=it.get("italic", False),
                         size=it.get("size"), label=f"{label}#{k}")
        if p is None:
            break
        created.append(p)
    return created


def insert_figure_after(anchor_substr, png_stem, fig_no, caption, width=5.7, label=""):
    i = find_para(anchor_substr)
    if i < 0:
        report.append(f"[MISS fig-anchor] {label}")
        return
    anchor = doc.paragraphs[i]
    # image paragraph
    p_img = OxmlElement("w:p"); anchor._p.addnext(p_img)
    para_img = Paragraph(p_img, anchor._parent)
    para_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para_img.add_run().add_picture(os.path.join(FIG, png_stem + ".png"), width=Inches(width))
    # caption paragraph (red) AFTER the image
    p_cap = OxmlElement("w:p"); p_img.addnext(p_cap)
    para_cap = Paragraph(p_cap, anchor._parent)
    para_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = para_cap.add_run(f"Figure {fig_no}. {caption}")
    r.font.name = BASE_FONT; r.font.size = Pt(9.5); r.italic = True
    r.font.color.rgb = RGBColor.from_string(RED)
    report.append(f"[OK figure {fig_no}] {label}")


# ====================================================================
# EDITS
# ====================================================================

# --- Abstract: fix phrase + append red clarifier ---
replace_phrase(
    "controlled experiments are conducted on Proof-of-Work",
    "Proof-of-Work reference models (Bitcoin and Ethereum)",
    "Proof-of-Work reference configurations (Bitcoin, and a historical "
    "Ethereum-like PoW configuration that does not represent current Ethereum, "
    "which has used Proof-of-Stake since The Merge)",
    "abstract phrase")
insert_after(
    "supporting reproducible",
    "In this revised version, the framework additionally distinguishes "
    "economically driven Proof-of-Work (PoW) energy consumption, in which the "
    "expected mining reward and cryptocurrency price are explicit inputs, from "
    "validator-count-driven Proof-of-Stake (PoS) energy consumption; it varies "
    "the carbon emission factor across grid scenarios; and it is positioned as a "
    "scenario-based evaluation tool for preliminary what-if analysis rather than "
    "a precise real-world energy estimator.",
    label="abstract clarifier")

# --- Keywords: append red ---
ki = find_para("Keywords:")
if ki >= 0:
    kp = doc.paragraphs[ki]
    r = kp.add_run(" Proof of Stake, Carbon Footprint, Energy Modeling, Sustainability.")
    r.font.name = BASE_FONT; r.font.size = kp.runs[0].font.size or BASE_SIZE
    r.font.color.rgb = RGBColor.from_string(RED)
    report.append("[OK keywords append]")

# --- Introduction: economic-drivers + PoW/PoS + Merge clarifier ---
insert_after(
    "This study expands upon BlockSim by incorporating energy consumption and carbon footprint metrics",
    "It is important to clarify the energy characteristics of the consensus "
    "mechanisms considered. Proof-of-Work (PoW) energy consumption is "
    "economically driven: a rational miner invests in electricity up to the fiat "
    "value of the expected block reward, so total PoW energy depends primarily on "
    "the cryptocurrency price, the block subsidy, transaction fees, the "
    "electricity price, mining hardware efficiency, and the difficulty/hashrate "
    "equilibrium, rather than on the raw number of miners [16], [4]. "
    "Proof-of-Stake (PoS), by contrast, secures the network through stake and its "
    "energy is dominated by the number of validators kept online and their "
    "hardware power, essentially independent of coin price [19]. Notably, "
    "Ethereum transitioned from PoW to PoS at The Merge (September 2022), reducing "
    "its consensus energy by roughly 99.95% [8]; accordingly, current Ethereum is "
    "not a PoW system, and any PoW Ethereum configuration in this paper is "
    "labelled as a historical Ethereum-like PoW configuration only.",
    label="intro economic drivers")

# --- Background: add red subsection on permissionlessness & Sybil resistance ---
bg_anchor = "explicit modeling of energy consumption and carbon emissions, thus facilitating systematic"
insert_after(bg_anchor,
    "Energy, Permissionlessness, and Sybil Resistance",
    style="Heading 2", label="bg subsection head")
insert_after("Energy, Permissionlessness, and Sybil Resistance",
    "The energy gap between PoW and PoS is tied to how each mechanism resists "
    "Sybil attacks in a permissionless setting. PoW achieves Sybil resistance by "
    "binding influence to an external, costly resource (computation and therefore "
    "electricity), so PoW is not “free”: its permissionlessness is "
    "purchased through continuous resource expenditure, which is precisely why "
    "its energy use is large and coupled to coin price [16], [4]. PoS instead "
    "binds influence to internal economic stake and validator participation, "
    "removing most computational waste but introducing different trust and "
    "economic assumptions [19]. Platt, Platt and McBurney formalise these "
    "tensions as a Sybil-attack vulnerability trilemma among permissionlessness, "
    "Sybil resistance, and freeness [20], and De Vries documents how Ethereum’s "
    "move to PoS illustrates a sustainability path for the wider ecosystem [8]. "
    "These distinctions motivate treating PoW and PoS as two separate energy "
    "models in the remainder of the paper.",
    label="bg subsection body")

# --- Communication Energy Model: add red analysis pointer ---
insert_after(
    "packet-level energy models commonly used in network simulators such as ns-3",
    "Although defined here, communication energy was not analysed in the previous "
    "version. In this revision it is instrumented with explicit transmit/receive "
    "counters for block and transaction messages and analysed in Section "
    "(Results) as a function of transaction rate, block size, and peer "
    "connectivity, and reported separately from consensus energy.",
    label="comm analysis pointer")

# --- Total Energy Consumption: add red PoW economic + PoS subsections ---
te_anchor = "forming a foundation for subsequent carbon footprint analysis"
insert_after(te_anchor, "D. Proof-of-Work Economic Energy Model",
             style="Heading 2", label="pow head")
insert_chain("D. Proof-of-Work Economic Energy Model", [
    {"text": "Because PoW energy is bounded by mining economics, we add an "
             "economic model in which the expected per-block reward in fiat is "
             "R_t = (B_t + F_t) × P_t, where B_t is the block subsidy, F_t the "
             "transaction fees, and P_t the coin price. A rational mining market "
             "spends a fraction κ ∈ [0,1] of this reward on electricity, "
             "giving an economic energy budget per block E_budget = κ · R_t / "
             "C_elec, where C_elec is the electricity price per kWh. When "
             "hardware data are available, a technical bound E_technical = "
             "H_block · ε_hash is derived from the expected hashes per block "
             "(H_block = D · 2^32 for difficulty D) and the per-hash efficiency "
             "ε_hash, and the network per-block energy is E_PoW = "
             "min(E_technical, E_budget), allocated to miner i by its hashpower "
             "share s_i as E_i = s_i · E_PoW. Thus PoW energy depends on coin "
             "price, reward, electricity price, efficiency, and difficulty/"
             "hashrate, and only the distribution (not the total) depends on the "
             "number of miners."},
], label="pow body")
insert_after("only the distribution (not the total) depends on the number of miners",
             "E. Proof-of-Stake Validator Energy Model",
             style="Heading 2", label="pos head")
insert_after("E. Proof-of-Stake Validator Energy Model",
    "For PoS we add a validator-count model in which the network energy is "
    "E_PoS = Σ_v (P_v · T · u_v) / 1000 + E_comm, where P_v is per-validator "
    "hardware power (W), T the horizon (h), u_v ∈ [0,1] the validator uptime, "
    "and E_comm the communication energy. PoS energy therefore scales with the "
    "validator count and hardware power and is independent of coin price [19], "
    "[20].",
    label="pos body")

# --- Carbon section: add red gamma sensitivity paragraph ---
insert_after(
    "consistent with prior studies on blockchain carbon emissions [3], [15]",
    "Because γ captures the carbon intensity of the underlying grid, the same "
    "energy yields very different emissions across regions and times. We "
    "therefore treat γ as an experimental variable with three scenarios: a "
    f"low-carbon grid (γ = {repro['gamma_low']} kgCO₂e/kWh), a global-average "
    f"grid (γ = {repro['gamma_average']}), and a high-carbon grid "
    f"(γ = {repro['gamma_high']}); the sensitivity is reported in the Results.",
    label="carbon gamma para")

# --- Carbon Footprint Analysis: qualify pre-existing 'fixed emission factor' ---
replace_phrase(
    "Carbon emissions closely follow energy consumption because emissions are computed",
    "via a fixed emission factor [3]",
    "via an emission factor that, in this revision, is varied across low/average/"
    "high grid scenarios rather than held fixed [3]",
    "carbon-analysis fixed-factor qualify")

# --- Experimental Setup B: relabel Ethereum model ---
replace_phrase(
    "Two PoW-based reference models were evaluated",
    "Bitcoin (Model 1) and Ethereum (Model 2)",
    "Bitcoin (Model 1) and a historical Ethereum-like PoW configuration "
    "(Model 2). The latter reflects the pre-Merge GPU-mining regime and does not "
    "represent current Ethereum, which has used Proof-of-Stake since The Merge",
    "exp Ethereum relabel")

# --- Experimental Setup C: qualify fixed emission factor ---
replace_phrase(
    "Carbon emissions are computed using a fixed electricity emission factor",
    "fixed electricity emission factor representing the global average carbon intensity",
    "configurable electricity emission factor; in this revision it is varied "
    "across low, average, and high grid scenarios (see Results) rather than held "
    "fixed",
    "exp fixed-emission qualify")

# --- Experimental Setup D: seeds / std / CI ---
replace_phrase(
    "Each experimental run is replicated several times",
    "Each experimental run is replicated several times, employing distinct random "
    "seeds; the reported findings are averaged values, thereby minimizing the "
    "influence of stochastic variability.",
    "Each scenario is replicated across 30 independent random seeds (generated "
    "deterministically as base + i, i = 0..29), and results are reported as the "
    "mean with sample standard deviation and 95% confidence interval (Student t).",
    "exp seeds/CI")

# --- Results A: add red PoW-economic / PoS / scenario note + figures ---
ra_anchor = "whereas Bitcoin’s effective power is substantially lower under the current parameterization"
if find_para(ra_anchor) < 0:
    ra_anchor = "effective power is substantially lower under the current parameterization"
insert_chain(ra_anchor, [
    {"text": "These absolute magnitudes are scenario-based model outputs, not "
             "real-world measurements, and the Ethereum-labelled curve is a "
             "historical Ethereum-like PoW configuration that does not represent "
             "current (Proof-of-Stake) Ethereum. Under the added economic PoW "
             "model, total network energy is governed by mining economics rather "
             "than miner count: holding the economics fixed, the network total is "
             f"approximately {gwh(pm[50]['network_energy_mean_kwh']):.1f} GWh over "
             "24 h and is essentially invariant across 50-1000 miners (95% CI "
             f"± {gwh(pm[50]['network_energy_ci95_kwh']):.1f} GWh), while mean "
             "per-miner energy falls approximately as 1/N. Energy scales linearly "
             "with coin price, rising from "
             f"{gwh(pp[('coin_price','low')]['network_energy_mean_kwh']):.1f} GWh "
             f"at 20,000 USD to "
             f"{gwh(pp[('coin_price','high')]['network_energy_mean_kwh']):.1f} GWh "
             "at 100,000 USD, and inversely with electricity price, confirming "
             "the economic argument of Section D."},
    {"text": "For Proof-of-Stake, the validator-count model yields far smaller "
             "totals: a 1000-validator network of standard 100 W servers consumes "
             f"about {float(ps[('standard_server',1000)]['total_energy_mean_kwh']):.0f} "
             "kWh over 24 h, scaling linearly with validator count "
             f"({float(ps[('standard_server',100)]['total_energy_mean_kwh']):.0f} kWh "
             "at 100 validators). The PoW/PoS energy ratio is on the order of "
             f"{float(repro['pow_pos_ratio']):,.0f}×, consistent with the "
             "order-of-magnitude reductions reported in the literature [16], [19] "
             "and the ~99.95% reduction at Ethereum’s Merge [8]. As an "
             "analytical sanity check, fixed-power configurations reproduce the "
             "closed-form E = P × T exactly (maximum relative error "
             f"{repro['validation_max_rel_error']})."},
], label="results PoW/PoS")

insert_figure_after(
    "the economic argument of Section D",
    "fig_pow_energy_vs_miners", 7,
    "PoW energy vs number of miners (economic model; 30 seeds, 95% CI). Total "
    "network energy is invariant to miner count (a); per-miner energy falls ~1/N "
    "(b).", label="fig7")
insert_figure_after(
    "analytical sanity check, fixed-power configurations reproduce",
    "fig_pos_energy_vs_validators", 8,
    "PoS total energy vs validator count for three hardware classes (30 seeds, "
    "95% CI).", label="fig8")

# --- Communication analysis paragraph + figure (Results A) ---
insert_after("PoS total energy vs validator count for three hardware classes",
    "Communication energy was also analysed. At peer degree 8 with 1 MB blocks it "
    f"grows from {float(cm[(8,1,1.0)]['comm_energy_mean_kwh']):.1f} kWh/day at "
    f"1 tx/s to {float(cm[(8,100,1.0)]['comm_energy_mean_kwh']):.0f} kWh/day at "
    "100 tx/s. Relative to PoW consensus energy this is negligible (ratio ~"
    f"{float(cm[(8,100,1.0)]['comm_to_compute_ratio']):.0e}), but at high "
    "throughput it becomes comparable to PoS consensus energy, so communication "
    "energy matters mainly in PoS and high-throughput settings.",
    label="comm analysis results")
insert_figure_after(
    "communication energy matters mainly in PoS and high-throughput settings",
    "fig_computation_vs_communication", 9,
    "Computation vs communication energy (log-log; peer degree 8, 1 MB blocks, "
    "30 seeds).", label="fig9")

# --- Carbon Footprint Analysis B: gamma sensitivity numbers + figure ---
cba_anchor = "This follows standard emissions accounting (kWh × kgCO₂e/kWh)"
if find_para(cba_anchor) < 0:
    cba_anchor = "standard emissions accounting"
insert_after(cba_anchor,
    "Varying the grid emission factor shows that geography dominates carbon "
    "outcomes for a given energy level. For the PoW reference, daily emissions "
    f"range from {float(cb[('PoW_BTC','low')]['carbon_mean_kg'])/1000:,.0f} t at "
    f"γ = {repro['gamma_low']} to "
    f"{float(cb[('PoW_BTC','high')]['carbon_mean_kg'])/1000:,.0f} t at γ = "
    f"{repro['gamma_high']} (about a "
    f"{float(cb[('PoW_BTC','high')]['carbon_mean_kg'])/float(cb[('PoW_BTC','low')]['carbon_mean_kg']):.0f}× "
    "spread from grid choice alone), while the PoS reference spans only "
    f"{float(cb[('PoS_ETH','low')]['carbon_mean_kg']):.0f}-"
    f"{float(cb[('PoS_ETH','high')]['carbon_mean_kg']):.0f} kg. A single fixed "
    "emission factor is therefore insufficient.",
    label="carbon gamma results")
insert_figure_after(
    "A single fixed emission factor is therefore insufficient",
    "fig_carbon_vs_gamma", 10,
    "Carbon emissions under low/average/high grid emission factors (log axis; "
    "30 seeds, 95% CI).", label="fig10")

# --- Threats to Validity: add red limitation paragraphs ---
tv_anchor = "this degree of abstraction is a commonly accepted compromise within blockchain research"
insert_chain(tv_anchor, [
    {"text": "Additional limitations follow from the revised scope. First, the "
             "framework is a scenario-based explorer; the absolute energy and "
             "carbon values are model outputs for the chosen assumptions and are "
             "not intended to predict the exact real-world consumption of Bitcoin "
             "or Ethereum."},
    {"text": "Second, PoW energy is sensitive to coin price, block reward, "
             "transaction fees, electricity price, mining efficiency, and "
             "difficulty/hashrate dynamics, and to the spend ratio κ; PoS "
             "energy is sensitive to validator count, node hardware, uptime, "
             "redundancy, and communication overhead."},
    {"text": "Third, carbon depends strongly on region- and time-specific grid "
             "mixes; the γ scenarios bracket but do not resolve this "
             "variability. Finally, historical Ethereum-like PoW results must not "
             "be read as current Ethereum, which uses Proof-of-Stake, and "
             "communication energy, while small under PoW, can matter in PoS and "
             "high-throughput scenarios."},
], label="threats additions")

# --- References: append red new entries ---
ref_anchor = "github.com/raedrasheed/BlockSim"
ri = find_para(ref_anchor)
if ri < 0:
    ri = find_para("References")
if ri >= 0:
    template = doc.paragraphs[ri]
    new_refs = [
        "[19] M. Platt, J. Sedlmeir, D. Platt, J. Xu, P. Tasca, N. Vadgama, and "
        "J. I. Ibanez, “The Energy Footprint of Blockchain Consensus "
        "Mechanisms Beyond Proof-of-Work,” IEEE 21st Int. Conf. on Software "
        "Quality, Reliability and Security Companion (QRS-C), 2021, pp. "
        "1135–1144. https://doi.org/10.1109/QRS-C55045.2021.00168",
        "[20] M. Platt, D. Platt, and P. McBurney, “Sybil attack "
        "vulnerability trilemma,” International Journal of Parallel, Emergent "
        "and Distributed Systems, vol. 39, no. 4, pp. 446–460, 2024. "
        "https://doi.org/10.1080/17445760.2024.2352740",
        "[21] A. de Vries, “Cryptocurrencies on the Road to Sustainability: "
        "Ethereum Paving the Way for Bitcoin,” Patterns, vol. 4, no. 1, art. "
        "100633, 2023. https://doi.org/10.1016/j.patter.2022.100633",
    ]
    cur = template
    for txt in new_refs:
        p_new = OxmlElement("w:p"); cur._p.addnext(p_new)
        np = Paragraph(p_new, cur._parent)
        try:
            np.style = template.style
        except Exception:
            pass
        r = np.add_run(txt)
        r.font.name = template.runs[0].font.name if template.runs else BASE_FONT
        r.font.size = template.runs[0].font.size if template.runs else BASE_SIZE
        r.font.color.rgb = RGBColor.from_string(RED)
        cur = np
    report.append("[OK refs append 19-21]")

doc.save(OUT)
print("Saved:", OUT)
print("\n--- EDIT REPORT ---")
for line in report:
    print("  " + line)
misses = [l for l in report if "MISS" in l]
print(f"\nTotal edits: {len(report)}  | misses: {len(misses)}")
