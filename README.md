# P30 — Executive KPI & Stakeholder Reporting Pack: what should I know this month, in one page?

**Client (SAMPLE):** NoorMart — fictional neighbourhood retailer, Lahore
· **Pack month:** December 2026 · **Status: SAMPLE delivery on synthetic data**
**Tools:** SQL (SQLite, star schema) · Python (data + checks) · Excel (live formulas) · Power BI (DAX)
**Deliverable:** `outputs/executive_kpi_pack_SAMPLE.xlsx` +
`outputs/executive_kpi_pack_SAMPLE.pdf` + `powerbi/` — a monthly
one-page KPI pack with RAG vs target, the year's trend, and a
narrative the owner can read in two minutes

> ⚠️ **What this is and is not.** NoorMart, the customers, the
> products and the 2,230 sale lines are synthetic SAMPLE data,
> generated in this repo with a fixed seed — not a real shop's
> books. What is real is the method: the same daily-lines →
> monthly-KPI → RAG → narrative pipeline, the same target-variance
> rules, and the same Power BI model run unchanged on the client's
> real sales export, and every number in the pack is recomputed
> from the loaded lines, never typed.

## Business question it answers

> "What should I know this month, in one page?"

An owner or manager does not want a dashboard to explore — they
want one page that says how the month went, against the plan, and
what needs attention. This delivery is that page, rebuilt every
month from the sales lines: seven KPIs with RAG against target,
the 12-month trend, the category mix, and a narrative in plain
words that names the cause, not just the number.

## The method (plainly stated)

**Ingest:** 3 SAMPLE files — `daily_sales.csv` (2,230 sale lines,
Jan–Dec 2026), `monthly_targets.csv` (the management plan, 12
rows), `monthly_prior_year.csv` (2025 monthly totals, so YoY is
computed, not typed) — loaded verbatim into staging, then typed
into the star schema (`dim_product`, `dim_customer`, `fact_sales`).

**Define:** every KPI is defined once, in `sql/01_monthly_kpi.sql` —
net revenue = gross sales − returns (a returned line earns
nothing), gross margin = profit on kept lines ÷ net revenue,
new customer = first order in that month, repeat customer =
ordered before that month. The workbook's formulas, the PDF and
the DAX measures all re-implement the same definitions, and
`src/checks.py` proves the three agree.

**Target:** the management plan was set BEFORE the year's sales —
planned revenue × 1.03 (targets sit 3% above plan). Actuals come
from the lines: each month is closed when its net revenue reaches
planned × a demand multiplier, so the RAG mix is earned, not
staged — 6 months beat target, 3 missed it by more than 5%, 3
landed within 5%.

**RAG:** one rule per KPI, written in `sql/03_target_variance.sql`
and repeated in the workbook's formulas and the DAX: revenue and
orders GREEN ≥ 100% of target, AMBER 95–99.9%, RED < 95%; margin
GREEN ≥ target, AMBER within 2 pts below, RED more; returns GREEN
≤ target (lower is better), AMBER up to 1 pt above, RED above;
new customers GREEN ≥ target, AMBER ≥ 80%, RED below.

**Narrate:** `src/analyze.py` builds the month's story from the
numbers — December's −1.8% vs target, the margin cap, the March
returns spike, the repeat-rate climb — so the words and the tables
can never disagree.

**Limits, stated upfront:** this is SAMPLE data — a fictional
retailer, one year only. A real pack has its own products, its own
targets and its own returns pattern; the scripts take the client's
files as inputs, but the RAG thresholds here are the set this
sample was built to show. The pack never invents a sale, a target
or a customer — a missing month is shown as missing, not filled.

## What is inside

| File | What it does |
|---|---|
| `outputs/executive_kpi_pack_SAMPLE.xlsx` | The deliverable: Cover (December pack, live formulas) + Monthly KPI (12 months) + Targets (variance + RAG) + Category Mix + Data Dictionary |
| `outputs/executive_kpi_pack_SAMPLE.pdf` | The one-page pack: KPI cards, revenue-vs-target + category charts, narrative, attention list |
| `outputs/summary.json` | Machine-readable headline numbers + narrative + attention list |
| `outputs/revenue_vs_target.png` | Monthly net revenue vs target, RAG-coloured bars |
| `outputs/kpi_trend.png` | Revenue bars + gross-margin % line vs the 23.5% target |
| `outputs/category_mix.png` | Annual revenue share by category (donut) |
| `outputs/orders_aov.png` | Monthly orders + average order value |
| `data/raw/daily_sales.csv` (2,230 lines) | The SAMPLE sale lines, Jan–Dec 2026 |
| `data/raw/monthly_targets.csv` (12 rows) | The management plan (targets set before the year) |
| `data/raw/monthly_prior_year.csv` (12 rows) | 2025 monthly totals for YoY |
| `data/raw/data_manifest.json` | Counts + the plan the checks verify against |
| `data/processed/noormart.db` | The built database: staging + star schema + monthly_kpi + category_monthly (NOT committed; rebuilds from the scripts) |
| `data/README.md` | Data dictionary + the plan behind the numbers |
| `data/schema.sql` | Staging + star schema |
| `sql/01_monthly_kpi.sql` | The KPI table — the definition of every KPI in the pack |
| `sql/02_growth.sql` | MoM and YoY growth queries |
| `sql/03_target_variance.sql` | Actual vs target, variance %, RAG |
| `sql/04_category_mix.sql` | Category mix by month + annual |
| `powerbi/model.md` | Star-schema model: tables, grain, relationships |
| `powerbi/dax_measures.md` | 12 DAX measures + the verification table they must match |
| `powerbi/build_guide.md` | Step-by-step: data in → model → measures → one-page pack |
| `src/generate_data.py` | Generates the 3 SAMPLE files (seed 30, deterministic) |
| `src/load_data.py` | Loads the files into SQLite, builds the KPI tables |
| `src/analyze.py` | Headline numbers + narrative → outputs/summary.json |
| `src/build_charts.py` | The 4 preview charts (matplotlib renders) |
| `src/build_workbook.py` | Builds the workbook: 5 sheets, live formulas |
| `src/build_report.py` | Builds the one-page report PDF |
| `src/checks.py` | Verification suite — 429 automated checks, all passing (incl. LibreOffice recalc) |
| `requirements.txt` | Pinned: `openpyxl==3.1.2`, `reportlab==5.0.1`, `matplotlib==3.6.3` (Python 3.12) |

## How it fits together

```
data/raw/daily_sales.csv (2,230) ──▶ stg_daily_sales ──▶ fact_sales (2,230)
data/raw/monthly_targets.csv (12) ──▶ stg_monthly_targets ──▶ monthly_targets (12)
data/raw/monthly_prior_year.csv (12) ──▶ stg_prior_year ──▶ monthly_prior_year (12)
        (src/load_data.py: load -> type -> star schema, data/schema.sql)
                                  │
                                  ▼
               sql/01_monthly_kpi.sql ──▶ monthly_kpi (12 months)
               sql/04_category_mix.sql ──▶ category_monthly (60 rows)
                                  │
                                  ▼
               src/analyze.py ──▶ outputs/summary.json (+ narrative)
                                  │
                                  ▼
               src/build_charts.py ──▶ 4 preview PNGs
               src/build_workbook.py ──▶ executive_kpi_pack_SAMPLE.xlsx
               src/build_report.py   ──▶ executive_kpi_pack_SAMPLE.pdf (1 page)
                                  ▲ src/checks.py verifies all of it (incl. LibreOffice recalc)
```

## Headline numbers (SAMPLE — NoorMart, Jan–Dec 2026)

- **Net revenue PKR 13,486,543 · gross sales PKR 13,983,480 · returns PKR 496,937 (3.6%)**
- **1,321 orders · 2,230 sale lines · 392 customers · average order value PKR 10,209**
- **Gross profit PKR 3,167,590 · gross margin 23.49% (target 23.5%)**
- **December 2026: PKR 1,234,359, −1.8% vs target (AMBER), −11.5% MoM, +23.6% YoY**
- **Best month March PKR 1,396,518 · weakest June PKR 929,233 — a PKR 467,285 swing**
- **Revenue RAG over the year: 6 GREEN · 3 AMBER · 3 RED**
- **Repeat rate climbed from 0% (January, a new shop has no repeat base) to 67% (December)**

## December 2026 — the pack month

| KPI | This month | Target | Variance | RAG |
|---|---|---|---|---|
| Net revenue | PKR 1,234,359 | PKR 1,256,600 | −1.8% | AMBER |
| Orders | 117 | 120 | −2.5% | AMBER |
| Avg order value | PKR 10,550 | — | — | — |
| Gross margin | 22.7% | 23.5% | −0.8 pts | AMBER |
| Returns rate | 4.6% | 4.5% | +0.1 pts | AMBER |
| New customers | 35 | 32 | +9.4% | GREEN |
| Repeat rate | 67.0% | — | — | — |

December held, just short of target on every line — the amber
month the pack is built to show honestly instead of rounding up.

## Monthly revenue vs target

| Month | Net revenue (PKR) | Target (PKR) | Variance | RAG |
|---|---|---|---|---|
| January | 950,059 | 978,500 | −2.9% | AMBER |
| February | 968,173 | 906,400 | +6.8% | GREEN |
| March | 1,396,518 | 1,287,500 | +8.5% | GREEN |
| April | 987,906 | 1,081,500 | −8.7% | RED |
| May | 1,352,203 | 1,339,000 | +1.0% | GREEN |
| June | 929,233 | 1,009,400 | −7.9% | RED |
| July | 1,077,984 | 1,050,600 | +2.6% | GREEN |
| August | 1,053,108 | 1,091,800 | −3.5% | AMBER |
| September | 943,625 | 1,019,700 | −7.5% | RED |
| October | 1,198,346 | 1,153,600 | +3.9% | GREEN |
| November | 1,395,029 | 1,318,400 | +5.8% | GREEN |
| December | 1,234,359 | 1,256,600 | −1.8% | AMBER |
| **2026 total** | **13,486,543** | **13,493,000** | **−0.0%** | — |

## Category mix (annual)

| Category | Net revenue (PKR) | Share | Margin |
|---|---|---|---|
| Electronics | 5,927,832 | 44.0% | 20.0% |
| Home & Kitchen | 3,380,860 | 25.1% | 28.0% |
| Groceries | 2,310,137 | 17.1% | 15.9% |
| Clothing | 1,417,953 | 10.5% | 36.0% |
| Beauty & Care | 449,761 | 3.3% | 34.1% |

Electronics carries the shop — 44% of revenue at 20% margin —
which is why the blended margin caps at ~23.5% and why the old
26% margin plan was replaced honestly instead of quietly missed
every month.

## What needs attention

- **March 2026: returns red** — 5.8% vs a 4.5% target, but only 10
  of 227 lines came back: a handful of big-ticket Electronics
  returns, not a broad quality problem.
- **April, June, September: revenue red** — −8.7%, −7.9%, −7.5% vs
  target. June is the year's weakest month (PKR 929,233) and the
  only month where new customers also went red (21 vs 32).
- **May and July: orders red while revenue beat target** — fewer,
  bigger baskets (May's average order value was PKR 12,520, the
  year's highest). Footfall and basket size are telling different
  stories; the pack watches both.
- **Margin target:** the 23.5% blended target already reflects the
  Electronics-heavy mix — raising margin means shifting mix
  (Clothing 36%, Beauty 34%) or renegotiating Electronics cost,
  not asking the shop to sell harder.

## Same logic, four ways — and they must agree

The headline numbers exist in four forms: the sale-line CSVs, the
SQL database, the workbook's formulas, and the report PDF (plus a
fifth, the DAX measures). `src/checks.py` recomputes all of them
from the raw files independently and compares them — a mistake in
any one shows up as a failure — including an independent
re-implementation of the monthly KPIs and the RAG rules that must
reproduce the database row for row. The workbook's formulas were
also recalculated in LibreOffice: every total matches the recompute
exactly, with zero error values.

## Reproduce it (2 minutes)

```bash
pip install -r requirements.txt
python3 src/generate_data.py   # 3 SAMPLE files -> data/raw/
python3 src/load_data.py       # staging -> star schema -> data/processed/noormart.db
python3 src/analyze.py         # headline numbers -> outputs/summary.json
python3 src/build_charts.py    # 4 preview charts -> outputs/
python3 src/build_workbook.py  # outputs/executive_kpi_pack_SAMPLE.xlsx
python3 src/build_report.py    # outputs/executive_kpi_pack_SAMPLE.pdf (1 page)
python3 src/checks.py          # verification suite — expect all passing
```

To reuse it for a real client: put their daily sales export in
place of the demo file (same column names, or update
`data/schema.sql` to their names), set their targets in
`monthly_targets.csv`, and re-run steps 2–7 — the pack, the
workbook and the PDF rebuild themselves from the new lines, and
the 12 DAX measures in `powerbi/dax_measures.md` stay with the
client for the Power BI build. The `.db` file is never committed;
it rebuilds from the scripts.
