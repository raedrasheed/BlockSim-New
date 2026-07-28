#!/usr/bin/env python3
"""Mathematical Equation Conversion Pass  (draft-40 -> draft-41).

Convert plain-text / Unicode mathematics in the thesis into native Word Equation
objects (OMML).

Safety model
------------
* Each candidate span is converted ONLY if its OMML linearises back to the
  (preprocessed) source text  ->  the mathematical content is provably preserved.
* Conversion runs at PARAGRAPH level (spans may cross run boundaries).
* Surrounding prose keeps its original run formatting (rPr copied per source run).
* After rebuilding a paragraph, the residual prose (text outside every oMath) must
  equal the original text with the converted spans removed, else the whole
  paragraph is rolled back untouched.
* Only body prose paragraphs and equation-layout table cells are considered;
  data tables, the bibliography, headings, captions, TOC and the number cells of
  numbered equations are never touched.
"""
import copy, re
import docx
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.enum.text import WD_ALIGN_PARAGRAPH as AL
import omml

FILE = "Raed-Rasheed-draft-41-WordEquations.docx"
M = omml.M
def qm(t): return f"{{{M}}}{t}"

# --------------------------------------------------------------- Unicode maps
SUP = {'⁰':'0','¹':'1','²':'2','³':'3','⁴':'4','⁵':'5','⁶':'6','⁷':'7','⁸':'8',
       '⁹':'9','ⁿ':'n','ⁱ':'i','⁺':'+','⁻':'−','⁽':'(','⁾':')'}
SUB = {'₀':'0','₁':'1','₂':'2','₃':'3','₄':'4','₅':'5','₆':'6','₇':'7','₈':'8',
       '₉':'9','ₙ':'n','ᵢ':'i','ⱼ':'j','ₖ':'k','ₐ':'a','ₑ':'e','ₒ':'o','ₓ':'x',
       '₌':'=','₊':'+','₋':'−','₍':'(','₎':')'}
SUPSET = set(SUP); SUBSET = set(SUB)

def unicodify(s):
    """Unicode super/subscript clusters -> _{..}/^{..} groups on the preceding base."""
    out = []; i = 0; n = len(s)
    while i < n:
        c = s[i]
        if c in SUPSET or c in SUBSET:
            sup = ''; sub = ''
            while i < n and (s[i] in SUPSET or s[i] in SUBSET):
                if s[i] in SUPSET: sup += SUP[s[i]]
                else: sub += SUB[s[i]]
                i += 1
            if sub: out.append('_{' + sub + '}')
            if sup: out.append('^{' + sup + '}')
        else:
            out.append(c); i += 1
    return ''.join(out)

LABELS = ('active', 'idle', 'coord')
def preprocess(s):
    s = unicodify(s)
    s = s.replace('Σ', '∑')                      # capital sigma = summation here
    for lab in LABELS:
        s = s.replace('(' + lab + ')', '^(' + lab + ')')
    s = s.replace('E_PoCol,idle', 'E_{PoCol,idle}').replace('E_PoCol,continuous', 'E_{PoCol,continuous}')
    return s

# --------------------------------------------------------------- signatures
# a paragraph/span worth looking at contains at least one of these
SIG = re.compile(r'[_^∑∫=≈≤≥≠→←⇒∈∉∪∩λΣΘσµθπρτφωαβγκℓ·×∀∃]|\|\||\{[01]|['
                 + ''.join(SUBSET) + ''.join(SUPSET) + r']')
# a TABLE cell is only converted if it carries a strong equation indicator
TABLE_SIG = re.compile(r'[=≈≤≥≠<>→←⇒∈∉∑∫]|\^|/')

def has_sig(s):
    if SIG.search(s): return True
    for ch in s:
        if 0x370 <= ord(ch) <= 0x3ff: return True   # any Greek letter
    return False

# --------------------------------------------------------------- round-trip
def rounds(pp, allow_prose=True):
    omml.ALLOW_PROSE = allow_prose
    try: nodes = omml.parse(pp)
    except Exception: return False
    return nodes is not None and omml.norm(omml.lin(nodes)) == omml.norm(pp)

def make_omath(src_text, red=False, allow_prose=True):
    """Bare <m:oMath> for src_text, or (None,False) if it does not round-trip."""
    pp = preprocess(src_text)
    om, ok = omml.to_omml(pp, display=False, allow_prose=allow_prose)
    if not ok: return None, False
    if red: colorize(om)
    return om, True

def colorize(el):
    for r in el.iter(qm('r')):
        t = r.find(qm('t'))
        if t is None: continue
        wrpr = OxmlElement('w:rPr')
        col = OxmlElement('w:color'); col.set(qn('w:val'), 'FF0000'); wrpr.append(col)
        t.addprevious(wrpr)

def wrap_display(om, align):
    """Wrap a bare oMath in <m:oMathPara> with justification matching the paragraph."""
    omp = OxmlElement('m:oMathPara')
    opr = OxmlElement('m:oMathParaPr')
    jc = OxmlElement('m:jc')
    jc.set(qm('val'), 'center' if align == AL.CENTER else ('right' if align == AL.RIGHT else 'left'))
    opr.append(jc); omp.append(opr); omp.append(om)
    return omp

# --------------------------------------------------------------- span finder
ATOM_START = re.compile(r'[A-Za-zλΣΘσµθπρτφωαβγκℓ0-9]|[∑∫⋃⋂∏⨁∅|]|\{[01]')
# a trailing comma/space-delimited English STOP word that was absorbed as in-equation
# text is prose to strip; math operands (e.g. "target") and function names are kept
STOPWORDS = {'the','and','for','all','each','where','with','such','that','then',
             'otherwise','hence','if','is','of','to','by','in','on','as','be','we',
             'its','this','these','those','an','or','but','denote','denotes','are',
             'was','were','which','who','can','may','a'}
_TRAIL_RE = re.compile(r'(?:,\s*|\s+)([A-Za-z]{1,})\s*$')
def trailing_word(s):
    m = _TRAIL_RE.search(s)
    return m if (m and m.group(1).lower() in STOPWORDS) else None
BOUNDARY_BEFORE = set(' \t([{|=≈≤≥≠→←⇒+·×/,∈∉∩∪⊆') | SUBSET | SUPSET

def find_spans(text):
    """Maximal [start,end) math spans that round-trip and carry a signature."""
    spans = []; i = 0; n = len(text)
    while i < n:
        prev = text[i-1] if i > 0 else ' '
        is_start = ATOM_START.match(text[i:]) or (0x370 <= ord(text[i]) <= 0x3ff)
        if not (is_start and (i == 0 or prev in BOUNDARY_BEFORE)):
            i += 1; continue
        best = None
        e = min(n, i + 200)
        while e > i:
            span = text[i:e]; st = span.rstrip()
            if st and st[-1] not in '+−-·×/=≈≤≥≠→←⇒∈∉∪∩,^_(' and has_sig(span) and rounds(preprocess(span), allow_prose=False):
                best = e; break
            e -= 1
        if best is not None:
            s2 = text[i:best]
            # trim trailing prose that was absorbed as in-equation text, e.g.
            # "H_i(r), and the" -> "H_i(r)",  "n(r)=|M(r)|. For each" -> "n(r)=|M(r)|".
            # A bare multi-letter lowercase word at the end (not a function name) is
            # prose; single-letter variables (r, h, n) and sub/super-scripted or
            # capitalised tokens are kept.
            while True:
                st = s2.rstrip().rstrip(',.').rstrip()
                m = trailing_word(st)              # trailing prose word
                if m:
                    s2 = st[:m.start()]; continue
                if st and st[-1] in '+−-·×/=≈≤≥≠→←⇒∈∉∪∩⊆^_(':   # dangling operator
                    s2 = st[:-1]; continue
                break
            s2 = s2.rstrip().rstrip(',.').rstrip()
            if s2 and has_sig(s2) and rounds(preprocess(s2), allow_prose=False):
                spans.append((i, i + len(s2))); i = i + len(s2)
                continue
            i += 1
        else:
            i += 1
    return spans

# --------------------------------------------------------------- paragraph model
def run_is_red(rpr):
    if rpr is None: return False
    col = rpr.find(qn('w:color'))
    return col is not None and (col.get(qn('w:val')) or '').upper() == 'FF0000'

def simple_run(node):
    """True if node is a w:r whose only children are rPr/t (a pure text run)."""
    if node.tag != qn('w:r'): return False
    for ch in node:
        if ch.tag not in (qn('w:rPr'), qn('w:t')): return False
    return True

def build_charmap(run_els):
    """From a list of pure text runs -> (text, [rpr_per_char], [red_per_char])."""
    text = []; rprs = []; reds = []
    for r in run_els:
        t = r.find(qn('w:t'))
        if t is None or t.text is None: continue
        rpr = r.find(qn('w:rPr')); red = run_is_red(rpr)
        for ch in t.text:
            text.append(ch); rprs.append(rpr); reds.append(red)
    return ''.join(text), rprs, reds

# --------------------------------------------------------------- driver
counters = {'display': 0, 'inline': 0}
skipped = []; conv_display = []; conv_inline = []

def txt_run(tx, rpr):
    nr = OxmlElement('w:r')
    if rpr is not None: nr.append(copy.deepcopy(rpr))
    wt = OxmlElement('w:t'); wt.set(qn('xml:space'), 'preserve'); wt.text = tx
    nr.append(wt); return nr

def convert_para(p, loc, table_cell=False):
    p_el = p._p
    if not has_sig(p.text): return
    align = p.alignment
    snapshot = copy.deepcopy(p_el)

    # drop empty layout markers (Word regenerates them); harmless & invisible
    for pe in list(p_el.findall(qn('w:proofErr'))): p_el.remove(pe)
    for lrpb in list(p_el.iter(qn('w:lastRenderedPageBreak'))):
        lrpb.getparent().remove(lrpb)
    # split runs that mix text with tab/break markers, so text runs become "simple"
    # (a tab/break run is kept intact and acts as a hard boundary).  Rendering is
    # identical: run "A<tab>B" == run "A" + run "<tab>" + run "B" with the same rPr.
    for r in list(p_el.findall(qn('w:r'))):
        content = [c for c in r if c.tag != qn('w:rPr')]
        if all(c.tag == qn('w:t') for c in content):
            continue
        rpr = r.find(qn('w:rPr'))
        parent = r.getparent(); idx = list(parent).index(r)
        pieces = []
        for c in content:
            nr = OxmlElement('w:r')
            if rpr is not None: nr.append(copy.deepcopy(rpr))
            nr.append(copy.deepcopy(c))
            pieces.append(nr)
        parent.remove(r)
        for k, nd in enumerate(pieces): parent.insert(idx + k, nd)

    # split inline content into contiguous groups of pure text runs; anything else
    # (tabs, breaks, hyperlinks, bookmarks, fields) is a hard boundary left in place
    groups = []; cur = []
    for node in p_el:
        if node.tag == qn('w:pPr'): continue
        if simple_run(node):
            cur.append(node)
        else:
            if cur: groups.append(cur); cur = []
    if cur: groups.append(cur)

    # a paragraph is a DISPLAY equation only if it has exactly one group whose one
    # span covers the whole (stripped) paragraph text
    single_group = (len(groups) == 1)
    removed = []
    try:
        for grp in groups:
            text, rprs, reds = build_charmap(grp)
            if not text.strip() or not has_sig(text): continue
            lead_n = len(text) - len(text.lstrip())
            tail_s = len(text.rstrip())
            stripped = text.strip()

            # (a) whole group is a single equation? allow intentional equation prose
            whole = single_group and rounds(preprocess(stripped), allow_prose=True)
            if table_cell and not (whole and TABLE_SIG.search(stripped)):
                continue

            new_nodes = []
            if whole:
                red = bool(reds[lead_n:tail_s]) and all(reds[lead_n:tail_s])
                om, ok = make_omath(stripped, red=red, allow_prose=True)
                if not ok: continue
                removed.append(stripped)
                if lead_n: new_nodes.append(txt_run(text[:lead_n], rprs[0]))
                new_nodes.append(wrap_display(om, align))
                if tail_s < len(text): new_nodes.append(txt_run(text[tail_s:], rprs[-1]))
                counters['display'] += 1; conv_display.append((loc, stripped))
            else:
                # (b) strict inline spans (pure mathematics, no absorbed prose)
                spans = find_spans(text)
                if not spans: continue
                pos = 0
                for (s, e) in spans:
                    j = pos
                    while j < s:
                        k = j
                        while k < s and rprs[k] is rprs[j]: k += 1
                        new_nodes.append(txt_run(text[j:k], rprs[j])); j = k
                    red = all(reds[s:e]) if e > s else False
                    om, ok = make_omath(text[s:e], red=red, allow_prose=False)
                    if not ok:
                        skipped.append((loc, text[s:e])); new_nodes.append(txt_run(text[s:e], rprs[s]))
                    else:
                        removed.append(text[s:e]); new_nodes.append(om)
                        counters['inline'] += 1; conv_inline.append((loc, text[s:e]))
                    pos = e
                j = pos
                while j < len(text):
                    k = j
                    while k < len(text) and rprs[k] is rprs[j]: k += 1
                    new_nodes.append(txt_run(text[j:k], rprs[j])); j = k

            # splice: replace this group's run elements in place
            first = grp[0]; parent = first.getparent(); idx = list(parent).index(first)
            for r in grp: parent.remove(r)
            for k2, nd in enumerate(new_nodes): parent.insert(idx + k2, nd)

        if not removed:
            return
        # prose-preservation check over the whole paragraph
        original = snapshot_text(snapshot)
        expected = original
        for sp in removed:
            q = expected.find(sp)
            if q < 0: raise ValueError("span not in original")
            expected = expected[:q] + expected[q+len(sp):]
        resid = []
        for node in p_el.iter():
            if node.tag == qn('w:t'):
                anc = node.getparent(); inm = False
                while anc is not None:
                    if anc.tag == qm('oMath'): inm = True; break
                    anc = anc.getparent()
                if not inm: resid.append(node.text or '')
        if ''.join(resid) != expected:
            raise ValueError("prose mismatch")
    except Exception as ex:
        parent = p_el.getparent(); idx = list(parent).index(p_el)
        parent.remove(p_el); parent.insert(idx, snapshot)
        skipped.append((loc + " [ROLLBACK: %s]" % ex, p.text.strip()[:60]))

def snapshot_text(p_el):
    out = []
    for node in p_el.iter():
        if node.tag == qn('w:t'): out.append(node.text or '')
    return ''.join(out)

# --------------------------------------------------------------- main
if __name__ == "__main__":
    d = docx.Document(FILE)

    # (1) equation-layout table cells (only whole single-equation cells convert)
    for ti, t in enumerate(d.tables):
        for row in t.rows:
            cells = row.cells
            if not cells: continue
            c0 = cells[0]
            if len(c0.paragraphs) == 1 and c0.paragraphs[0].text.strip():
                convert_para(c0.paragraphs[0], f"Table[{ti}]", table_cell=True)

    # (2) body prose paragraphs
    SKIP = ('TOC', 'Heading', 'Chapter', 'Caption', 'Title', 'Subtitle',
            'key words', 'Author', 'List of', 'header', 'footer')
    for i, p in enumerate(d.paragraphs):
        st = (p.style.name or '')
        if any(st.startswith(s) or s in st for s in SKIP): continue
        if not has_sig(p.text): continue
        convert_para(p, f"para[{i}]")

    d.save(FILE)
    print("display converted :", counters['display'])
    print("inline converted  :", counters['inline'])
    print("skipped           :", len(skipped))
    for loc, tx in skipped[:60]:
        print("   SKIP", loc, "|", repr(tx))
