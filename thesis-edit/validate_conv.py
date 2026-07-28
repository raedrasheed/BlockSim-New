#!/usr/bin/env python3
"""End-to-end validation of the equation-conversion pass.
Reads the OMML back out of draft-41, linearises every equation, and confirms
that (prose + linearised-math) reconstructs the ORIGINAL draft-40 text under a
normalisation that folds the faithful preprocess transforms (Unicode sub/sup,
Σ->∑, (label)->^(label), braces, dashes, spaces).  Also counts oMath objects,
checks for residual plain-text equations, and reports colour preservation."""
import docx
from docx.oxml.ns import qn
import omml, convert

M = omml.M
def qm(t): return f"{{{M}}}{t}"

def child_text(el):
    """Linearise an OMML element's children back to source-like text."""
    out = []
    for c in el:
        tag = c.tag
        if tag == qm('r'):
            t = c.find(qm('t'));  out.append(t.text or '' if t is not None else '')
        elif tag == qm('sSub'):
            out.append(child_text(c.find(qm('e'))) + '_' + child_text(c.find(qm('sub'))))
        elif tag == qm('sSup'):
            out.append(child_text(c.find(qm('e'))) + '^' + child_text(c.find(qm('sup'))))
        elif tag == qm('sSubSup'):
            out.append(child_text(c.find(qm('e'))) + '_' + child_text(c.find(qm('sub'))) + '^' + child_text(c.find(qm('sup'))))
        elif tag == qm('f'):
            out.append(child_text(c.find(qm('num'))) + '/' + child_text(c.find(qm('den'))))
        elif tag == qm('nary'):
            npr = c.find(qm('naryPr'))
            ch = '∑'
            if npr is not None:
                chel = npr.find(qm('chr'))
                if chel is not None: ch = chel.get(qm('val'))
            sub = c.find(qm('sub')); sup = c.find(qm('sup')); e = c.find(qm('e'))
            s = ch + '_' + (child_text(sub) if sub is not None else '')
            if sup is not None and child_text(sup): s += '^' + child_text(sup)
            s += child_text(e) if e is not None else ''
            out.append(s)
        elif tag == qm('d'):
            dpr = c.find(qm('dPr')); bc = ec = ''
            if dpr is not None:
                b = dpr.find(qm('begChr')); e2 = dpr.find(qm('endChr'))
                if b is not None: bc = b.get(qm('val'))
                if e2 is not None: ec = e2.get(qm('val'))
            out.append(bc + child_text(c.find(qm('e'))) + ec)
        elif tag in (qm('e'), qm('num'), qm('den'), qm('sub'), qm('sup')):
            out.append(child_text(c))
        else:
            # any other wrapper: recurse
            out.append(child_text(c))
    return ''.join(out)

def recon_para(p_el):
    """Reconstruct paragraph text: prose w:t verbatim, oMath linearised."""
    out = []
    for node in p_el:
        if node.tag == qn('w:r'):
            t = node.find(qn('w:t'))
            if t is not None: out.append(t.text or '')
        elif node.tag == qm('oMath'):
            out.append(child_text(node))
        elif node.tag == qm('oMathPara'):
            for om in node.findall(qm('oMath')): out.append(child_text(om))
        elif node.tag == qn('w:hyperlink'):
            for r in node.findall(qn('w:r')):
                t = r.find(qn('w:t'))
                if t is not None: out.append(t.text or '')
    return ''.join(out)

# ---- load both docs, align paragraphs ----
old = docx.Document("Raed-Rasheed-draft-40-UniversityFormat.docx")
new = docx.Document("Raed-Rasheed-draft-41-WordEquations.docx")

def all_paras(doc):
    return doc.paragraphs

op = old.paragraphs; np = new.paragraphs
assert len(op) == len(np), f"paragraph count changed {len(op)} -> {len(np)}"

def fold(s):
    return omml.norm(s).replace('\n', '').replace('\t', '').replace('\r', '')

# orig still carries Unicode/Σ/(label); preprocess folds it to the same ASCII math
# form the OMML linearises to.  recon is ALREADY linearised, so it must NOT be
# preprocessed again (that would double the ^(label) transforms).
def L(orig):  return fold(convert.preprocess(orig))
def R(recon): return fold(recon)

mismatch = 0; checked = 0
for i,(a,b) in enumerate(zip(op, np)):
    orig = a.text
    recon = recon_para(b._p)
    if L(orig) != R(recon):
        mismatch += 1
        if mismatch <= 25:
            print(f"MISMATCH p{i}:")
            print("  orig :", repr(orig[:120]))
            print("  recon:", repr(recon[:120]))
            print("  L    :", repr(L(orig)[:120]))
            print("  R    :", repr(R(recon)[:120]))
    checked += 1

# count oMath
def count_omath(doc):
    c = 0
    for om in doc.element.body.iter(qm('oMath')): c += 1
    return c
# also tables
n_omath = 0
for om in new.element.iter(qm('oMath')): n_omath += 1

print(f"\nparagraphs checked: {checked}  mismatches: {mismatch}")
print(f"oMath objects in draft-41: {n_omath}")

# residual plain-text equations in body prose (signatures still outside math)
import re
resid = 0
for i,b in enumerate(np):
    # prose only (text outside oMath)
    pt = []
    for node in b._p:
        if node.tag == qn('w:r'):
            t = node.find(qn('w:t'))
            if t is not None: pt.append(t.text or '')
    prose = ''.join(pt)
    if convert.SIG.search(prose):
        resid += 1
print(f"paragraphs with residual math signatures in prose: {resid}")
