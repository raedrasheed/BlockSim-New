#!/usr/bin/env python3
"""Build the TRACKED-CHANGES manuscript from the original, with w:ins/w:del
markup AND manual red colouring on every insertion (Track Changes alone is not
sufficient per the brief)."""
import copy
from docx import Document
from docx.shared import RGBColor, Pt
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import shared_edits as S

SRC = "manuscript.docx"
OUT = "Manuscript_Final_Editor_Revision_Red_Tracked.docx"
AUTHOR = "Editor Revision"
DATE = "2026-07-22T00:00:00Z"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
AC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}AlternateContent"

d = Document(SRC)
root = d.element
def wq(t): return qn("w:" + t)

_id = [1000]
def nid():
    _id[0] += 1
    return _id[0]

def make_run(text, red=False):
    r = OxmlElement("w:r")
    if red:
        rpr = OxmlElement("w:rPr")
        col = OxmlElement("w:color"); col.set(qn("w:val"), "FF0000")
        rpr.append(col); r.append(rpr)
    t = OxmlElement("w:t"); t.set(qn("xml:space"), "preserve"); t.text = text
    r.append(t)
    return r

def make_ins(children):
    ins = OxmlElement("w:ins")
    ins.set(qn("w:id"), str(nid())); ins.set(qn("w:author"), AUTHOR); ins.set(qn("w:date"), DATE)
    for c in children:
        ins.append(c)
    return ins

def del_run_inplace(r_el):
    """Wrap an existing run in <w:del>, converting w:t -> w:delText."""
    for it in r_el.iter(wq("instrText")):
        it.tag = wq("delInstrText")
    t = r_el.find(wq("t"))
    if t is not None:
        dt = OxmlElement("w:delText"); dt.set(qn("xml:space"), "preserve"); dt.text = t.text
        r_el.replace(t, dt)
    parent = r_el.getparent(); idx = list(parent).index(r_el)
    de = OxmlElement("w:del")
    de.set(qn("w:id"), str(nid())); de.set(qn("w:author"), AUTHOR); de.set(qn("w:date"), DATE)
    parent.remove(r_el); de.append(r_el); parent.insert(idx, de)
    return de

def _convert_instr(el):
    """Convert w:instrText->w:delInstrText and w:t->w:delText inside a deleted run
    (including nested text-box content) so the markup is schema-valid."""
    for it in el.iter(wq("instrText")):
        it.tag = wq("delInstrText")
    for t in el.iter(wq("t")):
        t.tag = wq("delText")

def del_whole_run(r_el):
    """Wrap a run (e.g. a floating drawing) in <w:del> without delText."""
    _convert_instr(r_el)
    parent = r_el.getparent(); idx = list(parent).index(r_el)
    de = OxmlElement("w:del")
    de.set(qn("w:id"), str(nid())); de.set(qn("w:author"), AUTHOR); de.set(qn("w:date"), DATE)
    parent.remove(r_el); de.append(r_el); parent.insert(idx, de)
    return de

def text_run_elems(p):
    return [r._r for r in p.runs if r._r.find(wq("t")) is not None]

def mark_para_mark_deleted(p):
    pPr = p._p.get_or_add_pPr()
    rPr = pPr.find(wq("rPr"))
    if rPr is None:
        rPr = OxmlElement("w:rPr")
        sect = pPr.find(wq("sectPr"))       # rPr must precede sectPr
        if sect is not None:
            sect.addprevious(rPr)
        else:
            pPr.append(rPr)
    de = OxmlElement("w:del")
    de.set(qn("w:id"), str(nid())); de.set(qn("w:author"), AUTHOR); de.set(qn("w:date"), DATE)
    rPr.insert(0, de)                        # ins/del must be first child of rPr

paras = d.paragraphs

# ---- REWRITES: delete old text runs, insert new red run --------------------
for idx, newtext in S.REWRITES.items():
    p = paras[idx]
    for r_el in text_run_elems(p):
        del_run_inplace(r_el)
    p._p.append(make_ins([make_run(newtext, red=True)]))

# ---- DELETES: delete all runs + paragraph mark -----------------------------
for idx in S.DELETES:
    p = paras[idx]
    for r_el in text_run_elems(p):
        del_run_inplace(r_el)
    mark_para_mark_deleted(p)

# ---- CLEAR_TEXT: delete text runs, keep drawing ----------------------------
for idx in S.CLEAR_TEXT:
    p = paras[idx]
    for r_el in text_run_elems(p):
        del_run_inplace(r_el)

# ---- SURGICAL: del old token, ins new red ----------------------------------
def surgical_tracked(p, old, new):
    for r in list(p.runs):
        if r.text and old in r.text:
            before, after = r.text.split(old, 1)
            r_el = r._r
            # keep 'before' in original run
            r_el.find(wq("t")).text = before
            # build del(old) and ins(new red) and after-run
            del_r = make_run(old)  # will convert to delText via wrapper
            # convert to delText
            t = del_r.find(wq("t")); dt = OxmlElement("w:delText"); dt.set(qn("xml:space"),"preserve"); dt.text = old
            del_r.replace(t, dt)
            de = OxmlElement("w:del"); de.set(qn("w:id"),str(nid())); de.set(qn("w:author"),AUTHOR); de.set(qn("w:date"),DATE)
            de.append(del_r)
            aft = make_run(after)
            r_el.addnext(aft)
            if new:                                    # empty new => pure deletion
                r_el.addnext(make_ins([make_run(new, red=True)]))
            r_el.addnext(de)
            return True
    return False

for idx, old, new in S.SURGICAL:
    assert surgical_tracked(paras[idx], old, new), f"surgical {idx} failed"

# keyword edit (para 16): '.'->','  and second 'PoW'->'PoS'
kw = paras[16]
runs = kw.runs
# run[12]='.'  -> del '.', ins ','
r12 = runs[12]._r; r12.find(wq("t")).text = ""  # empty original
# put del+ins after r12
dot_del = OxmlElement("w:del"); dot_del.set(qn("w:id"),str(nid())); dot_del.set(qn("w:author"),AUTHOR); dot_del.set(qn("w:date"),DATE)
dr = make_run("."); t=dr.find(wq("t")); dt=OxmlElement("w:delText"); dt.text="."; dr.replace(t,dt); dot_del.append(dr)
r12.addnext(make_ins([make_run(",", red=True)])); r12.addnext(dot_del)
# run[14]='PoW' -> del 'PoW', ins 'PoS'
r14 = runs[14]._r; r14.find(wq("t")).text = ""
pw_del = OxmlElement("w:del"); pw_del.set(qn("w:id"),str(nid())); pw_del.set(qn("w:author"),AUTHOR); pw_del.set(qn("w:date"),DATE)
dr2 = make_run("PoW"); t=dr2.find(wq("t")); dt=OxmlElement("w:delText"); dt.text="PoW"; dr2.replace(t,dt); pw_del.append(dr2)
r14.addnext(make_ins([make_run("PoS", red=True)])); r14.addnext(pw_del)

# ---- PREFIX deletes in references ------------------------------------------
for idx, prefix in S.PREFIX_DELETE:
    p = paras[idx]
    r = p.runs[0]; r_el = r._r
    assert r.text.startswith(prefix), f"prefix {idx}"
    rest = r.text[len(prefix):]
    r_el.find(wq("t")).text = rest
    # insert a del-run with the prefix BEFORE this run
    del_r = make_run(prefix); t=del_r.find(wq("t")); dt=OxmlElement("w:delText"); dt.set(qn("xml:space"),"preserve"); dt.text=prefix; del_r.replace(t,dt)
    de = OxmlElement("w:del"); de.set(qn("w:id"),str(nid())); de.set(qn("w:author"),AUTHOR); de.set(qn("w:date"),DATE); de.append(del_r)
    r_el.addprevious(de)

# ---- Reference mechanical fixes (tracked) ----------------------------------
# delete stray trailing punctuation runs (wrap each in w:del)
for idx in S.REF_TRAILING_PUNCT:
    for r in list(paras[idx].runs):
        if r.text in (" ", ".", " ."):
            del_run_inplace(r._r)
# replace a whole-run prefix: del old run, ins new red run
for idx, old, new in S.REF_REPLACE_RUN:
    done = False
    for r in list(paras[idx].runs):
        if r.text == old:
            r_el = r._r
            ins = make_ins([make_run(new, red=True)])
            r_el.addnext(ins)
            del_run_inplace(r_el)
            done = True; break
    assert done, f"refreplace {idx} failed"

# ---- Remove old Figures 1-3 (mark drawings + caption boxes as deleted) -----
for ac in list(root.iter(AC)):
    cap = "".join(t.text or "" for t in ac.iter(wq("t")))
    if cap.startswith(("Figure 1:", "Figure 2:", "Figure 3:")):
        del_whole_run(ac.getparent())
for dr in list(root.iter(wq("drawing"))):
    blip = dr.find(".//" + qn("a:blip"))
    emb = blip.get(R + "embed") if blip is not None else None
    if emb in {"rId8", "rId9", "rId10"}:
        del_whole_run(dr.getparent())

# ---- Renumber kept captions (del old number, ins new red) ------------------
CAPMAP = {"Figure 4.":"Figure 1.","Figure 5.":"Figure 2.","Figure 6.":"Figure 3.","Figure 7.":"Figure 4."}
for ac in list(root.iter(AC)):
    full = "".join(t.text or "" for t in ac.iter(wq("t")))
    for old, new in CAPMAP.items():
        if full.startswith(old):
            for wt in list(ac.iter(wq("t"))):
                if wt.text and wt.text.startswith(old):
                    rest = wt.text[len(old):]
                    r_el = wt.getparent()
                    wt.text = rest  # keep remainder black in original run
                    del_r = make_run(old); t=del_r.find(wq("t")); dt=OxmlElement("w:delText"); dt.set(qn("xml:space"),"preserve"); dt.text=old; del_r.replace(t,dt)
                    de = OxmlElement("w:del"); de.set(qn("w:id"),str(nid())); de.set(qn("w:author"),AUTHOR); de.set(qn("w:date"),DATE); de.append(del_r)
                    ins = make_ins([make_run(new, red=True)])
                    r_el.addprevious(de); de.addnext(ins)
            break

# ---- Insert Table 1 (as tracked insertion) ---------------------------------
def find_para(prefix):
    for p in d.paragraphs:
        if p.text.strip().startswith(prefix):
            return p
    raise RuntimeError(prefix)

intro = find_para("To evaluate the effectiveness of the proposed energy and carbon")

HEADER = S.TABLE_HEADER
ROWS = S.TABLE_ROWS

tbl = d.add_table(rows=1+len(ROWS), cols=len(HEADER))
try: tbl.style = d.styles["Table Grid"]
except KeyError: pass

def fill_cell_ins(cell, text, bold=False):
    p = cell.paragraphs[0]
    # clear
    for r in list(p.runs): r._r.getparent().remove(r._r)
    run = make_run(text, red=True)
    if bold:
        rpr = run.find(wq("rPr"))
        b = OxmlElement("w:b"); rpr.append(b)
    sz = run.find(wq("rPr"))
    szel = OxmlElement("w:sz"); szel.set(qn("w:val"), "16"); sz.append(szel)
    p._p.append(make_ins([run]))

for j,h in enumerate(HEADER): fill_cell_ins(tbl.rows[0].cells[j], h, bold=True)
for i,rw in enumerate(ROWS, start=1):
    for j,val in enumerate(rw): fill_cell_ins(tbl.rows[i].cells[j], val)

# mark each row as inserted
for row in tbl.rows:
    trPr = row._tr.get_or_add_trPr()
    ins = OxmlElement("w:ins"); ins.set(qn("w:id"),str(nid())); ins.set(qn("w:author"),AUTHOR); ins.set(qn("w:date"),DATE)
    trPr.append(ins)

def new_ins_para(text, style="RSR", bold=False):
    p = d.add_paragraph(); p.style = d.styles[style]
    run = make_run(text, red=True)
    if bold:
        run.find(wq("rPr")).append(OxmlElement("w:b"))
    p._p.append(make_ins([run]))
    return p

lead = new_ins_para(S.PARAM_LEAD)
cap = new_ins_para(S.PARAM_CAPTION, bold=True)
spacer = d.add_paragraph()

intro._p.addnext(lead._p)
lead._p.addnext(tbl._tbl)
tbl._tbl.addnext(cap._p)
cap._p.addnext(spacer._p)

# ---- Insert §E Randomness subsection (tracked) -----------------------------
metrics = find_para("The subsequent metrics are gathered for each simulation")
head = new_ins_para(S.RAND_HEAD, style="Heading 2")
body = new_ins_para(S.RAND_BODY)
metrics._p.addnext(head._p)
head._p.addnext(body._p)

# normalize xml:space on any text element with edge whitespace
for tag in ("t", "delText"):
    for t in root.iter(wq(tag)):
        if t.text and t.text != t.text.strip():
            t.set(qn("xml:space"), "preserve")

d.save(OUT)
print("tracked saved:", OUT)
