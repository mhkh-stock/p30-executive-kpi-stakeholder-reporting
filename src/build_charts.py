"""P30 — preview charts for the pack (matplotlib renders, not screenshots).

The same four charts the Power BI build guide tells the client to
build — rendered here from the database so the repo shows the pack's
shape before anyone opens Power BI:
  revenue_vs_target.png — monthly net revenue vs target (RAG bars)
  kpi_trend.png         — revenue bars + gross-margin % line
  category_mix.png      — annual revenue share by category (donut)
  orders_aov.png        — monthly orders + average order value

Usage:  python3 src/build_charts.py
"""
import json
import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "processed" / "noormart.db"
OUT = ROOT / "outputs"

GREEN = "#1F7A3A"
AMBER = "#C77D00"
RED = "#B3261E"
NAVY = "#1F3864"
GREY = "#6B7280"
LIGHT = "#E8EDF3"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.edgecolor": "#CBD5E1",
    "axes.labelcolor": "#1F2937",
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.titlecolor": NAVY,
    "figure.facecolor": "white",
})


def pkr_m(x, _pos=None):
    if x >= 1_000_000:
        return f"PKR {x / 1_000_000:.1f}M"
    return f"PKR {x / 1_000:.0f}k"


def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    months = [dict(r) for r in conn.execute(
        "SELECT k.*, t.revenue_target_pkr, t.orders_target, "
        "t.gross_margin_pct_target FROM monthly_kpi k "
        "JOIN monthly_targets t ON t.month = k.month ORDER BY k.month")]
    var = {r["month"]: dict(r) for r in conn.execute(
        open(ROOT / "sql" / "03_target_variance.sql").read())}
    cats = [dict(r) for r in conn.execute(
        open(ROOT / "sql" / "04_category_mix.sql").read()
        .split("-- annual mix")[1])]
    conn.close()
    labels = [m["month"][5:] + "/" + m["month"][2:4] for m in months]
    rag_color = {"GREEN": GREEN, "AMBER": AMBER, "RED": RED}
    colors = [rag_color[var[m["month"]]["revenue_rag"]] for m in months]

    # ---- 1. revenue vs target ----
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.bar(labels, [m["net_revenue_pkr"] for m in months],
           color=colors, width=0.65, label="Net revenue (actual)")
    ax.plot(labels, [m["revenue_target_pkr"] for m in months],
            color=NAVY, marker="o", ms=4, lw=2, label="Target")
    ax.set_title("NoorMart — monthly net revenue vs target (SAMPLE, 2026)")
    ax.yaxis.set_major_formatter(FuncFormatter(pkr_m))
    ax.set_ylabel("Net revenue")
    ax.grid(axis="y", color=LIGHT, lw=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    fig.savefig(OUT / "revenue_vs_target.png", dpi=150)
    plt.close(fig)

    # ---- 2. revenue + margin trend ----
    fig, ax1 = plt.subplots(figsize=(10, 4.2))
    ax1.bar(labels, [m["net_revenue_pkr"] for m in months],
            color="#9DB8D2", width=0.65, label="Net revenue")
    ax1.yaxis.set_major_formatter(FuncFormatter(pkr_m))
    ax1.set_ylabel("Net revenue")
    ax2 = ax1.twinx()
    ax2.plot(labels, [m["gross_margin_pct"] for m in months],
             color=RED, marker="o", ms=4, lw=2, label="Gross margin %")
    ax2.axhline(23.5, color=GREY, ls="--", lw=1, label="Margin target 23.5%")
    ax2.set_ylabel("Gross margin %")
    ax2.set_ylim(18, 28)
    ax1.set_title("Revenue and gross margin — margin is capped by the mix")
    ax1.grid(axis="y", color=LIGHT, lw=0.8)
    ax1.set_axisbelow(True)
    for s in ("top", "right"):
        ax1.spines[s].set_visible(False)
        ax2.spines[s].set_visible(False)
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, frameon=False, loc="upper left")
    fig.tight_layout()
    fig.savefig(OUT / "kpi_trend.png", dpi=150)
    plt.close(fig)

    # ---- 3. category mix donut ----
    cat_colors = {"Electronics": NAVY, "Home & Kitchen": "#2E7D6F",
                  "Groceries": "#8A6D3B", "Clothing": "#7C3AED",
                  "Beauty & Care": "#C77D00"}
    fig, ax = plt.subplots(figsize=(6.5, 4.6))
    wedges, _, autotexts = ax.pie(
        [c["net_revenue_pkr"] for c in cats],
        labels=[c["category"] for c in cats],
        colors=[cat_colors[c["category"]] for c in cats],
        autopct=lambda p: f"{p:.0f}%" if p >= 5 else "",
        pctdistance=0.78, wedgeprops=dict(width=0.42, edgecolor="white"),
        startangle=90)
    for t in autotexts:
        t.set_color("white")
        t.set_fontweight("bold")
    ax.set_title("Annual revenue share by category (SAMPLE, 2026)")
    ax.text(0, 0, "PKR 13.5M\nnet revenue", ha="center", va="center",
            fontsize=11, fontweight="bold", color=NAVY)
    fig.tight_layout()
    fig.savefig(OUT / "category_mix.png", dpi=150)
    plt.close(fig)

    # ---- 4. orders + AOV ----
    fig, ax1 = plt.subplots(figsize=(10, 4.2))
    ax1.bar(labels, [m["orders"] for m in months],
            color="#9DB8D2", width=0.65, label="Orders")
    ax1.set_ylabel("Orders")
    ax2 = ax1.twinx()
    ax2.plot(labels, [m["avg_order_value_pkr"] for m in months],
             color=NAVY, marker="o", ms=4, lw=2, label="Avg order value")
    ax2.yaxis.set_major_formatter(FuncFormatter(
        lambda x, _p: f"PKR {x:,.0f}"))
    ax2.set_ylabel("Average order value (PKR)")
    ax1.set_title("Orders and average order value — fewer, bigger baskets in May")
    ax1.grid(axis="y", color=LIGHT, lw=0.8)
    ax1.set_axisbelow(True)
    for s in ("top", "right"):
        ax1.spines[s].set_visible(False)
        ax2.spines[s].set_visible(False)
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, frameon=False, loc="upper left")
    fig.tight_layout()
    fig.savefig(OUT / "orders_aov.png", dpi=150)
    plt.close(fig)

    for name in ("revenue_vs_target.png", "kpi_trend.png",
                 "category_mix.png", "orders_aov.png"):
        print(f"wrote {name}")


if __name__ == "__main__":
    main()
