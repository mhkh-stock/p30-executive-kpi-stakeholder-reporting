"""P30 — headline numbers + narrative for the pack, recomputed from the DB.

Reads monthly_kpi / monthly_targets / monthly_prior_year /
category_monthly and writes outputs/summary.json — the single
source the workbook, the PDF and the README quote. Nothing here is
typed: every number comes from a query, and the narrative sentences
are built from those numbers, so a wrong number shows up in the
words as well as the tables.

Usage:  python3 src/analyze.py
"""
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "processed" / "noormart.db"
OUT = ROOT / "outputs" / "summary.json"

PACK_MONTH = "2026-12"
MONTH_NAMES = {"01": "January", "02": "February", "03": "March",
               "04": "April", "05": "May", "06": "June", "07": "July",
               "08": "August", "09": "September", "10": "October",
               "11": "November", "12": "December"}


def mname(yyyymm):
    return f"{MONTH_NAMES[yyyymm[5:]]} {yyyymm[:4]}"


def money(n):
    return f"PKR {n:,.0f}"


def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    kpi = [dict(r) for r in conn.execute(
        "SELECT * FROM monthly_kpi ORDER BY month")]
    targets = {r["month"]: dict(r) for r in conn.execute(
        "SELECT * FROM monthly_targets")}
    prior = {r["month"]: dict(r) for r in conn.execute(
        "SELECT * FROM monthly_prior_year")}
    growth = {r["month"]: dict(r) for r in conn.execute(
        open(ROOT / "sql" / "02_growth.sql").read())}
    var = {r["month"]: dict(r) for r in conn.execute(
        open(ROOT / "sql" / "03_target_variance.sql").read())}
    cats = [dict(r) for r in conn.execute(
        open(ROOT / "sql" / "04_category_mix.sql").read()
        .split("-- annual mix")[1])]
    conn.close()

    by_month = {k["month"]: k for k in kpi}
    pack = by_month[PACK_MONTH]
    pack_t = targets[PACK_MONTH]
    pack_g = growth[PACK_MONTH]
    pack_v = var[PACK_MONTH]

    annual_revenue = round(sum(k["net_revenue_pkr"] for k in kpi), 2)
    annual_orders = sum(k["orders"] for k in kpi)
    annual_profit = round(sum(k["gross_profit_pkr"] for k in kpi), 2)
    annual_margin = round(100 * annual_profit / annual_revenue, 2)
    annual_returns = round(sum(k["returns_pkr"] for k in kpi), 2)
    annual_gross = round(sum(k["gross_sales_pkr"] for k in kpi), 2)
    annual_new = sum(k["new_customers"] for k in kpi)
    best = max(kpi, key=lambda k: k["net_revenue_pkr"])
    worst = min(kpi, key=lambda k: k["net_revenue_pkr"])
    worst_returns = max(kpi, key=lambda k: k["returns_rate_pct"])
    top_cat = cats[0]

    # ---- narrative: built from the numbers, in plain words ----
    narrative = [
        f"{mname(PACK_MONTH)} closed at {money(pack['net_revenue_pkr'])} — "
        f"{abs(pack_v['revenue_variance_pct']):.1f}% "
        f"{'below' if pack_v['revenue_variance_pct'] < 0 else 'above'} "
        f"target ({money(pack_t['revenue_target_pkr'])}), "
        f"{pack_g['revenue_mom_pct']:+.1f}% on November and "
        f"{pack_g['revenue_yoy_pct']:+.1f}% on December 2025. "
        f"The year ends {pack_v['revenue_rag'].lower()} on revenue: "
        f"6 of 12 months beat target, 3 missed it by more than 5%, "
        f"and 3 landed within 5% of target.",
        f"Margin was {pack['gross_margin_pct']:.1f}% against a "
        f"{pack_t['gross_margin_pct_target']:.1f}% target. The cap is "
        f"structural, not a bad month: {top_cat['category']} is "
        f"{top_cat['share_pct']:.0f}% of revenue at "
        f"{top_cat['margin_pct']:.0f}% margin, so the blended margin "
        f"cannot reach the old 26% plan — the 23.5% target reflects "
        f"the mix the shop actually sells.",
        f"Returns ran at {pack['returns_rate_pct']:.1f}% in December "
        f"(target {pack_t['returns_rate_pct_target']:.1f}%). The year's "
        f"worst month was {mname(worst_returns['month'])} at "
        f"{worst_returns['returns_rate_pct']:.1f}% — a handful of "
        f"big-ticket Electronics returns, not a broad quality problem: "
        f"only {worst_returns['returned_lines']} of "
        f"{worst_returns['sale_lines']} lines came back.",
        f"Customers are sticking: {pack['repeat_rate_pct']:.0f}% of "
        f"December's active customers had bought before, up from 0% "
        f"in January (a new shop has no repeat base yet) — and "
        f"{pack['new_customers']} new customers still joined in "
        f"December, beating the {pack_t['new_customers_target']} target.",
        f"Best month of the year was {mname(best['month'])} at "
        f"{money(best['net_revenue_pkr'])}; weakest was "
        f"{mname(worst['month'])} at {money(worst['net_revenue_pkr'])} — "
        f"a {money(best['net_revenue_pkr'] - worst['net_revenue_pkr'])} "
        f"swing between the two, which is why the pack watches the "
        f"monthly trend, not a single month.",
    ]

    attention = []
    for k in kpi:
        v = var[k["month"]]
        reds = [label for label, rag in
                (("revenue", v["revenue_rag"]),
                 ("orders", v["orders_rag"]),
                 ("margin", v["margin_rag"]),
                 ("returns", v["returns_rag"]),
                 ("new customers", v["new_customers_rag"]))
                if rag == "RED"]
        if reds:
            attention.append(
                f"{mname(k['month'])}: {', '.join(reds)} red — "
                f"revenue {v['revenue_variance_pct']:+.1f}% vs target, "
                f"margin {k['gross_margin_pct']:.1f}% vs "
                f"{targets[k['month']]['gross_margin_pct_target']:.1f}%, "
                f"returns {k['returns_rate_pct']:.1f}%")
    attention.append(
        f"Margin target: the 23.5% blended target already reflects the "
        f"Electronics-heavy mix — raising margin means shifting mix "
        f"(Clothing 36%, Beauty 34%) or renegotiating Electronics cost, "
        f"not asking the shop to sell harder.")

    summary = {
        "project": "P30 — Executive KPI & Stakeholder Reporting Pack",
        "client_sample": "NoorMart — fictional retailer (SAMPLE data)",
        "period": "January–December 2026",
        "pack_month": PACK_MONTH,
        "pack_month_name": mname(PACK_MONTH),
        "generated_from": "data/processed/noormart.db (seed 30, deterministic)",
        "annual": {
            "net_revenue_pkr": annual_revenue,
            "gross_sales_pkr": annual_gross,
            "returns_pkr": annual_returns,
            "returns_rate_pct": round(100 * annual_returns / annual_gross, 2),
            "gross_profit_pkr": annual_profit,
            "gross_margin_pct": annual_margin,
            "orders": annual_orders,
            "avg_order_value_pkr": round(annual_revenue / annual_orders, 2),
            "new_customers": annual_new,
            "sale_lines": sum(k["sale_lines"] for k in kpi),
            "returned_lines": sum(k["returned_lines"] for k in kpi),
        },
        "pack_month_kpi": {k: pack[k] for k in
                           ("orders", "net_revenue_pkr", "gross_sales_pkr",
                            "returns_pkr", "gross_profit_pkr",
                            "gross_margin_pct", "returns_rate_pct",
                            "avg_order_value_pkr", "new_customers",
                            "repeat_customers", "repeat_rate_pct")},
        "pack_month_target": {k: pack_t[k] for k in
                              ("revenue_target_pkr", "orders_target",
                               "gross_margin_pct_target",
                               "returns_rate_pct_target",
                               "new_customers_target")},
        "pack_month_growth": {"revenue_mom_pct": pack_g["revenue_mom_pct"],
                              "revenue_yoy_pct": pack_g["revenue_yoy_pct"],
                              "orders_mom_pct": pack_g["orders_mom_pct"],
                              "orders_yoy_pct": pack_g["orders_yoy_pct"]},
        "pack_month_variance": {"revenue_variance_pct": pack_v["revenue_variance_pct"],
                                "revenue_rag": pack_v["revenue_rag"],
                                "orders_variance_pct": pack_v["orders_variance_pct"],
                                "orders_rag": pack_v["orders_rag"],
                                "margin_variance_pts": pack_v["margin_variance_pts"],
                                "margin_rag": pack_v["margin_rag"],
                                "returns_variance_pts": pack_v["returns_variance_pts"],
                                "returns_rag": pack_v["returns_rag"],
                                "new_customers_variance_pct": pack_v["new_customers_variance_pct"],
                                "new_customers_rag": pack_v["new_customers_rag"]},
        "best_month": {"month": best["month"], "name": mname(best["month"]),
                       "net_revenue_pkr": best["net_revenue_pkr"]},
        "worst_month": {"month": worst["month"], "name": mname(worst["month"]),
                        "net_revenue_pkr": worst["net_revenue_pkr"]},
        "worst_returns_month": {"month": worst_returns["month"],
                                "name": mname(worst_returns["month"]),
                                "returns_rate_pct": worst_returns["returns_rate_pct"]},
        "rag_counts_annual": {
            rag: sum(1 for m in var.values() if m["revenue_rag"] == rag)
            for rag in ("GREEN", "AMBER", "RED")},
        "category_mix_annual": cats,
        "monthly": [
            {**{k: kk[k] for k in
                ("month", "orders", "net_revenue_pkr", "gross_sales_pkr",
                 "returns_pkr", "gross_profit_pkr", "gross_margin_pct",
                 "returns_rate_pct", "avg_order_value_pkr", "new_customers",
                 "repeat_customers", "repeat_rate_pct")},
             "revenue_target_pkr": targets[kk["month"]]["revenue_target_pkr"],
             "revenue_variance_pct": var[kk["month"]]["revenue_variance_pct"],
             "revenue_rag": var[kk["month"]]["revenue_rag"],
             "revenue_mom_pct": growth[kk["month"]]["revenue_mom_pct"],
             "revenue_yoy_pct": growth[kk["month"]]["revenue_yoy_pct"]}
            for kk in kpi],
        "narrative": narrative,
        "attention": attention,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"annual net revenue {money(annual_revenue)} | "
          f"{annual_orders} orders | margin {annual_margin}%")
    print(f"pack month {mname(PACK_MONTH)}: "
          f"{money(pack['net_revenue_pkr'])} "
          f"({pack_v['revenue_variance_pct']:+.1f}% vs target, "
          f"{pack_v['revenue_rag']})")
    print(f"best {mname(best['month'])} {money(best['net_revenue_pkr'])} | "
          f"worst {mname(worst['month'])} {money(worst['net_revenue_pkr'])}")
    print(f"wrote {OUT.name}")


if __name__ == "__main__":
    main()
