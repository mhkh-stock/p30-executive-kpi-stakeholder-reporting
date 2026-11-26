"""P30 — verification suite: proves the pack, never trusts it.

Recomputes everything independently — from the raw CSVs in Python,
not from the database — and compares it with the database, the
workbook (recalculated in LibreOffice), the report PDF, the
summary.json and the README. A mistake in any one shows up as a
failure. Includes an independent re-implementation of the monthly
KPIs and the RAG rules that must reproduce the database row for row.

Usage:  python3 src/checks.py   (exit 0 = all passing)
"""
import csv
import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
from datetime import date
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "processed" / "noormart.db"
XLSX = ROOT / "outputs" / "executive_kpi_pack_SAMPLE.xlsx"
PDF = ROOT / "outputs" / "executive_kpi_pack_SAMPLE.pdf"
SUMMARY = ROOT / "outputs" / "summary.json"

CHECKS = 0
FAILURES = []


def check(name, ok, detail=""):
    global CHECKS
    CHECKS += 1
    if not ok:
        FAILURES.append(f"{name}  ({detail})")
    print(f"{'PASS' if ok else 'FAIL'}  {name}"
          + (f"  ({detail})" if detail and not ok else ""))


def close(a, b, tol=0.01):
    return a is not None and b is not None and abs(a - b) <= tol


def rag_revenue(actual, target):
    if actual >= target:
        return "GREEN"
    if actual >= 0.95 * target:
        return "AMBER"
    return "RED"


def rag_margin(actual_pct, target_pct):
    if actual_pct >= target_pct:
        return "GREEN"
    if actual_pct >= target_pct - 2.0:
        return "AMBER"
    return "RED"


def rag_returns(actual_pct, target_pct):
    if actual_pct <= target_pct:
        return "GREEN"
    if actual_pct <= target_pct + 1.0:
        return "AMBER"
    return "RED"


def rag_new(actual, target):
    if actual >= target:
        return "GREEN"
    if actual >= 0.80 * target:
        return "AMBER"
    return "RED"


def read_csv(name):
    with open(ROOT / "data" / "raw" / name, newline="") as f:
        return list(csv.DictReader(f))


def main():
    # ================= 1. Files exist =================
    expected = [
        "README.md", "PACKAGE-NOTE.md", "requirements.txt", ".gitignore",
        "data/README.md", "data/schema.sql",
        "data/raw/daily_sales.csv", "data/raw/monthly_targets.csv",
        "data/raw/monthly_prior_year.csv", "data/raw/data_manifest.json",
        "data/processed/noormart.db",
        "sql/01_monthly_kpi.sql", "sql/02_growth.sql",
        "sql/03_target_variance.sql", "sql/04_category_mix.sql",
        "powerbi/model.md", "powerbi/dax_measures.md",
        "powerbi/build_guide.md",
        "src/generate_data.py", "src/load_data.py", "src/analyze.py",
        "src/build_charts.py", "src/build_workbook.py",
        "src/build_report.py", "src/checks.py",
        "outputs/summary.json", "outputs/executive_kpi_pack_SAMPLE.xlsx",
        "outputs/executive_kpi_pack_SAMPLE.pdf",
        "outputs/revenue_vs_target.png", "outputs/kpi_trend.png",
        "outputs/category_mix.png", "outputs/orders_aov.png",
    ]
    for f in expected:
        check(f"file exists: {f}", (ROOT / f).exists())

    # ================= 2. Raw CSVs =================
    sales = read_csv("daily_sales.csv")
    targets = read_csv("monthly_targets.csv")
    prior = read_csv("monthly_prior_year.csv")
    manifest = json.loads((ROOT / "data" / "raw" / "data_manifest.json").read_text())

    check("daily_sales: 2,230 lines",
          len(sales) == 2230, f"got {len(sales)}")
    check("daily_sales: header is the 13 expected columns",
          list(sales[0]) == ["order_id", "sale_date", "customer_id",
                             "customer_type", "channel", "product",
                             "category", "qty", "unit_price_pkr",
                             "unit_cost_pkr", "line_amount_pkr", "returned"])
    months = sorted({r["sale_date"][:7] for r in sales})
    check("daily_sales: all 12 months of 2026 present",
          months == [f"2026-{m:02d}" for m in range(1, 13)], str(months))
    bad_dates = [r for r in sales
                 if not (len(r["sale_date"]) == 10
                         and r["sale_date"][4] == "-")]
    check("daily_sales: all sale_dates are ISO YYYY-MM-DD", not bad_dates,
          f"{len(bad_dates)} bad")
    try:
        for r in sales:
            date.fromisoformat(r["sale_date"])
        dates_ok = True
    except ValueError:
        dates_ok = False
    check("daily_sales: all sale_dates are real calendar dates", dates_ok)
    key_nulls = [r for r in sales if not all(
        r[c] for c in ("order_id", "sale_date", "customer_id", "product",
                       "category", "qty", "unit_price_pkr",
                       "line_amount_pkr"))]
    check("daily_sales: no nulls in key fields", not key_nulls,
          f"{len(key_nulls)} rows")
    bad_amount = [r for r in sales
                  if abs(float(r["line_amount_pkr"])
                         - int(r["qty"]) * float(r["unit_price_pkr"])) > 0.01]
    check("daily_sales: every line_amount = qty x unit_price",
          not bad_amount, f"{len(bad_amount)} mismatches")
    bad_cost = [r for r in sales
                if float(r["unit_cost_pkr"]) >= float(r["unit_price_pkr"])]
    check("daily_sales: unit_cost < unit_price on every line",
          not bad_cost, f"{len(bad_cost)} violations")
    check("daily_sales: returned is 0 or 1 only",
          {r["returned"] for r in sales} <= {"0", "1"})
    check("daily_sales: customer_type is new or repeat only",
          {r["customer_type"] for r in sales} <= {"new", "repeat"})
    check("daily_sales: channel is Store or Online only",
          {r["channel"] for r in sales} <= {"Store", "Online"})
    check("daily_sales: 5 categories",
          {r["category"] for r in sales} == {
              "Groceries", "Electronics", "Home & Kitchen",
              "Clothing", "Beauty & Care"})
    check("daily_sales: 25 products",
          len({r["product"] for r in sales}) == 25)
    check("daily_sales: 1,321 distinct orders",
          len({r["order_id"] for r in sales}) == 1321)
    check("daily_sales: 392 distinct customers",
          len({r["customer_id"] for r in sales}) == 392)
    check("monthly_targets: 12 rows, all 2026 months",
          [r["month"] for r in targets] == [f"2026-{m:02d}" for m in range(1, 13)])
    check("monthly_targets: margin target 23.5 every month",
          all(float(r["gross_margin_pct_target"]) == 23.5 for r in targets))
    check("monthly_targets: returns target 4.5 every month",
          all(float(r["returns_rate_pct_target"]) == 4.5 for r in targets))
    check("monthly_targets: new-customer target 32 every month",
          all(int(r["new_customers_target"]) == 32 for r in targets))
    check("monthly_targets: all revenue targets > 0",
          all(float(r["revenue_target_pkr"]) > 0 for r in targets))
    check("monthly_prior_year: 12 rows, all 2025 months",
          [r["month"] for r in prior] == [f"2025-{m:02d}" for m in range(1, 13)])
    check("monthly_prior_year: all revenues > 0",
          all(float(r["revenue_pkr"]) > 0 for r in prior))

    gross = sum(float(r["line_amount_pkr"]) for r in sales)
    ret = sum(float(r["line_amount_pkr"]) for r in sales if r["returned"] == "1")
    check("manifest: sale lines = CSV count",
          manifest["totals"]["sale_lines"] == len(sales))
    check("manifest: gross sales PKR 13,983,480.00",
          close(manifest["totals"]["gross_sales_pkr"], gross), f"{gross:,.2f}")
    check("manifest: returns PKR 496,937.00",
          close(manifest["totals"]["returns_pkr"], ret), f"{ret:,.2f}")
    check("manifest: net revenue = gross - returns",
          close(manifest["totals"]["net_revenue_pkr"], gross - ret))

    # ---- determinism: regenerating must be byte-identical ----
    before = hashlib.sha256(
        (ROOT / "data" / "raw" / "daily_sales.csv").read_bytes()).hexdigest()
    r = subprocess.run([sys.executable, str(ROOT / "src" / "generate_data.py")],
                       capture_output=True, text=True)
    after = hashlib.sha256(
        (ROOT / "data" / "raw" / "daily_sales.csv").read_bytes()).hexdigest()
    check("generate_data.py is deterministic (byte-identical re-run)",
          r.returncode == 0 and before == after)

    # ================= 3. Database =================
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    q = lambda sql: conn.execute(sql).fetchone()[0]
    check("db: fact_sales has 2,230 rows", q("SELECT COUNT(*) FROM fact_sales") == 2230)
    check("db: dim_product has 25 rows", q("SELECT COUNT(*) FROM dim_product") == 25)
    check("db: dim_customer has 392 rows", q("SELECT COUNT(*) FROM dim_customer") == 392)
    check("db: monthly_kpi has 12 rows", q("SELECT COUNT(*) FROM monthly_kpi") == 12)
    check("db: category_monthly has 60 rows (12 x 5)",
          q("SELECT COUNT(*) FROM category_monthly") == 60)
    check("db: monthly_targets has 12 rows",
          q("SELECT COUNT(*) FROM monthly_targets") == 12)
    check("db: monthly_prior_year has 12 rows",
          q("SELECT COUNT(*) FROM monthly_prior_year") == 12)
    check("db: no fact_sales orphans (customer FK)",
          q("SELECT COUNT(*) FROM fact_sales f LEFT JOIN dim_customer c "
            "ON c.customer_key = f.customer_key WHERE c.customer_key IS NULL") == 0)
    check("db: no fact_sales orphans (product FK)",
          q("SELECT COUNT(*) FROM fact_sales f LEFT JOIN dim_product p "
            "ON p.product_key = f.product_key WHERE p.product_key IS NULL") == 0)
    check("db: staging counts match the CSVs",
          q("SELECT COUNT(*) FROM stg_daily_sales") == len(sales)
          and q("SELECT COUNT(*) FROM stg_monthly_targets") == 12
          and q("SELECT COUNT(*) FROM stg_prior_year") == 12)

    db_kpi = {r["month"]: dict(r) for r in conn.execute(
        "SELECT * FROM monthly_kpi ORDER BY month")}
    db_var = {r["month"]: dict(r) for r in conn.execute(
        open(ROOT / "sql" / "03_target_variance.sql").read())}
    db_growth = {r["month"]: dict(r) for r in conn.execute(
        open(ROOT / "sql" / "02_growth.sql").read())}
    db_targets = {r["month"]: dict(r) for r in conn.execute(
        "SELECT * FROM monthly_targets")}
    db_prior = {r["month"]: dict(r) for r in conn.execute(
        "SELECT * FROM monthly_prior_year")}
    db_cats = [dict(r) for r in conn.execute(
        open(ROOT / "sql" / "04_category_mix.sql").read()
        .split("-- annual mix")[1])]

    # ================= 4. Independent Python recompute =================
    # First order per customer, from the CSV (not the DB).
    first_order = {}
    for r in sorted(sales, key=lambda x: (x["sale_date"], x["order_id"])):
        first_order.setdefault(r["customer_id"], r["sale_date"][:7])
    for month in [f"2026-{m:02d}" for m in range(1, 13)]:
        rows = [r for r in sales if r["sale_date"][:7] == month]
        kept = [r for r in rows if r["returned"] == "0"]
        net = sum(float(r["line_amount_pkr"]) for r in kept)
        gross_m = sum(float(r["line_amount_pkr"]) for r in rows)
        ret_m = sum(float(r["line_amount_pkr"]) for r in rows if r["returned"] == "1")
        profit = sum((float(r["unit_price_pkr"]) - float(r["unit_cost_pkr"]))
                     * int(r["qty"]) for r in kept)
        orders = len({r["order_id"] for r in rows})
        new = sum(1 for c, fm in first_order.items() if fm == month)
        repeat = len({r["customer_id"] for r in rows
                      if first_order[r["customer_id"]] < month})
        k = db_kpi[month]
        check(f"{month}: net revenue", close(k["net_revenue_pkr"], net),
              f"db {k['net_revenue_pkr']:,.2f} vs recompute {net:,.2f}")
        check(f"{month}: gross sales", close(k["gross_sales_pkr"], gross_m))
        check(f"{month}: returns", close(k["returns_pkr"], ret_m))
        check(f"{month}: gross profit", close(k["gross_profit_pkr"], profit),
              f"db {k['gross_profit_pkr']:,.2f} vs recompute {profit:,.2f}")
        check(f"{month}: orders", k["orders"] == orders,
              f"db {k['orders']} vs recompute {orders}")
        check(f"{month}: new customers", k["new_customers"] == new,
              f"db {k['new_customers']} vs recompute {new}")
        check(f"{month}: repeat customers", k["repeat_customers"] == repeat,
              f"db {k['repeat_customers']} vs recompute {repeat}")
        check(f"{month}: margin %",
              close(k["gross_margin_pct"], round(100 * profit / net, 2), 0.05))
        check(f"{month}: returns rate %",
              close(k["returns_rate_pct"], round(100 * ret_m / gross_m, 2), 0.05))
        check(f"{month}: avg order value",
              close(k["avg_order_value_pkr"], round(net / orders, 2)))

    annual_net = sum(k["net_revenue_pkr"] for k in db_kpi.values())
    annual_gross = sum(k["gross_sales_pkr"] for k in db_kpi.values())
    annual_ret = sum(k["returns_pkr"] for k in db_kpi.values())
    annual_profit = sum(k["gross_profit_pkr"] for k in db_kpi.values())
    check("annual: net revenue PKR 13,486,543.00",
          close(annual_net, 13_486_543.00), f"{annual_net:,.2f}")
    check("annual: gross - returns = net",
          close(annual_gross - annual_ret, annual_net))
    check("annual: gross margin 23.49%",
          close(round(100 * annual_profit / annual_net, 2), 23.49, 0.05))
    check("annual: 1,321 orders",
          sum(k["orders"] for k in db_kpi.values()) == 1321)
    check("annual: category revenue sums to monthly net revenue",
          close(sum(c["net_revenue_pkr"] for c in db_cats), annual_net))
    check("annual: category shares sum to 100%",
          close(sum(c["share_pct"] for c in db_cats), 100.0, 0.1))
    check("category: Electronics is the largest (44.0%)",
          db_cats[0]["category"] == "Electronics"
          and close(db_cats[0]["share_pct"], 43.95, 0.1))
    check("category: 5 categories in the annual mix", len(db_cats) == 5)

    # ================= 5. RAG rules, re-implemented =================
    for month in [f"2026-{m:02d}" for m in range(1, 13)]:
        k, t, v = db_kpi[month], db_targets[month], db_var[month]
        check(f"{month}: revenue RAG",
              v["revenue_rag"] == rag_revenue(k["net_revenue_pkr"],
                                              t["revenue_target_pkr"]),
              f"sql {v['revenue_rag']}")
        check(f"{month}: orders RAG",
              v["orders_rag"] == rag_revenue(k["orders"], t["orders_target"]))
        check(f"{month}: margin RAG",
              v["margin_rag"] == rag_margin(k["gross_margin_pct"],
                                            t["gross_margin_pct_target"]))
        check(f"{month}: returns RAG",
              v["returns_rag"] == rag_returns(k["returns_rate_pct"],
                                              t["returns_rate_pct_target"]))
        check(f"{month}: new-customers RAG",
              v["new_customers_rag"] == rag_new(k["new_customers"],
                                                t["new_customers_target"]))
    rag_counts = {"GREEN": 0, "AMBER": 0, "RED": 0}
    for v in db_var.values():
        rag_counts[v["revenue_rag"]] += 1
    check("revenue RAG year: 6 green / 3 amber / 3 red",
          rag_counts == {"GREEN": 6, "AMBER": 3, "RED": 3}, str(rag_counts))

    # ================= 6. Growth =================
    for i, month in enumerate([f"2026-{m:02d}" for m in range(1, 13)]):
        k, g = db_kpi[month], db_growth[month]
        py = db_prior["2025-" + month[5:]]
        check(f"{month}: YoY revenue %",
              close(g["revenue_yoy_pct"],
                    round(100 * (k["net_revenue_pkr"] - py["revenue_pkr"])
                          / py["revenue_pkr"], 2), 0.05))
        if i > 0:
            prev = db_kpi[f"2026-{i:02d}"]["net_revenue_pkr"]
            check(f"{month}: MoM revenue %",
                  close(g["revenue_mom_pct"],
                        round(100 * (k["net_revenue_pkr"] - prev) / prev, 2),
                        0.05))
    check("growth: December MoM is -11.52%",
          close(db_growth["2026-12"]["revenue_mom_pct"], -11.52, 0.05))
    check("growth: December YoY is +23.55%",
          close(db_growth["2026-12"]["revenue_yoy_pct"], 23.55, 0.05))

    # ================= 7. Targets vs the plan =================
    for month in [f"2026-{m:02d}" for m in range(1, 13)]:
        planned = manifest["plan"][month]["planned_revenue_pkr"]
        check(f"{month}: revenue target = plan x 1.03",
              close(db_targets[month]["revenue_target_pkr"], planned * 1.03))

    # ================= 8. Workbook structure (formulas present) ====
    wb = load_workbook(XLSX)
    check("workbook: 5 sheets in order",
          wb.sheetnames == ["Cover", "Monthly KPI", "Targets",
                            "Category Mix", "Data Dictionary"],
          str(wb.sheetnames))
    mk = wb["Monthly KPI"]
    for cell in ("D2", "F2", "I2", "L2", "N2", "O3", "B14"):
        check(f"workbook: Monthly KPI {cell} is a live formula",
              isinstance(mk[cell].value, str)
              and mk[cell].value.startswith("="), str(mk[cell].value))
    tg = wb["Targets"]
    for cell in ("G2", "H2", "J2", "L2", "N2", "P2"):
        check(f"workbook: Targets {cell} is a live formula",
              isinstance(tg[cell].value, str)
              and tg[cell].value.startswith("="), str(tg[cell].value))
    cm = wb["Category Mix"]
    check("workbook: Category Mix G2 is a live total formula",
          isinstance(cm["G2"].value, str) and cm["G2"].value.startswith("="))
    cov = wb["Cover"]
    check("workbook: Cover B6 (Dec revenue) is a formula",
          isinstance(cov["B6"].value, str) and cov["B6"].value.startswith("="))
    check("workbook: Cover B16 (Jan trend) is a formula",
          isinstance(cov["B16"].value, str) and cov["B16"].value.startswith("="))
    check("workbook: no post-2007 functions used (AGGREGATE/MINIFS/MAXIFS)",
          not any(isinstance(c.value, str)
                  and any(f in c.value.upper()
                          for f in ("AGGREGATE", "MINIFS", "MAXIFS"))
                  for ws in wb.worksheets for row in ws.iter_rows()
                  for c in row))

    # ================= 9. LibreOffice recalc =================
    recalc_dir = ROOT / "outputs" / ".recalc"
    if recalc_dir.exists():
        shutil.rmtree(recalc_dir)
    recalc_dir.mkdir()
    r = subprocess.run(["soffice", "--headless", "--calc", "--convert-to",
                        "xlsx", "--outdir", str(recalc_dir), str(XLSX)],
                       capture_output=True, text=True, timeout=180)
    check("libreoffice recalc ran", r.returncode == 0, r.stderr.strip()[:200])
    wb2 = load_workbook(recalc_dir / XLSX.name, data_only=True)
    mk2, tg2, cm2, cov2 = (wb2["Monthly KPI"], wb2["Targets"],
                           wb2["Category Mix"], wb2["Cover"])
    for i, month in enumerate([f"2026-{m:02d}" for m in range(1, 13)]):
        row = i + 2
        check(f"recalc: {month} revenue",
              close(mk2.cell(row=row, column=2).value,
                    db_kpi[month]["net_revenue_pkr"]),
              str(mk2.cell(row=row, column=2).value))
    check("recalc: annual total revenue",
          close(mk2["B14"].value, annual_net), str(mk2["B14"].value))
    check("recalc: Dec AOV", close(mk2["D13"].value, 10550.08, 0.05),
          str(mk2["D13"].value))
    check("recalc: Dec margin %", close(mk2["F13"].value, 0.2271, 0.001),
          str(mk2["F13"].value))
    check("recalc: Dec returns %", close(mk2["I13"].value, 0.0457, 0.001),
          str(mk2["I13"].value))
    check("recalc: Dec repeat %", close(mk2["L13"].value, 0.6698, 0.001),
          str(mk2["L13"].value))
    check("recalc: Dec YoY %", close(mk2["N13"].value, 0.2355, 0.001),
          str(mk2["N13"].value))
    check("recalc: Dec MoM %", close(mk2["O13"].value, -0.1152, 0.001),
          str(mk2["O13"].value))
    check("recalc: Jan MoM is blank (no previous month)",
          mk2["O2"].value in (None, ""))
    for i, month in enumerate([f"2026-{m:02d}" for m in range(1, 13)]):
        row = i + 2
        check(f"recalc: {month} revenue RAG",
              tg2.cell(row=row, column=8).value == db_var[month]["revenue_rag"],
              str(tg2.cell(row=row, column=8).value))
    check("recalc: Dec revenue variance %",
          close(tg2["G13"].value, -0.0177, 0.001), str(tg2["G13"].value))
    check("recalc: Dec margin variance pts",
          close(tg2["K13"].value, -0.79, 0.05), str(tg2["K13"].value))
    check("recalc: Dec returns variance pts",
          close(tg2["M13"].value, 0.07, 0.05), str(tg2["M13"].value))
    check("recalc: Dec new-customers RAG",
          tg2["P13"].value == db_var["2026-12"]["new_customers_rag"])
    check("recalc: Cover Dec revenue",
          close(cov2["B6"].value, db_kpi["2026-12"]["net_revenue_pkr"]),
          str(cov2["B6"].value))
    check("recalc: Cover Dec revenue RAG",
          cov2["E6"].value == db_var["2026-12"]["revenue_rag"])
    check("recalc: Cover Dec margin RAG",
          cov2["E9"].value == db_var["2026-12"]["margin_rag"])
    check("recalc: Cover Dec new-customers RAG",
          cov2["E11"].value == db_var["2026-12"]["new_customers_rag"])
    for i, month in enumerate([f"2026-{m:02d}" for m in range(1, 13)]):
        row = 16 + i
        check(f"recalc: Cover trend {month} revenue",
              close(cov2.cell(row=row, column=2).value,
                    db_kpi[month]["net_revenue_pkr"]))
    for i, month in enumerate([f"2026-{m:02d}" for m in range(1, 13)]):
        row = i + 2
        check(f"recalc: Category Mix {month} total",
              close(cm2.cell(row=row, column=7).value,
                    db_kpi[month]["net_revenue_pkr"]),
              str(cm2.cell(row=row, column=7).value))
    check("recalc: Category Mix annual total",
          close(cm2["G14"].value, annual_net), str(cm2["G14"].value))
    errors = []
    for ws in wb2.worksheets:
        for row in ws.iter_rows():
            for c in row:
                if isinstance(c.value, str) and c.value.startswith("#"):
                    errors.append(f"{ws.title}!{c.coordinate}={c.value}")
    check("recalc: zero error values in the workbook", not errors,
          "; ".join(errors[:5]))
    shutil.rmtree(recalc_dir)

    # ================= 10. PDF =================
    check("pdf: exists and is over 20 KB",
          PDF.exists() and PDF.stat().st_size > 20_000,
          f"{PDF.stat().st_size} bytes" if PDF.exists() else "missing")
    r = subprocess.run(["pdfinfo", str(PDF)], capture_output=True, text=True)
    pages = [ln for ln in r.stdout.splitlines() if ln.startswith("Pages:")]
    check("pdf: exactly 1 page", pages and pages[0].strip() == "Pages:           1",
          str(pages))

    # ================= 11. summary.json =================
    s = json.loads(SUMMARY.read_text())
    check("summary: annual net revenue matches the DB",
          close(s["annual"]["net_revenue_pkr"], annual_net))
    check("summary: annual orders = 1,321", s["annual"]["orders"] == 1321)
    check("summary: annual margin 23.49%",
          close(s["annual"]["gross_margin_pct"], 23.49, 0.05))
    check("summary: Dec revenue matches the DB",
          close(s["pack_month_kpi"]["net_revenue_pkr"],
                db_kpi["2026-12"]["net_revenue_pkr"]))
    check("summary: best month is March 2026",
          s["best_month"]["month"] == "2026-03")
    check("summary: worst month is June 2026",
          s["worst_month"]["month"] == "2026-06")
    check("summary: narrative names the December figure",
          "1,234,359" in " ".join(s["narrative"]))
    check("summary: narrative names the best month",
          "March 2026" in " ".join(s["narrative"]))
    check("summary: attention list has 7 items", len(s["attention"]) == 7)
    check("summary: 12 monthly rows", len(s["monthly"]) == 12)

    # ================= 12. Charts =================
    for name in ("revenue_vs_target.png", "kpi_trend.png",
                 "category_mix.png", "orders_aov.png"):
        p = ROOT / "outputs" / name
        check(f"chart: {name} exists and is over 10 KB",
              p.exists() and p.stat().st_size > 10_000)

    # ================= 13. Power BI docs =================
    model = (ROOT / "powerbi" / "model.md").read_text()
    check("powerbi: model doc names the star schema",
          "star schema" in model.lower())
    for table in ("fact_sales", "dim_product", "dim_customer",
                  "monthly_targets", "monthly_prior_year", "dim_date"):
        check(f"powerbi: model doc covers {table}", table in model)
    dax = (ROOT / "powerbi" / "dax_measures.md").read_text()
    measures = ["Total Revenue", "Gross Sales", "Returns Amount",
                "Returns Rate %", "Gross Profit", "Gross Margin %",
                "Total Orders", "Average Order Value", "New Customers",
                "Repeat Rate %", "Revenue MoM %", "Revenue YoY %"]
    for m in measures:
        check(f"powerbi: DAX measure present — {m}", m in dax)
    check("powerbi: DAX verification table has the December revenue",
          "1,234,359" in dax)
    check("powerbi: DAX verification table has the annual revenue",
          "13,486,543" in dax)
    guide = (ROOT / "powerbi" / "build_guide.md").read_text()
    check("powerbi: build guide covers data, model, measures, pack",
          all(word in guide for word in
              ("Get the data", "Model it", "measures", "one-page pack")))

    # ================= 14. README + package note =================
    readme = (ROOT / "README.md").read_text()
    for needle in ("13,486,543", "1,234,359", "1,396,518", "929,233",
                   "392 customers", "SAMPLE", "2,230 sale lines"):
        check(f"README: contains {needle!r}", needle in readme)
    note = (ROOT / "PACKAGE-NOTE.md").read_text()
    for needle in ("$20", "$65", "$140", "monthly executive KPI pack"):
        check(f"PACKAGE-NOTE: contains {needle!r}", needle in note)

    conn.close()
    print(f"\n{CHECKS - len(FAILURES)}/{CHECKS} checks passed")
    if FAILURES:
        print(f"{len(FAILURES)} FAILURES:")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
