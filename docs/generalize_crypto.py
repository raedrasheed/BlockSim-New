"""Stage 6 (conservative): generalize Bitcoin/Ethereum experimental framing to
PoW/PoS scenarios per Reviewer 1's latest comment.

- Abstract: remove the "Bitcoin, and a historical Ethereum-like PoW configuration
  ..." fragment -> "representative PoW and PoS consensus scenarios".
- Generalize all experimental labels (Bitcoin -> PoW baseline scenario; old
  Ethereum PoW -> high-throughput PoW scenario; "Bitcoin vs Ethereum" ->
  comparison of the two PoW scenarios).
- Keep De Vries [21] / Merge only in the Background subsection (para discussing
  Ethereum's transition to PoS); remove the Merge/[21] mention from the
  Introduction and from the Results experiment description.

Changed spans are coloured RED. Original formatting otherwise preserved. No
figures, equations, or section structure are altered. Run AFTER stages 1-5.
"""

import os
from copy import deepcopy
import docx
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

F = os.path.join(os.path.dirname(__file__),
                 "Extending_BlockSim_Energy_Carbon_REVISED_redline.docx")
RED = "C00000"
doc = docx.Document(F)
report = []


def _clone(run_el, text, red):
    r = deepcopy(run_el)
    for ch in list(r):
        if ch.tag in (qn("w:t"), qn("w:br"), qn("w:drawing")):
            r.remove(ch)
    if red:
        rpr = r.find(qn("w:rPr"))
        if rpr is None:
            rpr = OxmlElement("w:rPr"); r.insert(0, rpr)
        for c in rpr.findall(qn("w:color")):
            rpr.remove(c)
        col = OxmlElement("w:color"); col.set(qn("w:val"), RED); rpr.append(col)
    t = OxmlElement("w:t"); t.set(qn("xml:space"), "preserve"); t.text = text
    r.append(t)
    return r


def find_para(anchor):
    for p in doc.paragraphs:
        if anchor in p.text:
            return p
    return None


def replace_red(anchor, old, new, label):
    p = find_para(anchor)
    if p is None:
        report.append(f"[MISS anchor] {label}")
        return
    # single-run
    for run in p.runs:
        if old in run.text:
            i = run.text.find(old)
            before, after = run.text[:i], run.text[i + len(old):]
            run.text = before
            el = run._element
            if after:
                el.addnext(_clone(el, after, red=False))
            if new:
                el.addnext(_clone(el, new, red=True))
            report.append(f"[OK] {label}")
            return
    # spanned fallback (paragraphs here carry no images)
    full = "".join(r.text for r in p.runs)
    if old in full:
        b, a = full.split(old, 1)
        template = p.runs[0]._element
        for r in list(p._p.findall(qn("w:r"))):
            if not r.findall(".//" + qn("w:drawing")):
                r.getparent().remove(r)
        for txt, red in [(b, False), (new, True), (a, False)]:
            if txt:
                p._p.append(_clone(template, txt, red))
        report.append(f"[OK spanned] {label}")
        return
    report.append(f"[MISS text] {label}: {old[:35]!r}")


EDITS = [
    # --- Abstract ---
    ("controlled experiments are conducted on",
     "Proof-of-Work reference configurations (Bitcoin, and a historical "
     "Ethereum-like PoW configuration that does not represent current Ethereum, "
     "which has used Proof-of-Stake since The Merge)",
     "representative PoW and PoS consensus scenarios", "abstract"),

    # --- Introduction: drop Merge/[21] framing, keep PoW/PoS distinction ---
    ("rather than on the raw number of miners",
     "Notably, Ethereum transitioned from PoW to PoS at The Merge (September "
     "2022), reducing its consensus energy by roughly 99.95% [21]; accordingly, "
     "current Ethereum is not a PoW system, and any PoW Ethereum configuration in "
     "this paper is labelled as a historical Ethereum-like PoW configuration only.",
     "Accordingly, this paper treats PoW and PoS as distinct energy regimes and "
     "presents its experiments as generic PoW and PoS consensus scenarios rather "
     "than tying them to any specific cryptocurrency.", "intro"),

    # --- Related work: generalize the prior-studies mention ---
    ("these analyses are often retrospective",
     "particularly Bitcoin and Ethereum [2], [3]",
     "particularly permissionless PoW networks [2], [3]", "related-work"),

    # --- Background: keep the single De Vries/Merge sentence, lightly reworded ---
    ("sustainability path for the wider ecosystem",
     "De Vries documents how Ethereum’s move to PoS illustrates a "
     "sustainability path for the wider ecosystem [21]",
     "De Vries shows how Ethereum’s transition from PoW to PoS after The "
     "Merge illustrates why current PoS systems should not be modelled as "
     "historical PoW systems [21]", "background-devries"),

    # --- Experimental Setup B ---
    ("Two PoW-based reference models were evaluated",
     "Two PoW-based reference models were evaluated: Bitcoin (Model 1) and a "
     "historical Ethereum-like PoW configuration (Model 2). The latter reflects "
     "the pre-Merge GPU-mining regime and does not represent current Ethereum, "
     "which has used Proof-of-Stake since The Merge. Block generation intervals "
     "follow the default targets of each model (Bitcoin: ~10 minutes; Ethereum: "
     "~12–13 seconds),",
     "Two PoW timing scenarios were evaluated: a long-interval PoW baseline "
     "scenario (Model 1) and a short-interval, high-throughput PoW scenario "
     "(Model 2). Block generation intervals follow the default targets of each "
     "scenario (long-interval: ~10 minutes; short-interval: ~12–13 seconds),",
     "exp-setup-B"),

    # --- Energy/Carbon params ---
    ("Energy consumption is computed at runtime using mining-interval",
     "Bitcoin uses a hashrate-and-efficiency-based power derivation, while "
     "Ethereum uses a direct fixed per-miner power configuration",
     "the PoW baseline scenario uses a hashrate-and-efficiency-based power "
     "derivation, while the high-throughput PoW scenario uses a direct fixed "
     "per-miner power configuration", "exp-params"),

    # --- Results: magnitude difference sentence ---
    ("magnitude difference between",
     "between Bitcoin and Ethereum in these runs",
     "between the two PoW scenarios in these runs", "results-magdiff"),

    # --- Results data labels ---
    ("3.93 kWh (50 miners)", "Bitcoin: 3.93 kWh",
     "PoW baseline scenario: 3.93 kWh", "energy-data-baseline"),
    ("346.70 kWh (50 miners)", "Ethereum: 346.70 kWh",
     "High-throughput PoW scenario: 346.70 kWh", "energy-data-highthr"),

    # --- Results: the 83x discussion ---
    ("This behavior aligns with earlier observations",
     "the Ethereum totals are ~83–88× higher than Bitcoin at the same "
     "miner counts",
     "the high-throughput-scenario totals are ~83–88× higher than the "
     "baseline-scenario totals at the same miner counts", "results-83x-1"),
    ("This behavior aligns with earlier observations",
     "The primary reason is that Ethereum was configured with a fixed per-miner "
     "wattage",
     "The primary reason is that the high-throughput scenario was configured with "
     "a fixed per-miner wattage", "results-83x-2"),
    ("This behavior aligns with earlier observations",
     "whereas Bitcoin’s effective power is substantially lower",
     "whereas the baseline scenario’s effective power is substantially lower",
     "results-83x-3"),

    # --- Results: scenario-based caveat (drop Ethereum clause) ---
    ("These absolute magnitudes are scenario-based",
     ", and the Ethereum-labelled curve is a historical Ethereum-like PoW "
     "configuration that does not represent current (Proof-of-Stake) Ethereum",
     "", "results-caveat"),

    # --- Results: remove Merge/[21] from the experiment description ---
    ("The PoW/PoS energy ratio is on the order of",
     " and the ~99.95% reduction at Ethereum’s Merge [21]", "",
     "results-merge21"),

    # --- Results: block-interval paragraph ---
    ("modeled block interval is much shorter",
     "Because Ethereum’s modeled block interval is much shorter than "
     "Bitcoin’s, Ethereum produces hundreds of blocks within the same "
     "simulation window while Bitcoin produces tens of blocks. Consequently, "
     "energy per block is less extreme than total energy (since Ethereum divides "
     "its total energy across many more blocks). This effect is visible in the "
     "“step density” of event-based curves: Ethereum rises more "
     "frequently due to more block events.",
     "Because the high-throughput PoW scenario’s modeled block interval is "
     "much shorter than the baseline scenario’s, it produces hundreds of "
     "blocks within the same simulation window while the baseline scenario "
     "produces tens of blocks. Consequently, energy per block is less extreme "
     "than total energy (since the high-throughput scenario divides its total "
     "energy across many more blocks). This effect is visible in the “step "
     "density” of event-based curves: the high-throughput scenario rises "
     "more frequently due to more block events.", "results-blockinterval"),

    # --- Figure 1 in-text reference ---
    ("event-based cumulative energy sampled at block timestamps for both",
     "for both models and all miner counts. Ethereum curves rise much more "
     "steeply",
     "for both PoW scenarios and all miner counts. The high-throughput-scenario "
     "curves rise much more steeply", "fig1-ref"),

    # --- Figures 2-3 in-text reference ---
    ("compares Bitcoin vs Ethereum for the same miner count",
     "Each figure 2-3 compares Bitcoin vs Ethereum for the same miner count 50 "
     "miners and 1000 miners respectively",
     "Each of Figures 2–3 compares the two PoW scenarios for 50 miners and "
     "1000 miners respectively", "fig23-ref"),

    # --- Carbon data labels ---
    ("1.75 kg CO", "Bitcoin: 1.75 kg",
     "PoW baseline scenario: 1.75 kg", "carbon-data-baseline"),
    ("154.28 kg CO", "Ethereum: 154.28 kg",
     "High-throughput PoW scenario: 154.28 kg", "carbon-data-highthr"),

    # --- Discussion ---
    ("A key observation in the",
     "A key observation in the Bitcoin vs Ethereum comparison is",
     "A key observation in the comparison of the two PoW scenarios is",
     "disc-1"),
    ("A key observation in the",
     "In these experiments, Ethereum is configured with a fixed high per-miner "
     "power",
     "In these experiments, the high-throughput PoW scenario is configured with a "
     "fixed high per-miner power", "disc-2"),
    ("A key observation in the",
     "This makes Ethereum’s cumulative energy and carbon footprint "
     "substantially larger than Bitcoin in absolute terms, even though Ethereum "
     "also produces many more blocks",
     "This makes the high-throughput scenario’s cumulative energy and carbon "
     "footprint substantially larger than the baseline scenario in absolute "
     "terms, even though it also produces many more blocks", "disc-3"),

    # --- Threats to Validity ---
    ("region- and time-specific grid mixes",
     "Finally, historical Ethereum-like PoW results must not be read as current "
     "Ethereum, which uses Proof-of-Stake, and communication energy",
     "Finally, the PoW results represent scenario configurations rather than any "
     "specific cryptocurrency, and communication energy", "threats"),
]

for anchor, old, new, label in EDITS:
    replace_red(anchor, old, new, label)

doc.save(F)
print("Saved:", F)
for line in report:
    print("  " + line)
print("misses:", sum(1 for l in report if "MISS" in l))
