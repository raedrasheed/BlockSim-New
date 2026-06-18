"""Render the red-lined revised DOCX to a matching PDF (reportlab).

LibreOffice headless conversion is unavailable in this environment, so we read
the revised DOCX in document order -- paragraphs, inline OMML equations, the
equation tables, embedded figures, red colour, bold/italic, headings -- and
reproduce it as a PDF. OMML equations are linearised to readable Unicode math
(true native equations live in the DOCX). For a pixel-exact, fully typeset PDF,
export from Microsoft Word / LibreOffice locally.
"""

import io
import os

import docx
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.table import Table
from docx.text.paragraph import Paragraph
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph as RLPara, Spacer, Image
from PIL import Image as PILImage

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Serif font with Greek, summation and subscript glyphs for the math.
_DEJAVU = "/usr/share/fonts/truetype/dejavu"
SERIF, SERIF_B = "Times-Roman", "Times-Bold"
try:
    pdfmetrics.registerFont(TTFont("DejaVuSerif", os.path.join(_DEJAVU, "DejaVuSerif.ttf")))
    pdfmetrics.registerFont(TTFont("DejaVuSerif-Bold", os.path.join(_DEJAVU, "DejaVuSerif-Bold.ttf")))
    SERIF, SERIF_B = "DejaVuSerif", "DejaVuSerif-Bold"
except Exception:
    pass

IN = os.path.join(os.path.dirname(__file__),
                  "Extending_BlockSim_Energy_Carbon_REVISED_redline.docx")
OUT = os.path.join(os.path.dirname(__file__),
                   "Extending_BlockSim_Energy_Carbon_REVISED_redline.pdf")
RED_HEX = "C00000"
GREEN_HEX = "008000"

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
MM = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"

SUP = {"0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴",
       "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹",
       "+": "⁺", "-": "⁻", "(": "⁽", ")": "⁾", "n": "ⁿ",
       "i": "ⁱ"}
SUB = {"0": "₀", "1": "₁", "2": "₂", "3": "₃", "4": "₄",
       "5": "₅", "6": "₆", "7": "₇", "8": "₈", "9": "₉",
       "+": "₊", "-": "₋", "(": "₍", ")": "₎",
       "a": "ₐ", "e": "ₑ", "h": "ₕ", "i": "ᵢ", "k": "ₖ",
       "l": "ₗ", "m": "ₘ", "n": "ₙ", "o": "ₒ", "p": "ₚ",
       "r": "ᵣ", "s": "ₛ", "t": "ₜ", "u": "ᵤ", "v": "ᵥ",
       "x": "ₓ"}


def _to_uni(s, table):
    out = []
    for ch in s:
        if ch in table:
            out.append(table[ch])
        else:
            return None
    return "".join(out)


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def lname(el):
    return el.tag.split("}")[-1]


def lin(el):
    """Linearise an OMML element subtree to a readable Unicode string."""
    tag = lname(el)
    if tag in ("oMath", "oMathPara", "e", "num", "den"):
        return "".join(lin(c) for c in el)
    if tag == "r":
        return "".join(t.text or "" for t in el.findall(MM + "t"))
    if tag == "t":
        return el.text or ""
    if tag == "sSub":
        e = lin(el.find(MM + "e")); sub = lin(el.find(MM + "sub"))
        u = _to_uni(sub, SUB)
        return e + (u if u is not None else f"_({sub})")
    if tag == "sSup":
        e = lin(el.find(MM + "e")); sup = lin(el.find(MM + "sup"))
        u = _to_uni(sup, SUP)
        return e + (u if u is not None else f"^({sup})")
    if tag == "sSubSup":
        e = lin(el.find(MM + "e")); sub = lin(el.find(MM + "sub")); sup = lin(el.find(MM + "sup"))
        us = _to_uni(sub, SUB); up = _to_uni(sup, SUP)
        return e + (us if us is not None else f"_({sub})") + (up if up is not None else f"^({sup})")
    if tag == "f":
        return f"({lin(el.find(MM + 'num'))})/({lin(el.find(MM + 'den'))})"
    if tag == "d":
        return "(" + "".join(lin(c) for c in el.findall(MM + "e")) + ")"
    if tag == "nary":
        chrv = "∑"
        pr = el.find(MM + "naryPr")
        if pr is not None and pr.find(MM + "chr") is not None:
            chrv = pr.find(MM + "chr").get(qn("m:val")) or chrv
        sub = lin(el.find(MM + "sub")); sup = lin(el.find(MM + "sup")); e = lin(el.find(MM + "e"))
        return f"{chrv}({sub}..{sup}) {e}"
    return "".join(lin(c) for c in el)


def omath_is_red(el):
    for r in el.findall(".//" + MM + "r"):
        wrpr = r.find(W + "rPr")
        if wrpr is not None:
            col = wrpr.find(W + "color")
            if col is not None and col.get(qn("w:val")) == RED_HEX:
                return True
    return False


def run_markup(r):
    rpr = r.find(W + "rPr")
    txt = "".join(t.text or "" for t in r.findall(W + "t"))
    if not txt:
        return ""
    s = esc(txt)
    color = None; bold = False; ital = False
    if rpr is not None:
        bold = rpr.find(W + "b") is not None
        ital = rpr.find(W + "i") is not None
        col = rpr.find(W + "color")
        if col is not None and col.get(qn("w:val")) in (RED_HEX, GREEN_HEX):
            color = col.get(qn("w:val"))
    if bold:
        s = f"<b>{s}</b>"
    if ital:
        s = f"<i>{s}</i>"
    if color:
        s = f'<font color="#{color}">{s}</font>'
    return s


def para_markup_and_images(p_el, doc):
    """Walk a w:p in order; return (markup, [image_blobs])."""
    parts, imgs = [], []
    for child in p_el:
        t = lname(child)
        if t == "r":
            parts.append(run_markup(child))
            for blip in child.findall(".//" + qn("a:blip")):
                rid = blip.get(qn("r:embed"))
                if rid and rid in doc.part.related_parts:
                    imgs.append(doc.part.related_parts[rid].blob)
        elif t == "oMath":
            m = esc(lin(child))
            if omath_is_red(child):
                m = f'<font color="#{RED_HEX}">{m}</font>'
            parts.append(m)
    return "".join(parts).strip(), imgs


def main():
    doc = docx.Document(IN)
    ss = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=ss["Normal"], fontName=SERIF,
                          fontSize=10.5, leading=14, alignment=TA_JUSTIFY, spaceAfter=5)
    bodyc = ParagraphStyle("bodyc", parent=body, alignment=TA_CENTER)
    eqs = ParagraphStyle("eq", parent=body, alignment=TA_CENTER, spaceBefore=3,
                         spaceAfter=4)
    h1 = ParagraphStyle("h1", parent=ss["Heading1"], fontName=SERIF_B,
                        fontSize=13, spaceBefore=9, spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontName=SERIF_B,
                        fontSize=11.5, spaceBefore=7, spaceAfter=3)
    title = ParagraphStyle("title", parent=ss["Title"], fontName=SERIF_B,
                           fontSize=15, alignment=TA_CENTER, spaceAfter=6)

    story = []
    first_para_done = False
    for blk in doc.element.body:
        tag = lname(blk)
        if tag == "p":
            p = Paragraph(blk, doc)
            markup, imgs = para_markup_and_images(blk, doc)
            style_name = (p.style.name if p.style else "Normal") or "Normal"
            if not first_para_done:
                st = title; first_para_done = True
            elif style_name.startswith("Heading 1"):
                st = h1
            elif style_name.startswith("Heading 2"):
                st = h2
            elif p.alignment == WD_ALIGN_PARAGRAPH.CENTER:
                st = bodyc
            else:
                st = body
            if markup:
                story.append(RLPara(markup, st))
            for blob in imgs:
                with PILImage.open(io.BytesIO(blob)) as im:
                    w, h = im.size
                dw = 5.3 * inch; dh = dw * h / w
                story.append(Spacer(1, 3))
                story.append(Image(io.BytesIO(blob), width=dw, height=dh))
                story.append(Spacer(1, 2))
        elif tag == "tbl":
            t = Table(blk, doc)
            # equation table: 1x2 with OMML + (n)
            om = blk.findall(".//" + MM + "oMath")
            if om:
                eqtext = esc(lin(om[0]))
                if omath_is_red(om[0]):
                    eqtext = f'<font color="#{RED_HEX}">{eqtext}</font>'
                num = t.rows[0].cells[1].text.strip()
                numm = num
                if num.startswith("("):
                    numm = num
                story.append(RLPara(f"{eqtext}&nbsp;&nbsp;&nbsp;&nbsp;{esc(numm)}", eqs))

    SimpleDocTemplate(OUT, pagesize=A4, leftMargin=0.75 * inch,
                      rightMargin=0.75 * inch, topMargin=0.75 * inch,
                      bottomMargin=0.7 * inch,
                      title="Extending BlockSim - revised (red-line)").build(story)
    print("Saved PDF:", OUT)


if __name__ == "__main__":
    main()
