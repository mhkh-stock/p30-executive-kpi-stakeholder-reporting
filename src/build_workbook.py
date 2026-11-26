"""P30 — build the Executive KPI Pack workbook (openpyxl, live formulas).

Sheets:
  Cover         — the one-page pack for December 2026: KPI cards with
                  RAG vs target, 12-month trend, narrative, attention
  Monthly KPI   — 12 months; values from the DB, derived columns as
                  LIVE formulas (AOV, margin %, returns %, repeat %,
                  MoM %, YoY %)
  Category Mix  — monthly net revenue by category + total + share %
                  formulas, annual total row
  Targets       — the management plan + variance % and RAG formulas
                  (the same RAG rules as sql/03_target_variance.sql)
  Data Dictionary — every column, every KPI definition, RAG rules

Only plain functions are used in formulas (SUM, IF, ROUND) — no
post-2007 functions — so LibreOffice recalculates every value.
Usage:  python3 src/build_workbook.py
"""
import json
import math
import sqlite3
from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "processed" / "noormart.db"
OUT = ROOT / "outputs" / "executive_kpi_pack_SAMPLE.xlsx"

NAVY = "1F3864"
NAVY_FILL = PatternFill("solid", fgColor=NAVY)
LIGHT_FILL = PatternFill("solid", fgColor="E8EDF3")
GREEN_FILL = PatternFill("solid", fgColor="D9EAD3")
AMBER_FILL = PatternFill("solid", fgColor="FCE5CD")
RED_FILL = PatternFill("solid", fgColor="F4CCCC")
WHITE_FONT = Font(color="FFFFFF", bold=True, size=12)
TITLE_FONT = Font(color=NAVY, bold=True, size=18)
SUB_FONT = Font(color="404040", size=11)
HEAD_FONT = Font(color="FFFFFF", bold=True, size=11)
BODY_FONT = Font(size=11)
SMALL_FONT = Font(size=10, color="404040")
THIN = Side(style="thin", color="BFBFBF")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
PKR_FMT = '#,##0'
PCT_FMT = '0.0%'
PCT2_FMT = '0.00%'

MONTH_NAMES = {"01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr",
               "05": "May", "06": "Jun", "07": "Jul", "08": "Aug",
               "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec"}
CATEGORIES = ["Electronics", "Home & Kitchen", "Groceries",
              "Clothing", "Beauty & Care"]


def rag_rules(ws, cell_range):
    ws.conditional_formatting.add(
        cell_range, CellIsRule(operator="equal", formula=['"GREEN"'],
                               fill=GREEN_FILL))
    ws.conditional_formatting.add(
        cell_range, CellIsRule(operator="equal", formula=['"AMBER"'],
                               fill=AMBER_FILL))
    ws.conditional_formatting.add(
        cell_range, CellIsRule(operator="equal", formula=['"RED"'],
                               fill=RED_FILL))


def style_header(ws, row, ncols):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill = NAVY_FILL
        cell.font = HEAD_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center",
                                   wrap_text=True)
        cell.border = BOX


def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    kpi = [dict(r) for r in conn.execute(
        "SELECT * FROM monthly_kpi ORDER BY month")]
    targets = [dict(r) for r in conn.execute(
        "SELECT * FROM monthly_targets ORDER BY month")]
    prior = {r["month"]: dict(r) for r in conn.execute(
        "SELECT * FROM monthly_prior_year")}
    cat = [dict(r) for r in conn.execute(
        "SELECT * FROM category_monthly ORDER BY month, net_revenue_pkr DESC")]
    conn.close()
    summary = json.loads((ROOT / "outputs" / "summary.json").read_text())

    wb = Workbook()

    # ================= Monthly KPI =================
    ws = wb.active
    ws.title = "Monthly KPI"
    headers = ["Month", "Net revenue (PKR)", "Orders", "Avg order value (PKR)",
               "Gross profit (PKR)", "Gross margin %", "Gross sales (PKR)",
               "Returns (PKR)", "Returns rate %", "New customers",
               "Repeat customers", "Repeat rate %",
               "Prior-year revenue (PKR)", "YoY revenue %", "MoM revenue %"]
    ws.append(headers)
    style_header(ws, 1, len(headers))
    for i, k in enumerate(kpi):
        r = i + 2
        ws.cell(row=r, column=1,
               value=f"{MONTH_NAMES[k['month'][5:]]} {k['month'][:4]}")
        ws.cell(row=r, column=2, value=k["net_revenue_pkr"])
        ws.cell(row=r, column=3, value=k["orders"])
        ws.cell(row=r, column=4, value=f"=IF(C{r}=0,\"\",B{r}/C{r})")
        ws.cell(row=r, column=5, value=k["gross_profit_pkr"])
        ws.cell(row=r, column=6, value=f"=IF(B{r}=0,\"\",E{r}/B{r})")
        ws.cell(row=r, column=7, value=k["gross_sales_pkr"])
        ws.cell(row=r, column=8, value=k["returns_pkr"])
        ws.cell(row=r, column=9, value=f"=IF(G{r}=0,\"\",H{r}/G{r})")
        ws.cell(row=r, column=10, value=k["new_customers"])
        ws.cell(row=r, column=11, value=k["repeat_customers"])
        ws.cell(row=r, column=12, value=f"=IF((J{r}+K{r})=0,\"\",K{r}/(J{r}+K{r}))")
        ws.cell(row=r, column=13, value=prior["2025-" + k["month"][5:]]["revenue_pkr"])
        ws.cell(row=r, column=14, value=f"=IF(M{r}=0,\"\",(B{r}-M{r})/M{r})")
        ws.cell(row=r, column=15,
               value=None if i == 0 else f"=IF(B{r-1}=0,\"\",(B{r}-B{r-1})/B{r-1})")
        for c in (2, 5, 7, 8, 13):
            ws.cell(row=r, column=c).number_format = PKR_FMT
        ws.cell(row=r, column=4).number_format = PKR_FMT
        for c in (6, 9, 12, 14, 15):
            ws.cell(row=r, column=c).number_format = PCT_FMT
        for c in range(1, len(headers) + 1):
            ws.cell(row=r, column=c).border = BOX
            ws.cell(row=r, column=c).font = BODY_FONT
    # annual total row
    r = 14
    ws.cell(row=r, column=1, value="2026 TOTAL").font = Font(bold=True, size=11)
    for c, f in ((2, "=SUM(B2:B13)"), (3, "=SUM(C2:C13)"),
                 (5, "=SUM(E2:E13)"), (7, "=SUM(G2:G13)"),
                 (8, "=SUM(H2:H13)"), (10, "=SUM(J2:J13)"),
                 (13, "=SUM(M2:M13)")):
        ws.cell(row=r, column=c, value=f).font = Font(bold=True, size=11)
        ws.cell(row=r, column=c).number_format = PKR_FMT
    ws.cell(row=r, column=4, value="=IF(C14=0,\"\",B14/C14)").number_format = PKR_FMT
    ws.cell(row=r, column=6, value="=IF(B14=0,\"\",E14/B14)").number_format = PCT_FMT
    ws.cell(row=r, column=9, value="=IF(G14=0,\"\",H14/G14)").number_format = PCT_FMT
    ws.cell(row=r, column=14, value="=IF(M14=0,\"\",(B14-M14)/M14)").number_format = PCT_FMT
    for c in range(1, len(headers) + 1):
        ws.cell(row=r, column=c).border = BOX
        ws.cell(row=r, column=c).fill = LIGHT_FILL
    widths = [14, 18, 10, 18, 18, 13, 18, 15, 13, 14, 15, 12, 20, 12, 12]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 1

    # ================= Targets =================
    wt = wb.create_sheet("Targets")
    theaders = ["Month", "Revenue target (PKR)", "Orders target",
                "Margin % target", "Returns % target",
                "New customers target", "Revenue variance %", "Revenue RAG",
                "Orders variance %", "Orders RAG",
                "Margin variance (pts)", "Margin RAG",
                "Returns variance (pts)", "Returns RAG",
                "New customers variance %", "New customers RAG"]
    wt.append(theaders)
    style_header(wt, 1, len(theaders))
    for i, t in enumerate(targets):
        r = i + 2
        k = kpi[i]
        wt.cell(row=r, column=1,
               value=f"{MONTH_NAMES[t['month'][5:]]} {t['month'][:4]}")
        wt.cell(row=r, column=2, value=t["revenue_target_pkr"])
        wt.cell(row=r, column=3, value=t["orders_target"])
        wt.cell(row=r, column=4, value=t["gross_margin_pct_target"] / 100)
        wt.cell(row=r, column=5, value=t["returns_rate_pct_target"] / 100)
        wt.cell(row=r, column=6, value=t["new_customers_target"])
        # variance + RAG, all live formulas on the Monthly KPI sheet
        wt.cell(row=r, column=7,
               value=f"=IF(B{r}=0,\"\",('Monthly KPI'!B{r}-B{r})/B{r})")
        wt.cell(row=r, column=8, value=(
            f"=IF('Monthly KPI'!B{r}>=B{r},\"GREEN\","
            f"IF('Monthly KPI'!B{r}>=0.95*B{r},\"AMBER\",\"RED\"))"))
        wt.cell(row=r, column=9,
               value=f"=IF(C{r}=0,\"\",('Monthly KPI'!C{r}-C{r})/C{r})")
        wt.cell(row=r, column=10, value=(
            f"=IF('Monthly KPI'!C{r}>=C{r},\"GREEN\","
            f"IF('Monthly KPI'!C{r}>=0.95*C{r},\"AMBER\",\"RED\"))"))
        wt.cell(row=r, column=11,
               value=f"=('Monthly KPI'!F{r}-D{r})*100")
        wt.cell(row=r, column=12, value=(
            f"=IF('Monthly KPI'!F{r}>=D{r},\"GREEN\","
            f"IF('Monthly KPI'!F{r}>=D{r}-0.02,\"AMBER\",\"RED\"))"))
        wt.cell(row=r, column=13,
               value=f"=('Monthly KPI'!I{r}-E{r})*100")
        wt.cell(row=r, column=14, value=(
            f"=IF('Monthly KPI'!I{r}<=E{r},\"GREEN\","
            f"IF('Monthly KPI'!I{r}<=E{r}+0.01,\"AMBER\",\"RED\"))"))
        wt.cell(row=r, column=15,
               value=f"=IF(F{r}=0,\"\",('Monthly KPI'!J{r}-F{r})/F{r})")
        wt.cell(row=r, column=16, value=(
            f"=IF('Monthly KPI'!J{r}>=F{r},\"GREEN\","
            f"IF('Monthly KPI'!J{r}>=0.8*F{r},\"AMBER\",\"RED\"))"))
        for c in (2,):
            wt.cell(row=r, column=c).number_format = PKR_FMT
        for c in (4, 5, 7, 9, 15):
            wt.cell(row=r, column=c).number_format = PCT_FMT
        for c in (11, 13):
            wt.cell(row=r, column=c).number_format = '0.00" pts"'
        for c in range(1, len(theaders) + 1):
            wt.cell(row=r, column=c).border = BOX
            wt.cell(row=r, column=c).font = BODY_FONT
    rag_rules(wt, "H2:H13")
    rag_rules(wt, "J2:J13")
    rag_rules(wt, "L2:L13")
    rag_rules(wt, "N2:N13")
    rag_rules(wt, "P2:P13")
    for i, w in enumerate(
            [14, 18, 13, 13, 14, 17, 15, 12, 15, 12, 15, 12, 15, 12, 17, 15],
            start=1):
        wt.column_dimensions[get_column_letter(i)].width = w
    wt.freeze_panes = "A2"
    wt.sheet_properties.pageSetUpPr.fitToPage = True
    wt.page_setup.orientation = "landscape"
    wt.page_setup.fitToWidth = 1
    wt.page_setup.fitToHeight = 1

    # ================= Category Mix =================
    wc = wb.create_sheet("Category Mix")
    cheaders = ["Month"] + [f"{c} (PKR)" for c in CATEGORIES] + \
        ["Total (PKR)"] + [f"{c} share" for c in CATEGORIES]
    wc.append(cheaders)
    style_header(wc, 1, len(cheaders))
    cat_map = {(c["month"], c["category"]): c["net_revenue_pkr"] for c in cat}
    for i, k in enumerate(kpi):
        r = i + 2
        wc.cell(row=r, column=1,
               value=f"{MONTH_NAMES[k['month'][5:]]} {k['month'][:4]}")
        for j, cname in enumerate(CATEGORIES):
            wc.cell(row=r, column=2 + j,
                   value=cat_map.get((k["month"], cname), 0))
        wc.cell(row=r, column=7, value=f"=SUM(B{r}:F{r})")
        for j in range(5):
            col = get_column_letter(2 + j)
            wc.cell(row=r, column=8 + j,
                   value=f"=IF($G{r}=0,\"\",{col}{r}/$G{r})")
        for c in range(1, len(cheaders) + 1):
            cell = wc.cell(row=r, column=c)
            cell.border = BOX
            cell.font = BODY_FONT
            if 2 <= c <= 7:
                cell.number_format = PKR_FMT
            if c >= 8:
                cell.number_format = PCT_FMT
    r = 14
    wc.cell(row=r, column=1, value="2026 TOTAL").font = Font(bold=True, size=11)
    for j in range(5):
        col = get_column_letter(2 + j)
        wc.cell(row=r, column=2 + j, value=f"=SUM({col}2:{col}13)")
        wc.cell(row=r, column=8 + j, value=f"=IF($G14=0,\"\",{col}14/$G14)")
    wc.cell(row=r, column=7, value="=SUM(G2:G13)")
    for c in range(1, len(cheaders) + 1):
        cell = wc.cell(row=r, column=c)
        cell.border = BOX
        cell.fill = LIGHT_FILL
        cell.font = Font(bold=True, size=11)
        if 2 <= c <= 7:
            cell.number_format = PKR_FMT
        if c >= 8:
            cell.number_format = PCT_FMT
    for i, w in enumerate([14] + [18] * 5 + [18] + [13] * 5, start=1):
        wc.column_dimensions[get_column_letter(i)].width = w
    wc.freeze_panes = "A2"
    wc.sheet_properties.pageSetUpPr.fitToPage = True
    wc.page_setup.orientation = "landscape"
    wc.page_setup.fitToWidth = 1
    wc.page_setup.fitToHeight = 1

    # ================= Cover =================
    cov = wb.create_sheet("Cover", 0)
    cov.sheet_properties.pageSetUpPr.fitToPage = True
    cov.page_setup.orientation = "portrait"
    cov.page_setup.paperSize = cov.PAPERSIZE_A4
    cov.page_setup.fitToWidth = 1
    cov.page_setup.fitToHeight = 1
    cov.print_title_rows = "1:3"
    for col, w in zip("ABCDEF", (30, 20, 20, 15, 12, 16)):
        cov.column_dimensions[col].width = w

    cov.merge_cells("A1:F1")
    cov["A1"] = "NoorMart — Executive KPI Pack"
    cov["A1"].font = TITLE_FONT
    cov.merge_cells("A2:F2")
    cov["A2"] = ("December 2026  ·  What should I know this month, in one page?  ·  "
                 "SAMPLE data — fictional retailer, seed 30")
    cov["A2"].font = SUB_FONT
    cov.merge_cells("A3:F3")
    cov["A3"] = ("Net revenue = gross sales − returns  ·  RAG: GREEN beat target, "
                 "AMBER within 5% (2 pts margin / 1 pt returns), RED missed by more")
    cov["A3"].font = SMALL_FONT

    # KPI cards: rows 5-12, Dec is row 13 on Monthly KPI / Targets
    cov.merge_cells("A4:F4")
    cov["A4"] = "DECEMBER 2026 — THE MONTH AT A GLANCE"
    cov["A4"].font = Font(color="FFFFFF", bold=True, size=11)
    cov["A4"].fill = NAVY_FILL
    cov["A4"].alignment = Alignment(horizontal="left", vertical="center")
    cards = [
        # (label, actual ref, target ref, kind, variance kind)
        ("Net revenue (PKR)", "'Monthly KPI'!B13", "'Targets'!B13", "PKR", "rel"),
        ("Orders", "'Monthly KPI'!C13", "'Targets'!C13", "num", "rel"),
        ("Avg order value (PKR)", "'Monthly KPI'!D13", None, "PKR", None),
        ("Gross margin %", "'Monthly KPI'!F13", "'Targets'!D13", "pct", "pts"),
        ("Returns rate %", "'Monthly KPI'!I13", "'Targets'!E13", "pct", "pts"),
        ("New customers", "'Monthly KPI'!J13", "'Targets'!F13", "num", "rel"),
        ("Repeat rate %", "'Monthly KPI'!L13", None, "pct", None),
    ]
    cov_headers = ["KPI", "This month", "Target", "Variance", "RAG", "vs last year"]
    for j, h in enumerate(cov_headers, start=1):
        c = cov.cell(row=5, column=j, value=h)
        c.fill = NAVY_FILL
        c.font = HEAD_FONT
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = BOX
    rag_rows = {"Net revenue (PKR)": "H", "Orders": "J",
                "Gross margin %": "L", "Returns rate %": "N",
                "New customers": "P"}
    for i, (label, actual, target, kind, var_kind) in enumerate(cards):
        r = 6 + i
        cov.cell(row=r, column=1, value=label).font = BODY_FONT
        cov.cell(row=r, column=1).border = BOX
        a = cov.cell(row=r, column=2, value=f"={actual}")
        a.border = BOX
        a.font = BODY_FONT
        if kind == "PKR":
            a.number_format = PKR_FMT
        elif kind == "pct":
            a.number_format = PCT_FMT
        if target:
            t = cov.cell(row=r, column=3, value=f"={target}")
            t.border = BOX
            t.font = BODY_FONT
            t.number_format = PKR_FMT if kind == "PKR" else PCT_FMT
            if var_kind == "pts":
                v = cov.cell(row=r, column=4, value=f"=(B{r}-C{r})*100")
                v.number_format = '0.00" pts"'
            else:
                v = cov.cell(row=r, column=4,
                            value=f"=IF(C{r}=0,\"\",(B{r}-C{r})/C{r})")
                v.number_format = PCT_FMT
            v.border = BOX
            v.font = BODY_FONT
            rag_col = rag_rows[label]
            g = cov.cell(row=r, column=5, value=f"='Targets'!{rag_col}13")
            g.border = BOX
            g.font = Font(bold=True, size=11)
            g.alignment = Alignment(horizontal="center")
        else:
            for cc in (3, 4, 5):
                cov.cell(row=r, column=cc, value="—").border = BOX
                cov.cell(row=r, column=cc).font = BODY_FONT
                cov.cell(row=r, column=cc).alignment = Alignment(horizontal="center")
        y = cov.cell(row=r, column=6)
        y.border = BOX
        y.font = BODY_FONT
        if label == "Net revenue (PKR)":
            y.value = "='Monthly KPI'!N13"
            y.number_format = PCT_FMT
        elif label == "Orders":
            y.value = "=IF('Monthly KPI'!M13=0,\"\",('Monthly KPI'!C13-'Monthly KPI'!M13)/'Monthly KPI'!M13)"
            y.number_format = PCT_FMT
        else:
            y.value = "—"
            y.alignment = Alignment(horizontal="center")
    rag_rules(cov, "E6:E12")

    # Trend table: rows 14-27
    tr = 14
    cov.merge_cells(f"A{tr}:F{tr}")
    cov.cell(row=tr, column=1, value="2026 TREND — REVENUE VS TARGET").font = \
        Font(color="FFFFFF", bold=True, size=11)
    cov.cell(row=tr, column=1).fill = NAVY_FILL
    tr += 1
    for j, h in enumerate(["Month", "Net revenue", "Target", "Variance %",
                           "RAG", "MoM %"], start=1):
        c = cov.cell(row=tr, column=j, value=h)
        c.fill = NAVY_FILL
        c.font = HEAD_FONT
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = BOX
    for i in range(12):
        r = tr + 1 + i
        src = i + 2  # row on Monthly KPI / Targets
        cov.cell(row=r, column=1, value=f"='Monthly KPI'!A{src}").border = BOX
        cov.cell(row=r, column=1).font = BODY_FONT
        b = cov.cell(row=r, column=2, value=f"='Monthly KPI'!B{src}")
        b.number_format = PKR_FMT
        b.border = BOX
        b.font = BODY_FONT
        c = cov.cell(row=r, column=3, value=f"='Targets'!B{src}")
        c.number_format = PKR_FMT
        c.border = BOX
        c.font = BODY_FONT
        v = cov.cell(row=r, column=4, value=f"='Targets'!G{src}")
        v.number_format = PCT_FMT
        v.border = BOX
        v.font = BODY_FONT
        g = cov.cell(row=r, column=5, value=f"='Targets'!H{src}")
        g.border = BOX
        g.font = Font(bold=True, size=11)
        g.alignment = Alignment(horizontal="center")
        m = cov.cell(row=r, column=6, value=f"='Monthly KPI'!O{src}")
        m.number_format = PCT_FMT
        m.border = BOX
        m.font = BODY_FONT
    rag_rules(cov, f"E{tr+1}:E{tr+12}")

    # Narrative + attention
    nr = tr + 14
    cov.merge_cells(f"A{nr}:F{nr}")
    cov.cell(row=nr, column=1, value="WHAT HAPPENED — IN PLAIN WORDS").font = \
        Font(color="FFFFFF", bold=True, size=11)
    cov.cell(row=nr, column=1).fill = NAVY_FILL
    nr += 1
    for para in summary["narrative"]:
        cov.merge_cells(f"A{nr}:F{nr}")
        cell = cov.cell(row=nr, column=1, value="•  " + para)
        cell.font = BODY_FONT
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        cov.row_dimensions[nr].height = max(30, 15 * math.ceil(len(para) / 130))
        nr += 1
    nr += 1
    cov.merge_cells(f"A{nr}:F{nr}")
    cov.cell(row=nr, column=1, value="WHAT NEEDS ATTENTION").font = \
        Font(color="FFFFFF", bold=True, size=11)
    cov.cell(row=nr, column=1).fill = NAVY_FILL
    nr += 1
    for item in summary["attention"]:
        cov.merge_cells(f"A{nr}:F{nr}")
        cell = cov.cell(row=nr, column=1, value="•  " + item)
        cell.font = BODY_FONT
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        cov.row_dimensions[nr].height = max(30, 15 * math.ceil(len(item) / 130))
        nr += 1
    nr += 1
    cov.merge_cells(f"A{nr}:F{nr}")
    cov.cell(row=nr, column=1, value=(
        "SAMPLE — NoorMart is fictional; the 2,230 sale lines, the targets and the "
        "2025 history are generated with seed 30. What is real is the method: every "
        "number above is a live formula on the Monthly KPI, Targets and Category Mix "
        "sheets, recomputed from the loaded lines. Annual net revenue "
        f"PKR {summary['annual']['net_revenue_pkr']:,.0f} · "
        f"{summary['annual']['orders']:,} orders · "
        f"gross margin {summary['annual']['gross_margin_pct']:.1f}% · "
        f"returns {summary['annual']['returns_rate_pct']:.1f}%."
    )).font = SMALL_FONT
    cov.cell(row=nr, column=1).alignment = Alignment(wrap_text=True, vertical="top")
    cov.row_dimensions[nr].height = 45

    # ================= Data Dictionary =================
    wd = wb.create_sheet("Data Dictionary")
    wd.column_dimensions["A"].width = 30
    wd.column_dimensions["B"].width = 22
    wd.column_dimensions["C"].width = 78
    wd.merge_cells("A1:C1")
    wd["A1"] = "Data dictionary — NoorMart SAMPLE data"
    wd["A1"].font = TITLE_FONT
    rows = [
        ("FILE / TABLE", "COLUMN", "MEANING"),
        ("data/raw/daily_sales.csv", "order_id",
         "Order number, ORD-YYYYMMDD-nnnn. One order = 1–3 lines."),
        ("data/raw/daily_sales.csv", "sale_date",
         "Date of the sale, ISO YYYY-MM-DD, Jan–Dec 2026."),
        ("data/raw/daily_sales.csv", "customer_id",
         "Customer code, CUST-nnn (700-customer pool)."),
        ("data/raw/daily_sales.csv", "customer_type",
         "new = the customer's first order; repeat = any later order."),
        ("data/raw/daily_sales.csv", "channel", "Store or Online."),
        ("data/raw/daily_sales.csv", "product / category",
         "25 products in 5 categories (see Category Mix)."),
        ("data/raw/daily_sales.csv", "qty / unit_price_pkr",
         "Quantity and selling price per unit."),
        ("data/raw/daily_sales.csv", "unit_cost_pkr",
         "Cost per unit = price × (1 − category margin)."),
        ("data/raw/daily_sales.csv", "line_amount_pkr",
         "qty × unit_price — the line's gross value."),
        ("data/raw/daily_sales.csv", "returned",
         "1 = the line was returned in full; 0 = kept."),
        ("data/raw/monthly_targets.csv", "revenue_target_pkr",
         "Management plan × 1.03 — set before the year's sales."),
        ("data/raw/monthly_targets.csv", "orders_target",
         "Plan × 1.03 ÷ expected net basket (PKR 10,500)."),
        ("data/raw/monthly_targets.csv", "gross_margin_pct_target",
         "23.5% — the blended margin the category mix yields."),
        ("data/raw/monthly_targets.csv", "returns_rate_pct_target",
         "4.5% of gross sales returned."),
        ("data/raw/monthly_targets.csv", "new_customers_target",
         "32 new customers a month."),
        ("data/raw/monthly_prior_year.csv", "revenue_pkr / orders",
         "2025 monthly totals, so YoY is computed, not typed."),
        ("KPI — net revenue", "monthly_kpi.net_revenue_pkr",
         "Gross sales − returns. Returned lines earn nothing."),
        ("KPI — gross profit / margin %", "monthly_kpi",
         "Gross profit counts kept lines only; margin % = profit ÷ net revenue."),
        ("KPI — returns rate %", "monthly_kpi",
         "Returns PKR ÷ gross sales PKR."),
        ("KPI — avg order value", "monthly_kpi",
         "Net revenue ÷ orders."),
        ("KPI — new / repeat customers", "monthly_kpi",
         "New = first order in that month; repeat = ordered before that month."),
        ("KPI — repeat rate %", "monthly_kpi",
         "Repeat customers ÷ active customers (new + repeat)."),
        ("RAG — revenue / orders", "sql/03_target_variance.sql",
         "GREEN ≥ 100% of target; AMBER 95–99.9%; RED < 95%."),
        ("RAG — gross margin %", "sql/03_target_variance.sql",
         "GREEN ≥ target; AMBER within 2 pts below; RED more than 2 pts below."),
        ("RAG — returns rate %", "sql/03_target_variance.sql",
         "GREEN ≤ target (lower is better); AMBER up to 1 pt above; RED above that."),
        ("RAG — new customers", "sql/03_target_variance.sql",
         "GREEN ≥ target; AMBER ≥ 80% of target; RED below 80%."),
        ("DATABASE", "data/processed/noormart.db",
         "SQLite star schema (dim_product, dim_customer, fact_sales, "
         "monthly_kpi, category_monthly). Rebuilds from the scripts; "
         "never uploaded to GitHub."),
    ]
    r = 3
    for a, b, c in rows:
        wd.cell(row=r, column=1, value=a)
        wd.cell(row=r, column=2, value=b)
        wd.cell(row=r, column=3, value=c)
        for col in range(1, 4):
            cell = wd.cell(row=r, column=col)
            cell.border = BOX
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            if r == 3:
                cell.fill = NAVY_FILL
                cell.font = HEAD_FONT
            else:
                cell.font = BODY_FONT
        wd.row_dimensions[r].height = 30 if r > 3 else 18
        r += 1

    wb.save(OUT)
    print(f"wrote {OUT.name} — sheets: {wb.sheetnames}")


if __name__ == "__main__":
    main()
