# P30 — Power BI build guide: NoorMart Executive KPI Pack (SAMPLE)

Build time: about 45 minutes. You need Power BI Desktop (free)
and this repo. No .pbix is shipped — the client builds it from
their own data following these steps, so the file they keep is
theirs, not a black box.

## 1. Get the data in (10 minutes)

1. **Get Data → Text/CSV** → `data/raw/daily_sales.csv`.
   In Power Query: set `sale_date` to Date, `qty` to Whole Number,
   `unit_price_pkr` / `unit_cost_pkr` / `line_amount_pkr` to Decimal,
   `returned` to Whole Number. Name the query `fact_sales`.
2. **Get Data → Text/CSV** → `data/raw/monthly_targets.csv`.
   Set the target columns to Decimal / Whole Number as named.
   Name it `monthly_targets`.
3. **Get Data → Text/CSV** → `data/raw/monthly_prior_year.csv`.
   Name it `monthly_prior_year`.
4. **Reference `fact_sales`** twice to make the dimensions:
   - `dim_product`: keep `product`, `category`; remove duplicates;
     add `margin_pct` by category (Groceries 0.16, Electronics 0.20,
     Home & Kitchen 0.28, Clothing 0.36, Beauty & Care 0.34).
   - `dim_customer`: group by `customer_id`, take the minimum
     `sale_date` as `first_order_date` and minimum `order_id` as
     `first_order_id`.
5. **Date table** — in Power Query, blank query:
   `= List.Dates(#date(2026,1,1), 365, #duration(1,0,0,0))`,
   convert to table, rename column `date`, add `month` =
   `Date.ToText([date], "yyyy-MM")` and `month_name` =
   `Date.ToText([date], "mmm yyyy")`. Mark it as a date table
   (**Table tools → Mark as date table**, column `date`).
6. Close & Apply.

## 2. Model it (10 minutes)

1. **Model view** — create the relationships in `model.md`:
   `dim_product[product]` → `fact_sales[product]` (1:*),
   `dim_customer[customer_id]` → `fact_sales[customer_id]` (1:*),
   `dim_date[date]` → `fact_sales[sale_date]` (1:*).
   All single-direction. Leave `monthly_targets` and
   `monthly_prior_year` unconnected (the measures join them with
   `TREATAS`).
2. Add the calculated columns from `model.md` to `fact_sales`
   (`is_kept`, `net_amount`, `net_profit`) and to `dim_date`.
3. Hide the helper columns (`is_kept`, `net_amount`, `net_profit`,
   `month` on the fact table) so the field list stays clean.

## 3. Write the measures (10 minutes)

Paste the 12 measures from `dax_measures.md` into the tables named
there. Then check the verification table in that file — December
2026 must read PKR 1,234,359 revenue, 22.7% margin, 4.6% returns.
If revenue reads PKR 1,293,465 instead, a measure is summing
`line_amount_pkr` without excluding returned lines — fix it before
building any visual.

## 4. Build the one-page pack (15 minutes)

One page, portrait, the same layout as `outputs/…_SAMPLE.pdf`:

1. **KPI cards (top):** seven cards — Net revenue, Orders, Avg order
   value, Gross margin %, Returns rate %, New customers, Repeat
   rate %. Each card: the measure, the target (from
   `monthly_targets`), and the RAG colour from the `Revenue RAG`
   logic (green ≥ target, amber within 5%, red below). Use a
   **Card** visual with a background conditional-format rule on
   the variance measure.
2. **Revenue vs target (middle left):** clustered column chart,
   `dim_date[month_name]` on the axis, `Total Revenue` as columns,
   `Target Revenue` as a line. Colour the columns by the RAG rule
   (see `outputs/revenue_vs_target.png` for the target look).
3. **Category mix (middle right):** donut chart, `dim_product[category]`
   as legend, `Total Revenue` as values. Add the year total as the
   centre label (see `outputs/category_mix.png`).
4. **Narrative (bottom):** a text box with the month's story — copy
   the wording style from the PDF (numbers first, then the "why"),
   and rewrite the figures each month from the cards above. The
   narrative is the part the client reads; the charts are the proof.
5. **Slicers (left edge):** Month (single-select, defaults to the
   latest month), Category, Channel. The KPI cards respond to all
   three; the trend chart ignores Category/Channel (set its
   interactions to None) so the year trend never silently shrinks.

## 5. Publish and refresh

- **Publish** to the Power BI Service workspace the owner uses.
- **Refresh:** the model reads the three CSVs. For a real client,
  point Power Query at their sales export / SharePoint folder
  instead and schedule a monthly refresh on the 2nd working day —
  the pack is due the same week the month closes.
- **Targets:** the owner edits `monthly_targets.csv` (or the
  SharePoint list) — no DAX changes needed when a target moves.

## Preview charts

The four PNGs in `outputs/` are matplotlib renders of the same
charts, built from the same database — what the Power BI page
should look like when it is done:

| File | Chart |
|---|---|
| `outputs/revenue_vs_target.png` | Monthly revenue vs target, RAG bars |
| `outputs/kpi_trend.png` | Revenue + gross-margin % trend |
| `outputs/category_mix.png` | Annual revenue share by category |
| `outputs/orders_aov.png` | Orders + average order value |
