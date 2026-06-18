"""Stage 3 of the red-line revision: add in-text references for the NEW figures
(7-10) and cite reference [21] (De Vries, Patterns) in the text.

Strictly targeted:
  * Does NOT touch Figures 1-6 or their captions / references.
  * Appends short RED sentences that explicitly cite Figures 7-10, each in the
    red paragraph immediately preceding its figure.
  * Cites [21] in the De Vries / Merge discussion. Those added red sentences
    currently cite [8] (which is Gervais in the original list); we correct the
    pointer to [21] (De Vries, Patterns) in exactly the three De Vries sentences.
    Original black [8] (Gervais) citations are left untouched.

Run AFTER conservative_revision.py and fix_math_omml.py. Edits the same file.
"""

import os
import docx
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

F = os.path.join(os.path.dirname(__file__),
                 "Extending_BlockSim_Energy_Carbon_REVISED_redline.docx")
RED = "C00000"

doc = docx.Document(F)
report = []


def find_para(substr):
    for p in doc.paragraphs:
        if substr in p.text:
            return p
    return None


def red_run(text):
    r = OxmlElement("w:r")
    rpr = OxmlElement("w:rPr")
    rf = OxmlElement("w:rFonts")
    rf.set(qn("w:ascii"), "Times New Roman"); rf.set(qn("w:hAnsi"), "Times New Roman")
    rpr.append(rf)
    col = OxmlElement("w:color"); col.set(qn("w:val"), RED); rpr.append(col)
    sz = OxmlElement("w:sz"); sz.set(qn("w:val"), "22"); rpr.append(sz)
    r.append(rpr)
    t = OxmlElement("w:t"); t.set(qn("xml:space"), "preserve"); t.text = text
    r.append(t)
    return r


def append_red_sentence(anchor, sentence, guard):
    """Append a red sentence to the paragraph containing `anchor` (unless guard
    text already present)."""
    p = find_para(anchor)
    if p is None:
        report.append(f"[MISS] anchor not found: {anchor[:40]!r}")
        return
    if guard in p.text:
        report.append(f"[skip] already present: {guard[:30]!r}")
        return
    p._p.append(red_run(sentence))
    report.append(f"[OK] appended figure/cite sentence after {anchor[:32]!r}")


def replace_cite_in_para(anchor, old="[8]", new="[21]"):
    """Replace the first `old` citation with `new` inside the paragraph found by
    anchor (preserves the run's red formatting)."""
    p = find_para(anchor)
    if p is None:
        report.append(f"[MISS] cite anchor not found: {anchor[:40]!r}")
        return
    for run in p.runs:
        if old in run.text:
            run.text = run.text.replace(old, new, 1)
            report.append(f"[OK] {old}->{new} in {anchor[:32]!r}")
            return
    # citation may be in same run as anchor text or a separate run; fallback scan
    report.append(f"[MISS] {old} not found in para {anchor[:32]!r}")


# ----------------------------------------------------- new-figure in-text refs
append_red_sentence(
    "the economic argument of Section D",
    " Figure 7 summarizes the sensitivity of PoW network energy to the number of "
    "miners under the revised economic model: the network total is essentially "
    "invariant to miner count, while the mean per-miner energy falls "
    "approximately as 1/N.",
    "Figure 7 summarizes")

append_red_sentence(
    "consistent with the order-of-magnitude reductions reported in the literature",
    " As shown in Figure 8, PoS total energy scales linearly with the number of "
    "validators across the low-power, standard-server, and high-power hardware "
    "classes.",
    "Figure 8")

append_red_sentence(
    "communication energy matters mainly in PoS and high-throughput settings",
    " Figure 9 compares computational (consensus) energy with communication "
    "energy under the evaluated scenarios on logarithmic axes.",
    "Figure 9 compares")

append_red_sentence(
    "A single fixed emission factor is therefore insufficient",
    " Figure 10 reports the carbon-emission sensitivity under low, average, and "
    "high electricity emission factors γ.",
    "Figure 10 reports")

# ----------------------------------------------------- cite [21] (De Vries)
# 1) Introduction Merge sentence
replace_cite_in_para("reducing its consensus energy by roughly 99.95%")
# 2) Background Sybil/De Vries sentence
replace_cite_in_para("illustrates a sustainability path for the wider ecosystem")
# 3) Results Merge sentence
replace_cite_in_para("reduction at Ethereum")

doc.save(F)
print("Saved:", F)
for line in report:
    print("  " + line)
