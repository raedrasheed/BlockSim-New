"""Render the red-lined revised DOCX to a matching PDF (reportlab).

LibreOffice headless conversion is unavailable in this environment, so we read
the revised DOCX run-by-run -- preserving red colour, bold/italic, headings,
alignment, and embedded figures -- and reproduce it as a PDF. This keeps the PDF
faithful to the red-lined DOCX content; for a pixel-exact journal-template PDF,
export from Word/LibreOffice locally.
"""

import io
import os
import re

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image)
from PIL import Image as PILImage

IN = os.path.join(os.path.dirname(__file__),
                  "Extending_BlockSim_Energy_Carbon_REVISED_redline.docx")
OUT = os.path.join(os.path.dirname(__file__),
                   "Extending_BlockSim_Energy_Carbon_REVISED_redline.pdf")
RED_HEX = "C00000"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def run_markup(run):
    txt = run.text
    if not txt:
        return ""
    s = esc(txt)
    if run.bold:
        s = f"<b>{s}</b>"
    if run.italic:
        s = f"<i>{s}</i>"
    col = run.font.color
    is_red = False
    try:
        if col is not None and col.rgb is not None and str(col.rgb) == RED_HEX:
            is_red = True
    except Exception:
        pass
    if is_red:
        s = f'<font color="#{RED_HEX}">{s}</font>'
    return s


def run_images(run, doc):
    """Yield image blobs embedded in a run, in order."""
    blips = run._element.findall(".//" + qn("a:blip"))
    out = []
    for b in blips:
        rid = b.get(qn("r:embed"))
        if rid and rid in doc.part.related_parts:
            out.append(doc.part.related_parts[rid].blob)
    return out


def main():
    doc = docx.Document(IN)
    ss = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=ss["Normal"], fontName="Times-Roman",
                          fontSize=10.5, leading=14, alignment=TA_JUSTIFY, spaceAfter=5)
    bodyc = ParagraphStyle("bodyc", parent=body, alignment=TA_CENTER)
    h1 = ParagraphStyle("h1", parent=ss["Heading1"], fontName="Times-Bold",
                        fontSize=13, spaceBefore=9, spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontName="Times-Bold",
                        fontSize=11.5, spaceBefore=7, spaceAfter=3)
    title = ParagraphStyle("title", parent=ss["Title"], fontName="Times-Bold",
                           fontSize=15, alignment=TA_CENTER, spaceAfter=6)

    story = []
    for i, p in enumerate(doc.paragraphs):
        style_name = (p.style.name if p.style else "Normal") or "Normal"
        align = p.alignment
        # collect text markup and any images
        markup_parts, imgs = [], []
        for run in p.runs:
            markup_parts.append(run_markup(run))
            imgs.extend(run_images(run, doc))
        markup = "".join(markup_parts).strip()

        # choose style
        if i == 0:
            st = title
        elif style_name.startswith("Heading 1"):
            st = h1
        elif style_name.startswith("Heading 2"):
            st = h2
        elif align == WD_ALIGN_PARAGRAPH.CENTER:
            st = bodyc
        else:
            st = body

        if markup:
            story.append(Paragraph(markup, st))

        # images after text in the same paragraph
        for blob in imgs:
            with PILImage.open(io.BytesIO(blob)) as im:
                w, h = im.size
            disp_w = 5.3 * inch
            disp_h = disp_w * h / w
            tmp = io.BytesIO(blob)
            story.append(Spacer(1, 3))
            story.append(Image(tmp, width=disp_w, height=disp_h))
            story.append(Spacer(1, 2))

    SimpleDocTemplate(OUT, pagesize=A4, leftMargin=0.75 * inch,
                      rightMargin=0.75 * inch, topMargin=0.75 * inch,
                      bottomMargin=0.7 * inch,
                      title="Extending BlockSim - revised (red-line)").build(story)
    print("Saved PDF:", OUT)


if __name__ == "__main__":
    main()
