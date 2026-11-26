# P30 — Power BI model: NoorMart Executive KPI Pack (SAMPLE)

The same pack as the Excel workbook, rebuilt as a Power BI model so
the owner can filter by month, category and channel and the pack
refreshes itself. The model is a star schema on the SQLite database
(`data/processed/noormart.db` — or the CSVs in `data/raw/` via
Power Query; both routes are in the build guide).

## Tables and grain

| Table | Grain | Rows (SAMPLE) | Source |
|---|---|---|---|
| `fact_sales` | one row per sale line | 2,230 | `data/raw/daily_sales.csv` |
| `dim_product` | one row per product | 25 | `data/raw/daily_sales.csv` (distinct product + category) |
| `dim_customer` | one row per customer | 392 | `data/raw/daily_sales.csv` (first order per customer) |
| `monthly_targets` | one row per month | 12 | `data/raw/monthly_targets.csv` |
| `monthly_prior_year` | one row per month (2025) | 12 | `data/raw/monthly_prior_year.csv` |
| `dim_date` | one row per day | 365 | generated in Power Query (see build guide) |

## Relationships (all single-direction, one-to-many)

```
dim_product  1 ──<  fact_sales  >── 1  dim_customer
dim_date     1 ──<  fact_sales
monthly_targets (month)  1 ──<  fact_sales (month)   — inactive, used by
                                                       the vs-target measures
                                                       via TREATAS
monthly_prior_year — NOT related; YoY reads it by month key in DAX
```

`fact_sales` carries `month` (YYYY-MM) as a text column so the
targets table can join on it without a date table. The date table
relates on `fact_sales[sale_date]` for day-level filtering.

## Columns on fact_sales

| Column | Type | Notes |
|---|---|---|
| `order_id` | text | 1,321 distinct orders |
| `sale_date` | date | Jan–Dec 2026 |
| `month` | text (YYYY-MM) | join key to targets |
| `customer_key` / `product_key` | integer | FKs |
| `channel` | text | Store / Online |
| `qty` | integer | |
| `unit_price_pkr` / `unit_cost_pkr` | decimal | |
| `line_amount_pkr` | decimal | qty × unit_price |
| `gross_profit_pkr` | decimal | (price − cost) × qty, kept lines only in measures |
| `returned` | 0 / 1 | 1 = returned in full |

## Calculated columns (in the model, not in the source)

- `fact_sales[is_kept] = IF(fact_sales[returned] = 0, 1, 0)`
- `fact_sales[net_amount] = IF(fact_sales[returned] = 0, fact_sales[line_amount_pkr], 0)`
- `fact_sales[net_profit] = IF(fact_sales[returned] = 0, fact_sales[gross_profit_pkr], 0)`
- `dim_date[month] = FORMAT(dim_date[date], "yyyy-MM")`
- `dim_date[month_name] = FORMAT(dim_date[date], "mmm yyyy")`

## Design choices (and why)

- **Net revenue is a measure, not a column.** The rule "returned
  lines earn nothing" lives in one place (`Total Revenue`), so a
  filter can never silently count a returned TV as a sale.
- **Targets are a table, not typed numbers.** The owner changes a
  target in the CSV / SharePoint list and the pack re-reads it.
- **No bidirectional filters.** The targets table is joined with
  `TREATAS` inside the vs-target measures, so a month slicer never
  double-counts targets through the fact table.
- **Prior year is a separate table.** 2025 has monthly totals only
  (no daily lines), so it cannot sit in the fact table — YoY reads
  it by month key.
