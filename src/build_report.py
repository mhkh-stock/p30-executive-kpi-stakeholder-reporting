"""P30 — build the one-page monthly KPI pack PDF (reportlab).

A single A4 page the owner can print or forward: December 2026 KPI
cards with RAG vs target, the revenue-vs-target chart, the category
mix, the narrative in plain words, and what needs attention. Every
number comes from outputs/summary.json (which comes from the DB) —
nothing is typed here.

Usage:  python3 src/build_report.py
"""
import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (Image, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs" / "executive_kpi_pack_SAMPLE.pdf"

NAVY = colors.HexColor("#1F3864")
GREEN = colors.HexColor("#1F7A3A")
AMBER = colors.HexColor("#C77D00")
RED = colors.HexColor("#B3261E")
GREY = colors.HexColor("#404040")
LIGHT = colors.HexColor("#E8EDF3")
GREEN_BG = colors.HexColor("#D9EAD3")
AMBER_BG = colors.HexColor("#FCE5CD")
RED_BG = colors.HexColor("#F4CCCC")

RAG_FILL = {"GREEN": GREEN_BG, "AMBER": AMBER_BG, "RED": RED_BG}
RAG_FONT = {"GREEN": GREEN, "AMBER": AMBER, "RED": RED}


def money(n):
    return f"PKR {n:,.0f}"


def pct(x):
    return f"{x:+.1f}%"


def main():
    s = json.loads((ROOT / "outputs" / "summary.json").read_text())
    pack = s["pack_month_kpi"]
    tgt = s["pack_month_target"]
    var = s["pack_month_variance"]
    gro = s["pack_month_growth"]

    styles = {
        "title": ParagraphStyle("title", fontName="Helvetica-Bold",
                                fontSize=17, leading=20, textColor=NAVY),
        "sub": ParagraphStyle("sub", fontName="Helvetica", fontSize=9.5,
                              leading=12, textColor=GREY),
        "h": ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=10.5,
                            leading=13, textColor=NAVY, spaceBefore=7,
                            spaceAfter=3),
        "body": ParagraphStyle("body", fontName="Helvetica", fontSize=9,
                               leading=12.5, textColor=colors.black,
                               spaceAfter=3),
        "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=9,
                               leading=11),
        "cellb": ParagraphStyle("cellb", fontName="Helvetica-Bold",
                                fontSize=9, leading=11),
        "cellc": ParagraphStyle("cellc", fontName="Helvetica", fontSize=9,
                                leading=11, alignment=1),
        "cellcb": ParagraphStyle("cellcb", fontName="Helvetica-Bold",
                                 fontSize=9, leading=11, alignment=1),
        "foot": ParagraphStyle("foot", fontName="Helvetica", fontSize=8,
                               leading=10, textColor=GREY),
    }

    def rag_cell(rag):
        return Paragraph(f'<font color="{RAG_FONT[rag].hexval()}">'
                         f"<b>{rag}</b></font>", styles["cellc"])

    kpi_rows = [
        ("Net revenue", money(pack["net_revenue_pkr"]),
         money(tgt["revenue_target_pkr"]), pct(var["revenue_variance_pct"]),
         var["revenue_rag"]),
        ("Orders", f"{pack['orders']:,}", f"{tgt['orders_target']:,}",
         pct(var["orders_variance_pct"]), var["orders_rag"]),
        ("Avg order value", money(pack["avg_order_value_pkr"]), "—", "—", None),
        ("Gross margin", f"{pack['gross_margin_pct']:.1f}%",
         f"{tgt['gross_margin_pct_target']:.1f}%",
         f"{var['margin_variance_pts']:+.1f} pts", var["margin_rag"]),
        ("Returns rate", f"{pack['returns_rate_pct']:.1f}%",
         f"{tgt['returns_rate_pct_target']:.1f}%",
         f"{var['returns_variance_pts']:+.1f} pts", var["returns_rag"]),
        ("New customers", f"{pack['new_customers']}",
         f"{tgt['new_customers_target']}",
         pct(var["new_customers_variance_pct"]), var["new_customers_rag"]),
        ("Repeat rate", f"{pack['repeat_rate_pct']:.1f}%", "—", "—", None),
    ]
    header = [Paragraph("<b>KPI</b>", styles["cellc"]),
              Paragraph("<b>This month</b>", styles["cellc"]),
              Paragraph("<b>Target</b>", styles["cellc"]),
              Paragraph("<b>Variance</b>", styles["cellc"]),
              Paragraph("<b>RAG</b>", styles["cellc"])]
    table_data = [header]
    for label, actual, target, variance, rag in kpi_rows:
        table_data.append([
            Paragraph(label, styles["cell"]),
            Paragraph(actual, styles["cellc"]),
            Paragraph(target, styles["cellc"]),
            Paragraph(variance, styles["cellc"]),
            rag_cell(rag) if rag else Paragraph("—", styles["cellc"]),
        ])
    kpi_table = Table(table_data, colWidths=[120, 95, 95, 80, 70])
    kpi_style = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BFBFBF")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    for i, (_, _, _, _, rag) in enumerate(kpi_rows, start=1):
        if rag:
            kpi_style.append(("BACKGROUND", (4, i), (4, i), RAG_FILL[rag]))
    kpi_table.setStyle(TableStyle(kpi_style))

    charts = Table([[
        Image(str(ROOT / "outputs" / "revenue_vs_target.png"),
              width=275, height=116),
        Image(str(ROOT / "outputs" / "category_mix.png"),
              width=205, height=145),
    ]], colWidths=[280, 210])
    charts.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
    ]))

    story = [
        Paragraph("NoorMart — Executive KPI Pack", styles["title"]),
        Paragraph(f"{s['pack_month_name']}  ·  What should I know this month, "
                  f"in one page?  ·  SAMPLE data — fictional retailer",
                  styles["sub"]),
        Paragraph(f"December closed at {money(pack['net_revenue_pkr'])} "
                  f"({pct(var['revenue_variance_pct'])} vs target, "
                  f"{var['revenue_rag'].lower()}), "
                  f"{gro['revenue_mom_pct']:+.1f}% on November and "
                  f"{gro['revenue_yoy_pct']:+.1f}% on December 2025. "
                  f"Year to date: {money(s['annual']['net_revenue_pkr'])} "
                  f"across {s['annual']['orders']:,} orders at "
                  f"{s['annual']['gross_margin_pct']:.1f}% gross margin.",
                  styles["body"]),
        kpi_table,
        Paragraph("The year in one picture", styles["h"]),
        charts,
        Paragraph("What happened — in plain words", styles["h"]),
    ]
    for para in s["narrative"]:
        story.append(Paragraph("•  " + para, styles["body"]))
    story.append(Paragraph("What needs attention", styles["h"]))
    for item in s["attention"][:4]:
        story.append(Paragraph("•  " + item, styles["body"]))
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph(
        "SAMPLE — NoorMart is fictional; the 2,230 sale lines, the targets and "
        "the 2025 history are generated with seed 30. What is real is the "
        "method: every number above is recomputed from the loaded lines "
        "(monthly_kpi in the SQLite database), and the same figures appear "
        "as live formulas in the Excel pack. RAG: GREEN beat target, AMBER "
        "within 5% (2 pts margin / 1 pt returns), RED missed by more.",
        styles["foot"]))

    doc = SimpleDocTemplate(str(OUT), pagesize=A4,
                            leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=14 * mm, bottomMargin=12 * mm,
                            title="NoorMart — Executive KPI Pack (SAMPLE)",
                            author="Muhammad Hashir")
    doc.build(story)
    print(f"wrote {OUT.name}")


if __name__ == "__main__":
    main()
