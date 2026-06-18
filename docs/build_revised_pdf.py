"""Render the revised manuscript to PDF from the shared content model (reportlab).

Used because LibreOffice headless conversion is unavailable in the build
environment. Consumes the exact same content as the DOCX renderer.
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image,
                                Table, TableStyle, ListFlowable, ListItem)

from manuscript_content import build_blocks, FIG

OUT = os.path.join(os.path.dirname(__file__),
                   "Extending_BlockSim_Consensus_Aware_Energy_Carbon_REVISED.pdf")


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def styles():
    ss = getSampleStyleSheet()
    out = {
        "title": ParagraphStyle("title", parent=ss["Title"], fontSize=16,
                                leading=20, alignment=TA_CENTER, spaceAfter=6),
        "author": ParagraphStyle("author", parent=ss["Normal"], alignment=TA_CENTER),
        "body": ParagraphStyle("body", parent=ss["Normal"], fontSize=10.5,
                               leading=14.5, alignment=TA_JUSTIFY, spaceAfter=6),
        "h1": ParagraphStyle("h1", parent=ss["Heading1"], fontSize=13,
                             spaceBefore=10, spaceAfter=4),
        "h2": ParagraphStyle("h2", parent=ss["Heading2"], fontSize=11.5,
                             spaceBefore=8, spaceAfter=3),
        "eq": ParagraphStyle("eq", parent=ss["Normal"], fontSize=11,
                             alignment=TA_CENTER, fontName="Helvetica-Oblique",
                             spaceBefore=4, spaceAfter=6),
        "cap": ParagraphStyle("cap", parent=ss["Normal"], fontSize=8.5,
                              leading=11, alignment=TA_CENTER, fontName="Helvetica-Oblique",
                              spaceAfter=8),
        "tcap": ParagraphStyle("tcap", parent=ss["Normal"], fontSize=8.5,
                               leading=11, fontName="Helvetica-Bold", spaceAfter=3),
        "cell": ParagraphStyle("cell", parent=ss["Normal"], fontSize=7.6, leading=9.5),
        "hcell": ParagraphStyle("hcell", parent=ss["Normal"], fontSize=7.6,
                                leading=9.5, fontName="Helvetica-Bold",
                                textColor=colors.white),
        "ref": ParagraphStyle("ref", parent=ss["Normal"], fontSize=8.6,
                              leading=11, spaceAfter=2),
    }
    return out


def main():
    blocks = build_blocks()
    S = styles()
    story = []
    bullets, numbers = [], []

    def flush_lists():
        nonlocal bullets, numbers
        if bullets:
            story.append(ListFlowable(
                [ListItem(Paragraph(esc(b), S["body"])) for b in bullets],
                bulletType="bullet", start="circle"))
            story.append(Spacer(1, 4))
            bullets = []
        if numbers:
            story.append(ListFlowable(
                [ListItem(Paragraph(esc(n), S["body"])) for n in numbers],
                bulletType="1"))
            story.append(Spacer(1, 4))
            numbers = []

    for blk in blocks:
        kind = blk[0]
        if kind not in ("bullet",):
            pass
        if kind == "bullet":
            numbers and flush_lists()
            bullets.append(blk[1]); continue
        if kind == "number":
            bullets and flush_lists()
            numbers.append(blk[1]); continue
        flush_lists()

        if kind == "title":
            story.append(Paragraph(esc(blk[1]), S["title"]))
        elif kind == "author":
            story.append(Paragraph(esc(blk[1]), S["author"]))
        elif kind == "abstract":
            story.append(Spacer(1, 6))
            story.append(Paragraph("<b>Abstract — </b>" + esc(blk[1]), S["body"]))
        elif kind == "keywords":
            story.append(Paragraph("<b>Keywords: </b>" + esc(blk[1]), S["body"]))
            story.append(Spacer(1, 4))
        elif kind == "h1":
            story.append(Paragraph(esc(blk[1]), S["h1"]))
        elif kind == "h2":
            story.append(Paragraph(esc(blk[1]), S["h2"]))
        elif kind == "p":
            story.append(Paragraph(esc(blk[1]), S["body"]))
        elif kind == "eq":
            story.append(Paragraph(f"{esc(blk[1])}&nbsp;&nbsp;&nbsp;&nbsp;({blk[2]})", S["eq"]))
        elif kind == "fig":
            _, stem, num, caption = blk
            img_path = os.path.join(FIG, stem + ".png")
            from PIL import Image as PILImage
            with PILImage.open(img_path) as im:
                w, h = im.size
            disp_w = 5.6 * inch
            disp_h = disp_w * h / w
            story.append(Spacer(1, 4))
            story.append(Image(img_path, width=disp_w, height=disp_h))
            story.append(Paragraph(f"Figure {num}. {esc(caption)}", S["cap"]))
        elif kind == "table":
            _, num, caption, headers, rows = blk
            story.append(Paragraph(f"Table {num}. {esc(caption)}", S["tcap"]))
            data = [[Paragraph(esc(h), S["hcell"]) for h in headers]]
            for row in rows:
                data.append([Paragraph(esc(v), S["cell"]) for v in row])
            t = Table(data, repeatRows=1, hAlign="LEFT")
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4472C4")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                 [colors.white, colors.HexColor("#EAF0FB")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]))
            story.append(t)
            story.append(Spacer(1, 8))
        elif kind == "ref":
            story.append(Paragraph(f"<b>[{blk[1]}]</b> {esc(blk[2])}", S["ref"]))

    flush_lists()

    doc = SimpleDocTemplate(OUT, pagesize=A4,
                            leftMargin=0.7 * inch, rightMargin=0.7 * inch,
                            topMargin=0.7 * inch, bottomMargin=0.7 * inch,
                            title="Extending BlockSim with Consensus-Aware Energy "
                                  "and Carbon Footprint Modeling")
    doc.build(story)
    print("Saved PDF:", OUT)


if __name__ == "__main__":
    main()
