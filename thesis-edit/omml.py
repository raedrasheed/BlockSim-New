#!/usr/bin/env python3
"""Minimal but faithful plain-math -> OMML converter with a round-trip linearizer
used as a safety net (only equations whose OMML linearizes back to the source are
accepted as fully built-up)."""
import re
from lxml import etree

M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
def mq(t): return f"{{{M}}}{t}"

# ---------------------------------------------------------------- OMML builders
def el(tag, parent=None):
    e = etree.Element(mq(tag)) if parent is None else etree.SubElement(parent, mq(tag))
    return e
def run(text, upright=False):
    r = el('r')
    if upright:
        rpr = el('rPr', r); sty = el('sty', rpr); sty.set(mq('val'), 'p')
    t = el('t', r); t.set(f"{{{'http://www.w3.org/XML/1998/namespace'}}}space", 'preserve')
    t.text = text
    return r
def wrap_e(name, children):
    e = el(name)
    for c in children: e.append(c)
    return e

# node = ('run', text, upright) | ('sub', base_nodes, sub_nodes) | ('sup',..) |
#        ('subsup', base, sub, sup) | ('frac', num_nodes, den_nodes) |
#        ('nary', chr, sub_nodes, sup_nodes, body_nodes) | ('delim', open, close, nodes)
def build(nodes, parent):
    for n in nodes:
        k = n[0]
        if k == 'run':
            parent.append(run(n[1], n[2]))
        elif k == 'sub':
            s = el('sSub', parent)
            e = el('e', s); build(n[1], e)
            sb = el('sub', s); build(n[2], sb)
        elif k == 'sup':
            s = el('sSup', parent)
            e = el('e', s); build(n[1], e)
            sp = el('sup', s); build(n[2], sp)
        elif k == 'subsup':
            s = el('sSubSup', parent)
            e = el('e', s); build(n[1], e)
            sb = el('sub', s); build(n[2], sb)
            sp = el('sup', s); build(n[3], sp)
        elif k == 'frac':
            f = el('f', parent)
            num = el('num', f); build(n[1], num)
            den = el('den', f); build(n[2], den)
        elif k == 'nary':
            nary = el('nary', parent)
            npr = el('naryPr', nary)
            ch = el('chr', npr); ch.set(mq('val'), n[1])
            limloc = el('limLoc', npr); limloc.set(mq('val'), 'undOvr')
            if not n[2]: sh = el('subHide', npr); sh.set(mq('val'), '1')
            if not n[3]: sh = el('supHide', npr); sh.set(mq('val'), '1')
            sub = el('sub', nary); build(n[2], sub)
            sup = el('sup', nary); build(n[3], sup)
            e = el('e', nary); build(n[4], e)
        elif k == 'delim':
            dd = el('d', parent)
            dpr = el('dPr', dd)
            bc = el('begChr', dpr); bc.set(mq('val'), n[1])
            ec = el('endChr', dpr); ec.set(mq('val'), n[2])
            e = el('e', dd); build(n[3], e)
    return parent

# ---------------------------------------------------------------- linearizer (round-trip)
def lin(nodes):
    out = ""
    for n in nodes:
        k = n[0]
        if k == 'run': out += n[1]
        elif k == 'sub': out += lin(n[1]) + "_" + lin(n[2])
        elif k == 'sup': out += lin(n[1]) + "^" + lin(n[2])
        elif k == 'subsup': out += lin(n[1]) + "_" + lin(n[2]) + "^" + lin(n[3])
        elif k == 'frac': out += lin(n[1]) + "/" + lin(n[2])
        elif k == 'nary': out += n[1] + "_" + lin(n[2]) + ("^"+lin(n[3]) if n[3] else "") + lin(n[4])
        elif k == 'delim': out += n[1] + lin(n[3]) + n[2]
    return out

def norm(s):
    """Normalize for round-trip comparison: drop spaces, braces, unify dashes/dots."""
    s = s.replace('{','').replace('}','').replace(' ','')
    s = s.replace('−','-').replace('·','*').replace('∙','*')
    return s

# ---------------------------------------------------------------- parser
FUNCS = {'H','floor','ceil','header','id','log','min','max','exp','sin','cos',
         'Serialize','Encode','Header','Hash','Normalize'}
GREEK = set('λΣΘµσγκαβθπρτφω')
NARY = {'∑':'∑','∫':'∫','⋃':'⋃','⋂':'⋂','∏':'∏','⨁':'⨁'}
RELOPS = ['≈','≤','≥','≠','∈','∉','→','←','⇒','↔','⊆','⊂','⊇','⊄','∝','∣','≔',
          '=','<','>',':','∀','∉','∪','∩']
ADDOPS = ['+','−','-']
MULOPS = ['·','∙','*','×','||']

class P:
    def __init__(s, t): s.t=t; s.i=0; s.n=len(t)
    def peek(s): return s.t[s.i] if s.i<s.n else ''
    def peek2(s): return s.t[s.i:s.i+2]
    def eat(s,c=None):
        ch=s.t[s.i]; s.i+=1; return ch
    def ws(s):
        while s.i<s.n and s.t[s.i]==' ': s.i+=1

def parse(text):
    p = P(text)
    nodes = parse_seq(p)
    if p.i != p.n:  # leftover -> fail
        return None
    return nodes

WORDS = ('hence','for','all','and','where','if','then','otherwise','with','such','that')
# When False (inline span detection) the parser accepts ONLY pure mathematics:
# no English connector words, no top-level comma lists, no trailing sentence period.
# This stops inline spans from absorbing surrounding prose.  Whole-equation
# conversion sets it True so intentional equation prose ("hence", "for all") works.
ALLOW_PROSE = True
def parse_seq(p):
    """A relational sequence: term (relop term | word | ',' | '.' )*"""
    out = []
    p.ws()
    seg = parse_addsub(p)
    if seg is None: return None
    out += seg
    while True:
        p.ws()
        if p.i>=p.n: break
        one=p.peek()
        matched=False
        for op in RELOPS:
            if one==op:
                p.eat(); p.ws(); out.append(('run',' '+op+' ',True))
                seg=parse_addsub(p)
                if seg is None: return None
                out += seg; matched=True; break
        if matched: continue
        if ALLOW_PROSE and one==',':
            p.eat(); p.ws(); out.append(('run',', ',True))
            mw=re.match(r'[A-Za-z]+', p.t[p.i:])
            if mw and mw.group(0).lower() in WORDS:
                continue  # let the word handler below pick it up
            seg=parse_addsub(p)
            if seg is None: return None
            out += seg; continue
        if ALLOW_PROSE and one=='.':
            p.eat(); out.append(('run','.',True)); continue
        # a run of English word(s) inside the equation (hence, for all, …)
        if ALLOW_PROSE:
            m=re.match(r'[A-Za-z]+', p.t[p.i:])
            if m and m.group(0).lower() in WORDS:
                words=[]
                while True:
                    p.ws()
                    mm=re.match(r'[A-Za-z]+', p.t[p.i:])
                    if mm and mm.group(0).lower() in WORDS:
                        words.append(mm.group(0)); p.i+=len(mm.group(0))
                    else: break
                out.append(('run',' '+' '.join(words)+' ',True))
                p.ws()
                if p.i<p.n and p.peek() not in (',','.'):
                    seg=parse_addsub(p)
                    if seg is None: return None
                    out += seg
                continue
        break
    return out

def parse_addsub(p):
    out = parse_mul(p)
    if out is None: return None
    while True:
        p.ws()
        c=p.peek()
        if c in ('+','−','-'):
            p.eat(); p.ws(); out.append(('run',' '+c+' ',True)); out += parse_mul(p)
        else: break
    return out

def parse_mul(p):
    out = parse_frac(p)
    if out is None: return None
    while True:
        p.ws()
        if p.peek2()=='||':
            p.i+=2; p.ws(); out.append(('run',' || ',True)); out += parse_frac(p); continue
        c=p.peek()
        if c in ('·','∙','*','×'):
            p.eat(); p.ws(); out.append(('run',' · ',True)); out += parse_frac(p)
        else: break
    return out

def parse_frac(p):
    left = parse_unary(p)
    if left is None: return None
    p.ws()
    while p.peek()=='/':
        p.eat(); p.ws()
        right = parse_unary(p)
        left = [('frac', left, right)]
    return left

def parse_unary(p):
    p.ws()
    c=p.peek()
    if c in ('−','-','+'):
        p.eat(); rest=parse_unary(p)
        return [('run',c,True)] + (rest if rest else [])
    return parse_atom(p)

def parse_atom(p):
    p.ws()
    c=p.peek()
    if c=='':
        return []
    # n-ary operators (sum, integral, union, intersection, product)
    if c in NARY:
        p.eat()
        sub=[]; sup=[]
        if p.peek()=='_':
            p.eat(); sub=parse_script_group(p)
        if p.peek()=='^':
            p.eat(); sup=parse_script_group(p)
        p.ws()
        body=parse_mul(p)
        return [('nary',c,sub,sup,body)]
    # empty set
    if c=='∅':
        p.eat(); return attach_scripts(p, [('run','∅',True)])
    # delimiters
    if c=='(':
        p.eat(); inner=parse_seq_delim(p)
        if p.peek()==')': p.eat()
        else: return None
        node=[('delim','(',')',inner)]
        return attach_call(p, node)
    if c=='[':
        p.eat(); inner=parse_seq_delim(p)
        if p.peek()==']': p.eat()
        else: return None
        return [('delim','[',']',inner)]
    if c=='{':
        p.eat(); inner=parse_seq_delim(p)
        if p.peek()=='|':                # set-builder "{ x | condition }"
            p.eat(); p.ws()
            inner = inner + [('run',' | ',True)] + parse_seq_delim(p)
        if p.peek()=='}': p.eat()
        else: return None
        return attach_scripts(p, [('delim','{','}',inner)])
    if c=='|':
        p.eat(); inner=parse_seq_delim(p)
        if p.peek()=='|': p.eat()
        else: return None
        return [('delim','|','|',inner)]
    if c=='“' or c=='"':
        # quoted literal (preserve the original quote glyphs)
        q=c; p.eat(); j=p.i
        while p.i<p.n and p.t[p.i] not in ('”','"'): p.i+=1
        lit=p.t[j:p.i]
        close=''
        if p.i<p.n: close=p.t[p.i]; p.eat()
        return [('run',q+lit+close,True)]
    if c=='…':
        p.eat(); return [('run','…',True)]
    # prefix quantifier (∀ x, ∃ x)
    if c in ('∀','∃'):
        p.eat(); p.ws(); rest=parse_atom(p)
        if rest is None: rest=[]
        return [('run',c+' ',True)]+rest
    # number
    m=re.match(r'\d+', p.t[p.i:])
    if m:
        num=m.group(0); p.i+=len(num)
        base=[('run',num,True)]
        return attach_scripts(p, base)
    # identifier / greek  (allow trailing combining marks e.g. M̃ and primes T′)
    if c.isalpha() or c in GREEK or c=='ℓ':
        m=re.match(r'[A-Za-z]+', p.t[p.i:])
        if m:
            name=m.group(0); p.i+=len(name)
        else:
            name=c; p.eat()
        while p.i<p.n and (0x300<=ord(p.t[p.i])<=0x36f or p.t[p.i] in '′″‴'):
            name+=p.t[p.i]; p.i+=1
        upright = name in FUNCS
        base=[('run', name, upright)]
        base=attach_scripts(p, base)
        # function call
        if name in FUNCS and p.peek()=='(':
            base=attach_call(p, base)
        else:
            base=attach_call_ident(p, base)
        return base
    return None

def parse_seq_delim(p):
    """sequence inside delimiters, stops at matching close (handled by caller)."""
    out=[]
    p.ws()
    seg=parse_addsub(p)
    if seg is None: return out
    out+=seg
    while True:
        p.ws()
        c=p.peek()
        if c in (')',']','}','|','') : break
        matched=False
        for op in RELOPS:
            if c==op:
                p.eat(); p.ws(); out.append(('run',' '+op+' ',True))
                seg=parse_addsub(p)
                if seg is None: break
                out+=seg; matched=True; break
        if matched: continue
        if c==',':
            p.eat(); p.ws(); out.append(('run',', ',True))
            seg=parse_addsub(p)
            if seg is None: break
            out+=seg; continue
        break
    return out

def parse_script_group(p):
    """after _ or ^: a braced group {..} or a compound identifier run."""
    p.ws()
    if p.peek()=='{':
        p.eat(); inner=parse_seq_delim(p)
        if p.peek()=='}': p.eat()
        return inner
    if p.peek()=='(':
        # keep parens (e.g. ^(active))
        p.eat(); inner=parse_seq_delim(p)
        if p.peek()==')': p.eat()
        return [('delim','(',')',inner)]
    # compound: letters/digits with internal underscores (total_PoW)
    m=re.match(r'[A-Za-z0-9]+(?:_[A-Za-z0-9]+)*', p.t[p.i:])
    if m:
        tok=m.group(0); p.i+=len(tok)
        return [('run',tok, tok not in GREEK)]
    if p.peek() in GREEK or p.peek()=='ℓ':
        ch=p.eat(); return [('run',ch,False)]
    return [('run','',True)]

def attach_scripts(p, base):
    sub=None; sup=None
    if p.peek()=='_':
        p.eat(); sub=parse_script_group(p)
    if p.peek()=='^':
        p.eat(); sup=parse_script_group(p)
    if sub is not None and sup is not None:
        return [('subsup', base, sub, sup)]
    if sub is not None:
        return [('sub', base, sub)]
    if sup is not None:
        return [('sup', base, sup)]
    return base

def attach_call(p, base):
    if p.peek()=='(':
        p.eat(); inner=parse_seq_delim(p)
        if p.peek()==')': p.eat()
        else: return None
        return base+[('delim','(',')',inner)]
    return base

def attach_call_ident(p, base):
    # identifier immediately followed by '(' => function application R_r(...)
    if p.peek()=='(':
        p.eat(); inner=parse_seq_delim(p)
        if p.peek()==')': p.eat()
        else: return None
        return base+[('delim','(',')',inner)]
    return base

# ---------------------------------------------------------------- public API
def to_omml(text, display=True, allow_prose=True):
    """Return (oMath_or_oMathPara element, ok_bool). ok=True if round-trips."""
    global ALLOW_PROSE
    ALLOW_PROSE = allow_prose
    nodes = None
    try:
        nodes = parse(text)
    except Exception:
        nodes = None
    ok = False
    if nodes is not None:
        if norm(lin(nodes)) == norm(text):
            ok = True
    if not ok:
        return None, False
    if display:
        omp = el('oMathPara'); om = el('oMath', omp); build(nodes, om)
        return omp, True
    else:
        om = el('oMath'); build(nodes, om)
        return om, True
