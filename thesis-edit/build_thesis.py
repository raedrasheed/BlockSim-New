#!/usr/bin/env python3
"""Bounded related-work addition to the PhD thesis. New material RED (#FF0000);
existing content preserved; citations 133-148 shifted +5; new refs 133-137."""
import re, copy
import docx
from docx.shared import RGBColor, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.document import Document as _Doc
from docx.table import _Cell, Table
from docx.text.paragraph import Paragraph

FILE = "Raed-Rasheed-draft-37-Related-Work-Added.docx"
RED = RGBColor(0xFF, 0x00, 0x00)
d = docx.Document(FILE)

# citation placeholder -> final number
C = {"PARALLEL_POW": "133", "STRONGCHAIN": "134", "COLLABORATIVE_POW": "135",
     "POTS": "136", "GREEN_POW": "15", "APOW": "137"}

def redden(run): run.font.color.rgb = RED

def iter_block_items(parent):
    el = parent.element.body if isinstance(parent, _Doc) else (parent._tc if isinstance(parent, _Cell) else parent)
    for child in el.iterchildren():
        if child.tag == qn('w:p'): yield Paragraph(child, parent)
        elif child.tag == qn('w:tbl'): yield Table(child, parent)

# ---------------------------------------------------------------------------
# STEP A: shift existing citations 133-148 -> +5 (retain original color).
#   Skip the bibliography table (last table) - handled in STEP B.
# ---------------------------------------------------------------------------
def shift_num(m):
    n = int(m.group(1))
    return f"[{n+5}]" if 133 <= n <= 148 else m.group(0)

bib_tbl = d.tables[-1]._tbl
def shift_runs_in_par(p):
    for r in p.runs:
        if r.text and '[' in r.text:
            new = re.sub(r'\[(\d{1,3})\]', shift_num, r.text)
            if new != r.text: r.text = new

shift_par_count = 0
for b in iter_block_items(d):
    if isinstance(b, Paragraph):
        shift_runs_in_par(b); shift_par_count += 1
    else:
        if b._tbl is bib_tbl:      # skip bibliography here
            continue
        for row in b.rows:
            for c in row.cells:
                for p in c.paragraphs:
                    shift_runs_in_par(p)

# ---------------------------------------------------------------------------
# STEP B: bibliography - relabel [133]-[148] -> [138]-[153] (retain color),
#   then insert 5 NEW red rows [133]-[137] after the [132] row.
# ---------------------------------------------------------------------------
bib = d.tables[-1]
# relabel existing labels
for row in bib.rows:
    lab = row.cells[0]
    m = re.match(r'\[(\d{1,3})\]', lab.text.strip())
    if m and 133 <= int(m.group(1)) <= 148:
        newlab = f"[{int(m.group(1))+5}]"
        # update first run text only, preserve color
        for r in lab.paragraphs[0].runs:
            if '[' in r.text:
                r.text = re.sub(r'\[\d{1,3}\]', newlab, r.text, count=1); break

# find the row element for [132]
row132_tr = None
for row in bib.rows:
    if row.cells[0].text.strip() == '[132]':
        row132_tr = row._tr; break
assert row132_tr is not None, "row [132] not found"

NEW_REFS = [
 ("[133]", "S. S. Hazari and Q. H. Mahmoud, “Improving Transaction Speed and Scalability of Blockchain Systems via Parallel Proof of Work,” Future Internet, vol. 12, no. 8, Art. no. 125, 2020, doi: 10.3390/fi12080125."),
 ("[134]", "P. Szalachowski, D. Reijsbergen, I. Homoliak, and S. Sun, “StrongChain: Transparent and Collaborative Proof-of-Work Consensus,” in Proc. 28th USENIX Security Symposium, Santa Clara, CA, USA, 2019, pp. 819–836."),
 ("[135]", "R. Haque, S. M. T. Aziz, T. Hossain, F. H. Bappy, M. N. Yanhaona, and T. Islam, “Collaborative Proof-of-Work: A Secure Dynamic Approach to Fair and Efficient Blockchain Mining,” in Proc. IEEE 15th Annu. Computing and Communication Workshop and Conference (CCWC), 2025, doi: 10.1109/CCWC62904.2025.10903711."),
 ("[136]", "N. Yonezawa, “Proof of Team Sprint: A Collaborative Consensus Algorithm for Reducing Energy Consumption in Blockchain Systems,” IET Blockchain, vol. 6, no. 1, Art. no. e70034, 2026, doi: 10.1049/blc2.70034."),
 ("[137]", "S. D. Lerner, “APoW: Auditable Proof-of-Work Against Block Withholding Attacks,” arXiv preprint arXiv:2601.02496, 2026, doi: 10.48550/arXiv.2601.02496."),
]

def make_new_bib_row_after(ref_tr, label, text):
    """Deep-copy an existing bib row to keep identical cell structure, then
    overwrite text and colour RED. Insert after ref_tr. Returns new tr."""
    new_tr = copy.deepcopy(ref_tr)
    # clear paragraphs' runs in both cells and set new red text
    from docx.table import _Row
    tr = new_tr
    # helper to set a cell's tc text (tc is w:tc element)
    tcs = tr.findall(qn('w:tc'))
    def set_tc(tc, s):
        # remove all paragraphs' runs, keep first paragraph
        ps = tc.findall(qn('w:p'))
        # keep first p, drop others
        for extra in ps[1:]:
            tc.remove(extra)
        p = tc.find(qn('w:p'))
        for r in p.findall(qn('w:r')):
            p.remove(r)
        run = OxmlElement('w:r')
        rpr = OxmlElement('w:rPr')
        col = OxmlElement('w:color'); col.set(qn('w:val'), 'FF0000'); rpr.append(col)
        run.append(rpr)
        t = OxmlElement('w:t'); t.set(qn('xml:space'), 'preserve'); t.text = s
        run.append(t); p.append(run)
    set_tc(tcs[0], label)
    set_tc(tcs[1], text)
    ref_tr.addnext(new_tr)
    return new_tr

anchor_tr = row132_tr
for label, text in NEW_REFS:
    anchor_tr = make_new_bib_row_after(anchor_tr, label, text)

# ---------------------------------------------------------------------------
# helpers for inserting red paragraphs before an anchor paragraph
# ---------------------------------------------------------------------------
def find_par(pred):
    for p in d.paragraphs:
        if pred(p.text): return p
    raise RuntimeError("anchor not found")

def ins_before(anchor, text, style, center=False, bold=False, red=True):
    p = anchor.insert_paragraph_before(text, style=style)
    if center: p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for r in p.runs:
        if red: redden(r)
        if bold: r.font.bold = True
    return p

def cite(s):
    return re.sub(r'\[(\w+)\]', lambda m: f"[{C[m.group(1)]}]" if m.group(1) in C else m.group(0), s)

print("STEP A/B done. shifted paras:", shift_par_count, "| new bib rows:", len(NEW_REFS))
d.save(FILE)
print("saved after A/B")
